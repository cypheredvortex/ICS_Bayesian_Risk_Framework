"""API router for Compliance Framework management (frameworks, requirements, mappings, gaps, assessments)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database.repositories import (
    ComplianceAssessmentRepository, ComplianceFrameworkRepository,
    ComplianceGapRepository, ControlMappingRepository,
    ControlRepository, FrameworkRequirementRepository,
)
from backend.routers.common import get_db, prepare_create_data, prepare_update_data
from backend.security import get_current_user, require_module_access
from backend.schemas import (
    ComplianceAssessmentCreate, ComplianceAssessmentResponse,
    ComplianceFrameworkCreate, ComplianceFrameworkResponse,
    ComplianceGapCreate, ComplianceGapResponse, ComplianceGapUpdate,
    ControlMappingCreate, ControlMappingResponse,
    FrameworkRequirementCreate, FrameworkRequirementResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/compliance",
    tags=["Compliance"],
    dependencies=[Depends(get_current_user)],
)

GAP_DATE_FIELDS = ["target_closure_date", "closed_date"]
ASSESSMENT_DATE_FIELDS = ["assessment_date"]


# ═══════════════════════════════════════════════════════════════
# Compliance Framework Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/frameworks", response_model=list[ComplianceFrameworkResponse])
def list_frameworks(
    active_only: bool = Query(True, description="Only active frameworks"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance")),
):
    """List compliance frameworks."""
    repo = ComplianceFrameworkRepository(db)
    if active_only:
        return repo.list_active()
    return repo.list_all()


@router.post("/frameworks", response_model=ComplianceFrameworkResponse, status_code=201)
def create_framework(
    payload: ComplianceFrameworkCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance", write=True)),
):
    """Create a new compliance framework."""
    repo = ComplianceFrameworkRepository(db)
    existing = repo.get_by_name_version(payload.name, payload.version)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Framework '{payload.name}' version '{payload.version}' already exists.",
        )
    return repo.create(**payload.model_dump(exclude_unset=True))


@router.get("/frameworks/{framework_id}", response_model=ComplianceFrameworkResponse)
def get_framework(
    framework_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance")),
):
    """Get compliance framework details."""
    framework = ComplianceFrameworkRepository(db).get_by_id(framework_id)
    if not framework:
        raise HTTPException(status_code=404, detail="Compliance framework not found.")
    return framework


@router.delete("/frameworks/{framework_id}", status_code=204)
def delete_framework(
    framework_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance", write=True)),
):
    """Soft-delete a compliance framework."""
    repo = ComplianceFrameworkRepository(db)
    framework = repo.get_by_id(framework_id)
    if not framework:
        raise HTTPException(status_code=404, detail="Compliance framework not found.")
    framework.is_active = False
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Framework Requirement Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/frameworks/{framework_id}/requirements", response_model=list[FrameworkRequirementResponse])
def list_framework_requirements(
    framework_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance")),
):
    """List requirements for a compliance framework."""
    return FrameworkRequirementRepository(db).list_for_framework(framework_id)


@router.post("/requirements", response_model=FrameworkRequirementResponse, status_code=201)
def create_requirement(
    payload: FrameworkRequirementCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance", write=True)),
):
    """Create a new framework requirement."""
    framework = ComplianceFrameworkRepository(db).get_by_id(payload.framework_id)
    if not framework:
        raise HTTPException(status_code=404, detail="Compliance framework not found.")
    return FrameworkRequirementRepository(db).create(**payload.model_dump(exclude_unset=True))


@router.get("/requirements/{requirement_id}", response_model=FrameworkRequirementResponse)
def get_requirement(
    requirement_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance")),
):
    """Get framework requirement details."""
    req = FrameworkRequirementRepository(db).get_by_id(requirement_id)
    if not req:
        raise HTTPException(status_code=404, detail="Framework requirement not found.")
    return req


@router.delete("/requirements/{requirement_id}", status_code=204)
def delete_requirement(
    requirement_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance", write=True)),
):
    """Delete a framework requirement."""
    repo = FrameworkRequirementRepository(db)
    req = repo.get_by_id(requirement_id)
    if not req:
        raise HTTPException(status_code=404, detail="Framework requirement not found.")
    repo.delete(req)
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Control Mapping Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/mappings", response_model=list[ControlMappingResponse])
def list_mappings(
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance")),
):
    """List all control-to-requirement mappings."""
    return ControlMappingRepository(db).list_all()


@router.post("/mappings", response_model=ControlMappingResponse, status_code=201)
def create_mapping(
    payload: ControlMappingCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance", write=True)),
):
    """Create a control-to-requirement mapping."""
    control = ControlRepository(db).get_by_id(payload.control_id)
    if not control:
        raise HTTPException(status_code=404, detail="Control not found.")
    req = FrameworkRequirementRepository(db).get_by_id(payload.requirement_id)
    if not req:
        raise HTTPException(status_code=404, detail="Framework requirement not found.")
    return ControlMappingRepository(db).create(**payload.model_dump(exclude_unset=True))


@router.get("/controls/{control_id}/mappings", response_model=list[ControlMappingResponse])
def list_mappings_for_control(
    control_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance")),
):
    """List mappings for a control."""
    return ControlMappingRepository(db).list_for_control(control_id)


@router.get("/requirements/{requirement_id}/mappings", response_model=list[ControlMappingResponse])
def list_mappings_for_requirement(
    requirement_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance")),
):
    """List mappings for a requirement."""
    return ControlMappingRepository(db).list_for_requirement(requirement_id)


@router.delete("/mappings/{mapping_id}", status_code=204)
def delete_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance", write=True)),
):
    """Delete a control mapping."""
    repo = ControlMappingRepository(db)
    mapping = repo.get_by_id(mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="Control mapping not found.")
    repo.delete(mapping)
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Compliance Gap Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/gaps", response_model=list[ComplianceGapResponse])
def list_gaps(
    open_only: bool = Query(True, description="Only open/planned gaps"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance")),
):
    """List compliance gaps."""
    repo = ComplianceGapRepository(db)
    if open_only:
        return repo.list_open()
    return repo.list_all()


@router.post("/gaps", response_model=ComplianceGapResponse, status_code=201)
def create_gap(
    payload: ComplianceGapCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance", write=True)),
):
    """Create a new compliance gap."""
    req = FrameworkRequirementRepository(db).get_by_id(payload.requirement_id)
    if not req:
        raise HTTPException(status_code=404, detail="Framework requirement not found.")
    data = prepare_create_data(payload, GAP_DATE_FIELDS)
    return ComplianceGapRepository(db).create(**data)


@router.get("/requirements/{requirement_id}/gaps", response_model=list[ComplianceGapResponse])
def list_gaps_for_requirement(
    requirement_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance")),
):
    """List gaps for a requirement."""
    return ComplianceGapRepository(db).list_for_requirement(requirement_id)


@router.put("/gaps/{gap_id}", response_model=ComplianceGapResponse)
def update_gap(
    gap_id: int,
    payload: ComplianceGapUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance", write=True)),
):
    """Update a compliance gap."""
    repo = ComplianceGapRepository(db)
    gap = repo.get_by_id(gap_id)
    if not gap:
        raise HTTPException(status_code=404, detail="Compliance gap not found.")
    update_data = prepare_update_data(payload, GAP_DATE_FIELDS)
    for key, value in update_data.items():
        setattr(gap, key, value)
    db.commit()
    db.refresh(gap)
    return gap


@router.delete("/gaps/{gap_id}", status_code=204)
def delete_gap(
    gap_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance", write=True)),
):
    """Delete a compliance gap."""
    repo = ComplianceGapRepository(db)
    gap = repo.get_by_id(gap_id)
    if not gap:
        raise HTTPException(status_code=404, detail="Compliance gap not found.")
    repo.delete(gap)
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Compliance Assessment Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/assessments", response_model=list[ComplianceAssessmentResponse])
def list_assessments(
    framework_id: int | None = Query(None, description="Filter by framework ID"),
    organization_id: int | None = Query(None, description="Filter by organization ID"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance")),
):
    """List compliance assessments."""
    repo = ComplianceAssessmentRepository(db)
    if framework_id:
        return repo.list_for_framework(framework_id)
    if organization_id:
        return repo.list_for_organization(organization_id)
    return repo.list_all()


@router.post("/assessments", response_model=ComplianceAssessmentResponse, status_code=201)
def create_assessment(
    payload: ComplianceAssessmentCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance", write=True)),
):
    """Create a new compliance assessment."""
    framework = ComplianceFrameworkRepository(db).get_by_id(payload.framework_id)
    if not framework:
        raise HTTPException(status_code=404, detail="Compliance framework not found.")
    data = prepare_create_data(payload, ASSESSMENT_DATE_FIELDS)
    return ComplianceAssessmentRepository(db).create(**data)


@router.get("/assessments/{assessment_id}", response_model=ComplianceAssessmentResponse)
def get_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("compliance")),
):
    """Get compliance assessment details."""
    assessment = ComplianceAssessmentRepository(db).get_by_id(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Compliance assessment not found.")
    return assessment

