"""
tests/test_impossible_evidence.py - Impossible and contradictory evidence.

The framework must never silently display a normal-looking result for
evidence that is impossible under the model.  This file verifies:

* zero-probability evidence (physical asset with p_base_override=0 asserted
  compromised while nothing can raise its probability) is rejected with a
  structured IMPOSSIBLE_EVIDENCE diagnostic;
* contradictory duplicate evidence (same asset, two different states) is
  rejected with a clear message;
* valid evidence continues to work end-to-end.
"""

from fastapi.testclient import TestClient

from backend.api import app

client = TestClient(app, raise_server_exceptions=False)


def _topology_with_physical_zero():
    return {
        "assets": {
            "valve": {
                "kind": "physical",
                "p_base_override": 0.0,
                "consequence_severity": 8.0,
            }
        },
        "relationships": [],
    }


def _topology_with_device():
    return {
        "assets": {
            "plc_1": {
                "kind": "device",
                "cvss_type": 5.0,
                "exposed": True,
                "patched": False,
                "consequence_severity": 5.0,
            }
        },
        "relationships": [],
    }


def test_impossible_evidence_returns_structured_400():
    response = client.post(
        "/analyze",
        json={
            "topology": _topology_with_physical_zero(),
            "evidence": [{"asset": "valve", "state": "Compromised"}],
        },
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "IMPOSSIBLE_EVIDENCE"
    assert body["affected_nodes"] == ["valve"]
    assert "impossible" in body["detail"].lower()
    assert body["affected_nodes"]


def test_possible_evidence_on_same_asset_works():
    # The same zero-base asset asserted *safe* (state 0) is perfectly valid.
    response = client.post(
        "/analyze",
        json={
            "topology": _topology_with_physical_zero(),
            "evidence": [{"asset": "valve", "state": "Safe"}],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["posteriors"]["valve"] == 0.0


def test_contradictory_duplicate_evidence_rejected():
    response = client.post(
        "/analyze",
        json={
            "topology": _topology_with_device(),
            "evidence": [
                {"asset": "plc_1", "state": "Compromised"},
                {"asset": "plc_1", "state": "Safe"},
            ],
        },
    )
    assert response.status_code == 400
    body = response.json()
    assert "Contradictory evidence" in body["detail"]
    assert "plc_1" in body["detail"]


def test_duplicate_identical_evidence_is_fine():
    # Duplicate entries with the *same* state are harmless.
    response = client.post(
        "/analyze",
        json={
            "topology": _topology_with_device(),
            "evidence": [
                {"asset": "plc_1", "state": "Compromised"},
                {"asset": "plc_1", "state": 1},
            ],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["posteriors"]["plc_1"] == 1.0


def test_zero_probability_evidence_via_cli_raises():
    from backend.cli import run
    from backend.inference import ImpossibleEvidenceError

    try:
        run(
            _topology_with_physical_zero(),
            evidence={"valve": 1},
            persist=False,
        )
        raise AssertionError("Expected ImpossibleEvidenceError")
    except ImpossibleEvidenceError as exc:
        assert exc.affected_nodes == ["valve"]


def test_normal_evidence_end_to_end():
    response = client.post(
        "/analyze",
        json={
            "topology": _topology_with_device(),
            "evidence": [{"asset": "plc_1", "state": "Compromised"}],
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["posteriors"]["plc_1"] == 1.0
    # Normal-looking results are produced, not zero-valued diagnostics.
    assert data["summary"]["overall_risk"] > 0
