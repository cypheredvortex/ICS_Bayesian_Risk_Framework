export function getRiskTone(level: string) {
  if (level === 'critical') return 'text-rose-400 border-rose-500/40 bg-rose-500/10'
  if (level === 'high') return 'text-amber-300 border-amber-500/40 bg-amber-500/10'
  if (level === 'moderate') return 'text-cyan-300 border-cyan-500/40 bg-cyan-500/10'
  return 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10'
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

export function formatEvidence(evidence?: Record<string, number> | null) {
  const entries = Object.entries(evidence ?? {})
  if (!entries.length) return 'None — probabilities use the topology and configured assumptions.'
  return entries
    .map(([asset, state]) => `${asset}: ${state === 1 ? 'Compromised' : 'Safe'}`)
    .join(' · ')
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
// visualization settings already name.
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

