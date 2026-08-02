"""API router for Threat Library management (MITRE ICS, STRIDE, etc.)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database.repositories import (
    ThreatCategoryRepository, ThreatRepository, ThreatActorRepository,
)
from backend.routers.common import get_db
from backend.schemas import (
    ThreatActorCreate, ThreatActorResponse,
    ThreatCategoryCreate, ThreatCategoryResponse,
    ThreatCreate, ThreatResponse, ThreatUpdate,
)
from backend.security import get_current_user, require_module_access

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/threats",
    tags=["Threat Library"],
    dependencies=[Depends(get_current_user)],
)


# ═══════════════════════════════════════════════════════════════
# Threat Category Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/categories", response_model=list[ThreatCategoryResponse])
def list_threat_categories(
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("threats")),
):
    """List all threat categories."""
    repo = ThreatCategoryRepository(db)
    return repo.list_all()


@router.post("/categories", response_model=ThreatCategoryResponse, status_code=201)
def create_threat_category(
    payload: ThreatCategoryCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("threats", write=True)),
):
    """Create a new threat category."""
    repo = ThreatCategoryRepository(db)
    existing = repo.get_by_name(payload.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Threat category '{payload.name}' already exists.")
    cat = repo.create(**payload.model_dump(exclude_unset=True))
    return cat


@router.get("/categories/{category_id}", response_model=ThreatCategoryResponse)
def get_threat_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("threats")),
):
    """Get threat category details."""
    repo = ThreatCategoryRepository(db)
    cat = repo.get_by_id(category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Threat category not found.")
    return cat


@router.delete("/categories/{category_id}", status_code=204)
def delete_threat_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("threats", write=True)),
):
    """Delete a threat category."""
    repo = ThreatCategoryRepository(db)
    cat = repo.get_by_id(category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Threat category not found.")
    repo.delete(cat)
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Threat Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/", response_model=list[ThreatResponse])
def list_threats(
    category_id: int | None = Query(None, description="Filter by category ID"),
    source: str | None = Query(None, description="Filter by source (mitre_ics, stride, custom)"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("threats")),
):
    """List threats, optionally filtered by category or source."""
    repo = ThreatRepository(db)
    if category_id:
        return repo.list_by_category(category_id)
    if source:
        return repo.list_by_source(source)
    return repo.list_all()


@router.post("/", response_model=ThreatResponse, status_code=201)
def create_threat(
    payload: ThreatCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("threats", write=True)),
):
    """Create a new threat entry."""
    repo = ThreatRepository(db)
    existing = repo.get_by_name(payload.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Threat '{payload.name}' already exists.")

    # Validate category exists if specified
    if payload.threat_category_id:
        cat_repo = ThreatCategoryRepository(db)
        cat = cat_repo.get_by_id(payload.threat_category_id)
        if not cat:
            raise HTTPException(status_code=404, detail="Threat category not found.")

    threat = repo.create(**payload.model_dump(exclude_unset=True))
    return threat


@router.get("/{threat_id}", response_model=ThreatResponse)
def get_threat(
    threat_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("threats")),
):
    """Get threat details."""
    repo = ThreatRepository(db)
    threat = repo.get_by_id(threat_id)
    if not threat:
        raise HTTPException(status_code=404, detail="Threat not found.")
    return threat


@router.put("/{threat_id}", response_model=ThreatResponse)
def update_threat(
    threat_id: int,
    payload: ThreatUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("threats", write=True)),
):
    """Update a threat."""
    repo = ThreatRepository(db)
    threat = repo.get_by_id(threat_id)
    if not threat:
        raise HTTPException(status_code=404, detail="Threat not found.")
    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in update_data.items():
        setattr(threat, key, value)
    db.commit()
    db.refresh(threat)
    return threat


@router.delete("/{threat_id}", status_code=204)
def delete_threat(
    threat_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("threats", write=True)),
):
    """Delete a threat."""
    repo = ThreatRepository(db)
    threat = repo.get_by_id(threat_id)
    if not threat:
        raise HTTPException(status_code=404, detail="Threat not found.")
    repo.delete(threat)
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Threat Actor Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/actors", response_model=list[ThreatActorResponse])
def list_threat_actors(
    actor_type: str | None = Query(None, description="Filter by actor type"),
    active_only: bool = Query(True, description="Only active actors"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("threats")),
):
    """List threat actors, optionally filtered by type."""
    repo = ThreatActorRepository(db)
    if actor_type:
        return repo.list_by_actor_type(actor_type)
    if active_only:
        return repo.list_active()
    return repo.list_all()


@router.post("/actors", response_model=ThreatActorResponse, status_code=201)
def create_threat_actor(
    payload: ThreatActorCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("threats", write=True)),
):
    """Create a new threat actor."""
    repo = ThreatActorRepository(db)
    actor = repo.create(**payload.model_dump(exclude_unset=True))
    return actor


@router.get("/actors/{actor_id}", response_model=ThreatActorResponse)
def get_threat_actor(
    actor_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("threats")),
):
    """Get threat actor details."""
    repo = ThreatActorRepository(db)
    actor = repo.get_by_id(actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail="Threat actor not found.")
    return actor


@router.put("/actors/{actor_id}", response_model=ThreatActorResponse)
def update_threat_actor(
    actor_id: int,
    payload: ThreatActorCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("threats", write=True)),
):
    """Update a threat actor."""
    repo = ThreatActorRepository(db)
    actor = repo.get_by_id(actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail="Threat actor not found.")
    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in update_data.items():
        setattr(actor, key, value)
    db.commit()
    db.refresh(actor)
    return actor


@router.delete("/actors/{actor_id}", status_code=204)
def delete_threat_actor(
    actor_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("threats", write=True)),
):
    """Soft-delete a threat actor."""
    repo = ThreatActorRepository(db)
    actor = repo.get_by_id(actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail="Threat actor not found.")
    actor.is_active = False
    db.commit()



