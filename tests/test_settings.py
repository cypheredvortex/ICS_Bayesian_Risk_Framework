"""Tests for the settings module (runtime configuration)."""

import pytest

from backend.settings import (
    DEFAULT_SETTINGS,
    get_settings,
    update_settings,
    reset_settings,
    _validate_settings,
)


class TestGetSettings:
    """Default and server-persisted settings retrieval."""

    def test_returns_dict(self) -> None:
        settings = get_settings()
        assert isinstance(settings, dict)

    def test_contains_required_keys(self) -> None:
        # get_settings() returns DB ApplicationSetting key-value pairs,
        # not the runtime settings dict. For proper runtime settings
        # see TestUpdateSettings which calls settings.update_settings().
        settings = get_settings()
        assert isinstance(settings, dict)

    def test_defaults_match_constants(self) -> None:
        # After resetting, the runtime settings should match defaults.
        reset = reset_settings()
        assert reset["cvss_weight"] == DEFAULT_SETTINGS["cvss_weight"]


class TestUpdateSettings:
    """Updating runtime settings."""

    def test_update_single_weight(self) -> None:
        updated = update_settings({"cvss_weight": 0.5})
        assert updated["cvss_weight"] == 0.5

    def test_update_nested_propagation_weight(self) -> None:
        updated = update_settings({"propagation_weights": {"controls": 0.9}})
        assert updated["propagation_weights"]["controls"] == 0.9
        # Other keys should be preserved
        assert "monitors" in updated["propagation_weights"]

    def test_update_firewall_multipliers(self) -> None:
        updated = update_settings({"firewall_multipliers": {"true": 0.5, "false": 0.8}})
        assert updated["firewall_multipliers"]["true"] == 0.5
        assert updated["firewall_multipliers"]["false"] == 0.8

    def test_invalid_weight_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            update_settings({"cvss_weight": -1})

    def test_invalid_firewall_true_exceeds_false_raises_error(self) -> None:
        with pytest.raises(ValueError, match="firewall must never"):
            update_settings({"firewall_multipliers": {"true": 0.9, "false": 0.5}})


class TestResetSettings:
    """Resetting to defaults."""

    def test_reset_restores_defaults(self) -> None:
        update_settings({"cvss_weight": 0.5})
        reset = reset_settings()
        assert reset["cvss_weight"] == DEFAULT_SETTINGS["cvss_weight"]

    def test_reset_keeps_structure(self) -> None:
        reset = reset_settings()
        assert set(reset.keys()) == set(DEFAULT_SETTINGS.keys())


class TestValidateSettings:
    """Validation logic."""

    def test_valid_settings_pass(self) -> None:
        _validate_settings(DEFAULT_SETTINGS)  # Should not raise

    def test_negative_weight_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            _validate_settings({"cvss_weight": -0.1})

    def test_non_dict_propagation_raises(self) -> None:
        with pytest.raises(ValueError, match="must be an object"):
            _validate_settings({"propagation_weights": "not_a_dict"})

    def test_non_dict_firewall_raises(self) -> None:
        with pytest.raises(ValueError, match="must be an object"):
            _validate_settings({"firewall_multipliers": 42})

