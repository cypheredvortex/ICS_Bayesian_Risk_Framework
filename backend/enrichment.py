"""Cybersecurity enrichment for normalized ICS topology graphs.

This module adds inferred and default cybersecurity context to a normalized
asset graph so the Bayesian engine can operate without requiring user-supplied
Bayesian parameters in the source engineering files.
"""

from __future__ import annotations

from typing import Any

from backend.topology import DEFAULT_REL_TYPE, infer_asset_kind, infer_asset_zone

_DEFAULT_DEVICE_CVSS = 5.0
_DEFAULT_DEVICE_EXPOSED = True
_DEFAULT_DEVICE_PATCHED = False
_DEFAULT_DEVICE_CONSEQUENCE = 5.0

_DEFAULT_HUMAN_ROLE = "operator"
_DEFAULT_HUMAN_AWARENESS = 0.35
_DEFAULT_HUMAN_PRIVILEGE = "standard"
_DEFAULT_HUMAN_CONSEQUENCE = 3.0

_DEFAULT_PHYSICAL_P_BASE = 0.01
_DEFAULT_PHYSICAL_CONSEQUENCE = 4.0

_VENDOR_PATTERNS = {
    "siemens": "Siemens",
    "rockwell": "Rockwell Automation",
    "schneider": "Schneider Electric",
    "abb": "ABB",
    "honeywell": "Honeywell",
    "emerson": "Emerson",
}

_ROLE_PATTERNS = {
    "operator": ["operator", "hmi", "panel", "console"],
    "engineer": ["engineer", "engineering", "eng"],
    "admin": ["admin", "administrator", "root"],
    "guest": ["guest", "visitor"],
}

_PRIVILEGE_MAP = {
    "operator": "standard",
    "engineer": "elevated",
    "admin": "admin",
    "guest": "standard",
}

_PROTOCOL_PATTERNS = {
    "modbus": ["modbus"],
    "opc-ua": ["opc", "opc-ua"],
    "dnp3": ["dnp"],
    "ethernet/ip": ["ethernet/ip", "ethernet ip", "ethernetip"],
    "profinet": ["profinet"],
    "mqtt": ["mqtt"],
    "http": ["http", "https"],
}

_TRUST_PATTERNS = {
    "high": ["high", "trusted"],
    "medium": ["medium", "internal"],
    "low": ["low", "dmz", "external"],
    "none": ["none", "untrusted", "internet"],
}


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _infer_vendor(name: str, metadata: dict[str, Any]) -> str | None:
    name_text = _normalize_text(name).lower()
    if metadata and isinstance(metadata, dict):
        for candidate in (metadata.get("vendor"), metadata.get("manufacturer"), metadata.get("vendor_name")):
            if candidate:
                return _normalize_text(candidate)
    for token, vendor in _VENDOR_PATTERNS.items():
        if token in name_text:
            return vendor
    return None


def _infer_human_role(name: str, metadata: dict[str, Any]) -> str:
    name_text = _normalize_text(name).lower()
    for role, tokens in _ROLE_PATTERNS.items():
        if any(token in name_text for token in tokens):
            return role
    if metadata and isinstance(metadata, dict):
        role = metadata.get("role") or metadata.get("position")
        if isinstance(role, str) and role.strip():
            return role.strip().lower()
    return _DEFAULT_HUMAN_ROLE


def _infer_protocol(metadata: dict[str, Any], rel_type: str) -> str:
    if metadata and isinstance(metadata, dict):
        for key in ("protocol", "protocols"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().lower()
    rel_type_text = _normalize_text(rel_type).lower()
    for protocol, tokens in _PROTOCOL_PATTERNS.items():
        if any(token in rel_type_text for token in tokens):
            return protocol
    return "unknown"


def _infer_trust(metadata: dict[str, Any]) -> str:
    if metadata and isinstance(metadata, dict):
        for key in ("trust_level", "trust"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().lower()
    return "default"


def _infer_mitre(metadata: dict[str, Any]) -> str | None:
    if not metadata or not isinstance(metadata, dict):
        return None
    for key in ("mitre_technique", "mitre", "attack_id"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().upper()
    return None


def enrich_asset(raw: dict[str, Any]) -> dict[str, Any]:
    asset = dict(raw)
    asset_id = asset.get("id") or asset.get("name")
    name = _normalize_text(asset.get("name") or asset_id or "")
    metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}

    if "kind" not in asset or asset["kind"] not in {"device", "human", "physical"}:
        asset["kind"] = infer_asset_kind(name, asset)

    if "zone" not in asset or not asset.get("zone"):
        asset["zone"] = infer_asset_zone(name, asset) or asset.get("zone")

    if "vendor" not in asset or not asset.get("vendor"):
        vendor = _infer_vendor(name, metadata)
        if vendor:
            asset["vendor"] = vendor

    if asset["kind"] == "device":
        asset["cvss_type"] = float(asset.get("cvss_type", _DEFAULT_DEVICE_CVSS))
        asset["exposed"] = bool(asset.get("exposed", _DEFAULT_DEVICE_EXPOSED))
        asset["patched"] = bool(asset.get("patched", _DEFAULT_DEVICE_PATCHED))
        asset["consequence_severity"] = float(asset.get("consequence_severity", _DEFAULT_DEVICE_CONSEQUENCE))
        asset.setdefault("metadata", metadata)
    elif asset["kind"] == "human":
        asset["role"] = _infer_human_role(name, metadata)
        asset["awareness"] = float(asset.get("awareness", _DEFAULT_HUMAN_AWARENESS))
        asset["privilege"] = _normalize_text(asset.get("privilege", _PRIVILEGE_MAP.get(asset["role"], _DEFAULT_HUMAN_PRIVILEGE))).lower()
        asset["consequence_severity"] = float(asset.get("consequence_severity", _DEFAULT_HUMAN_CONSEQUENCE))
        asset.setdefault("metadata", metadata)
    else:
        asset["p_base_override"] = float(asset.get("p_base_override", _DEFAULT_PHYSICAL_P_BASE))
        asset["consequence_severity"] = float(asset.get("consequence_severity", _DEFAULT_PHYSICAL_CONSEQUENCE))
        asset.setdefault("metadata", metadata)

    if "protocols" in asset and isinstance(asset["protocols"], str):
        asset["protocols"] = [proto.strip().lower() for proto in asset["protocols"].split(",") if proto.strip()]

    if "purdue_level" not in asset:
        asset["purdue_level"] = asset.get("zone") or "unknown"

    return asset


def enrich_relationship(raw: tuple | dict[str, Any]) -> tuple:
    if isinstance(raw, tuple):
        source, target, rel_type, firewalled, metadata = raw
    else:
        source = raw.get("source")
        target = raw.get("target")
        rel_type = raw.get("type") or raw.get("rel_type") or DEFAULT_REL_TYPE
        firewalled = bool(raw.get("firewalled", False))
        metadata = raw.get("metadata", {}) if isinstance(raw.get("metadata", dict)) else {}
        metadata.setdefault("protocol", raw.get("protocol"))
        metadata.setdefault("trust_level", raw.get("trust_level") or raw.get("trust"))
        metadata.setdefault("mitre_technique", raw.get("mitre_technique") or raw.get("mitre"))

    metadata = metadata.copy() if isinstance(metadata, dict) else {}
    if "protocol" not in metadata or not metadata.get("protocol"):
        metadata["protocol"] = _infer_protocol(metadata, rel_type)
    if "trust_level" not in metadata or not metadata.get("trust_level"):
        metadata["trust_level"] = _infer_trust(metadata)
    if "mitre_technique" not in metadata or not metadata.get("mitre_technique"):
        mitre = _infer_mitre(metadata)
        if mitre:
            metadata["mitre_technique"] = mitre

    return source, target, rel_type, bool(firewalled), metadata


def enrich_graph(assets: dict[str, dict[str, Any]], relationships: list[tuple]) -> dict[str, Any]:
    enriched_assets: dict[str, dict[str, Any]] = {}
    for asset_id, attrs in assets.items():
        enriched_assets[asset_id] = enrich_asset(attrs)

    enriched_relationships: list[tuple] = [enrich_relationship(rel) for rel in relationships]

    return {"assets": enriched_assets, "relationships": enriched_relationships}
