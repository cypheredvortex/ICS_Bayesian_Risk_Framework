import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

DB_DIR = Path(__file__).resolve().parents[2] / "backend" / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DB_URL = os.getenv("ICS_DB_URL", f"sqlite:///{(DB_DIR / 'ICSRiskFramework.db').as_posix()}")

_engine = None
_SessionLocal = None
_initialized = False


class Base(DeclarativeBase):
    pass


def get_db_url() -> str:
    raw_url = os.getenv("ICS_DB_URL", DEFAULT_DB_URL)
    if raw_url.startswith("sqlite"):
        normalized = raw_url.replace("\\", "/")
        if normalized.startswith("sqlite://") and not normalized.startswith("sqlite:///"):
            path_part = normalized[len("sqlite://"):]
            if not path_part.startswith("/"):
                path_part = "/" + path_part
            return f"sqlite://{path_part}"
        return normalized
    return raw_url


def _create_engine() -> object:
    db_url = get_db_url()
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    poolclass = StaticPool if db_url.startswith("sqlite") else None
    return create_engine(
        db_url,
        connect_args=connect_args,
        poolclass=poolclass,
        future=True,
    )


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        global _engine
        _engine = _create_engine()
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def dispose_engine() -> None:
    global _engine, _SessionLocal, _initialized
    if _engine is not None:
        _engine.dispose()
        _engine = None
    _SessionLocal = None
    _initialized = False


def _resolve_sqlite_path(db_url: str) -> Path | None:
    """Extract the file path from a sqlite:/// URL and ensure parent dirs exist."""
    if not db_url.startswith("sqlite"):
        return None
    normalized = db_url.replace("\\", "/")
    if normalized.startswith("sqlite:///"):
        path_part = normalized[len("sqlite:///"):]
    else:
        return None
    if not path_part:
        return None
    path = Path(path_part)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def initialize_database() -> None:
    global _initialized
    if _initialized:
        return
    db_url = get_db_url()
    logger.info("Initializing SQLite database at %s", db_url)

    # Ensure parent directory exists for SQLite databases
    _resolve_sqlite_path(db_url)

    from backend.database.models import ApplicationSetting

    factory = get_session_factory()
    Base.metadata.create_all(bind=_engine)

    with session_scope() as session:
        existing = session.query(ApplicationSetting).filter(ApplicationSetting.key == "theme").first()
        if not existing:
            session.add(ApplicationSetting(key="theme", value="light"))
            session.add(ApplicationSetting(key="export_directory", value=str(DB_DIR)))
            session.add(ApplicationSetting(key="recent_projects", value="[]"))
            session.add(ApplicationSetting(key="language", value="en"))

    _initialized = True
    logger.info("Database initialization complete")
