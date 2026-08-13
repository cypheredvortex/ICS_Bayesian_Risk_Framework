import {
  assetTypeDescriptions,
  kindFallbackDescriptions,
  relationshipColors,
  RELATIONSHIP_FALLBACK_COLOR,
} from './constants'

export function getRiskTone(level: string) {
  if (level === 'critical') return 'text-rose-400 border-rose-500/40 bg-rose-500/10'
  if (level === 'high') return 'text-amber-300 border-amber-500/40 bg-amber-500/10'
  if (level === 'moderate') return 'text-cyan-300 border-cyan-500/40 bg-cyan-500/10'
  return 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10'
}

// Edge stroke colour for a relationship type.  Falls back to a neutral
// slate for types not in the semantic palette (e.g. custom types added via
// settings), so unknown relationships stay visible rather than vanishing.
export function relationshipColor(relType: string | undefined | null): string {
  if (relType) {
    const normalized = relType.toLowerCase().trim()
    const color = relationshipColors[normalized]
    if (color) return color
  }
  return RELATIONSHIP_FALLBACK_COLOR
}

export function getProbabilityColor(probability: number) {
  // Visualization scale for *posterior probabilities* (not risk levels).
  if (probability >= 0.7) return '#fb7185'
  if (probability >= 0.45) return '#f59e0b'
  if (probability >= 0.2) return '#38bdf8'
  return '#34d399'
}

// Risk-level classification. Mirrors backend/risk.py: the classification is
// driven entirely by the active thresholds (single source of truth from the
// backend settings), never by hardcoded constants.
export function riskLevelFor(
  risk: number,
  thresholds: { critical: number; high: number; moderate: number },
): 'critical' | 'high' | 'moderate' | 'low' {
  if (risk >= thresholds.critical) return 'critical'
  if (risk >= thresholds.high) return 'high'
  if (risk >= thresholds.moderate) return 'moderate'
  return 'low'
}

export function formatProbability(value: number) {
  return Number(value).toFixed(3)
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '—'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = bytes
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  return `${value.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`
}

// Compact a type/name into a lowercase alphanumeric token so "control valve",
// "ControlValve" and the CSV-derived "controlvalve" all match the same
// dictionary entry.
function compactToken(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '')
}

// Longest-first so "safety logic solver" wins over "logic solver" and
// "control valve" over "valve" when a candidate contains several entries.
const descriptionKeys = Object.keys(assetTypeDescriptions).sort(
  (a, b) => b.length - a.length,
)

// Resolve a plain-language "what is this asset?" explanation for the Node
// Details panel.  Priority:
//   1. the topology's own `description` field (authoritative, specific);
//   2. the asset-type dictionary keyed by the declared `type`;
//   3. the same dictionary matched against the asset name;
//   4. a generic kind-level fallback.
// Short dictionary keys (acronyms like "ct", "hmi", "rtu") only match as
// whole words to avoid false hits inside longer names.
export function assetDescription(
  attrs: Record<string, unknown> | undefined,
  name: string,
  kind: string,
): string | null {
  const declared = attrs?.description
  if (typeof declared === 'string' && declared.trim()) return declared.trim()

  const declaredType =
    typeof attrs?.type === 'string' && attrs.type.trim()
      ? attrs.type.trim()
      : ''
  const typeToken = declaredType ? compactToken(declaredType) : ''
  if (typeToken) {
    const direct = assetTypeDescriptions[typeToken]
    if (direct) return direct
  }

  const spaced = `${declaredType ? `${declaredType} ` : ''}${name}`.toLowerCase()
  const compacted = compactToken(spaced)
  for (const key of descriptionKeys) {
    if (key.length >= 4) {
      if (compacted.includes(key)) return assetTypeDescriptions[key]
    } else if (new RegExp(`(^|[^a-z0-9])${key}($|[^a-z0-9])`).test(spaced)) {
      return assetTypeDescriptions[key]
    }
  }

  const fallback = kindFallbackDescriptions[kind]
  return fallback ?? null
}

// Acronyms whose full expansion is not written parenthesised in the
// explanation texts (e.g. "A SCADA system …" never spells out "Supervisory
// Control and Data Acquisition"), keyed by the uppercased declared type.
// Used by assetTypeMeaning as a fallback when regex extraction finds no
// "full name (ACRONYM)" pattern.
const KNOWN_ACRONYM_MEANINGS: Record<string, string> = {
  SCADA: 'Supervisory Control and Data Acquisition',
  ERP: 'Enterprise Resource Planning',
  OPC: 'Open Platform Communications',
}

// Resolve the "meaning of the abbreviation" for an asset: e.g. the declared
// type "PLC" paired with the explanation "A programmable logic controller
// (PLC) is …" yields { acronym: "PLC", meaning: "Programmable logic
// controller" }.  Uses the same resolution chain as assetDescription, so the
// meaning always matches the explanation actually shown.  Returns null when
// no acronym expansion can be derived (plain-word types, no description).
export function assetTypeMeaning(
  attrs: Record<string, unknown> | undefined,
  name: string,
  kind: string,
): { acronym: string; meaning: string } | null {
  const description = assetDescription(attrs, name, kind)
  if (!description) return null

  const declaredType =
    typeof attrs?.type === 'string' && attrs.type.trim()
      ? attrs.type.trim()
      : ''
  // The candidate is the declared type when present ("PLC"), otherwise the
  // asset name ("plc_1") — the parenthesised acronym is matched against it.
  const candidate = (declaredType || name).trim()
  if (!candidate) return null

  const candidateUpper = candidate.toUpperCase()

  // Known acronyms whose expansion never appears parenthesised in the
  // explanation text (e.g. "A SCADA system collects …" uses the acronym
  // directly), so the regex below cannot extract them. The exact declared
  // type wins; a multi-word declared type ("SCADA System") falls back to
  // its leading token. The asset name alone never triggers this, so a
  // device named "SCADA-01" without a declared type gets no fabricated
  // meaning.
  const known = KNOWN_ACRONYM_MEANINGS[candidateUpper]
  if (known) return { acronym: candidateUpper, meaning: known }
  if (declaredType) {
    const leadingToken = candidateUpper.split(/[^A-Z0-9]+/).filter(Boolean)[0]
    if (leadingToken) {
      const knownLeading = KNOWN_ACRONYM_MEANINGS[leadingToken]
      if (knownLeading) return { acronym: leadingToken, meaning: knownLeading }
    }
  }

  // Match "full name (ACRONYM)" inside the explanation, e.g.
  // "A programmable logic controller (PLC) is an industrial computer …".
  const match = description.match(
    /([A-Za-z][A-Za-z0-9\-–— .]{1,60}?)\s*\(([A-Za-z0-9.]+)\)/,
  )
  if (!match) return null
  const [, full, acronym] = match

  // The acronym must be the declared type itself or one of its words
  // ("DCS" inside "DCS Controller"). A bare substring match would accept
  // nonsense like a single-letter "(H)" for an "HMI" asset.
  const candidateTokens = candidateUpper.split(/[^A-Z0-9]+/).filter(Boolean)
  const acronymUpper = acronym.toUpperCase()
  if (
    acronymUpper === candidateUpper ||
    candidateTokens.includes(acronymUpper)
  ) {
    const stripped = full.replace(/^(?:an?|the)\s+/i, '')
    const meaning = stripped.charAt(0).toUpperCase() + stripped.slice(1)
    return { acronym, meaning }
  }
  return null
}

// Derive the structural summary client-side from a normalized topology
// payload. Used as a graceful fallback when an upload response omits
// `summary`. It reads the exact same normalized fields the backend computes
// its summary from, so it never reports information the data does not contain.
export function deriveTopologySummary(
  topology: {
    assets: Record<string, Record<string, unknown>>
    relationships: Array<unknown[]>
  },
): {
  zones: Record<string, number>
  assets_without_zone: number
  kinds: Record<string, number>
  relationship_types: Record<string, number>
  firewalled_relationships: number
  field_coverage: Record<string, number>
  purdue_levels: Record<string, number>
} {
  const zones: Record<string, number> = {}
  const kinds: Record<string, number> = {}
  const relationshipTypes: Record<string, number> = {}
  const purdueLevels: Record<string, number> = {}
  const coverage: Record<string, number> = {
    cvss_type: 0,
    exposed: 0,
    patched: 0,
    consequence_severity: 0,
    zone: 0,
    vulnerabilities: 0,
    type: 0,
    description: 0,
  }
  let zoned = 0

  for (const attrs of Object.values(topology.assets)) {
    const kind = String(attrs?.kind ?? 'device')
    kinds[kind] = (kinds[kind] ?? 0) + 1
    const zone = attrs?.zone
    if (zone) {
      const name = String(zone)
      zones[name] = (zones[name] ?? 0) + 1
      zoned += 1
    }
    const level = attrs?.purdue_level
    if (level) {
      const name = String(level)
      purdueLevels[name] = (purdueLevels[name] ?? 0) + 1
    }
    for (const field of Object.keys(coverage)) {
      const value = attrs?.[field]
      if (field === 'vulnerabilities') {
        if (Array.isArray(value) && value.length) coverage[field] += 1
      } else if (value !== undefined && value !== null && value !== '') {
        coverage[field] += 1
      }
    }
  }

  let firewalled = 0
  for (const rel of topology.relationships) {
    const type = rel.length > 2 && rel[2] ? String(rel[2]) : 'connects-to'
    relationshipTypes[type] = (relationshipTypes[type] ?? 0) + 1
    if (rel.length > 3 && rel[3]) firewalled += 1
  }

  return {
    zones,
    assets_without_zone: Math.max(0, Object.keys(topology.assets).length - zoned),
    kinds,
    purdue_levels: purdueLevels,
    relationship_types: relationshipTypes,
    firewalled_relationships: firewalled,
    field_coverage: coverage,
  }
}

// FastAPI's HTTPException serializes as {"detail": "..."}. Pull that out
// instead of dumping raw JSON into the UI; fall back to plain text for
// non-JSON error bodies (e.g. a proxy/500 page).
export async function parseErrorDetail(
  response: Response,
  fallback: string,
): Promise<string> {
  return (await parseErrorBody(response, fallback)).message
}

// Structured variant of parseErrorDetail that also exposes the machine-
// readable error_code and affected_nodes (used by the IMPOSSIBLE_EVIDENCE
// diagnostic from /analyze).
export async function parseErrorBody(
  response: Response,
  fallback: string,
): Promise<{
  message: string
  errorCode?: string
  affectedNodes?: string[]
}> {
  const raw = await response.text()
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>
    let message = fallback
    if (typeof parsed?.detail === 'string') message = parsed.detail
    else if (parsed?.detail) message = JSON.stringify(parsed.detail)
    else if (raw) message = raw
    return {
      message,
      errorCode:
        typeof parsed?.error_code === 'string'
          ? parsed.error_code
          : undefined,
      affectedNodes: Array.isArray(parsed?.affected_nodes)
        ? (parsed.affected_nodes as unknown[]).map(String)
        : undefined,
    }
  } catch {
    return { message: raw || fallback }
  }
}

// Builds a left-to-right layered layout by BFS depth instead of a naive
// index % 3 grid, so upstream/downstream relationships read left-to-right.
// This also happens to match the "layered" layout the backend's
// visualization settings already name. Used as the fallback when a topology
// carries no zone metadata.
export function computeLayeredPositions(
  nodeIds: string[],
  edges: Array<{ source: string; target: string }>,
) {
  const outgoing = new Map<string, string[]>()
  const incomingCount = new Map<string, number>()
  nodeIds.forEach((id) => {
    outgoing.set(id, [])
    incomingCount.set(id, 0)
  })
  edges.forEach(({ source, target }) => {
    if (!outgoing.has(source) || !incomingCount.has(target)) return
    outgoing.get(source)!.push(target)
    incomingCount.set(target, (incomingCount.get(target) ?? 0) + 1)
  })

  const roots = nodeIds.filter((id) => (incomingCount.get(id) ?? 0) === 0)
  const queue: Array<{ id: string; depth: number }> = (
    roots.length ? roots : nodeIds.slice(0, 1)
  ).map((id) => ({
    id,
    depth: 0,
  }))
  const depth = new Map<string, number>()
  const visited = new Set<string>()

  while (queue.length) {
    const { id, depth: d } = queue.shift()!
    if (visited.has(id)) continue
    visited.add(id)
    depth.set(id, d)
    for (const next of outgoing.get(id) ?? []) {
      if (!visited.has(next)) queue.push({ id: next, depth: d + 1 })
    }
  }
  let maxDepth = Math.max(0, ...Array.from(depth.values()))
  nodeIds.forEach((id) => {
    if (!depth.has(id)) {
      maxDepth += 1
      depth.set(id, maxDepth)
    }
  })

  const layerCounts = new Map<number, number>()
  const positions = new Map<string, { x: number; y: number }>()
  nodeIds.forEach((id) => {
    const d = depth.get(id) ?? 0
    const rank = layerCounts.get(d) ?? 0
    layerCounts.set(d, rank + 1)
    positions.set(id, { x: d * 360 + 60, y: rank * 180 + 60 })
  })
  return positions
}

// Orders zone names into columns following the Purdue hierarchy (highest
// level first), keeping ties alphabetical. Zones without a declared Purdue
// level (or without any level at all) sort after every declared level.
export function orderZonesByPurdue(
  zones: Iterable<string>,
  zonePurdue: (zone: string) => string | null,
  rankLevel: (level: string | null) => number,
): string[] {
  // Deduplicate: callers commonly pass one zone name per node (e.g.
  // nodeIds.map(zoneOf)), and laying a zone out once per member would shift
  // every subsequent zone band by that zone's width each time.
  return [...new Set(zones)].sort((a, b) => {
    const ra = rankLevel(zonePurdue(a))
    const rb = rankLevel(zonePurdue(b))
    if (ra !== rb) return ra - rb
    return a.localeCompare(b)
  })
}

// Layouts the network as vertical zone bands ordered by Purdue level, with
// left-to-right causality preserved *within* each zone via BFS layering of
// the zone's local subgraph. Nodes are placed on a grid per zone: the BFS
// depth selects the sub-column (so causal chains such as SIS
// sensors → logic solver → final elements read left-to-right) and the rank
// within a layer selects the row. Dense layers wrap into additional
// sub-columns so no zone grows into an unreadably tall stack. Returns node
// positions plus band geometry (column x, width, extent height) for the
// zone-band decorations.
export function computeZonedPositions(
  nodeIds: string[],
  edges: Array<{ source: string; target: string }>,
  zoneOf: (id: string) => string,
  zoneOrder: string[],
  // Geometry constants — kept as parameters so tests can verify the packing
  // without magic numbers. COLUMN_STEP and ROW_STEP include the visual gaps
  // between adjacent nodes. They are tuned so nodes read as clearly separated
  // and the relationship labels ("controls w=0.70" …) fully fit in the gaps:
  // the 184px-wide cards keep ~146px horizontal and ~135px vertical breathing
  // room — enough for the widest label pill ("programs / operates w=0.80",
  // ~137px) to sit between cards without overlapping them. MAX_ROWS_PER_COLUMN
  // is set high enough that dense same-level layers pack vertically instead of
  // spilling into extra sub-columns, so the extra spacing does not blow up the
  // canvas width and fitView still fits everything on load. ZONE_GAP is the
  // spacing between level bands so the Purdue hierarchy reads as distinct
  // columns without wasting canvas width.
  columnStep = 330,
  rowStep = 220,
  nodeHeight = 76,
  maxRowsPerColumn = 10,
  zoneGap = 150,
) {
  const positions = new Map<string, { x: number; y: number }>()
  const bandExtents = new Map<string, { x: number; width: number; height: number }>()

  let columnX = 0
  zoneOrder.forEach((zone) => {
    const members = nodeIds.filter((id) => zoneOf(id) === zone)
    const localEdges = edges.filter(
      ({ source, target }) =>
        zoneOf(source) === zone && zoneOf(target) === zone,
    )

    // BFS depth within the zone's local subgraph so causal direction still
    // reads left-to-right where the zone contains chains (e.g. SIS sensors
    // -> logic solver -> final elements).
    const outgoing = new Map<string, string[]>()
    const incomingCount = new Map<string, number>()
    members.forEach((id) => {
      outgoing.set(id, [])
      incomingCount.set(id, 0)
    })
    localEdges.forEach(({ source, target }) => {
      if (!outgoing.has(source) || !incomingCount.has(target)) return
      outgoing.get(source)!.push(target)
      incomingCount.set(target, (incomingCount.get(target) ?? 0) + 1)
    })
    const roots = members.filter((id) => (incomingCount.get(id) ?? 0) === 0)
    const queue: Array<{ id: string; depth: number }> = (
      roots.length ? roots : members.slice(0, 1)
    ).map((id) => ({ id, depth: 0 }))
    const depth = new Map<string, number>()
    const visited = new Set<string>()
    while (queue.length) {
      const { id, depth: d } = queue.shift()!
      if (visited.has(id)) continue
      visited.add(id)
      depth.set(id, d)
      for (const next of outgoing.get(id) ?? []) {
        if (!visited.has(next)) queue.push({ id: next, depth: d + 1 })
      }
    }
    let maxDepth = Math.max(0, ...members.map((id) => depth.get(id) ?? 0))
    members.forEach((id) => {
      if (!depth.has(id)) {
        maxDepth += 1
        depth.set(id, maxDepth)
      }
    })

    // Deterministic order: depth first, then id, so dense layers pack the
    // same way on every render.
    const ordered = [...members].sort(
      (a, b) =>
        (depth.get(a) ?? 0) - (depth.get(b) ?? 0) || a.localeCompare(b),
    )
    // Group members by BFS depth; within a depth, assign rows 0..maxRows-1
    // and wrap into additional sub-columns when the column fills up.
    const rowsOf = new Map<string, number>()
    const subColumnOf = new Map<string, number>()
    const membersByDepth = new Map<number, string[]>()
    ordered.forEach((id) => {
      const d = depth.get(id) ?? 0
      const list = membersByDepth.get(d) ?? []
      list.push(id)
      membersByDepth.set(d, list)
    })
    membersByDepth.forEach((ids) => {
      ids.forEach((id, index) => {
        rowsOf.set(id, index % maxRowsPerColumn)
        subColumnOf.set(id, Math.floor(index / maxRowsPerColumn))
      })
    })

    let bandBottom = 0
    let maxColumnIndex = 0
    ordered.forEach((id) => {
      const d = depth.get(id) ?? 0
      const row = rowsOf.get(id) ?? 0
      // The node's depth selects the base sub-column; wrapping a layer past
      // maxRowsPerColumn spills into the next sub-column.
      const subColumn = d + (subColumnOf.get(id) ?? 0)
      const x = 40 + subColumn * columnStep
      const y = 46 + row * rowStep
      positions.set(id, { x: columnX + x, y })
      bandBottom = Math.max(bandBottom, y + nodeHeight)
      maxColumnIndex = Math.max(maxColumnIndex, subColumn)
    })

    const width = 40 + (maxColumnIndex + 1) * columnStep + 24
    bandExtents.set(zone, { x: columnX, width, height: bandBottom + 24 })
    columnX += width + zoneGap
  })

  return { positions, bandExtents }
}
