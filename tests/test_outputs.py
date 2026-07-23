"""Tests for the outputs module (file writers)."""

import tempfile
import unittest
from pathlib import Path

from backend.assets import load_topology
from backend.graph_builder import build_graph_skeleton
from backend.outputs import write_graph_image, write_metrics_json


class OutputsTests(unittest.TestCase):
    """Test output file writers."""

    def setUp(self):
        self.assets, self.relationships = load_topology("data/swat_example.json")
        self.model, self.edge_weights = build_graph_skeleton(
            self.relationships, node_ids=self.assets.keys()
        )

    def test_write_graph_image_creates_png_file(self):
        """Verify graph image writer creates a PNG file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "graph.png"
            written = write_graph_image(
                self.model, self.edge_weights, self.relationships, path=out_path
            )

            self.assertTrue(written.exists())
            self.assertEqual(written.suffix, ".png")
            self.assertGreater(written.stat().st_size, 0)

    def test_write_metrics_json_creates_json_file(self):
        """Verify metrics JSON writer creates a valid JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "metrics.json"
            written = write_metrics_json(
                {"runtime_seconds": 0.123, "asset_count": 3}, path=out_path
            )

            self.assertTrue(written.exists())
            self.assertEqual(written.suffix, ".json")
            self.assertGreater(written.stat().st_size, 0)

    def test_write_metrics_json_with_empty_metrics(self):
        """Verify metrics writer handles empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "metrics.json"
            written = write_metrics_json({}, path=out_path)
            self.assertTrue(written.exists())


if __name__ == "__main__":
    unittest.main()

