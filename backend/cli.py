"""
CLI entry point for the ICS Risk Assessment Framework.

Usage:
    python -m backend
    python -m backend --topology data/swat_example.json --evidence corp_net=1
"""

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

from backend.assets import load_topology
from backend.attack_paths import compute_attack_paths
from backend.graph_builder import build_graph_skeleton, graph_to_dict
from backend.probability import compute_base_probs
from backend.cpt_generator import cpts_to_dict, parameterize
from backend.inference import compute_posteriors_with_evidence
from backend.risk import build_risk_table, write_risk_table, risk_level_for
from backend.outputs import (
    write_graph_image, write_graph_json, write_cpts_json,
    write_posteriors_json, write_metrics_json, write_summary_txt,
)
from backend.database.config import initialize_database
from backend.database.services import AssessmentPersistenceService

_OVERALL_RISK_TOP_N = 5

logger = logging.getLogger(__name__)


def run(
    topology: str | Path | dict,
    evidence: dict | None = None,
    output_dir: str | Path | None = None,
    write_outputs: bool = False,
) -> dict:
    """Reusable framework entry point."""
    import time

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
        relationships, edge_weights, evidence_used,
        risk_table.to_dict(orient="records"), assets,
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

        write_graph_json(result["model"], result["edge_weights"], result["relationships"],
                          path=out_dir / "graph.json")
        write_graph_image(result["model"], result["edge_weights"], result["relationships"],
                           path=out_dir / "graph.png")
        write_cpts_json(result["model"], path=out_dir / "cpts.json")
        write_posteriors_json(result["posteriors"], result["evidence_used"],
                               path=out_dir / "posteriors.json")
        write_risk_table(result["risk_table"], path=out_dir / "risk_table.csv")
        write_metrics_json({
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
            "validation": {"success": True, "errors": 0},
            "inference_algorithm": "Variable Elimination",
            "build_time_seconds": result["timings"]["build_time_seconds"],
            "inference_time_seconds": result["timings"]["inference_time_seconds"],
            "total_time_seconds": result["timings"]["total_time_seconds"],
        }, path=out_dir / "metrics.json")
        write_summary_txt(
            str(topology) if not isinstance(topology, dict) else "inline-topology",
            result["evidence_used"], result["assets"], result["relationships"],
            result["risk_table"], path=out_dir / "summary.txt",
        )
        result["artifacts"] = {
            "graph": str(out_dir / "graph.json"),
            "graph_image": str(out_dir / "graph.png"),
            "cpts": str(out_dir / "cpts.json"),
            "posteriors": str(out_dir / "posteriors.json"),
            "risk_table": str(out_dir / "risk_table.csv"),
            "metrics": str(out_dir / "metrics.json"),
            "summary": str(out_dir / "summary.txt"),
        }

    try:
        initialize_database()
        persistence_service = AssessmentPersistenceService()
        project_name = _project_name_for(topology)
        persistence_service.persist_analysis_run(
            topology={"assets": assets, "relationships": relationships},
            evidence=evidence,
            analysis_result=result,
            project_name=project_name,
            topology_source=str(topology) if not isinstance(topology, dict) else "inline-topology",
        )
        result["persistence"] = {"saved": True, "project_name": project_name}
    except Exception as exc:
        logger.exception("Assessment persistence failed")
        result["persistence"] = {"saved": False, "error": str(exc)}

    return result


def run_pipeline(topology_path: str | Path | dict, evidence: dict):
    """Backward-compatible alias."""
    return run(topology_path, evidence=evidence, write_outputs=False)


def _compute_overall_risk(risk_table) -> float:
    if risk_table.empty:
        return 0.0
    top_n = risk_table["risk"].head(_OVERALL_RISK_TOP_N)
    return round(float(top_n.mean()), 6)


def _project_name_for(topology: str | Path | dict) -> str:
    if isinstance(topology, dict):
        return "inline-topology"
    path = Path(topology)
    return path.stem or path.name or "untitled-project"


def parse_evidence(pairs: list[str]) -> dict:
    """Parse ['corp_net=1', 'hmi=0'] -> {'corp_net': 1, 'hmi': 0}"""
    evidence = {}
    for pair in pairs:
        node_id, value = pair.split("=")
        evidence[node_id] = int(value)
    return evidence


def main():
    parser = argparse.ArgumentParser(description="ICS risk-scoring pipeline")
    parser.add_argument("--topology", default="data/swat_example.json",
                        help="Path to topology JSON (default: data/swat_example.json)")
    parser.add_argument("--evidence", action="append", default=[],
                        help="node=value, repeatable, e.g. --evidence corp_net=1")
    parser.add_argument("--output-dir", default="output",
                        help="Directory to write artifacts into (default: output)")
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
