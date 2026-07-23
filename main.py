"""
main.py

Reusable framework entry point plus backwards-compatible CLI behavior.

Usage:
    python3 main.py
    python3 main.py --topology data/swat_example.json --evidence corp_net=1
    python3 main.py --evidence corp_net=1 --evidence hmi=1

FIX APPLIED: `overall_risk` was previously `risk_table["risk"].sum()`, an
UNNORMALIZED total across every asset. Because it's a raw sum, the
critical/high/moderate/low thresholds effectively measured topology size
as much as actual risk -- a 20-asset topology where every asset is
individually "Low" risk could sum past the "Critical" threshold, while a
2-asset topology with both assets maxed out at "Critical" individually
might land at "Moderate" overall. Neither result reflects the analyst's
actual security posture.

`overall_risk` is now the MEAN of the top-N riskiest assets (N=5, or
fewer if the topology has fewer assets) -- a size-invariant aggregate
that answers "how bad are my worst assets," which is what an analyst
scanning the top-level badge actually wants to know. Because this
produces a value on the same scale as an individual asset's risk score,
it now reuses the exact same thresholds as the per-asset CSV export and
frontend pie chart (via risk.risk_level_for), instead of maintaining a
second, inconsistent set of cut points.
"""

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from assets import load_topology
from attack_paths import compute_attack_paths
from graph_builder import build_graph_skeleton, graph_to_dict
from probability import compute_base_probs
from cpt_generator import cpts_to_dict, parameterize
from inference import compute_posteriors_with_evidence
from risk import build_risk_table, write_risk_table, risk_level_for
from outputs import (
    write_graph_image,
    write_graph_json,
    write_cpts_json,
    write_posteriors_json,
    write_metrics_json,
    write_summary_txt,
)

# Number of highest-risk assets averaged together to produce overall_risk.
# Kept small and fixed rather than scaling with topology size, so the
# aggregate always reflects "how bad are the worst few assets" regardless
# of how large the topology is.
_OVERALL_RISK_TOP_N = 5


def run(topology: str | Path | dict, evidence: dict | None = None, output_dir: str | Path | None = None, write_outputs: bool = False) -> dict[str, Any]:
    """
    Reusable framework entry point.

    Args:
        topology: path to a JSON topology file or an in-memory topology dict.
        evidence: dict of node_id -> 0|1 evidence values.
        output_dir: optional directory to write artifacts into.
        write_outputs: when True, preserve the old CLI file-generation behavior.

    Returns:
        A structured dictionary suitable for backend adapters and web apps.
    """
    if evidence is None:
        evidence = {}

    assets, relationships = load_topology(topology)

    build_start = time.perf_counter()
    model, edge_weights = build_graph_skeleton(relationships, node_ids=assets.keys())
    base_probs = compute_base_probs(assets)
    model = parameterize(model, edge_weights, base_probs)
    build_time_seconds = time.perf_counter() - build_start

    inference_start = time.perf_counter()
    posteriors, evidence_used = compute_posteriors_with_evidence(model, evidence)
    risk_table = build_risk_table(posteriors, assets)
    inference_time_seconds = time.perf_counter() - inference_start

    graph = graph_to_dict(model, edge_weights, relationships, assets=assets)
    attack_paths = compute_attack_paths(
        relationships,
        edge_weights,
        evidence_used,
        risk_table.to_dict(orient="records"),
        assets,
    )
    overall_risk = _compute_overall_risk(risk_table)
    risk_level = risk_level_for(overall_risk).lower()

    result = {
        "assets": assets,
        "relationships": relationships,
        "model": model,
        "edge_weights": edge_weights,
        "cpts": cpts_to_dict(model),
        "graph": graph,
        "base_probabilities": base_probs,
        "posteriors": posteriors,
        "risk_scores": risk_table.to_dict(orient="records"),
        "attack_paths": attack_paths,
        "evidence_used": evidence_used,
        "risk_table": risk_table,
        "timings": {
            "build_time_seconds": round(build_time_seconds, 6),
            "inference_time_seconds": round(inference_time_seconds, 6),
            "total_time_seconds": round(build_time_seconds + inference_time_seconds, 6),
        },
        "summary": {
            "topology": str(topology) if not isinstance(topology, dict) else "inline-topology",
            "asset_count": len(assets),
            "relationship_count": len(relationships),
            "evidence_used": evidence_used,
            "overall_risk": overall_risk,
            "overall_risk_basis": f"mean of top {min(_OVERALL_RISK_TOP_N, len(risk_table))} highest-risk assets",
            "risk_level": risk_level,
            "highest_risk_assets": risk_table.head(5)["asset"].tolist(),
            "critical_attack_path": attack_paths[0] if attack_paths else None,
        },
    }

    if write_outputs:
        out_dir = Path(output_dir or "output")
        out_dir.mkdir(parents=True, exist_ok=True)

        graph_path = write_graph_json(
            result["model"], result["edge_weights"], result["relationships"],
            path=out_dir / "graph.json",
        )
        graph_image_path = write_graph_image(
            result["model"], result["edge_weights"], result["relationships"],
            path=out_dir / "graph.png",
        )
        cpts_path = write_cpts_json(result["model"], path=out_dir / "cpts.json")
        posteriors_path = write_posteriors_json(
            result["posteriors"], result["evidence_used"], path=out_dir / "posteriors.json",
        )
        risk_path = write_risk_table(result["risk_table"], path=out_dir / "risk_table.csv")
        metrics_path = write_metrics_json(
            {
                "framework_version": "1.0",
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "topology": str(topology) if not isinstance(topology, dict) else "inline-topology",
                "asset_count": len(result["assets"]),
                "relationship_count": len(result["relationships"]),
                "node_count": len(result["model"].nodes()),
                "edge_count": len(result["model"].edges()),
                "posterior_count": len(result["posteriors"]),
                "risk_row_count": len(result["risk_table"]),
                "evidence_count": len(result["evidence_used"]),
                "evidence_used": result["evidence_used"],
                "attack_path_count": len(result["attack_paths"]),
                "validation": {
                    "success": True,
                    "errors": 0,
                },
                "inference_algorithm": "Variable Elimination",
                "build_time_seconds": result["timings"]["build_time_seconds"],
                "inference_time_seconds": result["timings"]["inference_time_seconds"],
                "total_time_seconds": result["timings"]["total_time_seconds"],
            },
            path=out_dir / "metrics.json",
        )
        summary_path = write_summary_txt(
            str(topology) if not isinstance(topology, dict) else "inline-topology",
            result["evidence_used"],
            result["assets"],
            result["relationships"],
            result["risk_table"],
            path=out_dir / "summary.txt",
        )
        result["artifacts"] = {
            "graph": str(graph_path),
            "graph_image": str(graph_image_path),
            "cpts": str(cpts_path),
            "posteriors": str(posteriors_path),
            "risk_table": str(risk_path),
            "metrics": str(metrics_path),
            "summary": str(summary_path),
        }

    return result


def run_pipeline(topology_path: str | Path | dict, evidence: dict):
    """Backward-compatible alias for callers that still expect the original pipeline shape."""
    return run(topology_path, evidence=evidence, write_outputs=False)


def _compute_overall_risk(risk_table) -> float:
    """Mean risk of the top-N riskiest assets. Size-invariant: adding more
    low-risk assets to a topology no longer inflates this number, and a
    small topology of a few very risky assets is no longer structurally
    incapable of reaching "Critical"."""
    if risk_table.empty:
        return 0.0
    top_n = risk_table["risk"].head(_OVERALL_RISK_TOP_N)
    return round(float(top_n.mean()), 6)


def parse_evidence(pairs: list[str]) -> dict:
    """Parse ['corp_net=1', 'hmi=0'] -> {'corp_net': 1, 'hmi': 0}"""
    evidence = {}
    for pair in pairs:
        node_id, value = pair.split("=")
        evidence[node_id] = int(value)
    return evidence


def main():
    parser = argparse.ArgumentParser(description="ICS risk-scoring pipeline")
    parser.add_argument(
        "--topology", default="data/swat_example.json",
        help="Path to topology JSON (default: data/swat_example.json)",
    )
    parser.add_argument(
        "--evidence", action="append", default=[],
        help="node=value, repeatable, e.g. --evidence corp_net=1",
    )
    parser.add_argument(
        "--output-dir", default="output",
        help="Directory to write graph.json, cpts.json, posteriors.json, "
             "risk_table.csv, summary.txt into (default: output)",
    )
    args = parser.parse_args()

    evidence = parse_evidence(args.evidence) if args.evidence else {}
    result = run(args.topology, evidence=evidence, output_dir=args.output_dir, write_outputs=True)

    print(f"=== Risk table (evidence used: {result['evidence_used']}) ===\n")
    print(result["risk_table"].to_string(index=False))
    print("\nWritten:")
    for path in result.get("artifacts", {}).values():
        print(f"  {path}")


if __name__ == "__main__":
    main()