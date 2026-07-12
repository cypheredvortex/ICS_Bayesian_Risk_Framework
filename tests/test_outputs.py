import tempfile
import unittest
from pathlib import Path

from assets import load_topology
from graph_builder import build_graph_skeleton
from outputs import write_graph_image


class OutputsTests(unittest.TestCase):
    def test_write_graph_image_creates_png_file(self):
        assets, relationships = load_topology("data/swat_example.json")
        model, edge_weights = build_graph_skeleton(relationships, node_ids=assets.keys())

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "graph.png"
            written = write_graph_image(model, edge_weights, relationships, path=out_path)

            self.assertTrue(written.exists())
            self.assertEqual(written.suffix, ".png")


if __name__ == "__main__":
    unittest.main()
