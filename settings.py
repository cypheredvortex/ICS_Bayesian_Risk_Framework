"""
Runtime-configurable framework settings.

Defaults mirror config.py constants. The API and UI can override these
without restarting the process.
"""

from copy import deepcopy
from typing import Any

DEFAULT_SETTINGS: dict[str, Any] = {
    "cvss_weight": 1.0,
    "exposure_weight": 1.0,
    "patch_weight": 1.0,
    "impact_weight": 1.0,
    "propagation_weights": {
        "controls": 0.70,
        "monitors": 0.20,
        "actuates": 0.60,
        "connects-to": 0.50,
        "programs / operates": 0.80,
    },
    "firewall_multipliers": {
        "true": 0.30,
        "false": 1.00,
    },
    "protocol_multipliers": {
        "default": 1.0,
        "modbus": 1.15,
        "opc-ua": 0.95,
        "dnp3": 1.10,
        "ethernet/ip": 1.05,
        "profinet": 1.05,
        "mqtt": 1.20,
        "http": 1.25,
        "s7comm": 1.10,
    },
    "trust_multipliers": {
        "default": 1.0,
        "high": 0.70,
        "medium": 1.0,
        "low": 1.35,
        "none": 1.50,
    },
    "mitre_multipliers": {
        "default": 1.0,
        "T0886": 1.20,
        "T0885": 1.15,
        "T0831": 1.10,
        "T0855": 1.25,
        "T0866": 1.05,
    },
}

_runtime_settings: dict[str, Any] = deepcopy(DEFAULT_SETTINGS)


def get_settings() -> dict[str, Any]:
    return deepcopy(_runtime_settings)


def update_settings(updates: dict[str, Any]) -> dict[str, Any]:
    """Merge user updates into runtime settings and return the full snapshot."""
    global _runtime_settings
    merged = deepcopy(_runtime_settings)
    _deep_merge(merged, updates)
    _runtime_settings = merged
    return deepcopy(_runtime_settings)


def reset_settings() -> dict[str, Any]:
    global _runtime_settings
    _runtime_settings = deepcopy(DEFAULT_SETTINGS)
    return deepcopy(_runtime_settings)


def _deep_merge(base: dict, updates: dict) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
