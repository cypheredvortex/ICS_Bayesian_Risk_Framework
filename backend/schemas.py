"""Pydantic schemas for the API.

Includes request/response models with full documentation and validation.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ═══════════════════════════════════════════════════════════════
# Legacy Schemas (unchanged)
# ═══════════════════════════════════════════════════════════════


class EvidenceEntry(BaseModel):
    """A single piece of evidence: an asset in a known state."""
    asset: str = Field(..., description="Asset identifier", min_length=1)
    state: str | int = Field(
        ...,
        description="Asset state: Unknown, Compromised, Safe, 0, or 1",
    )

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str | int) -> str | int:
        if isinstance(v, int):
            if v not in (0, 1):
                raise ValueError("State integer must be 0 or 1")
            return v
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized not in ("unknown", "compromised", "safe", "0", "1"):
                raise ValueError(
                    "State string must be Unknown, Compromised, Safe, 0, or 1"
                )
            if normalized in ("0", "1"):
                return int(normalized)
            return v
        raise ValueError("State must be a string or integer")


class AnalyzeRequest(BaseModel):
    """Request payload for running a Bayesian risk assessment."""
    topology: dict[str, Any] = Field(
        ...,
        description="Topology JSON payload with assets and relationships",
    )
    evidence: list[EvidenceEntry] = Field(
        default_factory=list,
        description="Optional evidence to condition the Bayesian network",
    )


class TopologyUploadRequest(BaseModel):
    """Request payload for uploading a topology."""
    topology: dict[str, Any] = Field(
        ...,
        description="Topology JSON payload with assets and relationships",
    )


class SettingsUpdateRequest(BaseModel):
    """Request payload for updating runtime settings."""
    settings: dict[str, Any] = Field(
        default_factory=dict,
        description="Settings dictionary with weight overrides",
    )


# ---- Response models ----


class HealthCheckResponse(BaseModel):
    """Health check endpoint response."""
    status: str = Field(..., description="Service status (ok/error)")
    framework: str = Field(..., description="Framework name")
    version: str = Field(..., description="API version")
    database: str = Field(..., description="Database connection status")
    max_upload_size_mb: int = Field(..., description="Maximum upload file size in MB")
    endpoints: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Available API endpoints",
    )


class DatasetInfo(BaseModel):
    """Information about an available dataset."""
    datasets: list[str] = Field(..., description="List of dataset names")
    paths: dict[str, str] = Field(
        ...,
        description="Mapping of dataset names to API paths",
    )


class UploadTopologyResponse(BaseModel):
    """Response after uploading a topology."""
    message: str = Field(..., description="Status message")
    asset_count: int = Field(..., description="Number of assets parsed", ge=0)
    relationship_count: int = Field(..., description="Number of relationships parsed", ge=0)


class UploadTopologyFileResponse(UploadTopologyResponse):
    """Response after uploading a topology file."""
    topology: dict[str, Any] = Field(
        ...,
        description="Parsed topology payload",
    )


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str = Field(..., description="Error detail message")
    error_code: str | None = Field(None, description="Machine-readable error code")
    request_id: str | None = Field(None, description="Request ID for tracing")


# ═══════════════════════════════════════════════════════════════
# Phase 1: Organization Hierarchy Schemas
# ═══════════════════════════════════════════════════════════════


class OrganizationCreate(BaseModel):
    """Request to create an organization."""
    name: str = Field(..., description="Organization name", min_length=1, max_length=255)
    legal_name: str | None = Field(None, description="Legal entity name")
    registration_number: str | None = Field(None, description="Business registration number")
    tax_id: str | None = Field(None, description="Tax identifier")
    industry_sector: str | None = Field(None, description="Industry sector")
    address_line1: str | None = Field(None, description="Street address")
    city: str | None = Field(None, description="City")
    state: str | None = Field(None, description="State/Province")
    postal_code: str | None = Field(None, description="Postal/ZIP code")
    country: str | None = Field(None, description="Country")
    website: str | None = Field(None, description="Website URL")
    phone: str | None = Field(None, description="Phone number")
    email: str | None = Field(None, description="Contact email")


class OrganizationUpdate(BaseModel):
    """Request to update an organization."""
    name: str | None = Field(None, description="Organization name")
    legal_name: str | None = Field(None, description="Legal entity name")
    industry_sector: str | None = Field(None, description="Industry sector")
    city: str | None = Field(None, description="City")
    state: str | None = Field(None, description="State/Province")
    country: str | None = Field(None, description="Country")
    phone: str | None = Field(None, description="Phone number")
    email: str | None = Field(None, description="Contact email")
    is_active: bool | None = Field(None, description="Whether the organization is active")


class OrganizationResponse(BaseModel):
    """Organization response model."""
    id: int = Field(..., description="Organization ID")
    name: str = Field(..., description="Organization name")
    legal_name: str | None = None
    registration_number: str | None = None
    industry_sector: str | None = None
    address_line1: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    website: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SiteCreate(BaseModel):
    """Request to create a site."""
    organization_id: int = Field(..., description="Parent organization ID", ge=1)
    name: str = Field(..., description="Site name", min_length=1, max_length=255)
    code: str | None = Field(None, description="Site code")
    site_type: str | None = Field(None, description="Site type (headquarters, regional, etc.)")
    address_line1: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None


class SiteUpdate(BaseModel):
    """Request to update a site."""
    name: str | None = None
    code: str | None = None
    site_type: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    is_active: bool | None = None


class SiteResponse(BaseModel):
    """Site response model."""
    id: int = Field(..., description="Site ID")
    organization_id: int = Field(..., description="Parent organization ID")
    name: str = Field(..., description="Site name")
    code: str | None = None
    site_type: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PlantCreate(BaseModel):
    """Request to create a plant/facility."""
    site_id: int = Field(..., description="Parent site ID", ge=1)
    name: str = Field(..., description="Plant name", min_length=1, max_length=255)
    code: str | None = None
    plant_type: str | None = Field(None, description="Plant type (substation, factory, etc.)")
    ics_domain: str | None = Field(None, description="ICS domain (power, water, etc.)")
    criticality_level: str | None = Field(None, description="Criticality level")
    operational_status: str | None = Field(None, description="Operational status")


class PlantUpdate(BaseModel):
    """Request to update a plant."""
    name: str | None = None
    plant_type: str | None = None
    ics_domain: str | None = None
    criticality_level: str | None = None
    operational_status: str | None = None
    is_active: bool | None = None


class PlantResponse(BaseModel):
    """Plant response model."""
    id: int = Field(..., description="Plant ID")
    site_id: int = Field(..., description="Parent site ID")
    name: str = Field(..., description="Plant name")
    code: str | None = None
    plant_type: str | None = None
    ics_domain: str | None = None
    criticality_level: str | None = None
    operational_status: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ═══════════════════════════════════════════════════════════════
# Phase 1: User & Auth Schemas
# ═══════════════════════════════════════════════════════════════


class RoleCreate(BaseModel):
    """Request to create a role."""
    name: str = Field(..., description="Role name", min_length=1, max_length=100)
    description: str | None = Field(None, description="Role description")
    is_system_role: bool = Field(False, description="Whether this is a system-protected role")


class RoleResponse(BaseModel):
    """Role response model."""
    id: int
    name: str
    description: str | None = None
    is_system_role: bool = False
    created_at: datetime | None = None


class UserCreate(BaseModel):
    """Request to create a user."""
    username: str = Field(..., description="Username", min_length=3, max_length=100)
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password", min_length=8)
    first_name: str | None = Field(None, description="First name")
    last_name: str | None = Field(None, description="Last name")
    job_title: str | None = Field(None, description="Job title")
    organization_id: int | None = Field(None, description="Organization ID")
    role_id: int | None = Field(None, description="Role ID")
    phone: str | None = None


class UserUpdate(BaseModel):
    """Request to update a user."""
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    phone: str | None = None
    is_active: bool | None = None
    role_id: int | None = None


class UserResponse(BaseModel):
    """User response model."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    organization_id: int | None = None
    role_id: int | None = None
    department_name: str | None = None
    is_active: bool = True
    is_locked: bool = False
    last_login_at: datetime | None = None
    created_at: datetime | None = None


class LoginRequest(BaseModel):
    """Login request."""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class LoginResponse(BaseModel):
    """Login response with tokens."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token lifetime in seconds")
    user: UserResponse


class UserMeResponse(UserResponse):
    """Current-user response with resolved role name and permissions."""
    role_name: str | None = Field(None, description="Role name")
    permissions: list[str] = Field(default_factory=list, description="Effective permission codes")


class PasswordChangeRequest(BaseModel):
    """Request to change the current user's password."""
    current_password: str = Field(..., description="Current password", min_length=1)
    new_password: str = Field(..., description="New password", min_length=8, max_length=128)


# ═══════════════════════════════════════════════════════════════
# Phase 1: Security Zone Schemas
# ═══════════════════════════════════════════════════════════════


class SecurityZoneCreate(BaseModel):
    """Request to create a security zone."""
    plant_id: int = Field(..., description="Parent plant ID", ge=1)
    name: str = Field(..., description="Zone name", min_length=1, max_length=255)
    zone_level: int = Field(..., description="IEC 62443 zone level (1-5)", ge=1, le=5)
    description: str | None = None
    color_hex: str | None = Field(None, description="Display color hex code")
    classification: str | None = Field(None, description="Zone classification")
    access_requirements: str | None = None


class SecurityZoneResponse(BaseModel):
    """Security zone response model."""
    id: int
    plant_id: int
    name: str
    zone_level: int
    description: str | None = None
    color_hex: str | None = None
    classification: str | None = None
    access_requirements: str | None = None
    is_active: bool = True
    created_at: datetime | None = None


class ConduitCreate(BaseModel):
    """Request to create a conduit."""
    plant_id: int = Field(..., description="Parent plant ID", ge=1)
    name: str = Field(..., description="Conduit name", min_length=1)
    source_zone_id: int = Field(..., description="Source zone ID", ge=1)
    destination_zone_id: int = Field(..., description="Destination zone ID", ge=1)
    conduit_type: str | None = Field(None, description="Conduit type (network, physical, wireless)")
    communication_protocols: str | None = Field(None, description="Communication protocols used")
    security_requirements: str | None = None
    is_encrypted: bool = False
    is_physically_secured: bool = False


class ConduitResponse(BaseModel):
    """Conduit response model."""
    id: int
    plant_id: int
    name: str
    source_zone_id: int
    destination_zone_id: int
    conduit_type: str | None = None
    communication_protocols: str | None = None
    security_requirements: str | None = None
    is_encrypted: bool = False
    is_physically_secured: bool = False
    created_at: datetime | None = None


# ═══════════════════════════════════════════════════════════════
# Phase 1: Extended Asset Schemas
# ═══════════════════════════════════════════════════════════════


class AssetCategoryCreate(BaseModel):
    """Request to create an asset category."""
    name: str = Field(..., description="Category name", min_length=1, max_length=255)
    description: str | None = None
    parent_id: int | None = Field(None, description="Parent category ID")
    ics_category: str | None = Field(None, description="ICS category type")


class AssetCategoryResponse(BaseModel):
    """Asset category response model."""
    id: int
    name: str
    description: str | None = None
    parent_id: int | None = None
    ics_category: str | None = None
    created_at: datetime | None = None


class ExtendedAssetCreate(BaseModel):
    """Request to create an extended asset."""
    name: str = Field(..., description="Asset name", min_length=1, max_length=255)
    organization_id: int | None = None
    site_id: int | None = None
    plant_id: int | None = None
    security_zone_id: int | None = None
    category_id: int | None = None
    asset_tag: str | None = None
    asset_type: str | None = Field(None, description="Asset type (plc, rtu, hmi, etc.)")
    serial_number: str | None = None
    vendor: str | None = None
    model: str | None = None
    firmware_version: str | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    criticality: str | None = Field(None, description="Criticality level")
    operational_status: str | None = Field(None, description="Operational status")
    asset_owner_id: int | None = None
    location_building: str | None = None
    location_room: str | None = None
    x_position: float | None = None
    y_position: float | None = None


class ExtendedAssetUpdate(BaseModel):
    """Request to update an extended asset."""
    name: str | None = None
    security_zone_id: int | None = None
    category_id: int | None = None
    asset_type: str | None = None
    vendor: str | None = None
    model: str | None = None
    firmware_version: str | None = None
    ip_address: str | None = None
    criticality: str | None = None
    operational_status: str | None = None
    asset_owner_id: int | None = None
    is_active: bool | None = None


class ExtendedAssetResponse(BaseModel):
    """Extended asset response model."""
    id: int
    name: str
    organization_id: int | None = None
    site_id: int | None = None
    plant_id: int | None = None
    security_zone_id: int | None = None
    category_id: int | None = None
    asset_tag: str | None = None
    asset_type: str | None = None
    serial_number: str | None = None
    vendor: str | None = None
    model: str | None = None
    firmware_version: str | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    criticality: str | None = None
    operational_status: str | None = None
    asset_owner_id: int | None = None
    location_building: str | None = None
    location_room: str | None = None
    x_position: float | None = None
    y_position: float | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ═══════════════════════════════════════════════════════════════
# Phase 1: Audit Log Schemas
# ═══════════════════════════════════════════════════════════════


class AuditLogResponse(BaseModel):
    """Audit log entry response model."""
    id: int
    user_id: int | None = None
    action: str
    entity_type: str
    entity_id: int | None = None
    organization_id: int | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    changes: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime | None = None


class AuditLogListResponse(BaseModel):
    """Audit log list response model."""
    total: int
    logs: list[AuditLogResponse]


# ═══════════════════════════════════════════════════════════════
# Phase 2a: Threat & Vulnerability Schemas
# ═══════════════════════════════════════════════════════════════


class ThreatCategoryCreate(BaseModel):
    """Request to create a threat category."""
    name: str = Field(..., description="Category name", min_length=1, max_length=255)
    description: str | None = Field(None, description="Category description")
    reference_framework: str | None = Field(None, description="Reference framework (stride, mitre_ics, custom)")


class ThreatCategoryResponse(BaseModel):
    """Threat category response model."""
    id: int
    name: str
    description: str | None = None
    reference_framework: str | None = None
    created_at: datetime | None = None


class ThreatCreate(BaseModel):
    """Request to create a threat."""
    threat_category_id: int | None = Field(None, description="Threat category ID")
    name: str = Field(..., description="Threat name", min_length=1, max_length=255)
    description: str | None = None
    threat_id: str | None = Field(None, description="MITRE ICS ID (e.g., T0886)")
    source: str | None = Field(None, description="Source (mitre_ics, stride, custom)")
    likelihood_rating: str | None = Field(None, description="Likelihood rating")
    typical_impact: str | None = Field(None, description="Typical impact type")
    ics_impact: str | None = Field(None, description="ICS-specific impact")


class ThreatUpdate(BaseModel):
    """Request to update a threat."""
    name: str | None = None
    description: str | None = None
    threat_category_id: int | None = None
    threat_id: str | None = None
    likelihood_rating: str | None = None
    typical_impact: str | None = None
    ics_impact: str | None = None


class ThreatResponse(BaseModel):
    """Threat response model."""
    id: int
    threat_category_id: int | None = None
    name: str
    description: str | None = None
    threat_id: str | None = None
    source: str | None = None
    likelihood_rating: str | None = None
    typical_impact: str | None = None
    ics_impact: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ThreatActorCreate(BaseModel):
    """Request to create a threat actor."""
    name: str = Field(..., description="Actor name", min_length=1, max_length=255)
    description: str | None = None
    actor_type: str | None = Field(None, description="Actor type (nation_state, criminal, hacktivist, insider, terrorist)")
    capability: str | None = Field(None, description="Capability level (advanced, moderate, basic)")
    motivation: str | None = Field(None, description="Motivation")
    targeting_sectors: str | None = None
    common_ttps: str | None = None


class ThreatActorResponse(BaseModel):
    """Threat actor response model."""
    id: int
    name: str
    description: str | None = None
    actor_type: str | None = None
    capability: str | None = None
    motivation: str | None = None
    targeting_sectors: str | None = None
    common_ttps: str | None = None
    is_active: bool = True
    created_at: datetime | None = None


class VulnerabilityCreate(BaseModel):
    """Request to create a vulnerability."""
    cve_id: str | None = Field(None, description="CVE identifier (CVE-YYYY-NNNNN)")
    name: str = Field(..., description="Vulnerability name", min_length=1, max_length=255)
    description: str | None = None
    vulnerability_type: str | None = None
    cvss_score: float | None = Field(None, description="CVSS score (0-10)", ge=0, le=10)
    cvss_vector: str | None = None
    cvss_severity: str | None = Field(None, description="CVSS severity (none, low, medium, high, critical)")
    ics_impact: str | None = None
    exploit_available: bool = False
    exploitability: str | None = None
    affected_vendor: str | None = None
    affected_product: str | None = None
    affected_version: str | None = None
    patch_available: bool = False
    patch_url: str | None = None
    published_date: str | None = None
    discovered_date: str | None = None


class VulnerabilityUpdate(BaseModel):
    """Request to update a vulnerability."""
    name: str | None = None
    description: str | None = None
    cvss_score: float | None = None
    cvss_severity: str | None = None
    exploit_available: bool | None = None
    patch_available: bool | None = None
    patch_url: str | None = None


class VulnerabilityResponse(BaseModel):
    """Vulnerability response model."""
    id: int
    cve_id: str | None = None
    name: str
    description: str | None = None
    vulnerability_type: str | None = None
    cvss_score: float | None = None
    cvss_vector: str | None = None
    cvss_severity: str | None = None
    ics_impact: str | None = None
    exploit_available: bool = False
    exploitability: str | None = None
    affected_vendor: str | None = None
    affected_product: str | None = None
    affected_version: str | None = None
    patch_available: bool = False
    patch_url: str | None = None
    published_date: str | None = None
    discovered_date: str | None = None
    created_at: datetime | None = None


class AssetVulnerabilityCreate(BaseModel):
    """Request to link a vulnerability to an asset."""
    asset_id: int = Field(..., description="Asset ID", ge=1)
    vulnerability_id: int = Field(..., description="Vulnerability ID", ge=1)
    detected_date: str | None = None
    detection_method: str | None = Field(None, description="Detection method (scan, manual, vendor_advisory)")
    status: str = Field("open", description="Remediation status")
    mitigation_notes: str | None = None


class AssetVulnerabilityUpdate(BaseModel):
    """Request to update an asset-vulnerability link."""
    status: str | None = None
    mitigation_notes: str | None = None
    resolved_date: str | None = None


class AssetVulnerabilityResponse(BaseModel):
    """Asset-vulnerability link response model."""
    id: int
    asset_id: int
    vulnerability_id: int
    detected_date: str | None = None
    detection_method: str | None = None
    status: str
    mitigation_notes: str | None = None
    resolved_date: str | None = None
    created_at: datetime | None = None


# ═══════════════════════════════════════════════════════════════
# Phase 2b: Control Library Schemas
# ═══════════════════════════════════════════════════════════════


class ControlCategoryCreate(BaseModel):
    """Request to create a control category."""
    name: str = Field(..., description="Category name", min_length=1, max_length=255)
    description: str | None = None
    control_type: str | None = Field(None, description="preventive, detective, corrective, deterrent")
    ics_control_domain: str | None = None


class ControlCategoryResponse(BaseModel):
    """Control category response model."""
    id: int
    name: str
    description: str | None = None
    control_type: str | None = None
    ics_control_domain: str | None = None
    created_at: datetime | None = None


class ControlCreate(BaseModel):
    """Request to create a control."""
    control_category_id: int | None = None
    control_id: str | None = Field(None, description="Unique control identifier (e.g., AC-1, ICS-01)")
    name: str = Field(..., description="Control name", min_length=1, max_length=255)
    description: str | None = None
    control_type: str | None = Field(None, description="preventive, detective, corrective, deterrent")
    implementation_status: str | None = Field(None, description="implemented, partially, planned, not_implemented")
    effectiveness_rating: str | None = Field(None, description="very_high, high, medium, low, very_low")
    automation_level: str | None = Field(None, description="automated, semi_automated, manual")
    frequency: str | None = Field(None, description="continuous, daily, weekly, monthly, annually")
    owner_id: int | None = None
    evidence_required: bool = False
    evidence_description: str | None = None
    last_reviewed_date: str | None = None
    next_review_date: str | None = None


class ControlUpdate(BaseModel):
    """Request to update a control."""
    name: str | None = None
    description: str | None = None
    control_category_id: int | None = None
    control_type: str | None = None
    implementation_status: str | None = None
    effectiveness_rating: str | None = None
    automation_level: str | None = None
    frequency: str | None = None
    owner_id: int | None = None
    evidence_required: bool | None = None
    evidence_description: str | None = None
    last_reviewed_date: str | None = None
    next_review_date: str | None = None
    is_active: bool | None = None


class ControlResponse(BaseModel):
    """Control response model."""
    id: int
    control_category_id: int | None = None
    control_id: str | None = None
    name: str
    description: str | None = None
    control_type: str | None = None
    implementation_status: str | None = None
    effectiveness_rating: str | None = None
    automation_level: str | None = None
    frequency: str | None = None
    owner_id: int | None = None
    evidence_required: bool = False
    evidence_description: str | None = None
    last_reviewed_date: str | None = None
    next_review_date: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ControlTestCreate(BaseModel):
    """Request to create a control test."""
    control_id: int = Field(..., description="Control ID", ge=1)
    asset_id: int | None = None
    tester_id: int | None = None
    test_date: str | None = None
    test_method: str | None = Field(None, description="interview, observation, examination, technical")
    test_procedure: str | None = None
    result: str | None = Field(None, description="pass, fail, partial, not_tested, na")
    result_details: str | None = None
    evidence_path: str | None = None
    next_test_date: str | None = None


class ControlTestUpdate(BaseModel):
    """Request to update a control test."""
    result: str | None = None
    result_details: str | None = None
    evidence_path: str | None = None
    next_test_date: str | None = None


class ControlTestResponse(BaseModel):
    """Control test response model."""
    id: int
    control_id: int
    asset_id: int | None = None
    tester_id: int | None = None
    test_date: str | None = None
    test_method: str | None = None
    test_procedure: str | None = None
    result: str | None = None
    result_details: str | None = None
    evidence_path: str | None = None
    next_test_date: str | None = None
    created_at: datetime | None = None


class ControlEvidenceCreate(BaseModel):
    """Request to create control evidence."""
    control_id: int = Field(..., description="Control ID", ge=1)
    asset_id: int | None = None
    filename: str = Field(..., description="Evidence filename")
    file_path: str = Field(..., description="Evidence file path")
    file_type: str | None = None
    evidence_type: str | None = Field(None, description="screenshot, config, policy, log, certification")
    description: str | None = None
    collected_by_id: int | None = None
    collected_date: str | None = None
    valid_until: str | None = None
    is_current: bool = True


class ControlEvidenceResponse(BaseModel):
    """Control evidence response model."""
    id: int
    control_id: int
    asset_id: int | None = None
    filename: str
    file_path: str
    file_type: str | None = None
    evidence_type: str | None = None
    description: str | None = None
    collected_by_id: int | None = None
    collected_date: str | None = None
    valid_until: str | None = None
    is_current: bool = True
    created_at: datetime | None = None


# ═══════════════════════════════════════════════════════════════
# Phase 2c: Risk Register & Treatment Schemas
# ═══════════════════════════════════════════════════════════════


class RiskItemCreate(BaseModel):
    """Request to create a risk item."""
    project_id: int | None = None
    organization_id: int | None = None
    plant_id: int | None = None
    asset_id: int | None = None
    threat_id: int | None = None
    vulnerability_id: int | None = None
    bayesian_risk_result_id: int | None = None
    risk_id: str | None = Field(None, description="Unique risk identifier (e.g., RISK-2024-0001)")
    title: str = Field(..., description="Risk title", min_length=1, max_length=500)
    description: str | None = None
    scenario: str | None = None
    inherent_likelihood: float | None = None
    inherent_impact: float | None = None
    inherent_risk: float | None = None
    inherent_risk_level: str | None = None
    residual_likelihood: float | None = None
    residual_impact: float | None = None
    residual_risk: float | None = None
    residual_risk_level: str | None = None
    bayesian_likelihood: float | None = None
    bayesian_risk_score: float | None = None
    bayesian_risk_level: str | None = None
    risk_type: str | None = Field(None, description="strategic, operational, financial, compliance, security")
    risk_category: str | None = None
    root_cause: str | None = None
    consequence: str | None = None
    treatment_strategy: str | None = Field(None, description="mitigate, transfer, accept, avoid")
    treatment_status: str | None = None
    risk_owner_id: int | None = None
    review_frequency: str | None = Field(None, description="monthly, quarterly, annually")
    last_reviewed_date: str | None = None
    next_review_date: str | None = None
    status: str = Field("identified", description="identified, assessed, treatment_planned, in_progress, closed")


class RiskItemUpdate(BaseModel):
    """Request to update a risk item."""
    title: str | None = None
    description: str | None = None
    scenario: str | None = None
    asset_id: int | None = None
    threat_id: int | None = None
    vulnerability_id: int | None = None
    inherent_likelihood: float | None = None
    inherent_impact: float | None = None
    inherent_risk: float | None = None
    inherent_risk_level: str | None = None
    residual_likelihood: float | None = None
    residual_impact: float | None = None
    residual_risk: float | None = None
    residual_risk_level: str | None = None
    bayesian_likelihood: float | None = None
    bayesian_risk_score: float | None = None
    bayesian_risk_level: str | None = None
    risk_type: str | None = None
    risk_category: str | None = None
    root_cause: str | None = None
    consequence: str | None = None
    treatment_strategy: str | None = None
    treatment_status: str | None = None
    risk_owner_id: int | None = None
    review_frequency: str | None = None
    last_reviewed_date: str | None = None
    next_review_date: str | None = None
    status: str | None = None
    is_accepted: bool | None = None
    acceptance_reason: str | None = None
    is_active: bool | None = None


class RiskItemResponse(BaseModel):
    """Risk item response model."""
    id: int
    project_id: int | None = None
    organization_id: int | None = None
    plant_id: int | None = None
    asset_id: int | None = None
    threat_id: int | None = None
    vulnerability_id: int | None = None
    bayesian_risk_result_id: int | None = None
    risk_id: str | None = None
    title: str
    description: str | None = None
    scenario: str | None = None
    inherent_likelihood: float | None = None
    inherent_impact: float | None = None
    inherent_risk: float | None = None
    inherent_risk_level: str | None = None
    residual_likelihood: float | None = None
    residual_impact: float | None = None
    residual_risk: float | None = None
    residual_risk_level: str | None = None
    bayesian_likelihood: float | None = None
    bayesian_risk_score: float | None = None
    bayesian_risk_level: str | None = None
    risk_type: str | None = None
    risk_category: str | None = None
    root_cause: str | None = None
    consequence: str | None = None
    treatment_strategy: str | None = None
    treatment_status: str | None = None
    risk_owner_id: int | None = None
    review_frequency: str | None = None
    last_reviewed_date: str | None = None
    next_review_date: str | None = None
    is_accepted: bool = False
    accepted_by_id: int | None = None
    acceptance_date: str | None = None
    acceptance_reason: str | None = None
    status: str = "identified"
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RiskScenarioCreate(BaseModel):
    """Request to create a risk scenario."""
    risk_item_id: int = Field(..., description="Risk item ID", ge=1)
    name: str = Field(..., description="Scenario name", min_length=1, max_length=255)
    description: str | None = None
    evidence_used: dict[str, Any] | None = None
    inherent_risk: float | None = None
    residual_risk: float | None = None


class RiskScenarioResponse(BaseModel):
    """Risk scenario response model."""
    id: int
    risk_item_id: int
    name: str
    description: str | None = None
    evidence_used: dict[str, Any] | None = None
    inherent_risk: float | None = None
    residual_risk: float | None = None
    created_at: datetime | None = None


class RiskTreatmentPlanCreate(BaseModel):
    """Request to create a risk treatment plan."""
    risk_item_id: int = Field(..., description="Risk item ID", ge=1)
    title: str = Field(..., description="Plan title", min_length=1, max_length=500)
    description: str | None = None
    treatment_option: str | None = Field(None, description="mitigate, transfer, accept, avoid")
    target_date: str | None = None
    cost_estimate: float | None = None
    cost_currency: str | None = "USD"
    responsible_person_id: int | None = None
    status: str = Field("draft", description="draft, approved, in_progress, completed, cancelled")
    effectiveness_review_required: bool = False


class RiskTreatmentPlanUpdate(BaseModel):
    """Request to update a risk treatment plan."""
    title: str | None = None
    description: str | None = None
    treatment_option: str | None = None
    target_date: str | None = None
    cost_estimate: float | None = None
    responsible_person_id: int | None = None
    status: str | None = None
    effectiveness_review_required: bool | None = None
    effectiveness_review_date: str | None = None


class RiskTreatmentPlanResponse(BaseModel):
    """Risk treatment plan response model."""
    id: int
    risk_item_id: int
    title: str
    description: str | None = None
    treatment_option: str | None = None
    target_date: str | None = None
    cost_estimate: float | None = None
    cost_currency: str | None = "USD"
    responsible_person_id: int | None = None
    status: str = "draft"
    approval_status: str = "pending"
    approved_by_id: int | None = None
    approval_date: str | None = None
    rejection_reason: str | None = None
    effectiveness_review_required: bool = False
    effectiveness_review_date: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RiskAcceptanceCreate(BaseModel):
    """Request to create a risk acceptance."""
    risk_item_id: int = Field(..., description="Risk item ID", ge=1)
    accepted_by_id: int = Field(..., description="Accepting user ID", ge=1)
    acceptance_type: str | None = Field(None, description="temporary, permanent, conditional")
    justification: str = Field(..., description="Acceptance justification")
    expiration_date: str | None = None
    reviewing_authority: str | None = None
    conditions: str | None = None
    status: str = Field("active", description="active, expired, revoked")


class RiskAcceptanceResponse(BaseModel):
    """Risk acceptance response model."""
    id: int
    risk_item_id: int
    accepted_by_id: int
    acceptance_type: str | None = None
    justification: str
    expiration_date: str | None = None
    reviewing_authority: str | None = None
    conditions: str | None = None
    status: str = "active"
    created_at: datetime | None = None


class RiskHistoryResponse(BaseModel):
    """Risk history entry response model."""
    id: int
    risk_item_id: int
    changed_by_id: int | None = None
    change_type: str | None = None
    previous_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    change_reason: str | None = None
    created_at: datetime | None = None


# ═══════════════════════════════════════════════════════════════
# Phase 2d: Compliance Framework Schemas
# ═══════════════════════════════════════════════════════════════


class ComplianceFrameworkCreate(BaseModel):
    """Request to create a compliance framework."""
    name: str = Field(..., description="Framework name (ISO 27001, NIST CSF, IEC 62443)", min_length=1, max_length=255)
    version: str = Field(..., description="Framework version", min_length=1, max_length=50)
    publisher: str | None = None
    description: str | None = None
    domain: str | None = Field(None, description="information_security, ics_security, privacy")


class ComplianceFrameworkResponse(BaseModel):
    """Compliance framework response model."""
    id: int
    name: str
    version: str
    publisher: str | None = None
    description: str | None = None
    domain: str | None = None
    is_active: bool = True
    created_at: datetime | None = None


class FrameworkRequirementCreate(BaseModel):
    """Request to create a framework requirement."""
    framework_id: int = Field(..., description="Framework ID", ge=1)
    requirement_id: str = Field(..., description="Requirement ID (e.g., AC-1, PR.AC-1)")
    parent_requirement_id: int | None = None
    title: str = Field(..., description="Requirement title", min_length=1, max_length=500)
    description: str | None = None
    requirement_type: str | None = Field(None, description="control, policy, process, technical")
    implementation_guidance: str | None = None
    evidence_requirements: str | None = None
    weight_importance: str | None = Field(None, description="critical, high, medium, low")
    sort_order: int | None = None


class FrameworkRequirementResponse(BaseModel):
    """Framework requirement response model."""
    id: int
    framework_id: int
    requirement_id: str
    parent_requirement_id: int | None = None
    title: str
    description: str | None = None
    requirement_type: str | None = None
    implementation_guidance: str | None = None
    evidence_requirements: str | None = None
    weight_importance: str | None = None
    sort_order: int | None = None
    created_at: datetime | None = None


class ControlMappingCreate(BaseModel):
    """Request to map a control to a requirement."""
    control_id: int = Field(..., description="Control ID", ge=1)
    requirement_id: int = Field(..., description="Requirement ID", ge=1)
    mapping_type: str | None = Field(None, description="directly_addresses, partially_addresses, related")
    mapping_notes: str | None = None
    mapping_justification: str | None = None


class ControlMappingResponse(BaseModel):
    """Control mapping response model."""
    id: int
    control_id: int
    requirement_id: int
    mapping_type: str | None = None
    mapping_notes: str | None = None
    mapping_justification: str | None = None
    created_at: datetime | None = None


class ComplianceGapCreate(BaseModel):
    """Request to create a compliance gap."""
    organization_id: int | None = None
    plant_id: int | None = None
    requirement_id: int = Field(..., description="Requirement ID", ge=1)
    gap_description: str = Field(..., description="Gap description")
    severity: str | None = Field(None, description="critical, high, medium, low")
    status: str | None = Field("open", description="open, planned, remediated, accepted")
    remediation_plan: str | None = None
    target_closure_date: str | None = None


class ComplianceGapUpdate(BaseModel):
    """Request to update a compliance gap."""
    gap_description: str | None = None
    severity: str | None = None
    status: str | None = None
    remediation_plan: str | None = None
    target_closure_date: str | None = None
    closed_date: str | None = None


class ComplianceGapResponse(BaseModel):
    """Compliance gap response model."""
    id: int
    organization_id: int | None = None
    plant_id: int | None = None
    requirement_id: int
    gap_description: str
    severity: str | None = None
    status: str | None = "open"
    remediation_plan: str | None = None
    target_closure_date: str | None = None
    closed_date: str | None = None
    created_at: datetime | None = None


class ComplianceAssessmentCreate(BaseModel):
    """Request to create a compliance assessment."""
    organization_id: int | None = None
    plant_id: int | None = None
    framework_id: int = Field(..., description="Framework ID", ge=1)
    project_id: int | None = None
    assessment_date: str | None = None
    assessor_id: int | None = None
    overall_status: str | None = Field(None, description="compliant, partially_compliant, non_compliant, not_assessed")
    compliance_percentage: float | None = Field(None, ge=0, le=100)
    findings_summary: str | None = None


class ComplianceAssessmentResponse(BaseModel):
    """Compliance assessment response model."""
    id: int
    organization_id: int | None = None
    plant_id: int | None = None
    framework_id: int
    project_id: int | None = None
    assessment_date: str | None = None
    assessor_id: int | None = None
    overall_status: str | None = None
    compliance_percentage: float | None = None
    findings_summary: str | None = None
    created_at: datetime | None = None


# ═══════════════════════════════════════════════════════════════
# Phase 2d: Audit Management Schemas
# ═══════════════════════════════════════════════════════════════


class AuditProgramCreate(BaseModel):
    """Request to create an audit program."""
    organization_id: int | None = None
    name: str = Field(..., description="Program name", min_length=1, max_length=255)
    description: str | None = None
    program_type: str | None = Field(None, description="annual, quarterly, continuous, ad_hoc")
    start_date: str | None = None
    end_date: str | None = None
    status: str = Field("draft", description="draft, active, completed, archived")
    program_manager_id: int | None = None


class AuditProgramUpdate(BaseModel):
    """Request to update an audit program."""
    name: str | None = None
    description: str | None = None
    program_type: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    status: str | None = None
    program_manager_id: int | None = None


class AuditProgramResponse(BaseModel):
    """Audit program response model."""
    id: int
    organization_id: int | None = None
    name: str
    description: str | None = None
    program_type: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    status: str = "draft"
    program_manager_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AuditPlanCreate(BaseModel):
    """Request to create an audit plan."""
    audit_program_id: int | None = None
    organization_id: int | None = None
    plant_id: int | None = None
    title: str = Field(..., description="Plan title", min_length=1, max_length=500)
    description: str | None = None
    audit_type: str | None = Field(None, description="internal, external, compliance, ics_security, regulatory")
    scope: str | None = None
    objectives: str | None = None
    criteria: str | None = Field(None, description="Reference criteria (ISO 27001, NIST CSF, etc.)")
    start_date: str | None = None
    end_date: str | None = None
    estimated_hours: float | None = None
    status: str = Field("draft", description="draft, planned, scheduled, in_progress, completed, cancelled")
    lead_auditor_id: int | None = None


class AuditPlanUpdate(BaseModel):
    """Request to update an audit plan."""
    title: str | None = None
    description: str | None = None
    audit_type: str | None = None
    scope: str | None = None
    objectives: str | None = None
    criteria: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    estimated_hours: float | None = None
    status: str | None = None
    lead_auditor_id: int | None = None


class AuditPlanResponse(BaseModel):
    """Audit plan response model."""
    id: int
    audit_program_id: int | None = None
    organization_id: int | None = None
    plant_id: int | None = None
    title: str
    description: str | None = None
    audit_type: str | None = None
    scope: str | None = None
    objectives: str | None = None
    criteria: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    estimated_hours: float | None = None
    status: str = "draft"
    lead_auditor_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AuditProcedureCreate(BaseModel):
    """Request to create an audit procedure."""
    audit_plan_id: int = Field(..., description="Audit plan ID", ge=1)
    control_id: int | None = None
    requirement_id: int | None = None
    title: str = Field(..., description="Procedure title", min_length=1, max_length=500)
    description: str | None = None
    procedure_steps: str | None = None
    testing_method: str | None = Field(None, description="interview, observation, examination, technical_test")
    sample_size: int | None = None
    expected_evidence: str | None = None
    sort_order: int | None = None


class AuditProcedureResponse(BaseModel):
    """Audit procedure response model."""
    id: int
    audit_plan_id: int
    control_id: int | None = None
    requirement_id: int | None = None
    title: str
    description: str | None = None
    procedure_steps: str | None = None
    testing_method: str | None = None
    sample_size: int | None = None
    expected_evidence: str | None = None
    sort_order: int | None = None
    created_at: datetime | None = None


class AuditFindingCreate(BaseModel):
    """Request to create an audit finding."""
    audit_plan_id: int = Field(..., description="Audit plan ID", ge=1)
    procedure_id: int | None = None
    asset_id: int | None = None
    control_id: int | None = None
    finding_id: str | None = Field(None, description="Finding identifier (e.g., AUDIT-F-2024-0001)")
    title: str = Field(..., description="Finding title", min_length=1, max_length=500)
    description: str = Field(..., description="Finding description")
    finding_type: str | None = Field(None, description="non_conformity, observation, opportunity_for_improvement")
    severity: str | None = Field(None, description="critical, high, medium, low, informational")
    likelihood: str | None = Field(None, description="certain, likely, possible, unlikely, rare")
    criteria_reference: str | None = None
    root_cause: str | None = None
    impact: str | None = None
    recommendation: str | None = None
    status: str = Field("open", description="open, acknowledged, action_planned, verified, closed")


class AuditFindingUpdate(BaseModel):
    """Request to update an audit finding."""
    title: str | None = None
    description: str | None = None
    finding_type: str | None = None
    severity: str | None = None
    likelihood: str | None = None
    root_cause: str | None = None
    impact: str | None = None
    recommendation: str | None = None
    management_response: str | None = None
    response_by_id: int | None = None
    response_date: str | None = None
    acceptance_of_finding: bool | None = None
    status: str | None = None


class AuditFindingResponse(BaseModel):
    """Audit finding response model."""
    id: int
    audit_plan_id: int
    procedure_id: int | None = None
    asset_id: int | None = None
    control_id: int | None = None
    finding_id: str | None = None
    title: str
    description: str
    finding_type: str | None = None
    severity: str | None = None
    likelihood: str | None = None
    criteria_reference: str | None = None
    root_cause: str | None = None
    impact: str | None = None
    recommendation: str | None = None
    management_response: str | None = None
    response_by_id: int | None = None
    response_date: str | None = None
    acceptance_of_finding: bool | None = None
    status: str = "open"
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AuditEvidenceCreate(BaseModel):
    """Request to create audit evidence."""
    audit_plan_id: int = Field(..., description="Audit plan ID", ge=1)
    procedure_id: int | None = None
    evidence_title: str = Field(..., description="Evidence title", min_length=1, max_length=500)
    description: str | None = None
    filename: str | None = None
    file_path: str | None = None
    evidence_type: str | None = Field(None, description="document, screenshot, log, interview_notes, config")
    collected_by_id: int | None = None
    is_confidential: bool = False


class AuditEvidenceResponse(BaseModel):
    """Audit evidence response model."""
    id: int
    audit_plan_id: int
    procedure_id: int | None = None
    evidence_title: str
    description: str | None = None
    filename: str | None = None
    file_path: str | None = None
    evidence_type: str | None = None
    collected_by_id: int | None = None
    collected_date: datetime | None = None
    is_confidential: bool = False


class AuditInterviewCreate(BaseModel):
    """Request to create an audit interview."""
    audit_plan_id: int = Field(..., description="Audit plan ID", ge=1)
    interviewee_name: str = Field(..., description="Interviewee name", min_length=1, max_length=255)
    interviewee_title: str | None = None
    interviewee_department: str | None = None
    interviewer_id: int | None = None
    interview_date: str | None = None
    duration_minutes: int | None = None
    topics_covered: str | None = None
    key_findings: str | None = None
    notes: str | None = None


class AuditInterviewResponse(BaseModel):
    """Audit interview response model."""
    id: int
    audit_plan_id: int
    interviewee_name: str
    interviewee_title: str | None = None
    interviewee_department: str | None = None
    interviewer_id: int | None = None
    interview_date: str | None = None
    duration_minutes: int | None = None
    topics_covered: str | None = None
    key_findings: str | None = None
    notes: str | None = None
    created_at: datetime | None = None


# ═══════════════════════════════════════════════════════════════
# Phase 2e: Corrective Actions (CAPA) Schemas
# ═══════════════════════════════════════════════════════════════


class CorrectiveActionCreate(BaseModel):
    """Request to create a corrective action."""
    finding_id: int | None = None
    risk_item_id: int | None = None
    compliance_gap_id: int | None = None
    action_id: str | None = Field(None, description="Action identifier (e.g., CAPA-2024-0001)")
    title: str = Field(..., description="Action title", min_length=1, max_length=500)
    description: str | None = None
    root_cause_type: str | None = Field(None, description="process, technical, human, organizational")
    root_cause_description: str | None = None
    impact_assessment: str | None = None
    action_type: str | None = Field(None, description="corrective, preventive, improvement")
    priority: str | None = Field(None, description="critical, high, medium, low")
    assigned_to_id: int | None = None
    assigned_by_id: int | None = None
    assigned_date: str | None = None
    target_date: str | None = None
    status: str = Field("open", description="open, in_progress, implemented, verified, closed")


class CorrectiveActionUpdate(BaseModel):
    """Request to update a corrective action."""
    title: str | None = None
    description: str | None = None
    root_cause_type: str | None = None
    root_cause_description: str | None = None
    impact_assessment: str | None = None
    action_type: str | None = None
    priority: str | None = None
    assigned_to_id: int | None = None
    target_date: str | None = None
    extended_date: str | None = None
    status: str | None = None
    implementation_description: str | None = None
    implementation_evidence: str | None = None
    verifier_id: int | None = None
    verification_date: str | None = None
    verification_result: str | None = None
    verification_notes: str | None = None
    closure_notes: str | None = None


class CorrectiveActionResponse(BaseModel):
    """Corrective action response model."""
    id: int
    finding_id: int | None = None
    risk_item_id: int | None = None
    compliance_gap_id: int | None = None
    action_id: str | None = None
    title: str
    description: str | None = None
    root_cause_type: str | None = None
    root_cause_description: str | None = None
    impact_assessment: str | None = None
    action_type: str | None = None
    priority: str | None = None
    status: str = "open"
    assigned_to_id: int | None = None
    assigned_by_id: int | None = None
    assigned_date: str | None = None
    target_date: str | None = None
    extended_date: str | None = None
    completed_date: str | None = None
    implementation_description: str | None = None
    implementation_evidence: str | None = None
    verifier_id: int | None = None
    verification_date: str | None = None
    verification_result: str | None = None
    verification_notes: str | None = None
    closure_notes: str | None = None
    is_closed: bool = False
    closed_by_id: int | None = None
    closed_date: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ActionTaskCreate(BaseModel):
    """Request to create an action task."""
    corrective_action_id: int = Field(..., description="Corrective action ID", ge=1)
    title: str = Field(..., description="Task title", min_length=1, max_length=500)
    description: str | None = None
    assigned_to_id: int | None = None
    status: str = Field("pending", description="pending, in_progress, completed")
    due_date: str | None = None
    sort_order: int | None = None


class ActionTaskUpdate(BaseModel):
    """Request to update an action task."""
    title: str | None = None
    description: str | None = None
    assigned_to_id: int | None = None
    status: str | None = None
    due_date: str | None = None
    completed_date: str | None = None
    completion_notes: str | None = None


class ActionTaskResponse(BaseModel):
    """Action task response model."""
    id: int
    corrective_action_id: int
    title: str
    description: str | None = None
    assigned_to_id: int | None = None
    status: str = "pending"
    due_date: str | None = None
    completed_date: str | None = None
    completion_notes: str | None = None
    sort_order: int | None = None
    created_at: datetime | None = None


class EffectivenessReviewCreate(BaseModel):
    """Request to create an effectiveness review."""
    corrective_action_id: int = Field(..., description="Corrective action ID", ge=1)
    review_date: str | None = None
    reviewer_id: int | None = None
    criteria: str | None = None
    result: str | None = Field(None, description="effective, partially_effective, not_effective")
    findings: str | None = None
    follow_up_required: bool = False
    follow_up_action: str | None = None


class EffectivenessReviewResponse(BaseModel):
    """Effectiveness review response model."""
    id: int
    corrective_action_id: int
    review_date: str | None = None
    reviewer_id: int | None = None
    criteria: str | None = None
    result: str | None = None
    findings: str | None = None
    follow_up_required: bool = False
    follow_up_action: str | None = None
    created_at: datetime | None = None

