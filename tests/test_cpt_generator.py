"""Tests for the CPT generator (noisy-OR) module."""

import pytest
from pgmpy.models import DiscreteBayesianNetwork as BayesianNetwork

from backend.cpt_generator import (
    noisy_or_cpt,
    parameterize,
    cpts_to_dict,
)
from backend.probability import compute_base_probs


class TestNoisyOrCPT:
    """Single node CPT generation."""

    @pytest.fixture
    def model_and_weights(self) -> tuple:
        """Build a simple triangle: A -> B -> C with A -> C."""
        edges = [("A", "B"), ("B", "C"), ("A", "C")]
        model = BayesianNetwork(edges)
        weights = {("A", "B"): 0.7, ("B", "C"): 0.6, ("A", "C"): 0.5}
        return model, weights

    @pytest.fixture
    def assets(self) -> dict:
        return {
            "A": {"kind": "device", "cvss_type": "5.0", "exposed": False, "patched": True},
            "B": {"kind": "device", "cvss_type": "3.0", "exposed": False, "patched": True},
            "C": {"kind": "device", "cvss_type": "7.0", "exposed": False, "patched": True},
        }

    def test_root_node_has_no_parents(self, model_and_weights, assets) -> None:
        model, weights = model_and_weights
        base_probs = compute_base_probs(assets)
        cpd = noisy_or_cpt("A", model, weights, base_probs)
        parents = model.get_parents("A")
        assert len(parents) == 0
        # Root CPT: P(compromised) = base_prob
        p1 = cpd.get_value(**{"A": 1})
        assert p1 == pytest.approx(base_probs["A"], abs=1e-6)

    def test_child_node_has_parents(self, model_and_weights, assets) -> None:
        model, weights = model_and_weights
        base_probs = compute_base_probs(assets)
        cpd = noisy_or_cpt("B", model, weights, base_probs)
        assert len(list(model.get_parents("B"))) == 1

    def test_all_parents_active_increases_probability(self, model_and_weights, assets) -> None:
        model, weights = model_and_weights
        base_probs = compute_base_probs(assets)
        cpd = noisy_or_cpt("C", model, weights, base_probs)
        # P(C=1 | A=1, B=1)
        both_active = cpd.get_value(**{"C": 1, "A": 1, "B": 1})
        # P(C=1 | A=0, B=0)
        none_active = cpd.get_value(**{"C": 1, "A": 0, "B": 0})
        assert both_active > none_active

    def test_probabilities_sum_to_one(self, model_and_weights, assets) -> None:
        model, weights = model_and_weights
        base_probs = compute_base_probs(assets)
        for node in ["A", "B", "C"]:
            cpd = noisy_or_cpt(node, model, weights, base_probs)
            # P(node=0) + P(node=1) should be 1 for any parent combination
            for parent_state in [(0,), (1,), (0, 0), (1, 0), (1, 1)]:
                pass  # Verify via model check instead
            model.add_cpds(cpd)
        assert model.check_model()


class TestParameterize:
    """Full model parameterization."""

    def test_all_nodes_get_cpds(self) -> None:
        edges = [("X", "Y"), ("Y", "Z")]
        model = BayesianNetwork(edges)
        weights = {("X", "Y"): 0.7, ("Y", "Z"): 0.6}
        assets = {
            "X": {"kind": "device", "cvss_type": "4.0", "exposed": False, "patched": True},
            "Y": {"kind": "device", "cvss_type": "5.0", "exposed": False, "patched": True},
            "Z": {"kind": "device", "cvss_type": "6.0", "exposed": False, "patched": True},
        }
        base_probs = compute_base_probs(assets)
        model = parameterize(model, weights, base_probs)
        assert model.check_model()

    def test_model_check_passes(self) -> None:
        edges = [("A", "B")]
        model = BayesianNetwork(edges)
        weights = {("A", "B"): 0.8}
        assets = {
            "A": {"kind": "device", "cvss_type": "2.0", "exposed": False, "patched": True},
            "B": {"kind": "device", "cvss_type": "6.0", "exposed": False, "patched": True},
        }
        base_probs = compute_base_probs(assets)
        model = parameterize(model, weights, base_probs)
        assert model.check_model()


class TestCptsToDict:
    """Serialization of CPTs to dict format."""

    def test_returns_all_nodes(self) -> None:
        edges = [("A", "B")]
        model = BayesianNetwork(edges)
        weights = {("A", "B"): 0.7}
        assets = {
            "A": {"kind": "device", "cvss_type": "3.0", "exposed": False, "patched": True},
            "B": {"kind": "device", "cvss_type": "5.0", "exposed": False, "patched": True},
        }
        base_probs = compute_base_probs(assets)
        model = parameterize(model, weights, base_probs)
        result = cpts_to_dict(model)
        assert set(result.keys()) == {"A", "B"}

    def test_root_node_has_no_parents(self) -> None:
        edges = [("A", "B")]
        model = BayesianNetwork(edges)
        weights = {("A", "B"): 0.7}
        assets = {
            "A": {"kind": "device", "cvss_type": "3.0", "exposed": False, "patched": True},
            "B": {"kind": "device", "cvss_type": "5.0", "exposed": False, "patched": True},
        }
        base_probs = compute_base_probs(assets)
        model = parameterize(model, weights, base_probs)
        result = cpts_to_dict(model)
        assert result["A"]["parents"] == []
        assert len(result["A"]["rows"]) == 1

    def test_child_node_has_correct_parent_list(self) -> None:
        edges = [("A", "B")]
        model = BayesianNetwork(edges)
        weights = {("A", "B"): 0.7}
        assets = {
            "A": {"kind": "device", "cvss_type": "3.0", "exposed": False, "patched": True},
            "B": {"kind": "device", "cvss_type": "5.0", "exposed": False, "patched": True},
        }
        base_probs = compute_base_probs(assets)
        model = parameterize(model, weights, base_probs)
        result = cpts_to_dict(model)
        assert result["B"]["parents"] == ["A"]
        assert len(result["B"]["rows"]) == 2  # 2 parent state combinations

    def test_probabilities_in_valid_range(self) -> None:
        edges = [("A", "B")]
        model = BayesianNetwork(edges)
        weights = {("A", "B"): 0.7}
        assets = {
            "A": {"kind": "device", "cvss_type": "3.0", "exposed": False, "patched": True},
            "B": {"kind": "device", "cvss_type": "5.0", "exposed": False, "patched": True},
        }
        base_probs = compute_base_probs(assets)
        model = parameterize(model, weights, base_probs)
        result = cpts_to_dict(model)
        for node_data in result.values():
            for row in node_data["rows"]:
                assert 0 <= row["p_compromised"] <= 1.0

