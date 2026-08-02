"""API router for Corrective Actions (CAPA) management."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database.repositories import (
    ActionTaskRepository, CorrectiveActionRepository,
    EffectivenessReviewRepository,
)
from backend.routers.common import get_db, prepare_create_data, prepare_update_data
from backend.security import get_current_user, require_module_access
from backend.schemas import (
    ActionTaskCreate, ActionTaskResponse, ActionTaskUpdate,
    CorrectiveActionCreate, CorrectiveActionResponse,
    CorrectiveActionUpdate, EffectivenessReviewCreate,
    EffectivenessReviewResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/capa",
    tags=["Corrective Actions"],
    dependencies=[Depends(get_current_user)],
)

ACTION_DATE_FIELDS = ["assigned_date", "target_date", "extended_date", "verification_date"]
TASK_DATE_FIELDS = ["due_date", "completed_date"]
REVIEW_DATE_FIELDS = ["review_date"]


# ═══════════════════════════════════════════════════════════════
# Corrective Action Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/actions", response_model=list[CorrectiveActionResponse])
def list_corrective_actions(
    finding_id: int | None = Query(None, description="Filter by finding ID"),
    risk_item_id: int | None = Query(None, description="Filter by risk item ID"),
    status: str | None = Query(None, description="Filter by status"),
    open_only: bool = Query(False, description="Only open/in-progress/implemented actions"),
    overdue: bool = Query(False, description="Only overdue actions"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("capa")),
):
    """List corrective actions with optional filters."""
    repo = CorrectiveActionRepository(db)
    if finding_id:
        return repo.list_for_finding(finding_id)
    if risk_item_id:
        return repo.list_for_risk_item(risk_item_id)
    if overdue:
        return repo.list_overdue()
    if open_only:
        return repo.list_open()
    if status:
        return list(action for action in repo.list_all() if action.status == status)
    return repo.list_all()


@router.post("/actions", response_model=CorrectiveActionResponse, status_code=201)
def create_corrective_action(
    payload: CorrectiveActionCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("capa", write=True)),
):
    """Create a new corrective action."""
    repo = CorrectiveActionRepository(db)
    if payload.action_id:
        existing = repo.get_by_action_id(payload.action_id)
        if existing:
            raise HTTPException(status_code=409, detail=f"Action ID '{payload.action_id}' already exists.")
    data = prepare_create_data(payload, ACTION_DATE_FIELDS)
    return repo.create(**data)


@router.get("/actions/{action_id}", response_model=CorrectiveActionResponse)
def get_corrective_action(
    action_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("capa")),
):
    """Get corrective action details."""
    action = CorrectiveActionRepository(db).get_by_id(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Corrective action not found.")
    return action


@router.put("/actions/{action_id}", response_model=CorrectiveActionResponse)
def update_corrective_action(
    action_id: int,
    payload: CorrectiveActionUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("capa", write=True)),
):
    """Update a corrective action."""
    repo = CorrectiveActionRepository(db)
    action = repo.get_by_id(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Corrective action not found.")
    update_data = prepare_update_data(payload, ACTION_DATE_FIELDS)
    # Handle closure state transitions
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status in ("verified", "closed") and not action.is_closed:
            from datetime import date
            action.is_closed = True
            action.closed_date = action.closed_date or date.today()
        elif new_status != "closed" and action.is_closed:
            action.is_closed = False
    for key, value in update_data.items():
        setattr(action, key, value)
    db.commit()
    db.refresh(action)
    return action


@router.post("/actions/{action_id}/close", response_model=CorrectiveActionResponse)
def close_corrective_action(
    action_id: int,
    closure_notes: str | None = Query(None, description="Closure notes"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("capa", write=True)),
):
    """Close a corrective action (marks is_closed and sets closed_date)."""
    from datetime import date
    repo = CorrectiveActionRepository(db)
    action = repo.get_by_id(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Corrective action not found.")
    action.status = "closed"
    action.is_closed = True
    action.closed_date = action.closed_date or date.today()
    action.closure_notes = closure_notes or action.closure_notes
    db.commit()
    db.refresh(action)
    return action


# ═══════════════════════════════════════════════════════════════
# Action Task Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/tasks", response_model=list[ActionTaskResponse])
def list_action_tasks(
    pending_only: bool = Query(False, description="Only pending/in-progress tasks"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("capa")),
):
    """List action tasks."""
    repo = ActionTaskRepository(db)
    if pending_only:
        return repo.list_pending()
    return repo.list_all()


@router.post("/tasks", response_model=ActionTaskResponse, status_code=201)
def create_action_task(
    payload: ActionTaskCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("capa", write=True)),
):
    """Create a new action task."""
    action = CorrectiveActionRepository(db).get_by_id(payload.corrective_action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Corrective action not found.")
    data = prepare_create_data(payload, TASK_DATE_FIELDS)
    return ActionTaskRepository(db).create(**data)


@router.get("/actions/{action_id}/tasks", response_model=list[ActionTaskResponse])
def list_tasks_for_action(
    action_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("capa")),
):
    """List tasks for a corrective action."""
    return ActionTaskRepository(db).list_for_action(action_id)


@router.put("/tasks/{task_id}", response_model=ActionTaskResponse)
def update_action_task(
    task_id: int,
    payload: ActionTaskUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("capa", write=True)),
):
    """Update an action task."""
    repo = ActionTaskRepository(db)
    task = repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Action task not found.")
    update_data = prepare_update_data(payload, TASK_DATE_FIELDS)
    for key, value in update_data.items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


# ═══════════════════════════════════════════════════════════════
# Effectiveness Review Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/reviews", response_model=list[EffectivenessReviewResponse])
def list_reviews(
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("capa")),
):
    """List all effectiveness reviews."""
    return EffectivenessReviewRepository(db).list_all()


@router.post("/reviews", response_model=EffectivenessReviewResponse, status_code=201)
def create_review(
    payload: EffectivenessReviewCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("capa", write=True)),
):
    """Create a new effectiveness review."""
    action = CorrectiveActionRepository(db).get_by_id(payload.corrective_action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Corrective action not found.")
    data = prepare_create_data(payload, REVIEW_DATE_FIELDS)
    return EffectivenessReviewRepository(db).create(**data)


@router.get("/actions/{action_id}/reviews", response_model=list[EffectivenessReviewResponse])
def list_reviews_for_action(
    action_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("capa")),
):
    """List effectiveness reviews for a corrective action."""
    return EffectivenessReviewRepository(db).list_for_action(action_id)

