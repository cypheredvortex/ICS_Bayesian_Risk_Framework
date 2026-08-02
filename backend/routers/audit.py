"""API router for Audit Log management."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database.repositories import AuditLogRepository
from backend.routers.common import get_db
from backend.schemas import AuditLogResponse, AuditLogListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/audit-logs", tags=["Audit Log"])


@router.get("/", response_model=AuditLogListResponse)
def list_audit_logs(
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: int | None = Query(None, description="Filter by entity ID"),
    limit: int = Query(100, description="Maximum number of logs to return", ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List audit logs, optionally filtered by entity type and ID."""
    repo = AuditLogRepository(db)
    if entity_type and entity_id is not None:
        logs = repo.list_for_entity(entity_type, entity_id)
    elif entity_type:
        logs = [log for log in repo.list_all() if log.entity_type == entity_type]
    else:
        logs = repo.list_all()
    # Sort by created_at descending and limit
    logs = sorted(logs, key=lambda log: log.created_at, reverse=True)[:limit]
    return AuditLogListResponse(
        total=len(logs),
        logs=[AuditLogResponse.model_validate(log) for log in logs],
    )


@router.get("/{log_id}", response_model=AuditLogResponse)
def get_audit_log(log_id: int, db: Session = Depends(get_db)):
    """Get a specific audit log entry."""
    repo = AuditLogRepository(db)
    log_entry = repo.get_by_id(log_id)
    if not log_entry:
        raise HTTPException(status_code=404, detail="Audit log entry not found.")
    return AuditLogResponse.model_validate(log_entry)
