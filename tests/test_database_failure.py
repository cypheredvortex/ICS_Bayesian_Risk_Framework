"""
tests/test_database_failure.py - Behaviour when the persistence layer fails.

The API must keep serving the assessment pipeline and return *controlled*
errors (no raw tracebacks, no internal details) when the database is
unavailable, corrupted, or fails during writes.
"""

import os

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.api import app
from backend.database.config import dispose_engine, get_db_url


@pytest.fixture()
def client():
    return TestClient(app, raise_server_exceptions=False)


def test_health_reports_controlled_error_when_db_unavailable(client):
    """An unusable DB URL must not crash /health or leak connection details."""
    with patch.dict(os.environ, {"ICS_DB_URL": "postgresql://nouser:nopass@127.0.0.1:1/nodb"}):
        dispose_engine()
        response = client.get("/")
        dispose_engine()
    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "error"
    # No raw connection internals leak into the response.
    assert "nouser" not in body["database"]
    assert "127.0.0.1" not in body["database"]


def test_settings_read_degrades_gracefully_when_db_unavailable(client):
    """With the database down, settings degrade to in-memory defaults so the
    rest of the application keeps working -- with no internal detail leaked."""
    with patch.dict(os.environ, {"ICS_DB_URL": "postgresql://nouser:nopass@127.0.0.1:1/nodb"}):
        dispose_engine()
        response = client.get("/settings")
        dispose_engine()
    assert response.status_code == 200
    body = response.json()
    assert body["cvss_logistic_params"] == {"k": 0.8, "x0": 5.0}
    assert "traceback" not in response.text.lower()
    assert "127.0.0.1" not in response.text


def test_analyze_still_works_when_persistence_fails(client):
    """A failing persistence layer must not break the assessment itself:
    the pipeline result is still returned and the failure is recorded."""
    topology = {
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
    with patch("backend.cli.AssessmentPersistenceService.persist_analysis_run", side_effect=RuntimeError("db is gone")):
        response = client.post("/analyze", json={"topology": topology, "evidence": []})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["posteriors"]["plc_1"] >= 0
    assert data["persistence"]["saved"] is False


def test_settings_write_failure_returns_400_with_message(client):
    """A persistence failure while saving settings surfaces a 400 with the
    actionable message, not a traceback."""
    with patch("backend.settings.AssessmentPersistenceService.save_settings", side_effect=RuntimeError("disk full")):
        response = client.put("/settings", json={"settings": {"impact_weight": 1.5}})
    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "HTTP_400"
    assert "disk full" in body["detail"]
    assert "traceback" not in response.text.lower()


def test_corrupted_sqlite_database_degrades_gracefully(client, tmp_path):
    """A corrupted SQLite file must not break settings: the API degrades to
    in-memory defaults with a controlled response (no driver internals)."""
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"this is not a sqlite database at all....")
    with patch.dict(os.environ, {"ICS_DB_URL": f"sqlite:///{corrupt}"}):
        dispose_engine()
        response = client.get("/settings")
        dispose_engine()
    assert response.status_code == 200
    assert response.json()["risk_thresholds"]["critical"] == 0.75
    # The raw driver error must never be exposed.
    assert "file is not a database" not in response.text


def test_pipeline_reports_persistence_failure_on_corrupt_db(tmp_path):
    """cli.run records persistence failure instead of crashing when the
    database is unusable -- and the analysis itself still completes."""
    from backend.cli import run

    corrupt = tmp_path / "corrupt2.db"
    corrupt.write_bytes(b"not a sqlite file")
    with patch.dict(os.environ, {"ICS_DB_URL": f"sqlite:///{corrupt}"}):
        dispose_engine()
        topology = {
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
        result = run(topology, evidence={}, write_outputs=False, persist=True)
        dispose_engine()
    assert result["persistence"]["saved"] is False
    assert "posteriors" in result
    assert len(result["posteriors"]) == 1


def test_get_db_url_normalizes_sqlite_paths():
    url = get_db_url()
    assert isinstance(url, str) and url
