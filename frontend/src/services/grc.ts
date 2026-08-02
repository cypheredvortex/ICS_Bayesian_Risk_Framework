// ═══════════════════════════════════════════════════════════════
// GRC & Audit Platform — API client
// Typed wrapper around the FastAPI GRC routers with full CRUD support
// and automatic Bearer token injection.
// ═══════════════════════════════════════════════════════════════

import { API_BASE_URL } from '../constants'
import type {
  ActionTask,
  Asset,
  AssetCategory,
  AssetVulnerability,
  AuditEvidence,
  AuditFinding,
  AuditInterview,
  AuditLogEntry,
  AuditPlan,
  AuditProcedure,
  AuditProgram,
  ComplianceAssessment,
  ComplianceFramework,
  ComplianceGap,
  Conduit,
  Control,
  ControlCategory,
  ControlEvidence,
  ControlMapping,
  ControlTest,
  CorrectiveAction,
  DashboardSummary,
  EffectivenessReview,
  FrameworkRequirement,
  Organization,
  Plant,
  RiskAcceptance,
  RiskHistory,
  RiskItem,
  RiskScenario,
  RiskTreatmentPlan,
  Role,
  SecurityZone,
  Site,
  Threat,
  ThreatActor,
  ThreatCategory,
  User,
  Vulnerability,
} from '../types/grc'
import { parseErrorDetail } from '../utils'

// ── Auth header singleton ───────────────────────────────────────
// The AuthProvider calls setAuthHeader(token) after login/restore so
// every request automatically carries the Bearer token.

let authHeaderValue: Record<string, string> = {}

export function setAuthHeader(header: Record<string, string>): void {
  authHeaderValue = header
}

export function getAuthHeader(): Record<string, string> {
  return authHeaderValue
}

// ── Core request helpers ────────────────────────────────────────

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    ...authHeaderValue,
    ...(init?.headers as Record<string, string> | undefined),
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  })
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response, `Request to ${path} failed.`))
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

function json(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

// ── Auth ────────────────────────────────────────────────────────

export const authApi = {
  login: (username: string, password: string) =>
    request<{ access_token: string; token_type: string; expires_in: number; user: User }>(
      '/api/v1/auth/login',
      json('POST', { username, password }),
    ),
  me: () => request<{ user: User } & Record<string, unknown>>('/api/v1/auth/me'),
  logout: () => request<{ message: string }>('/api/v1/auth/logout', json('POST', {})),
  changePassword: (payload: { current_password: string; new_password: string }) =>
    request<{ message: string }>(
      '/api/v1/auth/users/me/change-password',
      json('POST', payload),
    ),
}

// ── Organizations / Hierarchy ───────────────────────────────────

export const organizationApi = {
  list: () => request<Organization[]>('/api/v1/organizations/'),
  create: (payload: Partial<Organization>) =>
    request<Organization>('/api/v1/organizations/', json('POST', payload)),
  get: (id: number) => request<Organization>(`/api/v1/organizations/${id}`),
  update: (id: number, payload: Partial<Organization>) =>
    request<Organization>(`/api/v1/organizations/${id}`, json('PUT', payload)),
  remove: (id: number) =>
    request<void>(`/api/v1/organizations/${id}`, { method: 'DELETE' }),
  sites: (orgId: number) => request<Site[]>(`/api/v1/organizations/${orgId}/sites`),
  createSite: (orgId: number, payload: Partial<Site>) =>
    request<Site>(`/api/v1/organizations/${orgId}/sites`, json('POST', payload)),
  getSite: (siteId: number) => request<Site>(`/api/v1/organizations/sites/${siteId}`),
  updateSite: (siteId: number, payload: Partial<Site>) =>
    request<Site>(`/api/v1/organizations/sites/${siteId}`, json('PUT', payload)),
  plants: (siteId: number) => request<Plant[]>(`/api/v1/organizations/sites/${siteId}/plants`),
  createPlant: (siteId: number, payload: Partial<Plant>) =>
    request<Plant>(`/api/v1/organizations/sites/${siteId}/plants`, json('POST', payload)),
  getPlant: (plantId: number) => request<Plant>(`/api/v1/organizations/plants/${plantId}`),
  updatePlant: (plantId: number, payload: Partial<Plant>) =>
    request<Plant>(`/api/v1/organizations/plants/${plantId}`, json('PUT', payload)),
}

// ── Roles / Users ───────────────────────────────────────────────

export const adminApi = {
  listRoles: () => request<Role[]>('/api/v1/auth/roles'),
  createRole: (payload: Partial<Role>) =>
    request<Role>('/api/v1/auth/roles', json('POST', payload)),
  listUsers: () => request<User[]>('/api/v1/auth/users'),
  getUser: (userId: number) => request<User>(`/api/v1/auth/users/${userId}`),
  createUser: (payload: Partial<User> & { password: string }) =>
    request<User>('/api/v1/auth/users', json('POST', payload)),
  updateUser: (userId: number, payload: Partial<User>) =>
    request<User>(`/api/v1/auth/users/${userId}`, json('PUT', payload)),
  changeUserPassword: (userId: number, payload: { new_password: string }) =>
    request<{ message: string }>(
      `/api/v1/auth/users/${userId}/change-password`,
      json('POST', payload),
    ),
  listOrganizations: () => organizationApi.list(),
  listAuditLogs: (limit = 100) =>
    request<{ total: number; logs: AuditLogEntry[] }>(`/api/v1/audit-logs/?limit=${limit}`),
}

// ── Zones / Conduits ────────────────────────────────────────────

export const zoneApi = {
  zonesForPlant: (plantId: number) =>
    request<SecurityZone[]>(`/api/v1/zones/plants/${plantId}/zones`),
  createZone: (plantId: number, payload: Partial<SecurityZone>) =>
    request<SecurityZone>(`/api/v1/zones/plants/${plantId}/zones`, json('POST', payload)),
  getZone: (zoneId: number) => request<SecurityZone>(`/api/v1/zones/zones/${zoneId}`),
  updateZone: (zoneId: number, payload: Partial<SecurityZone>) =>
    request<SecurityZone>(`/api/v1/zones/zones/${zoneId}`, json('PUT', payload)),
  removeZone: (zoneId: number) =>
    request<void>(`/api/v1/zones/zones/${zoneId}`, { method: 'DELETE' }),
  conduitsForPlant: (plantId: number) =>
    request<Conduit[]>(`/api/v1/zones/plants/${plantId}/conduits`),
  createConduit: (plantId: number, payload: Partial<Conduit>) =>
    request<Conduit>(`/api/v1/zones/plants/${plantId}/conduits`, json('POST', payload)),
  getConduit: (conduitId: number) => request<Conduit>(`/api/v1/zones/conduits/${conduitId}`),
  removeConduit: (conduitId: number) =>
    request<void>(`/api/v1/zones/conduits/${conduitId}`, { method: 'DELETE' }),
}

// ── Assets ──────────────────────────────────────────────────────

export const assetApi = {
  list: () => request<Asset[]>('/api/v1/assets/'),
  listByPlant: (plantId: number) => request<Asset[]>(`/api/v1/assets/?plant_id=${plantId}`),
  listByOrg: (orgId: number) => request<Asset[]>(`/api/v1/assets/?organization_id=${orgId}`),
  create: (payload: Partial<Asset>) =>
    request<Asset>('/api/v1/assets/', json('POST', payload)),
  get: (id: number) => request<Asset>(`/api/v1/assets/${id}`),
  update: (id: number, payload: Partial<Asset>) =>
    request<Asset>(`/api/v1/assets/${id}`, json('PUT', payload)),
  remove: (id: number) => request<void>(`/api/v1/assets/${id}`, { method: 'DELETE' }),
  categories: () => request<AssetCategory[]>('/api/v1/assets/categories'),
  createCategory: (payload: Partial<AssetCategory>) =>
    request<AssetCategory>('/api/v1/assets/categories', json('POST', payload)),
}

// ── Threats ─────────────────────────────────────────────────────

export const threatApi = {
  categories: () => request<ThreatCategory[]>('/api/v1/threats/categories'),
  createCategory: (payload: Partial<ThreatCategory>) =>
    request<ThreatCategory>('/api/v1/threats/categories', json('POST', payload)),
  getCategory: (id: number) => request<ThreatCategory>(`/api/v1/threats/categories/${id}`),
  removeCategory: (id: number) =>
    request<void>(`/api/v1/threats/categories/${id}`, { method: 'DELETE' }),
  list: () => request<Threat[]>('/api/v1/threats/'),
  create: (payload: Partial<Threat>) =>
    request<Threat>('/api/v1/threats/', json('POST', payload)),
  get: (id: number) => request<Threat>(`/api/v1/threats/${id}`),
  update: (id: number, payload: Partial<Threat>) =>
    request<Threat>(`/api/v1/threats/${id}`, json('PUT', payload)),
  remove: (id: number) => request<void>(`/api/v1/threats/${id}`, { method: 'DELETE' }),
  actors: () => request<ThreatActor[]>('/api/v1/threats/actors'),
  createActor: (payload: Partial<ThreatActor>) =>
    request<ThreatActor>('/api/v1/threats/actors', json('POST', payload)),
  getActor: (id: number) => request<ThreatActor>(`/api/v1/threats/actors/${id}`),
  updateActor: (id: number, payload: Partial<ThreatActor>) =>
    request<ThreatActor>(`/api/v1/threats/actors/${id}`, json('PUT', payload)),
  removeActor: (id: number) =>
    request<void>(`/api/v1/threats/actors/${id}`, { method: 'DELETE' }),
}

// ── Vulnerabilities ─────────────────────────────────────────────

export const vulnerabilityApi = {
  list: () => request<Vulnerability[]>('/api/v1/vulnerabilities/'),
  create: (payload: Partial<Vulnerability>) =>
    request<Vulnerability>('/api/v1/vulnerabilities/', json('POST', payload)),
  get: (id: number) => request<Vulnerability>(`/api/v1/vulnerabilities/${id}`),
  update: (id: number, payload: Partial<Vulnerability>) =>
    request<Vulnerability>(`/api/v1/vulnerabilities/${id}`, json('PUT', payload)),
  remove: (id: number) =>
    request<void>(`/api/v1/vulnerabilities/${id}`, { method: 'DELETE' }),
  bySeverity: (severity: string) =>
    request<Vulnerability[]>(`/api/v1/vulnerabilities/?severity=${severity}`),
  forAsset: (assetId: number) =>
    request<AssetVulnerability[]>(`/api/v1/vulnerabilities/by-asset/${assetId}`),
  link: (payload: { asset_id: number; vulnerability_id: number; status?: string }) =>
    request<AssetVulnerability>('/api/v1/vulnerabilities/link', json('POST', payload)),
  updateLink: (linkId: number, payload: Partial<AssetVulnerability>) =>
    request<AssetVulnerability>(`/api/v1/vulnerabilities/link/${linkId}`, json('PUT', payload)),
  unlink: (linkId: number) =>
    request<void>(`/api/v1/vulnerabilities/link/${linkId}`, { method: 'DELETE' }),
}

// ── Controls ────────────────────────────────────────────────────

export const controlApi = {
  categories: () => request<ControlCategory[]>('/api/v1/controls/categories'),
  createCategory: (payload: Partial<ControlCategory>) =>
    request<ControlCategory>('/api/v1/controls/categories', json('POST', payload)),
  getCategory: (id: number) => request<ControlCategory>(`/api/v1/controls/categories/${id}`),
  removeCategory: (id: number) =>
    request<void>(`/api/v1/controls/categories/${id}`, { method: 'DELETE' }),
  list: () => request<Control[]>('/api/v1/controls/'),
  create: (payload: Partial<Control>) =>
    request<Control>('/api/v1/controls/', json('POST', payload)),
  get: (id: number) => request<Control>(`/api/v1/controls/${id}`),
  update: (id: number, payload: Partial<Control>) =>
    request<Control>(`/api/v1/controls/${id}`, json('PUT', payload)),
  remove: (id: number) => request<void>(`/api/v1/controls/${id}`, { method: 'DELETE' }),
  tests: (controlId: number) =>
    request<ControlTest[]>(`/api/v1/controls/${controlId}/tests`),
  createTest: (payload: Partial<ControlTest>) =>
    request<ControlTest>('/api/v1/controls/tests', json('POST', payload)),
  updateTest: (testId: number, payload: Partial<ControlTest>) =>
    request<ControlTest>(`/api/v1/controls/tests/${testId}`, json('PUT', payload)),
  removeTest: (testId: number) =>
    request<void>(`/api/v1/controls/tests/${testId}`, { method: 'DELETE' }),
  evidence: (controlId: number) =>
    request<ControlEvidence[]>(`/api/v1/controls/${controlId}/evidence`),
  createEvidence: (payload: Partial<ControlEvidence>) =>
    request<ControlEvidence>('/api/v1/controls/evidence', json('POST', payload)),
  removeEvidence: (evidenceId: number) =>
    request<void>(`/api/v1/controls/evidence/${evidenceId}`, { method: 'DELETE' }),
}

// ── Risk Register ───────────────────────────────────────────────

export const riskApi = {
  list: () => request<RiskItem[]>('/api/v1/risk/items'),
  create: (payload: Partial<RiskItem>) =>
    request<RiskItem>('/api/v1/risk/items', json('POST', payload)),
  get: (id: number) => request<RiskItem>(`/api/v1/risk/items/${id}`),
  update: (id: number, payload: Partial<RiskItem>) =>
    request<RiskItem>(`/api/v1/risk/items/${id}`, json('PUT', payload)),
  remove: (id: number) => request<void>(`/api/v1/risk/items/${id}`, { method: 'DELETE' }),
  scenarios: (riskItemId: number) =>
    request<RiskScenario[]>(`/api/v1/risk/items/${riskItemId}/scenarios`),
  createScenario: (payload: Partial<RiskScenario>) =>
    request<RiskScenario>('/api/v1/risk/scenarios', json('POST', payload)),
  treatmentPlans: (riskItemId: number) =>
    request<RiskTreatmentPlan[]>(`/api/v1/risk/items/${riskItemId}/treatment-plans`),
  createTreatmentPlan: (payload: Partial<RiskTreatmentPlan>) =>
    request<RiskTreatmentPlan>('/api/v1/risk/treatment-plans', json('POST', payload)),
  updateTreatmentPlan: (planId: number, payload: Partial<RiskTreatmentPlan>) =>
    request<RiskTreatmentPlan>(`/api/v1/risk/treatment-plans/${planId}`, json('PUT', payload)),
  removeTreatmentPlan: (planId: number) =>
    request<void>(`/api/v1/risk/treatment-plans/${planId}`, { method: 'DELETE' }),
  acceptances: (riskItemId: number) =>
    request<RiskAcceptance[]>(`/api/v1/risk/items/${riskItemId}/acceptances`),
  createAcceptance: (payload: Partial<RiskAcceptance>) =>
    request<RiskAcceptance>('/api/v1/risk/acceptances', json('POST', payload)),
  removeAcceptance: (acceptanceId: number) =>
    request<void>(`/api/v1/risk/acceptances/${acceptanceId}`, { method: 'DELETE' }),
  history: (riskItemId: number) =>
    request<RiskHistory[]>(`/api/v1/risk/items/${riskItemId}/history`),
}

// ── Compliance ──────────────────────────────────────────────────

export const complianceApi = {
  frameworks: () => request<ComplianceFramework[]>('/api/v1/compliance/frameworks'),
  createFramework: (payload: Partial<ComplianceFramework>) =>
    request<ComplianceFramework>('/api/v1/compliance/frameworks', json('POST', payload)),
  getFramework: (id: number) =>
    request<ComplianceFramework>(`/api/v1/compliance/frameworks/${id}`),
  removeFramework: (id: number) =>
    request<void>(`/api/v1/compliance/frameworks/${id}`, { method: 'DELETE' }),
  requirements: (frameworkId: number) =>
    request<FrameworkRequirement[]>(`/api/v1/compliance/frameworks/${frameworkId}/requirements`),
  createRequirement: (payload: Partial<FrameworkRequirement>) =>
    request<FrameworkRequirement>('/api/v1/compliance/requirements', json('POST', payload)),
  getRequirement: (id: number) =>
    request<FrameworkRequirement>(`/api/v1/compliance/requirements/${id}`),
  removeRequirement: (id: number) =>
    request<void>(`/api/v1/compliance/requirements/${id}`, { method: 'DELETE' }),
  mappings: () => request<ControlMapping[]>('/api/v1/compliance/mappings'),
  createMapping: (payload: Partial<ControlMapping>) =>
    request<ControlMapping>('/api/v1/compliance/mappings', json('POST', payload)),
  removeMapping: (id: number) =>
    request<void>(`/api/v1/compliance/mappings/${id}`, { method: 'DELETE' }),
  gaps: () => request<ComplianceGap[]>('/api/v1/compliance/gaps'),
  createGap: (payload: Partial<ComplianceGap>) =>
    request<ComplianceGap>('/api/v1/compliance/gaps', json('POST', payload)),
  updateGap: (id: number, payload: Partial<ComplianceGap>) =>
    request<ComplianceGap>(`/api/v1/compliance/gaps/${id}`, json('PUT', payload)),
  removeGap: (id: number) =>
    request<void>(`/api/v1/compliance/gaps/${id}`, { method: 'DELETE' }),
  assessments: () => request<ComplianceAssessment[]>('/api/v1/compliance/assessments'),
  createAssessment: (payload: Partial<ComplianceAssessment>) =>
    request<ComplianceAssessment>('/api/v1/compliance/assessments', json('POST', payload)),
  getAssessment: (id: number) =>
    request<ComplianceAssessment>(`/api/v1/compliance/assessments/${id}`),
}

// ── Audit Management ────────────────────────────────────────────

export const auditApi = {
  programs: () => request<AuditProgram[]>('/api/v1/audit/programs'),
  createProgram: (payload: Partial<AuditProgram>) =>
    request<AuditProgram>('/api/v1/audit/programs', json('POST', payload)),
  getProgram: (id: number) => request<AuditProgram>(`/api/v1/audit/programs/${id}`),
  updateProgram: (id: number, payload: Partial<AuditProgram>) =>
    request<AuditProgram>(`/api/v1/audit/programs/${id}`, json('PUT', payload)),
  removeProgram: (id: number) =>
    request<void>(`/api/v1/audit/programs/${id}`, { method: 'DELETE' }),
  plans: () => request<AuditPlan[]>('/api/v1/audit/plans'),
  createPlan: (payload: Partial<AuditPlan>) =>
    request<AuditPlan>('/api/v1/audit/plans', json('POST', payload)),
  getPlan: (id: number) => request<AuditPlan>(`/api/v1/audit/plans/${id}`),
  updatePlan: (id: number, payload: Partial<AuditPlan>) =>
    request<AuditPlan>(`/api/v1/audit/plans/${id}`, json('PUT', payload)),
  removePlan: (id: number) => request<void>(`/api/v1/audit/plans/${id}`, { method: 'DELETE' }),
  procedures: (planId: number) =>
    request<AuditProcedure[]>(`/api/v1/audit/plans/${planId}/procedures`),
  createProcedure: (payload: Partial<AuditProcedure>) =>
    request<AuditProcedure>('/api/v1/audit/procedures', json('POST', payload)),
  getProcedure: (id: number) => request<AuditProcedure>(`/api/v1/audit/procedures/${id}`),
  removeProcedure: (id: number) =>
    request<void>(`/api/v1/audit/procedures/${id}`, { method: 'DELETE' }),
  findings: () => request<AuditFinding[]>('/api/v1/audit/findings'),
  createFinding: (payload: Partial<AuditFinding>) =>
    request<AuditFinding>('/api/v1/audit/findings', json('POST', payload)),
  getFinding: (id: number) => request<AuditFinding>(`/api/v1/audit/findings/${id}`),
  updateFinding: (id: number, payload: Partial<AuditFinding>) =>
    request<AuditFinding>(`/api/v1/audit/findings/${id}`, json('PUT', payload)),
  removeFinding: (id: number) =>
    request<void>(`/api/v1/audit/findings/${id}`, { method: 'DELETE' }),
  evidence: () => request<AuditEvidence[]>('/api/v1/audit/evidence'),
  createEvidence: (payload: Partial<AuditEvidence>) =>
    request<AuditEvidence>('/api/v1/audit/evidence', json('POST', payload)),
  getEvidence: (id: number) => request<AuditEvidence>(`/api/v1/audit/evidence/${id}`),
  removeEvidence: (id: number) =>
    request<void>(`/api/v1/audit/evidence/${id}`, { method: 'DELETE' }),
  interviews: () => request<AuditInterview[]>('/api/v1/audit/interviews'),
  createInterview: (payload: Partial<AuditInterview>) =>
    request<AuditInterview>('/api/v1/audit/interviews', json('POST', payload)),
  getInterview: (id: number) => request<AuditInterview>(`/api/v1/audit/interviews/${id}`),
  removeInterview: (id: number) =>
    request<void>(`/api/v1/audit/interviews/${id}`, { method: 'DELETE' }),
}

// ── Corrective Actions (CAPA) ───────────────────────────────────

export const capaApi = {
  list: () => request<CorrectiveAction[]>('/api/v1/capa/actions'),
  create: (payload: Partial<CorrectiveAction>) =>
    request<CorrectiveAction>('/api/v1/capa/actions', json('POST', payload)),
  get: (id: number) => request<CorrectiveAction>(`/api/v1/capa/actions/${id}`),
  update: (id: number, payload: Partial<CorrectiveAction>) =>
    request<CorrectiveAction>(`/api/v1/capa/actions/${id}`, json('PUT', payload)),
  close: (id: number, closure_notes?: string) =>
    request<CorrectiveAction>(
      `/api/v1/capa/actions/${id}/close${closure_notes ? `?closure_notes=${encodeURIComponent(closure_notes)}` : ''}`,
      { method: 'POST' },
    ),
  tasks: (actionId: number) =>
    request<ActionTask[]>(`/api/v1/capa/actions/${actionId}/tasks`),
  createTask: (payload: Partial<ActionTask>) =>
    request<ActionTask>('/api/v1/capa/tasks', json('POST', payload)),
  updateTask: (taskId: number, payload: Partial<ActionTask>) =>
    request<ActionTask>(`/api/v1/capa/tasks/${taskId}`, json('PUT', payload)),
  reviews: (actionId: number) =>
    request<EffectivenessReview[]>(`/api/v1/capa/actions/${actionId}/reviews`),
  createReview: (payload: Partial<EffectivenessReview>) =>
    request<EffectivenessReview>('/api/v1/capa/reviews', json('POST', payload)),
}

// ── Dashboard ───────────────────────────────────────────────────

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const [organizations, assets, threats, vulnerabilities, controls, riskItems, frameworks, auditPlans, findings, actions] =
    await Promise.all([
      organizationApi.list().catch(() => [] as Organization[]),
      assetApi.list().catch(() => [] as Asset[]),
      threatApi.list().catch(() => [] as Threat[]),
      vulnerabilityApi.list().catch(() => [] as Vulnerability[]),
      controlApi.list().catch(() => [] as Control[]),
      riskApi.list().catch(() => [] as RiskItem[]),
      complianceApi.frameworks().catch(() => [] as ComplianceFramework[]),
      auditApi.plans().catch(() => [] as AuditPlan[]),
      auditApi.findings().catch(() => [] as AuditFinding[]),
      capaApi.list().catch(() => [] as CorrectiveAction[]),
    ])

  return {
    organizations: organizations.length,
    sites: 0,
    plants: 0,
    assets: assets.length,
    threats: threats.length,
    vulnerabilities: vulnerabilities.length,
    controls: controls.length,
    risk_items: riskItems.length,
    open_risks: riskItems.filter((r) => r.status && r.status !== 'closed').length,
    frameworks: frameworks.length,
    audit_plans: auditPlans.length,
    open_findings: findings.filter((f) =>
      ['open', 'acknowledged', 'action_planned'].includes(f.status ?? ''),
    ).length,
    corrective_actions: actions.length,
    open_actions: actions.filter((a) =>
      ['open', 'in_progress', 'implemented'].includes(a.status ?? ''),
    ).length,
  }
}

