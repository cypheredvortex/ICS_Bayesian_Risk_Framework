"""Tests for the inference module."""

import unittest

from backend.assets import load_topology
from backend.cpt_generator import parameterize
from backend.graph_builder import build_graph_skeleton
from backend.inference import (
    EvidenceError,
    compute_posteriors,
    compute_posteriors_with_evidence,
)
from backend.probability import compute_base_probs


class InferenceTests(unittest.TestCase):
    """Test Bayesian network inference."""

    def setUp(self):
        """Load test topology and build model."""
        self.assets, self.relationships = load_topology("data/swat_example.json")
        self.model, self.edge_weights = build_graph_skeleton(
            self.relationships, node_ids=self.assets.keys()
        )
        self.base_probs = compute_base_probs(self.assets)
        self.model = parameterize(self.model, self.edge_weights, self.base_probs)

    def test_compute_posteriors_accepts_valid_evidence_nodes(self):
        """Verify posteriors return for valid evidence."""
        posteriors = compute_posteriors(self.model, {"local_hmi": 1})

        self.assertIsInstance(posteriors, dict)
        self.assertGreater(len(posteriors), 0)
        self.assertNotIn("local_hmi", posteriors)

    def test_compute_posteriors_returns_all_nodes_for_empty_evidence(self):
        """Verify all nodes get posteriors with empty evidence."""
        posteriors = compute_posteriors(self.model, {})
        self.assertEqual(len(posteriors), len(self.model.nodes()))

    def test_compute_posteriors_raises_error_for_invalid_node(self):
        """Verify EvidenceError for unknown evidence nodes."""
        with self.assertRaises(EvidenceError):
            compute_posteriors(self.model, {"nonexistent_node": 1})

    def test_compute_posteriors_raises_error_for_invalid_value(self):
        """Verify EvidenceError for invalid evidence values."""
        with self.assertRaises(EvidenceError):
            compute_posteriors(self.model, {"local_hmi": 2})

    def test_compute_posteriors_with_evidence_returns_sanitized(self):
        """Verify _with_evidence variant returns sanitized evidence."""
        posteriors, sanitized = compute_posteriors_with_evidence(
            self.model, {"local_hmi": 1}
        )
        self.assertIn("local_hmi", sanitized)
        self.assertEqual(sanitized["local_hmi"], 1)

    def test_posterior_probabilities_in_valid_range(self):
        """Verify all posterior probabilities are in [0, 1]."""
        posteriors = compute_posteriors(self.model, {"local_hmi": 1})
        for prob in posteriors.values():
            self.assertGreaterEqual(prob, 0.0)
            self.assertLessEqual(prob, 1.0)


if __name__ == "__main__":
    unittest.main()

