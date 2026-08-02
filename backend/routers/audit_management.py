"""API router for Audit Management (programs, plans, procedures, findings, evidence, interviews)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database.repositories import (
    AuditEvidenceRepository, AuditFindingRepository, AuditInterviewRepository,
    AuditPlanRepository, AuditProcedureRepository, AuditProgramRepository,
)
from backend.routers.common import get_db, prepare_create_data, prepare_update_data
from backend.security import get_current_user, require_module_access
from backend.schemas import (
    AuditEvidenceCreate, AuditEvidenceResponse,
    AuditFindingCreate, AuditFindingResponse, AuditFindingUpdate,
    AuditInterviewCreate, AuditInterviewResponse,
    AuditPlanCreate, AuditPlanResponse, AuditPlanUpdate,
    AuditProcedureCreate, AuditProcedureResponse,
    AuditProgramCreate, AuditProgramResponse, AuditProgramUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/audit",
    tags=["Audit Management"],
    dependencies=[Depends(get_current_user)],
)

PROGRAM_DATE_FIELDS = ["start_date", "end_date"]
PLAN_DATE_FIELDS = ["start_date", "end_date"]
FINDING_DATE_FIELDS = ["response_date"]
INTERVIEW_DATETIME_FIELDS = ["interview_date"]


# ═══════════════════════════════════════════════════════════════
# Audit Program Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/programs", response_model=list[AuditProgramResponse])
def list_audit_programs(
    organization_id: int | None = Query(None, description="Filter by organization ID"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit")),
):
    """List audit programs, optionally filtered by organization."""
    repo = AuditProgramRepository(db)
    if organization_id:
        return repo.list_for_organization(organization_id)
    return repo.list_all()


@router.post("/programs", response_model=AuditProgramResponse, status_code=201)
def create_audit_program(
    payload: AuditProgramCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit", write=True)),
):
    """Create a new audit program."""
    data = prepare_create_data(payload, PROGRAM_DATE_FIELDS)
    return AuditProgramRepository(db).create(**data)


@router.get("/programs/{program_id}", response_model=AuditProgramResponse)
def get_audit_program(
    program_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit")),
):
    """Get audit program details."""
    program = AuditProgramRepository(db).get_by_id(program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Audit program not found.")
    return program


@router.put("/programs/{program_id}", response_model=AuditProgramResponse)
def update_audit_program(
    program_id: int,
    payload: AuditProgramUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit", write=True)),
):
    """Update an audit program."""
    repo = AuditProgramRepository(db)
    program = repo.get_by_id(program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Audit program not found.")
    update_data = prepare_update_data(payload, PROGRAM_DATE_FIELDS)
    for key, value in update_data.items():
        setattr(program, key, value)
    db.commit()
    db.refresh(program)
    return program


@router.delete("/programs/{program_id}", status_code=204)
def delete_audit_program(
    program_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit", write=True)),
):
    """Delete an audit program."""
    repo = AuditProgramRepository(db)
    program = repo.get_by_id(program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Audit program not found.")
    repo.delete(program)
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Audit Plan Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/plans", response_model=list[AuditPlanResponse])
def list_audit_plans(
    program_id: int | None = Query(None, description="Filter by audit program ID"),
    organization_id: int | None = Query(None, description="Filter by organization ID"),
    status: str | None = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit")),
):
    """List audit plans with optional filters."""
    repo = AuditPlanRepository(db)
    if program_id:
        return repo.list_for_program(program_id)
    if organization_id:
        return repo.list_for_organization(organization_id)
    if status:
        return repo.list_by_status(status)
    return repo.list_all()


@router.post("/plans", response_model=AuditPlanResponse, status_code=201)
def create_audit_plan(
    payload: AuditPlanCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit", write=True)),
):
    """Create a new audit plan."""
    if payload.audit_program_id:
        program = AuditProgramRepository(db).get_by_id(payload.audit_program_id)
        if not program:
            raise HTTPException(status_code=404, detail="Audit program not found.")
    data = prepare_create_data(payload, PLAN_DATE_FIELDS)
    return AuditPlanRepository(db).create(**data)


@router.get("/plans/{plan_id}", response_model=AuditPlanResponse)
def get_audit_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit")),
):
    """Get audit plan details."""
    plan = AuditPlanRepository(db).get_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Audit plan not found.")
    return plan


@router.put("/plans/{plan_id}", response_model=AuditPlanResponse)
def update_audit_plan(
    plan_id: int,
    payload: AuditPlanUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit", write=True)),
):
    """Update an audit plan."""
    repo = AuditPlanRepository(db)
    plan = repo.get_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Audit plan not found.")
    update_data = prepare_update_data(payload, PLAN_DATE_FIELDS)
    for key, value in update_data.items():
        setattr(plan, key, value)
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/plans/{plan_id}", status_code=204)
def delete_audit_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit", write=True)),
):
    """Delete an audit plan."""
    repo = AuditPlanRepository(db)
    plan = repo.get_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Audit plan not found.")
    repo.delete(plan)
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Audit Procedure Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/plans/{plan_id}/procedures", response_model=list[AuditProcedureResponse])
def list_audit_procedures(
    plan_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit")),
):
    """List audit procedures for a plan."""
    return AuditProcedureRepository(db).list_for_plan(plan_id)


@router.post("/procedures", response_model=AuditProcedureResponse, status_code=201)
def create_audit_procedure(
    payload: AuditProcedureCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit", write=True)),
):
    """Create a new audit procedure."""
    plan = AuditPlanRepository(db).get_by_id(payload.audit_plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Audit plan not found.")
    return AuditProcedureRepository(db).create(**payload.model_dump(exclude_unset=True))


@router.get("/procedures/{procedure_id}", response_model=AuditProcedureResponse)
def get_audit_procedure(
    procedure_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit")),
):
    """Get audit procedure details."""
    procedure = AuditProcedureRepository(db).get_by_id(procedure_id)
    if not procedure:
        raise HTTPException(status_code=404, detail="Audit procedure not found.")
    return procedure


@router.delete("/procedures/{procedure_id}", status_code=204)
def delete_audit_procedure(
    procedure_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit", write=True)),
):
    """Delete an audit procedure."""
    repo = AuditProcedureRepository(db)
    procedure = repo.get_by_id(procedure_id)
    if not procedure:
        raise HTTPException(status_code=404, detail="Audit procedure not found.")
    repo.delete(procedure)
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Audit Finding Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/findings", response_model=list[AuditFindingResponse])
def list_audit_findings(
    plan_id: int | None = Query(None, description="Filter by audit plan ID"),
    severity: str | None = Query(None, description="Filter by severity"),
    open_only: bool = Query(False, description="Only open/acknowledged/action-planned findings"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit")),
):
    """List audit findings with optional filters."""
    repo = AuditFindingRepository(db)
    if plan_id:
        return repo.list_for_plan(plan_id)
    if severity:
        return repo.list_by_severity(severity)
    if open_only:
        return repo.list_open()
    return repo.list_all()


@router.post("/findings", response_model=AuditFindingResponse, status_code=201)
def create_audit_finding(
    payload: AuditFindingCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit", write=True)),
):
    """Create a new audit finding."""
    plan = AuditPlanRepository(db).get_by_id(payload.audit_plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Audit plan not found.")
    if payload.finding_id:
        existing = AuditFindingRepository(db).get_by_finding_id(payload.finding_id)
        if existing:
            raise HTTPException(status_code=409, detail=f"Finding ID '{payload.finding_id}' already exists.")
    data = prepare_create_data(payload, FINDING_DATE_FIELDS)
    return AuditFindingRepository(db).create(**data)


@router.get("/findings/{finding_id}", response_model=AuditFindingResponse)
def get_audit_finding(
    finding_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit")),
):
    """Get audit finding details."""
    finding = AuditFindingRepository(db).get_by_id(finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Audit finding not found.")
    return finding


@router.put("/findings/{finding_id}", response_model=AuditFindingResponse)
def update_audit_finding(
    finding_id: int,
    payload: AuditFindingUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit", write=True)),
):
    """Update an audit finding."""
    repo = AuditFindingRepository(db)
    finding = repo.get_by_id(finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Audit finding not found.")
    update_data = prepare_update_data(payload, FINDING_DATE_FIELDS)
    for key, value in update_data.items():
        setattr(finding, key, value)
    db.commit()
    db.refresh(finding)
    return finding


@router.delete("/findings/{finding_id}", status_code=204)
def delete_audit_finding(
    finding_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit", write=True)),
):
    """Delete an audit finding."""
    repo = AuditFindingRepository(db)
    finding = repo.get_by_id(finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Audit finding not found.")
    repo.delete(finding)
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Audit Evidence Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/evidence", response_model=list[AuditEvidenceResponse])
def list_audit_evidence(
    plan_id: int | None = Query(None, description="Filter by audit plan ID"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit")),
):
    """List audit evidence, optionally filtered by plan."""
    repo = AuditEvidenceRepository(db)
    if plan_id:
        return repo.list_for_plan(plan_id)
    return repo.list_all()


@router.post("/evidence", response_model=AuditEvidenceResponse, status_code=201)
def create_audit_evidence(
    payload: AuditEvidenceCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit", write=True)),
):
    """Create audit evidence."""
    plan = AuditPlanRepository(db).get_by_id(payload.audit_plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Audit plan not found.")
    return AuditEvidenceRepository(db).create(**payload.model_dump(exclude_unset=True))


@router.get("/evidence/{evidence_id}", response_model=AuditEvidenceResponse)
def get_audit_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit")),
):
    """Get audit evidence details."""
    evidence = AuditEvidenceRepository(db).get_by_id(evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Audit evidence not found.")
    return evidence


@router.delete("/evidence/{evidence_id}", status_code=204)
def delete_audit_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit", write=True)),
):
    """Delete audit evidence."""
    repo = AuditEvidenceRepository(db)
    evidence = repo.get_by_id(evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Audit evidence not found.")
    repo.delete(evidence)
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Audit Interview Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/interviews", response_model=list[AuditInterviewResponse])
def list_audit_interviews(
    plan_id: int | None = Query(None, description="Filter by audit plan ID"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit")),
):
    """List audit interviews, optionally filtered by plan."""
    repo = AuditInterviewRepository(db)
    if plan_id:
        return repo.list_for_plan(plan_id)
    return repo.list_all()


@router.post("/interviews", response_model=AuditInterviewResponse, status_code=201)
def create_audit_interview(
    payload: AuditInterviewCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit", write=True)),
):
    """Create an audit interview record."""
    plan = AuditPlanRepository(db).get_by_id(payload.audit_plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Audit plan not found.")
    data = payload.model_dump(exclude_unset=True)
    interview_date = data.get("interview_date")
    if interview_date:
        from backend.routers.common import parse_datetime
        data["interview_date"] = parse_datetime(interview_date, "interview_date")
    return AuditInterviewRepository(db).create(**data)


@router.get("/interviews/{interview_id}", response_model=AuditInterviewResponse)
def get_audit_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit")),
):
    """Get audit interview details."""
    interview = AuditInterviewRepository(db).get_by_id(interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Audit interview not found.")
    return interview


@router.delete("/interviews/{interview_id}", status_code=204)
def delete_audit_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("audit", write=True)),
):
    """Delete an audit interview."""
    repo = AuditInterviewRepository(db)
    interview = repo.get_by_id(interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Audit interview not found.")
    repo.delete(interview)
    db.commit()

