"""
tests/test_cvss.py - Verification of the official CVSS v3.1 implementation.

The vectors below are published examples whose Base Scores are documented
in the FIRST CVSS v3.1 specification and on NVD entries for the referenced
CVEs.
"""

import pytest

from backend.cvss import (
    CVSSVectorError,
    base_score_from_vector,
    compute_base_score,
    effective_cvss_score,
    normalize_vulnerabilities,
    parse_cvss_vector,
    severity_rating,
)

# (vector, expected official base score)
PUBLISHED_VECTORS = [
    # CVE-2014-0160 (Heartbleed) - 7.5
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N", 7.5),
    # CVE-2021-44228 (Log4Shell) - 10.0
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H", 10.0),
    # CVE-2014-6271 (Shellshock) - 9.8
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", 9.8),
    # Common generic vectors
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N", 5.3),
    ("CVSS:3.1/AV:A/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", 8.8),
    ("CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:L/A:N", 5.4),
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N", 6.1),
]


@pytest.mark.parametrize("vector,expected", PUBLISHED_VECTORS)
def test_base_score_matches_published_values(vector, expected):
    assert base_score_from_vector(vector) == pytest.approx(expected, abs=1e-9)


def test_parse_cvss_vector():
    metrics = parse_cvss_vector("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")
    assert metrics == {
        "AV": "N", "AC": "L", "PR": "N", "UI": "N",
        "S": "U", "C": "H", "I": "H", "A": "H",
    }


def test_parse_cvss_vector_without_prefix():
    metrics = parse_cvss_vector("AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")
    assert metrics["AV"] == "N"


def test_compute_base_score_requires_all_metrics():
    with pytest.raises(CVSSVectorError, match="requires all metrics"):
        compute_base_score({"AV": "N", "AC": "L"})


def test_invalid_metric_value_rejected():
    with pytest.raises(CVSSVectorError, match="Invalid value"):
        base_score_from_vector("CVSS:3.1/AV:X/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")


def test_unknown_metric_rejected():
    with pytest.raises(CVSSVectorError, match="Unknown CVSS metric"):
        base_score_from_vector("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H/XX:L")


def test_incomplete_vector_rejected():
    with pytest.raises(CVSSVectorError, match="missing metrics"):
        base_score_from_vector("CVSS:3.1/AV:N/AC:L")


def test_cvss_v4_vector_rejected_with_guidance():
    with pytest.raises(CVSSVectorError, match="CVSS v3.1 specification"):
        base_score_from_vector("CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H")


def test_empty_vector_rejected():
    with pytest.raises(CVSSVectorError):
        base_score_from_vector("  ")


def test_severity_rating():
    assert severity_rating(9.0) == "Critical"
    assert severity_rating(7.0) == "High"
    assert severity_rating(4.0) == "Medium"
    assert severity_rating(0.1) == "Low"
    assert severity_rating(0.0) == "None"


def test_normalize_vulnerabilities_from_vectors():
    vulns = normalize_vulnerabilities(
        ["CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N"], "asset-x"
    )
    assert vulns[0]["score"] == pytest.approx(7.5)
    assert "vector" in vulns[0]


def test_normalize_vulnerabilities_with_cve_and_score():
    vulns = normalize_vulnerabilities(
        [{"cve_id": "CVE-2021-44228", "score": 9.5, "source": "analyst-supplied"}], "asset-x"
    )
    assert vulns[0]["cve_id"] == "CVE-2021-44228"
    assert vulns[0]["score"] == 9.5
    # source is descriptive metadata only; it is preserved, never fetched.
    assert vulns[0]["source"] == "analyst-supplied"


def test_normalize_vulnerabilities_vector_is_authoritative():
    # When a vector is present it wins over any provided numeric score.
    vulns = normalize_vulnerabilities(
        [{"vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N", "score": 1.0}], "asset-x"
    )
    assert vulns[0]["score"] == pytest.approx(7.5)


def test_normalize_vulnerabilities_invalid_cve_rejected():
    with pytest.raises(ValueError, match="invalid CVE identifier"):
        normalize_vulnerabilities([{"cve_id": "CVE-999", "score": 5.0}], "asset-x")


def test_normalize_vulnerabilities_score_out_of_range_rejected():
    with pytest.raises(ValueError, match="must be in \\[0, 10\\]"):
        normalize_vulnerabilities([{"score": 11.0}], "asset-x")


def test_normalize_vulnerabilities_non_list_rejected():
    with pytest.raises(ValueError, match="must be a list"):
        normalize_vulnerabilities({"cve_id": "CVE-2014-0160"}, "asset-x")


def test_effective_score_is_maximum():
    vulns = normalize_vulnerabilities(
        [
            {"cve_id": "CVE-2014-0160", "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N"},
            {"cve_id": "CVE-2021-44228", "score": 9.5},
        ],
        "asset-x",
    )
    assert effective_cvss_score(vulns) == pytest.approx(9.5)


def test_effective_score_empty_is_zero():
    assert effective_cvss_score([]) == 0.0
