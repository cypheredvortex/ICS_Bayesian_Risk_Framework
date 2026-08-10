"""
outputs.py - Writers for graph.json, cpts.json, posteriors.json, summary.txt.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

from backend.attack_paths import _unpack_relationship
from backend.graph_builder import graph_to_dict
from backend.cpt_generator import cpts_to_dict


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
        graph, pos, arrowstyle="->", arrowsize=18, width=1.5, edge_color="#666666", ax=ax,
    )
    nx.draw_networkx_edge_labels(
        graph, pos,
        edge_labels={
            (s, t): f"{rel_type}\n{edge_weights[(s, t)]:.2f}"
            for rel in relationships
            for s, t, rel_type, _fw, _meta in [_unpack_relationship(rel)]
        },
        font_size=7, ax=ax,
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
    data = {"evidence": evidence, "posteriors": {nid: round(p, 6) for nid, p in posteriors.items()}}
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def write_metrics_json(metrics: dict, path="output/metrics.json") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(metrics, f, indent=2)
    return path


# The assessment fields that make up a complete, self-contained machine-
# readable record of a run. Excludes transport/persistence metadata
# (``artifacts`` paths, ``persistence`` status) which are not assessment data.
_ASSESSMENT_JSON_FIELDS = (
    "assets",
    "graph",
    "base_probabilities",
    "posteriors",
    "cpts",
    "risk_scores",
    "attack_paths",
    "summary",
    "evidence_used",
    "timings",
    "settings_used",
)


def _json_default(value):
    """Convert numpy/pandas scalar types to plain JSON types.

    ``json.dump`` raises TypeError on numpy scalars (e.g. values that slip
    through from pandas or pgmpy internals). This fallback keeps the export
    robust: it never silently produces a missing file because of a value
    type, and it never invents data.
    """
    try:
        import numpy as np

        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return float(value)
        if isinstance(value, np.bool_):
            return bool(value)
        if isinstance(value, np.ndarray):
            return value.tolist()
    except ImportError:
        pass
    raise TypeError(
        f"Object of type {type(value).__name__} is not JSON serializable"
    )


def write_assessment_json(result: dict, path="output/assessment.json") -> Path:
    """Write the complete assessment result as a machine-readable JSON record.

    The record mirrors exactly what ``/analyze`` returns and what the
    dashboard displays, plus a generation timestamp, so an archived run can be
    reproduced, compared with later runs, or consumed by other tooling. Every
    field is a real, calculated output of the run - nothing synthetic is added.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "format": "ics-risk-assessment",
        "version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "assessment": {
            key: result[key] for key in _ASSESSMENT_JSON_FIELDS if key in result
        },
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, default=_json_default)
    return path


def write_summary_txt(topology_path, evidence, assets, relationships, risk_table, path="output/summary.txt", top_n=5, settings_used=None, non_default_settings=None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "ICS Risk Pipeline -- Run Summary",
        "=" * 40,
        f"Topology file : {topology_path}",
        f"Assets        : {len(assets)}",
        f"Relationships : {len(relationships)}",
        f"Evidence used : {evidence if evidence else '(none provided)'}",
        "",
    ]

    if settings_used:
        lines += [
            "Model settings used for this run (traceability snapshot):",
            "-" * 40,
        ]
        for key in ("cvss_mapping", "cvss_logistic_params", "exposure_weight", "patch_weight", "impact_weight"):
            if key in settings_used:
                lines.append(f"  {key:24s} = {settings_used[key]}")
        if "propagation_weights" in settings_used:
            pw = settings_used["propagation_weights"]
            lines.append(f"  {'propagation_weights':24s} = {pw}")
        if "risk_thresholds" in settings_used:
            lines.append(f"  {'risk_thresholds':24s} = {settings_used['risk_thresholds']}")
        if non_default_settings:
            lines.append("")
            lines.append("WARNING: non-default settings are active:")
            for key, active, default in non_default_settings:
                lines.append(f"  {key}: active={active!r} vs default={default!r}")
        lines.append("")

    lines += [
        f"Top {top_n} assets by risk:",
        "-" * 40,
    ]

    top = risk_table.head(top_n)
    for _, row in top.iterrows():
        lines.append(f"  {row['asset']:<24} risk={row['risk']:.3f}  P(compromised)={row['P(compromised|evidence)']:.3f}  severity={row['severity']}")

    lines += [
        "",
        "Files written this run:",
        "  output/graph.json        - node list + edges + weights",
        "  output/graph.png         - visual diagram of the topology",
        "  output/cpts.json         - full CPT for every node",
        "  output/posteriors.json   - evidence used + posterior per node",
        "  output/risk_table.csv    - final ranked risk table",
        "  output/summary.txt       - this file",
    ]

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")

    return path
