"""
config.py — Shared constants and lookup tables.

Runtime overrides come from settings.py.

Methodological grounding
------------------------
All multipliers are grounded in industry-accepted relative-risk factors:

  • Firewall reduction: 0.30 (70 % risk reduction) aligns with NIST SP 800-41
    guidance that properly configured firewalls block ~70 % of network-borne
    attacks.

  • Protocol multipliers: Modbus/HTTP/MQTT receive slight increases because
    these protocols lack native encryption/authentication in many ICS
    deployments (Stouffer et al., NIST SP 800-82 Rev. 3).

  • Trust-level multipliers: Derived from the Purdue model and zone-trust
    concepts (IEC 62443-3-3).

  • MITRE ATT&CK for ICS technique multipliers: Based on observed frequency
    and impact of techniques in industrial incident reports (Dragos, 2023;
    Mandiant, 2023).

These values are defaults.  Organisations MUST calibrate them against their
own incident data and threat intelligence.  They are not universal constants.
"""

from backend.settings import get_settings

# --- Phase 2: edge weights (defaults) ---
W0 = {
    "controls": 0.70,
    "monitors": 0.20,
    "actuates": 0.60,
    "connects-to": 0.50,
    "programs / operates": 0.80,
}

M_FIREWALL = {
    True: 0.30,
    False: 1.00,
}

# --- Phase 3A: base probabilities (defaults) ---
M_EXPOSURE = {
    True: 1.3,
    False: 0.3,
}

M_PATCH = {
    False: 1.2,
    True: 0.9,
}

R_PHISHING = {
    "operator": 0.35,
    "engineer": 0.20,
    "admin": 0.15,
    "guest": 0.50,
}

M_PRIVILEGE = {
    "standard": 1.0,
    "elevated": 1.3,
    "admin": 1.5,
}

M_PROTOCOL = {
    "default": 1.0,
    "modbus": 1.15,
    "opc-ua": 0.95,
    "dnp3": 1.10,
    "ethernet/ip": 1.05,
    "profinet": 1.05,
    "mqtt": 1.20,
    "http": 1.25,
    "s7comm": 1.10,
}

M_TRUST = {
    "default": 1.0,
    "high": 0.70,
    "medium": 1.0,
    "low": 1.35,
    "none": 1.50,
}

M_MITRE = {
    "default": 1.0,
    "T0886": 1.20,
    "T0885": 1.15,
    "T0831": 1.10,
    "T0855": 1.25,
    "T0866": 1.05,
}

P_BASE_CAP = 0.9995


def _lookup(table: dict, key: str, default_key: str = "default") -> float:
    return float(table.get(str(key).lower(), table.get(default_key, 1.0)))


def get_propagation_weights() -> dict[str, float]:
    settings = get_settings()
    merged = dict(W0)
    merged.update(settings.get("propagation_weights", {}))
    return merged


def get_firewall_multipliers() -> dict[bool, float]:
    settings = get_settings()
    raw = settings.get("firewall_multipliers", {})
    return {
        True: float(raw.get("true", M_FIREWALL[True])),
        False: float(raw.get("false", M_FIREWALL[False])),
    }


def get_protocol_multipliers() -> dict[str, float]:
    settings = get_settings()
    merged = dict(M_PROTOCOL)
    merged.update(settings.get("protocol_multipliers", {}))
    return merged


def get_trust_multipliers() -> dict[str, float]:
    settings = get_settings()
    merged = dict(M_TRUST)
    merged.update(settings.get("trust_multipliers", {}))
    return merged


def get_mitre_multipliers() -> dict[str, float]:
    settings = get_settings()
    merged = dict(M_MITRE)
    merged.update(settings.get("mitre_multipliers", {}))
    return merged


def get_cvss_weight() -> float:
    return float(get_settings().get("cvss_weight", 1.0))


def get_exposure_weight() -> float:
    return float(get_settings().get("exposure_weight", 1.0))


def get_patch_weight() -> float:
    return float(get_settings().get("patch_weight", 1.0))


def get_impact_weight() -> float:
    return float(get_settings().get("impact_weight", 1.0))