"""Topology normalization and graph validation.

Defines the normalized internal representation used by the Bayesian engine.
"""

from __future__ import annotations

import re
from typing import Any

import networkx as nx

from backend.config import get_propagation_weights

VALID_KINDS = {"device", "human", "physical"}
DEFAULT_REL_TYPE = "connects-to"

_COMMON_DEVICE_KEYWORDS = [
    "plc",
    "rtu",
    "dcs",
    "controller",
    "hmi",
    "scada",
    "server",
    "gateway",
    "switch",
    "router",
    "firewall",
    "historian",
    "sensor",
    "actuator",
    "workstation",
    "engineering",
    "operator",
]

_COMMON_HUMAN_KEYWORDS = [
    "operator",
    "engineer",
    "admin",
    "user",
    "workstation",
    "console",
    "panel",
]

_COMMON_PHYSICAL_KEYWORDS = [
    "sensor",
    "actuator",
    "valve",
    "pump",
    "motor",
    "tank",
    "field",
    "physical",
    "pipe",
]

_ZONE_KEYWORDS = {
    "level 0": "Level 0",
    "level 1": "Level 1",
    "level 2": "Level 2",
    "level 3": "Level 3",
    "dmz": "DMZ",
    "corp": "Corporate",
    "enterprise": "Corporate",
    "internet": "Internet",
    "control": "Control",
    "substation": "Substation",
}

RELATIONSHIP_FILEDS = ["source", "target", "type", "firewalled", "protocol", "trust", "mitre", "trust_level"]


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = _normalize_text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _normalize_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def infer_asset_kind(name: str, raw: dict | None = None) -> str:
    candidate = _normalize_text(name).lower()
    for token in _COMMON_HUMAN_KEYWORDS:
        if token in candidate:
            return "human"
    for token in _COMMON_PHYSICAL_KEYWORDS:
        if token in candidate:
            return "physical"
    for token in _COMMON_DEVICE_KEYWORDS:
        if token in candidate:
            return "device"
    if raw is not None:
        kind = raw.get("kind") or raw.get("type") or raw.get("category")
        if isinstance(kind, str) and kind.strip().lower() in VALID_KINDS:
            return kind.strip().lower()
    return "device"


def infer_asset_zone(name: str, raw: dict | None = None) -> str | None:
    candidate = _normalize_text(name).lower()
    for token, zone_name in _ZONE_KEYWORDS.items():
        if token in candidate:
            return zone_name
    if raw is not None:
        zone = raw.get("zone") or raw.get("network")
        if zone:
            return _normalize_text(zone)
    return None


def normalize_asset(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None

    asset_id = (
        raw.get("id")
        or raw.get("name")
        or raw.get("asset")
        or raw.get("label")
        or raw.get("asset_id")
        or raw.get("assetName")
        or raw.get("node")
        or raw.get("node_id")
    )
    if asset_id is None:
        return None

    asset_id = _normalize_text(asset_id)
    if not asset_id:
        return None

    kind = raw.get("kind") or raw.get("type") or raw.get("category")
    kind = _normalize_text(kind).lower()
    if kind not in VALID_KINDS:
        kind = infer_asset_kind(asset_id, raw)

    attrs: dict[str, Any] = {
        "id": asset_id,
        "name": _normalize_text(raw.get("name") or raw.get("label") or asset_id),
        "kind": kind,
    }

    if vendor := raw.get("vendor"):
        attrs["vendor"] = _normalize_text(vendor)
    if model := raw.get("model"):
        attrs["model"] = _normalize_text(model)
    if ip := raw.get("ip"):
        attrs["ip"] = _normalize_text(ip)
    if zone := raw.get("zone"):
        attrs["zone"] = _normalize_text(zone)
    elif inferred_zone := infer_asset_zone(asset_id, raw):
        attrs["zone"] = inferred_zone
    if network := raw.get("network"):
        attrs["network"] = _normalize_text(network)
    if metadata := raw.get("metadata"):
        attrs["metadata"] = metadata

    if kind == "device":
        if "cvss_type" in raw:
            attrs["cvss_type"] = _normalize_float(raw["cvss_type"])
        if "exposed" in raw:
            attrs["exposed"] = _normalize_bool(raw["exposed"])
        if "patched" in raw:
            attrs["patched"] = _normalize_bool(raw["patched"])
        if "consequence_severity" in raw:
            attrs["consequence_severity"] = _normalize_float(raw["consequence_severity"])
    elif kind == "human":
        attrs["role"] = _normalize_text(raw.get("role") or raw.get("position") or "guest").lower()
        if "awareness" in raw:
            attrs["awareness"] = _normalize_float(raw["awareness"])
        if "privilege" in raw:
            attrs["privilege"] = _normalize_text(raw["privilege"]).lower()
        if "consequence_severity" in raw:
            attrs["consequence_severity"] = _normalize_float(raw["consequence_severity"])
    elif kind == "physical":
        if "p_base_override" in raw:
            attrs["p_base_override"] = _normalize_float(raw["p_base_override"])
        if "consequence_severity" in raw:
            attrs["consequence_severity"] = _normalize_float(raw["consequence_severity"])

    return attrs


def normalize_relationship(raw: dict | list | tuple) -> tuple | None:
    if isinstance(raw, (list, tuple)):
        if len(raw) < 2:
            return None
        source = _normalize_text(raw[0])
        target = _normalize_text(raw[1])
        if not source or not target:
            return None
        rel_type = _normalize_text(raw[2]) if len(raw) >= 3 else DEFAULT_REL_TYPE
        if not rel_type:
            rel_type = DEFAULT_REL_TYPE
        firewalled = _normalize_bool(raw[3]) if len(raw) >= 4 else False
        metadata = raw[4] if len(raw) >= 5 and isinstance(raw[4], dict) else {}
        return source, target, rel_type, firewalled, metadata

    if not isinstance(raw, dict):
        return None

    source = raw.get("source") or raw.get("src") or raw.get("from") or raw.get("source_asset")
    target = raw.get("target") or raw.get("dst") or raw.get("to") or raw.get("destination_asset")
    if source is None or target is None:
        return None

    source = _normalize_text(source)
    target = _normalize_text(target)
    rel_type = _normalize_text(raw.get("type") or raw.get("rel_type") or raw.get("relationship_type") or DEFAULT_REL_TYPE)
    if not rel_type:
        rel_type = DEFAULT_REL_TYPE
    supported_types = set(get_propagation_weights().keys())
    if rel_type not in supported_types:
        rel_type = DEFAULT_REL_TYPE

    firewalled = _normalize_bool(raw.get("firewalled") or raw.get("protected") or raw.get("is_firewalled"), False)
    metadata: dict[str, Any] = {}
    if protocol := raw.get("protocol"):
        metadata["protocol"] = _normalize_text(protocol)
    if trust := raw.get("trust"):
        metadata["trust_level"] = _normalize_text(trust)
    if trust := raw.get("trust_level"):
        metadata["trust_level"] = _normalize_text(trust)
    if mitre := raw.get("mitre") or raw.get("mitre_technique"):
        metadata["mitre_technique"] = _normalize_text(mitre)
    if "metadata" in raw and isinstance(raw["metadata"], dict):
        metadata.update(raw["metadata"])
    return source, target, rel_type, firewalled, metadata


def _asset_collection_from_dict(raw: dict) -> dict[str, dict]:
    assets: dict[str, dict] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            if isinstance(value, dict):
                normalized = normalize_asset(value)
                if normalized and normalized["id"]:
                    assets[normalized["id"]] = normalized
    return assets


def _asset_collection_from_list(raw: list) -> dict[str, dict]:
    assets: dict[str, dict] = {}
    for item in raw:
        if isinstance(item, dict):
            normalized = normalize_asset(item)
            if normalized and normalized["id"]:
                assets[normalized["id"]] = normalized
    return assets


def _relationship_collection_from_list(raw: list) -> list[tuple]:
    relationships: list[tuple] = []
    for item in raw:
        rel = normalize_relationship(item)
        if rel:
            relationships.append(rel)
    return relationships


def parse_generic_json(raw: Any) -> dict[str, Any]:
    assets: dict[str, dict] = {}
    relationships: list[tuple] = []

    if isinstance(raw, list):
        assets = _asset_collection_from_list(raw)
        return {"assets": assets, "relationships": relationships}

    if not isinstance(raw, dict):
        raise ValueError("Input data must be a JSON object or list.")

    asset_keys = ["assets", "nodes", "devices", "components", "items", "elements", "system_units"]
    for key in asset_keys:
        if key in raw:
            candidate = raw[key]
            if isinstance(candidate, dict):
                assets = _asset_collection_from_dict(candidate)
            elif isinstance(candidate, list):
                assets = _asset_collection_from_list(candidate)
            if assets:
                break

    if not assets:
        for key, candidate in raw.items():
            if isinstance(candidate, list) and candidate and isinstance(candidate[0], dict):
                candidate_assets = _asset_collection_from_list(candidate)
                if candidate_assets:
                    assets = candidate_assets
                    break

    rel_keys = ["relationships", "edges", "links", "connections", "connections_list", "paths"]
    for key in rel_keys:
        if key in raw and isinstance(raw[key], list):
            relationships = _relationship_collection_from_list(raw[key])
            if relationships:
                break

    if not assets:
        raise ValueError("Could not locate assets in the provided JSON document.")

    return {"assets": assets, "relationships": relationships}


def validate_graph(assets: dict[str, dict], relationships: list[tuple], source_label: str) -> None:
    if not assets:
        raise ValueError(f"{source_label}: no assets found in the topology.")

    node_ids = set(assets.keys())
    supported_types = set(get_propagation_weights().keys())
    for rel in relationships:
        source, target, rel_type, firewalled, metadata = rel
        if source not in node_ids:
            raise ValueError(f"Relationship ({source} -> {target}) references unknown source asset.")
        if target not in node_ids:
            raise ValueError(f"Relationship ({source} -> {target}) references unknown target asset.")
        if rel_type not in supported_types:
            raise ValueError(
                f"Relationship ({source} -> {target}): unknown relationship type '{rel_type}'."
            )
        if not isinstance(firewalled, bool):
            raise ValueError(f"Relationship ({source} -> {target}): firewalled must be a boolean.")
        if source == target:
            # Self-loops provide no useful Bayesian dependency and often come
            # from CSV/Excel authoring mistakes. Log and skip instead of
            # hard-failing the entire upload so users can correct inputs
            # without losing their session.
            import logging

            logging.getLogger(__name__).warning(
                "Relationship (%s -> %s): self-loop removed during validation.",
                source,
                target,
            )
            continue

    graph = nx.DiGraph()
    graph.add_nodes_from(node_ids)
    for source, target, *_ in relationships:
        graph.add_edge(source, target)

    if graph.number_of_nodes() > 1 and graph.number_of_edges() == 0:
        raise ValueError(f"{source_label}: topology contains assets but no relationships.")

    if graph.number_of_edges() > 0 and not nx.is_directed_acyclic_graph(graph):
        raise ValueError(f"{source_label}: topology contains cycles; Bayesian networks require a DAG.")

    if graph.number_of_edges() > 0:
        components = list(nx.weakly_connected_components(graph))
        non_singleton = [component for component in components if len(component) > 1]
        if len(non_singleton) > 1:
            # Multiple disconnected components are allowed for Bayesian
            # analysis; they simply represent independent submodels. Log a
            # warning to inform users but do not reject the topology.
            import logging

            logging.getLogger(__name__).warning(
                "%s: topology contains %d disconnected subgraphs; proceeding with analysis.",
                source_label,
                len(non_singleton),
            )


def relationship_to_dict(rel: tuple) -> dict[str, Any]:
    source, target, rel_type, firewalled, metadata = rel
    return {
        "source": source,
        "target": target,
        "type": rel_type,
        "firewalled": firewalled,
        "metadata": metadata,
    }
