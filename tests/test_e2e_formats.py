"""
tests/test_e2e_formats.py - End-to-end integration test.

For every supported topology file format, upload the file, parse it, and run
the complete analysis pipeline (/analyze). This validates the full chain:
import -> normalize -> validate -> Bayesian network -> inference -> risk.
"""

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from backend.api import app

VALIDATION_DIR = Path(__file__).resolve().parent / "validation_files"

# (filename, media_type)
FORMAT_CASES = [
    ("topology.json", "application/json"),
    ("topology.csv", "text/csv"),
    ("topology.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ("topology.graphml", "application/xml"),
    ("topology.xml", "application/xml"),
    ("topology.aml", "application/xml"),
    ("topology.vsdx", "application/octet-stream"),
]


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.parametrize("filename,media_type", FORMAT_CASES)
def test_full_pipeline_for_each_format(client, filename, media_type):
    path = VALIDATION_DIR / filename
    if not path.exists():
        pytest.skip(f"fixture {filename} not present")

    with path.open("rb") as handle:
        upload = client.post(
            "/upload-topology-file",
            files={"file": (filename, handle, media_type)},
        )
    assert upload.status_code == 200, upload.text
    body = upload.json()
    assert body["asset_count"] > 0
    assert body["relationship_count"] > 0

    analysis = client.post(
        "/analyze",
        json={"topology": body["topology"], "evidence": []},
    )
    assert analysis.status_code == 200, analysis.text
    data = analysis.json()

    assert data["summary"]["asset_count"] == body["asset_count"]
    assert len(data["risk_scores"]) == body["asset_count"]
    assert len(data["posteriors"]) == body["asset_count"]
    assert len(data["base_probabilities"]) == body["asset_count"]
    assert len(data["cpts"]) == body["asset_count"]
    # Every posterior is a genuine probability in [0, 1].
    for node, prob in data["posteriors"].items():
        assert 0.0 <= prob <= 1.0, f"{node}: {prob}"


def test_analyze_pipeline_produces_expected_artifacts(client):
    """The /analyze response exposes every step of the Bayesian workflow."""
    payload = {
        "assets": {
            "plc_1": {
                "kind": "device",
                "exposed": True,
                "patched": False,
                "consequence_severity": 9,
                "vulnerabilities": [
                    {
                        "cve_id": "CVE-2021-44228",
                        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
                        "source": "NVD",
                    }
                ],
            }
        },
        "relationships": [],
    }
    response = client.post("/analyze", json={"topology": payload, "evidence": []})
    assert response.status_code == 200, response.text
    data = response.json()

    # CVSS vector was scored with the official v3.1 equations.
    assert data["assets"]["plc_1"]["cvss_type"] == 10.0
    # Risk index = P x impact, with impact = severity/10 x scope (scope=1).
    row = data["risk_scores"][0]
    assert row["risk"] == pytest.approx(data["posteriors"]["plc_1"] * 0.9)
