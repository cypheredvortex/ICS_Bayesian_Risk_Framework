"""Pydantic schemas for the API.

Includes request/response models with full documentation and validation.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


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

