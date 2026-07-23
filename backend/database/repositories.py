from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database.config import Base
from backend.database.models import (
    ApplicationSetting, Asset, BayesianNode, Connection,
    CPT, InferenceResult, Project, Report, RiskResult,
)

ModelType = TypeVar("ModelType", bound=Base)


class RepositoryError(RuntimeError):
    """Raised when a repository operation fails."""


class BaseRepository(Generic[ModelType]):
    def __init__(self, session: Session, model_class: type[ModelType]) -> None:
        self.session = session
        self.model_class = model_class

    def add(self, instance: ModelType) -> ModelType:
        self.session.add(instance)
        return instance

    def commit(self) -> None:
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise RepositoryError(str(exc)) from exc

    def flush(self) -> None:
        self.session.flush()

    def get_by_id(self, object_id: int) -> ModelType | None:
        return self.session.get(self.model_class, object_id)

    def list_all(self) -> list[ModelType]:
        return list(self.session.scalars(select(self.model_class)).all())

    def delete(self, instance: ModelType) -> None:
        self.session.delete(instance)


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Project)

    def create(self, *, name: str, description: str | None = None, industry: str | None = None) -> Project:
        existing = self.get_by_name(name)
        if existing is not None:
            return existing
        project = Project(name=name, description=description, industry=industry)
        self.add(project)
        self.commit()
        return project

    def get_by_name(self, name: str) -> Project | None:
        return self.session.scalar(select(Project).where(Project.name == name))


class AssetRepository(BaseRepository[Asset]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Asset)

    def create_for_project(self, project_id: int, asset_data: dict[str, Any]) -> Asset:
        asset_name = asset_data.get("asset_name", asset_data.get("name", ""))
        # Check if asset already exists for this project (idempotent persistence)
        existing = self.session.scalar(
            select(Asset).where(
                Asset.project_id == project_id,
                Asset.asset_name == asset_name,
            )
        )
        if existing is not None:
            return existing
        asset = Asset(project_id=project_id, asset_name=asset_name)
        asset.asset_type = asset_data.get("asset_type")
        asset.zone = asset_data.get("zone")
        asset.vendor = asset_data.get("vendor")
        asset.firmware_version = asset_data.get("firmware_version")
        asset.exposure_level = asset_data.get("exposure_level")
        asset.patch_level = asset_data.get("patch_level")
        asset.criticality = asset_data.get("criticality")
        asset.availability_requirement = asset_data.get("availability_requirement")
        asset.integrity_requirement = asset_data.get("integrity_requirement")
        asset.confidentiality_requirement = asset_data.get("confidentiality_requirement")
        asset.intrinsic_probability = asset_data.get("intrinsic_probability")
        asset.x_position = asset_data.get("x_position")
        asset.y_position = asset_data.get("y_position")
        self.add(asset)
        return asset

    def list_for_project(self, project_id: int) -> list[Asset]:
        return list(self.session.scalars(select(Asset).where(Asset.project_id == project_id)).all())


class ConnectionRepository(BaseRepository[Connection]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Connection)

    def create_for_project(self, project_id: int, relationship: tuple[Any, ...]) -> Connection:
        source, target, rel_type, firewalled, metadata = relationship
        # Check if connection already exists (idempotent persistence)
        existing = self.session.scalar(
            select(Connection).where(
                Connection.project_id == project_id,
                Connection.source_asset == str(source),
                Connection.destination_asset == str(target),
            )
        )
        if existing is not None:
            return existing
        connection = Connection(
            project_id=project_id,
            source_asset=str(source),
            destination_asset=str(target),
            relationship_type=str(rel_type),
            propagation_weight=None,  # Weight computed by graph_builder.edge_weight; not stored in relationship metadata.
        )
        self.add(connection)
        return connection

    def list_for_project(self, project_id: int) -> list[Connection]:
        return list(self.session.scalars(select(Connection).where(Connection.project_id == project_id)).all())


class CPTRepository(BaseRepository[CPT]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, CPT)

    def create_for_project(self, project_id: int, node_name: str, table_data: dict[str, Any]) -> CPT:
        existing = self.session.scalar(
            select(CPT).where(
                CPT.project_id == project_id,
                CPT.node_name == node_name,
            )
        )
        if existing is not None:
            existing.table_data = table_data
            return existing
        cpt = CPT(project_id=project_id, node_name=node_name, table_data=table_data)
        self.add(cpt)
        return cpt

    def list_for_project(self, project_id: int) -> list[CPT]:
        return list(self.session.scalars(select(CPT).where(CPT.project_id == project_id)).all())


class InferenceRepository(BaseRepository[InferenceResult]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, InferenceResult)

    def create_for_project(self, project_id: int, asset_name: str, posterior_probability: float, asset_id: int | None = None) -> InferenceResult:
        # Always create new inference result (timestamp acts as version history)
        inference = InferenceResult(
            project_id=project_id,
            asset_id=asset_id,
            asset_name=asset_name,
            posterior_probability=posterior_probability,
        )
        self.add(inference)
        return inference

    def list_for_project(self, project_id: int) -> list[InferenceResult]:
        return list(self.session.scalars(select(InferenceResult).where(InferenceResult.project_id == project_id)).all())


class RiskRepository(BaseRepository[RiskResult]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, RiskResult)

    def create_for_project(self, project_id: int, asset_name: str, risk_score: float | None, risk_level: str | None = None, asset_id: int | None = None, likelihood: float | None = None, impact: float | None = None) -> RiskResult:
        # Always create new risk result (timestamp acts as version history)
        risk = RiskResult(
            project_id=project_id,
            asset_id=asset_id,
            asset_name=asset_name,
            likelihood=likelihood,
            impact=impact,
            risk_score=risk_score,
            risk_level=risk_level,
        )
        self.add(risk)
        return risk

    def list_for_project(self, project_id: int) -> list[RiskResult]:
        return list(self.session.scalars(select(RiskResult).where(RiskResult.project_id == project_id)).all())


class ReportRepository(BaseRepository[Report]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Report)

    def create_for_project(self, project_id: int, filename: str, path: str | None, report_type: str | None) -> Report:
        existing = self.session.scalar(
            select(Report).where(
                Report.project_id == project_id,
                Report.filename == filename,
            )
        )
        if existing is not None:
            return existing
        report = Report(project_id=project_id, filename=filename, path=path, report_type=report_type)
        self.add(report)
        return report

    def list_for_project(self, project_id: int) -> list[Report]:
        return list(self.session.scalars(select(Report).where(Report.project_id == project_id)).all())


class ApplicationSettingRepository(BaseRepository[ApplicationSetting]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ApplicationSetting)

    def get_by_key(self, key: str) -> ApplicationSetting | None:
        return self.session.scalar(select(ApplicationSetting).where(ApplicationSetting.key == key))

    def upsert(self, key: str, value: str) -> ApplicationSetting:
        setting = self.get_by_key(key)
        if setting is None:
            setting = ApplicationSetting(key=key, value=value)
            self.add(setting)
        else:
            setting.value = value
        return setting
