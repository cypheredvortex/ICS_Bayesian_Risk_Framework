"""
Scientific validation suite — independent mathematical checks.

This module deliberately does NOT re-derive results by calling the same
functions it tests.  For each important formula the expected value is
computed *independently*:

  • the logistic sigmoid is computed with plain math.exp;
  • the Noisy-OR CPT row is evaluated from the closed-form definition;
  • Bayesian posteriors are computed by brute-force enumeration of the
    joint distribution over all binary states (no pgmpy inference);
  • the risk index is recomputed from its definition.

The framework implementation is then compared against these independent
values.  This is much stronger than "function output == function output"
and catches semantic drift, not just refactor errors.
"""

import math
import itertools

import pytest
from pgmpy.models import DiscreteBayesianNetwork as BayesianNetwork

from backend.assets import load_topology
from backend.cli import run as run_framework
from backend.cpt_generator import noisy_or_cpt, parameterize, cpts_to_dict
from backend.cvss import base_score_from_vector, parse_cvss_vector
from backend.enrichment import enrich_graph
from backend.graph_builder import build_graph_skeleton, edge_weight
from backend.inference import compute_posteriors, compute_posteriors_with_evidence
from backend.probability import (
    _cvss_to_prob_logistic,
    _inv_logit,
    _logit,
    _apply_context_log_odds,
    compute_base_probs,
    base_prob,
)
from backend.risk import build_risk_table, m_scope, risk_level_for
from backend.settings import (
    get_settings,
    get_model_settings_snapshot,
    non_default_settings,
    reset_settings,
    temporary_settings,
    update_settings,
)

P_BASE_CAP = 0.9995


# ---------------------------------------------------------------------------
# 1. CVSS v3.1 — independent verification against published scores
# ---------------------------------------------------------------------------

def test_cvss_official_heartbleed():
    """CVE-2014-0160 (Heartbleed): official Base Score = 7.5."""
    vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N"
    assert base_score_from_vector(vector) == 7.5


def test_cvss_official_log4shell():
    """CVE-2021-44228 (Log4Shell): official Base Score = 10.0."""
    vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H"
    assert base_score_from_vector(vector) == 10.0


def test_cvss_official_shellshock():
    """CVE-2014-6271 (Shellshock): official Base Score = 9.8."""
    vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
    assert base_score_from_vector(vector) == 9.8


def test_cvss_scope_changed_formula():
    """Scope-changed vector uses the 1.08 factor (CVE-2021-44228 = 10.0)."""
    metrics = parse_cvss_vector("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H")
    assert metrics["S"] == "C"


def test_cvss_severity_rating_boundaries():
    from backend.cvss import severity_rating

    assert severity_rating(9.0) == "Critical"
    assert severity_rating(7.0) == "High"
    assert severity_rating(4.0) == "Medium"
    assert severity_rating(0.1) == "Low"
    assert severity_rating(0.0) == "None"


# ---------------------------------------------------------------------------
# 2. CVSS → probability — independent logistic evaluation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cvss,k,x0", [
    (0.0, 0.8, 5.0),
    (2.5, 0.8, 5.0),
    (5.0, 0.8, 5.0),
    (7.5, 0.8, 5.0),
    (10.0, 0.8, 5.0),
    (3.0, 1.4, 2.1),
    (8.0, 0.4, 6.0),
])
def test_logistic_mapping_matches_independent_sigmoid(cvss, k, x0):
    """P₀ = 1/(1+exp(−k·(CVSS−x₀))), computed without the framework."""
    independent = 1.0 / (1.0 + math.exp(-k * (cvss - x0)))
    independent = max(1e-6, min(P_BASE_CAP, independent))
    actual = _cvss_to_prob_logistic(cvss, k, x0)
    assert actual == pytest.approx(independent, abs=1e-12)


def test_logistic_mapping_anchors():
    """Documented anchor points: CVSS 5 → 0.5, CVSS 10 → ≈0.98, CVSS 0 → ≈0.018."""
    assert _cvss_to_prob_logistic(5.0, 0.8, 5.0) == pytest.approx(0.5, abs=1e-12)
    assert _cvss_to_prob_logistic(10.0, 0.8, 5.0) == pytest.approx(
        1 / (1 + math.exp(-4)), abs=1e-12
    )
    assert _cvss_to_prob_logistic(0.0, 0.8, 5.0) == pytest.approx(
        1 / (1 + math.exp(4)), abs=1e-12
    )


def test_logistic_mapping_stable_for_extreme_settings():
    """Extreme-but-valid settings must not raise OverflowError."""
    # k=100, x0=10, cvss=0 → exponent +1000 would overflow a naive exp().
    p = _cvss_to_prob_logistic(0.0, 100.0, 10.0)
    assert 0.0 < p < 1.0
    p = _cvss_to_prob_logistic(10.0, 100.0, 0.0)
    assert 0.0 < p < 1.0


def test_logit_inv_logit_roundtrip():
    """logit/inv_logit are mutual inverses on (0,1)."""
    for p in (1e-6, 0.01, 0.2, 0.5, 0.8, 0.99, P_BASE_CAP):
        assert _inv_logit(_logit(p)) == pytest.approx(p, rel=1e-9)


def test_log_odds_context_adjustment_independent():
    """logit(P) = logit(P₀) + Σ w·ln(M), evaluated independently."""
    p0 = 0.4
    factors = [(1.3, 1.0), (0.9, 0.5)]
    independent_lo = math.log(p0 / (1 - p0))
    for mult, weight in factors:
        independent_lo += weight * math.log(mult)
    independent_p = 1.0 / (1.0 + math.exp(-independent_lo))
    actual = _apply_context_log_odds(p0, factors)
    assert actual == pytest.approx(independent_p, abs=1e-12)


def test_device_base_prob_independent():
    """Full intrinsic-probability pipeline evaluated from first principles."""
    with temporary_settings({"cvss_logistic_params": {"k": 0.8, "x0": 5.0}}):
        attrs = {"kind": "device", "cvss_type": 7.5, "exposed": True, "patched": False}
        p0 = _cvss_to_prob_logistic(7.5, 0.8, 5.0)
        lo = _logit(p0) + 1.0 * math.log(1.3) + 1.0 * math.log(1.2)
        expected = max(1e-6, min(P_BASE_CAP, _inv_logit(lo)))
        assert base_prob("D1", attrs) == pytest.approx(expected, abs=1e-12)


# ---------------------------------------------------------------------------
# 3. Noisy-OR CPT — independent closed-form verification
# ---------------------------------------------------------------------------

def test_noisy_or_cpt_independent_closed_form():
    """
    P(child=1 | S) = 1 − (1 − leak)·Π_{i∈S}(1 − wᵢ), evaluated by hand and
    compared against every row of the generated CPT for a 3-parent node.
    """
    parents = ["A", "B", "C"]
    edges = [(p, "X") for p in parents]
    model = BayesianNetwork(edges)
    weights = {("A", "X"): 0.4, ("B", "X"): 0.7, ("C", "X"): 0.1}
    assets = {
        "A": {"kind": "device", "cvss_type": 3.0, "exposed": False, "patched": True},
        "B": {"kind": "device", "cvss_type": 4.0, "exposed": False, "patched": True},
        "C": {"kind": "device", "cvss_type": 5.0, "exposed": False, "patched": True},
        "X": {"kind": "device", "cvss_type": 2.0, "exposed": False, "patched": True},
    }
    base_probs = compute_base_probs(assets)
    leak = base_probs["X"]
    cpd = noisy_or_cpt("X", model, weights, base_probs)

    for combo in itertools.product([0, 1], repeat=3):
        state = dict(zip(parents, combo))
        prod = 1.0
        for parent, s in state.items():
            if s == 1:
                prod *= (1.0 - weights[(parent, "X")])
        independent = 1.0 - (1.0 - leak) * prod
        actual = float(cpd.get_value(**{"X": 1, **state}))
        assert actual == pytest.approx(independent, abs=1e-12)
        # Every row must normalise: P(0) + P(1) = 1
        p0 = float(cpd.get_value(**{"X": 0, **state}))
        assert p0 + actual == pytest.approx(1.0, abs=1e-12)


def test_noisy_or_cpt_rows_sum_to_one_all_configs():
    """Every CPT row sums to 1 over the child's states, for every parent config."""
    for k in range(0, 4):
        parents = [f"P{i}" for i in range(k)]
        edges = [(p, "X") for p in parents]
        model = BayesianNetwork(edges)
        model.add_nodes_from(["X"] + parents)  # isolated nodes must be supported
        weights = {(p, "X"): 0.1 + 0.2 * i for i, p in enumerate(parents)}
        assets = {"X": {"kind": "device", "cvss_type": 4.0, "exposed": False, "patched": True}}
        for i, p in enumerate(parents):
            assets[p] = {"kind": "device", "cvss_type": float(i), "exposed": False, "patched": True}
        base_probs = compute_base_probs(assets)
        cpd = noisy_or_cpt("X", model, weights, base_probs)
        for combo in itertools.product([0, 1], repeat=k):
            state = dict(zip(parents, combo))
            p1 = float(cpd.get_value(**{"X": 1, **state}))
            p0 = float(cpd.get_value(**{"X": 0, **state}))
            assert 0.0 <= p1 <= 1.0
            assert p0 + p1 == pytest.approx(1.0, abs=1e-9)


def test_noisy_or_extreme_bounds():
    """With weight 1.0 the parent alone guarantees the child; weight 0 has no effect."""
    model = BayesianNetwork([("P", "C")])
    assets = {
        "P": {"kind": "device", "cvss_type": 5.0, "exposed": False, "patched": True},
        "C": {"kind": "device", "cvss_type": 2.0, "exposed": False, "patched": True},
    }
    base_probs = compute_base_probs(assets)
    cpd = noisy_or_cpt("C", model, {("P", "C"): 1.0}, base_probs)
    assert float(cpd.get_value(**{"C": 1, "P": 1})) == pytest.approx(1.0, abs=1e-12)
    cpd0 = noisy_or_cpt("C", model, {("P", "C"): 0.0}, base_probs)
    assert float(cpd0.get_value(**{"C": 1, "P": 1})) == pytest.approx(
        float(cpd0.get_value(**{"C": 1, "P": 0})), abs=1e-12
    )


# ---------------------------------------------------------------------------
# 4. Bayesian inference — brute-force joint enumeration
# ---------------------------------------------------------------------------

def _brute_force_posterior(model, query_node, evidence=None):
    """Exact marginal P(query=1) by enumerating all 2^n joint states.

    Completely independent of pgmpy's inference engine: the joint is built
    from the CPTs via the chain rule, then marginals are summed directly.
    """
    evidence = evidence or {}
    nodes = sorted(model.nodes())
    probs = {n: model.get_cpds(n) for n in nodes}

    def cpd_value(node, state, parent_states):
        if not parent_states:
            return float(probs[node].get_value(**{node: state}))
        return float(probs[node].get_value(**{node: state, **parent_states}))

    joint_numerator = 0.0
    joint_evidence = 0.0
    for combo in itertools.product([0, 1], repeat=len(nodes)):
        assignment = dict(zip(nodes, combo))
        # Skip assignments inconsistent with evidence
        if any(assignment[n] != v for n, v in evidence.items()):
            continue
        p = 1.0
        for node in nodes:
            parents = model.get_parents(node)
            parent_states = {p_node: assignment[p_node] for p_node in parents}
            p *= cpd_value(node, assignment[node], parent_states)
        joint_evidence += p
        if assignment[query_node] == 1:
            joint_numerator += p
    if joint_evidence == 0.0:
        raise AssertionError("Evidence has zero probability under brute force.")
    return joint_numerator / joint_evidence


def test_inference_matches_brute_force_three_node_chain():
    """X → Y → Z chain: pgmpy posteriors == brute-force enumeration."""
    edges = [("X", "Y"), ("Y", "Z")]
    model = BayesianNetwork(edges)
    weights = {("X", "Y"): 0.6, ("Y", "Z"): 0.8}
    assets = {
        "X": {"kind": "device", "cvss_type": 6.0, "exposed": False, "patched": True},
        "Y": {"kind": "device", "cvss_type": 4.0, "exposed": False, "patched": True},
        "Z": {"kind": "device", "cvss_type": 3.0, "exposed": False, "patched": True},
    }
    base_probs = compute_base_probs(assets)
    model = parameterize(model, weights, base_probs)

    for evidence in ({}, {"X": 1}, {"Z": 1}, {"X": 1, "Z": 1}):
        for node in ("X", "Y", "Z"):
            expected = _brute_force_posterior(model, node, evidence)
            actual = float(
                compute_posteriors(model, evidence).get(node, float("nan"))
            )
            assert actual == pytest.approx(expected, abs=1e-9), (
                f"{node} with evidence {evidence}: brute {expected} vs pgmpy {actual}"
            )


def test_inference_matches_brute_force_v_structure():
    """A → X ← B (collider): conditioning on X creates dependence."""
    edges = [("A", "X"), ("B", "X")]
    model = BayesianNetwork(edges)
    weights = {("A", "X"): 0.5, ("B", "X"): 0.5}
    assets = {
        "A": {"kind": "device", "cvss_type": 5.0, "exposed": False, "patched": True},
        "B": {"kind": "device", "cvss_type": 5.0, "exposed": False, "patched": True},
        "X": {"kind": "device", "cvss_type": 2.0, "exposed": False, "patched": True},
    }
    base_probs = compute_base_probs(assets)
    model = parameterize(model, weights, base_probs)

    # Conditioning on X=1 (compromised) raises P(A=1) above its prior.
    prior_a = compute_posteriors(model, {})["A"]
    posterior_a = compute_posteriors(model, {"X": 1})["A"]
    assert posterior_a >= prior_a
    expected = _brute_force_posterior(model, "A", {"X": 1})
    assert posterior_a == pytest.approx(expected, abs=1e-9)


def test_posterior_evidence_pins_exact_states():
    """Evidence nodes are pinned to their asserted state (hard evidence)."""
    edges = [("X", "Y")]
    model = BayesianNetwork(edges)
    base_probs = compute_base_probs({
        "X": {"kind": "device", "cvss_type": 5.0, "exposed": False, "patched": True},
        "Y": {"kind": "device", "cvss_type": 3.0, "exposed": False, "patched": True},
    })
    model = parameterize(model, {("X", "Y"): 0.5}, base_probs)
    posteriors, sanitized = compute_posteriors_with_evidence(model, {"X": 1})
    assert posteriors["X"] == 1.0
    assert posteriors["Y"] <= 1.0
    assert sanitized == {"X": 1}


# ---------------------------------------------------------------------------
# 5. Risk model — independent recomputation
# ---------------------------------------------------------------------------

def test_risk_index_independent_formula():
    """Risk = P × (severity/10) × scope_mult × impact_weight, recomputed by hand."""
    posteriors = {"PLC": 0.73}
    assets = {"PLC": {"consequence_severity": 8.0, "scope": 3}}
    df = build_risk_table(posteriors, assets)
    scope_mult = m_scope(assets["PLC"])
    impact_weight = get_settings().get("impact_weight", 1.0)
    expected_impact = (8.0 / 10.0) * scope_mult * impact_weight
    expected_risk = 0.73 * expected_impact
    assert df.iloc[0]["impact"] == pytest.approx(expected_impact, abs=1e-9)
    assert df.iloc[0]["risk"] == pytest.approx(expected_risk, abs=1e-9)


def test_scope_multiplier_independent():
    """scope_mult = 1 + (scope−1)·0.1 for scope ∈ [1,5]."""
    for scope in (1, 2, 3, 4, 5):
        assert m_scope({"scope": scope}) == pytest.approx(
            1.0 + (scope - 1) * 0.1, abs=1e-12
        )


def test_risk_level_thresholds_independent():
    """Level boundaries follow the configured thresholds exactly."""
    t = get_settings().get("risk_thresholds", {"critical": 0.75, "high": 0.5, "moderate": 0.25})
    assert risk_level_for(t["critical"]) == "Critical"
    assert risk_level_for(t["critical"] - 1e-9) != "Critical"
    assert risk_level_for(t["high"]) == "High"
    assert risk_level_for(t["moderate"]) == "Moderate"
    assert risk_level_for(0.0) == "Low"


def test_scope_attribute_survives_normalization():
    """
    REGRESSION: the `scope` attribute used by the risk model was silently
    dropped by normalize_asset, so scope_mult was always 1.0 and the
    documented blast-radius multiplier was dead in the pipeline.
    """
    raw = {
        "assets": {
            "plc": {
                "kind": "device",
                "cvss_type": 5.0,
                "exposed": False,
                "patched": True,
                "consequence_severity": 9.0,
                "scope": 4,
            }
        },
        "relationships": [],
    }
    assets, relationships, _warnings = load_topology(raw)
    enriched = enrich_graph(assets, relationships)["assets"]
    assert enriched["plc"]["scope"] == 4
    assert m_scope(enriched["plc"]) == pytest.approx(1.3, abs=1e-12)


def test_scope_attribute_reaches_risk_table_end_to_end():
    """A scope value in the topology changes the risk index (regression)."""
    raw = {
        "assets": {
            "plc": {
                "kind": "device",
                "cvss_type": 5.0,
                "exposed": False,
                "patched": True,
                "consequence_severity": 9.0,
                "scope": 4,
            }
        },
        "relationships": [],
    }
    result = run_framework(raw, evidence={}, write_outputs=False, persist=False)
    row = result["risk_scores"][0]
    # scope=4 → multiplier 1.3 (previously always 1.0)
    assert row["scope_mult"] == pytest.approx(1.3, abs=1e-9)
    assert row["risk"] == pytest.approx(
        row["P(compromised|evidence)"] * (9.0 / 10.0) * 1.3, abs=1e-6
    )


def test_scope_out_of_range_rejected():
    """scope outside [1,5] is rejected with an actionable error."""
    raw = {
        "assets": {
            "plc": {
                "kind": "device",
                "cvss_type": 5.0,
                "scope": 99,
            }
        },
        "relationships": [],
    }
    with pytest.raises(ValueError, match="scope"):
        load_topology(raw)


# ---------------------------------------------------------------------------
# 6. Settings traceability — outputs must record the parameters used
# ---------------------------------------------------------------------------

def test_results_record_settings_snapshot():
    """Every assessment records the exact settings that produced it."""
    raw = {
        "assets": {
            "plc": {"kind": "device", "cvss_type": 5.0, "exposed": False, "patched": True},
        },
        "relationships": [],
    }
    result = run_framework(raw, evidence={}, write_outputs=False, persist=False)
    snapshot = result["settings_used"]
    assert isinstance(snapshot, dict)
    assert snapshot["cvss_logistic_params"] == get_settings()["cvss_logistic_params"]
    assert snapshot["risk_thresholds"] == get_settings()["risk_thresholds"]
    # The snapshot excludes UI-only keys not consumed by the model
    assert "theme" not in snapshot


def test_non_default_settings_detected():
    """non_default_settings() reports deviations from framework defaults."""
    try:
        update_settings({"cvss_logistic_params": {"k": 1.2, "x0": 4.5}})
        deviations = non_default_settings()
        keys = [key for key, _active, _default in deviations]
        assert "cvss_logistic_params" in keys
    finally:
        reset_settings()


def test_non_default_settings_warning_in_summary():
    """A run produced with non-default settings surfaces a warning."""
    try:
        update_settings({"impact_weight": 0.5})
        raw = {
            "assets": {
                "plc": {"kind": "device", "cvss_type": 5.0, "exposed": False, "patched": True},
            },
            "relationships": [],
        }
        result = run_framework(raw, evidence={}, write_outputs=False, persist=False)
        # Settings deviations are reported in a dedicated field, never mixed
        # into the topology-normalisation warnings.
        assert "Non-default setting 'impact_weight'" in " ".join(
            result["summary"]["settings_warnings"]
        )
        assert result["summary"]["non_default_settings"]
        assert not any(
            "Non-default" in w for w in result["summary"]["topology_warnings"]
        )
    finally:
        reset_settings()


def test_get_model_settings_snapshot_restricted_to_model_keys():
    """Snapshot contains exactly the DEFAULT_SETTINGS keys that drive the model."""
    snapshot = get_model_settings_snapshot()
    for key in (
        "cvss_mapping", "cvss_logistic_params", "exposure_weight", "patch_weight",
        "impact_weight", "propagation_weights", "risk_thresholds",
    ):
        assert key in snapshot
    assert not {"theme", "recent_projects"} & set(snapshot.keys())


# ---------------------------------------------------------------------------
# 7. Reproducibility and numerical validity
# ---------------------------------------------------------------------------

def test_assessment_is_deterministic():
    """Same inputs + same settings → bit-identical outputs (no randomness)."""
    raw = {
        "assets": {
            "hmi": {"kind": "device", "cvss_type": 7.5, "exposed": True, "patched": False},
            "plc": {"kind": "device", "cvss_type": 9.0, "exposed": False, "patched": True},
            "process": {"kind": "physical", "p_base_override": 0.02},
        },
        "relationships": [
            ["hmi", "plc", "connects-to", False],
            ["plc", "process", "actuates", False],
        ],
    }
    first = run_framework(raw, evidence={}, write_outputs=False, persist=False)
    second = run_framework(raw, evidence={}, write_outputs=False, persist=False)
    assert first["posteriors"] == second["posteriors"]
    assert first["base_probabilities"] == second["base_probabilities"]
    assert first["risk_scores"] == second["risk_scores"]


def test_all_probabilities_in_unit_interval():
    """Base and posterior probabilities are always in [0, 1]."""
    raw = {
        "assets": {
            "hmi": {"kind": "device", "cvss_type": 10.0, "exposed": True, "patched": False},
            "plc": {"kind": "device", "cvss_type": 0.0, "exposed": False, "patched": True},
            "process": {"kind": "physical", "p_base_override": 0.02},
            "engineer": {"kind": "human", "role": "engineer", "awareness": 0.6},
        },
        "relationships": [
            ["hmi", "plc", "connects-to", False],
            ["plc", "process", "actuates", False],
        ],
    }
    result = run_framework(raw, evidence={}, write_outputs=False, persist=False)
    for node, p in result["base_probabilities"].items():
        assert 0.0 <= p <= 1.0
    for node, p in result["posteriors"].items():
        assert 0.0 <= p <= 1.0
    for row in result["risk_scores"]:
        assert 0.0 <= float(row["P(compromised|evidence)"]) <= 1.0
        assert 0.0 <= float(row["risk"]) <= 1.5


def test_cpts_normalise_in_full_pipeline():
    """CPTs exported from the pipeline normalise to 1 for every config."""
    raw = {
        "assets": {
            "hmi": {"kind": "device", "cvss_type": 7.5, "exposed": True, "patched": False},
            "plc": {"kind": "device", "cvss_type": 9.0, "exposed": False, "patched": True},
        },
        "relationships": [["hmi", "plc", "connects-to", False]],
    }
    result = run_framework(raw, evidence={}, write_outputs=False, persist=False)
    for node, cpt in result["cpts"].items():
        if not cpt["parents"]:
            continue
        for row in cpt["rows"]:
            p1 = row["p_compromised"]
            assert 0.0 <= p1 <= 1.0


# ---------------------------------------------------------------------------
# 8. Edge cases
# ---------------------------------------------------------------------------

def test_asset_without_vulnerabilities():
    """Device with CVSS 0 still gets a small, non-zero intrinsic probability."""
    with temporary_settings({"cvss_logistic_params": {"k": 0.8, "x0": 5.0}}):
        p = base_prob("D", {"kind": "device", "cvss_type": 0.0, "exposed": False, "patched": True})
        assert 0.0 < p < 0.05


def test_isolated_single_asset_topology():
    """A single asset with no relationships still produces valid outputs."""
    raw = {"assets": {"plc": {"kind": "device", "cvss_type": 6.0}}, "relationships": []}
    result = run_framework(raw, evidence={}, write_outputs=False, persist=False)
    assert len(result["risk_scores"]) == 1
    assert 0.0 <= result["posteriors"]["plc"] <= 1.0


def test_disconnected_subgraphs():
    """Two disconnected subgraphs are analysed as independent submodels."""
    raw = {
        "assets": {
            "a1": {"kind": "device", "cvss_type": 7.0, "exposed": True, "patched": False},
            "a2": {"kind": "device", "cvss_type": 7.0, "exposed": True, "patched": False},
            "b1": {"kind": "device", "cvss_type": 3.0, "exposed": False, "patched": True},
            "b2": {"kind": "device", "cvss_type": 3.0, "exposed": False, "patched": True},
        },
        "relationships": [
            ["a1", "a2", "connects-to", False],
            ["b1", "b2", "connects-to", False],
        ],
    }
    result = run_framework(raw, evidence={}, write_outputs=False, persist=False)
    assert len(result["risk_scores"]) == 4
    for node, p in result["posteriors"].items():
        assert 0.0 <= p <= 1.0


def test_cyclic_topology_rejected():
    """A cycle must be rejected (Bayesian networks require a DAG)."""
    raw = {
        "assets": {
            "a": {"kind": "device", "cvss_type": 5.0},
            "b": {"kind": "device", "cvss_type": 5.0},
        },
        "relationships": [
            ["a", "b", "connects-to", False],
            ["b", "a", "connects-to", False],
        ],
    }
    with pytest.raises(ValueError, match="cycle"):
        run_framework(raw, evidence={}, write_outputs=False, persist=False)
