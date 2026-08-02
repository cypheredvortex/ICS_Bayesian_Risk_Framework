# Phase 2 Implementation Plan: Threat, Vulnerability, Control & Risk Management

## Overview
Build the core GRC modules on top of the Phase 1 foundation (Organization hierarchy, Users/Auth, Zones/Conduits, Extended Assets, Audit Trail).

## Proposed Implementation Order

### Phase 2a: Threat & Vulnerability Management (Week 1)
- **Threat Library**: Threat categories, threats, threat actors
- **Vulnerability Registry**: CVE-based vulnerabilities with CVSS scoring
- **Asset-Vulnerability Mapping**: Link vulnerabilities to assets
- **Models** in `backend/database/models.py`
- **Schemas** in `backend/schemas.py`
- **Repositories** in `backend/database/repositories.py`
- **Routers** in `backend/routers/threats.py` and `backend/routers/vulnerabilities.py`
- **Alembic Migration** for new tables

### Phase 2b: Control Library (Week 2)
- **Control Categories**: Preventive, detective, corrective, deterrent
- **Control Library**: Full CRUD with implementation status, effectiveness
- **Control Testing**: Test procedures and results
- **Control Evidence**: Document evidence collection
- **Alembic Migration**

### Phase 2c: Risk Register & Treatment (Week 2-3)
- **Risk Register**: Risk items with inherent/residual risk
- **Risk Scenarios**: Scenario modeling linked to Bayesian
- **Risk Treatment Plans**: Mitigate, transfer, accept, avoid
- **Risk Acceptance**: Formal acceptance workflow
- **Risk History**: Full audit trail for risk changes
- **Bayesian Integration**: Link risk results to risk register
- **Alembic Migration**

### Phase 2d: Compliance Framework & Audit Findings (Week 3-4)
- **Compliance Frameworks**: ISO 27001, NIST CSF, IEC 62443, CIS
- **Framework Requirements**: Individual requirements per framework
- **Control Mapping**: Map controls to framework requirements
- **Compliance Gaps**: Gap analysis entities
- **Audit Findings**: Finding entity with severity, recommendations
- **Management Response**: Response workflow
- **Alembic Migration**

### Phase 2e: Corrective Actions (CAPA) (Week 4)
- **Corrective Actions**: Full CAPA workflow
- **Action Tasks**: Sub-tasks with assignment
- **Effectiveness Reviews**: Verify closure effectiveness
- **Alembic Migration**

## Files to Create/Modify

### New Backend Router Files:
1. `backend/routers/threats.py` - Threat library endpoints
2. `backend/routers/vulnerabilities.py` - Vulnerability registry endpoints
3. `backend/routers/controls.py` - Control library endpoints
4. `backend/routers/risk.py` - Risk register & treatment endpoints
5. `backend/routers/compliance.py` - Compliance framework endpoints
6. `backend/routers/findings.py` - Audit finding endpoints
7. `backend/routers/capa.py` - Corrective action endpoints

### Modified Files:
1. `backend/database/models.py` - Add ~25 new ORM models
2. `backend/schemas.py` - Add ~40 Pydantic schemas
3. `backend/database/repositories.py` - Add ~15 new repositories
4. `backend/api.py` - Register new routers
5. `alembic/versions/` - New migration
6. `TODO.md` - Update progress

## Database Tables to Add (per ARCHITECTURAL_REVIEW.md)
- threat_categories, threats, threat_actors
- vulnerabilities, asset_vulnerabilities
- control_categories, controls, control_tests, control_evidence
- risk_items, risk_scenarios, risk_treatment_plans, risk_acceptances, risk_history
- compliance_frameworks, framework_requirements, control_mappings, compliance_gaps, compliance_assessments
- audit_findings, audit_evidence_collections, audit_interviews
- corrective_actions, action_tasks, effectiveness_reviews

