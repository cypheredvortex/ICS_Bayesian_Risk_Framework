"""
Runtime-configurable framework settings.

Defaults mirror config.py constants. The API and UI can override these
without restarting the process. Thread-safe via threading.Lock.
"""

import json
import logging
import threading
from contextlib import contextmanager
from copy import deepcopy
from typing import Any

from backend.database.config import initialize_database
from backend.database.services import AssessmentPersistenceService

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS: dict[str, Any] = {
    # CVSS is a severity score (0-10), not a probability. The logistic mapping
    # below is an explicit, configurable modelling assumption that turns a
    # severity score into an intrinsic compromise probability (see
    # backend/probability.py). Parameters (k, x0) allow organisation-level
    # calibration against incident data.
    "cvss_mapping": "logistic",
    "cvss_logistic_params": {"k": 0.8, "x0": 5.0},
    "exposure_weight": 1.0,
    "patch_weight": 1.0,
    "impact_weight": 1.0,
    # Exposure / patch multipliers applied through the additive log-odds
    # model (backend/probability.py).  Framework defaults live in
    # backend/config.py (M_EXPOSURE / M_PATCH); making them configurable lets
    # an organisation calibrate these effects against its own data.
    "exposure_multipliers": {"true": 1.3, "false": 0.3},
    "patch_multipliers": {"true": 0.9, "false": 1.2},
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
    "risk_thresholds": {
        "critical": 0.75,
        "high": 0.50,
        "moderate": 0.25,
    },
}

_SCALAR_WEIGHT_KEYS = ("exposure_weight", "patch_weight", "impact_weight")
_TABLE_KEYS = (
    "propagation_weights",
    "protocol_multipliers",
    "trust_multipliers",
    "mitre_multipliers",
    "exposure_multipliers",
    "patch_multipliers",
)

_runtime_settings: dict[str, Any] = deepcopy(DEFAULT_SETTINGS)
_settings_lock = threading.Lock()
_initialized_db = False
_db_available = False


def _ensure_db_initialized() -> bool:
    """Initialise the persistence layer exactly once.

    Returns True when the database is usable.  On failure the process keeps
    running with in-memory default settings (degraded mode): the analysis
    pipeline must never be blocked by an unavailable persistence layer.
    """
    global _initialized_db, _db_available
    if not _initialized_db:
        try:
            initialize_database()
            _db_available = True
        except Exception:
            logger.exception(
                "Database unavailable; running with in-memory default settings "
                "(settings will not be persisted)"
            )
            _db_available = False
        _initialized_db = True
    return _db_available


def _parse_db_value(key: str, raw: str) -> Any:
    """Parse a stored DB value back to its proper type.

    Dict values are stored as JSON strings. Scalars are stored as plain strings.
    Falls back to the default value if parsing fails.
    """
    if key in _TABLE_KEYS or key in ("firewall_multipliers", "risk_thresholds", "cvss_logistic_params"):
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


def _persist_runtime_settings() -> None:
    """Write the current runtime settings into the database."""
    service = AssessmentPersistenceService()
    for key, value in _runtime_settings.items():
        if isinstance(value, dict):
            service.save_settings(key, json.dumps(value))
        elif isinstance(value, float):
            service.save_settings(key, str(value))
        else:
            service.save_settings(key, str(value))


def get_settings() -> dict[str, Any]:
    with _settings_lock:
        if not _ensure_db_initialized():
            return deepcopy(_runtime_settings)
        try:
            service = AssessmentPersistenceService()
            db_settings = service.get_settings()
        except Exception:
            logger.exception("Could not read persisted settings; using in-memory values")
            return deepcopy(_runtime_settings)
        if db_settings:
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
        if _db_available:
            _persist_runtime_settings()
        return deepcopy(_runtime_settings)


@contextmanager
def temporary_settings(overrides: dict[str, Any]):
    """Temporarily override runtime settings for the duration of the context.

    Intended for offline sensitivity analysis and tests.  The overrides are
    persisted (so ``get_settings`` -- which prefers the database -- returns
    them) and the previous state is fully restored on exit, including the
    persisted copy.  NOTE: the settings store is process-global, so this
    helper must not be used concurrently with live API requests.
    """
    global _runtime_settings
    with _settings_lock:
        original = deepcopy(_runtime_settings)
        merged = deepcopy(_runtime_settings)
        _deep_merge(merged, overrides)
        _validate_settings(merged)
        _runtime_settings = merged
        if _db_available:
            try:
                _persist_runtime_settings()
            except Exception:
                logger.exception("Could not persist temporary settings")
    try:
        yield
    finally:
        with _settings_lock:
            _runtime_settings = original
            if _db_available:
                try:
                    _persist_runtime_settings()
                except Exception:
                    logger.exception("Could not restore persisted settings")


def reset_settings() -> dict[str, Any]:
    with _settings_lock:
        _ensure_db_initialized()
        global _runtime_settings
        _runtime_settings = deepcopy(DEFAULT_SETTINGS)
        if _db_available:
            try:
                _persist_runtime_settings()
            except Exception:
                logger.exception("Could not persist reset settings")
        return deepcopy(_runtime_settings)


def reset_settings_state() -> None:
    """Reset the in-memory settings store and persistence flags.

    Used by the test suite between tests that deliberately break the
    database, so later tests start from a clean state.
    """
    global _runtime_settings, _initialized_db, _db_available
    with _settings_lock:
        _runtime_settings = deepcopy(DEFAULT_SETTINGS)
        _initialized_db = False
        _db_available = False


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

    mapping = settings.get("cvss_mapping")
    if mapping is not None and mapping not in ("logistic", "linear"):
        raise ValueError(
            f"'cvss_mapping' must be 'logistic' or 'linear', got {mapping!r}."
        )

    logistic_params = settings.get("cvss_logistic_params")
    if logistic_params is not None:
        if not isinstance(logistic_params, dict):
            raise ValueError("'cvss_logistic_params' must be an object.")
        k = logistic_params.get("k")
        x0 = logistic_params.get("x0")
        if k is not None and (not isinstance(k, (int, float)) or k <= 0):
            raise ValueError(f"'cvss_logistic_params.k' must be a positive number, got {k!r}.")
        if x0 is not None and (not isinstance(x0, (int, float)) or not (0 <= x0 <= 10)):
            raise ValueError(f"'cvss_logistic_params.x0' must be in [0, 10], got {x0!r}.")

    for table_key in _TABLE_KEYS:
        table = settings.get(table_key, {})
        if not isinstance(table, dict):
            raise ValueError(f"'{table_key}' must be an object.")
        for name, value in table.items():
            if not isinstance(value, (int, float)) or value < 0:
                raise ValueError(
                    f"'{table_key}.{name}' must be a non-negative number, got {value!r}."
                )

    firewall = settings.get("firewall_multipliers", {})
    if not isinstance(firewall, dict):
        raise ValueError("'firewall_multipliers' must be an object.")
    true_value = firewall.get("true")
    false_value = firewall.get("false")
    for label, value in (("true", true_value), ("false", false_value)):
        if value is not None and (not isinstance(value, (int, float)) or value < 0):
            raise ValueError(
                f"'firewall_multipliers.{label}' must be a non-negative number, got {value!r}."
            )
    if true_value is not None and false_value is not None and float(true_value) > float(false_value):
        raise ValueError(
            "'firewall_multipliers.true' (firewalled) cannot exceed 'firewall_multipliers.false' "
            "(not firewalled) -- a firewall must never be configured to increase propagated risk."
        )

    for table_key in ("exposure_multipliers", "patch_multipliers"):
        table = settings.get(table_key, {})
        if not isinstance(table, dict):
            raise ValueError(f"'{table_key}' must be an object.")
        for label, value in table.items():
            if value is not None and (not isinstance(value, (int, float)) or value < 0):
                raise ValueError(
                    f"'{table_key}.{label}' must be a non-negative number, got {value!r}."
                )

    # Validate risk thresholds if present
    risk_thresholds = settings.get("risk_thresholds", {})
    if risk_thresholds:
        if not isinstance(risk_thresholds, dict):
            raise ValueError("'risk_thresholds' must be an object.")
        for level in ("critical", "high", "moderate"):
            val = risk_thresholds.get(level)
            if val is not None and (not isinstance(val, (int, float)) or val < 0):
                raise ValueError(f"'risk_thresholds.{level}' must be a non-negative number.")
        crit = float(risk_thresholds.get("critical", 1.5))
        high = float(risk_thresholds.get("high", 0.8))
        mod = float(risk_thresholds.get("moderate", 0.3))
        if not (crit > high > mod):
            raise ValueError("Risk thresholds must satisfy: critical > high > moderate.")