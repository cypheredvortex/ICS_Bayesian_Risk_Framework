"""
graph_builder.py  (PHASE 2)

Topology -> Weighted Graph Skeleton.
Purely generic: reads only rel_type and firewalled flag, never node names.
"""

from pgmpy.models import DiscreteBayesianNetwork as BayesianNetwork

from config import W0, M_FIREWALL


def edge_weight(rel_type: str, firewalled: bool) -> float:
    return W0[rel_type] * M_FIREWALL[firewalled]


def build_graph_skeleton(relationships: list, node_ids=None) -> tuple[BayesianNetwork, dict]:
    """
    relationships: list of (source, target, rel_type, firewalled)
    node_ids: optional full set of node ids (e.g. assets.keys()). Required if
        any asset has zero relationships -- BayesianNetwork(edges) only
        creates nodes that appear in an edge, so an isolated node would
        otherwise silently disappear from the model.
    returns: (model, edge_weights)
        model        - pgmpy DiscreteBayesianNetwork, edges only, no CPDs yet
        edge_weights - {(source, target): weight}
    """
    edges = [(s, t) for s, t, _, _ in relationships]
    edge_weights = {
        (s, t): edge_weight(rel_type, fw)
        for s, t, rel_type, fw in relationships
    }
    model = BayesianNetwork(edges)
    if node_ids is not None:
        model.add_nodes_from(node_ids)
    return model, edge_weights


def graph_to_dict(model, edge_weights: dict, relationships: list) -> dict:
    """
    Serialize the graph skeleton into a JSON-friendly structure:
    {
      "nodes": [node_id, ...],
      "edges": [
        {"source": s, "target": t, "rel_type": rt, "firewalled": bool, "weight": float},
        ...
      ]
    }
    """
    edges = []
    for s, t, rel_type, firewalled in relationships:
        edges.append({
            "source": s,
            "target": t,
            "rel_type": rel_type,
            "firewalled": firewalled,
            "weight": round(edge_weights[(s, t)], 6),
        })

    return {
        "nodes": list(model.nodes()),
        "edges": edges,
    }


if __name__ == "__main__":
    from assets import load_topology

    assets, relationships = load_topology("data/swat_example.json")
    model, edge_weights = build_graph_skeleton(relationships, node_ids=assets.keys())

    print("Nodes:", model.nodes())
    print("Edges:", model.edges())
    print("Weights:")
    for k, v in edge_weights.items():
        print(f"  {k}: {v:.3f}")