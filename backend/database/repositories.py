from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database.config import Base
from backend.database.models import (
    ActionTask, ApplicationSetting, Asset, AssetCategory, AssetDependency, AssetVulnerability,
    AuditEvidenceCollection, AuditFinding, AuditInterview, AuditLog, AuditPlan,
    AuditProcedure, AuditProgram, BayesianNode, ComplianceAssessment, ComplianceFramework,
    ComplianceGap, Connection, Control, ControlCategory, ControlEvidence, ControlMapping,
    ControlTest, Conduit, CorrectiveAction, CPT, Department, EffectivenessReview,
    ExtendedAsset, FrameworkRequirement, InferenceResult, Organization, Plant,
    Project, Report, RiskAcceptance, RiskHistory, RiskItem, RiskResult,
    RiskScenario, RiskTreatmentPlan, Role, SecurityZone, Site, Threat,
    ThreatActor, ThreatCategory, User, UserSession, Vulnerability,
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


# ═══════════════════════════════════════════════════════════════
# Phase 1: Organization Hierarchy Repositories
# ═══════════════════════════════════════════════════════════════


class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Organization)

    def create(self, *, name: str, **kwargs: Any) -> Organization:
        existing = self.session.scalar(select(Organization).where(Organization.name == name))
        if existing:
            return existing
        org = Organization(name=name, **kwargs)
        self.add(org)
        self.commit()
        return org

    def get_by_name(self, name: str) -> Organization | None:
        return self.session.scalar(select(Organization).where(Organization.name == name))

    def list_active(self) -> list[Organization]:
        return list(self.session.scalars(select(Organization).where(Organization.is_active == True)).all())


class SiteRepository(BaseRepository[Site]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Site)

    def create(self, *, organization_id: int, name: str, **kwargs: Any) -> Site:
        existing = self.session.scalar(
            select(Site).where(Site.organization_id == organization_id, Site.name == name)
        )
        if existing:
            return existing
        site = Site(organization_id=organization_id, name=name, **kwargs)
        self.add(site)
        self.commit()
        return site

    def list_for_organization(self, organization_id: int) -> list[Site]:
        return list(self.session.scalars(
            select(Site).where(Site.organization_id == organization_id, Site.is_active == True)
        ).all())


class PlantRepository(BaseRepository[Plant]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Plant)

    def create(self, *, site_id: int, name: str, **kwargs: Any) -> Plant:
        existing = self.session.scalar(
            select(Plant).where(Plant.site_id == site_id, Plant.name == name)
        )
        if existing:
            return existing
        plant = Plant(site_id=site_id, name=name, **kwargs)
        self.add(plant)
        self.commit()
        return plant

    def list_for_site(self, site_id: int) -> list[Plant]:
        return list(self.session.scalars(
            select(Plant).where(Plant.site_id == site_id, Plant.is_active == True)
        ).all())


# ═══════════════════════════════════════════════════════════════
# Phase 1: User & Role Repositories
# ═══════════════════════════════════════════════════════════════


class RoleRepository(BaseRepository[Role]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Role)

    def create(self, *, name: str, description: str | None = None, is_system_role: bool = False) -> Role:
        existing = self.session.scalar(select(Role).where(Role.name == name))
        if existing:
            return existing
        role = Role(name=name, description=description, is_system_role=is_system_role)
        self.add(role)
        self.commit()
        return role

    def get_by_name(self, name: str) -> Role | None:
        return self.session.scalar(select(Role).where(Role.name == name))


class UserRepository(BaseRepository[User]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, User)

    def create(self, *, username: str, email: str, password_hash: str, **kwargs: Any) -> User:
        existing = self.session.scalar(
            select(User).where((User.username == username) | (User.email == email))
        )
        if existing:
            return existing
        user = User(username=username, email=email, password_hash=password_hash, **kwargs)
        self.add(user)
        self.commit()
        return user

    def get_by_username(self, username: str) -> User | None:
        return self.session.scalar(select(User).where(User.username == username))

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email))

    def list_for_organization(self, organization_id: int) -> list[User]:
        return list(self.session.scalars(
            select(User).where(User.organization_id == organization_id, User.is_active == True)
        ).all())


class UserSessionRepository(BaseRepository[UserSession]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, UserSession)

    def create_session(self, *, user_id: int, token: str, ip_address: str | None = None, user_agent: str | None = None) -> UserSession:
        session = UserSession(user_id=user_id, token=token, ip_address=ip_address, user_agent=user_agent)
        self.add(session)
        self.commit()
        return session

    def get_active_by_token(self, token: str) -> UserSession | None:
        return self.session.scalar(
            select(UserSession).where(UserSession.token == token, UserSession.is_active == True)
        )

    def invalidate_user_sessions(self, user_id: int) -> None:
        self.session.query(UserSession).filter(UserSession.user_id == user_id).update({"is_active": False})
        self.commit()


# ═══════════════════════════════════════════════════════════════
# Phase 1: Zones & Conduits Repositories
# ═══════════════════════════════════════════════════════════════


class SecurityZoneRepository(BaseRepository[SecurityZone]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, SecurityZone)

    def create(self, *, plant_id: int, name: str, zone_level: int, **kwargs: Any) -> SecurityZone:
        existing = self.session.scalar(
            select(SecurityZone).where(SecurityZone.plant_id == plant_id, SecurityZone.name == name)
        )
        if existing:
            return existing
        zone = SecurityZone(plant_id=plant_id, name=name, zone_level=zone_level, **kwargs)
        self.add(zone)
        self.commit()
        return zone

    def list_for_plant(self, plant_id: int) -> list[SecurityZone]:
        return list(self.session.scalars(
            select(SecurityZone).where(SecurityZone.plant_id == plant_id, SecurityZone.is_active == True)
        ).all())


class ConduitRepository(BaseRepository[Conduit]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Conduit)

    def create(self, *, plant_id: int, name: str, source_zone_id: int, destination_zone_id: int, **kwargs: Any) -> Conduit:
        existing = self.session.scalar(
            select(Conduit).where(Conduit.plant_id == plant_id, Conduit.name == name)
        )
        if existing:
            return existing
        conduit = Conduit(plant_id=plant_id, name=name, source_zone_id=source_zone_id, destination_zone_id=destination_zone_id, **kwargs)
        self.add(conduit)
        self.commit()
        return conduit

    def list_for_plant(self, plant_id: int) -> list[Conduit]:
        return list(self.session.scalars(
            select(Conduit).where(Conduit.plant_id == plant_id)
        ).all())

    def list_between_zones(self, source_zone_id: int, destination_zone_id: int) -> list[Conduit]:
        return list(self.session.scalars(
            select(Conduit).where(
                Conduit.source_zone_id == source_zone_id,
                Conduit.destination_zone_id == destination_zone_id,
            )
        ).all())


# ═══════════════════════════════════════════════════════════════
# Phase 1: Extended Asset Repositories
# ═══════════════════════════════════════════════════════════════


class AssetCategoryRepository(BaseRepository[AssetCategory]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AssetCategory)

    def create(self, *, name: str, **kwargs: Any) -> AssetCategory:
        existing = self.session.scalar(select(AssetCategory).where(AssetCategory.name == name))
        if existing:
            return existing
        category = AssetCategory(name=name, **kwargs)
        self.add(category)
        self.commit()
        return category


class ExtendedAssetRepository(BaseRepository[ExtendedAsset]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ExtendedAsset)

    def create(self, *, name: str, **kwargs: Any) -> ExtendedAsset:
        asset = ExtendedAsset(name=name, **kwargs)
        self.add(asset)
        self.commit()
        return asset

    def list_for_plant(self, plant_id: int) -> list[ExtendedAsset]:
        return list(self.session.scalars(
            select(ExtendedAsset).where(ExtendedAsset.plant_id == plant_id, ExtendedAsset.is_active == True)
        ).all())

    def list_for_organization(self, organization_id: int) -> list[ExtendedAsset]:
        return list(self.session.scalars(
            select(ExtendedAsset).where(ExtendedAsset.organization_id == organization_id, ExtendedAsset.is_active == True)
        ).all())

    def get_by_asset_tag(self, asset_tag: str) -> ExtendedAsset | None:
        return self.session.scalar(select(ExtendedAsset).where(ExtendedAsset.asset_tag == asset_tag))


class AssetDependencyRepository(BaseRepository[AssetDependency]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AssetDependency)

    def create(self, *, asset_id: int, depends_on_asset_id: int, **kwargs: Any) -> AssetDependency:
        dep = AssetDependency(asset_id=asset_id, depends_on_asset_id=depends_on_asset_id, **kwargs)
        self.add(dep)
        self.commit()
        return dep

    def list_for_asset(self, asset_id: int) -> list[AssetDependency]:
        return list(self.session.scalars(
            select(AssetDependency).where(AssetDependency.asset_id == asset_id)
        ).all())


# ═══════════════════════════════════════════════════════════════
# Phase 1: Audit Log Repository
# ═══════════════════════════════════════════════════════════════


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AuditLog)

    def log(self, *, user_id: int | None, action: str, entity_type: str, entity_id: int | None = None,
            organization_id: int | None = None, ip_address: str | None = None,
            user_agent: str | None = None, changes: dict | None = None,
            metadata: dict | None = None) -> AuditLog:
        entry = AuditLog(
            user_id=user_id, action=action, entity_type=entity_type,
            entity_id=entity_id, organization_id=organization_id,
            ip_address=ip_address, user_agent=user_agent,
            changes=changes, metadata=metadata,
        )
        self.add(entry)
        self.commit()
        return entry

    def list_for_entity(self, entity_type: str, entity_id: int) -> list[AuditLog]:
        return list(self.session.scalars(
            select(AuditLog).where(
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id,
            ).order_by(AuditLog.created_at.desc())
        ).all())


# ═══════════════════════════════════════════════════════════════
# Phase 2a: Threat & Vulnerability Repositories
# ═══════════════════════════════════════════════════════════════


class ThreatCategoryRepository(BaseRepository[ThreatCategory]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ThreatCategory)

    def create(self, *, name: str, **kwargs: Any) -> ThreatCategory:
        existing = self.session.scalar(select(ThreatCategory).where(ThreatCategory.name == name))
        if existing:
            return existing
        cat = ThreatCategory(name=name, **kwargs)
        self.add(cat)
        self.commit()
        return cat

    def get_by_name(self, name: str) -> ThreatCategory | None:
        return self.session.scalar(select(ThreatCategory).where(ThreatCategory.name == name))


class ThreatRepository(BaseRepository[Threat]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Threat)

    def create(self, *, name: str, **kwargs: Any) -> Threat:
        existing = self.session.scalar(select(Threat).where(Threat.name == name))
        if existing:
            return existing
        threat = Threat(name=name, **kwargs)
        self.add(threat)
        self.commit()
        return threat

    def get_by_name(self, name: str) -> Threat | None:
        return self.session.scalar(select(Threat).where(Threat.name == name))

    def list_by_category(self, category_id: int) -> list[Threat]:
        return list(self.session.scalars(
            select(Threat).where(Threat.threat_category_id == category_id)
        ).all())

    def list_by_source(self, source: str) -> list[Threat]:
        return list(self.session.scalars(
            select(Threat).where(Threat.source == source)
        ).all())


class ThreatActorRepository(BaseRepository[ThreatActor]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ThreatActor)

    def create(self, *, name: str, **kwargs: Any) -> ThreatActor:
        actor = ThreatActor(name=name, **kwargs)
        self.add(actor)
        self.commit()
        return actor

    def list_by_actor_type(self, actor_type: str) -> list[ThreatActor]:
        return list(self.session.scalars(
            select(ThreatActor).where(ThreatActor.actor_type == actor_type, ThreatActor.is_active == True)
        ).all())

    def list_active(self) -> list[ThreatActor]:
        return list(self.session.scalars(
            select(ThreatActor).where(ThreatActor.is_active == True)
        ).all())


class VulnerabilityRepository(BaseRepository[Vulnerability]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Vulnerability)

    def create(self, *, name: str, **kwargs: Any) -> Vulnerability:
        vuln = Vulnerability(name=name, **kwargs)
        self.add(vuln)
        self.commit()
        return vuln

    def get_by_cve_id(self, cve_id: str) -> Vulnerability | None:
        return self.session.scalar(select(Vulnerability).where(Vulnerability.cve_id == cve_id))

    def list_by_severity(self, severity: str) -> list[Vulnerability]:
        return list(self.session.scalars(
            select(Vulnerability).where(Vulnerability.cvss_severity == severity)
        ).all())

    def list_exploitable(self) -> list[Vulnerability]:
        return list(self.session.scalars(
            select(Vulnerability).where(Vulnerability.exploit_available == True)
        ).all())

    def list_unpatched(self) -> list[Vulnerability]:
        return list(self.session.scalars(
            select(Vulnerability).where(Vulnerability.patch_available == False)
        ).all())


class AssetVulnerabilityRepository(BaseRepository[AssetVulnerability]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AssetVulnerability)

    def create(self, *, asset_id: int, vulnerability_id: int, **kwargs: Any) -> AssetVulnerability:
        existing = self.session.scalar(
            select(AssetVulnerability).where(
                AssetVulnerability.asset_id == asset_id,
                AssetVulnerability.vulnerability_id == vulnerability_id,
            )
        )
        if existing:
            return existing
        av = AssetVulnerability(asset_id=asset_id, vulnerability_id=vulnerability_id, **kwargs)
        self.add(av)
        self.commit()
        return av

    def list_for_asset(self, asset_id: int) -> list[AssetVulnerability]:
        return list(self.session.scalars(
            select(AssetVulnerability).where(AssetVulnerability.asset_id == asset_id)
        ).all())

    def list_for_vulnerability(self, vulnerability_id: int) -> list[AssetVulnerability]:
        return list(self.session.scalars(
            select(AssetVulnerability).where(AssetVulnerability.vulnerability_id == vulnerability_id)
        ).all())

    def list_open_for_asset(self, asset_id: int) -> list[AssetVulnerability]:
        return list(self.session.scalars(
            select(AssetVulnerability).where(
                AssetVulnerability.asset_id == asset_id,
                AssetVulnerability.status.in_(["open", "in_progress"]),
            )
        ).all())


# ═══════════════════════════════════════════════════════════════
# Phase 2b: Control Library Repositories
# ═══════════════════════════════════════════════════════════════


class ControlCategoryRepository(BaseRepository[ControlCategory]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ControlCategory)

    def create(self, *, name: str, **kwargs: Any) -> ControlCategory:
        existing = self.session.scalar(select(ControlCategory).where(ControlCategory.name == name))
        if existing:
            return existing
        cat = ControlCategory(name=name, **kwargs)
        self.add(cat)
        self.commit()
        return cat

    def get_by_name(self, name: str) -> ControlCategory | None:
        return self.session.scalar(select(ControlCategory).where(ControlCategory.name == name))


class ControlRepository(BaseRepository[Control]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Control)

    def create(self, *, name: str, **kwargs: Any) -> Control:
        control = Control(name=name, **kwargs)
        self.add(control)
        self.commit()
        return control

    def get_by_control_id(self, control_id: str) -> Control | None:
        return self.session.scalar(select(Control).where(Control.control_id == control_id))

    def list_by_category(self, category_id: int) -> list[Control]:
        return list(self.session.scalars(
            select(Control).where(Control.control_category_id == category_id, Control.is_active == True)
        ).all())

    def list_by_implementation_status(self, status: str) -> list[Control]:
        return list(self.session.scalars(
            select(Control).where(Control.implementation_status == status)
        ).all())

    def list_active(self) -> list[Control]:
        return list(self.session.scalars(select(Control).where(Control.is_active == True)).all())


class ControlTestRepository(BaseRepository[ControlTest]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ControlTest)

    def create(self, *, control_id: int, **kwargs: Any) -> ControlTest:
        test = ControlTest(control_id=control_id, **kwargs)
        self.add(test)
        self.commit()
        return test

    def list_for_control(self, control_id: int) -> list[ControlTest]:
        return list(self.session.scalars(
            select(ControlTest).where(ControlTest.control_id == control_id).order_by(ControlTest.created_at.desc())
        ).all())

    def list_failed(self) -> list[ControlTest]:
        return list(self.session.scalars(
            select(ControlTest).where(ControlTest.result.in_(["fail", "partial"]))
        ).all())


class ControlEvidenceRepository(BaseRepository[ControlEvidence]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ControlEvidence)

    def create(self, *, control_id: int, filename: str, file_path: str, **kwargs: Any) -> ControlEvidence:
        evidence = ControlEvidence(control_id=control_id, filename=filename, file_path=file_path, **kwargs)
        self.add(evidence)
        self.commit()
        return evidence

    def list_for_control(self, control_id: int) -> list[ControlEvidence]:
        return list(self.session.scalars(
            select(ControlEvidence).where(ControlEvidence.control_id == control_id).order_by(ControlEvidence.created_at.desc())
        ).all())


# ═══════════════════════════════════════════════════════════════
# Phase 2c: Risk Register & Treatment Repositories
# ═══════════════════════════════════════════════════════════════


class RiskItemRepository(BaseRepository[RiskItem]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, RiskItem)

    def create(self, *, title: str, **kwargs: Any) -> RiskItem:
        item = RiskItem(title=title, **kwargs)
        self.add(item)
        self.commit()
        return item

    def get_by_risk_id(self, risk_id: str) -> RiskItem | None:
        return self.session.scalar(select(RiskItem).where(RiskItem.risk_id == risk_id))

    def list_for_organization(self, organization_id: int) -> list[RiskItem]:
        return list(self.session.scalars(
            select(RiskItem).where(RiskItem.organization_id == organization_id, RiskItem.is_active == True)
        ).all())

    def list_for_asset(self, asset_id: int) -> list[RiskItem]:
        return list(self.session.scalars(
            select(RiskItem).where(RiskItem.asset_id == asset_id, RiskItem.is_active == True)
        ).all())

    def list_active(self) -> list[RiskItem]:
        return list(self.session.scalars(select(RiskItem).where(RiskItem.is_active == True)).all())

    def list_open(self) -> list[RiskItem]:
        return list(self.session.scalars(
            select(RiskItem).where(RiskItem.is_active == True, RiskItem.status != "closed")
        ).all())


class RiskScenarioRepository(BaseRepository[RiskScenario]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, RiskScenario)

    def create(self, *, risk_item_id: int, name: str, **kwargs: Any) -> RiskScenario:
        scenario = RiskScenario(risk_item_id=risk_item_id, name=name, **kwargs)
        self.add(scenario)
        self.commit()
        return scenario

    def list_for_risk_item(self, risk_item_id: int) -> list[RiskScenario]:
        return list(self.session.scalars(
            select(RiskScenario).where(RiskScenario.risk_item_id == risk_item_id)
        ).all())


class RiskTreatmentPlanRepository(BaseRepository[RiskTreatmentPlan]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, RiskTreatmentPlan)

    def create(self, *, risk_item_id: int, title: str, **kwargs: Any) -> RiskTreatmentPlan:
        plan = RiskTreatmentPlan(risk_item_id=risk_item_id, title=title, **kwargs)
        self.add(plan)
        self.commit()
        return plan

    def list_for_risk_item(self, risk_item_id: int) -> list[RiskTreatmentPlan]:
        return list(self.session.scalars(
            select(RiskTreatmentPlan).where(RiskTreatmentPlan.risk_item_id == risk_item_id)
        ).all())

    def list_by_status(self, status: str) -> list[RiskTreatmentPlan]:
        return list(self.session.scalars(
            select(RiskTreatmentPlan).where(RiskTreatmentPlan.status == status)
        ).all())


class RiskAcceptanceRepository(BaseRepository[RiskAcceptance]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, RiskAcceptance)

    def create(self, *, risk_item_id: int, accepted_by_id: int, justification: str, **kwargs: Any) -> RiskAcceptance:
        acceptance = RiskAcceptance(
            risk_item_id=risk_item_id, accepted_by_id=accepted_by_id, justification=justification, **kwargs
        )
        self.add(acceptance)
        self.commit()
        return acceptance

    def list_for_risk_item(self, risk_item_id: int) -> list[RiskAcceptance]:
        return list(self.session.scalars(
            select(RiskAcceptance).where(RiskAcceptance.risk_item_id == risk_item_id)
        ).all())

    def list_active(self) -> list[RiskAcceptance]:
        return list(self.session.scalars(
            select(RiskAcceptance).where(RiskAcceptance.status == "active")
        ).all())


class RiskHistoryRepository(BaseRepository[RiskHistory]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, RiskHistory)

    def create(self, *, risk_item_id: int, **kwargs: Any) -> RiskHistory:
        entry = RiskHistory(risk_item_id=risk_item_id, **kwargs)
        self.add(entry)
        self.commit()
        return entry

    def list_for_risk_item(self, risk_item_id: int) -> list[RiskHistory]:
        return list(self.session.scalars(
            select(RiskHistory).where(RiskHistory.risk_item_id == risk_item_id).order_by(RiskHistory.created_at.desc())
        ).all())


# ═══════════════════════════════════════════════════════════════
# Phase 2d: Compliance & Framework Repositories
# ═══════════════════════════════════════════════════════════════


class ComplianceFrameworkRepository(BaseRepository[ComplianceFramework]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ComplianceFramework)

    def create(self, *, name: str, version: str, **kwargs: Any) -> ComplianceFramework:
        existing = self.session.scalar(
            select(ComplianceFramework).where(
                ComplianceFramework.name == name,
                ComplianceFramework.version == version,
            )
        )
        if existing:
            return existing
        framework = ComplianceFramework(name=name, version=version, **kwargs)
        self.add(framework)
        self.commit()
        return framework

    def get_by_name_version(self, name: str, version: str) -> ComplianceFramework | None:
        return self.session.scalar(
            select(ComplianceFramework).where(
                ComplianceFramework.name == name,
                ComplianceFramework.version == version,
            )
        )

    def list_active(self) -> list[ComplianceFramework]:
        return list(self.session.scalars(
            select(ComplianceFramework).where(ComplianceFramework.is_active == True)
        ).all())


class FrameworkRequirementRepository(BaseRepository[FrameworkRequirement]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, FrameworkRequirement)

    def create(self, *, framework_id: int, requirement_id: str, title: str, **kwargs: Any) -> FrameworkRequirement:
        existing = self.session.scalar(
            select(FrameworkRequirement).where(
                FrameworkRequirement.framework_id == framework_id,
                FrameworkRequirement.requirement_id == requirement_id,
            )
        )
        if existing:
            return existing
        req = FrameworkRequirement(
            framework_id=framework_id, requirement_id=requirement_id, title=title, **kwargs
        )
        self.add(req)
        self.commit()
        return req

    def list_for_framework(self, framework_id: int) -> list[FrameworkRequirement]:
        return list(self.session.scalars(
            select(FrameworkRequirement)
            .where(FrameworkRequirement.framework_id == framework_id)
            .order_by(FrameworkRequirement.sort_order)
        ).all())


class ControlMappingRepository(BaseRepository[ControlMapping]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ControlMapping)

    def create(self, *, control_id: int, requirement_id: int, **kwargs: Any) -> ControlMapping:
        existing = self.session.scalar(
            select(ControlMapping).where(
                ControlMapping.control_id == control_id,
                ControlMapping.requirement_id == requirement_id,
            )
        )
        if existing:
            return existing
        mapping = ControlMapping(control_id=control_id, requirement_id=requirement_id, **kwargs)
        self.add(mapping)
        self.commit()
        return mapping

    def list_for_control(self, control_id: int) -> list[ControlMapping]:
        return list(self.session.scalars(
            select(ControlMapping).where(ControlMapping.control_id == control_id)
        ).all())

    def list_for_requirement(self, requirement_id: int) -> list[ControlMapping]:
        return list(self.session.scalars(
            select(ControlMapping).where(ControlMapping.requirement_id == requirement_id)
        ).all())


class ComplianceGapRepository(BaseRepository[ComplianceGap]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ComplianceGap)

    def create(self, *, requirement_id: int, gap_description: str, **kwargs: Any) -> ComplianceGap:
        gap = ComplianceGap(requirement_id=requirement_id, gap_description=gap_description, **kwargs)
        self.add(gap)
        self.commit()
        return gap

    def list_for_requirement(self, requirement_id: int) -> list[ComplianceGap]:
        return list(self.session.scalars(
            select(ComplianceGap).where(ComplianceGap.requirement_id == requirement_id)
        ).all())

    def list_open(self) -> list[ComplianceGap]:
        return list(self.session.scalars(
            select(ComplianceGap).where(ComplianceGap.status.in_(["open", "planned"]))
        ).all())


class ComplianceAssessmentRepository(BaseRepository[ComplianceAssessment]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ComplianceAssessment)

    def create(self, *, framework_id: int, **kwargs: Any) -> ComplianceAssessment:
        assessment = ComplianceAssessment(framework_id=framework_id, **kwargs)
        self.add(assessment)
        self.commit()
        return assessment

    def list_for_framework(self, framework_id: int) -> list[ComplianceAssessment]:
        return list(self.session.scalars(
            select(ComplianceAssessment).where(ComplianceAssessment.framework_id == framework_id)
        ).all())

    def list_for_organization(self, organization_id: int) -> list[ComplianceAssessment]:
        return list(self.session.scalars(
            select(ComplianceAssessment).where(ComplianceAssessment.organization_id == organization_id)
        ).all())


# ═══════════════════════════════════════════════════════════════
# Phase 2d: Audit Management Repositories
# ═══════════════════════════════════════════════════════════════


class AuditProgramRepository(BaseRepository[AuditProgram]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AuditProgram)

    def create(self, *, name: str, **kwargs: Any) -> AuditProgram:
        program = AuditProgram(name=name, **kwargs)
        self.add(program)
        self.commit()
        return program

    def list_for_organization(self, organization_id: int) -> list[AuditProgram]:
        return list(self.session.scalars(
            select(AuditProgram).where(AuditProgram.organization_id == organization_id)
        ).all())


class AuditPlanRepository(BaseRepository[AuditPlan]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AuditPlan)

    def create(self, *, title: str, **kwargs: Any) -> AuditPlan:
        plan = AuditPlan(title=title, **kwargs)
        self.add(plan)
        self.commit()
        return plan

    def list_for_program(self, audit_program_id: int) -> list[AuditPlan]:
        return list(self.session.scalars(
            select(AuditPlan).where(AuditPlan.audit_program_id == audit_program_id)
        ).all())

    def list_for_organization(self, organization_id: int) -> list[AuditPlan]:
        return list(self.session.scalars(
            select(AuditPlan).where(AuditPlan.organization_id == organization_id)
        ).all())

    def list_by_status(self, status: str) -> list[AuditPlan]:
        return list(self.session.scalars(
            select(AuditPlan).where(AuditPlan.status == status)
        ).all())


class AuditProcedureRepository(BaseRepository[AuditProcedure]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AuditProcedure)

    def create(self, *, audit_plan_id: int, title: str, **kwargs: Any) -> AuditProcedure:
        procedure = AuditProcedure(audit_plan_id=audit_plan_id, title=title, **kwargs)
        self.add(procedure)
        self.commit()
        return procedure

    def list_for_plan(self, audit_plan_id: int) -> list[AuditProcedure]:
        return list(self.session.scalars(
            select(AuditProcedure).where(AuditProcedure.audit_plan_id == audit_plan_id).order_by(AuditProcedure.sort_order)
        ).all())


class AuditFindingRepository(BaseRepository[AuditFinding]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AuditFinding)

    def create(self, *, audit_plan_id: int, title: str, description: str, **kwargs: Any) -> AuditFinding:
        finding = AuditFinding(audit_plan_id=audit_plan_id, title=title, description=description, **kwargs)
        self.add(finding)
        self.commit()
        return finding

    def get_by_finding_id(self, finding_id: str) -> AuditFinding | None:
        return self.session.scalar(select(AuditFinding).where(AuditFinding.finding_id == finding_id))

    def list_for_plan(self, audit_plan_id: int) -> list[AuditFinding]:
        return list(self.session.scalars(
            select(AuditFinding).where(AuditFinding.audit_plan_id == audit_plan_id)
        ).all())

    def list_open(self) -> list[AuditFinding]:
        return list(self.session.scalars(
            select(AuditFinding).where(AuditFinding.status.in_(["open", "acknowledged", "action_planned"]))
        ).all())

    def list_by_severity(self, severity: str) -> list[AuditFinding]:
        return list(self.session.scalars(
            select(AuditFinding).where(AuditFinding.severity == severity)
        ).all())


class AuditEvidenceRepository(BaseRepository[AuditEvidenceCollection]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AuditEvidenceCollection)

    def create(self, *, audit_plan_id: int, evidence_title: str, **kwargs: Any) -> AuditEvidenceCollection:
        evidence = AuditEvidenceCollection(audit_plan_id=audit_plan_id, evidence_title=evidence_title, **kwargs)
        self.add(evidence)
        self.commit()
        return evidence

    def list_for_plan(self, audit_plan_id: int) -> list[AuditEvidenceCollection]:
        return list(self.session.scalars(
            select(AuditEvidenceCollection).where(AuditEvidenceCollection.audit_plan_id == audit_plan_id)
        ).all())


class AuditInterviewRepository(BaseRepository[AuditInterview]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AuditInterview)

    def create(self, *, audit_plan_id: int, interviewee_name: str, **kwargs: Any) -> AuditInterview:
        interview = AuditInterview(audit_plan_id=audit_plan_id, interviewee_name=interviewee_name, **kwargs)
        self.add(interview)
        self.commit()
        return interview

    def list_for_plan(self, audit_plan_id: int) -> list[AuditInterview]:
        return list(self.session.scalars(
            select(AuditInterview).where(AuditInterview.audit_plan_id == audit_plan_id)
        ).all())


# ═══════════════════════════════════════════════════════════════
# Phase 2e: Corrective Actions (CAPA) Repositories
# ═══════════════════════════════════════════════════════════════


class CorrectiveActionRepository(BaseRepository[CorrectiveAction]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, CorrectiveAction)

    def create(self, *, title: str, **kwargs: Any) -> CorrectiveAction:
        action = CorrectiveAction(title=title, **kwargs)
        self.add(action)
        self.commit()
        return action

    def get_by_action_id(self, action_id: str) -> CorrectiveAction | None:
        return self.session.scalar(select(CorrectiveAction).where(CorrectiveAction.action_id == action_id))

    def list_for_finding(self, finding_id: int) -> list[CorrectiveAction]:
        return list(self.session.scalars(
            select(CorrectiveAction).where(CorrectiveAction.finding_id == finding_id)
        ).all())

    def list_for_risk_item(self, risk_item_id: int) -> list[CorrectiveAction]:
        return list(self.session.scalars(
            select(CorrectiveAction).where(CorrectiveAction.risk_item_id == risk_item_id)
        ).all())

    def list_open(self) -> list[CorrectiveAction]:
        return list(self.session.scalars(
            select(CorrectiveAction).where(CorrectiveAction.status.in_(["open", "in_progress", "implemented"]))
        ).all())

    def list_overdue(self) -> list[CorrectiveAction]:
        from datetime import date
        return list(self.session.scalars(
            select(CorrectiveAction).where(
                CorrectiveAction.status.in_(["open", "in_progress", "implemented"]),
                CorrectiveAction.target_date < date.today(),
            )
        ).all())


class ActionTaskRepository(BaseRepository[ActionTask]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ActionTask)

    def create(self, *, corrective_action_id: int, title: str, **kwargs: Any) -> ActionTask:
        task = ActionTask(corrective_action_id=corrective_action_id, title=title, **kwargs)
        self.add(task)
        self.commit()
        return task

    def list_for_action(self, corrective_action_id: int) -> list[ActionTask]:
        return list(self.session.scalars(
            select(ActionTask)
            .where(ActionTask.corrective_action_id == corrective_action_id)
            .order_by(ActionTask.sort_order)
        ).all())

    def list_pending(self) -> list[ActionTask]:
        return list(self.session.scalars(
            select(ActionTask).where(ActionTask.status.in_(["pending", "in_progress"]))
        ).all())


class EffectivenessReviewRepository(BaseRepository[EffectivenessReview]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, EffectivenessReview)

    def create(self, *, corrective_action_id: int, **kwargs: Any) -> EffectivenessReview:
        review = EffectivenessReview(corrective_action_id=corrective_action_id, **kwargs)
        self.add(review)
        self.commit()
        return review

    def list_for_action(self, corrective_action_id: int) -> list[EffectivenessReview]:
        return list(self.session.scalars(
            select(EffectivenessReview)
            .where(EffectivenessReview.corrective_action_id == corrective_action_id)
            .order_by(EffectivenessReview.created_at.desc())
        ).all())
