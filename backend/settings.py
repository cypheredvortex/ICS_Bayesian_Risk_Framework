"""
Runtime-configurable framework settings.

Defaults mirror config.py constants. The API and UI can override these
without restarting the process. Thread-safe via threading.Lock.
"""

import json
import threading
from copy import deepcopy
from typing import Any

from backend.database.config import initialize_database
from backend.database.services import AssessmentPersistenceService

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
_settings_lock = threading.Lock()
_initialized_db = False


def _ensure_db_initialized() -> None:
    global _initialized_db
    if not _initialized_db:
        initialize_database()
        _initialized_db = True


def _parse_db_value(key: str, raw: str) -> Any:
    """Parse a stored DB value back to its proper type.

    Dict values are stored as JSON strings. Scalars are stored as plain strings.
    Falls back to the default value if parsing fails.
    """
    if key in _TABLE_KEYS or key == "firewall_multipliers":
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return deepcopy(DEFAULT_SETTINGS.get(key, {}))
    if key in _SCALAR_WEIGHT_KEYS:
        try:
            return float(raw)
        except (ValueError, TypeError):
            return DEFAULT_SETTINGS.get(key, 1.0)
    return raw


def get_settings() -> dict[str, Any]:
    with _settings_lock:
        _ensure_db_initialized()
        service = AssessmentPersistenceService()
        db_settings = service.get_settings()
        if db_settings:
            # Reconstruct properly typed settings from DB values,
            # falling back to runtime defaults for missing keys.
            merged = deepcopy(DEFAULT_SETTINGS)
            for key, value in db_settings.items():
                if value is not None:
                    merged[key] = _parse_db_value(key, value)
            return merged
        return deepcopy(_runtime_settings)


def update_settings(updates: dict[str, Any]) -> dict[str, Any]:
    with _settings_lock:
        _ensure_db_initialized()
        global _runtime_settings
        merged = deepcopy(_runtime_settings)
        _deep_merge(merged, updates)
        _validate_settings(merged)
        _runtime_settings = merged
        service = AssessmentPersistenceService()
        for key, value in merged.items():
            if isinstance(value, dict):
                service.save_settings(key, json.dumps(value))
            elif isinstance(value, float):
                service.save_settings(key, str(value))
            else:
                service.save_settings(key, str(value))
        return deepcopy(_runtime_settings)


def reset_settings() -> dict[str, Any]:
    with _settings_lock:
        _ensure_db_initialized()
        global _runtime_settings
        _runtime_settings = deepcopy(DEFAULT_SETTINGS)
        service = AssessmentPersistenceService()
        for key, value in _runtime_settings.items():
            if isinstance(value, dict):
                service.save_settings(key, json.dumps(value))
            elif isinstance(value, float):
                service.save_settings(key, str(value))
            else:
                service.save_settings(key, str(value))
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
