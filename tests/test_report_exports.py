"""Tests for report export functionality."""

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.api import app
from backend.pdf_reports import generate_pdf_report


class ReportExportTests(unittest.TestCase):
    """Test report download endpoints."""

    def test_reports_are_downloadable(self):
        """Verify report endpoints return files with correct content types."""
        client = TestClient(app)

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

    def test_only_decision_ready_reports_are_exposed(self):
        """Verify only expected report types are exposed."""
        client = TestClient(app)

        reports = client.get("/reports").json()
        self.assertEqual(
            reports,
            {
                "risk_table": "/reports/risk_table.csv",
                "assessment_pdf": "/reports/assessment.pdf",
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


if __name__ == "__main__":
    unittest.main()

