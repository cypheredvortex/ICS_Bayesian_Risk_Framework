"""API router for Organization/Site/Plant hierarchy management."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database.repositories import (
    OrganizationRepository, SiteRepository, PlantRepository,
    AuditLogRepository,
)
from backend.routers.common import get_db
from backend.schemas import (
    OrganizationCreate, OrganizationResponse, OrganizationUpdate,
    PlantCreate, PlantResponse, PlantUpdate,
    SiteCreate, SiteResponse, SiteUpdate,
)
from backend.security import get_current_user, require_module_access

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/organizations",
    tags=["Organizations"],
    dependencies=[Depends(get_current_user)],
)


# ═══════════════════════════════════════════════════════════════
# Organization Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/", response_model=list[OrganizationResponse])
def list_organizations(
    active_only: bool = Query(True, description="Filter to active organizations only"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("organizations")),
):
    """List all organizations."""
    repo = OrganizationRepository(db)
    if active_only:
        return repo.list_active()
    return repo.list_all()


@router.post("/", response_model=OrganizationResponse, status_code=201)
def create_organization(
    payload: OrganizationCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("organizations", write=True)),
):
    """Create a new organization."""
    repo = OrganizationRepository(db)
    existing = repo.get_by_name(payload.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Organization '{payload.name}' already exists.")
    org = repo.create(**payload.model_dump(exclude_unset=True))
    return org


@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization(
    org_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("organizations")),
):
    """Get organization details."""
    repo = OrganizationRepository(db)
    org = repo.get_by_id(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")
    return org


@router.put("/{org_id}", response_model=OrganizationResponse)
def update_organization(
    org_id: int,
    payload: OrganizationUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("organizations", write=True)),
):
    """Update an organization."""
    repo = OrganizationRepository(db)
    org = repo.get_by_id(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")
    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in update_data.items():
        setattr(org, key, value)
    db.commit()
    db.refresh(org)
    return org


@router.delete("/{org_id}", status_code=204)
def delete_organization(
    org_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("organizations", write=True)),
):
    """Soft-delete an organization."""
    repo = OrganizationRepository(db)
    org = repo.get_by_id(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")
    org.is_active = False
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Site Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/{org_id}/sites", response_model=list[SiteResponse])
def list_sites(
    org_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("organizations")),
):
    """List all sites for an organization."""
    repo = SiteRepository(db)
    return repo.list_for_organization(org_id)


@router.post("/{org_id}/sites", response_model=SiteResponse, status_code=201)
def create_site(
    org_id: int,
    payload: SiteCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("organizations", write=True)),
):
    """Create a new site within an organization."""
    if payload.organization_id != org_id:
        raise HTTPException(status_code=400, detail="Organization ID mismatch.")
    repo = SiteRepository(db)
    site = repo.create(**payload.model_dump(exclude_unset=True))
    return site


@router.get("/sites/{site_id}", response_model=SiteResponse)
def get_site(
    site_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("organizations")),
):
    """Get site details."""
    repo = SiteRepository(db)
    site = repo.get_by_id(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found.")
    return site


@router.put("/sites/{site_id}", response_model=SiteResponse)
def update_site(
    site_id: int,
    payload: SiteUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("organizations", write=True)),
):
    """Update a site."""
    repo = SiteRepository(db)
    site = repo.get_by_id(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found.")
    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in update_data.items():
        setattr(site, key, value)
    db.commit()
    db.refresh(site)
    return site


# ═══════════════════════════════════════════════════════════════
# Plant Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/sites/{site_id}/plants", response_model=list[PlantResponse])
def list_plants(
    site_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("organizations")),
):
    """List all plants for a site."""
    repo = PlantRepository(db)
    return repo.list_for_site(site_id)


@router.post("/sites/{site_id}/plants", response_model=PlantResponse, status_code=201)
def create_plant(
    site_id: int,
    payload: PlantCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("organizations", write=True)),
):
    """Create a new plant within a site."""
    if payload.site_id != site_id:
        raise HTTPException(status_code=400, detail="Site ID mismatch.")
    repo = PlantRepository(db)
    plant = repo.create(**payload.model_dump(exclude_unset=True))
    return plant


@router.get("/plants/{plant_id}", response_model=PlantResponse)
def get_plant(
    plant_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("organizations")),
):
    """Get plant details."""
    repo = PlantRepository(db)
    plant = repo.get_by_id(plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found.")
    return plant


@router.put("/plants/{plant_id}", response_model=PlantResponse)
def update_plant(
    plant_id: int,
    payload: PlantUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("organizations", write=True)),
):
    """Update a plant."""
    repo = PlantRepository(db)
    plant = repo.get_by_id(plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found.")
    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in update_data.items():
        setattr(plant, key, value)
    db.commit()
    db.refresh(plant)
    return plant
