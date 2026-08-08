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

    def test_analyze_response_exposes_active_risk_thresholds(self):
        """The /analyze response must carry the thresholds the backend used,
        so the frontend never hardcodes its own."""
        topology = {
            "assets": {
                "plc_1": {
                    "kind": "device",
                    "cvss_type": 5.0,
                    "exposed": True,
                    "patched": False,
                    "consequence_severity": 5.0,
                }
            },
            "relationships": [],
        }
        response = self.client.post("/analyze", json={"topology": topology, "evidence": []})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        thresholds = body["summary"]["risk_thresholds"]
        self.assertEqual(thresholds, {"critical": 0.75, "high": 0.5, "moderate": 0.25})

    def test_settings_endpoint_exposes_cvss_and_threshold_settings(self):
        """The settings endpoint exposes cvss_mapping, cvss_logistic_params
        and risk_thresholds for the frontend to render."""
        response = self.client.get("/settings")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["cvss_mapping"], "logistic")
        self.assertEqual(body["cvss_logistic_params"], {"k": 0.8, "x0": 5.0})
        self.assertEqual(body["risk_thresholds"], {"critical": 0.75, "high": 0.5, "moderate": 0.25})

    def test_upload_topology_returns_warnings(self):
        topology = {
            "assets": {
                "a": {"kind": "device"},
                "b": {"kind": "device"},
            },
            "relationships": [
                ["a", "b", "connects-to", False],
                ["a", "a", "connects-to", False],
            ],
        }
        response = self.client.post("/upload-topology", json={"topology": topology})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertGreaterEqual(len(response.json()["warnings"]), 1)
        self.assertTrue(any("self-loop" in w for w in response.json()["warnings"]))
        self.assertEqual(response.json()["relationship_count"], 1)

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
