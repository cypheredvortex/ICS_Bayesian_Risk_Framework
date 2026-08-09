export type AssetState = 'Unknown' | 'Compromised' | 'Safe'

// Relationships from the backend always come back as 5-element arrays
// (source, target, rel_type, firewalled, metadata) once they've passed
// through assets.py's normalizer. Some topology sources (e.g. hand-written
// data files) may only have 4 elements, so metadata is optional here.
export type Relationship = [string, string, string, boolean, Record<string, unknown>?]

export type TopologyPayload = {
  assets: Record<string, Record<string, unknown>>
  relationships: Relationship[]
}

// Structural summary computed by the backend from the *normalized* topology
// so the pre-analysis review shows only what the framework actually knows.
// The frontend can derive an equivalent summary client-side as a fallback
// when an upload response omits it.
export type TopologySummary = {
  zones: Record<string, number>
  assets_without_zone: number
  kinds: Record<string, number>
  relationship_types: Record<string, number>
  firewalled_relationships: number
  field_coverage: Record<string, number>
}

// Full /upload-topology-file response: parsed topology + counts + review data.
export type TopologyUploadResult = {
  message: string
  asset_count: number
  relationship_count: number
  warnings: string[]
  summary?: TopologySummary | null
  topology: TopologyPayload
}

// Review data shown in the Topology Assessment workspace before analysis:
// what was parsed, what the backend flagged, and the structural summary.
export type TopologyReviewInfo = {
  fileName: string
  fileSize?: number
  formatLabel: string
  assetCount: number
  relationshipCount: number
  warnings: string[]
  summary: TopologySummary
  source: 'upload'
}

export type GraphNode = { id: string; kind?: string }
export type GraphEdge = {
  source: string
  target: string
  rel_type: string
  firewalled?: boolean
  weight?: number
  protocol?: string | null
  trust?: string | null
  mitre?: string | null
}

export type ResultSummary = {
  topology: string
  asset_count: number
  relationship_count: number
  topology_warnings?: string[]
  risk_thresholds?: RiskThresholds
  evidence_used: Record<string, number>
  overall_risk: number
  risk_level: string
  highest_risk_assets: string[]
  overall_risk_basis?: string
  aggregate_risk?: Record<string, unknown>
  // Model-parameter snapshot that produced this run (traceability).
  non_default_settings?: Array<[string, unknown, unknown]>
}

// Full model-parameter snapshot recorded by the backend for a run, so
// outputs can be traced back to the exact settings that produced them.
export type SettingsSnapshot = Record<string, unknown>

export type ResultPayload = {
  assets?: Record<string, Record<string, unknown>>
  graph: {
    nodes: GraphNode[]
    edges: GraphEdge[]
  }
  posteriors: Record<string, number>
  base_probabilities: Record<string, number>
  cpts?: Record<
    string,
    { parents: string[]; rows: Array<{ parent_state: Record<string, number>; p_compromised: number }> }
  >
  risk_scores: Array<Record<string, unknown>>
  attack_paths: Array<Record<string, unknown>>
  summary: ResultSummary
  evidence_used: Record<string, number>
  timings?: {
    total_time_seconds?: number
  }
  settings_used?: SettingsSnapshot
}

// Active risk-level thresholds (single source of truth: backend settings).
// The backend classifies with these values and every consumer (dashboard,
// pie chart, PDF) reads them from the same place.
export type RiskThresholds = {
  critical: number
  high: number
  moderate: number
}

// Mirrors the fields backend/settings.py actually exposes. protocol/
// trust/mitre multiplier tables exist server-side too but aren't editable
// in the panel to keep it usable.
export type CoreSettings = {
  exposure_weight: number
  patch_weight: number
  impact_weight: number
  // CVSS is a severity score; the mapping to an intrinsic probability is an
  // explicit modelling assumption (logistic | linear legacy).
  cvss_mapping: 'logistic' | 'linear'
  cvss_logistic_params: { k: number; x0: number }
  propagation_weights: Record<string, number>
  firewall_multipliers: Record<'true' | 'false', number>
  risk_thresholds: RiskThresholds
}

export type ToastItem = {
  id: number
  message: string
  tone: 'info' | 'success' | 'error'
}

