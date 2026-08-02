"""API router for Risk Register, Treatment, and Acceptance management."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database.repositories import (
    RiskAcceptanceRepository, RiskHistoryRepository, RiskItemRepository,
    RiskScenarioRepository, RiskTreatmentPlanRepository,
)
from backend.routers.common import get_db, prepare_create_data, prepare_update_data
from backend.security import get_current_user, require_module_access
from backend.schemas import (
    RiskAcceptanceCreate, RiskAcceptanceResponse,
    RiskHistoryResponse,
    RiskItemCreate, RiskItemResponse, RiskItemUpdate,
    RiskScenarioCreate, RiskScenarioResponse,
    RiskTreatmentPlanCreate, RiskTreatmentPlanResponse,
    RiskTreatmentPlanUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/risk",
    tags=["Risk Register"],
    dependencies=[Depends(get_current_user)],
)

RISK_ITEM_DATE_FIELDS = ["last_reviewed_date", "next_review_date"]
TREATMENT_DATE_FIELDS = ["target_date", "approval_date", "effectiveness_review_date"]
ACCEPTANCE_DATE_FIELDS = ["expiration_date"]
SCENARIO_DATE_FIELDS: list[str] = []


# ═══════════════════════════════════════════════════════════════
# Risk Item Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/items", response_model=list[RiskItemResponse])
def list_risk_items(
    organization_id: int | None = Query(None, description="Filter by organization ID"),
    asset_id: int | None = Query(None, description="Filter by asset ID"),
    status: str | None = Query(None, description="Filter by status"),
    active_only: bool = Query(True, description="Only active items"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("risk")),
):
    """List risk register items with optional filters."""
    repo = RiskItemRepository(db)
    if organization_id:
        return repo.list_for_organization(organization_id)
    if asset_id:
        return repo.list_for_asset(asset_id)
    if status:
        return list(item for item in repo.list_all() if item.status == status)
    if active_only:
        return repo.list_active()
    return repo.list_all()


@router.post("/items", response_model=RiskItemResponse, status_code=201)
def create_risk_item(
    payload: RiskItemCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("risk", write=True)),
):
    """Create a new risk register item."""
    repo = RiskItemRepository(db)
    if payload.risk_id:
        existing = repo.get_by_risk_id(payload.risk_id)
        if existing:
            raise HTTPException(status_code=409, detail=f"Risk ID '{payload.risk_id}' already exists.")
    data = prepare_create_data(payload, RISK_ITEM_DATE_FIELDS)
    return repo.create(**data)


@router.get("/items/{item_id}", response_model=RiskItemResponse)
def get_risk_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("risk")),
):
    """Get risk item details."""
    item = RiskItemRepository(db).get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Risk item not found.")
    return item


@router.put("/items/{item_id}", response_model=RiskItemResponse)
def update_risk_item(
    item_id: int,
    payload: RiskItemUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("risk", write=True)),
):
    """Update a risk item."""
    repo = RiskItemRepository(db)
    item = repo.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Risk item not found.")
    update_data = prepare_update_data(payload, RISK_ITEM_DATE_FIELDS)
    for key, value in update_data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/items/{item_id}", status_code=204)
def delete_risk_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("risk", write=True)),
):
    """Soft-delete a risk item."""
    repo = RiskItemRepository(db)
    item = repo.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Risk item not found.")
    item.is_active = False
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Risk Scenario Endpoints
# ═══════════════════════════════════════════════════════════════


@router.post("/scenarios", response_model=RiskScenarioResponse, status_code=201)
def create_risk_scenario(
    payload: RiskScenarioCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("risk", write=True)),
):
    """Create a new risk scenario."""
    item = RiskItemRepository(db).get_by_id(payload.risk_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Risk item not found.")
    return RiskScenarioRepository(db).create(**payload.model_dump(exclude_unset=True))


@router.get("/items/{item_id}/scenarios", response_model=list[RiskScenarioResponse])
def list_risk_scenarios(
    item_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("risk")),
):
    """List scenarios for a risk item."""
    return RiskScenarioRepository(db).list_for_risk_item(item_id)


# ═══════════════════════════════════════════════════════════════
# Risk Treatment Plan Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/treatment-plans", response_model=list[RiskTreatmentPlanResponse])
def list_treatment_plans(
    status: str | None = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("risk")),
):
    """List risk treatment plans, optionally filtered by status."""
    repo = RiskTreatmentPlanRepository(db)
    if status:
        return repo.list_by_status(status)
    return repo.list_all()


@router.post("/treatment-plans", response_model=RiskTreatmentPlanResponse, status_code=201)
def create_treatment_plan(
    payload: RiskTreatmentPlanCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("risk", write=True)),
):
    """Create a new risk treatment plan."""
    item = RiskItemRepository(db).get_by_id(payload.risk_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Risk item not found.")
    data = prepare_create_data(payload, TREATMENT_DATE_FIELDS)
    return RiskTreatmentPlanRepository(db).create(**data)


@router.get("/items/{item_id}/treatment-plans", response_model=list[RiskTreatmentPlanResponse])
def list_treatment_plans_for_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("risk")),
):
    """List treatment plans for a risk item."""
    return RiskTreatmentPlanRepository(db).list_for_risk_item(item_id)


@router.put("/treatment-plans/{plan_id}", response_model=RiskTreatmentPlanResponse)
def update_treatment_plan(
    plan_id: int,
    payload: RiskTreatmentPlanUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("risk", write=True)),
):
    """Update a risk treatment plan."""
    repo = RiskTreatmentPlanRepository(db)
    plan = repo.get_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Risk treatment plan not found.")
    update_data = prepare_update_data(payload, TREATMENT_DATE_FIELDS)
    for key, value in update_data.items():
        setattr(plan, key, value)
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/treatment-plans/{plan_id}", status_code=204)
def delete_treatment_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("risk", write=True)),
):
    """Delete a risk treatment plan."""
    repo = RiskTreatmentPlanRepository(db)
    plan = repo.get_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Risk treatment plan not found.")
    repo.delete(plan)
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Risk Acceptance Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/acceptances", response_model=list[RiskAcceptanceResponse])
def list_acceptances(
    active_only: bool = Query(True, description="Only active acceptances"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("risk")),
):
    """List risk acceptances."""
    repo = RiskAcceptanceRepository(db)
    if active_only:
        return repo.list_active()
    return repo.list_all()


@router.post("/acceptances", response_model=RiskAcceptanceResponse, status_code=201)
def create_acceptance(
    payload: RiskAcceptanceCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("risk", write=True)),
):
    """Create a new risk acceptance."""
    item = RiskItemRepository(db).get_by_id(payload.risk_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Risk item not found.")
    data = prepare_create_data(payload, ACCEPTANCE_DATE_FIELDS)
    return RiskAcceptanceRepository(db).create(**data)


@router.get("/items/{item_id}/acceptances", response_model=list[RiskAcceptanceResponse])
def list_acceptances_for_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("risk")),
):
    """List acceptances for a risk item."""
    return RiskAcceptanceRepository(db).list_for_risk_item(item_id)


@router.delete("/acceptances/{acceptance_id}", status_code=204)
def delete_acceptance(
    acceptance_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("risk", write=True)),
):
    """Delete a risk acceptance."""
    repo = RiskAcceptanceRepository(db)
    acceptance = repo.get_by_id(acceptance_id)
    if not acceptance:
        raise HTTPException(status_code=404, detail="Risk acceptance not found.")
    repo.delete(acceptance)
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Risk History Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/items/{item_id}/history", response_model=list[RiskHistoryResponse])
def list_risk_history(
    item_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("risk")),
):
    """List history for a risk item."""
    return RiskHistoryRepository(db).list_for_risk_item(item_id)

