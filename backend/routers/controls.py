"""API router for Control Library management (categories, controls, tests, evidence)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database.repositories import (
    ControlCategoryRepository, ControlEvidenceRepository,
    ControlRepository, ControlTestRepository,
)
from backend.routers.common import (
    get_db,
    prepare_create_data,
    prepare_update_data,
)
from backend.security import get_current_user, require_module_access
from backend.schemas import (
    ControlCategoryCreate, ControlCategoryResponse,
    ControlCreate, ControlEvidenceCreate, ControlEvidenceResponse,
    ControlResponse, ControlTestCreate, ControlTestResponse,
    ControlTestUpdate, ControlUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/controls",
    tags=["Control Library"],
    dependencies=[Depends(get_current_user)],
)

CONTROL_DATE_FIELDS = ["last_reviewed_date", "next_review_date"]
TEST_DATE_FIELDS = ["test_date", "next_test_date"]
EVIDENCE_DATE_FIELDS = ["collected_date", "valid_until"]


# ═══════════════════════════════════════════════════════════════
# Control Category Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/categories", response_model=list[ControlCategoryResponse])
def list_control_categories(
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("controls")),
):
    """List all control categories."""
    return ControlCategoryRepository(db).list_all()


@router.post("/categories", response_model=ControlCategoryResponse, status_code=201)
def create_control_category(
    payload: ControlCategoryCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("controls", write=True)),
):
    """Create a new control category."""
    repo = ControlCategoryRepository(db)
    existing = repo.get_by_name(payload.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Control category '{payload.name}' already exists.")
    return repo.create(**payload.model_dump(exclude_unset=True))


@router.get("/categories/{category_id}", response_model=ControlCategoryResponse)
def get_control_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("controls")),
):
    """Get control category details."""
    cat = ControlCategoryRepository(db).get_by_id(category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Control category not found.")
    return cat


@router.delete("/categories/{category_id}", status_code=204)
def delete_control_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("controls", write=True)),
):
    """Delete a control category."""
    repo = ControlCategoryRepository(db)
    cat = repo.get_by_id(category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Control category not found.")
    repo.delete(cat)
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Control Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/", response_model=list[ControlResponse])
def list_controls(
    category_id: int | None = Query(None, description="Filter by control category ID"),
    implementation_status: str | None = Query(None, description="Filter by implementation status"),
    active_only: bool = Query(True, description="Only active controls"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("controls")),
):
    """List controls with optional filters."""
    repo = ControlRepository(db)
    if category_id:
        return repo.list_by_category(category_id)
    if implementation_status:
        return repo.list_by_implementation_status(implementation_status)
    if active_only:
        return repo.list_active()
    return repo.list_all()


@router.post("/", response_model=ControlResponse, status_code=201)
def create_control(
    payload: ControlCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("controls", write=True)),
):
    """Create a new control."""
    repo = ControlRepository(db)
    if payload.control_id:
        existing = repo.get_by_control_id(payload.control_id)
        if existing:
            raise HTTPException(status_code=409, detail=f"Control ID '{payload.control_id}' already exists.")
    if payload.control_category_id:
        cat = ControlCategoryRepository(db).get_by_id(payload.control_category_id)
        if not cat:
            raise HTTPException(status_code=404, detail="Control category not found.")
    data = prepare_create_data(payload, CONTROL_DATE_FIELDS)
    return repo.create(**data)


@router.get("/{control_id}", response_model=ControlResponse)
def get_control(
    control_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("controls")),
):
    """Get control details."""
    control = ControlRepository(db).get_by_id(control_id)
    if not control:
        raise HTTPException(status_code=404, detail="Control not found.")
    return control


@router.put("/{control_id}", response_model=ControlResponse)
def update_control(
    control_id: int,
    payload: ControlUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("controls", write=True)),
):
    """Update a control."""
    repo = ControlRepository(db)
    control = repo.get_by_id(control_id)
    if not control:
        raise HTTPException(status_code=404, detail="Control not found.")
    update_data = prepare_update_data(payload, CONTROL_DATE_FIELDS)
    for key, value in update_data.items():
        setattr(control, key, value)
    db.commit()
    db.refresh(control)
    return control


@router.delete("/{control_id}", status_code=204)
def delete_control(
    control_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("controls", write=True)),
):
    """Soft-delete a control."""
    repo = ControlRepository(db)
    control = repo.get_by_id(control_id)
    if not control:
        raise HTTPException(status_code=404, detail="Control not found.")
    control.is_active = False
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Control Test Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/tests", response_model=list[ControlTestResponse])
def list_control_tests(
    failed_only: bool = Query(False, description="Only show failed/partial tests"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("controls")),
):
    """List control tests, optionally filtering failures."""
    repo = ControlTestRepository(db)
    if failed_only:
        return repo.list_failed()
    return repo.list_all()


@router.post("/tests", response_model=ControlTestResponse, status_code=201)
def create_control_test(
    payload: ControlTestCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("controls", write=True)),
):
    """Create a new control test."""
    control = ControlRepository(db).get_by_id(payload.control_id)
    if not control:
        raise HTTPException(status_code=404, detail="Control not found.")
    data = prepare_create_data(payload, TEST_DATE_FIELDS)
    return ControlTestRepository(db).create(**data)


@router.get("/{control_id}/tests", response_model=list[ControlTestResponse])
def list_tests_for_control(
    control_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("controls")),
):
    """List all tests for a specific control."""
    return ControlTestRepository(db).list_for_control(control_id)


@router.put("/tests/{test_id}", response_model=ControlTestResponse)
def update_control_test(
    test_id: int,
    payload: ControlTestUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("controls", write=True)),
):
    """Update a control test result."""
    repo = ControlTestRepository(db)
    test = repo.get_by_id(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Control test not found.")
    update_data = prepare_update_data(payload, TEST_DATE_FIELDS)
    for key, value in update_data.items():
        setattr(test, key, value)
    db.commit()
    db.refresh(test)
    return test


@router.delete("/tests/{test_id}", status_code=204)
def delete_control_test(
    test_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("controls", write=True)),
):
    """Delete a control test."""
    repo = ControlTestRepository(db)
    test = repo.get_by_id(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Control test not found.")
    repo.delete(test)
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Control Evidence Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/evidence", response_model=list[ControlEvidenceResponse])
def list_control_evidence(
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("controls")),
):
    """List all control evidence records."""
    return ControlEvidenceRepository(db).list_all()


@router.post("/evidence", response_model=ControlEvidenceResponse, status_code=201)
def create_control_evidence(
    payload: ControlEvidenceCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("controls", write=True)),
):
    """Create a new control evidence record."""
    control = ControlRepository(db).get_by_id(payload.control_id)
    if not control:
        raise HTTPException(status_code=404, detail="Control not found.")
    data = prepare_create_data(payload, EVIDENCE_DATE_FIELDS)
    return ControlEvidenceRepository(db).create(**data)


@router.get("/{control_id}/evidence", response_model=list[ControlEvidenceResponse])
def list_evidence_for_control(
    control_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("controls")),
):
    """List evidence for a specific control."""
    return ControlEvidenceRepository(db).list_for_control(control_id)


@router.delete("/evidence/{evidence_id}", status_code=204)
def delete_control_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("controls", write=True)),
):
    """Delete a control evidence record."""
    repo = ControlEvidenceRepository(db)
    evidence = repo.get_by_id(evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Control evidence not found.")
    repo.delete(evidence)
    db.commit()

