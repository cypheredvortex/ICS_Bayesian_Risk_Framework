"""
tests/test_attack_paths.py - Validation of attack path analysis.

These tests exercise the actual `compute_attack_paths` entry point (the
previous test module referenced functions that were removed during an
earlier refactor and therefore never ran).
"""

import pytest

from backend.attack_paths import compute_attack_paths

# Diamond model: A -> B -> D and A -> C -> D
RELATIONSHIPS = [
    ("A", "B", "connects-to", False, {}),
    ("A", "C", "connects-to", False, {}),
    ("B", "D", "connects-to", False, {}),
    ("C", "D", "connects-to", False, {}),
]

EDGE_WEIGHTS = {
    ("A", "B"): 0.6,
    ("A", "C"): 0.6,
    ("B", "D"): 0.7,
    ("C", "D"): 0.7,
}

# Only D carries consequence, so it is the sole attack-path target.
ASSETS = {
    "A": {"kind": "device", "consequence_severity": 5.0},
    "B": {"kind": "device", "consequence_severity": 0.0},
    "C": {"kind": "device", "consequence_severity": 0.0},
    "D": {"kind": "device", "consequence_severity": 9.0},
}

POSTERIORS = {"A": 0.9, "B": 0.7, "C": 0.7, "D": 0.6}


def _risk_rows():
    """Risk register rows consistent with the posteriors + severities."""
    rows = []
    for asset, attrs in ASSETS.items():
        severity = float(attrs["consequence_severity"])
        impact = severity / 10.0
        rows.append({
            "asset": asset,
            "risk": round(POSTERIORS[asset] * impact, 6),
            "P(compromised|evidence)": POSTERIORS[asset],
        })
    return rows


def test_paths_follow_dag_direction():
    """Every path must follow the causal DAG direction (parent -> child)."""
    paths = compute_attack_paths(
        RELATIONSHIPS, EDGE_WEIGHTS, {}, _risk_rows(), ASSETS, posteriors=POSTERIORS
    )
    assert paths, "expected at least one attack path"
    valid_edges = set(EDGE_WEIGHTS)
    for path in paths:
        for i in range(len(path["path"]) - 1):
            assert (path["path"][i], path["path"][i + 1]) in valid_edges, (
                f"path {path['path']} uses a non-DAG edge"
            )


def test_paths_start_at_entry_node():
    """With no evidence the entry node is the DAG root (A)."""
    paths = compute_attack_paths(
        RELATIONSHIPS, EDGE_WEIGHTS, {}, _risk_rows(), ASSETS, posteriors=POSTERIORS
    )
    for path in paths:
        assert path["path"][0] == "A"


def test_compromised_evidence_becomes_entry():
    """Marking C as compromised should make C the path source."""
    paths = compute_attack_paths(
        RELATIONSHIPS, EDGE_WEIGHTS, {"C": 1}, _risk_rows(), ASSETS, posteriors=POSTERIORS
    )
    assert paths
    for path in paths:
        assert path["path"][0] == "C"


def test_paths_reach_only_consequence_targets():
    """Only assets with non-zero consequence severity are path targets."""
    paths = compute_attack_paths(
        RELATIONSHIPS, EDGE_WEIGHTS, {}, _risk_rows(), ASSETS, posteriors=POSTERIORS
    )
    targets = {path["target"] for path in paths}
    assert targets == {"D"}


def test_paths_sorted_by_score_descending():
    paths = compute_attack_paths(
        RELATIONSHIPS, EDGE_WEIGHTS, {}, _risk_rows(), ASSETS, posteriors=POSTERIORS
    )
    scores = [path["score"] for path in paths]
    assert scores == sorted(scores, reverse=True)


def test_score_is_min_posterior_times_target_risk():
    """Default scoring: min posterior along path x target risk index."""
    paths = compute_attack_paths(
        RELATIONSHIPS, EDGE_WEIGHTS, {}, _risk_rows(), ASSETS, posteriors=POSTERIORS
    )
    target_risk = POSTERIORS["D"] * (9.0 / 10.0)  # 0.54
    for path in paths:
        min_post = min(POSTERIORS[n] for n in path["path"])
        assert path["path_probability"] == pytest.approx(min_post)
        assert path["score"] == pytest.approx(min_post * target_risk)


def test_max_paths_limit():
    paths = compute_attack_paths(
        RELATIONSHIPS, EDGE_WEIGHTS, {}, _risk_rows(), ASSETS,
        posteriors=POSTERIORS, max_paths=1,
    )
    assert len(paths) == 1


def test_no_evidence_no_posteriors_falls_back_to_edge_weights():
    """Without posteriors the path probability falls back to the geometric
    mean of edge weights (backward-compatible heuristic)."""
    paths = compute_attack_paths(RELATIONSHIPS, EDGE_WEIGHTS, {}, _risk_rows(), ASSETS)
    assert paths
    for path in paths:
        assert 0.0 <= path["path_probability"] <= 1.0


def test_empty_topology_returns_empty():
    paths = compute_attack_paths([], {}, {}, [], {}, posteriors={})
    assert paths == []


def test_weak_edges_are_pruned():
    """Edges below the minimum propagation threshold never appear."""
    weak_relationships = [("A", "D", "connects-to", False, {})]
    weak_weights = {("A", "D"): 0.01}
    paths = compute_attack_paths(
        weak_relationships, weak_weights, {}, _risk_rows(), ASSETS, posteriors=POSTERIORS
    )
    assert all(len(path["path"]) == 1 for path in paths) or not paths
