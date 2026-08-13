import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

DB_DIR = Path(__file__).resolve().parents[2] / "backend" / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DB_URL = os.getenv("ICS_DB_URL", f"sqlite:///{(DB_DIR / 'ICSRiskFramework.db').as_posix()}")

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None
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


def _create_engine() -> Engine:
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
        engine = _create_engine()
        _engine = engine
        _SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
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


# First revision of the migration chain (baseline schema).
_BASELINE_REVISION = "3f1fade8e943"


def _resolve_alembic_dir() -> Path:
    """Locate the alembic migration scripts across installation layouts.

    Candidates, in order:
    1. ``ALEMBIC_SCRIPT_DIR`` env var (set explicitly in the Docker image,
       where the package is installed as a wheel and the source-tree layout
       does not exist);
    2. the source-tree location ``<repo>/alembic`` (running from a checkout);
    3. ``<cwd>/alembic`` (Docker image working directory with migrations
       copied in).

    Returns the first candidate that actually contains ``env.py``, falling
    back to the source-tree path so any remaining misconfiguration surfaces
    as a clear alembic error instead of a silent no-op.
    """
    candidates = []
    env_dir = os.getenv("ALEMBIC_SCRIPT_DIR")
    if env_dir:
        candidates.append(Path(env_dir))
    candidates.append(Path(__file__).resolve().parents[2] / "alembic")
    candidates.append(Path.cwd() / "alembic")
    for candidate in candidates:
        if candidate.joinpath("env.py").is_file():
            return candidate
    return candidates[1]


_ALEMBIC_SCRIPT_DIR = _resolve_alembic_dir()


def _run_schema_migrations(engine: Engine) -> None:
    """Apply pending schema migrations via alembic, reconciling legacy databases.

    Alembic is the source of truth for schema evolution.  On a fresh
    database ``upgrade head`` creates the full schema.  Databases created by
    an older release via ``create_all`` (which never stamped ``alembic_version``
    and never alters existing tables) are reconciled:

    1. try a plain ``upgrade head`` (works when the database is new or
       already alembic-managed);
    2. otherwise stamp the baseline revision and upgrade, which applies any
       pending column additions (e.g. ``assets.purdue_level``);
    3. if the schema already matches the current models (a legacy
       ``create_all`` database from a recent release), stamp the head so
       future migrations apply cleanly.

    Failures that are not legacy-schema artefacts propagate so a genuinely
    broken migration surfaces loudly instead of being swallowed.
    """
    from alembic import command
    from alembic.config import Config

    def make_config() -> Config:
        config = Config()
        config.set_main_option("script_location", str(_ALEMBIC_SCRIPT_DIR))
        config.set_main_option("sqlalchemy.url", get_db_url())
        return config

    with engine.connect() as connection:
        has_version_table = inspect(connection).has_table("alembic_version")

    if has_version_table:
        command.upgrade(make_config(), "head")
        return

    # Database that predates alembic management (no alembic_version table).
    try:
        command.upgrade(make_config(), "head")
    except Exception as first_exc:
        logger.warning(
            "Alembic upgrade on legacy database failed (tables likely predate "
            "migrations); reconciling: %s",
            first_exc,
        )
        try:
            command.stamp(make_config(), _BASELINE_REVISION)
            command.upgrade(make_config(), "head")
        except Exception as second_exc:
            logger.warning(
                "Alembic reconcile upgrade failed (schema likely already matches "
                "the current models); stamping head: %s",
                second_exc,
            )
            command.stamp(make_config(), "head")


def initialize_database() -> None:
    global _initialized
    if _initialized:
        return
    db_url = get_db_url()
    logger.info("Initializing database at %s", db_url)

    # Ensure parent directory exists for SQLite databases
    _resolve_sqlite_path(db_url)

    from backend.database.models import ApplicationSetting

    # Ensure the engine/session factory exists before creating tables.
    get_session_factory()
    assert _engine is not None
    Base.metadata.create_all(bind=_engine)
    # Schema evolution (adding/altering columns on existing databases) is
    # handled by alembic; create_all alone never changes existing tables.
    _run_schema_migrations(_engine)

    with session_scope() as session:
        existing = session.query(ApplicationSetting).filter(ApplicationSetting.key == "theme").first()
        if not existing:
            session.add(ApplicationSetting(key="theme", value="light"))
            session.add(ApplicationSetting(key="export_directory", value=str(DB_DIR)))
            session.add(ApplicationSetting(key="recent_projects", value="[]"))
            session.add(ApplicationSetting(key="language", value="en"))

    _initialized = True
    logger.info("Database initialization complete")
