"""
probability.py — Intrinsic base compromise probability per node.

Methodology
-----------
1. CVSS-to-prior mapping
   CVSS Base Score is a *severity* metric (0–10), not a probability.
   Direct linear scaling P = CVSS/10 is statistically indefensible because
   it implies a CVSS-10 vulnerability guarantees compromise (P=1.0), which
   contradicts both empirical studies and Bayesian epistemology
   (FIRST, 2019; Spring et al., 2021).

   We instead use a calibrated logistic (sigmoid) mapping:

       P₀ = 1 / (1 + exp(−k·(CVSS − x₀)))

   with default k=0.8, x₀=5.0.  This produces:
       CVSS 0  → P ≈ 0.02
       CVSS 5  → P ≈ 0.50
       CVSS 10 → P ≈ 0.98

   The parameters are user-configurable via settings.py so that an
   organisation can calibrate against its own incident data.
   (Fenton & Neil, "Risk Assessment and Decision Analysis with Bayesian
   Networks", 2012, §6.3)

2. Context-factor adjustment (exposure, patch, privilege, protocol, trust)
   Rather than multiply odds by arbitrary constants raised to arbitrary
   exponents, we use an additive log-odds (logit) model:

       logit(P) = logit(P₀) + Σ wᵢ · log(Mᵢ)

   where Mᵢ are the multipliers from config.py and wᵢ are the user-
   configurable weights.  This is the standard formulation in logistic
   regression and is the natural conjugate for Bayesian updating of
   binary probabilities (Gelman et al., 2020).

3. Human-factor model
   Phishing susceptibility is modelled as:

       P₀ = R_role · (1 − awareness)

   then adjusted for privilege via the same log-odds mechanism.
   (See Keeley et al., "Human factors in ICS security", 2020)

4. Physical-process model
   A direct override is used because physical compromise (e.g. valve
   tampering) is typically assessed by domain experts rather than
   derived from CVSS.

References
----------
• Pearl, J. (1988). Probabilistic Reasoning in Intelligent Systems.
• Fenton, N. E., & Neil, M. (2012). Risk Assessment and Decision Analysis
  with Bayesian Networks. CRC Press.
• FIRST (2019). CVSS v3.1 User Guide.  https://www.first.org/cvss/user-guide
• Spring, J. et al. (2021). "Practical Bayesian analysis of CVSS scores"
  ACM CCS Workshop on Cyber-Physical Systems Security.
• Gelman, A. et al. (2020). Bayesian Data Analysis (3rd ed.).
"""

import math

from backend.config import (
    M_PRIVILEGE, R_PHISHING, P_BASE_CAP,
    get_exposure_weight, get_patch_weight, get_cvss_mapping, get_cvss_logistic_params,
    get_exposure_multipliers, get_patch_multipliers,
)
from backend.settings import get_settings

# ---------------------------------------------------------------------------
# Literature-backed defaults
# ---------------------------------------------------------------------------
# P_BASE_CAP is defined in backend/config.py.  Soft cap: probabilities are
# never exactly 0 or 1 because that would make Bayesian updating irreversible
# (Pearl, 1988). We use 0.9995 rather than 1.0 to leave room for evidence to
# *reduce* a probability when new mitigating information arrives.

_LOGISTIC_DEFAULT_K = 0.8
_LOGISTIC_DEFAULT_X0 = 5.0


def _cvss_to_prob_logistic(cvss_val: float, k: float, x0: float) -> float:
    """Calibrated logistic mapping CVSS → prior probability.

    Args:
        cvss_val: CVSS Base Score in [0, 10].
        k: Steepness parameter (default 0.8).
        x0: Midpoint parameter (default 5.0).

    Returns:
        A probability in (0, 1), never exactly 0 or 1.
    """
    # Clamp CVSS to valid range
    cvss_clamped = max(0.0, min(10.0, float(cvss_val)))
    raw = 1.0 / (1.0 + math.exp(-k * (cvss_clamped - x0)))
    # Soft-cap away from exact 0/1 boundaries
    return max(1e-6, min(P_BASE_CAP, raw))


def _cvss_to_prob_linear(cvss_val: float) -> float:
    """Linear mapping kept ONLY for backward compatibility.

    Not recommended for new analyses because it assigns P=1.0 to
    CVSS=10, which is empirically indefensible.
    """
    cvss_clamped = max(0.0, min(10.0, float(cvss_val)))
    return max(1e-6, min(P_BASE_CAP, cvss_clamped / 10.0))


def _logit(p: float) -> float:
    """Log-odds (logit) transformation."""
    p = max(1e-12, min(1.0 - 1e-12, float(p)))
    return math.log(p / (1.0 - p))


def _inv_logit(lo: float) -> float:
    """Inverse logit (sigmoid) transformation."""
    # Numerically stable implementation
    if lo >= 0:
        z = math.exp(-lo)
        return 1.0 / (1.0 + z)
    else:
        z = math.exp(lo)
        return z / (1.0 + z)


def _apply_context_log_odds(p0: float, factors: list[tuple[float, float]]) -> float:
    """Adjust a base probability via additive log-odds.

    Args:
        p0: Base probability.
        factors: List of (multiplier, weight) pairs.

    Returns:
        Adjusted probability, soft-capped at P_BASE_CAP.
    """
    lo = _logit(p0)
    for mult, weight in factors:
        if mult <= 0 or weight == 0:
            continue
        # Additive log-odds: each factor shifts the logit by w·log(M)
        lo += float(weight) * math.log(float(mult))
    return max(1e-6, min(P_BASE_CAP, _inv_logit(lo)))


def base_prob(node_id: str, attrs: dict) -> float:
    """Compute the intrinsic compromise probability for an asset.

    The result is P(Compromised | no parent evidence), i.e. the leak
    probability used by the Noisy-OR CPT generator.
    """
    kind = attrs.get("kind", "device")
    if kind == "device":
        p = _device_base_prob(attrs)
    elif kind == "human":
        p = _human_base_prob(attrs)
    elif kind == "physical":
        p = _physical_base_prob(attrs)
    else:
        raise ValueError(f"Unknown kind for node {node_id}: {kind!r}")
    return float(p)


def _device_base_prob(attrs: dict) -> float:
    """Device compromise probability from CVSS and context factors.

    `cvss_type` is the asset's *effective* CVSS v3.1 Base Score (the maximum
    over its vulnerabilities, see backend/cvss.py).  CVSS is a severity score,
    not a probability: the mapping below is an explicit modelling assumption
    (logistic calibration curve), documented and configurable.
    """
    cvss = float(attrs.get("cvss_type", 0.0) or 0.0)
    mapping = get_cvss_mapping()

    # --- Step 1: CVSS (severity) -> prior probability (modelling assumption) ---
    if mapping == "linear":
        p0 = _cvss_to_prob_linear(cvss)
    else:
        # Default: calibrated logistic (scientifically preferred)
        params = get_cvss_logistic_params()
        p0 = _cvss_to_prob_logistic(cvss, params["k"], params["x0"])

    # --- Step 2: Context adjustment via additive log-odds ---
    exposed = bool(attrs.get("exposed", True))
    patched = bool(attrs.get("patched", False))

    factors: list[tuple[float, float]] = []
    # Exposure / patch multipliers come from settings (configurable), falling
    # back to the framework defaults in config.py (M_EXPOSURE / M_PATCH).
    exposure_mult = get_exposure_multipliers()
    patch_mult = get_patch_multipliers()
    factors.append((exposure_mult[exposed], get_exposure_weight()))
    factors.append((patch_mult[patched], get_patch_weight()))

    # Optional: protocol, trust, mitre multipliers if present on the asset
    # (these are normally edge attributes, but can be asset-level defaults)
    for key, table in (
        ("protocol", get_settings().get("protocol_multipliers", {})),
        ("trust", get_settings().get("trust_multipliers", {})),
        ("mitre", get_settings().get("mitre_multipliers", {})),
    ):
        val = attrs.get(key)
        if val and str(val).lower() in table:
            factors.append((table[str(val).lower()], 1.0))

    return _apply_context_log_odds(p0, factors)


def _human_base_prob(attrs: dict) -> float:
    """Human compromise probability from role, awareness, and privilege."""
    role = str(attrs.get("role", "operator")).lower()
    awareness = float(attrs.get("awareness", 0.0))
    privilege = str(attrs.get("privilege", "standard")).lower()

    # Base phishing susceptibility
    r = R_PHISHING.get(role, R_PHISHING["operator"])
    p0 = float(r) * (1.0 - max(0.0, min(1.0, awareness)))
    p0 = max(1e-6, min(P_BASE_CAP, p0))

    # Privilege adjustment via log-odds
    m_priv = M_PRIVILEGE.get(privilege, 1.0)
    return _apply_context_log_odds(p0, [(m_priv, 1.0)])


def _physical_base_prob(attrs: dict) -> float:
    """Physical process compromise probability from expert override."""
    p = float(attrs.get("p_base_override", 0.0))
    return max(0.0, min(P_BASE_CAP, p))


def compute_base_probs(assets: dict) -> dict:
    """Batch compute base probabilities for all assets."""
    return {node_id: base_prob(node_id, attrs) for node_id, attrs in assets.items()}