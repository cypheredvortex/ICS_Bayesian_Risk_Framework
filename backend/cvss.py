"""
cvss.py — Official CVSS v3.1 vector parsing and base-score computation.

CVSS is a *severity* scoring system, not a probability.  This module
implements the official CVSS v3.1 Base Score equations published by FIRST
(https://www.first.org/cvss/v3-1/specification-document).  It is used to:

1. Parse a CVSS v3.1 vector string (e.g. "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")
   and compute the official Base Score and severity rating.
2. Normalize an asset's vulnerability list so each entry carries a validated
   CVE identifier, vector, and score.
3. Derive the asset's *effective* CVSS score (the maximum over its
   vulnerabilities) used by the probabilistic model.

The framework NEVER invents a proprietary "CVSS formula": scores that are
not provided as a numeric override are always computed with the equations
below, which are the FIRST v3.1 specification.

Metric value weights (CVSS v3.1, Table 2-7 of the specification):
  AV (Attack Vector):       N=0.85  A=0.62  L=0.55  P=0.20
  AC (Attack Complexity):   L=0.77  H=0.44
  PR (Privileges Required): N=0.85  L=0.62  H=0.27   (scope unchanged)
                            N=0.85  L=0.68  H=0.50   (scope changed)
  UI (User Interaction):    N=0.85  R=0.62
  C/I/A (Impact):           H=0.56  L=0.22  N=0.00
"""

from __future__ import annotations

import math
import re
from typing import Any

# ---------------------------------------------------------------------------
# CVSS v3.1 metric weights
# ---------------------------------------------------------------------------

_AV = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.20}
_AC = {"L": 0.77, "H": 0.44}
_PR = {"N": 0.85, "L": 0.62, "H": 0.27}   # scope unchanged
_PR_SCOPE_CHANGED = {"N": 0.85, "L": 0.68, "H": 0.50}
_UI = {"N": 0.85, "R": 0.62}
_IMPACT = {"H": 0.56, "L": 0.22, "N": 0.00}

_VALID_METRICS = {
    "AV": set(_AV),
    "AC": set(_AC),
    "PR": set(_PR),
    "UI": set(_UI),
    "S": {"U", "C"},
    "C": set(_IMPACT),
    "I": set(_IMPACT),
    "A": set(_IMPACT),
}


class CVSSVectorError(ValueError):
    """Raised when a CVSS vector string cannot be parsed or validated."""


def _roundup(value: float) -> float:
    """Official CVSS 'Roundup' function (FIRST reference implementation).

    Returns the smallest number, specified to 1 decimal place, that is equal
    to or higher than the input.
    """
    int_input = round(value * 100000)
    if int_input % 10000 == 0:
        return int_input / 100000
    return (math.floor(int_input / 10000) + 1) / 10


def parse_cvss_vector(vector: str) -> dict[str, str]:
    """Parse a CVSS v3.1 vector string into a metric dictionary.

    Accepts both the fully qualified form ("CVSS:3.1/AV:N/...") and the bare
    metric form ("AV:N/AC:L/...").  Raises :class:`CVSSVectorError` on
    malformed or unsupported vectors (e.g. CVSS v4.0 strings).

    Args:
        vector: The vector string.

    Returns:
        A dict like {"AV": "N", "AC": "L", "PR": "N", "UI": "N",
                     "S": "U", "C": "H", "I": "H", "A": "H"}.
    """
    if not isinstance(vector, str) or not vector.strip():
        raise CVSSVectorError("CVSS vector must be a non-empty string.")

    text = vector.strip()
    # Optional version prefix.  Only v3.x (and bare vectors) are supported.
    version_prefix = None
    if text.upper().startswith("CVSS:"):
        head, sep, rest = text.partition("/")
        if not sep:
            raise CVSSVectorError(
                f"Malformed CVSS vector {vector!r}: missing '/' after version prefix."
            )
        version_prefix = head.split(":")[-1]
        if not version_prefix.startswith("3."):
            raise CVSSVectorError(
                f"Unsupported CVSS version {version_prefix!r} in {vector!r}. "
                "This framework implements the CVSS v3.1 specification. "
                "Provide a v3.x vector or a numeric score instead."
            )
        text = rest

    metrics: dict[str, str] = {}
    for token in text.split("/"):
        token = token.strip()
        if not token:
            continue
        if ":" not in token:
            raise CVSSVectorError(
                f"Malformed CVSS vector {vector!r}: token {token!r} has no ':'."
            )
        key, _, value = token.partition(":")
        key = key.strip().upper()
        value = value.strip().upper()
        if key not in _VALID_METRICS:
            raise CVSSVectorError(
                f"Unknown CVSS metric {key!r} in {vector!r}. Valid metrics: "
                "AV, AC, PR, UI, S, C, I, A."
            )
        if value not in _VALID_METRICS[key]:
            raise CVSSVectorError(
                f"Invalid value {value!r} for metric {key} in {vector!r}. "
                f"Allowed: {sorted(_VALID_METRICS[key])}."
            )
        metrics[key] = value

    missing = set(_VALID_METRICS) - set(metrics)
    if missing:
        raise CVSSVectorError(
            f"Incomplete CVSS vector {vector!r}: missing metrics {sorted(missing)}."
        )
    return metrics


def compute_base_score(metrics: dict[str, str]) -> float:
    """Compute the CVSS v3.1 Base Score from a parsed metric dictionary.

    Implements equations 1-4 of the FIRST CVSS v3.1 specification:

        ISS  = 1 - (1 - C)(1 - I)(1 - A)                         (eq. 1)
        Impact (scope unchanged) = 6.42 * ISS                    (eq. 2a)
        Impact (scope changed)   = 7.52*(ISS-0.029) - 3.25*(ISS-0.02)^15
        Exploitability = 8.22 * AV * AC * PR * UI                (eq. 3)
        Base (scope unchanged) = Roundup(min(Impact + Exploitability, 10))
        Base (scope changed)   = Roundup(min(1.08*(Impact + Exploitability), 10))

    Args:
        metrics: Parsed metric dict (see :func:`parse_cvss_vector`).

    Returns:
        The official Base Score in [0.0, 10.0].
    """
    required = set(_VALID_METRICS)
    if set(metrics) != required:
        raise CVSSVectorError(
            f"compute_base_score requires all metrics {sorted(required)}, "
            f"got {sorted(metrics)}."
        )

    iss = 1.0 - (
        (1.0 - _IMPACT[metrics["C"]])
        * (1.0 - _IMPACT[metrics["I"]])
        * (1.0 - _IMPACT[metrics["A"]])
    )

    if metrics["S"] == "U":
        impact = 6.42 * iss
        pr_weight = _PR[metrics["PR"]]
    else:
        impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15
        pr_weight = _PR_SCOPE_CHANGED[metrics["PR"]]

    exploitability = (
        8.22
        * _AV[metrics["AV"]]
        * _AC[metrics["AC"]]
        * pr_weight
        * _UI[metrics["UI"]]
    )

    if metrics["S"] == "U":
        base = _roundup(min(impact + exploitability, 10.0))
    else:
        base = _roundup(min(1.08 * (impact + exploitability), 10.0))
    return round(base, 1)


def base_score_from_vector(vector: str) -> float:
    """Parse a vector string and return its official CVSS v3.1 Base Score."""
    return compute_base_score(parse_cvss_vector(vector))


def severity_rating(score: float) -> str:
    """Map a CVSS v3.1 Base Score to its qualitative severity rating."""
    score = float(score)
    if score >= 9.0:
        return "Critical"
    if score >= 7.0:
        return "High"
    if score >= 4.0:
        return "Medium"
    if score > 0.0:
        return "Low"
    return "None"


# ---------------------------------------------------------------------------
# Asset vulnerability normalization
# ---------------------------------------------------------------------------

_CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,7}$", re.IGNORECASE)


def _parse_score(value: Any, context: str) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{context}: vulnerability score must be a number, got {value!r}.") from None
    if not (0.0 <= score <= 10.0):
        raise ValueError(f"{context}: vulnerability score must be in [0, 10], got {score}.")
    return score


def normalize_vulnerability(raw: Any, context: str) -> dict[str, Any]:
    """Normalize a single vulnerability entry.

    Accepted forms:
      - a string: a CVSS v3.1 vector ("CVSS:3.1/AV:N/...")
      - a dict:   {"cve_id": "...", "vector": "...", "score": 8.8,
                   "source": "analyst-supplied"}

    When a vector is provided it is authoritative: the official Base Score is
    computed from it.  A numeric score is used only when no vector is given.

    ``source`` is descriptive provenance metadata ONLY.  It is preserved
    verbatim and never used to fetch data: this framework does NOT retrieve
    vulnerability data from NVD or any other service.  Vulnerability records
    are analyst-supplied; ``source`` documents where the analyst obtained
    them (e.g. "analyst-supplied", "NVD reference", "vendor advisory").
    """
    vuln: dict[str, Any] = {}
    if isinstance(raw, str):
        vector = raw.strip()
        if vector.upper().startswith("CVSS:"):
            vuln["vector"] = vector
        else:
            raise ValueError(
                f"{context}: vulnerability string {raw!r} is not a CVSS v3.1 vector. "
                "Use the form 'CVSS:3.1/AV:...' or provide a dict with a score."
            )
    elif isinstance(raw, dict):
        cve_id = raw.get("cve_id") or raw.get("cve") or raw.get("id")
        if cve_id:
            cve_id_text = str(cve_id).strip()
            if not _CVE_RE.match(cve_id_text):
                raise ValueError(
                    f"{context}: invalid CVE identifier {cve_id_text!r}. Expected 'CVE-YYYY-NNNN'."
                )
            vuln["cve_id"] = cve_id_text.upper()
        vector_raw = raw.get("vector") or raw.get("cvss_vector") or raw.get("cvss3_vector")
        score = raw.get("score", raw.get("cvss_score", raw.get("cvss", raw.get("base_score"))))
        if vector_raw:
            vuln["vector"] = str(vector_raw).strip()
        elif score is not None:
            vuln["score"] = _parse_score(score, context)
        else:
            raise ValueError(
                f"{context}: each vulnerability must provide a 'vector' or a 'score'."
            )
        source = raw.get("source") or raw.get("data_source") or raw.get("feed")
        if source:
            vuln["source"] = str(source).strip()
    else:
        raise ValueError(
            f"{context}: vulnerability entries must be strings (CVSS vectors) or dicts, "
            f"got {type(raw).__name__}."
        )

    if "vector" in vuln:
        try:
            vuln["score"] = base_score_from_vector(vuln["vector"])
        except CVSSVectorError as exc:
            raise ValueError(f"{context}: {exc}") from exc
    return vuln


def normalize_vulnerabilities(raw_vulns: Any, context: str) -> list[dict[str, Any]]:
    """Normalize an asset's vulnerability list and return validated entries."""
    if raw_vulns is None:
        return []
    if not isinstance(raw_vulns, list):
        raise ValueError(f"{context}: 'vulnerabilities' must be a list, got {type(raw_vulns).__name__}.")
    return [normalize_vulnerability(item, context) for item in raw_vulns]


def effective_cvss_score(vulnerabilities: list[dict[str, Any]]) -> float:
    """Return the maximum Base Score over the asset's vulnerabilities.

    An asset is only as strong as its weakest (i.e. most severe) exposed
    vulnerability; the effective score drives the intrinsic compromise
    probability model.
    """
    if not vulnerabilities:
        return 0.0
    return max(float(v["score"]) for v in vulnerabilities)
