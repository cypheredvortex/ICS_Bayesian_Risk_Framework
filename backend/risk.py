"""
risk.py — Risk index computation and ranking.

Methodology
-----------
The quantity computed here is a **relative risk index**, not an absolute
quantitative risk measure (e.g. Annual Loss Expectancy or monetary
exposure).  It is designed for *ranking* assets so that analysts can
prioritise investigation and mitigation effort.

    Risk Index  =  P(Compromised | evidence)  ×  Consequence Impact

    Consequence Impact = (consequence_severity / 10) × scope_multiplier
                                                      × impact_weight

where
• P(Compromised | evidence) is the posterior probability from the
  Bayesian network inference (Variable Elimination).  It is a genuine
  probability in [0, 1].
• consequence_severity is a user-supplied asset attribute on a 0–10
  scale (10 = catastrophic loss of availability/safety for the
  process).  Dividing by 10 normalises it to [0, 1].
• scope_multiplier captures the blast radius of a compromise:
      scope_mult = 1 + (scope − 1) × 0.1     (scope ∈ [1, 5] → [1.0, 1.4])
• impact_weight is an organisation-level calibration knob.

Because Impact is normalised, the Risk Index lives in a bounded,
interpretable range (≈ [0, 1.4] at maximum scope).  The Risk Index is
NOT a probability: it is a product of a probability and a normalised
consequence score, and the UI reports Probability, Impact and Risk as
separate columns.

Risk-Level Thresholds
---------------------
The default thresholds are calibration placeholders tuned so that a
typical ICS topology produces a usable spread across four levels.  They
are NOT derived from a formal standard — ISO 27005 and NIST SP 800-30
use qualitative likelihood/impact matrices — and an organisation should
tune them against its own risk appetite:

    Critical  ≥ 0.75
    High      ≥ 0.50
    Moderate  ≥ 0.25
    Low       <  0.25

Overall Network Risk
--------------------
The network-level risk is the **worst-case single-asset risk index**
(max_risk) — the riskiest asset in the topology — which is defensible
and size-independent.  Mean and median risk indices are also reported,
plus the count of assets in each risk level.

References
----------
• ISO/IEC 27005:2022 — Information security risk management.
• NIST SP 800-30 Rev. 1 — Guide for conducting risk assessments.
• Fenton & Neil (2012). Risk Assessment and Decision Analysis with
  Bayesian Networks. CRC Press.
"""

import pandas as pd
from pathlib import Path
from typing import Any

from backend.config import get_impact_weight

# ---------------------------------------------------------------------------
# Thresholds — user-configurable via settings.py
# ---------------------------------------------------------------------------
_DEFAULT_THRESHOLDS = {
    "critical": 0.75,
    "high": 0.50,
    "moderate": 0.25,
}


def _thresholds() -> dict[str, float]:
    """Return current risk-level thresholds."""
    from backend.settings import get_settings
    settings = get_settings()
    raw = settings.get("risk_thresholds", {})
    return {
        "critical": float(raw.get("critical", _DEFAULT_THRESHOLDS["critical"])),
        "high": float(raw.get("high", _DEFAULT_THRESHOLDS["high"])),
        "moderate": float(raw.get("moderate", _DEFAULT_THRESHOLDS["moderate"])),
    }


def get_risk_thresholds() -> dict[str, float]:
    """Return the *active* risk-level thresholds.

    This is the single source of truth for risk-level classification: the
    PDF report colouring, the CLI, and (via ``/settings``) the frontend all
    consume these values so that a change in ``risk_thresholds`` propagates
    everywhere.  See ``backend/settings.py`` for the configurable defaults.
    """
    return _thresholds()


def m_scope(attrs: dict) -> float:
    """Scope multiplier: 1 + (scope-1)*0.1.

    scope=1 → 1.0 (single asset)
    scope=5 → 1.4 (wide blast radius)
    """
    scope = float(attrs.get("scope", 1))
    if scope <= 0:
        return 0.9
    return 1.0 + (scope - 1.0) * 0.1


def risk_level_for(risk_index: float) -> str:
    """Classify a risk index into a qualitative level."""
    t = _thresholds()
    if risk_index >= t["critical"]:
        return "Critical"
    if risk_index >= t["high"]:
        return "High"
    if risk_index >= t["moderate"]:
        return "Moderate"
    return "Low"


def build_risk_table(posteriors: dict[str, float], assets: dict[str, dict]) -> pd.DataFrame:
    """Build a ranked risk register (DataFrame) from posteriors and asset attributes.

    Columns:
        asset, P(compromised|evidence), severity, scope_mult, impact, risk,
        risk_level, Rank

    NOTE: The column is named "risk" (not "risk_index") to maintain backward
    compatibility with the REST API and React frontend, which both expect
    the "risk" key in JSON responses.
    """
    rows: list[dict[str, Any]] = []
    impact_weight = get_impact_weight()

    for asset_id, attrs in assets.items():
        prob = float(posteriors.get(asset_id, 0.0))
        severity = float(attrs.get("consequence_severity", 0.0) or 0.0)
        scope_mult = m_scope(attrs)
        # Normalise the 0-10 consequence severity to [0, 1] so the risk index
        # stays bounded and is never confused with a raw severity.
        impact = (severity / 10.0) * scope_mult * impact_weight
        risk_index = prob * impact

        rows.append({
            "asset": asset_id,
            "P(compromised|evidence)": round(prob, 6),
            "severity": round(severity, 3),
            "scope_mult": round(scope_mult, 3),
            "impact": round(impact, 6),
            "risk": round(risk_index, 6),   # ← kept as "risk" for API/frontend compat
            "risk_level": risk_level_for(risk_index),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df.sort_values(by="risk", ascending=False).reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df) + 1))
    return df


def write_risk_table(df: pd.DataFrame, path: str | Path = "output/risk_table.csv") -> Path:
    """Export the risk register to a UTF-8 CSV with BOM for Excel compatibility."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def compute_aggregate_risk(df: pd.DataFrame) -> dict[str, Any]:
    """Compute defensible aggregate risk statistics.

    The network-level risk is the worst-case single-asset risk index
    (``max_risk``) — the riskiest asset in the topology.  ``mean_risk``,
    ``median_risk`` and the per-level asset counts give context without
    double-counting severity (severity is already embedded in each asset's
    risk index).

    Returns:
        {
            "max_risk": worst-case single-asset risk index,
            "mean_risk": arithmetic mean risk index,
            "median_risk": median risk index,
            "level_counts": {critical, high, moderate, low} asset counts,
            "asset_count": number of assets assessed,
        }
    """
    empty_level_counts: dict[str, int] = {"critical": 0, "high": 0, "moderate": 0, "low": 0}
    empty: dict[str, Any] = {
        "max_risk": 0.0,
        "mean_risk": 0.0,
        "median_risk": 0.0,
        "level_counts": empty_level_counts,
        "asset_count": 0,
    }
    if df.empty:
        return empty

    risk_values = df["risk"].astype(float)
    level_counts: dict[str, int] = {
        level: int((df["risk_level"] == level.title()).sum())
        for level in ("critical", "high", "moderate", "low")
    }

    return {
        "max_risk": round(float(risk_values.max()), 6),
        "mean_risk": round(float(risk_values.mean()), 6),
        "median_risk": round(float(risk_values.median()), 6),
        "level_counts": level_counts,
        "asset_count": int(len(df)),
    }