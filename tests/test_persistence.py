"""Tests for the database persistence layer."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import close_all_sessions

from backend.database.config import (
    dispose_engine,
    get_session_factory,
    initialize_database,
)
from backend.database.services import AssessmentPersistenceService


class PersistenceTests(unittest.TestCase):
    """Test database persistence operations."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test.db"
        os.environ["ICS_DB_URL"] = f"sqlite:///{self.db_path}"
        dispose_engine()
        initialize_database()
        self.service = AssessmentPersistenceService()

    def tearDown(self):
        try:
            close_all_sessions()
        except Exception:
            pass
        try:
            dispose_engine()
        except Exception:
            pass
        self.tmpdir.cleanup()

    def test_initialize_database_creates_missing_parent_directory(self):
        """Verify DB initialization creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_dir = Path(tmpdir) / "nested" / "subdir"
            db_path = db_dir / "custom.db"
            os.environ["ICS_DB_URL"] = f"sqlite:///{db_path}"
            dispose_engine()
            shutil.rmtree(db_dir, ignore_errors=True)

            initialize_database()

            self.assertTrue(db_path.parent.exists())
            with get_session_factory()() as session:
                self.assertEqual(
                    session.execute(text("select 1")).scalar(), 1
                )
            dispose_engine()

    def test_persist_analysis_project_and_results(self):
        """Verify full analysis persistence creates all relations."""
        topology = {
            "assets": {
                "plc_1": {
                    "kind": "device",
                    "cvss_type": 8.8,
                    "exposed": True,
                    "patched": False,
                    "consequence_severity": 5.0,
                }
            },
            "relationships": [],
        }
        analysis_result = {
            "posteriors": {"plc_1": 0.72},
            "risk_scores": [
                {"asset": "plc_1", "risk": 0.91, "risk_level": "high"}
            ],
            "summary": {"overall_risk": 0.91, "risk_level": "high"},
        }

        project = self.service.persist_analysis_run(
            topology=topology,
            evidence={"plc_1": 1},
            analysis_result=analysis_result,
            project_name="Demo Project",
            topology_source="inline",
        )

        reloaded = self.service.get_project(project.id)
        self.assertIsNotNone(reloaded)
        self.assertEqual(reloaded.name, "Demo Project")
        self.assertEqual(len(reloaded.assets), 1)
        self.assertGreaterEqual(len(reloaded.inference_results), 1)
        self.assertEqual(len(reloaded.risk_results), 1)
        self.assertEqual(len(reloaded.reports), 1)

    def test_save_and_get_settings(self):
        """Verify settings persistence round-trip."""
        setting = self.service.save_settings("test_key", "test_value")
        self.assertIsNotNone(setting)

        settings = self.service.get_settings()
        self.assertIn("test_key", settings)
        self.assertEqual(settings["test_key"], "test_value")


if __name__ == "__main__":
    unittest.main()

