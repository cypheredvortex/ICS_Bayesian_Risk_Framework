"""
Shared test fixtures and configuration for the ICS Risk Framework test suite.

All tests automatically use a temporary SQLite database to avoid
side effects on the development or production database.
"""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from backend.database.config import dispose_engine, initialize_database


@pytest.fixture(autouse=True)
def temp_db() -> Generator[None, None, None]:
    """Replace the database with a temporary file for each test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        old_db_url = os.environ.get("ICS_DB_URL")
        os.environ["ICS_DB_URL"] = f"sqlite:///{db_path}"
        dispose_engine()
        initialize_database()
        yield
        dispose_engine()
        if old_db_url is not None:
            os.environ["ICS_DB_URL"] = old_db_url
        else:
            del os.environ["ICS_DB_URL"]

