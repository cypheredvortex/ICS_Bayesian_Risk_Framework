"""API router for Vulnerability Registry management (CVE/CVSS)."""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database.repositories import (
    AssetVulnerabilityRepository, ExtendedAssetRepository,
    VulnerabilityRepository,
)
from backend.routers.common import get_db
from backend.schemas import (
    AssetVulnerabilityCreate, AssetVulnerabilityResponse,
    AssetVulnerabilityUpdate,
    VulnerabilityCreate, VulnerabilityResponse, VulnerabilityUpdate,
)
from backend.security import get_current_user, require_module_access

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/vulnerabilities",
    tags=["Vulnerability Registry"],
    dependencies=[Depends(get_current_user)],
)


# ═══════════════════════════════════════════════════════════════
# Vulnerability Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/", response_model=list[VulnerabilityResponse])
def list_vulnerabilities(
    severity: str | None = Query(None, description="Filter by CVSS severity"),
    exploitable: bool | None = Query(None, description="Filter for exploitable only"),
    unpatched: bool | None = Query(None, description="Filter for unpatched only"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("vulnerabilities")),
):
    """List vulnerabilities with optional filters."""
    repo = VulnerabilityRepository(db)
    if severity:
        return repo.list_by_severity(severity)
    if exploitable:
        return repo.list_exploitable()
    if unpatched:
        return repo.list_unpatched()
    return repo.list_all()


@router.post("/", response_model=VulnerabilityResponse, status_code=201)
def create_vulnerability(
    payload: VulnerabilityCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("vulnerabilities", write=True)),
):
    """Create a new vulnerability entry."""
    repo = VulnerabilityRepository(db)

    # Check CVE uniqueness
    if payload.cve_id:
        existing = repo.get_by_cve_id(payload.cve_id)
        if existing:
            raise HTTPException(status_code=409, detail=f"CVE '{payload.cve_id}' already exists.")

    # Parse dates if provided
    data = payload.model_dump(exclude_unset=True)
    for date_field in ("published_date", "discovered_date"):
        if data.get(date_field):
            try:
                data[date_field] = date.fromisoformat(data[date_field])
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail=f"Invalid date format for {date_field}. Use YYYY-MM-DD.")

    vuln = repo.create(**data)
    return vuln


@router.get("/{vuln_id}", response_model=VulnerabilityResponse)
def get_vulnerability(
    vuln_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("vulnerabilities")),
):
    """Get vulnerability details."""
    repo = VulnerabilityRepository(db)
    vuln = repo.get_by_id(vuln_id)
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found.")
    return vuln


@router.put("/{vuln_id}", response_model=VulnerabilityResponse)
def update_vulnerability(
    vuln_id: int,
    payload: VulnerabilityUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("vulnerabilities", write=True)),
):
    """Update a vulnerability."""
    repo = VulnerabilityRepository(db)
    vuln = repo.get_by_id(vuln_id)
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found.")
    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in update_data.items():
        setattr(vuln, key, value)
    db.commit()
    db.refresh(vuln)
    return vuln


@router.delete("/{vuln_id}", status_code=204)
def delete_vulnerability(
    vuln_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("vulnerabilities", write=True)),
):
    """Delete a vulnerability."""
    repo = VulnerabilityRepository(db)
    vuln = repo.get_by_id(vuln_id)
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found.")
    repo.delete(vuln)
    db.commit()


# ═══════════════════════════════════════════════════════════════
# Asset-Vulnerability Mapping Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/assets/{asset_id}/vulnerabilities", response_model=list[AssetVulnerabilityResponse])
def list_asset_vulnerabilities(
    asset_id: int,
    open_only: bool = Query(False, description="Only show open/in-progress vulnerabilities"),
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("vulnerabilities")),
):
    """List vulnerabilities linked to an asset."""
    repo = AssetVulnerabilityRepository(db)
    if open_only:
        return repo.list_open_for_asset(asset_id)
    return repo.list_for_asset(asset_id)


@router.get("/by-asset/{asset_id}", response_model=list[AssetVulnerabilityResponse])
def list_vulnerabilities_for_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("vulnerabilities")),
):
    """Alias: list vulnerabilities linked to an asset."""
    repo = AssetVulnerabilityRepository(db)
    return repo.list_for_asset(asset_id)


@router.post("/link", response_model=AssetVulnerabilityResponse, status_code=201)
def link_vulnerability_to_asset(
    payload: AssetVulnerabilityCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("vulnerabilities", write=True)),
):
    """Link a vulnerability to an asset."""
    # Validate asset exists
    asset_repo = ExtendedAssetRepository(db)
    asset = asset_repo.get_by_id(payload.asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")

    # Validate vulnerability exists
    vuln_repo = VulnerabilityRepository(db)
    vuln = vuln_repo.get_by_id(payload.vulnerability_id)
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found.")

    repo = AssetVulnerabilityRepository(db)
    data = payload.model_dump(exclude_unset=True)
    av = repo.create(**data)
    return av


@router.put("/link/{link_id}", response_model=AssetVulnerabilityResponse)
def update_asset_vulnerability_link(
    link_id: int,
    payload: AssetVulnerabilityUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("vulnerabilities", write=True)),
):
    """Update an asset-vulnerability link (status, notes, etc.)."""
    repo = AssetVulnerabilityRepository(db)
    av = repo.get_by_id(link_id)
    if not av:
        raise HTTPException(status_code=404, detail="Asset-vulnerability link not found.")

    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in update_data.items():
        setattr(av, key, value)
    db.commit()
    db.refresh(av)
    return av


@router.delete("/link/{link_id}", status_code=204)
def remove_vulnerability_from_asset(
    link_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_module_access("vulnerabilities", write=True)),
):
    """Remove a vulnerability link from an asset."""
    repo = AssetVulnerabilityRepository(db)
    av = repo.get_by_id(link_id)
    if not av:
        raise HTTPException(status_code=404, detail="Asset-vulnerability link not found.")
    repo.delete(av)
    db.commit()
