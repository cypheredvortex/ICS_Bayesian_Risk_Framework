"""
probability.py  (PHASE 3A)

Intrinsic base rate per node. Reads only from `assets`, independent of the
graph -- deliberately kept separate from cpt_generator.py (3B).

FIX APPLIED: cvss_weight was previously applied as an EXPONENT on
(cvss / 10), a value always in [0, 1]. Raising the exponent on a
sub-1 base pushes the result TOWARD zero, so dragging the "CVSS weight"
slider up actually shrank CVSS's influence -- the opposite of what a
"weight" implies. It's now a direct linear multiplier instead:
weight=1.0 reproduces the original default behavior exactly
((cvss/10) * 1.0 == (cvss/10) ** 1.0), weight=0 removes CVSS's
contribution, and weight=2.0 doubles it -- all in the intuitive
direction. exposure_weight and patch_weight are left as exponents:
their underlying multiplier tables (M_EXPOSURE, M_PATCH) contain values
both above and below 1 depending on the boolean state, so an exponent
correctly amplifies deviation from neutral (1.0) in both directions --
that part already worked as intended.
"""

from config import (
    M_EXPOSURE,
    M_PATCH,
    M_PRIVILEGE,
    P_BASE_CAP,
    R_PHISHING,
    get_cvss_weight,
    get_exposure_weight,
    get_patch_weight,
)


def base_prob(node_id: str, attrs: dict) -> float:
    if attrs["kind"] == "device":
        p = _device_base_prob(attrs)
    elif attrs["kind"] == "human":
        p = _human_base_prob(attrs)
    elif attrs["kind"] == "physical":
        p = _physical_base_prob(attrs)
    else:
        raise ValueError(f"Unknown kind for node {node_id}: {attrs['kind']!r}")

    return min(p, P_BASE_CAP)


def _device_base_prob(attrs: dict) -> float:
    cvss = float(attrs["cvss_type"])
    # Linear multiplier: weight=1.0 matches the original (cvss/10)**1.0
    # behavior exactly; weight=0 removes CVSS entirely; weight=2.0 doubles
    # its contribution. Increasing the slider now increases influence.
    cvss_component = (cvss / 10.0) * get_cvss_weight()
    m_exposure = M_EXPOSURE[attrs["exposed"]] ** get_exposure_weight()
    m_patch = M_PATCH[attrs["patched"]] ** get_patch_weight()
    return cvss_component * m_exposure * m_patch


def _human_base_prob(attrs: dict) -> float:
    r = R_PHISHING[attrs["role"]]
    a = attrs["awareness"]
    m_priv = M_PRIVILEGE[attrs["privilege"]]
    return r * (1 - a) * m_priv


def _physical_base_prob(attrs: dict) -> float:
    return attrs.get("p_base_override", 0.0)


def compute_base_probs(assets: dict) -> dict:
    """assets: {node_id: attrs} -> {node_id: P_base}"""
    return {node_id: base_prob(node_id, attrs) for node_id, attrs in assets.items()}


if __name__ == "__main__":
    from assets import load_topology

    assets, _ = load_topology("data/swat_example.json")
    base_probs = compute_base_probs(assets)

    print("Base probabilities:")
    for nid, p in base_probs.items():
        print(f"  {nid}: {p:.3f}")