"""API router for Security Zones and Conduits (IEC 62443)."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.repositories import (
    ConduitRepository, SecurityZoneRepository, PlantRepository,
)
from backend.routers.common import get_db
from backend.schemas import (
    ConduitCreate, ConduitResponse,
    SecurityZoneCreate, SecurityZoneResponse,
)
from backend.security import get_current_user, require_module_access

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/zones",
    tags=["Zones & Conduits"],
    dependencies=[Depends(get_current_user)],
)


# ═══════════════════════════════════════════════════════════════
# Security Zone Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/plants/{plant_id}/zones", response_model=list[SecurityZoneResponse])
def list_zones(
    plant_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("zones")),
):
    """List all security zones for a plant."""
    repo = SecurityZoneRepository(db)
    return repo.list_for_plant(plant_id)


@router.post("/plants/{plant_id}/zones", response_model=SecurityZoneResponse, status_code=201)
def create_zone(
    plant_id: int,
    payload: SecurityZoneCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("zones", write=True)),
):
    """Create a new security zone within a plant."""
    if payload.plant_id != plant_id:
        raise HTTPException(status_code=400, detail="Plant ID mismatch.")

    # Validate plant exists
    plant_repo = PlantRepository(db)
    plant = plant_repo.get_by_id(plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found.")

    repo = SecurityZoneRepository(db)
    zone = repo.create(**payload.model_dump(exclude_unset=True))
    return zone


@router.get("/zones/{zone_id}", response_model=SecurityZoneResponse)
def get_zone(
    zone_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("zones")),
):
    """Get security zone details."""
    repo = SecurityZoneRepository(db)
    zone = repo.get_by_id(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Security zone not found.")
    return zone


@router.put("/zones/{zone_id}", response_model=SecurityZoneResponse)
def update_zone(
    zone_id: int,
    payload: SecurityZoneCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("zones", write=True)),
):
    """Update a security zone."""
    repo = SecurityZoneRepository(db)
    zone = repo.get_by_id(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Security zone not found.")
    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in update_data.items():
        setattr(zone, key, value)
    db.commit()
    db.refresh(zone)
    return zone


@router.delete("/zones/{zone_id}", status_code=204)
def delete_zone(
    zone_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("zones", write=True)),
):
    """Soft-delete a security zone."""
    repo = SecurityZoneRepository(db)
    zone = repo.get_by_id(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Security zone not found.")
    zone.is_active = False
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Conduit Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/plants/{plant_id}/conduits", response_model=list[ConduitResponse])
def list_conduits(
    plant_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("zones")),
):
    """List all conduits for a plant."""
    repo = ConduitRepository(db)
    return repo.list_for_plant(plant_id)


@router.post("/plants/{plant_id}/conduits", response_model=ConduitResponse, status_code=201)
def create_conduit(
    plant_id: int,
    payload: ConduitCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("zones", write=True)),
):
    """Create a new conduit between zones."""
    if payload.plant_id != plant_id:
        raise HTTPException(status_code=400, detail="Plant ID mismatch.")

    # Validate zones exist
    zone_repo = SecurityZoneRepository(db)
    source = zone_repo.get_by_id(payload.source_zone_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source zone not found.")
    dest = zone_repo.get_by_id(payload.destination_zone_id)
    if not dest:
        raise HTTPException(status_code=404, detail="Destination zone not found.")

    repo = ConduitRepository(db)
    conduit = repo.create(**payload.model_dump(exclude_unset=True))
    return conduit


@router.get("/conduits/{conduit_id}", response_model=ConduitResponse)
def get_conduit(
    conduit_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("zones")),
):
    """Get conduit details."""
    repo = ConduitRepository(db)
    conduit = repo.get_by_id(conduit_id)
    if not conduit:
        raise HTTPException(status_code=404, detail="Conduit not found.")
    return conduit


@router.delete("/conduits/{conduit_id}", status_code=204)
def delete_conduit(
    conduit_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("zones", write=True)),
):
    """Delete a conduit."""
    repo = ConduitRepository(db)
    conduit = repo.get_by_id(conduit_id)
    if not conduit:
        raise HTTPException(status_code=404, detail="Conduit not found.")
    repo.delete(conduit)
    db.commit()
