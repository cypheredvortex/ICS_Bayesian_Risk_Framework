
from backend.probability import _device_base_prob


def test_exposure_increases_probability():
    attrs_low = {"kind": "device", "cvss_type": "5.0", "exposed": False, "patched": True}
    attrs_high = {"kind": "device", "cvss_type": "5.0", "exposed": True, "patched": True}
    p_low = _device_base_prob(attrs_low)
    p_high = _device_base_prob(attrs_high)
    assert p_high >= p_low


def test_unpatched_increases_probability():
    attrs_patched = {"kind": "device", "cvss_type": "5.0", "exposed": True, "patched": True}
    attrs_unpatched = {"kind": "device", "cvss_type": "5.0", "exposed": True, "patched": False}
    p_patched = _device_base_prob(attrs_patched)
    p_unpatched = _device_base_prob(attrs_unpatched)
    assert p_unpatched >= p_patched


def test_zero_cvss_returns_small_nonzero():
    # The calibrated logistic mapping never yields exactly 0: even a CVSS-0
    # asset carries residual compromise risk (unknown vulnerabilities).
    attrs = {"kind": "device", "cvss_type": "0.0", "exposed": True, "patched": False}
    p = _device_base_prob(attrs)
    assert 0.0 < p < 0.1
