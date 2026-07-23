"""Tests for the intrinsic probability computation module."""

import pytest

from backend.probability import base_prob, compute_base_probs, _device_base_prob, _human_base_prob, _physical_base_prob


class TestDeviceBaseProb:
    """CVSS-driven device probability."""

    def test_low_cvss_high_patch_returns_low_probability(self) -> None:
        attrs = {"kind": "device", "cvss_type": "2.0", "exposed": False, "patched": True}
        prob = _device_base_prob(attrs)
        assert 0 <= prob <= 0.95

    def test_high_cvss_unpatched_exposed_returns_high_probability(self) -> None:
        attrs = {"kind": "device", "cvss_type": "9.5", "exposed": True, "patched": False}
        prob = _device_base_prob(attrs)
        assert prob > 0.5

    def test_cvss_zero_returns_zero_base(self) -> None:
        attrs = {"kind": "device", "cvss_type": "0.0", "exposed": False, "patched": True}
        prob = _device_base_prob(attrs)
        assert prob == pytest.approx(0.0, abs=1e-10)


class TestHumanBaseProb:
    """Role/awareness/privilege-driven human probability."""

    def test_operator_low_awareness_returns_moderate_probability(self) -> None:
        attrs = {"kind": "human", "role": "operator", "awareness": 0.3, "privilege": "standard"}
        prob = _human_base_prob(attrs)
        assert 0 < prob < 0.5

    def test_admin_high_awareness_returns_low_probability(self) -> None:
        attrs = {"kind": "human", "role": "admin", "awareness": 0.9, "privilege": "admin"}
        prob = _human_base_prob(attrs)
        assert prob < 0.1

    def test_guest_elevated_returns_highest_probability(self) -> None:
        attrs = {"kind": "human", "role": "guest", "awareness": 0.1, "privilege": "elevated"}
        prob = _human_base_prob(attrs)
        assert prob > 0.5


class TestPhysicalBaseProb:
    """Physical process probability uses override value."""

    def test_override_value_returned(self) -> None:
        attrs = {"kind": "physical", "p_base_override": 0.42}
        prob = _physical_base_prob(attrs)
        assert prob == 0.42

    def test_missing_override_returns_zero(self) -> None:
        attrs = {"kind": "physical"}
        prob = _physical_base_prob(attrs)
        assert prob == 0.0


class TestBaseProb:
    """Top-level dispatch function."""

    def test_device_kind_dispatches_to_device(self) -> None:
        attrs = {"kind": "device", "cvss_type": "5.0", "exposed": False, "patched": True}
        prob = base_prob("PLC_01", attrs)
        assert 0 <= prob <= 0.95

    def test_human_kind_dispatches_to_human(self) -> None:
        attrs = {"kind": "human", "role": "engineer", "awareness": 0.5, "privilege": "standard"}
        prob = base_prob("Operator_01", attrs)
        assert 0 <= prob <= 0.95

    def test_physical_kind_dispatches_to_physical(self) -> None:
        attrs = {"kind": "physical", "p_base_override": 0.15}
        prob = base_prob("Tank_01", attrs)
        assert prob == 0.15

    def test_unknown_kind_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown kind"):
            base_prob("BadNode", {"kind": "unknown"})

    def test_probability_capped_at_p_base_cap(self) -> None:
        attrs = {"kind": "human", "role": "guest", "awareness": 0.0, "privilege": "admin"}
        prob = base_prob("Guest_01", attrs)
        assert prob <= 0.95


class TestComputeBaseProbs:
    """Batch computation across all assets."""

    def test_returns_dict_with_all_assets(self) -> None:
        assets = {
            "PLC_01": {"kind": "device", "cvss_type": "5.0", "exposed": False, "patched": True},
            "Operator_01": {"kind": "human", "role": "operator", "awareness": 0.5, "privilege": "standard"},
            "Tank_01": {"kind": "physical", "p_base_override": 0.1},
        }
        result = compute_base_probs(assets)
        assert set(result.keys()) == {"PLC_01", "Operator_01", "Tank_01"}
        for node_id, prob in result.items():
            assert 0 <= prob <= 0.95, f"{node_id} probability {prob} out of range"

    def test_empty_assets_returns_empty_dict(self) -> None:
        assert compute_base_probs({}) == {}

    def test_invalid_asset_raises_error(self) -> None:
        with pytest.raises(ValueError):
            compute_base_probs({"BadNode": {"kind": "invalid"}})

