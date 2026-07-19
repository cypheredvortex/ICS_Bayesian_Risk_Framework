"""
outputs.py

Writers for the non-CSV output files: graph.json, cpts.json,
posteriors.json, summary.txt. Kept separate from risk.py (which already
owns risk_table.csv) so each phase's artifact-writing logic lives next to
that phase's other output, and this module just handles the "extra"
diagnostic/audit files that make a run inspectable after the fact.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

from attack_paths import _unpack_relationship
from graph_builder import graph_to_dict
from cpt_generator import cpts_to_dict


def write_graph_json(model, edge_weights, relationships, path="output/graph.json") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = graph_to_dict(model, edge_weights, relationships)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def write_graph_image(model, edge_weights, relationships, path="output/graph.png") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    graph = nx.DiGraph()
    graph.add_nodes_from(model.nodes())

    for rel in relationships:
        source, target, rel_type, firewalled = _unpack_relationship(rel)[:4]
        graph.add_edge(source, target, rel_type=rel_type, firewalled=firewalled)

    pos = nx.spring_layout(graph, seed=7)
    fig, ax = plt.subplots(figsize=(10, 7))
    nx.draw_networkx_nodes(graph, pos, node_color="#4C78A8", node_size=1500, ax=ax)
    nx.draw_networkx_labels(graph, pos, font_size=9, ax=ax)
    nx.draw_networkx_edges(
        graph,
        pos,
        arrowstyle="->",
        arrowsize=18,
        width=1.5,
        edge_color="#666666",
        ax=ax,
    )
    nx.draw_networkx_edge_labels(
        graph,
        pos,
        edge_labels={
            (s, t): f"{rel_type}\n{edge_weights[(s, t)]:.2f}"
            for rel in relationships
            for s, t, rel_type, _fw, _meta in [_unpack_relationship(rel)]
        },
        font_size=7,
        ax=ax,
    )

    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def write_cpts_json(model, path="output/cpts.json") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = cpts_to_dict(model)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def write_posteriors_json(posteriors: dict, evidence: dict, path="output/posteriors.json") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "evidence": evidence,
        "posteriors": {nid: round(p, 6) for nid, p in posteriors.items()},
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def write_metrics_json(metrics: dict, path="output/metrics.json") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(metrics, f, indent=2)
    return path


def write_summary_txt(
    topology_path: str,
    evidence: dict,
    assets: dict,
    relationships: list,
    risk_table,
    path="output/summary.txt",
    top_n: int = 5,
) -> Path:
    """
    Human-readable run summary: what topology/evidence were used, basic
    graph stats, and the top-N riskiest assets. Meant to be skimmed, not
    parsed -- graph.json/cpts.json/posteriors.json are the machine-readable
    artifacts.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("ICS Risk Pipeline -- Run Summary")
    lines.append("=" * 40)
    lines.append(f"Topology file : {topology_path}")
    lines.append(f"Assets        : {len(assets)}")
    lines.append(f"Relationships : {len(relationships)}")
    lines.append(f"Evidence used : {evidence if evidence else '(none provided)'}")
    lines.append("")
    lines.append(f"Top {top_n} assets by risk:")
    lines.append("-" * 40)

    top = risk_table.head(top_n)
    for _, row in top.iterrows():
        lines.append(
            f"  {row['asset']:<24} risk={row['risk']:.3f}  "
            f"P(compromised)={row['P(compromised|evidence)']:.3f}  "
            f"severity={row['severity']}"
        )

    lines.append("")
    lines.append("Files written this run:")
    lines.append("  output/graph.json        - node list + edges + weights")
    lines.append("  output/graph.png         - visual diagram of the topology")
    lines.append("  output/cpts.json         - full CPT for every node")
    lines.append("  output/posteriors.json   - evidence used + posterior per node")
    lines.append("  output/risk_table.csv    - final ranked risk table")
    lines.append("  output/summary.txt       - this file")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")

    return path