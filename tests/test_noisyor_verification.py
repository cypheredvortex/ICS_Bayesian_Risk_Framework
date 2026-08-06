import itertools
from pgmpy.models import DiscreteBayesianNetwork as BayesianNetwork
from pgmpy.inference import VariableElimination

from backend.cpt_generator import noisy_or_cpt, parameterize
from backend.probability import compute_base_probs


def test_noisyor_extreme_weights_and_leak():
    # Single parent network
    edges = [("P", "C")]
    model = BayesianNetwork(edges)
    # extreme weight: parent alone always causes child
    weights = {("P", "C"): 1.0}
    assets = {"P": {"kind": "device", "cvss_type": "5.0", "exposed": False, "patched": True},
              "C": {"kind": "device", "cvss_type": "2.0", "exposed": False, "patched": True}}
    base_probs = compute_base_probs(assets)
    cpd = noisy_or_cpt("C", model, weights, base_probs)
    # P(C=1 | P=1) should be 1 (weight=1)
    p_given_parent = float(cpd.get_value(**{"C": 1, "P": 1}))
    assert p_given_parent == 1.0

    # zero weight: parent has no effect
    weights = {("P", "C"): 0.0}
    cpd = noisy_or_cpt("C", model, weights, base_probs)
    p_given_parent = float(cpd.get_value(**{"C": 1, "P": 1}))
    p_given_none = float(cpd.get_value(**{"C": 1, "P": 0}))
    assert abs(p_given_parent - p_given_none) < 1e-12


def test_noisyor_monotonicity_multiple_parents():
    edges = [("A", "X"), ("B", "X")]
    model = BayesianNetwork(edges)
    weights = {("A", "X"): 0.5, ("B", "X"): 0.3}
    assets = {
        "A": {"kind": "device", "cvss_type": "3.0", "exposed": False, "patched": True},
        "B": {"kind": "device", "cvss_type": "4.0", "exposed": False, "patched": True},
        "X": {"kind": "device", "cvss_type": "1.0", "exposed": False, "patched": True},
    }
    base_probs = compute_base_probs(assets)
    cpd = noisy_or_cpt("X", model, weights, base_probs)
    # monotonic: adding active parents should not decrease P(X=1)
    p00 = float(cpd.get_value(**{"X": 1, "A": 0, "B": 0}))
    p10 = float(cpd.get_value(**{"X": 1, "A": 1, "B": 0}))
    p01 = float(cpd.get_value(**{"X": 1, "A": 0, "B": 1}))
    p11 = float(cpd.get_value(**{"X": 1, "A": 1, "B": 1}))
    assert p10 >= p00
    assert p01 >= p00
    assert p11 >= max(p10, p01)


def test_inference_matches_analytic_single_parent():
    # Analytic posterior check for single parent
    edges = [("P", "C")]
    model = BayesianNetwork(edges)
    weights = {("P", "C"): 0.7}
    assets = {"P": {"kind": "device", "cvss_type": "4.0", "exposed": False, "patched": True},
              "C": {"kind": "device", "cvss_type": "2.0", "exposed": False, "patched": True}}
    base_probs = compute_base_probs(assets)
    model = parameterize(model, weights, base_probs)

    infer = VariableElimination(model)
    # prior parent prob
    p_parent = base_probs["P"]
    # likelihoods
    p_c_given_p = float(model.get_cpds("C").get_value(**{"C": 1, "P": 1}))
    p_c_given_notp = float(model.get_cpds("C").get_value(**{"C": 1, "P": 0}))
    # analytic posterior P(P=1 | C=1)
    numerator = p_c_given_p * p_parent
    denominator = p_c_given_p * p_parent + p_c_given_notp * (1 - p_parent)
    analytic = numerator / denominator

    result = infer.query(variables=["P"], evidence={"C": 1}, show_progress=False)
    posterior = float(result.get_value(**{"P": 1}))
    assert abs(analytic - posterior) < 1e-9
