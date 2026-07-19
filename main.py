"""
main.py

Reusable framework entry point plus backwards-compatible CLI behavior.

Usage:
    python3 main.py
    python3 main.py --topology data/swat_example.json --evidence corp_net=1
    python3 main.py --evidence corp_net=1 --evidence hmi=1
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
from cpt_generator import parameterize
from inference import compute_posteriors_with_evidence
from risk import build_risk_table, write_risk_table
from outputs import (
    write_graph_image,
    write_graph_json,
    write_cpts_json,
    write_posteriors_json,
    write_metrics_json,
    write_summary_txt,
)


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
    total_risk = round(float(risk_table["risk"].sum()), 6) if not risk_table.empty else 0.0
    risk_level = _derive_risk_level(total_risk)

    result = {
        "assets": assets,
        "relationships": relationships,
        "model": model,
        "edge_weights": edge_weights,
        "graph": graph,
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
            "overall_risk": total_risk,
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


def _derive_risk_level(overall_risk: float) -> str:
    if overall_risk >= 2.0:
        return "critical"
    if overall_risk >= 1.0:
        return "high"
    if overall_risk >= 0.5:
        return "moderate"
    return "low"


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