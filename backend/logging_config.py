"""
Centralized logging configuration for the ICS Risk Assessment Framework.

Provides structured, production-grade logging with:
- JSON-formatted output (optional, via LOG_FORMAT=json)
- Configurable log levels via LOG_LEVEL env var
- Request context propagation via threading.local
- Automatic handler setup
"""

import json
import logging
import os
import sys
import threading
from datetime import datetime, timezone
from typing import Any

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "standard").lower()

_request_context = threading.local()


def set_request_id(request_id: str) -> None:
    """Set the current request ID for log correlation."""
    _request_context.request_id = request_id


def get_request_id() -> str | None:
    """Get the current request ID, if set."""
    return getattr(_request_context, "request_id", None)


class StructuredFormatter(logging.Formatter):
    """JSON-structured log formatter for production environments."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request ID if available
        request_id = get_request_id()
        if request_id:
            log_entry["request_id"] = request_id

        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }

        # Add extra fields from the record
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry, default=str)


class StandardFormatter(logging.Formatter):
    """Human-readable log formatter for development."""

    def format(self, record: logging.LogRecord) -> str:
        request_id = get_request_id()
        prefix = f"[{request_id}] " if request_id else ""
        return (
            f"{self.formatTime(record, '%Y-%m-%d %H:%M:%S')} "
            f"{record.levelname:8s} {prefix}{record.name}: {record.getMessage()}"
        )


def configure_logging() -> None:
    """Configure the root logger for the application.

    Call once at startup. Respects LOG_LEVEL and LOG_FORMAT env vars.
    """
    level = getattr(logging, LOG_LEVEL, logging.INFO)

    # Choose formatter based on LOG_FORMAT
    if LOG_FORMAT == "json":
        formatter = StructuredFormatter()
    else:
        formatter = StandardFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)

    # Remove any existing handlers on the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
    root_logger.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("pgmpy").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logging.info(
        "Logging configured: level=%s, format=%s",
        LOG_LEVEL,
        LOG_FORMAT,
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name, ensuring basic config exists."""
    if not logging.getLogger().handlers:
        configure_logging()
    return logging.getLogger(name)

