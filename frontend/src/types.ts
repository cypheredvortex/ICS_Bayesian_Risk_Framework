export type AssetState = 'Unknown' | 'Compromised' | 'Safe'

// Relationships from the backend always come back as 5-element arrays
// (source, target, rel_type, firewalled, metadata) once they've passed
// through assets.py's normalizer. Preset dataset files on disk may only
// have 4 elements, so metadata is optional here.
export type Relationship = [string, string, string, boolean, Record<string, unknown>?]

export type TopologyPayload = {
  assets: Record<string, Record<string, unknown>>
  relationships: Relationship[]
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
}

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

