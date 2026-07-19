import unittest

from assets import load_topology
from cpt_generator import parameterize
from graph_builder import build_graph_skeleton
from inference import compute_posteriors
from probability import compute_base_probs


class InferenceTests(unittest.TestCase):
    def test_compute_posteriors_accepts_valid_evidence_nodes(self):
        assets, relationships = load_topology("data/swat_example.json")
        model, edge_weights = build_graph_skeleton(relationships, node_ids=assets.keys())
        base_probs = compute_base_probs(assets)
        model = parameterize(model, edge_weights, base_probs)

        posteriors = compute_posteriors(model, {"local_hmi": 1})

        self.assertIsInstance(posteriors, dict)
        self.assertGreater(len(posteriors), 0)
        self.assertNotIn("local_hmi", posteriors)


if __name__ == "__main__":
    unittest.main()
