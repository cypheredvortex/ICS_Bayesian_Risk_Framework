"""API router for Extended Asset Register."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database.repositories import (
    AssetCategoryRepository, AssetDependencyRepository,
    ExtendedAssetRepository, PlantRepository,
)
from backend.routers.common import get_db
from backend.schemas import (
    AssetCategoryCreate, AssetCategoryResponse,
    ExtendedAssetCreate, ExtendedAssetResponse, ExtendedAssetUpdate,
)
from backend.security import get_current_user, require_module_access

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/assets",
    tags=["Asset Register"],
    dependencies=[Depends(get_current_user)],
)


# ═══════════════════════════════════════════════════════════════
# Asset Category Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/categories", response_model=list[AssetCategoryResponse])
def list_categories(
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("assets")),
):
    """List all asset categories."""
    repo = AssetCategoryRepository(db)
    return repo.list_all()


@router.post("/categories", response_model=AssetCategoryResponse, status_code=201)
def create_category(
    payload: AssetCategoryCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("assets", write=True)),
):
    """Create a new asset category."""
    repo = AssetCategoryRepository(db)
    category = repo.create(**payload.model_dump(exclude_unset=True))
    return category


# ═══════════════════════════════════════════════════════════════
# Extended Asset Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/", response_model=list[ExtendedAssetResponse])
def list_assets(
    plant_id: int | None = Query(None, description="Filter by plant ID"),
    organization_id: int | None = Query(None, description="Filter by organization ID"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("assets")),
):
    """List assets, optionally filtered by plant or organization."""
    repo = ExtendedAssetRepository(db)
    if plant_id:
        return repo.list_for_plant(plant_id)
    if organization_id:
        return repo.list_for_organization(organization_id)
    return repo.list_all()


@router.post("/", response_model=ExtendedAssetResponse, status_code=201)
def create_asset(
    payload: ExtendedAssetCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("assets", write=True)),
):
    """Create a new asset in the register."""
    repo = ExtendedAssetRepository(db)

    # Check asset tag uniqueness
    if payload.asset_tag:
        existing = repo.get_by_asset_tag(payload.asset_tag)
        if existing:
            raise HTTPException(status_code=409, detail=f"Asset tag '{payload.asset_tag}' already exists.")

    asset = repo.create(**payload.model_dump(exclude_unset=True))
    return asset


@router.get("/{asset_id}", response_model=ExtendedAssetResponse)
def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("assets")),
):
    """Get asset details."""
    repo = ExtendedAssetRepository(db)
    asset = repo.get_by_id(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return asset


@router.put("/{asset_id}", response_model=ExtendedAssetResponse)
def update_asset(
    asset_id: int,
    payload: ExtendedAssetUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("assets", write=True)),
):
    """Update an asset."""
    repo = ExtendedAssetRepository(db)
    asset = repo.get_by_id(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")
    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in update_data.items():
        setattr(asset, key, value)
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=204)
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("assets", write=True)),
):
    """Soft-delete an asset."""
    repo = ExtendedAssetRepository(db)
    asset = repo.get_by_id(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")
    asset.is_active = False
    db.commit()
