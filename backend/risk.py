"""
risk.py — Risk index computation and ranking.

Methodology
-----------
The quantity computed here is a **relative risk index**, not an absolute
quantitative risk measure (e.g. Annual Loss Expectancy).  It is designed
for *ranking* assets so that analysts can prioritise investigation and
mitigation effort.

Risk Index  =  P(Compromised | evidence)  ×  Impact

Impact      =  consequence_severity  ×  scope_multiplier  ×  impact_weight

where
• P(Compromised | evidence) is the posterior probability from the
  Bayesian network inference (Variable Elimination).
• consequence_severity is a user-supplied asset attribute (0–10 scale).
• scope_multiplier captures the blast-radius of a compromise:
      scope_mult = 1 + (scope − 1) × 0.1
  (scope = 1 → 1.0, scope = 5 → 1.4).
• impact_weight is a user-configurable calibration knob.

Risk-Level Thresholds
---------------------
The default thresholds are *calibration placeholders*.  An organisation
should tune them against its own risk appetite and historical incident
data.  The defaults are:

    Critical  ≥ 1.50
    High      ≥ 0.80
    Moderate  ≥ 0.30
    Low       <  0.30

These defaults are chosen so that a typical ICS topology with severity
in [1, 10] and posterior probabilities in [0, 1] produces a usable
spread across the four levels.  They are NOT derived from a formal
standard because no published standard provides calibrated thresholds
for Bayesian posterior × severity products; ISO 27005 and NIST SP 800-30
use qualitative likelihood/impact matrices instead.

Overall Network Risk
--------------------
We report two aggregate statistics:
1. **max_risk** — the highest single-asset risk index (worst-case).
2. **weighted_mean_risk** — mean risk index weighted by consequence
   severity, giving higher influence to business-critical assets.

The previous "mean of top 5" metric has been removed because it is
not statistically justified and is sensitive to topology size.

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
    "critical": 1.50,
    "high": 0.80,
    "moderate": 0.30,
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
        impact = severity * scope_mult * impact_weight
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


def compute_aggregate_risk(df: pd.DataFrame) -> dict[str, float]:
    """Compute defensible aggregate risk statistics.

    Returns:
        {
            "max_risk": maximum single-asset risk index,
            "weighted_mean_risk": severity-weighted mean risk index,
            "mean_risk": arithmetic mean risk index,
            "median_risk": median risk index,
            "asset_count": number of assets assessed,
        }
    """
    if df.empty:
        return {
            "max_risk": 0.0,
            "weighted_mean_risk": 0.0,
            "mean_risk": 0.0,
            "median_risk": 0.0,
            "asset_count": 0,
        }

    risk_values = df["risk"].astype(float)
    severities = df["severity"].astype(float)

    max_risk = float(risk_values.max())
    mean_risk = float(risk_values.mean())
    median_risk = float(risk_values.median())

    # Severity-weighted mean: business-critical assets count more
    total_sev = severities.sum()
    weighted_mean_risk = float((risk_values * severities).sum() / total_sev) if total_sev > 0 else mean_risk

    return {
        "max_risk": round(max_risk, 6),
        "weighted_mean_risk": round(weighted_mean_risk, 6),
        "mean_risk": round(mean_risk, 6),
        "median_risk": round(median_risk, 6),
        "asset_count": int(len(df)),
    }