"""
tests/test_attack_paths.py — Validation of attack path analysis.
"""

import pytest
from pgmpy.models import DiscreteBayesianNetwork as BayesianNetwork

from backend.attack_paths import (
    enumerate_attack_paths,
    compute_path_probability,
    get_entry_nodes,
    get_critical_assets,
    compute_counterfactual_impact,
)
from backend.cpt_generator import parameterize
from backend.inference import compute_posteriors


@pytest.fixture
def diamond_model():
    """
        A
       / \
      B   C
       \ /
        D
    """
    model = BayesianNetwork([("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")])
    edge_probs = {
        ("A", "B"): 0.6,
        ("A", "C"): 0.6,
        ("B", "D"): 0.7,
        ("C", "D"): 0.7,
    }
    base_probs = {"A": 0.2, "B": 0.1, "C": 0.1, "D": 0.1}
    parameterize(model, edge_probs, base_probs)
    return model


def test_get_entry_nodes(diamond_model):
    entries = get_entry_nodes(diamond_model, {})
    assert entries == ["A"]


def test_enumerate_attack_paths(diamond_model):
    paths = enumerate_attack_paths(diamond_model, "A", "D")
    assert len(paths) == 2
    assert ["A", "B", "D"] in paths
    assert ["A", "C", "D"] in paths


def test_path_probability_range(diamond_model):
    paths = enumerate_attack_paths(diamond_model, "A", "D")
    for path in paths:
        prob = compute_path_probability(diamond_model, path)
        assert 0.0 <= prob <= 1.0


def test_path_probability_vs_base(diamond_model):
    """Path probability with all path nodes=1 should be >= base posterior."""
    base = compute_posteriors(diamond_model, {})
    paths = enumerate_attack_paths(diamond_model, "A", "D")
    for path in paths:
        prob = compute_path_probability(diamond_model, path)
        assert prob >= base["D"]


def test_counterfactual_delta_positive(diamond_model):
    impacts = compute_counterfactual_impact(diamond_model, "D", {})
    assert "A" in impacts
    assert impacts["A"]["delta"] >= 0
    assert impacts["A"]["counterfactual_probability"] >= impacts["A"]["base_probability"]