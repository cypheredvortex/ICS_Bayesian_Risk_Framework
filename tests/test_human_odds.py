
from backend.probability import _human_base_prob


def test_awareness_reduces_probability():
    attrs_low = {"kind": "human", "role": "operator", "awareness": 0.1, "privilege": "standard"}
    attrs_high = {"kind": "human", "role": "operator", "awareness": 0.9, "privilege": "standard"}
    p_low = _human_base_prob(attrs_low)
    p_high = _human_base_prob(attrs_high)
    assert p_high <= p_low


def test_privilege_increases_probability():
    attrs_standard = {"kind": "human", "role": "operator", "awareness": 0.5, "privilege": "standard"}
    attrs_admin = {"kind": "human", "role": "operator", "awareness": 0.5, "privilege": "admin"}
    p_std = _human_base_prob(attrs_standard)
    p_admin = _human_base_prob(attrs_admin)
    assert p_admin >= p_std
