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

export type ResultPayload = {
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
  summary: {
    topology: string
    asset_count: number
    relationship_count: number
    evidence_used: Record<string, number>
    overall_risk: number
    risk_level: string
    highest_risk_assets: string[]
  }
  evidence_used: Record<string, number>
  timings?: {
    total_time_seconds?: number
  }
}

// Mirrors the fields backend/settings.py actually exposes. Kept as a
// subset — protocol/trust/mitre multiplier tables exist server-side too
// but aren't editable here to keep the panel usable.
export type CoreSettings = {
  cvss_weight: number
  exposure_weight: number
  patch_weight: number
  impact_weight: number
  propagation_weights: Record<string, number>
  firewall_multipliers: Record<'true' | 'false', number>
}

export type ToastItem = {
  id: number
  message: string
  tone: 'info' | 'success' | 'error'
}

