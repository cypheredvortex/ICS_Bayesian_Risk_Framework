import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Background,
  Controls,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  type Node,
  type Edge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

type AssetState = 'Unknown' | 'Compromised' | 'Safe'

// Relationships from the backend always come back as 5-element arrays
// (source, target, rel_type, firewalled, metadata) once they've passed
// through assets.py's normalizer. Preset dataset files on disk may only
// have 4 elements, so metadata is optional here.
type Relationship = [string, string, string, boolean, Record<string, unknown>?]

type TopologyPayload = {
  assets: Record<string, Record<string, unknown>>
  relationships: Relationship[]
}

type GraphNode = { id: string; kind?: string }
type GraphEdge = {
  source: string
  target: string
  rel_type: string
  firewalled?: boolean
  weight?: number
  protocol?: string | null
  trust?: string | null
  mitre?: string | null
}

type ResultPayload = {
  graph: {
    nodes: GraphNode[]
    edges: GraphEdge[]
  }
  posteriors: Record<string, number>
  cpts?: Record<string, { parents: string[]; rows: Array<{ parent_state: Record<string, number>; p_compromised: number }> }>
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
type CoreSettings = {
  cvss_weight: number
  exposure_weight: number
  patch_weight: number
  impact_weight: number
  noisy_or_leak: number
  propagation_weights: Record<string, number>
  firewall_multipliers: Record<'true' | 'false', number>
}

type ToastItem = {
  id: number
  message: string
  tone: 'info' | 'success' | 'error'
}

const API_BASE_URL = '/api'
const defaultTopology: TopologyPayload = {
  assets: {},
  relationships: [],
}
const assetStateOrder: AssetState[] = ['Unknown', 'Compromised', 'Safe']

const defaultCoreSettings: CoreSettings = {
  cvss_weight: 1.0,
  exposure_weight: 1.0,
  patch_weight: 1.0,
  impact_weight: 1.0,
  noisy_or_leak: 0.0,
  propagation_weights: {
    controls: 0.7,
    monitors: 0.2,
    actuates: 0.6,
    'connects-to': 0.5,
    'programs / operates': 0.8,
  },
  firewall_multipliers: { true: 0.3, false: 1.0 },
}

const kindColors: Record<string, string> = {
  human: '#a78bfa',
  device: '#38bdf8',
  physical: '#f59e0b',
}

function getRiskTone(level: string) {
  if (level === 'critical') return 'text-rose-400 border-rose-500/40 bg-rose-500/10'
  if (level === 'high') return 'text-amber-300 border-amber-500/40 bg-amber-500/10'
  if (level === 'moderate') return 'text-cyan-300 border-cyan-500/40 bg-cyan-500/10'
  return 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10'
}

function getProbabilityColor(probability: number) {
  if (probability >= 0.7) return '#fb7185'
  if (probability >= 0.45) return '#f59e0b'
  if (probability >= 0.2) return '#38bdf8'
  return '#34d399'
}

function formatProbability(value: number) {
  return Number(value).toFixed(3)
}

function formatEvidence(evidence: Record<string, number>) {
  const entries = Object.entries(evidence)
  if (!entries.length) return 'None — probabilities use the topology and configured assumptions.'
  return entries.map(([asset, state]) => `${asset}: ${state === 1 ? 'Compromised' : 'Safe'}`).join(' · ')
}

// FastAPI's HTTPException serializes as {"detail": "..."}. Pull that out
// instead of dumping raw JSON into the UI; fall back to plain text for
// non-JSON error bodies (e.g. a proxy/500 page).
async function parseErrorDetail(response: Response, fallback: string): Promise<string> {
  const raw = await response.text()
  try {
    const parsed = JSON.parse(raw)
    if (typeof parsed?.detail === 'string') return parsed.detail
    if (parsed?.detail) return JSON.stringify(parsed.detail)
    return raw || fallback
  } catch {
    return raw || fallback
  }
}

// Builds a left-to-right layered layout by BFS depth instead of a naive
// index % 3 grid, so upstream/downstream relationships read left-to-right.
// This also happens to match the "layered" layout the backend's
// visualization settings already name.
function computeLayeredPositions(nodeIds: string[], edges: Array<{ source: string; target: string }>) {
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
  const queue: Array<{ id: string; depth: number }> = (roots.length ? roots : nodeIds.slice(0, 1)).map((id) => ({
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

function Toasts({ items, onDismiss }: { items: ToastItem[]; onDismiss: (id: number) => void }) {
  if (!items.length) return null
  return (
    <div className="fixed right-4 top-4 z-50 flex w-80 flex-col gap-2">
      {items.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className={`rounded-lg border px-4 py-3 text-sm shadow-lg backdrop-blur transition ${
            toast.tone === 'error'
              ? 'border-rose-500/40 bg-rose-950/90 text-rose-200'
              : toast.tone === 'success'
                ? 'border-emerald-500/40 bg-emerald-950/90 text-emerald-200'
                : 'border-cyan-500/40 bg-slate-900/95 text-cyan-100'
          }`}
        >
          <div className="flex items-start justify-between gap-3">
            <span>{toast.message}</span>
            <button onClick={() => onDismiss(toast.id)} className="text-slate-400 hover:text-white" aria-label="Dismiss notification">
              ×
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

export default function App() {
  const [topology, setTopology] = useState<TopologyPayload>(defaultTopology)
  const [evidence, setEvidence] = useState<Record<string, AssetState>>({})
  const [result, setResult] = useState<ResultPayload | null>(null)
  const [uploadedFileName, setUploadedFileName] = useState('')
  const [selectedDataset, setSelectedDataset] = useState('swat_example')
  const [pendingDataset, setPendingDataset] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [nodeQuery, setNodeQuery] = useState('')
  const [cptQuery, setCptQuery] = useState('')
  const [colorMode, setColorMode] = useState<'risk' | 'kind'>('risk')
  const [showAttackPath, setShowAttackPath] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [serverSettings, setServerSettings] = useState<CoreSettings>(defaultCoreSettings)
  const [draftSettings, setDraftSettings] = useState<CoreSettings>(defaultCoreSettings)
  const [settingsLoading, setSettingsLoading] = useState(false)
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const searchInputRef = useRef<HTMLInputElement>(null)
  const toastCounter = useRef(0)

  const pushToast = useCallback((message: string, tone: ToastItem['tone'] = 'info') => {
    toastCounter.current += 1
    const id = toastCounter.current
    setToasts((current) => [...current, { id, message, tone }])
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id))
    }, 5000)
  }, [])

  const dismissToast = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  // Settings live server-side (GET/PUT /settings), independent of any one
  // analysis run, so pull the current values in on mount.
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/settings`)
        if (!response.ok) throw new Error(await parseErrorDetail(response, 'Could not load settings.'))
        const data = (await response.json()) as Record<string, unknown>
        const merged: CoreSettings = {
          cvss_weight: Number(data.cvss_weight ?? defaultCoreSettings.cvss_weight),
          exposure_weight: Number(data.exposure_weight ?? defaultCoreSettings.exposure_weight),
          patch_weight: Number(data.patch_weight ?? defaultCoreSettings.patch_weight),
          impact_weight: Number(data.impact_weight ?? defaultCoreSettings.impact_weight),
          noisy_or_leak: Number(data.noisy_or_leak ?? defaultCoreSettings.noisy_or_leak),
          propagation_weights: {
            ...defaultCoreSettings.propagation_weights,
            ...(data.propagation_weights as Record<string, number> | undefined),
          },
          firewall_multipliers: {
            true: Number((data.firewall_multipliers as Record<string, number> | undefined)?.true ?? defaultCoreSettings.firewall_multipliers.true),
            false: Number((data.firewall_multipliers as Record<string, number> | undefined)?.false ?? defaultCoreSettings.firewall_multipliers.false),
          },
        }
        setServerSettings(merged)
        setDraftSettings(merged)
      } catch {
        // Backend may not be reachable yet on first paint; sliders keep
        // sensible defaults and Save will surface the real error.
      }
    }
    void loadSettings()
  }, [])

  // keyboard shortcuts: "/" focuses node search, "r" runs the assessment
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement
      const typing = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT'
      if (event.key === '/' && !typing) {
        event.preventDefault()
        searchInputRef.current?.focus()
      }
      if (event.key.toLowerCase() === 'r' && !typing) {
        event.preventDefault()
        void runAssessment()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topology, evidence])

  const assets = useMemo(() => Object.entries(topology.assets), [topology.assets])

  const nodeIds = useMemo(() => {
    if (result?.graph?.nodes?.length) return result.graph.nodes.map((node) => node.id)
    return Object.keys(topology.assets)
  }, [result, topology.assets])

  const nodeKindMap = useMemo(() => {
    const map = new Map<string, string>()
    if (result?.graph?.nodes?.length) {
      result.graph.nodes.forEach((node) => {
        if (node.kind) map.set(node.id, node.kind)
      })
    }
    Object.entries(topology.assets).forEach(([id, attrs]) => {
      if (!map.has(id) && attrs.kind) map.set(id, String(attrs.kind))
    })
    return map
  }, [result, topology.assets])

  // The backend only returns posteriors for nodes NOT pinned by evidence
  // (compute_posteriors_with_evidence skips them). Merge evidence back in
  // so evidence-marked assets still show a probability instead of falling
  // back to 0.
  const combinedProbabilities = useMemo(() => {
    const map = new Map<string, number>()
    nodeIds.forEach((id) => {
      if (result?.evidence_used && id in result.evidence_used) {
        map.set(id, result.evidence_used[id])
      } else if (result?.posteriors && id in result.posteriors) {
        map.set(id, result.posteriors[id])
      }
    })
    return map
  }, [nodeIds, result])

  const isEvidenceNode = useCallback((id: string) => Boolean(result?.evidence_used && id in result.evidence_used), [result])

  const chartData = useMemo(() => {
    return nodeIds
      .filter((id) => combinedProbabilities.has(id))
      .map((id) => ({ asset: id, probability: Number(combinedProbabilities.get(id)), pinned: isEvidenceNode(id) }))
      .sort((left, right) => right.probability - left.probability)
  }, [nodeIds, combinedProbabilities, isEvidenceNode])

  const riskRanking = useMemo(() => {
    return (result?.risk_scores ?? []).slice(0, 5).map((item) => ({
      asset: String(item.asset ?? 'unknown'),
      risk: Number(item.risk ?? 0),
      probability: Number(item['P(compromised|evidence)'] ?? 0),
    }))
  }, [result])

  const edgeList = useMemo(() => {
    if (result?.graph?.edges?.length) {
      return result.graph.edges.map((edge) => ({
        source: edge.source,
        target: edge.target,
        label: `${edge.rel_type}${edge.firewalled ? ' 🔒' : ''}${typeof edge.weight === 'number' ? ` (${edge.weight.toFixed(2)})` : ''}`,
      }))
    }
    return topology.relationships.map(([source, target, relType, firewalled]) => ({
      source,
      target,
      label: `${relType}${firewalled ? ' (firewalled)' : ''}`,
    }))
  }, [result, topology.relationships])

  const attackPathNodes = useMemo(() => {
    const first = result?.attack_paths?.[0]
    if (!first) return new Set<string>()
    const path = (first.path ?? first.nodes ?? first.assets) as unknown
    if (Array.isArray(path)) return new Set(path.map(String))
    return new Set<string>()
  }, [result])

  const attackPathEdgeKeys = useMemo(() => {
    const keys = new Set<string>()
    const ordered = Array.from(attackPathNodes)
    for (let i = 0; i < ordered.length - 1; i += 1) {
      keys.add(`${ordered[i]}->${ordered[i + 1]}`)
    }
    return keys
  }, [attackPathNodes])

  const neighborSet = useMemo(() => {
    if (!selectedNode) return null
    const neighbors = new Set<string>([selectedNode])
    edgeList.forEach(({ source, target }) => {
      if (source === selectedNode) neighbors.add(target)
      if (target === selectedNode) neighbors.add(source)
    })
    return neighbors
  }, [selectedNode, edgeList])

  const matchingNodes = useMemo(() => {
    if (!nodeQuery.trim()) return null
    const query = nodeQuery.trim().toLowerCase()
    return new Set(nodeIds.filter((id) => id.toLowerCase().includes(query)))
  }, [nodeQuery, nodeIds])

  const nodePositions = useMemo(() => computeLayeredPositions(nodeIds, edgeList), [nodeIds, edgeList])

  const networkNodes = useMemo<Node[]>(() => {
    return nodeIds.map((nodeId) => {
      const probability = combinedProbabilities.get(nodeId) ?? 0
      const kind = nodeKindMap.get(nodeId) ?? 'device'
      const baseColor = colorMode === 'kind' ? (kindColors[kind] ?? '#94a3b8') : getProbabilityColor(probability)
      const dimmed = (matchingNodes && !matchingNodes.has(nodeId)) || (neighborSet && !neighborSet.has(nodeId))
      const onPath = attackPathNodes.has(nodeId)
      const position = nodePositions.get(nodeId) ?? { x: 0, y: 0 }
      const pinned = isEvidenceNode(nodeId)

      return {
        id: nodeId,
        data: { label: pinned ? `${nodeId} 📌` : nodeId },
        position,
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        style: {
          background: baseColor,
          color: '#02131f',
          border:
            selectedNode === nodeId
              ? '2px solid #f8fafc'
              : onPath && showAttackPath
                ? '2px solid #fb7185'
                : pinned
                  ? '2px dashed #0f172a'
                  : '1px solid rgba(255,255,255,0.14)',
          boxShadow: selectedNode === nodeId ? '0 0 0 4px rgba(34,211,238,0.25)' : 'none',
          opacity: dimmed ? 0.25 : 1,
          width: 170,
          transition: 'opacity 150ms ease, border 150ms ease',
        },
      }
    })
  }, [
    nodeIds,
    combinedProbabilities,
    nodeKindMap,
    selectedNode,
    colorMode,
    matchingNodes,
    neighborSet,
    attackPathNodes,
    showAttackPath,
    nodePositions,
    isEvidenceNode,
  ])

  const networkEdges = useMemo<Edge[]>(() => {
    return edgeList.map(({ source, target, label }, index) => {
      const onPath = showAttackPath && attackPathEdgeKeys.has(`${source}->${target}`)
      const dimmed = neighborSet ? !(neighborSet.has(source) && neighborSet.has(target)) : false
      return {
        id: `${source}-${target}-${index}`,
        source,
        target,
        label,
        type: 'smoothstep',
        animated: onPath,
        style: {
          stroke: onPath ? '#fb7185' : '#64748b',
          strokeWidth: onPath ? 2.5 : 1.5,
          opacity: dimmed ? 0.15 : 1,
        },
        labelStyle: { fill: '#cbd5e1', fontSize: 11 },
        labelBgStyle: { fill: '#0f172a', fillOpacity: 0.85 },
        markerEnd: { type: 'arrowclosed', color: onPath ? '#fb7185' : '#64748b' },
      }
    })
  }, [edgeList, showAttackPath, attackPathEdgeKeys, neighborSet])

  const pieData = useMemo(() => {
    const counts = { critical: 0, high: 0, moderate: 0, low: 0 }
    for (const item of result?.risk_scores ?? []) {
      const risk = Number(item.risk ?? 0)
      if (risk >= 1.5) counts.critical += 1
      else if (risk >= 0.8) counts.high += 1
      else if (risk >= 0.3) counts.moderate += 1
      else counts.low += 1
    }
    return Object.entries(counts).map(([name, value]) => ({ name, value }))
  }, [result])

  const selectedNodeProbability = selectedNode ? (combinedProbabilities.get(selectedNode) ?? null) : null

  const persistTopology = async (payload: TopologyPayload) => {
    const response = await fetch(`${API_BASE_URL}/upload-topology`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topology: payload }),
    })
    if (!response.ok) {
      throw new Error(await parseErrorDetail(response, 'Topology upload failed.'))
    }
    return response.json()
  }

  const applyTopology = (parsed: TopologyPayload, sourceName: string) => {
    setUploadedFileName(sourceName)
    setTopology(parsed)
    setResult(null)
    setSelectedNode(null)
    setEvidence({})
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const supported = /\.(json|ya?ml|csv)$/i.test(file.name)
    if (!supported) {
      pushToast('Unsupported file type. Upload a .json, .yaml/.yml, or .csv topology file.', 'error')
      event.target.value = ''
      return
    }

    // The backend's /upload-topology-file endpoint parses and validates
    // JSON, YAML, and CSV topologies server-side (DAG check, required
    // per-kind fields, etc.), so hand it the raw file rather than trying
    // to parse non-JSON formats in the browser.
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`${API_BASE_URL}/upload-topology-file`, {
        method: 'POST',
        body: formData,
      })
      if (!response.ok) {
        throw new Error(await parseErrorDetail(response, 'Topology file upload failed.'))
      }
      const data = (await response.json()) as { topology: TopologyPayload; asset_count: number; relationship_count: number }
      applyTopology(data.topology, file.name)
      pushToast(`Loaded ${file.name}: ${data.asset_count} assets, ${data.relationship_count} relationships.`, 'success')
    } catch (caughtError) {
      pushToast(caughtError instanceof Error ? caughtError.message : 'Invalid topology file.', 'error')
    } finally {
      event.target.value = ''
    }
  }

  const hasUnsavedEvidence = Object.keys(evidence).some((key) => evidence[key] !== 'Unknown')

  const requestPresetChange = (datasetName: string) => {
    if (datasetName === selectedDataset) return
    if (hasUnsavedEvidence) {
      setPendingDataset(datasetName)
      return
    }
    void loadPresetTopology(datasetName)
  }

  const loadPresetTopology = async (datasetName: string) => {
    setSelectedDataset(datasetName)
    setPendingDataset(null)
    pushToast(`Loading the ${datasetName.replace(/_/g, ' ')} preset dataset…`)

    try {
      const response = await fetch(`${API_BASE_URL}/datasets/${datasetName}`)
      if (!response.ok) {
        throw new Error(await parseErrorDetail(response, 'Preset dataset could not be loaded.'))
      }
      const dataset = (await response.json()) as TopologyPayload
      if (!dataset.assets || !dataset.relationships) {
        throw new Error('Preset dataset payload is invalid.')
      }
      applyTopology(dataset, `${datasetName}.json`)
      await persistTopology(dataset)
      pushToast(`${datasetName.replace(/_/g, ' ')} preset loaded successfully.`, 'success')
    } catch (caughtError) {
      pushToast(caughtError instanceof Error ? caughtError.message : 'Failed to load the preset dataset.', 'error')
    }
  }

  const updateEvidence = (asset: string, state: AssetState) => {
    setEvidence((current) => ({ ...current, [asset]: state }))
  }

  const runAssessment = async () => {
    if (!topology.assets || !Object.keys(topology.assets).length) {
      pushToast('Upload a valid topology file before running the assessment.', 'error')
      return
    }

    setLoading(true)
    // AnalyzeRequest.evidence entries need integer 0/1 state values to
    // match inference.py's _sanitize_evidence, not the UI's Compromised/Safe
    // labels — 422 otherwise.
    const payload = {
      topology,
      evidence: Object.entries(evidence)
        .filter(([, state]) => state !== 'Unknown')
        .map(([asset, state]) => ({ asset, state })),
    }

    try {
      const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!response.ok) {
        throw new Error(await parseErrorDetail(response, 'Assessment request failed.'))
      }
      const data = (await response.json()) as ResultPayload
      setResult(data)
      setSelectedNode(data.graph.nodes[0]?.id ?? null)
      pushToast('Assessment complete — results are now on the dashboard.', 'success')
    } catch (caughtError) {
      pushToast(caughtError instanceof Error ? caughtError.message : 'Assessment could not be completed.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const saveSettings = async () => {
    setSettingsLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: draftSettings }),
      })
      if (!response.ok) {
        throw new Error(await parseErrorDetail(response, 'Could not save settings.'))
      }
      const data = (await response.json()) as Record<string, unknown>
      const merged: CoreSettings = {
        ...draftSettings,
        cvss_weight: Number(data.cvss_weight ?? draftSettings.cvss_weight),
        exposure_weight: Number(data.exposure_weight ?? draftSettings.exposure_weight),
        patch_weight: Number(data.patch_weight ?? draftSettings.patch_weight),
        impact_weight: Number(data.impact_weight ?? draftSettings.impact_weight),
        noisy_or_leak: Number(data.noisy_or_leak ?? draftSettings.noisy_or_leak),
      }
      setServerSettings(merged)
      setDraftSettings(merged)
      pushToast('Settings saved. They apply to the next assessment you run.', 'success')
    } catch (caughtError) {
      pushToast(caughtError instanceof Error ? caughtError.message : 'Could not save settings.', 'error')
    } finally {
      setSettingsLoading(false)
    }
  }

  const resetSettings = async () => {
    setSettingsLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/settings/reset`, { method: 'POST' })
      if (!response.ok) {
        throw new Error(await parseErrorDetail(response, 'Could not reset settings.'))
      }
      const data = (await response.json()) as Record<string, unknown>
      const merged: CoreSettings = {
        cvss_weight: Number(data.cvss_weight ?? defaultCoreSettings.cvss_weight),
        exposure_weight: Number(data.exposure_weight ?? defaultCoreSettings.exposure_weight),
        patch_weight: Number(data.patch_weight ?? defaultCoreSettings.patch_weight),
        impact_weight: Number(data.impact_weight ?? defaultCoreSettings.impact_weight),
        noisy_or_leak: Number(data.noisy_or_leak ?? defaultCoreSettings.noisy_or_leak),
        propagation_weights: {
          ...defaultCoreSettings.propagation_weights,
          ...(data.propagation_weights as Record<string, number> | undefined),
        },
        firewall_multipliers: {
          true: Number((data.firewall_multipliers as Record<string, number> | undefined)?.true ?? defaultCoreSettings.firewall_multipliers.true),
          false: Number((data.firewall_multipliers as Record<string, number> | undefined)?.false ?? defaultCoreSettings.firewall_multipliers.false),
        },
      }
      setServerSettings(merged)
      setDraftSettings(merged)
      pushToast('Settings reset to framework defaults.', 'success')
    } catch (caughtError) {
      pushToast(caughtError instanceof Error ? caughtError.message : 'Could not reset settings.', 'error')
    } finally {
      setSettingsLoading(false)
    }
  }

  const settingsDirty = JSON.stringify(serverSettings) !== JSON.stringify(draftSettings)

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Toasts items={toasts} onDismiss={dismissToast} />

      {pendingDataset ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-sm rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <h3 className="text-lg font-semibold">Discard current evidence?</h3>
            <p className="mt-2 text-sm text-slate-300">
              Switching to the {pendingDataset.replace(/_/g, ' ')} preset will clear the evidence you've marked on the current topology.
            </p>
            <div className="mt-5 flex justify-end gap-3">
              <button onClick={() => setPendingDataset(null)} className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800">
                Cancel
              </button>
              <button
                onClick={() => void loadPresetTopology(pendingDataset)}
                className="rounded-lg bg-rose-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-rose-400"
              >
                Discard and switch
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <header className="border-b border-slate-800 bg-slate-900/80 p-6 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-cyan-300">SOC / Bayesian Risk Console</p>
            <h1 className="mt-2 text-3xl font-semibold">ICS Risk Assessment Framework</h1>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSettingsOpen((open) => !open)}
              className="rounded-full border border-slate-700 bg-slate-950 px-4 py-2 text-sm text-slate-200 hover:border-cyan-500/50 hover:text-cyan-200"
              aria-expanded={settingsOpen}
            >
              Settings {settingsDirty ? '•' : ''}
            </button>
            <div className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-4 py-2 text-sm text-cyan-200">Backend API: {API_BASE_URL}</div>
          </div>
        </div>

        {settingsOpen ? (
          <div className="mx-auto mt-4 max-w-7xl rounded-xl border border-slate-800 bg-slate-950/80 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">Analysis Weighting</h3>
                <p className="mt-1 text-xs text-slate-500">
                  Stored server-side via GET/PUT /settings and applied to every future run — not just this session.
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => void resetSettings()}
                  disabled={settingsLoading}
                  className="rounded-md border border-slate-600 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-50"
                >
                  Reset to defaults
                </button>
                <button
                  onClick={() => void saveSettings()}
                  disabled={settingsLoading || !settingsDirty}
                  className="rounded-md bg-cyan-500 px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {settingsLoading ? 'Saving…' : settingsDirty ? 'Save changes' : 'Saved'}
                </button>
              </div>
            </div>

            <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-5">
              {(
                [
                  ['cvss_weight', 'CVSS weight', 0, 2],
                  ['exposure_weight', 'Exposure weight', 0, 2],
                  ['patch_weight', 'Patch weight', 0, 2],
                  ['impact_weight', 'Impact weight', 0, 2],
                  ['noisy_or_leak', 'Noisy-OR leak', 0, 1],
                ] as Array<[keyof Omit<CoreSettings, 'propagation_weights' | 'firewall_multipliers'>, string, number, number]>
              ).map(([key, label, min, max]) => (
                <label key={key} className="text-xs text-slate-300">
                  <div className="flex items-center justify-between">
                    <span>{label}</span>
                    <span className="font-mono text-cyan-300">{draftSettings[key].toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min={min}
                    max={max}
                    step={0.01}
                    value={draftSettings[key]}
                    onChange={(event) => setDraftSettings((current) => ({ ...current, [key]: Number(event.target.value) }))}
                    className="mt-2 w-full accent-cyan-500"
                    aria-label={label}
                  />
                </label>
              ))}
            </div>

            <div className="mt-6 border-t border-slate-800 pt-4">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Propagation weight by relationship type</h4>
              <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                {Object.entries(draftSettings.propagation_weights).map(([relType, value]) => (
                  <label key={relType} className="text-xs text-slate-300">
                    <div className="flex items-center justify-between">
                      <span className="truncate" title={relType}>
                        {relType}
                      </span>
                      <span className="font-mono text-cyan-300">{value.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={1}
                      step={0.01}
                      value={value}
                      onChange={(event) =>
                        setDraftSettings((current) => ({
                          ...current,
                          propagation_weights: { ...current.propagation_weights, [relType]: Number(event.target.value) },
                        }))
                      }
                      className="mt-2 w-full accent-cyan-500"
                      aria-label={`Propagation weight for ${relType}`}
                    />
                  </label>
                ))}
              </div>
            </div>

            <div className="mt-6 border-t border-slate-800 pt-4">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Firewall multiplier</h4>
              <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:w-1/2">
                {(['true', 'false'] as const).map((flag) => (
                  <label key={flag} className="text-xs text-slate-300">
                    <div className="flex items-center justify-between">
                      <span>Link is {flag === 'true' ? 'firewalled' : 'not firewalled'}</span>
                      <span className="font-mono text-cyan-300">{draftSettings.firewall_multipliers[flag].toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={1.5}
                      step={0.01}
                      value={draftSettings.firewall_multipliers[flag]}
                      onChange={(event) =>
                        setDraftSettings((current) => ({
                          ...current,
                          firewall_multipliers: { ...current.firewall_multipliers, [flag]: Number(event.target.value) },
                        }))
                      }
                      className="mt-2 w-full accent-cyan-500"
                      aria-label={`Firewall multiplier when ${flag}`}
                    />
                  </label>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-6">
        <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl shadow-slate-950/30">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-2xl font-semibold">Topology &amp; Assessment</h2>
              <p className="mt-2 text-slate-300">Choose a preset or upload a topology, then run a full Bayesian cyber-risk assessment.</p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200">
                <span>Preset dataset</span>
                <select
                  className="bg-slate-950 text-slate-100 outline-none"
                  value={selectedDataset}
                  onChange={(event) => requestPresetChange(event.target.value)}
                  aria-label="Select a predefined dataset"
                >
                  <option value="swat_example">SWAT Example</option>
                  <option value="building_automation">Building Automation</option>
                  <option value="power_substation">Power Substation</option>
                  <option value="water_treatment">Water Treatment</option>
                </select>
              </label>
              <label className="cursor-pointer rounded-lg border border-slate-600 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-cyan-500/50 hover:text-cyan-200">
                Upload topology
                <input
                  type="file"
                  accept=".json,.yaml,.yml,.csv,application/json,text/yaml,text/csv"
                  onChange={(event) => void handleFileUpload(event)}
                  className="sr-only"
                  aria-label="Upload a topology file"
                />
              </label>
              <button
                onClick={() => void runAssessment()}
                disabled={loading || !Object.keys(topology.assets).length}
                className="rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
                title="Shortcut: r"
              >
                {loading ? 'Running…' : 'Run assessment'}
              </button>
            </div>
          </div>
          <div className="mt-4 rounded-xl bg-slate-950/80 px-4 py-3 text-sm text-slate-300" aria-live="polite">
            {Object.keys(topology.assets).length ? (
              <span>Active topology: <strong className="text-slate-100">{uploadedFileName || 'Preset dataset'}</strong> &middot; {Object.keys(topology.assets).length} assets &middot; {topology.relationships.length} connections</span>
            ) : (
              <span className="text-slate-400">Select a preset or upload a .json, .yaml/.yml, or .csv topology file to begin.</span>
            )}
          </div>
        </section>

        <section>
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">Evidence Selection</h2>
            <div className="mt-4 max-h-72 space-y-3 overflow-y-auto pr-1">
              {assets.length === 0 ? (
                <p className="text-sm text-slate-400">Upload a topology to populate the evidence controls.</p>
              ) : (
                assets.map(([asset]) => (
                  <div key={asset} className="flex flex-col gap-3 rounded-xl bg-slate-800 p-3 lg:flex-row lg:items-center lg:justify-between">
                    <span className="font-medium">{asset}</span>
                    <div className="flex flex-wrap gap-2">
                      {assetStateOrder.map((state) => (
                        <button
                          key={state}
                          onClick={() => updateEvidence(asset, state)}
                          className={`rounded px-3 py-1 text-sm transition ${evidence[asset] === state ? 'bg-cyan-500 text-slate-950' : 'bg-slate-700 text-white hover:bg-slate-600'}`}
                          aria-label={`Mark ${asset} as ${state}`}
                          aria-pressed={evidence[asset] === state}
                        >
                          {state}
                        </button>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-xl font-semibold">Network Viewer</h2>
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <input
                  ref={searchInputRef}
                  value={nodeQuery}
                  onChange={(event) => setNodeQuery(event.target.value)}
                  placeholder="Search nodes… ( / )"
                  className="w-40 rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-slate-100 outline-none focus:border-cyan-500"
                  aria-label="Search nodes"
                />
                <div className="flex overflow-hidden rounded-md border border-slate-700" role="group" aria-label="Color mode">
                  <button onClick={() => setColorMode('risk')} className={`px-2 py-1.5 ${colorMode === 'risk' ? 'bg-cyan-500 text-slate-950' : 'bg-slate-950 text-slate-300'}`}>
                    By risk
                  </button>
                  <button onClick={() => setColorMode('kind')} className={`px-2 py-1.5 ${colorMode === 'kind' ? 'bg-cyan-500 text-slate-950' : 'bg-slate-950 text-slate-300'}`}>
                    By asset type
                  </button>
                </div>
                <button
                  onClick={() => setShowAttackPath((value) => !value)}
                  className={`rounded-md border px-2 py-1.5 ${showAttackPath ? 'border-rose-400/60 bg-rose-500/10 text-rose-200' : 'border-slate-700 bg-slate-950 text-slate-300'}`}
                  aria-pressed={showAttackPath}
                >
                  Attack path
                </button>
              </div>
            </div>
            <div className="h-[440px] rounded-xl bg-slate-950">
              {nodeIds.length ? (
                <ReactFlowProvider>
                  <ReactFlow
                    nodes={networkNodes}
                    edges={networkEdges}
                    fitView
                    fitViewOptions={{ padding: 0.2 }}
                    onNodeClick={(_, node) => setSelectedNode(String(node.id))}
                    onPaneClick={() => setSelectedNode(null)}
                    proOptions={{ hideAttribution: true }}
                  >
                    <MiniMap pannable zoomable />
                    <Controls />
                    <Background />
                  </ReactFlow>
                </ReactFlowProvider>
              ) : (
                <div className="flex h-full items-center justify-center text-sm text-slate-500">No topology to display yet — upload a file or load a preset.</div>
              )}
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Colors: {colorMode === 'risk' ? 'blue (lower posterior probability) → amber → rose (higher posterior probability)' : 'purple = human, blue = device, amber = physical process'}. 📌 marks
              evidence-pinned assets. An attack path is a calculated sequence of directed links from a likely entry point to a high-risk asset; it is not proof that an attack occurred.
              {showAttackPath && attackPathNodes.size ? ' The rose outline shows the highest-scoring calculated path in this assessment.' : ''}
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">Node Details</h2>
            {selectedNode ? (
              <div className="mt-4 space-y-3 rounded-xl bg-slate-950/80 p-4 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Asset</span>
                  <span className="font-semibold text-white">{selectedNode}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Kind</span>
                  <span className="font-semibold text-white">{nodeKindMap.get(selectedNode) ?? '—'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Posterior</span>
                  <span className="font-semibold text-cyan-300">
                    {selectedNodeProbability === null ? '—' : formatProbability(selectedNodeProbability)}
                    {isEvidenceNode(selectedNode) ? ' (pinned by evidence)' : ''}
                  </span>
                </div>
                <p className="-mt-2 text-xs text-slate-400">Probability that this asset is compromised after applying evidence and network dependencies. A pinned value comes directly from selected evidence.</p>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Risk rank</span>
                  <span className="font-semibold text-white">{riskRanking.findIndex((entry) => entry.asset === selectedNode) + 1 || '—'}</span>
                </div>
                <p className="-mt-2 text-xs text-slate-400">Position in the risk register. Risk combines posterior probability with configured consequence impact; it is not probability alone.</p>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">On top attack path</span>
                  <span className={`font-semibold ${attackPathNodes.has(selectedNode) ? 'text-rose-300' : 'text-slate-400'}`}>
                    {attackPathNodes.has(selectedNode) ? 'Yes' : 'No'}
                  </span>
                </div>
                <p className="-mt-2 text-xs text-slate-400">“Yes” means that this asset lies on the calculated path with the highest combined propagation-and-target-risk score for this run.</p>
              </div>
            ) : (
              <p className="mt-4 text-sm text-slate-400">Select a node in the network to inspect its probability details.</p>
            )}
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">Results Dashboard</h2>
            {result ? (
              <div className="mt-4 space-y-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl bg-slate-800 p-4">
                    <p className="text-sm text-slate-400">Overall Risk</p>
                    <p className="mt-2 text-2xl font-semibold text-cyan-300">{formatProbability(result.summary.overall_risk)}</p>
                    <p className="mt-1 text-xs text-slate-400">Sum of asset risk scores; compare scenarios using the same model and settings.</p>
                  </div>
                  <div className={`rounded-xl border p-4 ${getRiskTone(result.summary.risk_level)}`}>
                    <p className="text-sm">Risk Level</p>
                    <p className="mt-2 text-2xl font-semibold uppercase">{result.summary.risk_level}</p>
                  </div>
                </div>

                <div className="rounded-xl bg-slate-800 p-4">
                  <h3 className="font-semibold">Posterior probabilities</h3>
                  <p className="mt-1 text-xs text-slate-400">Estimated compromise probability after evidence propagates through the Bayesian network.</p>
                  <div className="mt-3 max-h-56 space-y-2 overflow-y-auto pr-1 text-sm">
                    {chartData.map(({ asset, probability, pinned }) => (
                      <button key={asset} onClick={() => setSelectedNode(asset)} className="flex w-full items-center justify-between rounded-lg bg-slate-900/70 px-3 py-2 text-left hover:bg-slate-900">
                        <span>
                          {asset}
                          {pinned ? ' 📌' : ''}
                        </span>
                        <span className="font-medium text-cyan-200">{formatProbability(probability)}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="rounded-xl bg-slate-800 p-4">
                  <h3 className="font-semibold">Top high-risk assets</h3>
                  <p className="mt-1 text-xs text-slate-400">Priorities by risk score: posterior probability × configured consequence impact.</p>
                  <div className="mt-3 space-y-2 text-sm">
                    {riskRanking.map((entry) => (
                      <button key={entry.asset} onClick={() => setSelectedNode(entry.asset)} className="flex w-full items-center justify-between rounded-lg bg-slate-900/70 px-3 py-2 text-left hover:bg-slate-900">
                        <span>{entry.asset}</span>
                        <span className="font-medium text-rose-300">{formatProbability(entry.risk)}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="rounded-xl bg-slate-800 p-4">
                  <h3 className="font-semibold">Highest-priority attack path</h3>
                  <p className="mt-3 break-words text-sm text-slate-300">
                    {result.attack_paths?.length
                      ? `${((result.attack_paths[0].path as string[] | undefined) ?? []).join(' → ')}`
                      : 'No path was calculated. Mark an entry asset as Compromised to analyse a specific scenario.'}
                  </p>
                  {result.attack_paths?.length ? <p className="mt-2 text-xs text-slate-400">Score {formatProbability(Number(result.attack_paths[0].score ?? 0))}: this modelled route combines link propagation weights and destination risk. It prioritises investigation; it is not proof of a real intrusion.</p> : null}
                </div>
              </div>
            ) : (
              <p className="mt-4 text-slate-400">No assessment results yet. Load a topology, optionally mark evidence, then run the assessment.</p>
            )}
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">Compromise probability by asset</h2>
            <p className="mt-1 text-sm text-slate-400">Posterior probability for each asset after the current evidence is applied. This chart shows probability, not the risk score.</p>
            <div className="mt-4 h-80 w-full">
              {chartData.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 24 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="asset" tick={{ fill: '#e2e8f0', fontSize: 12 }} angle={-24} textAnchor="end" height={52} axisLine={{ stroke: '#64748b' }} tickLine={{ stroke: '#64748b' }} />
                    <YAxis
                      domain={[0, 1]}
                      tick={{ fill: '#cbd5e1', fontSize: 12 }}
                      label={{ value: 'Posterior probability (0–1)', angle: -90, position: 'insideLeft', fill: '#f8fafc', fontSize: 13, fontWeight: 700 }}
                      axisLine={{ stroke: '#64748b' }}
                      tickLine={{ stroke: '#64748b' }}
                    />
                    <Tooltip
                      formatter={(value: number) => [formatProbability(value), 'Posterior probability']}
                      labelStyle={{ color: '#e2e8f0' }}
                      itemStyle={{ color: '#f8fafc', fontWeight: 700 }}
                      contentStyle={{ background: '#0f172a', borderRadius: '12px', border: '1px solid rgba(56, 189, 248, 0.25)', color: '#f8fafc' }}
                    />
                    <Bar dataKey="probability" name="Posterior Probability" radius={[6, 6, 0, 0]} onClick={(entry: { asset: string }) => setSelectedNode(entry.asset)} cursor="pointer">
                      {chartData.map((entry) => (
                        <Cell key={entry.asset} fill={getProbabilityColor(entry.probability)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-sm text-slate-500">Run an assessment to populate this chart.</div>
              )}
            </div>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">Risk Ranking</h2>
            <div className="mt-4 h-72 w-full">
              {pieData.some((entry) => entry.value > 0) ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={58} outerRadius={96} paddingAngle={3} label={false} labelLine={false}>
                      <Cell fill="#fb7185" />
                      <Cell fill="#f59e0b" />
                      <Cell fill="#38bdf8" />
                      <Cell fill="#34d399" />
                    </Pie>
                    <Tooltip formatter={(value: number) => [`${value} assets`, 'Count']} contentStyle={{ background: '#0f172a', border: '1px solid rgba(56, 189, 248, 0.25)', color: '#f8fafc' }} labelStyle={{ color: '#f8fafc', fontWeight: 700 }} itemStyle={{ color: '#f8fafc' }} />
                    <Legend wrapperStyle={{ color: '#e2e8f0' }} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-sm text-slate-500">Run an assessment to see the risk-level breakdown.</div>
              )}
            </div>
            {pieData.some((entry) => entry.value > 0) ? (
              <div className="mt-2 flex flex-wrap justify-center gap-x-4 gap-y-2 text-xs" aria-label="Risk level counts">
                {pieData.map((entry, index) => (
                  <span key={entry.name} className="whitespace-nowrap text-slate-200">
                    <span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: ['#fb7185', '#f59e0b', '#38bdf8', '#34d399'][index] }} />
                    {entry.name[0].toUpperCase() + entry.name.slice(1)}: {entry.value}
                  </span>
                ))}
              </div>
            ) : null}
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">Bayesian Results</h2>
            <p className="mt-1 text-sm text-slate-400">Run context and model outputs. Evidence is what you supplied; probabilities and rankings are calculated from that evidence and the topology.</p>
            <div className="mt-4 rounded-xl bg-slate-950/80 p-4 text-sm">
              {result ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Evidence used</span>
                    <span className="max-w-[65%] text-right font-semibold text-white">{formatEvidence(result.evidence_used)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Assets</span>
                    <span className="font-semibold text-white">{result.summary.asset_count}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Connections</span>
                    <span className="font-semibold text-white">{result.summary.relationship_count}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Run time</span>
                    <span className="font-semibold text-white">{Number(result.timings?.total_time_seconds ?? 0).toFixed(3)}s</span>
                  </div>
                </div>
              ) : (
                <p className="text-slate-400">No assessment results available.</p>
              )}
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold">Conditional Probability Tables</h2>
              <p className="mt-1 text-sm text-slate-400">Inspect each node’s generated Noisy-OR CPT. Each row is P(node compromised | parent states).</p>
            </div>
            <input value={cptQuery} onChange={(event) => setCptQuery(event.target.value)} placeholder="Search node CPTs" aria-label="Search conditional probability tables" className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-500" />
          </div>
          {result?.cpts ? (
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              {Object.entries(result.cpts).filter(([asset]) => asset.toLowerCase().includes(cptQuery.trim().toLowerCase())).map(([asset, cpt]) => (
                <details key={asset} className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950/60">
                  <summary className="cursor-pointer px-4 py-3 font-semibold text-slate-100 hover:bg-slate-800">
                    {asset} <span className="ml-2 text-xs font-normal text-slate-400">parents: {cpt.parents.length ? cpt.parents.join(', ') : 'none'}</span>
                  </summary>
                  <div className="max-h-60 overflow-auto border-t border-slate-800">
                    <table className="w-full text-left text-xs"><thead className="sticky top-0 bg-slate-800 text-slate-300"><tr><th className="p-3">Parent states</th><th className="p-3">P(compromised)</th></tr></thead>
                      <tbody>{cpt.rows.map((row, index) => <tr key={index} className="border-t border-slate-800"><td className="p-3 text-slate-300">{Object.entries(row.parent_state).map(([parent, state]) => `${parent}=${state}`).join(', ') || 'Root node'}</td><td className="p-3 font-semibold text-cyan-200">{formatProbability(row.p_compromised)}</td></tr>)}</tbody>
                    </table>
                  </div>
                </details>
              ))}
            </div>
          ) : <p className="mt-4 text-sm text-slate-500">Run an assessment to generate CPTs for every node.</p>}
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-xl font-semibold">Reports</h2>
          <p className="mt-1 text-sm text-slate-400">Download the two decision-ready outputs from the latest assessment: a sortable risk register and an executive assessment report.</p>
          <div className="mt-4 flex flex-wrap gap-3">
            {[
              ['risk_table.csv', 'Download risk register (CSV)'],
              ['assessment.pdf', 'Download assessment report (PDF)'],
            ].map(([file, label]) => (
              <a
                key={file}
                className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-cyan-500/50 hover:text-cyan-200"
                href={`${API_BASE_URL}/reports/${file}`}
                download
              >
                {label}
              </a>
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}
