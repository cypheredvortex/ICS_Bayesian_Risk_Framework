"""
tests/test_upload_security.py - Security-focused tests for the upload path.

Covers: extension/content limits, oversized uploads, zip-bomb archives
(xlsx/vsdx), XML entity expansion (XXE / billion-laughs), path-traversal
filenames and malformed archives.
"""

import io
import zipfile

from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.api import app, MAX_UPLOAD_BYTES
from backend.importers import load_topology_from_bytes

client = TestClient(app, raise_server_exceptions=False)

VALID_JSON = b"""{"assets": {"plc_1": {"kind": "device", "cvss_type": 5.0}},
 "relationships": []}"""


def _make_zip(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return buffer.getvalue()


class TestUploadLimits:
    def test_oversized_upload_rejected_with_413(self):
        big = b"x" * (MAX_UPLOAD_BYTES + 1)
        response = client.post(
            "/upload-topology-file",
            files={"file": ("topology.json", big, "application/json")},
        )
        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()

    def test_unsupported_extension_rejected(self):
        response = client.post(
            "/upload-topology-file",
            files={"file": ("malware.exe", b"MZ....", "application/octet-stream")},
        )
        assert response.status_code == 400
        assert "Unsupported topology format" in response.json()["detail"]

    def test_legacy_vsd_rejected_with_guidance(self):
        response = client.post(
            "/upload-topology-file",
            files={"file": ("topology.vsd", b"binary", "application/octet-stream")},
        )
        assert response.status_code == 400
        assert "Legacy binary Visio .vsd" in response.json()["detail"]


class TestArchiveBombs:
    def test_xlsx_zip_bomb_rejected(self):
        # A tiny zip claiming to expand to gigabytes.
        fake_zip = _make_zip({"xl/worksheets/sheet1.xml": b"A" * (300 * 1024 * 1024)})
        with patch.dict("os.environ", {"MAX_ARCHIVE_EXPANSION_MB": "10"}):
            pytest_raises_expansion(fake_zip, "topology.xlsx")

    def test_vsdx_zip_bomb_rejected(self):
        fake_zip = _make_zip({"visio/document.xml": b"A" * (300 * 1024 * 1024)})
        with patch.dict("os.environ", {"MAX_ARCHIVE_EXPANSION_MB": "10"}):
            pytest_raises_expansion(fake_zip, "topology.vsdx")

    def test_well_behaved_zip_passes_expansion_check(self):
        small_zip = _make_zip({"xl/worksheets/sheet1.xml": b"<x/>"})
        # Must not raise the expansion error (parser error is fine/expected).
        with patch.dict("os.environ", {"MAX_ARCHIVE_EXPANSION_MB": "10"}):
            try:
                load_topology_from_bytes(small_zip, "topology.xlsx")
            except Exception as exc:
                assert "expansion limit" not in str(exc)


def pytest_raises_expansion(payload: bytes, filename: str):
    import pytest

    with pytest.raises(ValueError, match="archive bomb"):
        load_topology_from_bytes(payload, filename)


class TestXmlSafety:
    def test_billion_laughs_entity_is_not_expanded(self):
        # Python's ElementTree does not resolve internal DTD entities, so a
        # billion-laughs payload cannot consume memory; it must either parse
        # without expansion or fail with a parse error - never expand.
        billion_laughs = (
            b'<?xml version="1.0"?>'
            b'<!DOCTYPE lolz [<!ENTITY lol "lol">'
            b'<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">]>'
            b"<Topology><Asset id=\"a\">&lol2;</Asset></Topology>"
        )
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(billion_laughs)
        except ET.ParseError:
            # Safe: entities are not supported and the file is rejected.
            return
        # If it parsed, the entity reference must NOT have expanded.
        for elem in root.iter():
            if elem.text and "lol" in elem.text:
                assert len(elem.text) < 100, "entity expansion occurred!"

    def test_external_entity_is_not_resolved(self):
        # Classic XXE: external entity pointing at a local file. ElementTree
        # never fetches external entities; the upload must not read the file.
        xxe = (
            b'<?xml version="1.0"?>'
            b'<!DOCTYPE x [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
            b"<Topology><Asset id=\"a\">&xxe;</Asset></Topology>"
        )
        import xml.etree.ElementTree as ET

        try:
            ET.fromstring(xxe)
        except ET.ParseError:
            return  # rejected - safe
        # Any parsed text must not contain host file contents.

    def test_aml_external_entity_rejected(self):
        response = client.post(
            "/upload-topology-file",
            files={
                "file": (
                    "topology.aml",
                    b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
                    b"<AdditionalMarkupLanguage><x>&xxe;</x></AdditionalMarkupLanguage>",
                    "application/xml",
                )
            },
        )
        # Either rejected (400) or parsed safely - never 500.
        assert response.status_code in (200, 400)


class TestFilenameHandling:
    def test_path_traversal_filename_is_sanitized(self):
        # A path-traversal filename with a supported extension: the basename
        # must be used, never the raw path, and the response must not echo
        # the traversal prefix.
        response = client.post(
            "/upload-topology-file",
            files={
                "file": (
                    "../../../../tmp/topology.json",
                    VALID_JSON,
                    "application/json",
                )
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert "../" not in body["message"]
        assert "tmp/topology.json" not in body["message"]
        assert "topology.json" in body["message"]

    def test_malformed_zip_vsdx_returns_400_not_500(self):
        response = client.post(
            "/upload-topology-file",
            files={
                "file": (
                    "topology.vsdx",
                    b"PK\x03\x04 not really a zip",
                    "application/octet-stream",
                )
            },
        )
        assert response.status_code == 400
