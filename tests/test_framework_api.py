"""Tests for the main framework API (cli.run)."""

import unittest

from backend.cli import run


class FrameworkApiTests(unittest.TestCase):
    """Test the framework's core run() function."""

    def test_run_returns_structured_result(self):
        """Verify that run() returns all expected keys."""
        result = run("data/swat_example.json", {"local_hmi": 1})

        self.assertIsInstance(result, dict)
        self.assertIn("graph", result)
        self.assertIn("posteriors", result)
        self.assertIn("risk_scores", result)
        self.assertIn("attack_paths", result)
        self.assertIn("summary", result)
        self.assertIn("evidence_used", result)
        self.assertIn("timings", result)
        self.assertIn("cpts", result)

    def test_run_with_empty_evidence(self):
        """Verify that run() works with empty evidence."""
        result = run("data/swat_example.json", {})
        self.assertIn("posteriors", result)
        self.assertGreater(len(result["posteriors"]), 0)

    def test_run_with_inline_topology(self):
        """Verify that run() works with an inline topology dict."""
        topology = {
            "assets": {
                "plc_1": {
                    "kind": "device",
                    "cvss_type": 8.8,
                    "exposed": True,
                    "patched": False,
                    "consequence_severity": 5.0,
                }
            },
            "relationships": [],
        }
        result = run(topology)
        self.assertIn("risk_scores", result)
        self.assertEqual(len(result["risk_scores"]), 1)


if __name__ == "__main__":
    unittest.main()

