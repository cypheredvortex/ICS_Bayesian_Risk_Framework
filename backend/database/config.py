import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from alembic import command
from alembic.config import Config
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


def _run_alembic_migrations(db_url: str) -> None:
    """Run Alembic migrations to bring the database schema up to date."""
    try:
        alembic_cfg = Config(Path(__file__).resolve().parents[2] / "alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully")
    except Exception as exc:
        logger.warning("Alembic migration failed (%s), falling back to create_all", exc)
        # Fallback: if alembic hasn't been initialized yet, use create_all.
        # The session factory stores the bound engine in its kw arguments.
        from backend.database.models import Base as ModelsBase
        fallback_engine = get_session_factory().kw.get("bind")
        ModelsBase.metadata.create_all(bind=fallback_engine)


# Default system roles seeded on first init. These align with the navigation
# structure and permission model used across the GRC platform.
DEFAULT_ROLES = [
    {"name": "admin", "description": "Full platform administration and configuration access", "is_system_role": True},
    {"name": "auditor", "description": "Audit program execution, findings, and evidence management", "is_system_role": True},
    {"name": "risk_manager", "description": "Risk register, treatment plans, and risk acceptance", "is_system_role": True},
    {"name": "compliance_officer", "description": "Compliance framework mapping and gap analysis", "is_system_role": True},
    {"name": "analyst", "description": "Bayesian assessment and asset/vulnerability analysis", "is_system_role": True},
    {"name": "viewer", "description": "Read-only access to all GRC modules", "is_system_role": True},
]

# Compliance frameworks seeded so the Compliance module has meaningful content
# immediately after first initialization.
DEFAULT_FRAMEWORKS = [
    {"name": "ISO 27001", "version": "2022", "publisher": "ISO/IEC", "domain": "information_security",
     "description": "International standard for information security management systems (ISMS)."},
    {"name": "NIST CSF", "version": "2.0", "publisher": "NIST", "domain": "cybersecurity",
     "description": "NIST Cybersecurity Framework covering Identify, Protect, Detect, Respond, Recover."},
    {"name": "IEC 62443", "version": "2023", "publisher": "IEC", "domain": "ics_security",
     "description": "Industrial automation and control systems (IACS) security standard."},
    {"name": "CIS Controls", "version": "8.1", "publisher": "CIS", "domain": "cybersecurity",
     "description": "Center for Internet Security Critical Security Controls."},
]


def _seed_default_data() -> None:
    """Seed default roles and compliance frameworks on first init."""
    from backend.database.models import ComplianceFramework, Role

    with session_scope() as session:
        for role_data in DEFAULT_ROLES:
            existing = session.query(Role).filter(Role.name == role_data["name"]).first()
            if not existing:
                session.add(Role(**role_data))

        for framework_data in DEFAULT_FRAMEWORKS:
            existing = (
                session.query(ComplianceFramework)
                .filter(
                    ComplianceFramework.name == framework_data["name"],
                    ComplianceFramework.version == framework_data["version"],
                )
                .first()
            )
            if not existing:
                session.add(ComplianceFramework(**framework_data))


def initialize_database() -> None:
    global _initialized
    if _initialized:
        return
    db_url = get_db_url()
    logger.info("Initializing SQLite database at %s", db_url)

    # Ensure parent directory exists for SQLite databases
    _resolve_sqlite_path(db_url)

    from backend.database.models import ApplicationSetting

    # Run Alembic migrations instead of raw create_all to maintain
    # proper migration history and enable rollback.
    _run_alembic_migrations(db_url)

    with session_scope() as session:
        existing = session.query(ApplicationSetting).filter(ApplicationSetting.key == "theme").first()
        if not existing:
            session.add(ApplicationSetting(key="theme", value="light"))
            session.add(ApplicationSetting(key="export_directory", value=str(DB_DIR)))
            session.add(ApplicationSetting(key="recent_projects", value="[]"))
            session.add(ApplicationSetting(key="language", value="en"))

    # Seed default roles and compliance frameworks (idempotent).
    _seed_default_data()

    _initialized = True
    logger.info("Database initialization complete")
