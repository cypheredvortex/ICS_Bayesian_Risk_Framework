"""
risk.py  (PHASE 5)

Posterior Probabilities -> Risk Table.
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
        impact = (severity * scope_mult) ** impact_weight
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


def write_risk_table(df: pd.DataFrame, path: str | Path = "output/risk_table.csv") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # The API needs the compact internal columns above, but the download is a
    # decision-facing register. Export descriptive headers, a rank and a
    # readable risk level while retaining numeric values for sorting in Excel.
    export = df.copy().reset_index(drop=True)
    export.insert(0, "Rank", export.index + 1)
    export["Risk Level"] = export["risk"].map(
        lambda value: "Critical" if value >= 1.5 else "High" if value >= 0.8 else "Moderate" if value >= 0.3 else "Low"
    )
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
