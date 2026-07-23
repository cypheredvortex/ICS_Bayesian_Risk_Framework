"""
risk.py  (PHASE 5)

Posterior Probabilities -> Risk Table.

FIX APPLIED: impact_weight was previously an EXPONENT on
(severity * scope_mult). Whether raising that exponent actually
amplified impact depended entirely on whether the topology author set
consequence_severity above or below 1 -- an undocumented, easy-to-get-
backwards convention. It's now a direct linear multiplier: weight=1.0
reproduces the original default behavior exactly
(severity * scope_mult * 1.0 == (severity * scope_mult) ** 1.0), and
increasing the slider always increases impact regardless of how
severity happens to be scaled in a given topology.
"""

from pathlib import Path

import pandas as pd

from config import get_impact_weight


def m_scope(attrs: dict) -> float:
    if "scope" in attrs:
        return 1 + 0.1 * (attrs["scope"] - 1)
    return 1.0


def build_risk_table(posteriors: dict, assets: dict) -> pd.DataFrame:
    impact_weight = get_impact_weight()
    rows = []
    for node_id, p in posteriors.items():
        attrs = assets[node_id]
        severity = float(attrs.get("consequence_severity", 0))
        scope_mult = m_scope(attrs)
        # Linear multiplier -- see module docstring. weight=1.0 matches
        # the original (severity * scope_mult) ** 1.0 behavior exactly.
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

    return pd.DataFrame(rows).sort_values("risk", ascending=False).reset_index(drop=True)


# Shared risk-level thresholds -- kept in one place so the CSV export, the
# aggregate summary (main.py), and the frontend can't drift out of sync
# with each other again. See main.py's RISK_LEVEL_THRESHOLDS docstring for
# why these specific cut points were chosen.
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
    # The API needs the compact internal columns above, but the download is a
    # decision-facing register. Export descriptive headers, a rank and a
    # readable risk level while retaining numeric values for sorting in Excel.
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
    # UTF-8 BOM makes the headings readable when the file is opened directly
    # in spreadsheet applications on Windows.
    export.to_csv(path, index=False, float_format="%.3f", encoding="utf-8-sig")
    return path


if __name__ == "__main__":
    from assets import load_topology
    from graph_builder import build_graph_skeleton
    from probability import compute_base_probs
    from cpt_generator import parameterize
    from inference import compute_posteriors

    assets, relationships = load_topology("data/swat_example.json")
    model, edge_weights = build_graph_skeleton(relationships, node_ids=assets.keys())
    base_probs = compute_base_probs(assets)
    model = parameterize(model, edge_weights, base_probs)

    evidence = {"local_hmi": 1}
    posteriors = compute_posteriors(model, evidence)

    risk_table = build_risk_table(posteriors, assets)
    out_path = write_risk_table(risk_table)

    print(f"Risk table (evidence: {evidence}) written to {out_path}\n")
    print(risk_table.to_string(index=False))