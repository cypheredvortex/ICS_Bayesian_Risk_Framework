# ICS Bayesian Risk Framework — Complete Architectural Review & Transformation Plan

---

## Executive Summary

The current application represents a mathematically sound, production-hardened **Bayesian quantitative risk engine** for ICS environments. However, it operates as a **single-purpose risk calculator** rather than a **professional GRC and Audit Management Platform**.

After a comprehensive review, the following document outlines:

1. **Gap Analysis** — Current state vs. enterprise GRC platform
2. **Prioritized Roadmap** — Critical / High / Medium / Low
3. **Redesigned Information Architecture** — Entities, relationships, data flow
4. **Redesigned Navigation Tree** — Professional UI structure
5. **Redesigned Database Schema** — Full ERD with 40+ tables
6. **Redesigned Backend Architecture** — Modular service-oriented design
7. **Redesigned Frontend Architecture** — Component tree, routing, state
8. **Role-Based Workflow Diagrams** — Every professional role's journey
9. **Feature Dependency Graph** — Build order dependencies
10. **Phased Implementation Plan** — 6 phases over 3 releases

---

## 1. Gap Analysis: Current vs. Enterprise GRC Platform

### Legend
| Icon | Meaning |
|------|---------|
| ✅ | Fully implemented |
| 🟡 | Partially implemented |
| ❌ | Not implemented |
| N/A | Not applicable at this layer |

### 1.1 Business Context Layer

| Capability | Current State | Gap | Priority |
|-----------|--------------|-----|----------|
| Organizations | ❌ | No entity for parent organizations | Critical |
| Sites / Facilities | ❌ | No site hierarchy | Critical |
| Plants / Departments | ❌ | No plant/department model | Critical |
| Business Processes | ❌ | No process mapping | Medium |
| Regulatory Obligations | ❌ | No regulatory tracking | High |

### 1.2 Project & Engagement Layer

| Capability | Current State | Gap | Priority |
|-----------|--------------|-----|----------|
| Projects | 🟡 | Basic project exists but minimal fields | High |
| Engagement Lifecycle | ❌ | No project state machine | High |
| Project Templates | ❌ | No reusable templates | Medium |
| Stakeholder Management | ❌ | No stakeholder registry | Medium |
| Project Documents | ❌ | No document management | Medium |

### 1.3 ICS Asset Management Layer

| Capability | Current State | Gap | Priority |
|-----------|--------------|-----|----------|
| Asset Register | 🟡 | Basic asset model (name, type, zone) | Critical |
| Asset Classification | 🟡 | Basic classification (criticality) | High |
| Asset Ownership | ❌ | No asset owner field | High |
| Asset Location | ❌ | No physical/virtual location | High |
| Asset Dependencies | ❌ | No dependency mapping | Medium |
| Asset Configuration | ❌ | No configuration management | Medium |
| Asset Lifecycle Status | ❌ | No lifecycle states | High |
| Asset Documents | ❌ | No asset documents | Medium |

### 1.4 Zoning & Architecture Layer

| Capability | Current State | Gap | Priority |
|-----------|--------------|-----|----------|
| Security Zones | 🟡 | Zone field on asset, no formal zone model | Critical |
| Conduits | ❌ | No conduit entity between zones | Critical |
| Zone Classification | ❌ | No zone levels (IEC 62443) | Critical |
| Zone Trust Relationships | ❌ | No inter-zone trust model | High |
| Architecture Diagrams | ❌ | No visual topology mapper | Medium |

### 1.5 Risk Assessment Layer (Bayesian)

| Capability | Current State | Gap | Priority |
|-----------|--------------|-----|----------|
| Bayesian Network Engine | ✅ | Complete pipeline (topology→graph→CPT→inference→risk) | — |
| Intrinsic Probability | ✅ | Per-asset base probability | — |
| CPT Generation | ✅ | Noisy-OR CPT | — |
| Variable Elimination | ✅ | Exact inference | — |
| Attack Path Analysis | ✅ | BFS-based path finding | — |
| Risk Scoring | ✅ | P × I risk computation | — |
| Evidence-Based Analysis | ✅ | Mark assets compromised/safe | — |
| Risk Register | 🟡 | Risk results stored but no treatment workflow | Critical |
| Risk Matrix (5×5) | ❌ | No visual risk matrix | High |
| Heat Maps | ❌ | No heat map visualization | High |
| Inherent vs Residual Risk | ❌ | Only current risk computed | Critical |
| Risk Scenarios | ❌ | No scenario modeling | High |
| Risk Trend Analysis | ❌ | No historical comparison | Medium |

### 1.6 Threat & Vulnerability Layer

| Capability | Current State | Gap | Priority |
|-----------|--------------|-----|----------|
| Threat Library | ❌ | No threat catalog (STRIDE, ICS-TAXII) | Critical |
| Threat Actor Profiles | ❌ | No actor modeling | Medium |
| Vulnerability Registry | ❌ | No vulnerability database | Critical |
| Vulnerability Scoring | ❌ | No CVSS integration | High |
| Threat-Vulnerability Mapping | ❌ | No TTP→CVE mapping | High |

### 1.7 Controls Management Layer

| Capability | Current State | Gap | Priority |
|-----------|--------------|-----|----------|
| Control Library | ❌ | No controls catalog | Critical |
| Control Categories | ❌ | No preventive/detective/corrective | Critical |
| Control Effectiveness | ❌ | No control effectiveness rating | High |
| Control Testing | ❌ | No test procedures | High |
| Control Ownership | ❌ | No control owners | High |
| Control Evidence | ❌ | No evidence collection | High |

### 1.8 Risk Treatment Layer

| Capability | Current State | Gap | Priority |
|-----------|--------------|-----|----------|
| Treatment Plans | ❌ | No treatment plan entity | Critical |
| Treatment Options | ❌ | No mitigate/transfer/accept/avoid | Critical |
| Risk Acceptance | ❌ | No formal acceptance workflow | Critical |
| Treatment Deadlines | ❌ | No due dates | High |
| Treatment Budget | ❌ | No cost estimation | Medium |

### 1.9 Compliance Layer

| Capability | Current State | Gap | Priority |
|-----------|--------------|-----|----------|
| Compliance Frameworks | ❌ | No framework data model | Critical |
| ISO 27001 Mapping | ❌ | No mapping | High |
| NIST CSF Mapping | ❌ | No mapping | High |
| NIST SP 800-53 Mapping | ❌ | No mapping | High |
| IEC 62443 Mapping | ❌ | No mapping | Critical |
| CIS Controls Mapping | ❌ | No mapping | High |
| Control-to-Requirement Mapping | ❌ | No mapping entity | Critical |
| Compliance Gap Analysis | ❌ | No gap reporting | High |

### 1.10 Audit Management Layer

| Capability | Current State | Gap | Priority |
|-----------|--------------|-----|----------|
| Audit Programs | ❌ | No program definition | Critical |
| Audit Plans | ❌ | No plan entity | Critical |
| Audit Scope | ❌ | No scope definition | Critical |
| Audit Objectives | ❌ | No objective setting | Critical |
| Audit Procedures | ❌ | No procedure checklists | High |
| Evidence Collection | ❌ | No evidence forms | Critical |
| Interview Management | ❌ | No interview tracking | Medium |
| Control Testing | ❌ | No test execution | High |
| Audit Findings | ❌ | No finding entity | Critical |
| Finding Severity | ❌ | No severity classification | Critical |
| Recommendations | ❌ | No recommendation model | High |
| Management Responses | ❌ | No response workflow | High |

### 1.11 Corrective Action Layer

| Capability | Current State | Gap | Priority |
|-----------|--------------|-----|----------|
| CAPA Workflow | ❌ | No corrective action process | Critical |
| Action Assignment | ❌ | No assignment workflow | Critical |
| Due Date Tracking | ❌ | No deadline management | Critical |
| Status Tracking | ❌ | No state machine | Critical |
| Evidence of Closure | ❌ | No closure evidence | High |
| Effectiveness Review | ❌ | No effectiveness check | Medium |

### 1.12 Reporting & Dashboard Layer

| Capability | Current State | Gap | Priority |
|-----------|--------------|-----|----------|
| Executive Dashboard | ❌ | No dashboard | Critical |
| Risk Dashboard | ❌ | No risk-specific view | Critical |
| Compliance Dashboard | ❌ | No compliance view | High |
| Audit Dashboard | ❌ | No audit view | High |
| CISO Dashboard | ❌ | No executive view | High |
| ICS Security Posture Report | ❌ | No posture report | High |
| Risk Register Report | ❌ | No register export | High |
| Compliance Report | ❌ | No compliance export | High |
| Audit Report | ❌ | No audit report | High |
| Treatment Plan Report | ❌ | No treatment report | Medium |

### 1.13 User & Access Management Layer

| Capability | Current State | Gap | Priority |
|-----------|--------------|-----|----------|
| User Management | ❌ | No user model | Critical |
| Role-Based Access | ❌ | No roles | Critical |
| Permissions | ❌ | No permission system | Critical |
| Authentication | ❌ | No auth (no login) | Critical |
| Multi-tenancy | ❌ | No tenant isolation | High |
| Session Management | ❌ | No sessions | Critical |
| Audit Trail | ❌ | No activity log | High |

### 1.14 Infrastructure & Integration Layer

| Capability | Current State | Gap | Priority |
|-----------|--------------|-----|----------|
| API Security | 🟡 | Rate limiting, CORS, but no auth | Critical |
| File Storage | 🟡 | Local files only | Medium |
| Email Notifications | ❌ | No email integration | Medium |
| Import/Export | 🟡 | JSON/YAML/CSV import only | Medium |
| API Documentation | 🟡 | OpenAPI auto-generated | Medium |
| Data Retention | ❌ | No retention policies | Low |
| Backup/Restore | ❌ | No backup workflow | Medium |

---

## 2. Prioritized Roadmap

### Critical (Foundation — Must Have for MVP)

| # | Capability | Rationale | Effort |
|---|-----------|-----------|--------|
| 1 | User Authentication & RBAC | No GRC platform operates without user identity | 3 weeks |
| 2 | Organization/Site/Plant Hierarchy | Must know "where" risk lives | 1 week |
| 3 | Comprehensive Asset Register | Foundation for all risk calculations | 2 weeks |
| 4 | Formal Zone & Conduit Model | IEC 62443 requires formal zoning | 2 weeks |
| 5 | Threat Library | Must catalog threats to assess risk | 1 week |
| 6 | Vulnerability Registry | Must catalog vulnerabilities | 1 week |
| 7 | Control Library | Must catalog existing controls | 2 weeks |
| 8 | Risk Register with Treatment Workflow | Core GRC function | 3 weeks |
| 9 | Risk Matrix & Heat Map | Professional requirement | 1 week |
| 10 | Compliance Framework Data Model | Multi-framework support | 2 weeks |
| 11 | Audit Finding Entity | Core audit function | 1 week |
| 12 | Corrective Action Workflow | Must close the loop | 2 weeks |
| 13 | Role-Based Dashboards | Professional requirement | 2 weeks |
| 14 | Bayesian Integration with Risk Register | Core differentiator | 2 weeks |

**Total Critical Effort: ~25 weeks (6 months)**

### High (Release 1.1)

| # | Capability | Rationale | Effort |
|---|-----------|-----------|--------|
| 15 | Asset Classification Taxonomy | ICS-specific classification | 1 week |
| 16 | Inherent vs Residual Risk | Professional requirement | 1 week |
| 17 | Control Effectiveness Rating | Required for residual risk | 1 week |
| 18 | Framework-to-Control Mapping | Compliance verification | 2 weeks |
| 19 | Audit Program & Plan | Structured audit | 2 weeks |
| 20 | Compliance Gap Analysis | Required for audits | 1 week |
| 21 | Executive Reports (PDF) | Stakeholder communication | 2 weeks |
| 22 | Email Notifications | Workflow requirement | 1 week |
| 23 | ICS Security Posture Report | CISO requirement | 1 week |

**Total High Effort: ~12 weeks (3 months)**

### Medium (Release 1.2)

| # | Capability | Rationale | Effort |
|---|-----------|-----------|--------|
| 24 | Business Process Mapping | Context enrichment | 2 weeks |
| 25 | Asset Dependency Mapping | Impact analysis | 2 weeks |
| 26 | Risk Scenario Modeling | What-if analysis | 3 weeks |
| 27 | Trend Analysis | Risk over time | 2 weeks |
| 28 | Audit Evidence Forms | Structured collection | 2 weeks |
| 29 | Interview Management | Audit practice | 1 week |
| 30 | Document Management | Evidence repository | 2 weeks |
| 31 | API Token Authentication | Integration | 1 week |
| 32 | Data Export (XLSX, DOCX) | Professional need | 2 weeks |

**Total Medium Effort: ~17 weeks (4 months)**

### Low (Release 2.0)

| # | Capability | Rationale | Effort |
|---|-----------|-----------|--------|
| 33 | Threat Actor Profiles | Advanced threat intel | 2 weeks |
| 34 | Budget/Cost Estimation | Risk financing | 2 weeks |
| 35 | Effectiveness Review Workflow | Mature CAPA | 1 week |
| 36 | Data Retention Policies | Compliance | 1 week |
| 37 | Backup/Restore UI | Operational | 1 week |
| 38 | Multi-language Support | International | 3 weeks |
| 39 | REST API Rate Limit by Role | Enterprise hardening | 1 week |
| 40 | SSO / LDAP Integration | Enterprise auth | 3 weeks |

**Total Low Effort: ~14 weeks (3.5 months)**

---

## 3. Redesigned Information Architecture

### 3.1 Core Domain Model

```
┌──────────────────────────────────────────────────────────┐
│                     ORGANIZATION                          │
│  (Legal entity / Enterprise / Government Agency)          │
└────────────────────────┬─────────────────────────────────┘
                         │ has many
                         ▼
┌──────────────────────────────────────────────────────────┐
│                         SITE                              │
│  (Physical location / Campus / Region)                    │
└────────────────────────┬─────────────────────────────────┘
                         │ has many
                         ▼
┌──────────────────────────────────────────────────────────┐
│                         PLANT                             │
│  (Facility / Factory / Substation / Treatment Plant)      │
└────────────┬──────────────────────┬──────────────────────┘
             │                      │
    ┌────────┴────────┐    ┌───────┴────────┐
    │    PROJECTS     │    │   ASSET REGISTER              │
    │  (Engagements)  │    │  (All ICS assets)             │
    └────────┬────────┘    └───────┬───────────────────────┘
             │                      │
             ▼                      ▼
    ┌──────────────────┐  ┌──────────────────┐
    │  RISK ASSESSMENT │  │  ZONES & CONDUITS│
    │  (Bayesian)      │  │  (IEC 62443)     │
    └────────┬─────────┘  └────────┬─────────┘
             │                      │
             ▼                      ▼
    ┌──────────────────┐  ┌──────────────────┐
    │  RISK REGISTER   │  │  THREATS         │
    │  (All risks)     │  │  VULNERABILITIES │
    └────────┬─────────┘  └────────┬─────────┘
             │                      │
             ▼                      ▼
    ┌──────────────────┐  ┌──────────────────┐
    │  RISK TREATMENT  │  │  CONTROLS        │
    │  (Plans)         │  │  (Library)       │
    └────────┬─────────┘  └────────┬─────────┘
             │                      │
             └──────┬──────────────┘
                    ▼
    ┌──────────────────────────────────┐
    │      COMPLIANCE MAPPING          │
    │  (ISO 27001, NIST CSF, IEC 62443)│
    └──────────────┬───────────────────┘
                   ▼
    ┌──────────────────────────────────┐
    │          AUDIT                   │
    │  (Program → Plan → Execution)    │
    └──────────────┬───────────────────┘
                   ▼
    ┌──────────────────────────────────┐
    │    CORRECTIVE ACTIONS (CAPA)     │
    │  (Findings → Actions → Closure)  │
    └──────────────────────────────────┘
```

### 3.2 Entity Relationship Summary

| Domain | Key Entities |
|--------|-------------|
| **Business Context** | Organization, Site, Plant, Department, BusinessProcess |
| **Projects** | Project, ProjectTeam, ProjectPhase, ProjectDocument |
| **Asset Management** | Asset, AssetCategory, AssetCriticality, AssetDependency, AssetDocument |
| **Zones & Conduits** | SecurityZone, ZoneClassification, Conduit, ConduitType |
| **Threats** | Threat, ThreatActor, ThreatCategory, TTP_Mapping |
| **Vulnerabilities** | Vulnerability, VulnerabilityScan, CVE_Entry, CVSS_Score |
| **Controls** | Control, ControlCategory, ControlTest, ControlEvidence |
| **Risk Assessment** | BayesianNetwork, BayesianNode, CPT, InferenceResult, Evidence_Entry |
| **Risk Register** | RiskItem, RiskScenario, RiskMatrix, RiskHistory |
| **Risk Treatment** | TreatmentPlan, TreatmentOption, RiskAcceptance, ActionItem |
| **Compliance** | ComplianceFramework, FrameworkRequirement, ControlMapping, ComplianceGap |
| **Audit** | AuditProgram, AuditPlan, AuditScope, AuditProcedure, AuditFinding, AuditEvidence |
| **Quality** | CorrectiveAction, ActionTask, EffectivenessReview, ClosureEvidence |
| **Users & Access** | User, Role, Permission, UserRole, UserSession |
| **Reporting** | Dashboard, DashboardWidget, ReportDefinition, ReportSchedule |
| **System** | Notification, NotificationTemplate, AuditLog, Comment, Attachment |

---

## 4. Redesigned Navigation Tree

### 4.1 Main Navigation Structure

```
┌──────────────────────────────────────────────────────────────────┐
│  Logo   [Search bar]        [Notifications] [Profile ▼] [Help]   │
├──────────────────────────────────────────────────────────────────┤
│ ◆ Dashboard                                                     │
│ ◆ Projects                                                      │
│ ◆ Assets                                                        │
│ ◆ Threats & Vulnerabilities                                     │
│ ◆ Controls                                                      │
│ ◆ Risk Management                                               │
│ ◆ Compliance                                                    │
│ ◆ Audit                                                         │
│ ◆ Corrective Actions                                            │
│ ◆ Reporting                                                     │
│ ⚙ Administration                                                │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 Dashboard Sub-navigation

```
◆ Dashboard
├─ 📊 Executive Dashboard (CISO)
├─ 📊 Risk Manager Dashboard
├─ 📊 Compliance Dashboard
├─ 📊 Audit Dashboard
├─ 📊 ICS Security Engineer Dashboard
└─ 📊 Analyst Dashboard
```

### 4.3 Projects Sub-navigation

```
◆ Projects
├─ All Projects
├─ My Projects
├─ Create Project
├─ Project Templates
└─ 🗂 Archived Projects
```

### 4.4 Assets Sub-navigation

```
◆ Assets
├─ 📋 Asset Register
├─ 🏭 Sites & Plants
├─ 🔲 Zones & Conduits
├─ 📂 Asset Categories
├─ 📎 Asset Dependencies
└─ 📄 Asset Documents
```

### 4.5 Threats & Vulnerabilities Sub-navigation

```
◆ Threats & Vulnerabilities
├─ 🦠 Threat Library
├─ 🎭 Threat Actors
├─ 🐛 Vulnerability Registry
├─ 📡 Vulnerability Scans
├─ 🔗 TTP-CVE Mappings
└─ 📊 Threat Intelligence
```

### 4.6 Controls Sub-navigation

```
◆ Controls
├─ 🛡️ Control Library
├─ 📂 Control Categories
├─ ✅ Control Tests
├─ 📎 Control Evidence
├─ 📊 Control Effectiveness
└─ 📋 Control Mapping
```

### 4.7 Risk Management Sub-navigation

```
◆ Risk Management
├─ 📋 Risk Register
├─ 📊 Risk Matrix
├─ 🔥 Heat Maps
├─ 🧠 Bayesian Analysis
├─ 📈 Risk Trends
├─ 🎯 Risk Scenarios
├─ 🛠️ Risk Treatment
├─ ✅ Risk Acceptance
└─ 📜 Risk History
```

### 4.8 Compliance Sub-navigation

```
◆ Compliance
├─ 📚 Frameworks
│  ├─ ISO 27001
│  ├─ NIST CSF
│  ├─ NIST SP 800-53
│  ├─ IEC 62443
│  └─ CIS Controls
├─ 🔗 Control Mapping
├─ 📊 Compliance Status
├─ 📉 Gap Analysis
└─ 📄 Compliance Reports
```

### 4.9 Audit Sub-navigation

```
◆ Audit
├─ 📋 Audit Programs
├─ 📅 Audit Plans
├─ 🔍 Audit Execution
├─ 📝 Audit Findings
├─ 📎 Audit Evidence
├─ 🗣️ Interview Records
└─ 📊 Audit Reports
```

### 4.10 Corrective Actions Sub-navigation

```
◆ Corrective Actions
├─ 📋 All Actions
├─ 📝 My Actions
├─ ⏳ Overdue Actions
├─ ✅ Completed Actions
├─ 📊 CAPA Dashboard
└─ 📄 Effectiveness Reviews
```

### 4.11 Reporting Sub-navigation

```
◆ Reporting
├─ 📄 Executive Risk Report
├─ 📋 Risk Register Report
├─ 📄 Compliance Report
├─ 📄 Audit Report
├─ 📄 Asset Report
├─ 📄 ICS Security Posture
├─ 📄 Treatment Plan Report
├─ 📄 Bayesian Analysis Report
├─ 📊 Custom Reports
└─ 📅 Scheduled Reports
```

### 4.12 Administration Sub-navigation

```
⚙ Administration
├─ 👥 Users
├─ 🔐 Roles & Permissions
├─ 🏢 Organizations
├─ ⚙️ System Settings
├─ 📁 Data Management
│  ├─ Import
│  └─ Export
├─ 🔄 Integrations
├─ 📋 Audit Log
└─ 📊 System Health
```

---

## 5. Redesigned Database Schema

### 5.1 Business Context Tables

```sql
-- === ORGANIZATIONS & SITES ===
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    legal_name VARCHAR(255),
    registration_number VARCHAR(100),
    tax_id VARCHAR(100),
    industry_sector VARCHAR(100),
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),
    website VARCHAR(255),
    phone VARCHAR(50),
    email VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

CREATE TABLE sites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50),
    site_type VARCHAR(50), -- headquarters, regional, branch, plant
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    timezone VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(organization_id, name)
);

CREATE TABLE plants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50),
    plant_type VARCHAR(100), -- substation, treatment_plant, factory, refinery
    ics_domain VARCHAR(100), -- power, water, oil_gas, manufacturing
    criticality_level VARCHAR(20), -- critical, high, medium, low
    is_active BOOLEAN DEFAULT true,
    operational_status VARCHAR(50), -- operational, maintenance, decommissioned
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(site_id, name)
);

CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plant_id UUID REFERENCES plants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50),
    manager_name VARCHAR(255),
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE business_processes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plant_id UUID NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    process_owner VARCHAR(255),
    criticality VARCHAR(20),
    recovery_time_objective INTEGER, -- minutes
    recovery_point_objective INTEGER, -- minutes
    is_critical BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 5.2 User & Access Control

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    job_title VARCHAR(255),
    department VARCHAR(255),
    phone VARCHAR(50),
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    is_locked BOOLEAN DEFAULT false,
    password_changed_at TIMESTAMP WITH TIME ZONE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    mfa_enabled BOOLEAN DEFAULT false,
    mfa_secret VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_system_role BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(100) NOT NULL UNIQUE, -- e.g., "risk:register:write"
    name VARCHAR(255) NOT NULL,
    description TEXT,
    module VARCHAR(50), -- dashboard, project, asset, risk, compliance, audit, capa, admin
    action VARCHAR(50), -- read, write, delete, approve
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE, -- scope
    assigned_by UUID REFERENCES users(id),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id, organization_id)
);

CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 5.3 Project & Engagement

```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    plant_id UUID REFERENCES plants(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    project_type VARCHAR(50), -- risk_assessment, audit, compliance, consulting
    status VARCHAR(30) DEFAULT 'draft',
    -- Status: draft, active, on_hold, completed, archived, cancelled
    priority VARCHAR(20) DEFAULT 'medium',
    start_date DATE,
    end_date DATE,
    project_manager UUID REFERENCES users(id),
    sponsor UUID REFERENCES users(id),
    methodology VARCHAR(100), -- iso_27005, nist_rmf, octave, custom
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

CREATE TABLE project_team (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_name VARCHAR(100), -- lead_auditor, team_member, reviewer
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(project_id, user_id)
);

CREATE TABLE project_phases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    sequence_order INTEGER NOT NULL,
    status VARCHAR(30) DEFAULT 'pending',
    start_date DATE,
    end_date DATE,
    completed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(project_id, sequence_order)
);

CREATE TABLE project_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    file_size INTEGER,
    document_type VARCHAR(50), -- scope, report, evidence, reference
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 5.4 Asset Register (Extended)

```sql
CREATE TABLE asset_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    parent_id UUID REFERENCES asset_categories(id),
    ics_category VARCHAR(50), -- controller, network, hmi, server, iot, physical, human
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plant_id UUID REFERENCES plants(id) ON DELETE SET NULL,
    site_id UUID REFERENCES sites(id) ON DELETE SET NULL,
    organization_id UUID REFERENCES organizations(id),
    project_id UUID REFERENCES projects(id),
    
    -- Identity
    asset_tag VARCHAR(100) UNIQUE,
    name VARCHAR(255) NOT NULL,
    alias VARCHAR(255),
    barcode VARCHAR(100),
    serial_number VARCHAR(100),
    
    -- Categorization
    category_id UUID REFERENCES asset_categories(id),
    asset_type VARCHAR(100), -- plc, rtu, hmi, scada_server, historian, firewall, switch, operator
    sub_type VARCHAR(100),
    
    -- ICS Security Zoning
    security_zone_id UUID REFERENCES security_zones(id),
    zone VARCHAR(255), -- flat zone name (legacy compat)
    
    -- Classification
    criticality VARCHAR(20), -- critical, high, medium, low
    classification VARCHAR(50), -- public, internal, confidential, restricted
    data_sensitivity VARCHAR(50),
    
    -- Technical
    vendor VARCHAR(255),
    model VARCHAR(255),
    firmware_version VARCHAR(100),
    software_version VARCHAR(100),
    hardware_version VARCHAR(100),
    operating_system VARCHAR(100),
    ip_address VARCHAR(45),
    mac_address VARCHAR(17),
    network_segment VARCHAR(255),
    
    -- Operational
    operational_status VARCHAR(50), -- operational, standby, maintenance, retired
    commissioning_date DATE,
    last_maintenance_date DATE,
    maintenance_interval_days INTEGER,
    expected_lifetime_years INTEGER,
    
    -- Risk Parameters (for Bayesian engine)
    exposure_level VARCHAR(20),
    patch_level VARCHAR(20),
    availability_requirement VARCHAR(20), -- high, medium, low
    integrity_requirement VARCHAR(20),
    confidentiality_requirement VARCHAR(20),
    intrinsic_probability DECIMAL(6,4),
    consequence_severity DECIMAL(6,2),
    scope_multiplier DECIMAL(6,2),
    
    -- Ownership
    asset_owner UUID REFERENCES users(id),
    technical_owner UUID REFERENCES users(id),
    custodian UUID REFERENCES users(id),
    
    -- Location
    location_building VARCHAR(255),
    location_room VARCHAR(255),
    location_rack VARCHAR(100),
    location_rack_position INTEGER,
    
    -- Spatial (for topology visualization)
    x_position DECIMAL(10,4),
    y_position DECIMAL(10,4),
    
    -- Lifecycle
    lifecycle_status VARCHAR(30), -- planned, active, decommissioned
    decommissioned_date DATE,
    
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

CREATE TABLE asset_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    depends_on_asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    dependency_type VARCHAR(50), -- network, power, data, physical
    description TEXT,
    criticality VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(asset_id, depends_on_asset_id, dependency_type)
);

CREATE TABLE asset_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    document_type VARCHAR(50), -- datasheet, manual, diagram, certificate
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE asset_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),
    source_asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    destination_asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL,
    -- controls, monitors, actuates, connects-to, programs/operates
    protocol VARCHAR(50), -- modbus, dnp3, opc-ua, profinet, mqtt, http
    trust_level VARCHAR(20), -- none, low, medium, high
    mitre_technique VARCHAR(20),
    is_firewalled BOOLEAN DEFAULT false,
    firewall_rule_id VARCHAR(100),
    propagation_weight DECIMAL(6,4),
    bandwidth_mbps INTEGER,
    is_encrypted BOOLEAN DEFAULT false,
    is_critical BOOLEAN DEFAULT false,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(source_asset_id, destination_asset_id, relationship_type)
);
```

### 5.5 Zones & Conduits

```sql
CREATE TABLE security_zones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plant_id UUID NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    zone_level INTEGER NOT NULL, -- 1(Cell/Area) through 5(Enterprise) per IEC 62443
    description TEXT,
    color_hex VARCHAR(7),
    classification VARCHAR(50), -- safety_critical, security_critical, operational, business
    access_requirements TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(plant_id, name)
);

CREATE TABLE conduits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plant_id UUID NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    source_zone_id UUID NOT NULL REFERENCES security_zones(id) ON DELETE CASCADE,
    destination_zone_id UUID NOT NULL REFERENCES security_zones(id) ON DELETE CASCADE,
    conduit_type VARCHAR(50), -- network, physical, wireless
    communication_protocols TEXT,
    security_requirements TEXT,
    is_encrypted BOOLEAN DEFAULT false,
    is_physically_secured BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(plant_id, name)
);
```

### 5.6 Threats & Vulnerabilities

```sql
CREATE TABLE threat_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    reference_framework VARCHAR(50), -- stride, ics_attack, mitre_ics
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE threats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    threat_category_id UUID REFERENCES threat_categories(id),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    threat_id VARCHAR(50), -- e.g., T0886 (MITRE ICS)
    source VARCHAR(100), -- mitre_ics, stride, custom
    likelihood_rating VARCHAR(20), -- very_high, high, medium, low, very_low
    typical_impact VARCHAR(50), -- safety, environmental, operational, financial
    ics_impact VARCHAR(50), -- loss_of_view, loss_of_control, equipment_damage
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE threat_actors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    actor_type VARCHAR(50), -- nation_state, criminal, hacktivist, insider, terrorist
    capability VARCHAR(30), -- advanced, moderate, basic
    motivation VARCHAR(100), -- financial, espionage, sabotage, ideological
    targeting_sectors TEXT,
    common_ttps TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE vulnerabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cve_id VARCHAR(30), -- CVE-YYYY-NNNNN
    name VARCHAR(255) NOT NULL,
    description TEXT,
    vulnerability_type VARCHAR(100), -- buffer_overflow, xss, auth_bypass, etc.
    cvss_score DECIMAL(3,1),
    cvss_vector VARCHAR(100),
    cvss_severity VARCHAR(20), -- none, low, medium, high, critical
    ics_impact VARCHAR(50),
    exploit_available BOOLEAN DEFAULT false,
    exploitability VARCHAR(30), -- easy, moderate, difficult
    affected_vendor VARCHAR(255),
    affected_product VARCHAR(255),
    affected_version VARCHAR(100),
    patch_available BOOLEAN DEFAULT false,
    patch_url VARCHAR(500),
    published_date DATE,
    discovered_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(cve_id)
);

CREATE TABLE asset_vulnerabilities (
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    vulnerability_id UUID NOT NULL REFERENCES vulnerabilities(id) ON DELETE CASCADE,
    detected_date DATE DEFAULT CURRENT_DATE,
    detection_method VARCHAR(50), -- scan, manual, vendor_advisory
    status VARCHAR(30) DEFAULT 'open', -- open, in_progress, mitigated, accepted, resolved
    mitigation_notes TEXT,
    resolved_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (asset_id, vulnerability_id)
);
```

### 5.7 Control Library

```sql
CREATE TABLE control_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    control_type VARCHAR(30), -- preventive, detective, corrective, deterrent, compensating
    ics_control_domain VARCHAR(100), -- access_control, network_seg, monitoring, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE controls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    control_category_id UUID REFERENCES control_categories(id),
    control_id VARCHAR(50) UNIQUE, -- e.g., "AC-1", "ICS-01"
    name VARCHAR(255) NOT NULL,
    description TEXT,
    control_type VARCHAR(30), -- preventive, detective, corrective, deterrent
    implementation_status VARCHAR(30), -- implemented, partially, planned, not_implemented
    effectiveness_rating VARCHAR(20), -- very_high, high, medium, low, very_low
    automation_level VARCHAR(20), -- automated, semi_automated, manual
    frequency VARCHAR(50), -- continuous, daily, weekly, monthly, annually
    owner UUID REFERENCES users(id),
    evidence_required BOOLEAN DEFAULT false,
    evidence_description TEXT,
    last_reviewed_date DATE,
    next_review_date DATE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE control_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    control_id UUID NOT NULL REFERENCES controls(id) ON DELETE CASCADE,
    asset_id UUID REFERENCES assets(id),
    tester UUID REFERENCES users(id),
    test_date DATE,
    test_method VARCHAR(50), -- interview, observation, examination, technical
    test_procedure TEXT,
    result VARCHAR(30), -- pass, fail, partial, not_tested, na
    result_details TEXT,
    evidence_path VARCHAR(500),
    next_test_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE control_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    control_id UUID NOT NULL REFERENCES controls(id) ON DELETE CASCADE,
    asset_id UUID REFERENCES assets(id),
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    evidence_type VARCHAR(50), -- screenshot, config, policy, log, certification
    description TEXT,
    collected_by UUID REFERENCES users(id),
    collected_date DATE DEFAULT CURRENT_DATE,
    valid_until DATE,
    is_current BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 5.8 Bayesian Network Integration

```sql
CREATE TABLE bayesian_networks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version INTEGER DEFAULT 1,
    inference_algorithm VARCHAR(50) DEFAULT 'variable_elimination',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE bayesian_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bayesian_network_id UUID NOT NULL REFERENCES bayesian_networks(id) ON DELETE CASCADE,
    asset_id UUID REFERENCES assets(id),
    node_name VARCHAR(255) NOT NULL,
    node_type VARCHAR(50), -- device, human, physical
    intrinsic_probability DECIMAL(6,4),
    is_evidence_node BOOLEAN DEFAULT false,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(bayesian_network_id, node_name)
);

CREATE TABLE bayesian_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bayesian_network_id UUID NOT NULL REFERENCES bayesian_networks(id) ON DELETE CASCADE,
    asset_connection_id UUID REFERENCES asset_connections(id),
    source_node_id UUID NOT NULL REFERENCES bayesian_nodes(id) ON DELETE CASCADE,
    target_node_id UUID NOT NULL REFERENCES bayesian_nodes(id) ON DELETE CASCADE,
    propagation_weight DECIMAL(6,4),
    firewalled BOOLEAN DEFAULT false,
    protocol VARCHAR(50),
    trust_level VARCHAR(20),
    mitre_technique VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(bayesian_network_id, source_node_id, target_node_id)
);

CREATE TABLE conditional_probability_tables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bayesian_network_id UUID NOT NULL REFERENCES bayesian_networks(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES bayesian_nodes(id) ON DELETE CASCADE,
    table_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(bayesian_network_id, node_id)
);

CREATE TABLE inference_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bayesian_network_id UUID NOT NULL REFERENCES bayesian_networks(id) ON DELETE CASCADE,
    node_id UUID REFERENCES bayesian_nodes(id),
    asset_id UUID REFERENCES assets(id),
    posterior_probability DECIMAL(6,4),
    evidence_snapshot JSONB,
    inference_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE evidence_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bayesian_network_id UUID NOT NULL REFERENCES bayesian_networks(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES bayesian_nodes(id),
    state_value INTEGER NOT NULL, -- 0 (Safe) or 1 (Compromised)
    set_by UUID REFERENCES users(id),
    scenario_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE attack_paths (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bayesian_network_id UUID NOT NULL REFERENCES bayesian_networks(id) ON DELETE CASCADE,
    path_nodes JSONB NOT NULL, -- ordered array of node IDs
    path_score DECIMAL(8,4),
    length INTEGER,
    score_components JSONB,
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE bayesian_risk_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bayesian_network_id UUID NOT NULL REFERENCES bayesian_networks(id) ON DELETE CASCADE,
    asset_id UUID REFERENCES assets(id),
    asset_name VARCHAR(255) NOT NULL,
    likelihood DECIMAL(6,4), -- P(compromised|evidence)
    impact DECIMAL(8,4), -- severity × scope_mult × impact_weight
    risk_score DECIMAL(8,4), -- likelihood × impact
    risk_level VARCHAR(20), -- critical, high, moderate, low
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 5.9 Risk Register

```sql
CREATE TABLE risk_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),
    organization_id UUID REFERENCES organizations(id),
    plant_id UUID REFERENCES plants(id),
    asset_id UUID REFERENCES assets(id),
    bayesian_risk_result_id UUID REFERENCES bayesian_risk_results(id),
    
    -- Identification
    risk_id VARCHAR(50) UNIQUE, -- RISK-2024-0001
    title VARCHAR(500) NOT NULL,
    description TEXT,
    
    -- Risk Scenario
    threat_id UUID REFERENCES threats(id),
    vulnerability_id UUID REFERENCES vulnerabilities(id),
    scenario TEXT,
    
    -- Current Risk
    inherent_likelihood DECIMAL(6,4),
    inherent_impact DECIMAL(8,4),
    inherent_risk DECIMAL(8,4),
    inherent_risk_level VARCHAR(20),
    
    -- Residual Risk (after controls)
    residual_likelihood DECIMAL(6,4),
    residual_impact DECIMAL(8,4),
    residual_risk DECIMAL(8,4),
    residual_risk_level VARCHAR(20),
    
    -- Bayesian-Specific
    bayesian_likelihood DECIMAL(6,4), -- P(compromised|evidence)
    bayesian_risk_score DECIMAL(8,4), -- Bayesian × impact
    bayesian_risk_level VARCHAR(20),
    
    -- Risk Details
    risk_type VARCHAR(50), -- strategic, operational, financial, compliance, security
    risk_category VARCHAR(100), -- maliciouse_act, natural_disaster, system_failure, human_error
    root_cause TEXT,
    consequence TEXT,
    
    -- Treatment
    treatment_strategy VARCHAR(30), -- mitigate, transfer, accept, avoid
    treatment_status VARCHAR(30), -- identified, planned, in_progress, completed, accepted
    risk_owner UUID REFERENCES users(id),
    risk_owner_approval BOOLEAN DEFAULT false,
    
    -- Review
    review_frequency VARCHAR(30), -- monthly, quarterly, annually
    last_reviewed_date DATE,
    next_review_date DATE,
    is_accepted BOOLEAN DEFAULT false,
    accepted_by UUID REFERENCES users(id),
    acceptance_date DATE,
    acceptance_reason TEXT,
    
    -- State
    status VARCHAR(30) DEFAULT 'identified', -- identified, assessed, treatment_planned, in_progress, closed
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

CREATE TABLE risk_scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    risk_item_id UUID NOT NULL REFERENCES risk_items(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    bayesian_network_id UUID REFERENCES bayesian_networks(id),
    evidence_used JSONB,
    inherent_risk DECIMAL(8,4),
    residual_risk DECIMAL(8,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE risk_treatment_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    risk_item_id UUID NOT NULL REFERENCES risk_items(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    treatment_option VARCHAR(30), -- mitigate, transfer, accept, avoid
    target_date DATE,
    cost_estimate DECIMAL(14,2),
    cost_currency VARCHAR(3) DEFAULT 'USD',
    responsible_person UUID REFERENCES users(id),
    status VARCHAR(30) DEFAULT 'draft',
    -- Status: draft, approved, in_progress, completed, cancelled
    approval_status VARCHAR(30) DEFAULT 'pending',
    approved_by UUID REFERENCES users(id),
    approval_date DATE,
    rejection_reason TEXT,
    effectiveness_review_required BOOLEAN DEFAULT false,
    effectiveness_review_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE risk_acceptances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    risk_item_id UUID NOT NULL REFERENCES risk_items(id) ON DELETE CASCADE,
    accepted_by UUID NOT NULL REFERENCES users(id),
    acceptance_type VARCHAR(30), -- temporary, permanent, conditional
    justification TEXT NOT NULL,
    expiration_date DATE,
    reviewing_authority VARCHAR(255),
    conditions TEXT,
    status VARCHAR(30) DEFAULT 'active', -- active, expired, revoked
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE risk_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    risk_item_id UUID NOT NULL REFERENCES risk_items(id) ON DELETE CASCADE,
    changed_by UUID NOT NULL REFERENCES users(id),
    change_type VARCHAR(50), -- created, assessed, treated, accepted, reviewed
    previous_values JSONB,
    new_values JSONB,
    change_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 5.10 Compliance Framework

```sql
CREATE TABLE compliance_frameworks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE, -- ISO 27001, NIST CSF, IEC 62443
    version VARCHAR(50) NOT NULL,
    publisher VARCHAR(255),
    description TEXT,
    domain VARCHAR(100), -- information_security, ics_security, privacy
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name, version)
);

CREATE TABLE framework_requirements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    framework_id UUID NOT NULL REFERENCES compliance_frameworks(id) ON DELETE CASCADE,
    requirement_id VARCHAR(50) NOT NULL, -- e.g., "AC-1", "PR.AC-1", "IEC 62443-2-1"
    parent_requirement_id UUID REFERENCES framework_requirements(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    requirement_type VARCHAR(50), -- control, policy, process, technical
    implementation_guidance TEXT,
    evidence_requirements TEXT,
    weight_importance VARCHAR(20), -- critical, high, medium, low
    sort_order INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(framework_id, requirement_id)
);

CREATE TABLE control_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    control_id UUID NOT NULL REFERENCES controls(id) ON DELETE CASCADE,
    requirement_id UUID NOT NULL REFERENCES framework_requirements(id) ON DELETE CASCADE,
    mapping_type VARCHAR(30), -- directly_addresses, partially_addresses, related
    mapping_notes TEXT,
    mapping_justification TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(control_id, requirement_id)
);

CREATE TABLE compliance_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    plant_id UUID REFERENCES plants(id),
    requirement_id UUID NOT NULL REFERENCES framework_requirements(id) ON DELETE CASCADE,
    gap_description TEXT NOT NULL,
    severity VARCHAR(20),
    status VARCHAR(30), -- open, planned, remediated, accepted
    remediation_plan TEXT,
    target_closure_date DATE,
    closed_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE compliance_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    plant_id UUID REFERENCES plants(id),
    framework_id UUID NOT NULL REFERENCES compliance_frameworks(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id),
    assessment_date DATE DEFAULT CURRENT_DATE,
    assessor UUID REFERENCES users(id),
    overall_status VARCHAR(30), -- compliant, partially_compliant, non_compliant, not_assessed
    compliance_percentage DECIMAL(5,2),
    findings_summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 5.11 Audit Management

```sql
CREATE TABLE audit_programs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    program_type VARCHAR(50), -- annual, quarterly, continuous, ad_hoc
    start_date DATE,
    end_date DATE,
    status VARCHAR(30) DEFAULT 'draft', -- draft, active, completed, archived
    program_manager UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE audit_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_program_id UUID REFERENCES audit_programs(id),
    organization_id UUID REFERENCES organizations(id),
    plant_id UUID REFERENCES plants(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    audit_type VARCHAR(50), -- internal, external, compliance, ics_security, regulatory
    scope TEXT,
    objectives TEXT,
    criteria TEXT, -- ISO 27001, NIST CSF, etc.
    start_date DATE,
    end_date DATE,
    estimated_hours DECIMAL(8,2),
    status VARCHAR(30) DEFAULT 'draft',
    -- Draft: planned, scheduled, in_progress, completed, cancelled
    lead_auditor UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE audit_team (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_plan_id UUID NOT NULL REFERENCES audit_plans(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50), -- lead_auditor, auditor, technical_expert, observer
    assigned_date DATE,
    UNIQUE(audit_plan_id, user_id)
);

CREATE TABLE audit_procedures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_plan_id UUID NOT NULL REFERENCES audit_plans(id) ON DELETE CASCADE,
    control_id UUID REFERENCES controls(id),
    requirement_id UUID REFERENCES framework_requirements(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    procedure_steps TEXT,
    testing_method VARCHAR(50), -- interview, observation, examination, technical_test
    sample_size INTEGER,
    expected_evidence TEXT,
    sort_order INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE audit_evidence_collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_plan_id UUID NOT NULL REFERENCES audit_plans(id) ON DELETE CASCADE,
    procedure_id UUID REFERENCES audit_procedures(id),
    evidence_title VARCHAR(500) NOT NULL,
    description TEXT,
    filename VARCHAR(255),
    file_path VARCHAR(500),
    evidence_type VARCHAR(50), -- document, screenshot, log, interview_notes, config
    collected_by UUID REFERENCES users(id),
    collected_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_confidential BOOLEAN DEFAULT false
);

CREATE TABLE audit_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_plan_id UUID NOT NULL REFERENCES audit_plans(id) ON DELETE CASCADE,
    procedure_id UUID REFERENCES audit_procedures(id),
    asset_id UUID REFERENCES assets(id),
    control_id UUID REFERENCES controls(id),
    
    -- Finding Details
    finding_id VARCHAR(50) UNIQUE, -- AUDIT-F-2024-0001
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    finding_type VARCHAR(50), -- non_conformity, observation, opportunity_for_improvement
    severity VARCHAR(20), -- critical, high, medium, low, informational
    likelihood VARCHAR(20), -- certain, likely, possible, unlikely, rare
    
    -- Context
    criteria_reference VARCHAR(255), -- e.g., "ISO 27001 A.9.1.2"
    root_cause TEXT,
    impact TEXT,
    recommendation TEXT,
    
    -- Management Response
    management_response TEXT,
    response_by UUID REFERENCES users(id),
    response_date DATE,
    acceptance_of_finding BOOLEAN,
    
    -- Status
    status VARCHAR(30) DEFAULT 'open', -- open, acknowledged, action_planned, verified, closed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE audit_interviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_plan_id UUID NOT NULL REFERENCES audit_plans(id) ON DELETE CASCADE,
    interviewee_name VARCHAR(255) NOT NULL,
    interviewee_title VARCHAR(255),
    interviewee_department VARCHAR(255),
    interviewer_id UUID REFERENCES users(id),
    interview_date TIMESTAMP WITH TIME ZONE,
    duration_minutes INTEGER,
    topics_covered TEXT,
    key_findings TEXT,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 5.12 Corrective Actions

```sql
CREATE TABLE corrective_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id UUID REFERENCES audit_findings(id) ON DELETE SET NULL,
    risk_item_id UUID REFERENCES risk_items(id) ON DELETE SET NULL,
    compliance_gap_id UUID REFERENCES compliance_gaps(id) ON DELETE SET NULL,
    
    -- Identification
    action_id VARCHAR(50) UNIQUE, -- CAPA-2024-0001
    title VARCHAR(500) NOT NULL,
    description TEXT,
    
    -- Root Cause
    root_cause_type VARCHAR(50), -- process, technical, human, organizational
    root_cause_description TEXT,
    impact_assessment TEXT,
    
    -- Action
    action_type VARCHAR(30), -- corrective, preventive, improvement
    priority VARCHAR(20), -- critical, high, medium, low
    status VARCHAR(30) DEFAULT 'open',
    -- Status: open, in_progress, implemented, verified, closed
    
    -- Assignment
    assigned_to UUID REFERENCES users(id),
    assigned_by UUID REFERENCES users(id),
    assigned_date DATE DEFAULT CURRENT_DATE,
    
    -- Timeline
    target_date DATE,
    extended_date DATE,
    completed_date DATE,
    
    -- Implementation
    implementation_description TEXT,
    implementation_evidence TEXT,
    
    -- Verification
    verifier UUID REFERENCES users(id),
    verification_date DATE,
    verification_result VARCHAR(30), -- effective, partially_effective, not_effective
    verification_notes TEXT,
    
    -- Closure
    closure_notes TEXT,
    is_closed BOOLEAN DEFAULT false,
    closed_by UUID REFERENCES users(id),
    closed_date DATE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE action_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corrective_action_id UUID NOT NULL REFERENCES corrective_actions(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    assigned_to UUID REFERENCES users(id),
    status VARCHAR(30) DEFAULT 'pending', -- pending, in_progress, completed
    due_date DATE,
    completed_date DATE,
    completion_notes TEXT,
    sort_order INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE effectiveness_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corrective_action_id UUID NOT NULL REFERENCES corrective_actions(id) ON DELETE CASCADE,
    review_date DATE DEFAULT CURRENT_DATE,
    reviewer UUID REFERENCES users(id),
    criteria TEXT,
    result VARCHAR(30), -- effective, partially_effective, not_effective
    findings TEXT,
    follow_up_required BOOLEAN DEFAULT false,
    follow_up_action TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 5.13 System Tables

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    body TEXT,
    notification_type VARCHAR(50), -- risk_assigned, finding_created, due_date_reminder, etc.
    reference_type VARCHAR(50), -- risk_item, finding, corrective_action
    reference_id UUID,
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE notification_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_name VARCHAR(100) NOT NULL UNIQUE,
    subject_template TEXT NOT NULL,
    body_template TEXT NOT NULL,
    channels VARCHAR(100) DEFAULT 'in_app', -- in_app, email, both
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id UUID NOT NULL REFERENCES users(id),
    reference_type VARCHAR(50) NOT NULL, -- risk_item, finding, action, asset
    reference_id UUID NOT NULL,
    parent_comment_id UUID REFERENCES comments(id),
    content TEXT NOT NULL,
    is_edited BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reference_type VARCHAR(50) NOT NULL, -- risk_item, finding, action, asset, evidence
    reference_id UUID NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    file_size INTEGER,
    uploaded_by UUID REFERENCES users(id),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(50) NOT NULL, -- create, update, delete, approve, reject
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID,
    organization_id UUID REFERENCES organizations(id),
    ip_address VARCHAR(45),
    user_agent TEXT,
    changes JSONB,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for efficient audit log queries
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);
```

---

## 6. Redesigned Backend Architecture

### 6.1 Package Structure

```
backend/
├── __init__.py
├── __main__.py                    # Entry point
├── cli.py                         # CLI entry point
│
├── api/                           # API layer
│   ├── __init__.py
│   ├── app.py                     # FastAPI application factory
│   ├── dependencies.py            # Dependency injection (auth, db, permissions)
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py                # JWT authentication middleware
│   │   ├── audit.py               # Audit log middleware
│   │   ├── cors.py                # CORS configuration
│   │   ├── rate_limit.py          # Rate limiting
│   │   └── request_id.py          # Request tracing
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py                # Login, logout, refresh, MFA
│   │   ├── users.py               # User CRUD, profile
│   │   ├── organizations.py       # Organization, site, plant management
│   │   ├── projects.py            # Project lifecycle
│   │   ├── assets.py              # Asset register, categories, dependencies
│   │   ├── zones.py               # Security zones & conduits
│   │   ├── threats.py             # Threat library & actors
│   │   ├── vulnerabilities.py     # Vulnerability registry & scans
│   │   ├── controls.py            # Control library, tests, evidence
│   │   ├── bayesian.py            # Bayesian network API
│   │   ├── risk.py                # Risk register, treatment, acceptance
│   │   ├── compliance.py          # Frameworks, mapping, gap analysis
│   │   ├── audit.py               # Audit programs, plans, execution
│   │   ├── findings.py            # Audit findings
│   │   ├── capa.py                # Corrective actions
│   │   ├── dashboards.py          # Dashboard endpoints
│   │   ├── reports.py             # Report generation & download
│   │   ├── notifications.py       # Notification management
│   │   ├── search.py              # Global search
│   │   └── admin.py               # System administration
│   ├── schemas/                   # Pydantic request/response models
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── organizations.py
│   │   ├── projects.py
│   │   ├── assets.py
│   │   ├── zones.py
│   │   ├── threats.py
│   │   ├── controls.py
│   │   ├── bayesian.py
│   │   ├── risk.py
│   │   ├── compliance.py
│   │   ├── audit.py
│   │   ├── capa.py
│   │   ├── reports.py
│   │   ├── notifications.py
│   │   └── common.py              # Pagination, sorting, filtering
│   └── responses.py               # Standardized response helpers
│
├── core/                          # Core business logic & Bayesian engine
│   ├── __init__.py
│   ├── bayesian/
│   │   ├── __init__.py
│   │   ├── engine.py              # Bayesian inference orchestrator
│   │   ├── graph_builder.py       # DAG construction from assets/zones
│   │   ├── probability.py         # Intrinsic probability computation
│   │   ├── cpt_generator.py       # Noisy-OR CPT generation
│   │   ├── inference.py           # Variable Elimination inference
│   │   ├── risk_scorer.py         # Risk computation
│   │   ├── attack_paths.py        # Attack path analysis
│   │   └── sensitivity.py         # Sensitivity analysis
│   ├── config.py                  # Constants and lookup tables
│   ├── settings.py                # Runtime-configurable settings
│   └── exceptions.py             # Domain exceptions
│
├── domain/                        # Domain models & business logic
│   ├── __init__.py
│   ├── organizations.py           # Org/site/plant service
│   ├── projects.py                # Project lifecycle service
│   ├── assets.py                  # Asset register service
│   ├── zones.py                   # Zone & conduit service
│   ├── threats.py                 # Threat management service
│   ├── vulnerabilities.py         # Vulnerability service
│   ├── controls.py                # Controls library service
│   ├── risk.py                    # Risk register service
│   ├── treatment.py               # Treatment plan service
│   ├── compliance.py              # Compliance service
│   ├── audit.py                   # Audit service
│   ├── findings.py                # Findings service
│   ├── capa.py                    # Corrective action service
│   ├── notifications.py           # Notification service
│   ├── reports.py                 # Report generation service
│   └── workflow.py                # Workflow/state machine engine
│
├── infrastructure/                # External integrations & cross-cutting
│   ├── __init__.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── config.py              # SQLAlchemy engine/session
│   │   ├── models.py              # SQLAlchemy ORM models
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Generic CRUD repository
│   │   │   ├── user_repo.py
│   │   │   ├── organization_repo.py
│   │   │   ├── project_repo.py
│   │   │   ├── asset_repo.py
│   │   │   ├── zone_repo.py
│   │   │   ├── threat_repo.py
│   │   │   ├── control_repo.py
│   │   │   ├── risk_repo.py
│   │   │   ├── compliance_repo.py
│   │   │   ├── audit_repo.py
│   │   │   ├── finding_repo.py
│   │   │   └── capa_repo.py
│   │   └── migrations/            # Alembic migrations
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── jwt.py                 # JWT token management
│   │   ├── password.py            # Password hashing
│   │   └── permissions.py         # Permission checking
│   ├── files/
│   │   ├── __init__.py
│   │   ├── storage.py             # File storage abstraction
│   │   ├── local_storage.py       # Local filesystem
│   │   └── s3_storage.py          # S3-compatible storage
│   ├── email/
│   │   ├── __init__.py
│   │   ├── sender.py              # Email sending abstraction
│   │   └── templates.py           # Email template rendering
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── pdf_generator.py       # Professional PDF generation
│   │   ├── csv_exporter.py        # CSV export
│   │   ├── xlsx_exporter.py       # Excel export
│   │   └── docx_exporter.py       # Word export
│   └── logging/
│       ├── __init__.py
│       ├── config.py              # Logging configuration
│       └── audit_logger.py        # Audit trail logging
│
└── main.py                        # FastAPI application entry point
```

### 6.2 API Design Principles

```
┌──────────────────────────────────────────────────────────────────┐
│                          API LAYER                               │
│                                                                  │
│  GET    /api/v1/resources        → List (paginated, filtered)    │
│  POST   /api/v1/resources        → Create                        │
│  GET    /api/v1/resources/{id}   → Read                          │
│  PUT    /api/v1/resources/{id}   → Full update                   │
│  PATCH  /api/v1/resources/{id}   → Partial update                │
│  DELETE /api/v1/resources/{id}   → Soft-delete                   │
│                                                                  │
│  Special actions:                                                │
│  POST   /api/v1/resources/{id}/submit    → Submit for review     │
│  POST   /api/v1/resources/{id}/approve   → Approve               │
│  POST   /api/v1/resources/{id}/reject    → Reject with reason    │
│  POST   /api/v1/resources/{id}/archive   → Archive               │
└──────────────────────────────────────────────────────────────────┘
```

### 6.3 Authentication Flow

```
Client                    API Server                    Database
  │                         │                            │
  │  POST /api/v1/auth/login│                            │
  │  {email, password}      │                            │
  │────────────────────────►│                            │
  │                         │  SELECT user WHERE email   │
  │                         │───────────────────────────►│
  │                         │◄───────────────────────────│
  │                         │                            │
  │                         │  Verify password hash      │
  │                         │  Generate Access Token     │
  │                         │  (JWT, 15min expiry)       │
  │                         │  Generate Refresh Token    │
  │                         │  (JWT, 7d expiry)          │
  │                         │                            │
  │  {access_token,         │                            │
  │   refresh_token, user}  │                            │
  │◄────────────────────────│                            │
  │                         │                            │
  │  GET /api/v1/projects   │                            │
  │  Authorization: Bearer  │                            │
  │────────────────────────►│                            │
  │                         │  Validate JWT              │
  │                         │  Load user + permissions   │
  │                         │  Execute request           │
  │  {projects}             │                            │
  │◄────────────────────────│                            │
```

### 6.4 Service Layer Patterns

```python
# Example: Asset Service Pattern
class AssetService:
    def __init__(
        self,
        asset_repo: AssetRepository,
        zone_repo: ZoneRepository,
        bayesian_engine: BayesianEngine,
        audit_logger: AuditLogger,
    ):
        self.asset_repo = asset_repo
        self.zone_repo = zone_repo
        self.bayesian_engine = bayesian_engine
        self.audit_logger = audit_logger

    def create_asset(self, data: AssetCreate, user: User) -> Asset:
        # 1. Validate business rules
        if data.asset_tag:
            existing = self.asset_repo.get_by_tag(data.asset_tag)
            if existing:
                raise BusinessError("Asset tag must be unique")

        # 2. Create asset
        asset = self.asset_repo.create(data)

        # 3. If zone specified, validate zone belongs to same plant
        if data.security_zone_id:
            zone = self.zone_repo.get_or_404(data.security_zone_id)
            if zone.plant_id != data.plant_id:
                raise BusinessError("Zone must belong to the same plant")

        # 4. Trigger Bayesian recalc if asset is part of a network
        connections = self.asset_repo.get_connections(asset.id)
        if connections:
            self.bayesian_engine.schedule_recalculation(asset.plant_id)

        # 5. Audit log
        self.audit_logger.log(
            user=user,
            action="create",
            entity_type="asset",
            entity_id=asset.id,
        )

        # 6. Notify asset owner
        if data.asset_owner_id:
            notifications.notify(
                user_id=data.asset_owner_id,
                type="asset_assigned",
                reference_type="asset",
                reference_id=asset.id,
            )

        return asset

    def recalculate_bayesian_for_asset(self, asset_id: UUID) -> dict:
        """When an asset changes, recalculate its Bayesian risk."""
        asset = self.asset_repo.get_or_404(asset_id)
        connections = self.asset_repo.get_connections(asset_id)

        # Build subgraph around this asset
        bayesian_network = self.bayesian_engine.build_network(
            assets=[asset],
            connections=connections,
        )
        result = self.bayesian_engine.run_inference(bayesian_network)

        # Update risk register items linked to this asset
        risk_items = self.risk_repo.get_by_asset(asset_id)
        for risk_item in risk_items:
            risk_item.bayesian_likelihood = result.posterior
            risk_item.bayesian_risk_score = result.risk_score
            risk_item.bayesian_risk_level = result.risk_level
            self.risk_repo.update(risk_item)

        return result
```

---

## 7. Redesigned Frontend Architecture

### 7.1 Technology Stack

```
Framework:   React 18 + TypeScript (strict mode)
Build Tool:  Vite 5
Routing:     React Router v6 (with nested layouts)
State:       Zustand (global) + React Query/TanStack Query (server state)
UI:          Tailwind CSS 3 + Headless UI + Radix UI Primitives
Charts:      Recharts + D3.js (heat maps)
Flow:        ReactFlow (network topology)
Forms:       React Hook Form + Zod validation
Tables:      TanStack Table v8 (virtualized, filterable, sortable)
i18n:        react-i18next
PDF:         @react-pdf/renderer (client-side preview)
Testing:     Vitest + React Testing Library + Playwright
```

### 7.2 Component Architecture

```
frontend/src/
├── main.tsx                          # Entry point
├── App.tsx                           # Root component with providers
│
├── routes/                           # Route definitions
│   ├── index.tsx                     # Route configuration
│   ├── ProtectedRoute.tsx            # Auth guard
│   └── RoleRoute.tsx                 # Role-based guard
│
├── layouts/
│   ├── RootLayout.tsx                # Main app shell
│   ├── DashboardLayout.tsx           # Dashboard grid layout
│   ├── WorkspaceLayout.tsx           # Sidebar + main content
│   └── AuthLayout.tsx               # Login/register layout
│
├── pages/                            # Page components (one per route)
│   ├── auth/
│   │   ├── LoginPage.tsx
│   │   ├── LogoutPage.tsx
│   │   └── MFAPage.tsx
│   ├── dashboard/
│   │   ├── ExecutiveDashboard.tsx
│   │   ├── RiskManagerDashboard.tsx
│   │   ├── ComplianceDashboard.tsx
│   │   ├── AuditDashboard.tsx
│   │   ├── ICSDashboard.tsx
│   │   └── AnalystDashboard.tsx
│   ├── projects/
│   │   ├── ProjectListPage.tsx
│   │   ├── ProjectDetailPage.tsx
│   │   └── ProjectCreatePage.tsx
│   ├── assets/
│   │   ├── AssetRegisterPage.tsx
│   │   ├── AssetDetailPage.tsx
│   │   ├── AssetCreatePage.tsx
│   │   ├── ZonesPage.tsx
│   │   └── ConduitsPage.tsx
│   ├── threats/
│   │   ├── ThreatLibraryPage.tsx
│   │   ├── ThreatDetailPage.tsx
│   │   └── VulnerabilityPage.tsx
│   ├── controls/
│   │   ├── ControlLibraryPage.tsx
│   │   ├── ControlDetailPage.tsx
│   │   └── ControlTestPage.tsx
│   ├── risk/
│   │   ├── RiskRegisterPage.tsx
│   │   ├── RiskDetailPage.tsx
│   │   ├── RiskMatrixPage.tsx
│   │   ├── HeatMapPage.tsx
│   │   ├── BayesianAnalysisPage.tsx
│   │   ├── RiskTreatmentPage.tsx
│   │   └── RiskAcceptancePage.tsx
│   ├── compliance/
│   │   ├── FrameworkListPage.tsx
│   │   ├── FrameworkDetailPage.tsx
│   │   ├── ControlMappingPage.tsx
│   │   └── GapAnalysisPage.tsx
│   ├── audit/
│   │   ├── AuditProgramPage.tsx
│   │   ├── AuditPlanPage.tsx
│   │   ├── AuditExecutionPage.tsx
│   │   ├── AuditFindingsPage.tsx
│   │   └── AuditEvidencePage.tsx
│   ├── capa/
│   │   ├── CorrectiveActionListPage.tsx
│   │   ├── CorrectiveActionDetailPage.tsx
│   │   └── EffectivenessReviewPage.tsx
│   ├── reports/
│   │   ├── ReportCenterPage.tsx
│   │   ├── ReportViewerPage.tsx
│   │   └── ReportSchedulerPage.tsx
│   └── admin/
│       ├── UserManagementPage.tsx
│       ├── RoleManagementPage.tsx
│       ├── SystemSettingsPage.tsx
│       └── AuditLogPage.tsx
│
├── components/                       # Shared components
│   ├── ui/                           # Design system primitives
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Badge.tsx
│   │   ├── Modal.tsx
│   │   ├── Table.tsx
│   │   ├── FormField.tsx
│   │   ├── Select.tsx
│   │   ├── DatePicker.tsx
│   │   ├── FileUpload.tsx
│   │   ├── SearchInput.tsx
│   │   ├── Pagination.tsx
│   │   ├── Breadcrumbs.tsx
│   │   ├── Tabs.tsx
│   │   ├── SplitPanel.tsx
│   │   ├── Toast.tsx
│   │   └── Spinner.tsx
│   │
│   ├── layout/                       # Layout components
│   │   ├── Sidebar.tsx
│   │   ├── TopNav.tsx
│   │   ├── Footer.tsx
│   │   └── BreadcrumbTrail.tsx
│   │
│   ├── dashboard/                    # Dashboard widgets
│   │   ├── RiskWidget.tsx
│   │   ├── ComplianceWidget.tsx
│   │   ├── AuditWidget.tsx
│   │   ├── CAPAWidget.tsx
│   │   ├── BayesianStatusWidget.tsx
│   │   ├── RiskTrendChart.tsx
│   │   └── RecentFindingsList.tsx
│   │
│   ├── asset/                        # Asset components
│   │   ├── AssetTable.tsx
│   │   ├── AssetForm.tsx
│   │   ├── AssetDetail.tsx
│   │   ├── AssetClassification.tsx
│   │   ├── AssetDependencyGraph.tsx
│   │   └── ZoneMap.tsx
│   │
│   ├── risk/                         # Risk components
│   │   ├── RiskTable.tsx
│   │   ├── RiskMatrix.tsx
│   │   ├── HeatMap.tsx
│   │   ├── RiskDetail.tsx
│   │   ├── RiskTreatmentForm.tsx
│   │   ├── RiskAcceptanceForm.tsx
│   │   └── RiskHistory.tsx
│   │
│   ├── bayesian/                     # Bayesian components
│   │   ├── NetworkViewer.tsx         # Extended from current
│   │   ├── EvidencePanel.tsx         # Extended from current
│   │   ├── BayesianResults.tsx       # Extended from current
│   │   ├── CptSection.tsx            # Extended from current
│   │   ├── SensitivityAnalysis.tsx
│   │   ├── WhatIfScenarios.tsx
│   │   └── ProbabilityChart.tsx      # Extended from current
│   │
│   ├── compliance/                   # Compliance components
│   │   ├── FrameworkSelector.tsx
│   │   ├── ControlMappingTable.tsx
│   │   ├── ComplianceGauge.tsx
│   │   ├── GapAnalysisTable.tsx
│   │   └── ComplianceScoreCard.tsx
│   │
│   ├── audit/                        # Audit components
│   │   ├── AuditPlanForm.tsx
│   │   ├── ProcedureChecklist.tsx
│   │   ├── EvidenceCollector.tsx
│   │   ├── FindingForm.tsx
│   │   └── AuditTrail.tsx
│   │
│   ├── capa/                         # CAPA components
│   │   ├── CAPAForm.tsx
│   │   ├── ActionTaskList.tsx
│   │   └── EffectivenessReview.tsx
│   │
│   ├── reporting/                    # Reporting components
│   │   ├── ReportViewer.tsx
│   │   ├── ExportMenu.tsx
│   │   ├── PDFPreview.tsx
│   │   └── ScheduleForm.tsx
│   │
│   └── common/                       # Common components
│       ├── PageHeader.tsx
│       ├── StatusBadge.tsx
│       ├── ConfirmDialog.tsx
│       ├── EmptyState.tsx
│       ├── ErrorBoundary.tsx
│       ├── LoadingSkeleton.tsx
│       └── UserAvatar.tsx
│
├── hooks/                            # Custom hooks
│   ├── useAuth.ts
│   ├── usePermissions.ts
│   ├── usePagination.ts
│   ├── useDebounce.ts
│   ├── useLocalStorage.ts
│   └── useWebSocket.ts              # Real-time notifications
│
├── stores/                           # Zustand stores
│   ├── authStore.ts
│   ├── projectStore.ts
│   ├── uiStore.ts                   # Sidebar, theme, preferences
│   └── notificationStore.ts
│
├── services/                         # API client
│   ├── api.ts                        # Axios instance with interceptors
│   ├── authService.ts
│   ├── projectService.ts
│   ├── assetService.ts
│   ├── riskService.ts
│   ├── complianceService.ts
│   ├── auditService.ts
│   ├── capaService.ts
│   ├── bayesianService.ts
│   └── reportService.ts
│
├── types/                            # TypeScript type definitions
│   ├── index.ts
│   ├── auth.ts
│   ├── project.ts
│   ├── asset.ts
│   ├── risk.ts
│   ├── compliance.ts
│   ├── audit.ts
│   ├── capa.ts
│   ├── bayesian.ts
│   ├── report.ts
│   └── common.ts
│
├── utils/                            # Utility functions
│   ├── formatters.ts                 # Date, currency, percentage
│   ├── validators.ts                 # Form validation
│   ├── permissions.ts                # Permission helpers
│   ├── export.ts                     # Client-side export
│   └── constants.ts
│
├── styles/                           # Global styles
│   ├── globals.css                   # Tailwind imports + base
│   ├── dark-mode.css
│   ├── risk-matrix.css
│   └── print.css
│
└── assets/                           # Static assets
    ├── icons/
    ├── logos/
    └── illustrations/
```

### 7.3 Routing Structure

```typescript
const routes = [
  {
    path: '/login',
    element: <AuthLayout />,
    children: [
      { path: '', element: <LoginPage /> },
      { path: 'mfa', element: <MFAPage /> },
    ],
  },
  {
    path: '/',
    element: <ProtectedRoute><RootLayout /></ProtectedRoute>,
    children: [
      // Redirect
      { index: true, element: <Navigate to="/dashboard" /> },

      // Dashboards
      {
        path: 'dashboard',
        element: <DashboardLayout />,
        children
