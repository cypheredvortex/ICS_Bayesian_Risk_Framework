import unittest

from main import run


class FrameworkApiTests(unittest.TestCase):
    def test_run_returns_structured_result(self):
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


if __name__ == "__main__":
    unittest.main()
