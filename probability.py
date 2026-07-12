"""
probability.py  (PHASE 3A)

Intrinsic base rate per node. Reads only from `assets`, independent of the
graph -- deliberately kept separate from cpt_generator.py (3B), since this
step doesn't need to know about parents, edges, or weights at all.
"""

from config import M_EXPOSURE, M_PATCH, R_PHISHING, M_PRIVILEGE, P_BASE_CAP


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
    m_exposure = M_EXPOSURE[attrs["exposed"]]
    m_patch = M_PATCH[attrs["patched"]]
    # cvss_type is on a 0-10 scale; normalize to 0-1 before scaling
    return (attrs["cvss_type"] / 10.0) * m_exposure * m_patch


def _human_base_prob(attrs: dict) -> float:
    r = R_PHISHING[attrs["role"]]
    a = attrs["awareness"]
    m_priv = M_PRIVILEGE[attrs["privilege"]]
    return r * (1 - a) * m_priv


def _physical_base_prob(attrs: dict) -> float:
    """
    Physical equipment/process nodes (pumps, valves, the process itself) have
    no CVSS score and no phishing profile -- there's no meaningful formula
    for "how likely is a pump to spontaneously get hacked." Their compromise
    probability should come almost entirely from noisy-OR over their parents
    (e.g. sensors/actuators), so we require an explicit low baseline instead
    of guessing one. Defaults to 0.0 (no intrinsic vulnerability) if omitted.
    """
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