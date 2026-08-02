"""Shared helpers for GRC & Audit API routers."""

from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.database.config import get_session_factory


def get_db():
    """FastAPI dependency that yields a session and always closes it."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def parse_date(value: str | None, field_name: str) -> date | None:
    """Parse an ISO date string into a ``date``, raising a 400 on failure."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format for '{field_name}'. Use YYYY-MM-DD.",
        ) from exc


def parse_datetime(value: str | None, field_name: str) -> datetime | None:
    """Parse an ISO datetime string into ``datetime`` (with timezone)."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid datetime format for '{field_name}'. Use ISO-8601 format.",
        ) from exc


DATE_FIELD_MAP = {
    "date": ["date", "test_date", "next_test_date", "collected_date", "valid_until",
              "last_reviewed_date", "next_review_date", "start_date", "end_date",
              "last_reviewed_date", "target_date", "approval_date", "acceptance_date",
              "expiration_date", "assessment_date", "published_date", "discovered_date",
              "detected_date", "resolved_date", "assigned_date", "extended_date",
              "completed_date", "verification_date", "closure_date", "response_date",
              "target_closure_date", "closed_date", "review_date", "due_date"],
}


def prepare_create_data(payload, date_fields: list[str] | None = None):
    """Convert a Pydantic payload to a dict with ISO date strings parsed to date/datetime.

    Returns ``(data, parsed_date_fields)`` where ``parsed_date_fields`` is the set of
    model attribute names that were converted, for any post-create handling.
    """
    data = payload.model_dump(exclude_unset=True)
    fields = date_fields or []
    for field in fields:
        if field in data:
            data[field] = parse_date(data[field], field)
    return data


def prepare_update_data(payload, date_fields: list[str] | None = None):
    """Convert an update payload, excluding unset/none values and parsing date fields."""
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    fields = date_fields or []
    for field in fields:
        if field in data:
            data[field] = parse_date(data[field], field)
    return data

