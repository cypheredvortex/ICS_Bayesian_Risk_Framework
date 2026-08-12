"""Topology normalization and graph validation.

Defines the normalized internal representation used by the Bayesian engine.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any

import networkx as nx

from backend.config import get_propagation_weights
from backend.cvss import effective_cvss_score, normalize_vulnerabilities

logger = logging.getLogger(__name__)

VALID_KINDS = {"device", "human", "physical"}
DEFAULT_REL_TYPE = "connects-to"

# Purdue Enterprise Reference Architecture levels.  "3.5" is the industrial
# DMZ level (introduced by the ISA-99/IEC 62443 community as the controlled
# boundary between Enterprise IT and OT).
VALID_PURDUE_LEVELS = {"0", "1", "2", "3", "3.5", "4", "5"}

# Fallback zone-name -> Purdue level mapping used when an asset does not
# declare an explicit ``purdue_level``.  It keeps the two architectural
# concepts distinct: a *security zone* (IEC 62443) and a *Purdue level* are
# orthogonal — an asset's level is derived from its zone only as a sensible
# default, and an explicit per-asset attribute always wins.
ZONE_PURDUE_DEFAULTS = {
    "internet": "5",
    "enterprise": "4",
    "corporate": "4",
    "idmz": "3.5",
    "industrial dmz": "3.5",
    "dmz": "3.5",
    "operations": "3",
    "control room": "3",
    "supervisory": "3",
    "control": "2",
    "dcs": "2",
    "shopfloor": "2",
    "cell": "2",
    "sis": "2",
    "safety": "2",
    "substation": "2",
    "utility": "2",
    "field": "1",
    "remote": "1",
    "remotesite": "1",
    "process": "0",
}

# Asset-type vocabulary used by the architecture audit to recognise control-
# plane assets (which must never sit inside an industrial DMZ) and firewall-
# class boundary assets (which mediate Enterprise <-> OT traffic).  Tokens are
# whole words; multi-word descriptors live in _CONTROL_PLANE_PHRASES and are
# matched as substrings of the joined lowercase name/type/id (a token set
# cannot represent "operator station" because tokenization splits on
# non-alphanumerics).
_CONTROL_PLANE_TOKENS = {
    "plc", "rtu", "dcs", "controller", "scada", "protection", "ied",
    "hmi", "operator", "engineering", "workstation",
}
_CONTROL_PLANE_PHRASES = {
    "operator station", "engineering station", "engineering workstation",
    "logic solver", "safety plc", "safety logic", "control system",
}
_FIREWALL_TOKENS = {"firewall", "gateway", "diode", "proxy"}

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
    "staff",
    "person",
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


def _strict_float(value: Any, context: str, field: str, lo: float, hi: float) -> float:
    """Parse a numeric attribute strictly, raising a useful error when invalid."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"{context}: '{field}' must be a number, got {value!r}."
        ) from None
    if not (lo <= number <= hi):
        raise ValueError(
            f"{context}: '{field}' must be in [{lo}, {hi}], got {number}."
        )
    return number


def _strict_bool(value: Any, context: str, field: str) -> bool:
    """Parse a boolean attribute strictly when explicitly provided."""
    if isinstance(value, bool):
        return value
    text = _normalize_text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(
        f"{context}: '{field}' must be a boolean, got {value!r}."
    )


def _name_tokens(name: str) -> set[str]:
    """Whole-word tokens from an asset name (underscores/hyphens split).

    Matching whole tokens instead of substrings avoids collisions such as
    'engineer' matching 'engineering' or 'operator' matching 'operator_console'
    incorrectly.
    """
    candidate = _normalize_text(name).lower()
    return {token for token in re.split(r"[^a-z0-9]+", candidate) if token}


def infer_asset_kind(name: str, raw: dict | None = None) -> str:
    """Infer an asset kind from its name using whole-token keyword matching.

    This is a heuristic fallback only: an explicit 'kind'/'type' attribute in
    the source data always wins.  The heuristic prioritises unambiguous human
    role words, then physical-process vocabulary, then ICS device vocabulary.
    """
    if raw is not None:
        kind = raw.get("kind") or raw.get("type") or raw.get("category")
        if isinstance(kind, str) and kind.strip().lower() in VALID_KINDS:
            return kind.strip().lower()

    tokens = _name_tokens(name)
    if tokens & set(_COMMON_HUMAN_KEYWORDS):
        return "human"
    if tokens & set(_COMMON_PHYSICAL_KEYWORDS):
        return "physical"
    if tokens & set(_COMMON_DEVICE_KEYWORDS):
        return "device"
    return "device"


def zone_to_purdue_level(zone: Any) -> str | None:
    """Map a declared security zone to a Purdue level (heuristic default).

    The zone is matched exactly first, then by whole-zone substring so
    multi-word zone names such as "DCS Network", "Control Network",
    "Industrial DMZ" or "Remote Tank Farm" still resolve.  Returns ``None``
    when nothing matches — the asset simply has no derived level.
    """
    candidate = _normalize_text(zone).lower()
    if candidate in ZONE_PURDUE_DEFAULTS:
        return ZONE_PURDUE_DEFAULTS[candidate]
    for zone_name, level in ZONE_PURDUE_DEFAULTS.items():
        if zone_name in candidate:
            return level
    return None


def infer_purdue_level(name: str, raw: dict | None = None) -> str | None:
    """Infer a Purdue level from an asset name or its declared zone.

    An explicit ``purdue_level`` attribute wins; otherwise the declared zone
    is mapped through ``zone_to_purdue_level``; finally a zone-like name token
    is matched.  This is a heuristic fallback only.
    """
    if raw is not None:
        explicit = raw.get("purdue_level")
        if explicit is not None and str(explicit).strip() in VALID_PURDUE_LEVELS:
            return str(explicit).strip()
        zone = raw.get("zone") or raw.get("network")
        if zone:
            level = zone_to_purdue_level(zone)
            if level:
                return level
    candidate = _normalize_text(name).lower()
    for zone_name, level in ZONE_PURDUE_DEFAULTS.items():
        if zone_name in candidate:
            return level
    return None


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
    # The declared asset type (e.g. "Firewall", "DCS Controller") and a
    # plain-language description are display/metadata fields: they never
    # affect the risk model, but dropping them silently destroyed information
    # the analyst sees in the UI (asset explanation, architecture audit).
    # A `type`/`category` that is actually a kind alias ("device", "human",
    # "physical") has already been consumed by kind inference above and is
    # deliberately not duplicated.
    asset_type = _normalize_text(raw.get("type") or raw.get("category"))
    if asset_type and asset_type not in VALID_KINDS:
        attrs["type"] = asset_type
    description = _normalize_text(raw.get("description"))
    if description:
        attrs["description"] = description
    if zone := raw.get("zone"):
        attrs["zone"] = _normalize_text(zone)
    elif inferred_zone := infer_asset_zone(asset_id, raw):
        attrs["zone"] = inferred_zone
    if network := raw.get("network"):
        attrs["network"] = _normalize_text(network)
    if metadata := raw.get("metadata"):
        attrs["metadata"] = metadata

    # Purdue Enterprise Reference Architecture level ("0".."5", plus "3.5"
    # for the industrial DMZ).  It is architectural metadata that orients the
    # asset in the OT hierarchy; it never alters the Bayesian mathematics
    # directly.  When absent, enrichment derives a sensible default from the
    # asset's zone.
    if "purdue_level" in raw and raw.get("purdue_level") not in (None, ""):
        level = _normalize_text(raw["purdue_level"])
        if level not in VALID_PURDUE_LEVELS:
            raise ValueError(
                f"asset '{asset_id}': 'purdue_level' must be one of "
                f"{sorted(VALID_PURDUE_LEVELS, key=lambda v: (float(v), v))}, got {level!r}."
            )
        attrs["purdue_level"] = level

    # Blast-radius scope (1-5) is a risk-model attribute consumed by
    # backend/risk.m_scope as the scope multiplier 1 + (scope-1)*0.1.
    # It must be preserved here; otherwise it is silently dropped and the
    # documented scope multiplier always evaluates to 1.0.
    if "scope" in raw:
        attrs["scope"] = _strict_float(raw["scope"], f"asset '{asset_id}'", "scope", 1.0, 5.0)

    context = f"asset '{asset_id}'"

    if kind == "device":
        # A vulnerability list (CVE + CVSS vector/score) is authoritative for
        # the asset's effective CVSS base score.  The legacy single-number
        # `cvss_type` field is kept as a shortcut for one implicit
        # vulnerability.
        if "vulnerabilities" in raw:
            try:
                vulns = normalize_vulnerabilities(raw["vulnerabilities"], context)
            except ValueError:
                raise  # already contextualized
            attrs["vulnerabilities"] = vulns
            attrs["cvss_type"] = effective_cvss_score(vulns)
        elif "cvss_type" in raw:
            attrs["cvss_type"] = _strict_float(raw["cvss_type"], context, "cvss_type", 0.0, 10.0)
        if "exposed" in raw:
            attrs["exposed"] = _strict_bool(raw["exposed"], context, "exposed")
        if "patched" in raw:
            attrs["patched"] = _strict_bool(raw["patched"], context, "patched")
        if "consequence_severity" in raw:
            attrs["consequence_severity"] = _strict_float(
                raw["consequence_severity"], context, "consequence_severity", 0.0, 10.0
            )
    elif kind == "human":
        attrs["role"] = _normalize_text(raw.get("role") or raw.get("position") or "guest").lower()
        if "awareness" in raw:
            attrs["awareness"] = _strict_float(raw["awareness"], context, "awareness", 0.0, 1.0)
        if "privilege" in raw:
            attrs["privilege"] = _normalize_text(raw["privilege"]).lower()
        if "consequence_severity" in raw:
            attrs["consequence_severity"] = _strict_float(
                raw["consequence_severity"], context, "consequence_severity", 0.0, 10.0
            )
    elif kind == "physical":
        if "p_base_override" in raw:
            attrs["p_base_override"] = _strict_float(raw["p_base_override"], context, "p_base_override", 0.0, 1.0)
        if "consequence_severity" in raw:
            attrs["consequence_severity"] = _strict_float(
                raw["consequence_severity"], context, "consequence_severity", 0.0, 10.0
            )

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

    source_raw = raw.get("source") or raw.get("src") or raw.get("from") or raw.get("source_asset")
    target_raw = raw.get("target") or raw.get("dst") or raw.get("to") or raw.get("destination_asset")
    if source_raw is None or target_raw is None:
        return None

    source = _normalize_text(source_raw)
    target = _normalize_text(target_raw)
    rel_type = _normalize_text(raw.get("type") or raw.get("rel_type") or raw.get("relationship_type") or DEFAULT_REL_TYPE)
    if not rel_type:
        rel_type = DEFAULT_REL_TYPE
    # NOTE: unknown relationship types are deliberately NOT rewritten here.
    # validate_graph() rejects them with an actionable error so a typo never
    # silently becomes a generic "connects-to" edge.

    firewalled = _normalize_bool(raw.get("firewalled") or raw.get("protected") or raw.get("is_firewalled"), False)
    metadata_dict: dict[str, Any] = {}
    if protocol := raw.get("protocol"):
        metadata_dict["protocol"] = _normalize_text(protocol)
    if trust := raw.get("trust"):
        metadata_dict["trust_level"] = _normalize_text(trust)
    if trust := raw.get("trust_level"):
        metadata_dict["trust_level"] = _normalize_text(trust)
    if mitre := raw.get("mitre") or raw.get("mitre_technique"):
        metadata_dict["mitre_technique"] = _normalize_text(mitre)
    # Physical transport for a link (e.g. "Ethernet", "Leased line + VPN",
    # "Radio") — display/conduit metadata that makes remote links explicit
    # instead of pretending everything is ordinary Ethernet.
    if transport := raw.get("transport"):
        metadata_dict["transport"] = _normalize_text(transport)
    if "metadata" in raw and isinstance(raw["metadata"], dict):
        metadata_dict.update(raw["metadata"])
    return source, target, rel_type, firewalled, metadata_dict


def _asset_collection_from_dict(raw: dict, warnings: list[str] | None = None) -> dict[str, dict]:
    assets: dict[str, dict] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            if not isinstance(value, dict):
                if warnings is not None:
                    warnings.append(
                        f"asset '{key}' was skipped because its attributes are not an object."
                    )
                continue
            normalized = normalize_asset(value)
            if normalized and normalized["id"]:
                assets[normalized["id"]] = normalized
            elif warnings is not None:
                warnings.append(
                    f"asset '{key}' was skipped because it has no usable identifier."
                )
    return assets


def _asset_collection_from_list(raw: list, warnings: list[str] | None = None) -> dict[str, dict]:
    assets: dict[str, dict] = {}
    for item in raw:
        if not isinstance(item, dict):
            if warnings is not None:
                warnings.append(
                    "an asset record was skipped because it is not an object."
                )
            continue
        normalized = normalize_asset(item)
        if normalized and normalized["id"]:
            assets[normalized["id"]] = normalized
        elif warnings is not None:
            warnings.append(
                f"asset record {item!r} was skipped because it has no usable identifier."
            )
    return assets


def _relationship_collection_from_list(raw: list, warnings: list[str] | None = None) -> list[tuple]:
    relationships: list[tuple] = []
    for item in raw:
        rel = normalize_relationship(item)
        if rel:
            relationships.append(rel)
        elif warnings is not None:
            warnings.append(
                f"relationship {item!r} was skipped because it is malformed (missing source or target)."
            )
    return relationships


def parse_generic_json(raw: Any, warnings: list[str] | None = None) -> dict[str, Any]:
    assets: dict[str, dict] = {}
    relationships: list[tuple] = []

    if isinstance(raw, list):
        assets = _asset_collection_from_list(raw, warnings)
        return {"assets": assets, "relationships": relationships}

    if not isinstance(raw, dict):
        raise ValueError("Input data must be a JSON object or list.")

    asset_keys = ["assets", "nodes", "devices", "components", "items", "elements", "system_units"]
    for key in asset_keys:
        if key in raw:
            candidate = raw[key]
            if isinstance(candidate, dict):
                assets = _asset_collection_from_dict(candidate, warnings)
            elif isinstance(candidate, list):
                assets = _asset_collection_from_list(candidate, warnings)
            if assets:
                break

    if not assets:
        for key, candidate in raw.items():
            if isinstance(candidate, list) and candidate and isinstance(candidate[0], dict):
                candidate_assets = _asset_collection_from_list(candidate, warnings)
                if candidate_assets:
                    assets = candidate_assets
                    break

    rel_keys = ["relationships", "edges", "links", "connections", "connections_list", "paths"]
    for key in rel_keys:
        if key in raw and isinstance(raw[key], list):
            relationships = _relationship_collection_from_list(raw[key], warnings)
            if relationships:
                break

    if not assets:
        raise ValueError("Could not locate assets in the provided JSON document.")

    return {"assets": assets, "relationships": relationships}


def validate_graph(
    assets: dict[str, dict],
    relationships: list[tuple],
    source_label: str,
    warnings: list[str] | None = None,
) -> list[tuple]:
    """Validate a normalized topology and return the cleaned relationship list.

    Self-loops and duplicate edges are removed with an explicit warning (they
    add no causal information and usually come from spreadsheet authoring
    mistakes).  References to unknown assets, unknown relationship types, and
    cycles are rejected with actionable error messages.

    Args:
        warnings: Optional list that receives human-readable notes for every
            relationship that was normalized away, so the analyst is always
            informed instead of seeing silent input changes.
    """
    if not assets:
        raise ValueError(f"{source_label}: no assets found in the topology.")

    node_ids = set(assets.keys())
    supported_types = set(get_propagation_weights().keys())
    clean_relationships: list[tuple] = []
    seen_edges: set[tuple[str, str]] = set()

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
            # from CSV/Excel authoring mistakes. Warn and skip instead of
            # hard-failing the entire upload so users can correct inputs
            # without losing their session.
            message = (
                f"{source_label}: relationship ({source} -> {target}) is a self-loop "
                "and was removed."
            )
            logger.warning(message)
            if warnings is not None:
                warnings.append(message)
            continue
        if (source, target) in seen_edges:
            message = (
                f"{source_label}: duplicate relationship ({source} -> {target}) was "
                "removed."
            )
            logger.warning(message)
            if warnings is not None:
                warnings.append(message)
            continue
        seen_edges.add((source, target))
        clean_relationships.append(rel)

    graph = nx.DiGraph()
    graph.add_nodes_from(node_ids)
    for source, target, *_ in clean_relationships:
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
            logger.warning(
                "%s: topology contains %d disconnected subgraphs; proceeding with analysis.",
                source_label,
                len(non_singleton),
            )

    return clean_relationships


def relationship_to_dict(rel: tuple) -> dict[str, Any]:
    source, target, rel_type, firewalled, metadata = rel
    return {
        "source": source,
        "target": target,
        "type": rel_type,
        "firewalled": firewalled,
        "metadata": metadata,
    }


def audit_ics_architecture(
    assets: dict[str, dict],
    relationships: list[tuple],
) -> list[dict[str, Any]]:
    """Audit a normalized topology against ICS architectural good practice.

    This is deliberately advisory: it distinguishes structural *errors*
    (architectures that violate defensible ICS segmentation principles),
    *warnings* (configurations that should be reviewed) and *info* notes.
    It never rejects a topology — the structural validation in
    ``validate_graph`` is the gatekeeper for uploads.  The audit surfaces
    findings so an analyst can see whether an architecture is defensible
    before trusting its risk numbers.

    Rules are grounded in Purdue-inspired zoning, IEC 62443 zone/conduit
    concepts and NIST SP 800-82: control assets do not belong in a DMZ, the
    Enterprise/OT boundary should be mediated by firewalls, field devices must
    not be directly reachable from enterprise networks, and SIS should not be
    exposed to enterprise networks.

    Returns:
        A list of issue dicts ``{"severity": "error"|"warning"|"info",
        "code", "message", "assets": [...]}`` sorted by severity.
    """
    issues: list[dict[str, Any]] = []

    def add(severity: str, code: str, message: str, involved: list[str]) -> None:
        issues.append({
            "severity": severity,
            "code": code,
            "message": message,
            "assets": sorted(set(involved)),
        })

    zone_of = {aid: str(attrs.get("zone", "")) for aid, attrs in assets.items()}
    kind_of = {aid: str(attrs.get("kind", "device")) for aid, attrs in assets.items()}
    purdue_of = {
        aid: str(attrs.get("purdue_level", "")) for aid, attrs in assets.items()
    }
    type_of = {aid: str(attrs.get("type", "")) for aid, attrs in assets.items()}

    def is_control_plane(aid: str) -> bool:
        # The normalized asset model preserves `name` and `id` (the original
        # `type` is consumed for kind inference), so classify from all three.
        # Whole-word tokens AND multi-word phrases are checked, so an
        # "Operator Station" or "Engineering Workstation" in a DMZ is caught
        # (phrases cannot be represented as tokens).
        attrs = assets[aid]
        combined = f"{type_of.get(aid, '')} {attrs.get('name', '')} {aid}".lower()
        if any(phrase in combined for phrase in _CONTROL_PLANE_PHRASES):
            return True
        tokens = _name_tokens(combined)
        return bool(tokens & _CONTROL_PLANE_TOKENS)

    def is_firewall_class(aid: str) -> bool:
        attrs = assets[aid]
        tokens = _name_tokens(
            f"{type_of.get(aid, '')} {attrs.get('name', '')} {aid}"
        )
        return bool(tokens & _FIREWALL_TOKENS)

    def is_dmz_zone(zone: str) -> bool:
        candidate = _normalize_text(zone).lower()
        return "dmz" in candidate or "demilitar" in candidate

    def is_enterprise_zone(zone: str) -> bool:
        candidate = _normalize_text(zone).lower()
        return candidate in {"enterprise", "corporate", "business", "internet"} \
            or "enterprise" in candidate or "corp" in candidate

    def purdue_rank(level: str) -> float:
        try:
            return float(level)
        except (TypeError, ValueError):
            return float("nan")

    # --- 1. Control-plane assets inside an industrial DMZ -------------------
    dmz_control = [
        aid for aid, attrs in assets.items()
        if is_dmz_zone(str(attrs.get("zone", ""))) and is_control_plane(aid)
    ]
    if dmz_control:
        add(
            "error", "CONTROL_ASSET_IN_DMZ",
            "Control-plane assets (controllers, HMIs, operator/engineering "
            "stations, SCADA) must not be placed inside an industrial DMZ; "
            "the DMZ should only host broker/proxy/jump/transfer services.",
            dmz_control,
        )

    # --- 2. SIS exposure to enterprise networks -----------------------------
    sis_exposed: list[str] = []
    for aid, attrs in assets.items():
        if not (is_dmz_zone(str(attrs.get("zone", "")))
                or is_enterprise_zone(str(attrs.get("zone", "")))):
            continue
        tokens = _name_tokens(
            f"{type_of.get(aid, '')} {attrs.get('name', '')} {aid}"
        )
        if tokens & {"sis", "safety", "esd", "logic", "solver"}:
            sis_exposed.append(aid)
    if sis_exposed:
        add(
            "error", "SIS_EXPOSED_TO_ENTERPRISE",
            "Safety instrumented system assets must not be reachable from "
            "enterprise/DMZ networks; the SIS requires its own protected zone "
            "with controlled conduits.",
            sis_exposed,
        )

    # --- 3. Enterprise assets directly controlling/actuating field/process --
    direct_control: list[str] = []
    for rel in relationships:
        source, target, rel_type, _firewalled, _meta = rel
        src_zone = zone_of.get(source, "")
        if not (is_enterprise_zone(src_zone) and rel_type in {"controls", "actuates"}):
            continue
        if kind_of.get(target) in ("physical",) or purdue_rank(purdue_of.get(target, "")) <= 1:
            direct_control.append(f"{source} -> {target}")
    if direct_control:
        add(
            "error", "ENTERPRISE_CONTROLS_FIELD",
            "Enterprise-zone assets directly control or actuate field/process "
            "assets; command paths to field devices must be mediated by OT "
            "control systems (e.g. via the IDMZ and the control network).",
            [edge.split(" -> ")[0] for edge in direct_control],
        )

    # --- 4. Field/process assets directly reachable from enterprise --------
    direct_field: list[str] = []
    for rel in relationships:
        source, target, _rel_type, _firewalled, _meta = rel
        if is_enterprise_zone(zone_of.get(source, "")) and (
            kind_of.get(target) == "physical" or purdue_rank(purdue_of.get(target, "")) <= 1
        ):
            direct_field.append(f"{source} -> {target}")
    if direct_field:
        add(
            "warning", "ENTERPRISE_TO_FIELD_LINK",
            "A direct communication link exists between an enterprise-zone "
            "asset and a field/process asset; such paths should be mediated "
            "by the industrial DMZ and OT firewalls.",
            [edge.split(" -> ")[0] for edge in direct_field],
        )

    # --- 5. Missing security boundary between Enterprise and OT ------------
    boundary_paths = [
        rel for rel in relationships
        if is_enterprise_zone(zone_of.get(rel[0], ""))
        and not is_enterprise_zone(zone_of.get(rel[1], ""))
    ]
    if boundary_paths and not any(
        is_firewall_class(aid) for aid in assets
    ):
        add(
            "warning", "MISSING_SECURITY_BOUNDARY",
            "No firewall-class asset (firewall/gateway/data diode) was found "
            "between the Enterprise and OT zones; a controlled security "
            "boundary is expected where enterprise and OT traffic meet.",
            [rel[0] for rel in boundary_paths],
        )
    else:
        unfirewalled = [
            f"{rel[0]} -> {rel[1]}" for rel in boundary_paths
            if not rel[3]
        ]
        if unfirewalled:
            add(
                "info", "BOUNDARY_LINK_NOT_FIREWALLED",
                "Enterprise-to-OT boundary links are not individually marked "
                "as firewalled in the data; consider flagging them so the "
                "propagation model applies the firewall reduction factor.",
                [edge.split(" -> ")[0] for edge in unfirewalled],
            )

    # --- 6. Purdue level present and consistent -----------------------------
    missing_level = [aid for aid, attrs in assets.items() if not purdue_of.get(aid)]
    if missing_level:
        add(
            "info", "PURDUE_LEVEL_MISSING",
            "Assets without an explicit Purdue level; a default will be "
            "derived from the declared zone.",
            missing_level,
        )

    # --- 7. SIS self-containment --------------------------------------------
    _SIS_TOKENS = {"sis", "safety", "esd", "logic", "solver"}
    sis_assets = [
        aid for aid, attrs in assets.items()
        if "sis" in str(attrs.get("zone", "")).lower()
        or "sis" in str(attrs.get("type", "")).lower()
        or bool(_name_tokens(f"{type_of.get(aid, '')} {aid}") & _SIS_TOKENS)
    ]
    if sis_assets:
        sis_ids = set(sis_assets)
        sis_names = {
            aid: str(assets[aid].get("name", "")) for aid in sis_ids
        }
        has_final_elements = any(
            "valve" in _name_tokens(f"{sis_names.get(aid, '')} {aid}")
            for aid in sis_ids
        )
        has_sensors = any(
            bool(_name_tokens(f"{sis_names.get(aid, '')} {aid}") & {"transmitter", "sensor"})
            for aid in sis_ids
        )
        if not (has_final_elements and has_sensors):
            add(
                "warning", "SIS_CHAIN_INCOMPLETE",
                "The SIS zone does not expose a complete safety chain "
                "(dedicated safety sensors -> safety logic solver -> final "
                "elements); verify the representation.",
                sorted(sis_ids),
            )

    # --- 8. Cross-zone direct links that skip the IDMZ ----------------------
    skipped_dmz: list[str] = []
    for rel in relationships:
        source, target, _rel_type, _firewalled, _meta = rel
        src_p, tgt_p = purdue_of.get(source, ""), purdue_of.get(target, "")
        if not src_p or not tgt_p:
            continue
        if purdue_rank(src_p) >= 4 and purdue_rank(tgt_p) <= 2:
            skipped_dmz.append(f"{source} -> {target}")
    if skipped_dmz:
        add(
            "warning", "DMZ_BYPASS_LINK",
            "A link connects an Enterprise-level asset directly to a "
            "control-level asset, bypassing the industrial DMZ boundary; "
            "such paths should be mediated by the DMZ.",
            [edge.split(" -> ")[0] for edge in skipped_dmz],
        )

    order = {"error": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda item: (order.get(item["severity"], 9), item["code"]))
    return issues


def build_topology_summary(
    assets: dict[str, dict], relationships: list[tuple]
) -> dict[str, Any]:
    """Compute a structural summary of a normalized topology for analyst review.

    This is computed from the *normalized* assets/relationships the backend
    already validated, so every number it reports is something the framework
    actually knows (never fabricated). It powers the pre-analysis review step
    in the UI: zone inventory, asset-kind mix, relationship-type mix, and
    per-asset field coverage so missing security attributes are visible
    before an assessment is run.

    Args:
        assets: normalized asset map (``id -> attrs``).
        relationships: normalized relationship tuples
            ``(source, target, rel_type, firewalled, metadata)``.

    Returns:
        A dict with ``zones``, ``assets_without_zone``, ``kinds``,
        ``relationship_types``, ``firewalled_relationships`` and
        ``field_coverage`` keys.
    """
    kinds: Counter[str] = Counter()
    zones: Counter[str] = Counter()
    rel_types: Counter[str] = Counter()
    purdue_levels: Counter[str] = Counter()

    field_coverage = {
        "cvss_type": 0,
        "exposed": 0,
        "patched": 0,
        "consequence_severity": 0,
        "zone": 0,
        "vulnerabilities": 0,
        # Declared device type and plain-language description (display
        # metadata preserved by normalize_asset since the earlier rework).
        "type": 0,
        "description": 0,
    }
    for attrs in assets.values():
        kinds[str(attrs.get("kind", "device"))] += 1
        zone = attrs.get("zone")
        if zone:
            zones[str(zone)] += 1
        level = attrs.get("purdue_level")
        if level:
            purdue_levels[str(level)] += 1
        for field in field_coverage:
            if field == "vulnerabilities":
                if attrs.get("vulnerabilities"):
                    field_coverage[field] += 1
            elif attrs.get(field) is not None:
                field_coverage[field] += 1

    firewalled_relationships = 0
    for rel in relationships:
        rel_type = rel[2] if len(rel) > 2 else DEFAULT_REL_TYPE
        rel_types[str(rel_type)] += 1
        if len(rel) > 3 and rel[3]:
            firewalled_relationships += 1

    architecture_issues = audit_ics_architecture(assets, relationships)
    issues_by_severity = Counter(
        issue["severity"] for issue in architecture_issues
    )

    return {
        "zones": dict(sorted(zones.items())),
        "assets_without_zone": max(0, len(assets) - sum(zones.values())),
        "kinds": {k: kinds[k] for k in sorted(kinds)},
        "purdue_levels": {
            level: purdue_levels[level]
            for level in sorted(purdue_levels, key=lambda v: (float(v), v))
        },
        "relationship_types": dict(sorted(rel_types.items())),
        "firewalled_relationships": firewalled_relationships,
        "field_coverage": field_coverage,
        # ICS architectural review: advisory findings (errors/warnings/info)
        # so an analyst can tell whether an architecture is defensible
        # before trusting its risk numbers.
        "architecture_issues": architecture_issues,
        "architecture_issue_counts": dict(issues_by_severity),
    }
