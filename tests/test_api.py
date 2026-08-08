import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api import app


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_analyze_endpoint_returns_generic_500_on_internal_error(self):
        with patch("backend.api.analyze", side_effect=RuntimeError("internal failure")):
            response = self.client.post(
                "/analyze",
                json={
                    "topology": {
                        "assets": {
                            "plc_1": {
                                "kind": "device",
                                "cvss_type": 5.0,
                                "exposed": True,
                                "patched": False,
                                "consequence_severity": 3.0,
                            }
                        },
                        "relationships": [],
                    },
                    "evidence": [],
                },
            )
        self.assertEqual(response.status_code, 500)
        body = response.json()
        self.assertEqual(body["error_code"], "INTERNAL_ERROR")
        self.assertEqual(body["detail"], "An internal error occurred. Please try again later.")
        self.assertIn("request_id", body)

    def test_upload_topology_file_returns_400_for_invalid_json(self):
        response = self.client.post(
            "/upload-topology-file",
            files={"file": ("topology.json", b"{invalid json}", "application/json")},
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["error_code"], "HTTP_400")
        self.assertTrue(
            body["detail"].startswith("Invalid JSON: Expecting property name enclosed in double quotes")
        )
        self.assertIn("request_id", body)

    def test_upload_topology_file_returns_400_for_invalid_yaml(self):
        response = self.client.post(
            "/upload-topology-file",
            files={"file": ("topology.yaml", b"assets: [unclosed", "application/x-yaml")},
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["error_code"], "HTTP_400")
        self.assertTrue(body["detail"].startswith("Invalid YAML:"))
        self.assertIn("request_id", body)

    def test_upload_topology_file_returns_400_for_invalid_xml(self):
        response = self.client.post(
            "/upload-topology-file",
            files={"file": ("topology.xml", b"<Topology><Asset></Topology>", "application/xml")},
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["error_code"], "HTTP_400")
        self.assertTrue(body["detail"].startswith("Invalid XML/AML:"))
        self.assertIn("request_id", body)

    def test_upload_topology_file_rejects_legacy_vsd_with_guidance(self):
        # Legacy binary .vsd files cannot be parsed natively. The API must
        # reject them with an actionable conversion message rather than
        # claiming support that does not exist.
        path = Path(__file__).resolve().parent / "validation_files" / "topology.vsdx"
        with path.open("rb") as handle:
            response = self.client.post(
                "/upload-topology-file",
                files={"file": ("topology.vsd", handle, "application/octet-stream")},
            )
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn("Legacy binary Visio .vsd files cannot be parsed natively", body["detail"])

    def test_upload_topology_file_accepts_vsdx_files(self):
        path = Path(__file__).resolve().parent / "validation_files" / "topology.vsdx"
        with path.open("rb") as handle:
            response = self.client.post(
                "/upload-topology-file",
                files={"file": (path.name, handle, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("message", body)
        self.assertEqual(body["asset_count"], len(body["topology"]["assets"]))


if __name__ == "__main__":
    unittest.main()
