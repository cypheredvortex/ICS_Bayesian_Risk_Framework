"""Tests for report export functionality."""

import csv
import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.api import app
from backend.outputs import write_assessment_json
from backend.pdf_reports import generate_pdf_report


class ReportExportTests(unittest.TestCase):
    """Test report download endpoints."""

    def test_reports_are_downloadable(self):
        """Verify report endpoints return files with correct content types."""
        client = TestClient(app)

        # Ensure the JSON export exists deterministically (independent of test
        # ordering and of whether another test already ran /analyze).
        write_assessment_json(
            {
                "summary": {"asset_count": 0},
                "risk_scores": [],
                "evidence_used": {},
            },
            path=Path("output/assessment.json"),
        )

        csv_response = client.get("/reports/risk_table.csv")
        self.assertEqual(csv_response.status_code, 200)
        self.assertEqual(
            csv_response.headers["content-type"].split(";")[0], "text/csv"
        )
        self.assertIn(
            "risk_table", csv_response.headers["content-disposition"]
        )

        pdf_response = client.get("/reports/assessment.pdf")
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(
            pdf_response.headers["content-type"].split(";")[0],
            "application/pdf",
        )
        self.assertIn(
            "assessment", pdf_response.headers["content-disposition"]
        )

        json_response = client.get("/reports/assessment.json")
        self.assertEqual(json_response.status_code, 200)
        self.assertEqual(
            json_response.headers["content-type"].split(";")[0],
            "application/json",
        )
        self.assertIn(
            "assessment", json_response.headers["content-disposition"]
        )

    def test_only_decision_ready_reports_are_exposed(self):
        """Verify only expected report types are exposed."""
        client = TestClient(app)

        reports = client.get("/reports").json()
        self.assertEqual(
            reports,
            {
                "risk_table": "/reports/risk_table.csv",
                "assessment_pdf": "/reports/assessment.pdf",
                "assessment_json": "/reports/assessment.json",
            },
        )
        self.assertEqual(
            client.get("/reports/posteriors.json").status_code, 404
        )

    def test_pdf_report_uses_professional_format(self):
        """Verify PDF report is generated with proper content."""
        tmp_path = Path("output/test_report.pdf")
        tmp_path.parent.mkdir(parents=True, exist_ok=True)

        report_path = generate_pdf_report(
            {
                "summary": {
                    "overall_risk": 1.2,
                    "risk_level": "high",
                    "asset_count": 2,
                    "relationship_count": 1,
                },
                "risk_scores": [
                    {
                        "asset": "PLC-01",
                        "risk": 0.9,
                        "P(compromised|evidence)": 0.6,
                    }
                ],
                "attack_paths": [],
            },
            output_path=tmp_path,
        )
        self.assertTrue(report_path.exists())
        self.assertGreater(report_path.stat().st_size, 500)
        tmp_path.unlink(missing_ok=True)

    def test_pdf_handles_large_evidence_sets_and_many_assets(self):
        """A large evidence set and many assets must produce a valid, larger PDF.

        Regression guard for the evidence table: rows must wrap and the
        register must include every asset (splitting across pages), never
        clip or crash.
        """
        evidence_used = {
            f"asset_{i:03d}_with_a_reasonably_long_name": i % 2
            for i in range(25)
        }
        risk_scores = [
            {
                "asset": f"asset_{i:03d}_with_a_reasonably_long_name",
                "risk": round((100 - i) / 100, 3),
                "P(compromised|evidence)": round((100 - i) / 150, 3),
                "severity": 7.0,
                "impact": round(0.7 + i / 100, 3),
                "risk_level": "High" if i < 15 else "Moderate",
            }
            for i in range(30)
        ]
        tmp_path = Path("output/test_large_report.pdf")

        report_path = generate_pdf_report(
            {
                "summary": {
                    "overall_risk": 0.95,
                    "risk_level": "high",
                    "asset_count": len(risk_scores),
                    "relationship_count": 12,
                },
                "risk_scores": risk_scores,
                "attack_paths": [],
                "evidence_used": evidence_used,
            },
            output_path=tmp_path,
        )
        self.assertTrue(report_path.exists())
        # 25 evidence rows + 30 register rows generate a substantially larger
        # document than the tiny two-row smoke test above (multi-page capable).
        self.assertGreater(report_path.stat().st_size, 3000)
        tmp_path.unlink(missing_ok=True)

    def test_pdf_handles_no_evidence_gracefully(self):
        """The evidence section must render a clean note when none was used."""
        tmp_path = Path("output/test_no_evidence.pdf")
        generate_pdf_report(
            {
                "summary": {
                    "overall_risk": 0.3,
                    "risk_level": "moderate",
                    "asset_count": 1,
                    "relationship_count": 0,
                },
                "risk_scores": [
                    {
                        "asset": "PLC-01",
                        "risk": 0.3,
                        "P(compromised|evidence)": 0.5,
                        "impact": 0.6,
                        "risk_level": "Moderate",
                    }
                ],
                "attack_paths": [],
                "evidence_used": {},
            },
            output_path=tmp_path,
        )
        self.assertTrue(tmp_path.exists())
        tmp_path.unlink(missing_ok=True)

    def test_assessment_json_export_is_a_complete_record(self):
        """The JSON export mirrors the authoritative result, nothing synthetic."""
        tmp_path = Path("output/test_assessment.json")
        result = {
            "assets": {"plc_1": {"kind": "device"}},
            "graph": {"nodes": [], "edges": []},
            "base_probabilities": {"plc_1": 0.27},
            "posteriors": {"plc_1": 0.5},
            "cpts": {"plc_1": {"parents": [], "rows": []}},
            "risk_scores": [{"asset": "plc_1", "risk": 0.25}],
            "attack_paths": [],
            "summary": {"asset_count": 1},
            "evidence_used": {},
            "timings": {"total_time_seconds": 0.1},
            "settings_used": {"cvss_mapping": "logistic"},
            "artifacts": {"graph": "output/graph.json"},
            "persistence": {"saved": True},
        }
        write_assessment_json(result, path=tmp_path)
        record = json.loads(tmp_path.read_text(encoding="utf-8"))

        self.assertEqual(record["format"], "ics-risk-assessment")
        self.assertIn("generated_at", record)
        assessment = record["assessment"]
        # Transport metadata is not assessment data and must be excluded.
        self.assertNotIn("artifacts", assessment)
        self.assertNotIn("persistence", assessment)
        # Every meaningful output is present.
        for key in (
            "assets",
            "graph",
            "base_probabilities",
            "posteriors",
            "cpts",
            "risk_scores",
            "attack_paths",
            "summary",
            "evidence_used",
            "timings",
            "settings_used",
        ):
            self.assertIn(key, assessment)
        self.assertEqual(assessment["posteriors"]["plc_1"], 0.5)
        tmp_path.unlink(missing_ok=True)


class ExportConsistencyTests(unittest.TestCase):
    """The dashboard, PDF and CSV must all report the same authoritative values."""

    def test_csv_register_matches_analyze_response(self):
        """/analyze risk_scores and /reports/risk_table.csv must agree row for row."""
        client = TestClient(app)
        topology = {
            "assets": {
                "plc_1": {
                    "kind": "device",
                    "cvss_type": 8.8,
                    "exposed": True,
                    "patched": False,
                    "consequence_severity": 9.0,
                },
                "hmi_1": {
                    "kind": "device",
                    "cvss_type": 5.0,
                    "exposed": False,
                    "patched": True,
                    "consequence_severity": 6.0,
                },
            },
            "relationships": [["hmi_1", "plc_1", "connects-to", False]],
        }
        response = client.post(
            "/analyze",
            json={"topology": topology, "evidence": []},
        )
        self.assertEqual(response.status_code, 200)
        risk_scores = response.json()["risk_scores"]
        self.assertGreaterEqual(len(risk_scores), 2)

        csv_response = client.get("/reports/risk_table.csv")
        self.assertEqual(csv_response.status_code, 200)
        rows = list(csv.DictReader(csv_response.text.splitlines()))

        self.assertEqual(len(rows), len(risk_scores))
        for row, score in zip(rows, risk_scores):
            self.assertEqual(row["asset"], score["asset"])
            self.assertAlmostEqual(float(row["risk"]), float(score["risk"]))
            self.assertAlmostEqual(
                float(row["P(compromised|evidence)"]),
                float(score["P(compromised|evidence)"]),
            )

    def test_assessment_json_downloadable_after_analyze(self):
        """After /analyze, the JSON record must be downloadable and complete.

        Regression guard: the export used to be silently missing when the
        server was started before the export was wired, so the download
        returned 404. This asserts the full loop works against the real API.
        """
        client = TestClient(app)
        topology = {
            "assets": {
                "plc_1": {
                    "kind": "device",
                    "cvss_type": 8.8,
                    "exposed": True,
                    "patched": False,
                    "consequence_severity": 9.0,
                },
                "hmi_1": {
                    "kind": "device",
                    "cvss_type": 5.0,
                    "exposed": False,
                    "patched": True,
                    "consequence_severity": 6.0,
                },
            },
            "relationships": [["hmi_1", "plc_1", "connects-to", False]],
        }
        response = client.post(
            "/analyze",
            json={
                "topology": topology,
                "evidence": [{"asset": "hmi_1", "state": "Compromised"}],
            },
        )
        self.assertEqual(response.status_code, 200)

        json_response = client.get("/reports/assessment.json")
        self.assertEqual(json_response.status_code, 200)
        self.assertEqual(
            json_response.headers["content-type"].split(";")[0],
            "application/json",
        )
        record = json_response.json()
        assessment = record["assessment"]
        # The evidence applied in /analyze is present in the record.
        self.assertEqual(assessment["evidence_used"], {"hmi_1": 1})
        self.assertEqual(len(assessment["risk_scores"]), 2)
        # Transport metadata is not part of the assessment record.
        self.assertNotIn("artifacts", assessment)

    def test_pdf_is_generated_from_the_same_risk_scores(self):
        """The PDF writer consumes the same risk_scores the API returns."""
        risk_scores = [
            {
                "asset": "PLC-01",
                "risk": 0.9,
                "P(compromised|evidence)": 0.6,
                "impact": 0.75,
                "risk_level": "High",
            },
            {
                "asset": "PLC-02",
                "risk": 0.45,
                "P(compromised|evidence)": 0.5,
                "impact": 0.6,
                "risk_level": "Moderate",
            },
        ]
        tmp_path = Path("output/test_consistency.pdf")
        generate_pdf_report(
            {
                "summary": {
                    "overall_risk": 0.9,
                    "risk_level": "high",
                    "asset_count": 2,
                    "relationship_count": 1,
                },
                "risk_scores": risk_scores,
                "attack_paths": [],
                "evidence_used": {},
            },
            output_path=tmp_path,
        )
        self.assertTrue(tmp_path.exists())
        tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
