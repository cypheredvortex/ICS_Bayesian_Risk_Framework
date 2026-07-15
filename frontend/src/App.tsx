import { useMemo, useState } from 'react'
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

type TopologyPayload = {
  assets: Record<string, Record<string, unknown>>
  relationships: Array<[string, string, string, boolean]>
}

type ResultPayload = {
  graph: {
    nodes: string[]
    edges: Array<Record<string, unknown>>
  }
  posteriors: Record<string, number>
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
const API_BASE_URL = '/api'
const defaultTopology: TopologyPayload = {
  assets: {},
  relationships: [],
}
const assetStateOrder: AssetState[] = ['Unknown', 'Compromised', 'Safe']
const presetTopology: TopologyPayload = {
  assets: {
    operators: {
      kind: 'human',
      role: 'operator',
      awareness: 0.4,
      privilege: 'standard',
    },
    automation_engineers: {
      kind: 'human',
      role: 'engineer',
      awareness: 0.6,
      privilege: 'elevated',
    },
    local_hmi: {
      kind: 'device',
      cvss_type: 7.5,
      exposed: true,
      patched: false,
      consequence_severity: 5,
    },
    scada: {
      kind: 'device',
      cvss_type: 8.0,
      exposed: true,
      patched: true,
      consequence_severity: 7,
    },
    industrial_network: {
      kind: 'device',
      cvss_type: 6.0,
      exposed: false,
      patched: true,
      consequence_severity: 4,
    },
    plc_1: {
      kind: 'device',
      cvss_type: 9.0,
      exposed: false,
      patched: true,
      consequence_severity: 9,
      scope: 4,
    },
    plc_2: {
      kind: 'device',
      cvss_type: 9.0,
      exposed: false,
      patched: true,
      consequence_severity: 9,
      scope: 4,
    },
    sensors_actuators_1: {
      kind: 'device',
      cvss_type: 5.0,
      exposed: false,
      patched: true,
      consequence_severity: 8,
      scope: 4,
    },
    sensors_actuators_2: {
      kind: 'device',
      cvss_type: 5.0,
      exposed: false,
      patched: true,
      consequence_severity: 8,
      scope: 4,
    },
    physical_process: {
      kind: 'physical',
      p_base_override: 0.02,
      consequence_severity: 10,
      scope: 5,
    },
    historian: {
      kind: 'device',
      cvss_type: 6.5,
      exposed: false,
      patched: true,
      consequence_severity: 5,
    },
  },
  relationships: [
    ['operators', 'local_hmi', 'controls', false],
    ['operators', 'scada', 'controls', false],
    ['local_hmi', 'industrial_network', 'connects-to', false],
    ['scada', 'industrial_network', 'connects-to', false],
    ['industrial_network', 'plc_1', 'programs / operates', true],
    ['industrial_network', 'plc_2', 'programs / operates', true],
    ['plc_1', 'sensors_actuators_1', 'actuates', false],
    ['plc_2', 'sensors_actuators_2', 'actuates', false],
    ['sensors_actuators_1', 'physical_process', 'actuates', false],
    ['sensors_actuators_2', 'physical_process', 'actuates', false],
    ['physical_process', 'historian', 'monitors', false],
    ['historian', 'automation_engineers', 'monitors', false],
  ],
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

export default function App() {
  const [topology, setTopology] = useState<TopologyPayload>(defaultTopology)
  const [evidence, setEvidence] = useState<Record<string, AssetState>>({})
  const [result, setResult] = useState<ResultPayload | null>(null)
  const [uploadedFileName, setUploadedFileName] = useState('')
  const [selectedDataset, setSelectedDataset] = useState('swat_example')
  const [status, setStatus] = useState('Upload a topology or load a preset dataset to begin an assessment.')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<string | null>(null)

  const assets = useMemo(() => Object.entries(topology.assets), [topology.assets])

  const chartData = useMemo(() => {
    return Object.entries(result?.posteriors ?? {})
      .map(([asset, probability]) => ({ asset, probability: Number(probability) }))
      .sort((left, right) => right.probability - left.probability)
  }, [result])

  const riskRanking = useMemo(() => {
    return (result?.risk_scores ?? []).slice(0, 5).map((item) => ({
      asset: String(item.asset ?? 'unknown'),
      risk: Number(item.risk ?? 0),
      probability: Number(item['P(compromised|evidence)'] ?? 0),
    }))
  }, [result])

  const networkNodes = useMemo<Node[]>(() => {
    const nodeIds = result?.graph?.nodes?.length ? result.graph.nodes : Object.keys(topology.assets)
    return nodeIds.map((nodeId, index) => ({
      id: nodeId,
      data: {
        label: nodeId,
        probability: result?.posteriors?.[nodeId] ?? 0,
      },
      position: {
        x: 180 * (index % 3) + 40,
        y: 120 * Math.floor(index / 3) + 40,
      },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: {
        background: getProbabilityColor(result?.posteriors?.[nodeId] ?? 0),
        color: '#02131f',
        border: selectedNode === nodeId ? '2px solid #f8fafc' : '1px solid rgba(255,255,255,0.14)',
        boxShadow: selectedNode === nodeId ? '0 0 0 4px rgba(34,211,238,0.25)' : 'none',
        width: 170,
      },
    }))
  }, [result, selectedNode, topology.assets])

  const networkEdges = useMemo<Edge[]>(() => {
    if (result?.graph?.edges?.length) {
      return result.graph.edges.map((edge, index) => ({
        id: `${String(edge.source)}-${String(edge.target)}-${index}`,
        source: String(edge.source),
        target: String(edge.target),
        label: String(edge.rel_type ?? 'link'),
        animated: true,
        style: { stroke: '#38bdf8' },
        markerEnd: { type: 'arrowclosed' },
      }))
    }

    return topology.relationships.map(([source, target, relType, firewalled], index) => ({
      id: `${source}-${target}-${index}`,
      source,
      target,
      label: `${relType}${firewalled ? ' (firewalled)' : ''}`,
      animated: true,
      style: { stroke: '#64748b' },
      markerEnd: { type: 'arrowclosed' },
    }))
  }, [result, topology.relationships])

  const pieData = useMemo(() => {
    const counts = {
      critical: 0,
      high: 0,
      moderate: 0,
      low: 0,
    }

    const ranking = result?.risk_scores ?? []
    for (const item of ranking) {
      const risk = Number(item.risk ?? 0)
      if (risk >= 1.5) counts.critical += 1
      else if (risk >= 0.8) counts.high += 1
      else if (risk >= 0.3) counts.moderate += 1
      else counts.low += 1
    }

    return Object.entries(counts).map(([name, value]) => ({ name, value }))
  }, [result])

  const selectedNodeProbability = result?.posteriors?.[selectedNode ?? ''] ?? null

  const persistTopology = async (payload: TopologyPayload) => {
    const response = await fetch(`${API_BASE_URL}/upload-topology`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topology: payload }),
    })

    if (!response.ok) {
      const message = await response.text()
      throw new Error(message || 'Topology upload failed.')
    }

    return response.json()
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const text = await file.text()
    try {
      const parsed = JSON.parse(text) as TopologyPayload
      if (!parsed.assets || !parsed.relationships) {
        throw new Error('Topology JSON must contain assets and relationships.')
      }

      setUploadedFileName(file.name)
      setTopology(parsed)
      setStatus(`Loaded ${Object.keys(parsed.assets).length} assets and ${parsed.relationships.length} relationships.`)
      setError(null)
      await persistTopology(parsed)
      setStatus(`Uploaded ${file.name} to the backend and loaded ${Object.keys(parsed.assets).length} assets.`)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Invalid topology JSON.')
      setStatus('Topology validation failed.')
    }
  }

  const loadPresetTopology = async (datasetName: string) => {
    setSelectedDataset(datasetName)
    setTopology(presetTopology)
    setResult(null)
    setSelectedNode(null)
    setUploadedFileName(`${datasetName}.json`)
    setStatus(`Loaded the ${datasetName} preset dataset.`)
    setError(null)

    try {
      await persistTopology(presetTopology)
      setStatus(`Preset dataset ${datasetName} uploaded to the backend successfully.`)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Failed to persist the preset dataset.')
    }
  }

  const updateEvidence = (asset: string, state: AssetState) => {
    setEvidence((current) => ({ ...current, [asset]: state }))
  }

  const runAssessment = async () => {
    if (!topology.assets || !topology.relationships.length) {
      setError('Upload a valid topology file before running the assessment.')
      setStatus('No topology available.')
      return
    }

    setLoading(true)
    setError(null)
    setStatus('Running assessment...')

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
        const message = await response.text()
        throw new Error(message || 'Assessment request failed.')
      }

      const data = (await response.json()) as ResultPayload
      setResult(data)
      setStatus('Assessment complete. Results are now available in the dashboard.')
      setSelectedNode(data.graph.nodes[0] ?? null)
    } catch (caughtError) {
      const message = caughtError instanceof Error ? caughtError.message : 'Assessment could not be completed.'
      setError(message)
      setStatus('Assessment failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/80 p-6 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-cyan-300">SOC / Bayesian Risk Console</p>
            <h1 className="mt-2 text-3xl font-semibold">ICS Risk Assessment Framework</h1>
          </div>
          <div className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-4 py-2 text-sm text-cyan-200">
            Backend API: {API_BASE_URL}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-6">
        <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl shadow-slate-950/30">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-2xl font-semibold">Home</h2>
              <p className="mt-2 text-slate-300">Run a full cyber-risk assessment using the existing Bayesian inference engine.</p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200">
                <span>Preset dataset</span>
                <select
                  className="bg-slate-950 text-slate-100 outline-none"
                  value={selectedDataset}
                  onChange={(event) => void loadPresetTopology(event.target.value)}
                  aria-label="Select a predefined dataset"
                >
                  <option value="swat_example">SWAT Example</option>
                  <option value="building_automation">Building Automation</option>
                  <option value="power_substation">Power Substation</option>
                  <option value="water_treatment">Water Treatment</option>
                </select>
              </label>
              <button
                onClick={() => setStatus('Ready for topology upload.')}
                className="rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950 transition hover:bg-cyan-400"
              >
                Start Assessment
              </button>
            </div>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">Upload Topology</h2>
            <label className="mt-4 block text-sm text-slate-300" htmlFor="topology-upload">
              JSON topology file
            </label>
            <input
              id="topology-upload"
              type="file"
              accept="application/json"
              onChange={(event) => void handleFileUpload(event)}
              className="mt-2 block w-full rounded-lg border border-slate-700 bg-slate-950 p-3 text-sm"
              aria-label="Upload a topology JSON file"
            />
            <div className="mt-4 rounded-xl bg-slate-950/80 p-4 text-sm text-slate-300">
              <p>File: {uploadedFileName || 'None selected'}</p>
              <p className="mt-2">Assets: {Object.keys(topology.assets).length}</p>
              <p>Connections: {topology.relationships.length}</p>
              <p className="mt-3 text-cyan-200">{status}</p>
              {error ? <p className="mt-2 text-rose-300">{error}</p> : null}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">Evidence Selection</h2>
            <div className="mt-4 space-y-3">
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
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold">Network Viewer</h2>
              <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">Interactive topology</span>
            </div>
            <div className="h-[420px] rounded-xl bg-slate-950">
              <ReactFlowProvider>
                <ReactFlow
                  nodes={networkNodes}
                  edges={networkEdges}
                  fitView
                  fitViewOptions={{ padding: 0.2 }}
                  onNodeClick={(_, node) => setSelectedNode(String(node.id))}
                  proOptions={{ hideAttribution: true }}
                >
                  <MiniMap pannable zoomable />
                  <Controls />
                  <Background />
                </ReactFlow>
              </ReactFlowProvider>
            </div>
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
                  <span className="text-slate-400">Posterior</span>
                  <span className="font-semibold text-cyan-300">{formatProbability(selectedNodeProbability ?? 0)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Risk rank</span>
                  <span className="font-semibold text-white">{riskRanking.findIndex((entry) => entry.asset === selectedNode) + 1 || '—'}</span>
                </div>
              </div>
            ) : (
              <p className="mt-4 text-sm text-slate-400">Select a node in the network to inspect its probability details.</p>
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <h2 className="text-xl font-semibold">Run Assessment</h2>
            <div className="flex items-center gap-3">
              {loading ? <span className="text-cyan-300">Computing posterior risk...</span> : null}
              <button
                onClick={() => void runAssessment()}
                className="rounded-lg bg-emerald-500 px-4 py-2 font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:opacity-60"
                disabled={loading || !topology.assets || !Object.keys(topology.assets).length}
              >
                {loading ? 'Running...' : 'Run Assessment'}
              </button>
            </div>
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
                  </div>
                  <div className={`rounded-xl border p-4 ${getRiskTone(result.summary.risk_level)}`}>
                    <p className="text-sm">Risk Level</p>
                    <p className="mt-2 text-2xl font-semibold uppercase">{result.summary.risk_level}</p>
                  </div>
                </div>

                <div className="rounded-xl bg-slate-800 p-4">
                  <h3 className="font-semibold">Posterior probabilities</h3>
                  <div className="mt-3 space-y-2 text-sm">
                    {Object.entries(result.posteriors).map(([asset, probability]) => (
                      <div key={asset} className="flex items-center justify-between rounded-lg bg-slate-900/70 px-3 py-2">
                        <span>{asset}</span>
                        <span className="font-medium text-cyan-200">{formatProbability(probability)}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-xl bg-slate-800 p-4">
                  <h3 className="font-semibold">Top high-risk assets</h3>
                  <div className="mt-3 space-y-2 text-sm">
                    {riskRanking.map((entry) => (
                      <div key={entry.asset} className="flex items-center justify-between rounded-lg bg-slate-900/70 px-3 py-2">
                        <span>{entry.asset}</span>
                        <span className="font-medium text-rose-300">{formatProbability(entry.risk)}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-xl bg-slate-800 p-4">
                  <h3 className="font-semibold">Critical attack path</h3>
                  <p className="mt-3 text-sm text-slate-300">
                    {result.attack_paths?.length ? JSON.stringify(result.attack_paths[0]) : 'No attack path available from the current evidence.'}
                  </p>
                </div>
              </div>
            ) : (
              <p className="mt-4 text-slate-400">No assessment results available. Run the assessment to populate the dashboard.</p>
            )}
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">Risk Distribution</h2>
            <div className="mt-4 h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 24 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis
                    dataKey="asset"
                    tick={{ fill: '#e2e8f0', fontSize: 12 }}
                    angle={-24}
                    textAnchor="end"
                    height={52}
                    axisLine={{ stroke: '#64748b' }}
                    tickLine={{ stroke: '#64748b' }}
                  />
                  <YAxis
                    domain={[0, 1]}
                    tick={{ fill: '#cbd5e1', fontSize: 12 }}
                    label={{ value: 'Probability', angle: -90, position: 'insideLeft', fill: '#cbd5e1' }}
                    axisLine={{ stroke: '#64748b' }}
                    tickLine={{ stroke: '#64748b' }}
                  />
                  <Tooltip
                    formatter={(value: number) => formatProbability(value)}
                    labelStyle={{ color: '#e2e8f0' }}
                    contentStyle={{ background: '#0f172a', borderRadius: '12px', border: '1px solid rgba(56, 189, 248, 0.25)', color: '#e2e8f0' }}
                  />
                  <Legend wrapperStyle={{ color: '#e2e8f0' }} />
                  <Bar dataKey="probability" name="Posterior Probability" radius={[6, 6, 0, 0]}>
                    {chartData.map((entry) => (
                      <Cell key={entry.asset} fill={getProbabilityColor(entry.probability)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">Risk Ranking</h2>
            <div className="mt-4 h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={58}
                    outerRadius={96}
                    paddingAngle={3}
                    label={({ name, percent }) => `${name}: ${(percent ?? 0) * 100}%`}
                    labelLine={false}
                  >
                    <Cell fill="#fb7185" />
                    <Cell fill="#f59e0b" />
                    <Cell fill="#38bdf8" />
                    <Cell fill="#34d399" />
                  </Pie>
                  <Tooltip
                    formatter={(value: number) => [`${value} assets`, 'Count']}
                    contentStyle={{ background: '#0f172a', border: '1px solid rgba(56, 189, 248, 0.25)', color: '#e2e8f0' }}
                  />
                  <Legend wrapperStyle={{ color: '#e2e8f0' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">Bayesian Results</h2>
            <div className="mt-4 rounded-xl bg-slate-950/80 p-4 text-sm">
              {result ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Evidence used</span>
                    <span className="font-semibold text-white">{JSON.stringify(result.evidence_used)}</span>
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
          <h2 className="text-xl font-semibold">Reports</h2>
          <div className="mt-4 flex flex-wrap gap-3">
            <a className="rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950 transition hover:bg-cyan-400" href={`${API_BASE_URL}/reports/summary.txt`} download>
              Summary Report
            </a>
            <a className="rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950 transition hover:bg-cyan-400" href={`${API_BASE_URL}/reports/risk_table.csv`} download>
              CSV Risk Table
            </a>
            <a className="rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950 transition hover:bg-cyan-400" href={`${API_BASE_URL}/reports/posteriors.json`} download>
              Posterior JSON
            </a>
            <a className="rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950 transition hover:bg-cyan-400" href={`${API_BASE_URL}/reports/assessment.pdf`} download>
              Assessment PDF
            </a>
          </div>
        </section>
      </main>
    </div>
  )
}
