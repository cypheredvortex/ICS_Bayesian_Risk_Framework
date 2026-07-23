"""
risk.py - Posterior Probabilities to Risk Table.
"""

from pathlib import Path

import pandas as pd

from backend.config import get_impact_weight


def m_scope(attrs: dict) -> float:
    if "scope" in attrs:
        return 1 + 0.1 * (attrs["scope"] - 1)
    return 1.0


def build_risk_table(posteriors: dict, assets: dict) -> pd.DataFrame:
    impact_weight = get_impact_weight()
    rows = []
    for node_id, p in posteriors.items():
        attrs = assets.get(node_id, {})
        severity = float(attrs.get("consequence_severity", 0))
        scope_mult = m_scope(attrs)
        impact = severity * scope_mult * impact_weight
        risk = p * impact
        rows.append({
            "asset": node_id,
            "P(compromised|evidence)": round(p, 3),
            "severity": severity,
            "scope_mult": round(scope_mult, 3),
            "impact": round(impact, 3),
            "risk": round(risk, 3),
        })

    if not rows:
        return pd.DataFrame(columns=["asset", "P(compromised|evidence)", "severity", "scope_mult", "impact", "risk"])

    return pd.DataFrame(rows).sort_values("risk", ascending=False).reset_index(drop=True)


RISK_LEVEL_THRESHOLDS = {
    "critical": 1.5,
    "high": 0.8,
    "moderate": 0.3,
}


def risk_level_for(value: float) -> str:
    if value >= RISK_LEVEL_THRESHOLDS["critical"]:
        return "Critical"
    if value >= RISK_LEVEL_THRESHOLDS["high"]:
        return "High"
    if value >= RISK_LEVEL_THRESHOLDS["moderate"]:
        return "Moderate"
    return "Low"


def write_risk_table(df: pd.DataFrame, path: str | Path = "output/risk_table.csv") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    export = df.copy().reset_index(drop=True)
    export.insert(0, "Rank", export.index + 1)
    export["Risk Level"] = export["risk"].map(risk_level_for)
    export = export.rename(columns={
        "asset": "Asset",
        "P(compromised|evidence)": "Compromise Probability",
        "severity": "Consequence Severity",
        "scope_mult": "Scope Multiplier",
        "impact": "Impact Score",
        "risk": "Risk Score",
    })[
        ["Rank", "Asset", "Risk Level", "Risk Score", "Compromise Probability", "Impact Score", "Consequence Severity", "Scope Multiplier"]
    ]
    export.to_csv(path, index=False, float_format="%.3f", encoding="utf-8-sig")
    return path
