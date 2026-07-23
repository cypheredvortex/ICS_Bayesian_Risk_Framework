"""
graph_builder.py - Topology to Weighted Graph Skeleton.
"""

from pgmpy.models import DiscreteBayesianNetwork as BayesianNetwork

from backend.config import (
    get_firewall_multipliers, get_mitre_multipliers,
    get_propagation_weights, get_protocol_multipliers, get_trust_multipliers,
)
from backend.attack_paths import _unpack_relationship


def edge_weight(rel_type: str, firewalled: bool, metadata: dict | None = None) -> float:
    metadata = metadata or {}
    w0 = get_propagation_weights()
    m_firewall = get_firewall_multipliers()
    m_protocol = get_protocol_multipliers()
    m_trust = get_trust_multipliers()
    m_mitre = get_mitre_multipliers()

    base = w0[rel_type] * m_firewall[firewalled]
    protocol = str(metadata.get("protocol", "default")).lower()
    trust = str(metadata.get("trust", metadata.get("trust_level", "default"))).lower()
    mitre = str(metadata.get("mitre", metadata.get("mitre_technique", "default"))).upper()

    return min(
        0.99,
        base
        * m_protocol.get(protocol, m_protocol.get("default", 1.0))
        * m_trust.get(trust, m_trust.get("default", 1.0))
        * m_mitre.get(mitre, m_mitre.get("default", 1.0)),
    )


def build_graph_skeleton(relationships: list, node_ids=None) -> tuple[BayesianNetwork, dict]:
    edges = []
    edge_weights = {}
    for rel in relationships:
        source, target, rel_type, firewalled, metadata = _unpack_relationship(rel)
        edges.append((source, target))
        edge_weights[(source, target)] = edge_weight(rel_type, firewalled, metadata)

    model = BayesianNetwork(edges)
    if node_ids is not None:
        model.add_nodes_from(node_ids)
    return model, edge_weights


def graph_to_dict(model, edge_weights: dict, relationships: list, assets: dict | None = None) -> dict:
    nodes = []
    for node_id in model.nodes():
        node = {"id": node_id}
        if assets and node_id in assets:
            node["kind"] = assets[node_id].get("kind", "device")
        nodes.append(node)

    edges = []
    for rel in relationships:
        source, target, rel_type, firewalled, metadata = _unpack_relationship(rel)
        edge = {
            "source": source,
            "target": target,
            "rel_type": rel_type,
            "firewalled": firewalled,
            "weight": round(edge_weights[(source, target)], 6),
        }
        if metadata:
            if "protocol" in metadata:
                edge["protocol"] = metadata.get("protocol")
            if "trust" in metadata or "trust_level" in metadata:
                edge["trust"] = metadata.get("trust", metadata.get("trust_level"))
            if "mitre" in metadata or "mitre_technique" in metadata:
                edge["mitre"] = metadata.get("mitre", metadata.get("mitre_technique"))
        edges.append(edge)

    return {"nodes": nodes, "edges": edges}
