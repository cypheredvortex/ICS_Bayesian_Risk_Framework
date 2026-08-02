// ═══════════════════════════════════════════════════════════════
// GRC & Audit Platform — TypeScript types
// Mirrors backend/schemas.py response models for all modules.
// ═══════════════════════════════════════════════════════════════

// ── Common ──────────────────────────────────────────────────────

export type IscDateTime = string | null

// ── Organizations / Hierarchy ───────────────────────────────────

export interface Organization {
  id: number
  name: string
  legal_name?: string | null
  registration_number?: string | null
  industry_sector?: string | null
  address_line1?: string | null
  city?: string | null
  state?: string | null
  country?: string | null
  website?: string | null
  phone?: string | null
  email?: string | null
  is_active?: boolean
  created_at?: IscDateTime
  updated_at?: IscDateTime
}

export interface Site {
  id: number
  organization_id: number
  name: string
  code?: string | null
  site_type?: string | null
  city?: string | null
  state?: string | null
  country?: string | null
  latitude?: number | null
  longitude?: number | null
  timezone?: string | null
  is_active?: boolean
}

export interface Plant {
  id: number
  site_id: number
  name: string
  code?: string | null
  plant_type?: string | null
  ics_domain?: string | null
  criticality_level?: string | null
  operational_status?: string | null
  is_active?: boolean
}

// ── Users / Roles ───────────────────────────────────────────────

export interface Role {
  id: number
  name: string
  description?: string | null
  is_system_role?: boolean
}

export interface User {
  id: number
  username: string
  email: string
  first_name?: string | null
  last_name?: string | null
  job_title?: string | null
  organization_id?: number | null
  role_id?: number | null
  department_name?: string | null
  is_active?: boolean
  is_locked?: boolean
  last_login_at?: IscDateTime
  created_at?: IscDateTime
}

// ── Zones / Conduits ────────────────────────────────────────────

export interface SecurityZone {
  id: number
  plant_id: number
  name: string
  zone_level: number
  description?: string | null
  color_hex?: string | null
  classification?: string | null
  access_requirements?: string | null
  is_active?: boolean
}

export interface Conduit {
  id: number
  plant_id: number
  name: string
  source_zone_id: number
  destination_zone_id: number
  conduit_type?: string | null
  communication_protocols?: string | null
  security_requirements?: string | null
  is_encrypted?: boolean
  is_physically_secured?: boolean
}

// ── Assets ──────────────────────────────────────────────────────

export interface AssetCategory {
  id: number
  name: string
  description?: string | null
  parent_id?: number | null
  ics_category?: string | null
}

export interface Asset {
  id: number
  name: string
  organization_id?: number | null
  site_id?: number | null
  plant_id?: number | null
  security_zone_id?: number | null
  category_id?: number | null
  asset_tag?: string | null
  asset_type?: string | null
  serial_number?: string | null
  vendor?: string | null
  model?: string | null
  firmware_version?: string | null
  ip_address?: string | null
  mac_address?: string | null
  criticality?: string | null
  operational_status?: string | null
  asset_owner_id?: number | null
  location_building?: string | null
  location_room?: string | null
  x_position?: number | null
  y_position?: number | null
  is_active?: boolean
  created_at?: IscDateTime
}

export interface AssetDependency {
  id: number
  asset_id: number
  depends_on_asset_id: number
  dependency_type?: string | null
  description?: string | null
  criticality?: string | null
}

// ── Threats & Vulnerabilities ───────────────────────────────────

export interface ThreatCategory {
  id: number
  name: string
  description?: string | null
  reference_framework?: string | null
}

export interface Threat {
  id: number
  threat_category_id?: number | null
  name: string
  description?: string | null
  threat_id?: string | null
  source?: string | null
  likelihood_rating?: string | null
  typical_impact?: string | null
  ics_impact?: string | null
  created_at?: IscDateTime
}

export interface ThreatActor {
  id: number
  name: string
  description?: string | null
  actor_type?: string | null
  capability?: string | null
  motivation?: string | null
  targeting_sectors?: string | null
  common_ttps?: string | null
  is_active?: boolean
}

export interface Vulnerability {
  id: number
  cve_id?: string | null
  name: string
  description?: string | null
  vulnerability_type?: string | null
  cvss_score?: number | null
  cvss_vector?: string | null
  cvss_severity?: string | null
  ics_impact?: string | null
  exploit_available?: boolean
  exploitability?: string | null
  affected_vendor?: string | null
  affected_product?: string | null
  affected_version?: string | null
  patch_available?: boolean
  patch_url?: string | null
  published_date?: string | null
  discovered_date?: string | null
  created_at?: IscDateTime
}

export interface AssetVulnerability {
  id: number
  asset_id: number
  vulnerability_id: number
  detected_date?: string | null
  detection_method?: string | null
  status: string
  mitigation_notes?: string | null
  resolved_date?: string | null
}

// ── Controls ────────────────────────────────────────────────────

export interface ControlCategory {
  id: number
  name: string
  description?: string | null
  control_type?: string | null
  ics_control_domain?: string | null
}

export interface Control {
  id: number
  control_category_id?: number | null
  control_id?: string | null
  name: string
  description?: string | null
  control_type?: string | null
  implementation_status?: string | null
  effectiveness_rating?: string | null
  automation_level?: string | null
  frequency?: string | null
  owner_id?: number | null
  evidence_required?: boolean
  evidence_description?: string | null
  last_reviewed_date?: string | null
  next_review_date?: string | null
  is_active?: boolean
  created_at?: IscDateTime
}

export interface ControlTest {
  id: number
  control_id: number
  asset_id?: number | null
  tester_id?: number | null
  test_date?: string | null
  test_method?: string | null
  test_procedure?: string | null
  result?: string | null
  result_details?: string | null
  evidence_path?: string | null
  next_test_date?: string | null
}

export interface ControlEvidence {
  id: number
  control_id: number
  asset_id?: number | null
  filename: string
  file_path: string
  file_type?: string | null
  evidence_type?: string | null
  description?: string | null
  collected_by_id?: number | null
  collected_date?: string | null
  valid_until?: string | null
  is_current?: boolean
}

// ── Risk Register ───────────────────────────────────────────────

export interface RiskItem {
  id: number
  project_id?: number | null
  organization_id?: number | null
  plant_id?: number | null
  asset_id?: number | null
  threat_id?: number | null
  vulnerability_id?: number | null
  bayesian_risk_result_id?: number | null
  risk_id?: string | null
  title: string
  description?: string | null
  scenario?: string | null
  inherent_likelihood?: number | null
  inherent_impact?: number | null
  inherent_risk?: number | null
  inherent_risk_level?: string | null
  residual_likelihood?: number | null
  residual_impact?: number | null
  residual_risk?: number | null
  residual_risk_level?: string | null
  bayesian_likelihood?: number | null
  bayesian_risk_score?: number | null
  bayesian_risk_level?: string | null
  risk_type?: string | null
  risk_category?: string | null
  root_cause?: string | null
  consequence?: string | null
  treatment_strategy?: string | null
  treatment_status?: string | null
  risk_owner_id?: number | null
  review_frequency?: string | null
  last_reviewed_date?: string | null
  next_review_date?: string | null
  is_accepted?: boolean
  acceptance_reason?: string | null
  status?: string | null
  is_active?: boolean
  created_at?: IscDateTime
}

export interface RiskScenario {
  id: number
  risk_item_id: number
  name: string
  description?: string | null
  evidence_used?: Record<string, unknown> | null
  inherent_risk?: number | null
  residual_risk?: number | null
}

export interface RiskTreatmentPlan {
  id: number
  risk_item_id: number
  title: string
  description?: string | null
  treatment_option?: string | null
  target_date?: string | null
  cost_estimate?: number | null
  cost_currency?: string | null
  responsible_person_id?: number | null
  status?: string | null
  approval_status?: string | null
  approved_by?: number | null
  approval_date?: string | null
  rejection_reason?: string | null
  effectiveness_review_required?: boolean
  effectiveness_review_date?: string | null
}

export interface RiskAcceptance {
  id: number
  risk_item_id: number
  accepted_by_id: number
  acceptance_type?: string | null
  justification: string
  expiration_date?: string | null
  reviewing_authority?: string | null
  conditions?: string | null
  status?: string | null
}

export interface RiskHistory {
  id: number
  risk_item_id: number
  changed_by_id?: number | null
  change_type?: string | null
  previous_values?: Record<string, unknown> | null
  new_values?: Record<string, unknown> | null
  change_reason?: string | null
  created_at?: IscDateTime
}

// ── Compliance ──────────────────────────────────────────────────

export interface ComplianceFramework {
  id: number
  name: string
  version: string
  publisher?: string | null
  description?: string | null
  domain?: string | null
  is_active?: boolean
  created_at?: IscDateTime
}

export interface FrameworkRequirement {
  id: number
  framework_id: number
  requirement_id: string
  parent_requirement_id?: number | null
  title: string
  description?: string | null
  requirement_type?: string | null
  implementation_guidance?: string | null
  evidence_requirements?: string | null
  weight_importance?: string | null
  sort_order?: number | null
  created_at?: IscDateTime
}

export interface ControlMapping {
  id: number
  control_id: number
  requirement_id: number
  mapping_type?: string | null
  mapping_notes?: string | null
  mapping_justification?: string | null
}

export interface ComplianceGap {
  id: number
  organization_id?: number | null
  plant_id?: number | null
  requirement_id: number
  gap_description: string
  severity?: string | null
  status?: string | null
  remediation_plan?: string | null
  target_closure_date?: string | null
  closed_date?: string | null
}

export interface ComplianceAssessment {
  id: number
  organization_id?: number | null
  plant_id?: number | null
  framework_id: number
  project_id?: number | null
  assessment_date?: string | null
  assessor_id?: number | null
  overall_status?: string | null
  compliance_percentage?: number | null
  findings_summary?: string | null
}

// ── Audit Management ────────────────────────────────────────────

export interface AuditProgram {
  id: number
  organization_id?: number | null
  name: string
  description?: string | null
  program_type?: string | null
  start_date?: string | null
  end_date?: string | null
  status?: string | null
  program_manager_id?: number | null
  created_at?: IscDateTime
}

export interface AuditPlan {
  id: number
  audit_program_id?: number | null
  organization_id?: number | null
  plant_id?: number | null
  title: string
  description?: string | null
  audit_type?: string | null
  scope?: string | null
  objectives?: string | null
  criteria?: string | null
  start_date?: string | null
  end_date?: string | null
  estimated_hours?: number | null
  status?: string | null
  lead_auditor_id?: number | null
  created_at?: IscDateTime
}

export interface AuditProcedure {
  id: number
  audit_plan_id: number
  control_id?: number | null
  requirement_id?: number | null
  title: string
  description?: string | null
  procedure_steps?: string | null
  testing_method?: string | null
  sample_size?: number | null
  expected_evidence?: string | null
  sort_order?: number | null
}

export interface AuditFinding {
  id: number
  audit_plan_id: number
  procedure_id?: number | null
  asset_id?: number | null
  control_id?: number | null
  finding_id?: string | null
  title: string
  description: string
  finding_type?: string | null
  severity?: string | null
  likelihood?: string | null
  criteria_reference?: string | null
  root_cause?: string | null
  impact?: string | null
  recommendation?: string | null
  management_response?: string | null
  response_by_id?: number | null
  response_date?: string | null
  acceptance_of_finding?: boolean | null
  status?: string | null
  created_at?: IscDateTime
}

export interface AuditEvidence {
  id: number
  audit_plan_id: number
  procedure_id?: number | null
  evidence_title: string
  description?: string | null
  filename?: string | null
  file_path?: string | null
  evidence_type?: string | null
  collected_by_id?: number | null
  collected_date?: IscDateTime
  is_confidential?: boolean
}

export interface AuditInterview {
  id: number
  audit_plan_id: number
  interviewee_name: string
  interviewee_title?: string | null
  interviewee_department?: string | null
  interviewer_id?: number | null
  interview_date?: IscDateTime
  duration_minutes?: number | null
  topics_covered?: string | null
  key_findings?: string | null
  notes?: string | null
}

// ── Audit Log ───────────────────────────────────────────────────

export interface AuditLogEntry {
  id: number
  user_id?: number | null
  action: string
  entity_type: string
  entity_id?: number | null
  organization_id?: number | null
  ip_address?: string | null
  user_agent?: string | null
  changes?: Record<string, unknown> | null
  metadata?: Record<string, unknown> | null
  created_at?: IscDateTime
}

// ── Corrective Actions (CAPA) ───────────────────────────────────

export interface CorrectiveAction {
  id: number
  finding_id?: number | null
  risk_item_id?: number | null
  compliance_gap_id?: number | null
  action_id?: string | null
  title: string
  description?: string | null
  root_cause_type?: string | null
  root_cause_description?: string | null
  impact_assessment?: string | null
  action_type?: string | null
  priority?: string | null
  status?: string | null
  assigned_to_id?: number | null
  assigned_by_id?: number | null
  assigned_date?: string | null
  target_date?: string | null
  extended_date?: string | null
  completed_date?: string | null
  implementation_description?: string | null
  implementation_evidence?: string | null
  verifier_id?: number | null
  verification_date?: string | null
  verification_result?: string | null
  verification_notes?: string | null
  closure_notes?: string | null
  is_closed?: boolean
  closed_by?: number | null
  closed_date?: string | null
  created_at?: IscDateTime
}

export interface ActionTask {
  id: number
  corrective_action_id: number
  title: string
  description?: string | null
  assigned_to_id?: number | null
  status?: string | null
  due_date?: string | null
  completed_date?: string | null
  completion_notes?: string | null
  sort_order?: number | null
}

export interface EffectivenessReview {
  id: number
  corrective_action_id: number
  review_date?: string | null
  reviewer_id?: number | null
  criteria?: string | null
  result?: string | null
  findings?: string | null
  follow_up_required?: boolean
  follow_up_action?: string | null
}

// ── Dashboard aggregates ────────────────────────────────────────

export interface DashboardSummary {
  organizations: number
  sites: number
  plants: number
  assets: number
  threats: number
  vulnerabilities: number
  controls: number
  risk_items: number
  open_risks: number
  frameworks: number
  audit_plans: number
  open_findings: number
  corrective_actions: number
  open_actions: number
}

