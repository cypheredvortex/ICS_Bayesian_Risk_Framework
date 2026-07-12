"""
main.py

Executes the full pipeline: Phase 1 -> Phase 5, and writes every
intermediate/final artifact to the output/ folder:
    output/graph.json
    output/cpts.json
    output/posteriors.json
    output/risk_table.csv
    output/summary.txt

Usage:
    python3 main.py
    python3 main.py --topology data/swat_example.json --evidence corp_net=1
    python3 main.py --evidence corp_net=1 --evidence hmi=1
"""

import argparse
from pathlib import Path

from assets import load_topology
from graph_builder import build_graph_skeleton
from probability import compute_base_probs
from cpt_generator import parameterize
from inference import compute_posteriors_with_evidence
from risk import build_risk_table, write_risk_table
from outputs import (
    write_graph_image,
    write_graph_json,
    write_cpts_json,
    write_posteriors_json,
    write_summary_txt,
)


def run_pipeline(topology_path: str, evidence: dict):
    assets, relationships = load_topology(topology_path)

    # Phase 1 -> 2
    model, edge_weights = build_graph_skeleton(relationships, node_ids=assets.keys())

    # Phase 3A -> 3B
    base_probs = compute_base_probs(assets)
    model = parameterize(model, edge_weights, base_probs)

    # Phase 3 -> 4 (also returns the sanitized evidence actually used,
    # since inference.py may fall back to a default node if the evidence
    # passed in referenced unknown nodes or was empty)
    posteriors, evidence_used = compute_posteriors_with_evidence(model, evidence)

    # Phase 4 -> 5
    risk_table = build_risk_table(posteriors, assets)

    return {
        "assets": assets,
        "relationships": relationships,
        "model": model,
        "edge_weights": edge_weights,
        "posteriors": posteriors,
        "evidence_used": evidence_used,
        "risk_table": risk_table,
    }


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
    out_dir = Path(args.output_dir)

    result = run_pipeline(args.topology, evidence)

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
    summary_path = write_summary_txt(
        args.topology, result["evidence_used"], result["assets"], result["relationships"],
        result["risk_table"], path=out_dir / "summary.txt",
    )

    print(f"=== Risk table (evidence used: {result['evidence_used']}) ===\n")
    print(result["risk_table"].to_string(index=False))
    print(f"\nWritten:")
    for p in [graph_path, graph_image_path, cpts_path, posteriors_path, risk_path, summary_path]:
        print(f"  {p}")


if __name__ == "__main__":
    main()