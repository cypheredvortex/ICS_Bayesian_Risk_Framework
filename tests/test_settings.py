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

    def test_defaults_match_constants(self) -> None:
        # After resetting, the runtime settings should match defaults.
        reset = reset_settings()
        assert reset == DEFAULT_SETTINGS


class TestUpdateSettings:
    """Updating runtime settings."""

    def test_update_single_weight(self) -> None:
        updated = update_settings({"exposure_weight": 0.5})
        assert updated["exposure_weight"] == 0.5

    def test_update_nested_propagation_weight(self) -> None:
        updated = update_settings({"propagation_weights": {"controls": 0.9}})
        assert updated["propagation_weights"]["controls"] == 0.9
        # Other keys should be preserved
        assert "monitors" in updated["propagation_weights"]

    def test_update_firewall_multipliers(self) -> None:
        updated = update_settings({"firewall_multipliers": {"true": 0.5, "false": 0.8}})
        assert updated["firewall_multipliers"]["true"] == 0.5
        assert updated["firewall_multipliers"]["false"] == 0.8

    def test_update_cvss_mapping(self) -> None:
        updated = update_settings({"cvss_mapping": "linear"})
        assert updated["cvss_mapping"] == "linear"

    def test_invalid_weight_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            update_settings({"exposure_weight": -1})

    def test_invalid_firewall_true_exceeds_false_raises_error(self) -> None:
        with pytest.raises(ValueError, match="firewall must never"):
            update_settings({"firewall_multipliers": {"true": 0.9, "false": 0.5}})

    def test_invalid_cvss_mapping_raises(self) -> None:
        with pytest.raises(ValueError, match="'cvss_mapping' must be"):
            update_settings({"cvss_mapping": "exponential"})

    def test_invalid_logistic_params_raise(self) -> None:
        with pytest.raises(ValueError, match="'cvss_logistic_params.k' must be a positive number"):
            update_settings({"cvss_logistic_params": {"k": 0}})
        with pytest.raises(ValueError, match="'cvss_logistic_params.x0' must be in \\[0, 10\\]"):
            update_settings({"cvss_logistic_params": {"x0": 12}})


class TestPersistenceRoundTrip:
    """Regression: complex (dict) settings are stored as JSON in the DB and
    must be JSON-decoded on read (_parse_db_value). Previously
    ``cvss_logistic_params`` came back as its raw JSON string, breaking the
    probability model."""

    def test_dict_setting_round_trips_through_db(self) -> None:
        update_settings({"cvss_logistic_params": {"k": 1.2, "x0": 4.5}})
        try:
            settings = get_settings()
            assert isinstance(settings["cvss_logistic_params"], dict)
            assert settings["cvss_logistic_params"] == {"k": 1.2, "x0": 4.5}
        finally:
            reset_settings()

    def test_table_setting_round_trips_through_db(self) -> None:
        update_settings({"propagation_weights": {"controls": 0.55}})
        try:
            settings = get_settings()
            assert isinstance(settings["propagation_weights"], dict)
            assert settings["propagation_weights"]["controls"] == 0.55
            assert settings["propagation_weights"]["connects-to"] == pytest.approx(0.5)
        finally:
            reset_settings()

    def test_scalar_setting_round_trips_through_db(self) -> None:
        update_settings({"impact_weight": 1.25})
        try:
            settings = get_settings()
            assert isinstance(settings["impact_weight"], float)
            assert settings["impact_weight"] == pytest.approx(1.25)
        finally:
            reset_settings()


class TestResetSettings:
    """Resetting to defaults."""

    def test_reset_restores_defaults(self) -> None:
        update_settings({"exposure_weight": 0.5})
        reset = reset_settings()
        assert reset["exposure_weight"] == DEFAULT_SETTINGS["exposure_weight"]

    def test_reset_keeps_structure(self) -> None:
        reset = reset_settings()
        assert set(reset.keys()) == set(DEFAULT_SETTINGS.keys())


class TestValidateSettings:
    """Validation logic."""

    def test_valid_settings_pass(self) -> None:
        _validate_settings(DEFAULT_SETTINGS)  # Should not raise

    def test_negative_weight_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            _validate_settings({"exposure_weight": -0.1})

    def test_non_dict_propagation_raises(self) -> None:
        with pytest.raises(ValueError, match="must be an object"):
            _validate_settings({"propagation_weights": "not_a_dict"})

    def test_non_dict_firewall_raises(self) -> None:
        with pytest.raises(ValueError, match="must be an object"):
            _validate_settings({"firewall_multipliers": 42})
