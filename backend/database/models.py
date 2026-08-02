from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON, Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.config import Base


# ═══════════════════════════════════════════════════════════════
# Phase 1: Business Context — Organization Hierarchy
# ═══════════════════════════════════════════════════════════════


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry_sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    sites = relationship("Site", back_populates="organization", cascade="all, delete-orphan")
    users = relationship("User", back_populates="organization")

    __table_args__ = (
        Index("ix_organizations_name", "name"),
        UniqueConstraint("name", name="uq_organizations_name"),
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name='{self.name}')>"


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    site_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # headquarters, regional, branch, plant
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    organization = relationship("Organization", back_populates="sites")
    plants = relationship("Plant", back_populates="site", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_sites_organization_id", "organization_id"),
        UniqueConstraint("organization_id", "name", name="uq_sites_org_name"),
    )


class Plant(Base):
    __tablename__ = "plants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    plant_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # substation, treatment_plant, factory, refinery
    ics_domain: Mapped[str | None] = mapped_column(String(100), nullable=True)  # power, water, oil_gas, manufacturing
    criticality_level: Mapped[str | None] = mapped_column(String(20), nullable=True)  # critical, high, medium, low
    operational_status: Mapped[str | None] = mapped_column(String(50), nullable=True)  # operational, maintenance, decommissioned
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    site = relationship("Site", back_populates="plants")
    security_zones = relationship("SecurityZone", back_populates="plant", cascade="all, delete-orphan")
    conduits = relationship("Conduit", back_populates="plant", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_plants_site_id", "site_id"),
        UniqueConstraint("site_id", "name", name="uq_plants_site_name"),
    )


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plant_id: Mapped[int | None] = mapped_column(ForeignKey("plants.id", ondelete="CASCADE"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    manager_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


# ═══════════════════════════════════════════════════════════════
# Phase 1: User & Access Control
# ═══════════════════════════════════════════════════════════════


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    organization = relationship("Organization", back_populates="users")
    role = relationship("Role", back_populates="users")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_users_organization_id", "organization_id"),
        Index("ix_users_role_id", "role_id"),
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(String(500), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index("ix_user_sessions_user_id", "user_id"),
        Index("ix_user_sessions_token", "token"),
    )


# ═══════════════════════════════════════════════════════════════
# Phase 1: Zones & Conduits (IEC 62443)
# ═══════════════════════════════════════════════════════════════


class SecurityZone(Base):
    __tablename__ = "security_zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plant_id: Mapped[int] = mapped_column(ForeignKey("plants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    zone_level: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 (Cell/Area) through 5 (Enterprise)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    classification: Mapped[str | None] = mapped_column(String(50), nullable=True)  # safety_critical, security_critical, operational, business
    access_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    plant = relationship("Plant", back_populates="security_zones")
    conduits_from = relationship("Conduit", foreign_keys="Conduit.source_zone_id", back_populates="source_zone", cascade="all, delete-orphan")
    conduits_to = relationship("Conduit", foreign_keys="Conduit.destination_zone_id", back_populates="destination_zone", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_security_zones_plant_id", "plant_id"),
        UniqueConstraint("plant_id", "name", name="uq_security_zones_plant_name"),
    )


class Conduit(Base):
    __tablename__ = "conduits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plant_id: Mapped[int] = mapped_column(ForeignKey("plants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_zone_id: Mapped[int] = mapped_column(ForeignKey("security_zones.id", ondelete="CASCADE"), nullable=False)
    destination_zone_id: Mapped[int] = mapped_column(ForeignKey("security_zones.id", ondelete="CASCADE"), nullable=False)
    conduit_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # network, physical, wireless
    communication_protocols: Mapped[str | None] = mapped_column(Text, nullable=True)
    security_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_encrypted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_physically_secured: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    plant = relationship("Plant", back_populates="conduits")
    source_zone = relationship("SecurityZone", foreign_keys=[source_zone_id], back_populates="conduits_from")
    destination_zone = relationship("SecurityZone", foreign_keys=[destination_zone_id], back_populates="conduits_to")

    __table_args__ = (
        Index("ix_conduits_plant_id", "plant_id"),
        UniqueConstraint("plant_id", "name", name="uq_conduits_plant_name"),
    )


# ═══════════════════════════════════════════════════════════════
# Phase 1: Extended Asset Register
# ═══════════════════════════════════════════════════════════════


class AssetCategory(Base):
    __tablename__ = "asset_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("asset_categories.id", ondelete="CASCADE"), nullable=True)
    ics_category: Mapped[str | None] = mapped_column(String(50), nullable=True)  # controller, network, hmi, server, iot, physical, human
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    children = relationship("AssetCategory", back_populates="parent", cascade="all, delete-orphan")
    parent = relationship("AssetCategory", back_populates="children", remote_side="AssetCategory.id")


class ExtendedAsset(Base):
    """Extended asset register with full GRC fields (separate from Bayesian Asset)."""
    __tablename__ = "extended_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id", ondelete="SET NULL"), nullable=True)
    plant_id: Mapped[int | None] = mapped_column(ForeignKey("plants.id", ondelete="SET NULL"), nullable=True)
    security_zone_id: Mapped[int | None] = mapped_column(ForeignKey("security_zones.id", ondelete="SET NULL"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("asset_categories.id", ondelete="SET NULL"), nullable=True)

    # Identity
    asset_tag: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    alias: Mapped[str | None] = mapped_column(String(255), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Categorization
    asset_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # plc, rtu, hmi, scada_server, etc.
    sub_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Classification
    criticality: Mapped[str | None] = mapped_column(String(20), nullable=True)  # critical, high, medium, low
    data_sensitivity: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Technical
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    software_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    operating_system: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    mac_address: Mapped[str | None] = mapped_column(String(17), nullable=True)
    network_segment: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Operational
    operational_status: Mapped[str | None] = mapped_column(String(50), nullable=True)  # operational, standby, maintenance, retired
    commissioning_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    last_maintenance_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    expected_lifetime_years: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Risk Parameters (for Bayesian engine)
    exposure_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    patch_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    availability_requirement: Mapped[str | None] = mapped_column(String(20), nullable=True)
    integrity_requirement: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidentiality_requirement: Mapped[str | None] = mapped_column(String(20), nullable=True)
    intrinsic_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    consequence_severity: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Ownership
    asset_owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    technical_owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Location
    location_building: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_room: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_rack: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location_rack_position: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Spatial (for topology visualization)
    x_position: Mapped[float | None] = mapped_column(Float, nullable=True)
    y_position: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Lifecycle
    lifecycle_status: Mapped[str | None] = mapped_column(String(30), nullable=True)  # planned, active, decommissioned
    decommissioned_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_extended_assets_organization_id", "organization_id"),
        Index("ix_extended_assets_site_id", "site_id"),
        Index("ix_extended_assets_plant_id", "plant_id"),
        Index("ix_extended_assets_zone_id", "security_zone_id"),
        Index("ix_extended_assets_name", "name"),
    )


class AssetDependency(Base):
    __tablename__ = "asset_dependencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("extended_assets.id", ondelete="CASCADE"), nullable=False)
    depends_on_asset_id: Mapped[int] = mapped_column(ForeignKey("extended_assets.id", ondelete="CASCADE"), nullable=False)
    dependency_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # network, power, data, physical
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    criticality: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("asset_id", "depends_on_asset_id", "dependency_type", name="uq_asset_dependency"),
    )


# ═══════════════════════════════════════════════════════════════
# Phase 1: Audit Trail (Foundation for all modules)
# ═══════════════════════════════════════════════════════════════


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # create, update, delete, approve, reject
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metadata_payload: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_user", "user_id"),
        Index("ix_audit_logs_created", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════
# Phase 2a: Threat & Vulnerability Management
# ═══════════════════════════════════════════════════════════════


class ThreatCategory(Base):
    """Taxonomy for categorizing threats (STRIDE, MITRE ICS, etc.)."""
    __tablename__ = "threat_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_framework: Mapped[str | None] = mapped_column(String(50), nullable=True)  # stride, mitre_ics, custom
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    threats = relationship("Threat", back_populates="threat_category", cascade="all, delete-orphan")


class Threat(Base):
    """Threat library entry (e.g., T0886 from MITRE ICS)."""
    __tablename__ = "threats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    threat_category_id: Mapped[int | None] = mapped_column(ForeignKey("threat_categories.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    threat_id: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g., T0886 (MITRE ICS)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)  # mitre_ics, stride, custom
    likelihood_rating: Mapped[str | None] = mapped_column(String(20), nullable=True)  # very_high, high, medium, low, very_low
    typical_impact: Mapped[str | None] = mapped_column(String(50), nullable=True)  # safety, environmental, operational, financial
    ics_impact: Mapped[str | None] = mapped_column(String(50), nullable=True)  # loss_of_view, loss_of_control, equipment_damage
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    threat_category = relationship("ThreatCategory", back_populates="threats")

    __table_args__ = (
        Index("ix_threats_threat_category_id", "threat_category_id"),
    )


class ThreatActor(Base):
    """Threat actor profile (nation-state, criminal, insider, etc.)."""
    __tablename__ = "threat_actors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # nation_state, criminal, hacktivist, insider, terrorist
    capability: Mapped[str | None] = mapped_column(String(30), nullable=True)  # advanced, moderate, basic
    motivation: Mapped[str | None] = mapped_column(String(100), nullable=True)  # financial, espionage, sabotage, ideological
    targeting_sectors: Mapped[str | None] = mapped_column(Text, nullable=True)
    common_ttps: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class Vulnerability(Base):
    """Vulnerability registry with CVE and CVSS scoring."""
    __tablename__ = "vulnerabilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cve_id: Mapped[str | None] = mapped_column(String(30), nullable=True, unique=True)  # CVE-YYYY-NNNNN
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    vulnerability_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # buffer_overflow, xss, auth_bypass, etc.
    cvss_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    cvss_vector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cvss_severity: Mapped[str | None] = mapped_column(String(20), nullable=True)  # none, low, medium, high, critical
    ics_impact: Mapped[str | None] = mapped_column(String(50), nullable=True)
    exploit_available: Mapped[bool] = mapped_column(Boolean, default=False)
    exploitability: Mapped[str | None] = mapped_column(String(30), nullable=True)  # easy, moderate, difficult
    affected_vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    affected_product: Mapped[str | None] = mapped_column(String(255), nullable=True)
    affected_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    patch_available: Mapped[bool] = mapped_column(Boolean, default=False)
    patch_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    discovered_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_vulnerabilities_cve_id", "cve_id"),
        Index("ix_vulnerabilities_cvss_severity", "cvss_severity"),
    )


class AssetVulnerability(Base):
    """Many-to-many link between assets and vulnerabilities with status tracking."""
    __tablename__ = "asset_vulnerabilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("extended_assets.id", ondelete="CASCADE"), nullable=False)
    vulnerability_id: Mapped[int] = mapped_column(ForeignKey("vulnerabilities.id", ondelete="CASCADE"), nullable=False)
    detected_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    detection_method: Mapped[str | None] = mapped_column(String(50), nullable=True)  # scan, manual, vendor_advisory
    status: Mapped[str] = mapped_column(String(30), default="open")  # open, in_progress, mitigated, accepted, resolved
    mitigation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_asset_vulnerabilities_asset_id", "asset_id"),
        Index("ix_asset_vulnerabilities_vulnerability_id", "vulnerability_id"),
    )

# ═══════════════════════════════════════════════════════════════


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    assets = relationship("Asset", back_populates="project", cascade="all, delete-orphan")
    connections = relationship("Connection", back_populates="project", cascade="all, delete-orphan")
    bayesian_nodes = relationship("BayesianNode", back_populates="project", cascade="all, delete-orphan")
    cpts = relationship("CPT", back_populates="project", cascade="all, delete-orphan")
    inference_results = relationship("InferenceResult", back_populates="project", cascade="all, delete-orphan")
    risk_results = relationship("RiskResult", back_populates="project", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="project", cascade="all, delete-orphan")
    settings = relationship("ApplicationSetting", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_projects_name", "name"),
        UniqueConstraint("name", name="uq_projects_name"),
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}', industry='{self.industry}')>"

    def __str__(self) -> str:
        return f"Project: {self.name}"


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    asset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    zone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exposure_level: Mapped[str | None] = mapped_column(String(255), nullable=True)
    patch_level: Mapped[str | None] = mapped_column(String(255), nullable=True)
    criticality: Mapped[str | None] = mapped_column(String(255), nullable=True)
    availability_requirement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    integrity_requirement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidentiality_requirement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    intrinsic_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    x_position: Mapped[float | None] = mapped_column(Float, nullable=True)
    y_position: Mapped[float | None] = mapped_column(Float, nullable=True)

    project = relationship("Project", back_populates="assets")
    inference_results = relationship("InferenceResult", back_populates="asset", cascade="all, delete-orphan")
    risk_results = relationship("RiskResult", back_populates="asset", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_assets_project_id", "project_id"),
        Index("ix_assets_asset_name", "asset_name"),
        UniqueConstraint("project_id", "asset_name", name="uq_assets_project_asset"),
    )


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    source_asset: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_asset: Mapped[str] = mapped_column(String(255), nullable=False)
    relationship_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    propagation_weight: Mapped[float | None] = mapped_column(Float, nullable=True)

    project = relationship("Project", back_populates="connections")

    __table_args__ = (
        Index("ix_connections_project_id", "project_id"),
        UniqueConstraint("project_id", "source_asset", "destination_asset", name="uq_connections_project_edge"),
    )


class BayesianNode(Base):
    __tablename__ = "bayesian_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    node_name: Mapped[str] = mapped_column(String(255), nullable=False)
    node_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_payload: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

    project = relationship("Project", back_populates="bayesian_nodes")

    __table_args__ = (
        Index("ix_bayesian_nodes_project_id", "project_id"),
        UniqueConstraint("project_id", "node_name", name="uq_bayesian_nodes_project_name"),
    )


class CPT(Base):
    __tablename__ = "cpts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    node_name: Mapped[str] = mapped_column(String(255), nullable=False)
    table_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    project = relationship("Project", back_populates="cpts")

    __table_args__ = (
        Index("ix_cpts_project_id", "project_id"),
        UniqueConstraint("project_id", "node_name", name="uq_cpts_project_node"),
    )


class InferenceResult(Base):
    __tablename__ = "inference_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=True)
    asset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    posterior_probability: Mapped[float] = mapped_column(Float, nullable=False)
    inference_timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    project = relationship("Project", back_populates="inference_results")
    asset = relationship("Asset", back_populates="inference_results")

    __table_args__ = (
        Index("ix_inference_results_project_id", "project_id"),
        Index("ix_inference_results_asset_id", "asset_id"),
    )


class RiskResult(Base):
    __tablename__ = "risk_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=True)
    asset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    likelihood: Mapped[float | None] = mapped_column(Float, nullable=True)
    impact: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(255), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    project = relationship("Project", back_populates="risk_results")
    asset = relationship("Asset", back_populates="risk_results")

    __table_args__ = (
        Index("ix_risk_results_project_id", "project_id"),
        Index("ix_risk_results_asset_id", "asset_id"),
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    project = relationship("Project", back_populates="reports")

    __table_args__ = (
        Index("ix_reports_project_id", "project_id"),
        UniqueConstraint("project_id", "filename", name="uq_reports_project_filename"),
    )


class ApplicationSetting(Base):
    __tablename__ = "application_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    project = relationship("Project", back_populates="settings")

    __table_args__ = (
        Index("ix_application_settings_key", "key"),
        UniqueConstraint("project_id", "key", name="uq_application_settings_project_key"),
    )


# ═══════════════════════════════════════════════════════════════
# Phase 2b: Control Library
# ═══════════════════════════════════════════════════════════════


class ControlCategory(Base):
    """Taxonomy for controls (preventive, detective, corrective, etc.)."""
    __tablename__ = "control_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    control_type: Mapped[str | None] = mapped_column(String(30), nullable=True)  # preventive, detective, corrective, deterrent
    ics_control_domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    controls = relationship("Control", back_populates="control_category", cascade="all, delete-orphan")


class Control(Base):
    """Control library entry with implementation status and effectiveness."""
    __tablename__ = "controls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    control_category_id: Mapped[int | None] = mapped_column(ForeignKey("control_categories.id", ondelete="SET NULL"), nullable=True)
    control_id: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    control_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    implementation_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    effectiveness_rating: Mapped[str | None] = mapped_column(String(20), nullable=True)
    automation_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    evidence_required: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_reviewed_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    next_review_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    control_category = relationship("ControlCategory", back_populates="controls")
    tests = relationship("ControlTest", back_populates="control", cascade="all, delete-orphan")
    evidence = relationship("ControlEvidence", back_populates="control", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_controls_control_category_id", "control_category_id"),
    )


class ControlTest(Base):
    """Control test record."""
    __tablename__ = "control_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    control_id: Mapped[int] = mapped_column(ForeignKey("controls.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("extended_assets.id", ondelete="SET NULL"), nullable=True)
    tester_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    test_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    test_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    test_procedure: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(String(30), nullable=True)
    result_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    next_test_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    control = relationship("Control", back_populates="tests")

    __table_args__ = (
        Index("ix_control_tests_control_id", "control_id"),
    )


class ControlEvidence(Base):
    """Control evidence document."""
    __tablename__ = "control_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    control_id: Mapped[int] = mapped_column(ForeignKey("controls.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("extended_assets.id", ondelete="SET NULL"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    evidence_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    collected_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    collected_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[Date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    control = relationship("Control", back_populates="evidence")

    __table_args__ = (
        Index("ix_control_evidence_control_id", "control_id"),
    )


# ═══════════════════════════════════════════════════════════════
# Phase 2c: Risk Register & Treatment
# ═══════════════════════════════════════════════════════════════


class RiskItem(Base):
    """Risk register item with inherent/residual risk and treatment tracking."""
    __tablename__ = "risk_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    plant_id: Mapped[int | None] = mapped_column(ForeignKey("plants.id", ondelete="SET NULL"), nullable=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("extended_assets.id", ondelete="SET NULL"), nullable=True)
    threat_id: Mapped[int | None] = mapped_column(ForeignKey("threats.id", ondelete="SET NULL"), nullable=True)
    vulnerability_id: Mapped[int | None] = mapped_column(ForeignKey("vulnerabilities.id", ondelete="SET NULL"), nullable=True)
    bayesian_risk_result_id: Mapped[int | None] = mapped_column(ForeignKey("risk_results.id", ondelete="SET NULL"), nullable=True)

    risk_id: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scenario: Mapped[str | None] = mapped_column(Text, nullable=True)

    inherent_likelihood: Mapped[float | None] = mapped_column(Float, nullable=True)
    inherent_impact: Mapped[float | None] = mapped_column(Float, nullable=True)
    inherent_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    inherent_risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)

    residual_likelihood: Mapped[float | None] = mapped_column(Float, nullable=True)
    residual_impact: Mapped[float | None] = mapped_column(Float, nullable=True)
    residual_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    residual_risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)

    bayesian_likelihood: Mapped[float | None] = mapped_column(Float, nullable=True)
    bayesian_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    bayesian_risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)

    risk_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    risk_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    consequence: Mapped[str | None] = mapped_column(Text, nullable=True)

    treatment_strategy: Mapped[str | None] = mapped_column(String(30), nullable=True)
    treatment_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    risk_owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    review_frequency: Mapped[str | None] = mapped_column(String(30), nullable=True)
    last_reviewed_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    next_review_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    is_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    accepted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    acceptance_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    acceptance_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="identified")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    scenarios = relationship("RiskScenario", back_populates="risk_item", cascade="all, delete-orphan")
    treatment_plans = relationship("RiskTreatmentPlan", back_populates="risk_item", cascade="all, delete-orphan")
    acceptances = relationship("RiskAcceptance", back_populates="risk_item", cascade="all, delete-orphan")
    history = relationship("RiskHistory", back_populates="risk_item", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_risk_items_organization_id", "organization_id"),
        Index("ix_risk_items_plant_id", "plant_id"),
        Index("ix_risk_items_asset_id", "asset_id"),
        Index("ix_risk_items_status", "status"),
    )


class RiskScenario(Base):
    """Risk scenario linked to a risk item."""
    __tablename__ = "risk_scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    risk_item_id: Mapped[int] = mapped_column(ForeignKey("risk_items.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_used: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    inherent_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    residual_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    risk_item = relationship("RiskItem", back_populates="scenarios")


class RiskTreatmentPlan(Base):
    """Risk treatment plan."""
    __tablename__ = "risk_treatment_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    risk_item_id: Mapped[int] = mapped_column(ForeignKey("risk_items.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    treatment_option: Mapped[str | None] = mapped_column(String(30), nullable=True)
    target_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    cost_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_currency: Mapped[str | None] = mapped_column(String(3), default="USD")
    responsible_person_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    approval_status: Mapped[str] = mapped_column(String(30), default="pending")
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approval_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    effectiveness_review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    effectiveness_review_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    risk_item = relationship("RiskItem", back_populates="treatment_plans")


class RiskAcceptance(Base):
    """Formal risk acceptance record."""
    __tablename__ = "risk_acceptances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    risk_item_id: Mapped[int] = mapped_column(ForeignKey("risk_items.id", ondelete="CASCADE"), nullable=False)
    accepted_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    acceptance_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    expiration_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    reviewing_authority: Mapped[str | None] = mapped_column(String(255), nullable=True)
    conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    risk_item = relationship("RiskItem", back_populates="acceptances")


class RiskHistory(Base):
    """Audit trail for risk item changes."""
    __tablename__ = "risk_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    risk_item_id: Mapped[int] = mapped_column(ForeignKey("risk_items.id", ondelete="CASCADE"), nullable=False)
    changed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    change_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    previous_values: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    risk_item = relationship("RiskItem", back_populates="history")


# ═══════════════════════════════════════════════════════════════
# Phase 2d: Compliance Framework
# ═══════════════════════════════════════════════════════════════


class ComplianceFramework(Base):
    """Compliance framework (ISO 27001, NIST CSF, IEC 62443, etc.)."""
    __tablename__ = "compliance_frameworks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    requirements = relationship("FrameworkRequirement", back_populates="framework", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_frameworks_name_version"),
    )


class FrameworkRequirement(Base):
    """Individual requirement within a compliance framework."""
    __tablename__ = "framework_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    framework_id: Mapped[int] = mapped_column(ForeignKey("compliance_frameworks.id", ondelete="CASCADE"), nullable=False)
    requirement_id: Mapped[str] = mapped_column(String(50), nullable=False)
    parent_requirement_id: Mapped[int | None] = mapped_column(ForeignKey("framework_requirements.id", ondelete="CASCADE"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirement_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    implementation_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight_importance: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sort_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    framework = relationship("ComplianceFramework", back_populates="requirements")
    control_mappings = relationship("ControlMapping", back_populates="requirement", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_framework_requirements_framework_id", "framework_id"),
        UniqueConstraint("framework_id", "requirement_id", name="uq_framework_requirement"),
    )


class ControlMapping(Base):
    """Mapping between controls and framework requirements."""
    __tablename__ = "control_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    control_id: Mapped[int] = mapped_column(ForeignKey("controls.id", ondelete="CASCADE"), nullable=False)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("framework_requirements.id", ondelete="CASCADE"), nullable=False)
    mapping_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    mapping_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    mapping_justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    requirement = relationship("FrameworkRequirement", back_populates="control_mappings")

    __table_args__ = (
        UniqueConstraint("control_id", "requirement_id", name="uq_control_requirement_mapping"),
    )


class ComplianceGap(Base):
    """Compliance gap identified during assessment."""
    __tablename__ = "compliance_gaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    plant_id: Mapped[int | None] = mapped_column(ForeignKey("plants.id", ondelete="SET NULL"), nullable=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("framework_requirements.id", ondelete="CASCADE"), nullable=False)
    gap_description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str | None] = mapped_column(String(30), default="open")
    remediation_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_closure_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    closed_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_compliance_gaps_requirement_id", "requirement_id"),
    )


class ComplianceAssessment(Base):
    """Compliance assessment record."""
    __tablename__ = "compliance_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    plant_id: Mapped[int | None] = mapped_column(ForeignKey("plants.id", ondelete="SET NULL"), nullable=True)
    framework_id: Mapped[int] = mapped_column(ForeignKey("compliance_frameworks.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    assessment_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    assessor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    overall_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    compliance_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    findings_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_compliance_assessments_framework_id", "framework_id"),
    )


# ═══════════════════════════════════════════════════════════════
# Phase 2d: Audit Management
# ═══════════════════════════════════════════════════════════════


class AuditProgram(Base):
    """Audit program definition."""
    __tablename__ = "audit_programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    program_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    start_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    program_manager_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    audit_plans = relationship("AuditPlan", back_populates="audit_program", cascade="all, delete-orphan")


class AuditPlan(Base):
    """Audit plan within a program."""
    __tablename__ = "audit_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_program_id: Mapped[int | None] = mapped_column(ForeignKey("audit_programs.id", ondelete="CASCADE"), nullable=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    plant_id: Mapped[int | None] = mapped_column(ForeignKey("plants.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    objectives: Mapped[str | None] = mapped_column(Text, nullable=True)
    criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    estimated_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    lead_auditor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    audit_program = relationship("AuditProgram", back_populates="audit_plans")
    findings = relationship("AuditFinding", back_populates="audit_plan", cascade="all, delete-orphan")
    procedures = relationship("AuditProcedure", back_populates="audit_plan", cascade="all, delete-orphan")
    evidence_collections = relationship("AuditEvidenceCollection", back_populates="audit_plan", cascade="all, delete-orphan")
    interviews = relationship("AuditInterview", back_populates="audit_plan", cascade="all, delete-orphan")


class AuditProcedure(Base):
    """Audit procedure/checklist item."""
    __tablename__ = "audit_procedures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_plan_id: Mapped[int] = mapped_column(ForeignKey("audit_plans.id", ondelete="CASCADE"), nullable=False)
    control_id: Mapped[int | None] = mapped_column(ForeignKey("controls.id", ondelete="SET NULL"), nullable=True)
    requirement_id: Mapped[int | None] = mapped_column(ForeignKey("framework_requirements.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    procedure_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    testing_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    audit_plan = relationship("AuditPlan", back_populates="procedures")


class AuditFinding(Base):
    """Audit finding entity with severity and recommendations."""
    __tablename__ = "audit_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_plan_id: Mapped[int] = mapped_column(ForeignKey("audit_plans.id", ondelete="CASCADE"), nullable=False)
    procedure_id: Mapped[int | None] = mapped_column(ForeignKey("audit_procedures.id", ondelete="SET NULL"), nullable=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("extended_assets.id", ondelete="SET NULL"), nullable=True)
    control_id: Mapped[int | None] = mapped_column(ForeignKey("controls.id", ondelete="SET NULL"), nullable=True)

    finding_id: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    finding_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    likelihood: Mapped[str | None] = mapped_column(String(20), nullable=True)

    criteria_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    management_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    response_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    acceptance_of_finding: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    audit_plan = relationship("AuditPlan", back_populates="findings")
    corrective_actions = relationship("CorrectiveAction", back_populates="finding")

    __table_args__ = (
        Index("ix_audit_findings_audit_plan_id", "audit_plan_id"),
        Index("ix_audit_findings_severity", "severity"),
    )


class AuditEvidenceCollection(Base):
    """Audit evidence collection record."""
    __tablename__ = "audit_evidence_collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_plan_id: Mapped[int] = mapped_column(ForeignKey("audit_plans.id", ondelete="CASCADE"), nullable=False)
    procedure_id: Mapped[int | None] = mapped_column(ForeignKey("audit_procedures.id", ondelete="SET NULL"), nullable=True)
    evidence_title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    evidence_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    collected_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    collected_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=False)

    audit_plan = relationship("AuditPlan", back_populates="evidence_collections")


class AuditInterview(Base):
    """Audit interview record."""
    __tablename__ = "audit_interviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_plan_id: Mapped[int] = mapped_column(ForeignKey("audit_plans.id", ondelete="CASCADE"), nullable=False)
    interviewee_name: Mapped[str] = mapped_column(String(255), nullable=False)
    interviewee_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    interviewee_department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    interviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    interview_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    topics_covered: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_findings: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    audit_plan = relationship("AuditPlan", back_populates="interviews")


# ═══════════════════════════════════════════════════════════════
# Phase 2e: Corrective Actions (CAPA)
# ═══════════════════════════════════════════════════════════════


class CorrectiveAction(Base):
    """Corrective action workflow entity."""
    __tablename__ = "corrective_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    finding_id: Mapped[int | None] = mapped_column(ForeignKey("audit_findings.id", ondelete="SET NULL"), nullable=True)
    risk_item_id: Mapped[int | None] = mapped_column(ForeignKey("risk_items.id", ondelete="SET NULL"), nullable=True)
    compliance_gap_id: Mapped[int | None] = mapped_column(ForeignKey("compliance_gaps.id", ondelete="SET NULL"), nullable=True)

    action_id: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    root_cause_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    root_cause_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)

    action_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open")

    assigned_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_date: Mapped[Date | None] = mapped_column(Date, nullable=True)

    target_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    extended_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    completed_date: Mapped[Date | None] = mapped_column(Date, nullable=True)

    implementation_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    implementation_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    verifier_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verification_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    verification_result: Mapped[str | None] = mapped_column(String(30), nullable=True)
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    closure_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    closed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    closed_date: Mapped[Date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    finding = relationship("AuditFinding", back_populates="corrective_actions")
    tasks = relationship("ActionTask", back_populates="corrective_action", cascade="all, delete-orphan")
    effectiveness_reviews = relationship("EffectivenessReview", back_populates="corrective_action", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_corrective_actions_status", "status"),
        Index("ix_corrective_actions_assigned_to_id", "assigned_to_id"),
    )


class ActionTask(Base):
    """Sub-task within a corrective action."""
    __tablename__ = "action_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    corrective_action_id: Mapped[int] = mapped_column(ForeignKey("corrective_actions.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    due_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    completed_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    corrective_action = relationship("CorrectiveAction", back_populates="tasks")


class EffectivenessReview(Base):
    """Effectiveness review for a corrective action."""
    __tablename__ = "effectiveness_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    corrective_action_id: Mapped[int] = mapped_column(ForeignKey("corrective_actions.id", ondelete="CASCADE"), nullable=False)
    review_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(String(30), nullable=True)
    findings: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_required: Mapped[bool] = mapped_column(Boolean, default=False)
    follow_up_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    corrective_action = relationship("CorrectiveAction", back_populates="effectiveness_reviews")
