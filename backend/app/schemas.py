from typing import Any

from pydantic import BaseModel, Field


class EvidenceEntry(BaseModel):
    asset: str = Field(..., description="Asset identifier")
    state: str | int = Field(..., description="Unknown | Compromised | Safe | 0 | 1")


class AnalyzeRequest(BaseModel):
    topology: dict[str, Any] = Field(..., description="Topology JSON payload")
    evidence: list[EvidenceEntry] = Field(default_factory=list)


class TopologyUploadRequest(BaseModel):
    topology: dict[str, Any] = Field(..., description="Topology JSON payload")


class SettingsUpdateRequest(BaseModel):
    settings: dict[str, Any] = Field(default_factory=dict)
