"""
assets.py - Load and validate ICS topology from JSON, YAML, or CSV.
"""

import csv
import io
import json
from pathlib import Path

import yaml

from backend.attack_paths import _unpack_relationship
from backend.config import W0

VALID_KINDS = {"device", "human", "physical"}
VALID_REL_TYPES = set(W0.keys())

REQUIRED_DEVICE_KEYS = {"cvss_type", "exposed", "patched"}
REQUIRED_HUMAN_KEYS = {"role", "awareness", "privilege"}
REQUIRED_PHYSICAL_KEYS: set = set()


def load_topology(path: str | Path | dict) -> tuple[dict, list]:
    """Load and validate assets + relationships from a path or in-memory dict."""
    if isinstance(path, dict):
        raw = path
        source_label = "inline topology"
    else:
        path = Path(path)
        raw = _load_raw_file(path)
        source_label = str(path)

    return _parse_topology_dict(raw, source_label)


def load_topology_from_bytes(content: bytes, filename: str) -> tuple[dict, list]:
    """Load topology from uploaded bytes, inferring format from filename."""
    suffix = Path(filename).suffix.lower()
    text = content.decode("utf-8-sig")

    if suffix == ".json":
        raw = json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        raw = yaml.safe_load(text)
    elif suffix == ".csv":
        raw = _parse_csv_text(text)
    else:
        raise ValueError(
            f"Unsupported topology format '{suffix}'. "
            "Supported formats: .json, .yaml, .yml, .csv"
        )

    return _parse_topology_dict(raw, filename)


def _load_raw_file(path: Path) -> dict:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8-sig")

    if suffix == ".json":
        return json.loads(text)
    if suffix in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    if suffix == ".csv":
        return _parse_csv_text(text)
    raise ValueError(
        f"Unsupported topology format '{suffix}'. "
        "Supported formats: .json, .yaml, .yml, .csv"
    )


def _parse_csv_text(text: str) -> dict:
    """
    CSV format:
      section,field,value...
      asset,id,kind,cvss_type,exposed,patched,...
      relationship,source,target,rel_type,firewalled,protocol,trust,mitre
    """
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise ValueError("CSV topology file is empty.")

    assets: dict[str, dict] = {}
    relationships: list = []

    for row in rows:
        if not row or not row[0].strip():
            continue
        section = row[0].strip().lower()
        if section == "asset" and len(row) >= 3:
            asset_id = row[1].strip()
            kind = row[2].strip()
            attrs: dict = {"kind": kind}
            if kind == "device" and len(row) >= 7:
                attrs.update({
                    "cvss_type": float(row[3]),
                    "exposed": row[4].strip().lower() in {"1", "true", "yes"},
                    "patched": row[5].strip().lower() in {"1", "true", "yes"},
                })
                if row[6].strip():
                    attrs["consequence_severity"] = float(row[6])
            elif kind == "human" and len(row) >= 7:
                attrs.update({
                    "role": row[3].strip(),
                    "awareness": float(row[4]),
                    "privilege": row[5].strip(),
                })
                if row[6].strip():
                    attrs["consequence_severity"] = float(row[6])
            elif kind == "physical":
                if len(row) >= 4 and row[3].strip():
                    attrs["p_base_override"] = float(row[3])
                if len(row) >= 5 and row[4].strip():
                    attrs["consequence_severity"] = float(row[4])
            assets[asset_id] = attrs
        elif section == "relationship" and len(row) >= 5:
            metadata = {}
            if len(row) >= 6 and row[5].strip():
                metadata["protocol"] = row[5].strip()
            if len(row) >= 7 and row[6].strip():
                metadata["trust"] = row[6].strip()
            if len(row) >= 8 and row[7].strip():
                metadata["mitre"] = row[7].strip().upper()
            relationships.append(
                (
                    row[1].strip(),
                    row[2].strip(),
                    row[3].strip(),
                    row[4].strip().lower() in {"1", "true", "yes"},
                    metadata,
                )
            )

    if not assets:
        raise ValueError("CSV topology must include at least one 'asset' row.")
    return {"assets": assets, "relationships": relationships}


def _parse_topology_dict(raw: dict, source_label: str) -> tuple[dict, list]:
    if not isinstance(raw, dict):
        raise ValueError(f"{source_label}: topology payload must be an object.")
    if "assets" not in raw or "relationships" not in raw:
        raise ValueError(f"{source_label}: must contain 'assets' and 'relationships' keys")

    assets = raw["assets"]
    if not isinstance(assets, dict):
        raise ValueError(f"{source_label}: 'assets' must be an object.")
    if not assets:
        raise ValueError(f"{source_label}: topology must include at least one asset.")

    relationships = [_normalize_relationship(record) for record in raw["relationships"]]

    _validate_assets(assets)
    _validate_relationships(relationships, assets)
    _validate_graph_structure(assets, relationships, source_label)

    return assets, relationships


def _normalize_relationship(record) -> tuple:
    if not isinstance(record, (list, tuple)) or len(record) < 4:
        raise ValueError("Each relationship must contain at least 4 fields.")
    source, target, rel_type, firewalled = record[:4]
    metadata = record[4] if len(record) > 4 else {}
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise ValueError(
            f"Relationship ({source} -> {target}): optional metadata must be a dict."
        )
    return source, target, rel_type, bool(firewalled), metadata


def _validate_assets(assets: dict) -> None:
    for node_id, attrs in assets.items():
        if not isinstance(attrs, dict):
            raise ValueError(f"Asset '{node_id}': attributes must be an object.")

        kind = attrs.get("kind")
        if kind not in VALID_KINDS:
            raise ValueError(
                f"Asset '{node_id}': kind must be one of {VALID_KINDS}, got {kind!r}"
            )

        required = {
            "device": REQUIRED_DEVICE_KEYS,
            "human": REQUIRED_HUMAN_KEYS,
            "physical": REQUIRED_PHYSICAL_KEYS,
        }[kind]
        missing = required - attrs.keys()
        if missing:
            raise ValueError(f"Asset '{node_id}': missing required keys {missing}")

        if kind == "device":
            cvss = attrs["cvss_type"]
            if not isinstance(cvss, (int, float)) or cvss < 0 or cvss > 10:
                raise ValueError(
                    f"Asset '{node_id}': cvss_type must be a number between 0 and 10."
                )
            if not isinstance(attrs["exposed"], bool):
                raise ValueError(f"Asset '{node_id}': exposed must be true/false.")
            if not isinstance(attrs["patched"], bool):
                raise ValueError(f"Asset '{node_id}': patched must be true/false.")

        if kind == "human":
            awareness = attrs["awareness"]
            if not isinstance(awareness, (int, float)) or awareness < 0 or awareness > 1:
                raise ValueError(
                    f"Asset '{node_id}': awareness must be a number between 0 and 1."
                )
            if attrs["role"] not in {"operator", "engineer", "admin", "guest"}:
                raise ValueError(f"Asset '{node_id}': unsupported role {attrs['role']!r}.")
            if attrs["privilege"] not in {"standard", "elevated", "admin"}:
                raise ValueError(
                    f"Asset '{node_id}': unsupported privilege {attrs['privilege']!r}."
                )

        if "consequence_severity" in attrs:
            severity = attrs["consequence_severity"]
            if not isinstance(severity, (int, float)) or severity < 0:
                raise ValueError(
                    f"Asset '{node_id}': consequence_severity must be a non-negative number."
                )


def _validate_relationships(relationships: list, assets: dict) -> None:
    seen_edges: set[tuple[str, str]] = set()
    for rel in relationships:
        source, target, rel_type, firewalled, _metadata = _unpack_relationship(rel)
        if source not in assets or target not in assets:
            raise ValueError(f"Relationship ({source} -> {target}): references unknown asset")
        if rel_type not in VALID_REL_TYPES:
            raise ValueError(
                f"Relationship ({source} -> {target}): rel_type '{rel_type}' not in {VALID_REL_TYPES}"
            )
        if not isinstance(firewalled, bool):
            raise ValueError(f"Relationship ({source} -> {target}): firewalled must be true/false")
        if source == target:
            raise ValueError(f"Relationship ({source} -> {target}): self-loops are not allowed.")

        edge_key = (source, target)
        if edge_key in seen_edges:
            raise ValueError(f"Duplicate relationship detected: {source} -> {target}")
        seen_edges.add(edge_key)


def _validate_graph_structure(assets: dict, relationships: list, source_label: str) -> None:
    import networkx as nx

    graph = nx.DiGraph()
    graph.add_nodes_from(assets.keys())
    for rel in relationships:
        source, target, _, _, _ = _unpack_relationship(rel)
        graph.add_edge(source, target)

    if not nx.is_directed_acyclic_graph(graph):
        raise ValueError(f"{source_label}: topology contains cycles; Bayesian networks require a DAG.")

    if graph.number_of_nodes() > 1 and graph.number_of_edges() == 0:
        raise ValueError(f"{source_label}: topology has assets but no relationships.")

    if not nx.is_weakly_connected(graph) and graph.number_of_edges() > 0:
        components = list(nx.weakly_connected_components(graph))
        if len(components) > 1:
            component_sizes = sorted((len(c) for c in components), reverse=True)
            if component_sizes[0] > 1 and component_sizes[1] > 1:
                raise ValueError(
                    f"{source_label}: topology contains disconnected subgraphs with multiple nodes."
                )

