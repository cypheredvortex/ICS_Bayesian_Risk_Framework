from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, selectinload

from backend.database.config import get_session_factory, initialize_database, session_scope
from backend.database.models import ApplicationSetting, Asset, Project
from backend.database.repositories import (
    ApplicationSettingRepository, AssetRepository, ConnectionRepository,
    CPTRepository, InferenceRepository, ProjectRepository, ReportRepository, RiskRepository,
)

logger = logging.getLogger(__name__)


class AssessmentPersistenceService:
    """Persist framework runs and restore them later through repositories."""

    def __init__(self, session: Session | None = None) -> None:
        self.session = session
        self._project_repository: ProjectRepository | None = None
        self._asset_repository: AssetRepository | None = None
        self._connection_repository: ConnectionRepository | None = None
        self._cpt_repository: CPTRepository | None = None
        self._inference_repository: InferenceRepository | None = None
        self._risk_repository: RiskRepository | None = None
        self._report_repository: ReportRepository | None = None
        self._setting_repository: ApplicationSettingRepository | None = None

    def _get_session(self) -> Session:
        return self.session if self.session is not None else get_session_factory()()

    @property
    def project_repository(self) -> ProjectRepository:
        if self._project_repository is None:
            self._project_repository = ProjectRepository(self._get_session())
        return self._project_repository

    @property
    def asset_repository(self) -> AssetRepository:
        if self._asset_repository is None:
            self._asset_repository = AssetRepository(self._get_session())
        return self._asset_repository

    @property
    def connection_repository(self) -> ConnectionRepository:
        if self._connection_repository is None:
            self._connection_repository = ConnectionRepository(self._get_session())
        return self._connection_repository

    @property
    def cpt_repository(self) -> CPTRepository:
        if self._cpt_repository is None:
            self._cpt_repository = CPTRepository(self._get_session())
        return self._cpt_repository

    @property
    def inference_repository(self) -> InferenceRepository:
        if self._inference_repository is None:
            self._inference_repository = InferenceRepository(self._get_session())
        return self._inference_repository

    @property
    def risk_repository(self) -> RiskRepository:
        if self._risk_repository is None:
            self._risk_repository = RiskRepository(self._get_session())
        return self._risk_repository

    @property
    def report_repository(self) -> ReportRepository:
        if self._report_repository is None:
            self._report_repository = ReportRepository(self._get_session())
        return self._report_repository

    @property
    def setting_repository(self) -> ApplicationSettingRepository:
        if self._setting_repository is None:
            self._setting_repository = ApplicationSettingRepository(self._get_session())
        return self._setting_repository

    def persist_analysis_run(
        self,
        *,
        topology: dict[str, Any],
        evidence: dict[str, Any] | None,
        analysis_result: dict[str, Any],
        project_name: str,
        topology_source: str,
    ) -> Project:
        initialize_database()
        session = self._get_session()
        try:
            # Use local repo instances with the same session to avoid
            # cross-session detached instance errors.
            project_repo = ProjectRepository(session)
            asset_repo = AssetRepository(session)
            connection_repo = ConnectionRepository(session)
            cpt_repo = CPTRepository(session)
            inference_repo = InferenceRepository(session)
            risk_repo = RiskRepository(session)
            report_repo = ReportRepository(session)
            setting_repo = ApplicationSettingRepository(session)

            project = project_repo.create(name=project_name, description=f"Imported from {topology_source}", industry="ICS")
            assets = topology.get("assets", {}) or {}
            relationships = topology.get("relationships", []) or []

            for asset_key, attributes in assets.items():
                asset_payload = {
                    "asset_name": asset_key,
                    "asset_type": attributes.get("kind"),
                    "zone": attributes.get("zone"),
                    "vendor": attributes.get("vendor"),
                    "firmware_version": attributes.get("firmware_version"),
                    "exposure_level": attributes.get("exposure_level"),
                    "patch_level": attributes.get("patch_level"),
                    "criticality": attributes.get("criticality"),
                    "availability_requirement": attributes.get("availability_requirement"),
                    "integrity_requirement": attributes.get("integrity_requirement"),
                    "confidentiality_requirement": attributes.get("confidentiality_requirement"),
                    "intrinsic_probability": attributes.get("intrinsic_probability"),
                    "x_position": attributes.get("x_position"),
                    "y_position": attributes.get("y_position"),
                }
                asset = asset_repo.create_for_project(project.id, asset_payload)
                if evidence and asset_key in evidence:
                    inference_repo.create_for_project(project.id, asset.asset_name, float(evidence[asset_key]), asset_id=asset.id)

            for relationship in relationships:
                connection_repo.create_for_project(project.id, relationship)

            for node_name, table_data in (analysis_result.get("cpts") or {}).items():
                cpt_repo.create_for_project(project.id, node_name, table_data)

            for asset_name, posterior_probability in (analysis_result.get("posteriors") or {}).items():
                asset = session.query(Asset).filter(Asset.project_id == project.id, Asset.asset_name == asset_name).first()
                inference_repo.create_for_project(project.id, asset_name, float(posterior_probability), asset_id=asset.id if asset else None)

            risk_rows = analysis_result.get("risk_scores") or []
            for row in risk_rows:
                asset_name = row.get("asset")
                asset = session.query(Asset).filter(Asset.project_id == project.id, Asset.asset_name == asset_name).first()
                risk_repo.create_for_project(
                    project.id, asset_name,
                    risk_score=row.get("risk"),
                    risk_level=row.get("risk_level"),
                    asset_id=asset.id if asset else None,
                )

            report_path = analysis_result.get("artifacts", {}).get("risk_table")
            if report_path:
                report_filename = Path(report_path).name
            else:
                report_filename = f"{project.name.replace(' ', '_')}_report.csv"
            report_repo.create_for_project(project.id, report_filename, report_path, "risk_table")

            setting_repo.upsert("theme", "light")
            setting_repo.upsert("export_directory", str(Path("output")))
            setting_repo.upsert("recent_projects", json.dumps([project.name]))
            setting_repo.upsert("language", "en")
            session.commit()
            # Re-fetch the project within the same session to avoid
            # detached instance errors on refresh.
            reloaded_project = session.get(Project, project.id)
            if reloaded_project is not None:
                session.refresh(reloaded_project)
            logger.info("Persisted assessment project %s", project.id)
            return reloaded_project or project
        finally:
            if self.session is None:
                session.close()

    def get_project(self, project_id: int) -> Project | None:
        initialize_database()
        session = self._get_session()
        try:
            project = (
                session.query(Project)
                .options(
                    selectinload(Project.assets),
                    selectinload(Project.inference_results),
                    selectinload(Project.risk_results),
                    selectinload(Project.reports),
                )
                .filter(Project.id == project_id)
                .first()
            )
            if project is None:
                return None
            session.refresh(project)
            return project
        finally:
            if self.session is None:
                session.close()

    def list_projects(self) -> list[Project]:
        initialize_database()
        session = self._get_session()
        try:
            return list(session.query(Project).order_by(Project.created_at.desc()).all())
        finally:
            if self.session is None:
                session.close()

    def save_settings(self, key: str, value: str) -> ApplicationSetting:
        initialize_database()
        session = self._get_session()
        try:
            repository = ApplicationSettingRepository(session)
            setting = repository.upsert(key, value)
            session.flush()
            session.commit()
            return setting
        finally:
            if self.session is None:
                session.close()

    def get_settings(self) -> dict[str, str]:
        initialize_database()
        session = self._get_session()
        try:
            repository = ApplicationSettingRepository(session)
            settings = repository.list_all()
            return {setting.key: setting.value or "" for setting in settings}
        finally:
            if self.session is None:
                session.close()
