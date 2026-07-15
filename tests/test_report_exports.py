import unittest

from fastapi.testclient import TestClient

from backend.app.main import app


class ReportExportTests(unittest.TestCase):
    def test_reports_are_downloadable(self):
        client = TestClient(app)

        csv_response = client.get('/reports/risk_table.csv')
        self.assertEqual(csv_response.status_code, 200)
        self.assertEqual(csv_response.headers['content-type'].split(';')[0], 'text/csv')
        self.assertIn('risk_table', csv_response.headers['content-disposition'])

        json_response = client.get('/reports/posteriors.json')
        self.assertEqual(json_response.status_code, 200)
        self.assertEqual(json_response.headers['content-type'].split(';')[0], 'application/json')
        self.assertIn('posteriors', json_response.headers['content-disposition'])

        pdf_response = client.get('/reports/assessment.pdf')
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response.headers['content-type'].split(';')[0], 'application/pdf')
        self.assertIn('assessment', pdf_response.headers['content-disposition'])


if __name__ == '__main__':
    unittest.main()
