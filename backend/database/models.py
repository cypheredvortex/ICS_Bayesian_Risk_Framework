from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint, Float,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.config import Base


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
