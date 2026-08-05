"""
probability.py - Intrinsic base rate per node.
"""

from backend.config import (
    M_EXPOSURE, M_PATCH, M_PRIVILEGE, P_BASE_CAP, R_PHISHING,
    get_cvss_weight, get_exposure_weight, get_patch_weight,
)
from backend.settings import get_settings
import math


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
    # Map CVSS to a base probability. Default mapping is linear (cvss/10),
    # but users may configure a logistic mapping via settings for more
    # realistic calibration. See `get_settings().cvss_mapping` for options.
    cvss = float(attrs.get("cvss_type", 0.0))
    def _cvss_to_prob(cvss_val: float) -> float:
        settings = get_settings()
        mapping = settings.get("cvss_mapping", "linear")
        weight = get_cvss_weight()
        if mapping == "logistic":
            # logistic mapping parameters: k (steepness) and x0 (midpoint)
            params = settings.get("cvss_logistic_params", {})
            k = float(params.get("k", 1.0))
            x0 = float(params.get("x0", 5.0))
            # map cvss in [0,10] to probability via logistic then scale by weight
            raw = 1.0 / (1.0 + math.exp(-k * (cvss_val - x0)))
            return min(max(raw * weight, 0.0), 1.0)
        # default: linear
        return min(max((cvss_val / 10.0) * weight, 0.0), 1.0)

    p0 = _cvss_to_prob(cvss)

    # If p0 is 0 or 1, handle edge cases directly
    if p0 <= 0.0:
        return 0.0
    if p0 >= 1.0:
        return min(p0, P_BASE_CAP)

    # Convert to odds, apply multiplicative context factors, convert back
    odds = p0 / (1.0 - p0)
    m_exposure = M_EXPOSURE[attrs["exposed"]] ** get_exposure_weight()
    m_patch = M_PATCH[attrs["patched"]] ** get_patch_weight()
    adjusted_odds = odds * m_exposure * m_patch
    p = adjusted_odds / (1.0 + adjusted_odds)
    return min(p, P_BASE_CAP)


def _human_base_prob(attrs: dict) -> float:
    r = R_PHISHING.get(attrs.get("role"), R_PHISHING.get("operator"))
    a = float(attrs.get("awareness", 0.0))
    m_priv = M_PRIVILEGE.get(attrs.get("privilege"), 1.0)

    p0 = float(r) * (1.0 - a)
    if p0 <= 0.0:
        return 0.0
    if p0 >= 1.0:
        return min(p0, P_BASE_CAP)

    odds = p0 / (1.0 - p0)
    adjusted_odds = odds * m_priv
    p = adjusted_odds / (1.0 + adjusted_odds)
    return min(p, P_BASE_CAP)


def _physical_base_prob(attrs: dict) -> float:
    return attrs.get("p_base_override", 0.0)


def compute_base_probs(assets: dict) -> dict:
    return {node_id: base_prob(node_id, attrs) for node_id, attrs in assets.items()}
