import unittest

from fastapi.testclient import TestClient

from backend.app.main import _build_pdf_bytes, app


class ReportExportTests(unittest.TestCase):
    def test_reports_are_downloadable(self):
        client = TestClient(app)

        csv_response = client.get('/reports/risk_table.csv')
        self.assertEqual(csv_response.status_code, 200)
        self.assertEqual(csv_response.headers['content-type'].split(';')[0], 'text/csv')
        self.assertIn('risk_table', csv_response.headers['content-disposition'])

        pdf_response = client.get('/reports/assessment.pdf')
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response.headers['content-type'].split(';')[0], 'application/pdf')
        self.assertIn('assessment', pdf_response.headers['content-disposition'])

    def test_only_decision_ready_reports_are_exposed(self):
        client = TestClient(app)

        self.assertEqual(
            client.get('/reports').json(),
            {
                'risk_table': '/reports/risk_table.csv',
                'assessment_pdf': '/reports/assessment.pdf',
            },
        )
        self.assertEqual(client.get('/reports/posteriors.json').status_code, 404)

    def test_pdf_report_uses_separate_readable_lines(self):
        report = _build_pdf_bytes({
            'summary': {'overall_risk': 1.2, 'risk_level': 'high', 'asset_count': 2, 'relationship_count': 1},
            'risk_scores': [{'asset': 'PLC-01', 'risk': 0.9, 'P(compromised|evidence)': 0.6}],
            'attack_paths': [],
        })
        self.assertIn(b'Highest-risk assets', report)
        self.assertGreater(report.count(b' Tm ('), 5)


if __name__ == '__main__':
    unittest.main()
