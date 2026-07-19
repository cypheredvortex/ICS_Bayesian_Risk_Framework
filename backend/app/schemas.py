from typing import Any

from pydantic import BaseModel, Field


class EvidenceEntry(BaseModel):
    asset: str = Field(..., description="Asset identifier")
    state: str = Field(..., description="Unknown | Compromised | Safe")


class AnalyzeRequest(BaseModel):
    topology: dict[str, Any] = Field(..., description="Topology JSON payload")
    evidence: list[EvidenceEntry] = Field(default_factory=list)


class TopologyUploadRequest(BaseModel):
    topology: dict[str, Any] = Field(..., description="Topology JSON payload")


class SettingsUpdateRequest(BaseModel):
    settings: dict[str, Any] = Field(default_factory=dict)
