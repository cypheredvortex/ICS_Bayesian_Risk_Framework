"""
Runtime-configurable framework settings.

Defaults mirror config.py constants. The API and UI can override these
without restarting the process.

FIX APPLIED: update_settings() previously merged arbitrary client input
with no validation at all. That allowed:
  - negative weight values (e.g. cvss_weight < 0), which can crash
    /analyze with a ZeroDivisionError when raised as an exponent on 0.
  - a firewalled multiplier greater than the non-firewalled multiplier,
    i.e. a "firewall" configured to increase propagated risk instead of
    reducing it.
_validate_settings() now runs on every update and rejects both cases
before they're committed to runtime state.
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

_SCALAR_WEIGHT_KEYS = ("cvss_weight", "exposure_weight", "patch_weight", "impact_weight")
_TABLE_KEYS = ("propagation_weights", "protocol_multipliers", "trust_multipliers", "mitre_multipliers")

_runtime_settings: dict[str, Any] = deepcopy(DEFAULT_SETTINGS)


def get_settings() -> dict[str, Any]:
    return deepcopy(_runtime_settings)


def update_settings(updates: dict[str, Any]) -> dict[str, Any]:
    """Merge user updates into runtime settings and return the full snapshot.

    Raises ValueError (caught by the API layer as a 400) if the merged
    result would be out of bounds. The merge is validated as a whole, not
    field-by-field, so a partial update can't leave settings in a state
    that only looks fine in isolation.
    """
    global _runtime_settings
    merged = deepcopy(_runtime_settings)
    _deep_merge(merged, updates)
    _validate_settings(merged)
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


def _validate_settings(settings: dict[str, Any]) -> None:
    for key in _SCALAR_WEIGHT_KEYS:
        value = settings.get(key)
        if value is not None and (not isinstance(value, (int, float)) or value < 0):
            raise ValueError(f"'{key}' must be a non-negative number, got {value!r}.")

    for table_key in _TABLE_KEYS:
        table = settings.get(table_key, {})
        if not isinstance(table, dict):
            raise ValueError(f"'{table_key}' must be an object.")
        for name, value in table.items():
            if not isinstance(value, (int, float)) or value < 0:
                raise ValueError(f"'{table_key}.{name}' must be a non-negative number, got {value!r}.")

    firewall = settings.get("firewall_multipliers", {})
    if not isinstance(firewall, dict):
        raise ValueError("'firewall_multipliers' must be an object.")
    true_value = firewall.get("true")
    false_value = firewall.get("false")
    for label, value in (("true", true_value), ("false", false_value)):
        if value is not None and (not isinstance(value, (int, float)) or value < 0):
            raise ValueError(f"'firewall_multipliers.{label}' must be a non-negative number, got {value!r}.")
    if true_value is not None and false_value is not None and float(true_value) > float(false_value):
        raise ValueError(
            "'firewall_multipliers.true' (firewalled) cannot exceed 'firewall_multipliers.false' "
            "(not firewalled) -- a firewall must never be configured to increase propagated risk."
        )