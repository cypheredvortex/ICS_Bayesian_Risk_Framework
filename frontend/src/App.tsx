import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { AssetState } from './types'
import type {
  TopologyPayload,
  ResultPayload,
  CoreSettings,
  ToastItem,
} from './types'
import {
  API_BASE_URL,
  defaultTopology,
  defaultCoreSettings,
} from './constants'
import { parseErrorDetail } from './utils'
import Toasts from './components/Toasts'
import ConfirmDialog from './components/ConfirmDialog'
import Header from './components/Header'
import SettingsPanel from './components/SettingsPanel'
import TopologySection from './components/TopologySection'
import EvidencePanel from './components/EvidencePanel'
import NetworkViewer from './components/NetworkViewer'
import NodeDetails from './components/NodeDetails'
import ResultsDashboard from './components/ResultsDashboard'
import ProbabilityChart from './components/ProbabilityChart'
import RiskPieChart from './components/RiskPieChart'
import BayesianResults from './components/BayesianResults'
import CptSection from './components/CptSection'
import ReportsSection from './components/ReportsSection'

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
  const [serverSettings, setServerSettings] =
    useState<CoreSettings>(defaultCoreSettings)
  const [draftSettings, setDraftSettings] =
    useState<CoreSettings>(defaultCoreSettings)
  const [settingsLoading, setSettingsLoading] = useState(false)
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const searchInputRef = useRef<HTMLInputElement>(null)
  const toastCounter = useRef(0)

  const pushToast = useCallback(
    (message: string, tone: ToastItem['tone'] = 'info') => {
      toastCounter.current += 1
      const id = toastCounter.current
      setToasts((current) => [...current, { id, message, tone }])
      window.setTimeout(() => {
        setToasts((current) => current.filter((toast) => toast.id !== id))
      }, 5000)
    },
    [],
  )

  const dismissToast = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  // Settings live server-side (GET/PUT /settings), independent of any one
  // analysis run, so pull the current values in on mount.
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/settings`)
        if (!response.ok)
          throw new Error(await parseErrorDetail(response, 'Could not load settings.'))
        const data = (await response.json()) as Record<string, unknown>
        const merged: CoreSettings = {
          cvss_weight: Number(
            data.cvss_weight ?? defaultCoreSettings.cvss_weight,
          ),
          exposure_weight: Number(
            data.exposure_weight ?? defaultCoreSettings.exposure_weight,
          ),
          patch_weight: Number(
            data.patch_weight ?? defaultCoreSettings.patch_weight,
          ),
          impact_weight: Number(
            data.impact_weight ?? defaultCoreSettings.impact_weight,
          ),
          propagation_weights: {
            ...defaultCoreSettings.propagation_weights,
            ...(data.propagation_weights as Record<string, number> | undefined),
          },
          firewall_multipliers: {
            true: Number(
              (
                data.firewall_multipliers as Record<string, number> | undefined
              )?.true ?? defaultCoreSettings.firewall_multipliers.true,
            ),
            false: Number(
              (
                data.firewall_multipliers as Record<string, number> | undefined
              )?.false ?? defaultCoreSettings.firewall_multipliers.false,
            ),
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
      const typing =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT'
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

  const assets = useMemo(
    () => Object.entries(topology.assets),
    [topology.assets],
  )

  const nodeIds = useMemo(() => {
    if (result?.graph?.nodes?.length)
      return result.graph.nodes.map((node) => node.id)
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

  const isEvidenceNode = useCallback(
    (id: string) =>
      Boolean(result?.evidence_used && id in result.evidence_used),
    [result],
  )

  const chartData = useMemo(() => {
    return nodeIds
      .filter((id) => combinedProbabilities.has(id))
      .map((id) => ({
        asset: id,
        probability: Number(combinedProbabilities.get(id)),
        pinned: isEvidenceNode(id),
      }))
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
    return topology.relationships.map(
      ([source, target, relType, firewalled]) => ({
        source,
        target,
        label: `${relType}${firewalled ? ' (firewalled)' : ''}`,
      }),
    )
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

  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0]
    if (!file) return

    const supported = /\.(json|ya?ml|csv)$/i.test(file.name)
    if (!supported) {
      pushToast(
        'Unsupported file type. Upload a .json, .yaml/.yml, or .csv topology file.',
        'error',
      )
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
        throw new Error(
          await parseErrorDetail(response, 'Topology file upload failed.'),
        )
      }
      const data = (await response.json()) as {
        topology: TopologyPayload
        asset_count: number
        relationship_count: number
      }
      applyTopology(data.topology, file.name)
      pushToast(
        `Loaded ${file.name}: ${data.asset_count} assets, ${data.relationship_count} relationships.`,
        'success',
      )
    } catch (caughtError) {
      pushToast(
        caughtError instanceof Error ? caughtError.message : 'Invalid topology file.',
        'error',
      )
    } finally {
      event.target.value = ''
    }
  }

  const hasUnsavedEvidence = Object.keys(evidence).some(
    (key) => evidence[key] !== 'Unknown',
  )

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
        throw new Error(
          await parseErrorDetail(response, 'Preset dataset could not be loaded.'),
        )
      }
      const dataset = (await response.json()) as TopologyPayload
      if (!dataset.assets || !dataset.relationships) {
        throw new Error('Preset dataset payload is invalid.')
      }
      applyTopology(dataset, `${datasetName}.json`)
      await persistTopology(dataset)
      pushToast(
        `${datasetName.replace(/_/g, ' ')} preset loaded successfully.`,
        'success',
      )
    } catch (caughtError) {
      pushToast(
        caughtError instanceof Error
          ? caughtError.message
          : 'Failed to load the preset dataset.',
        'error',
      )
    }
  }

  const updateEvidence = (asset: string, state: AssetState) => {
    setEvidence((current) => ({ ...current, [asset]: state }))
  }

  const runAssessment = async () => {
    if (!topology.assets || !Object.keys(topology.assets).length) {
      pushToast(
        'Upload a valid topology file before running the assessment.',
        'error',
      )
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
        throw new Error(
          await parseErrorDetail(response, 'Assessment request failed.'),
        )
      }
      const data = (await response.json()) as ResultPayload
      setResult(data)
      setSelectedNode(data.graph.nodes[0]?.id ?? null)
      pushToast(
        'Assessment complete — results are now on the dashboard.',
        'success',
      )
    } catch (caughtError) {
      pushToast(
        caughtError instanceof Error
          ? caughtError.message
          : 'Assessment could not be completed.',
        'error',
      )
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
        throw new Error(
          await parseErrorDetail(response, 'Could not save settings.'),
        )
      }
      const data = (await response.json()) as Record<string, unknown>
      const merged: CoreSettings = {
        ...draftSettings,
        cvss_weight: Number(
          data.cvss_weight ?? draftSettings.cvss_weight,
        ),
        exposure_weight: Number(
          data.exposure_weight ?? draftSettings.exposure_weight,
        ),
        patch_weight: Number(
          data.patch_weight ?? draftSettings.patch_weight,
        ),
        impact_weight: Number(
          data.impact_weight ?? draftSettings.impact_weight,
        ),
      }
      setServerSettings(merged)
      setDraftSettings(merged)
      pushToast(
        'Settings saved. They apply to the next assessment you run.',
        'success',
      )
    } catch (caughtError) {
      pushToast(
        caughtError instanceof Error
          ? caughtError.message
          : 'Could not save settings.',
        'error',
      )
    } finally {
      setSettingsLoading(false)
    }
  }

  const resetSettings = async () => {
    setSettingsLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/settings/reset`, {
        method: 'POST',
      })
      if (!response.ok) {
        throw new Error(
          await parseErrorDetail(response, 'Could not reset settings.'),
        )
      }
      const data = (await response.json()) as Record<string, unknown>
      const merged: CoreSettings = {
        cvss_weight: Number(
          data.cvss_weight ?? defaultCoreSettings.cvss_weight,
        ),
        exposure_weight: Number(
          data.exposure_weight ?? defaultCoreSettings.exposure_weight,
        ),
        patch_weight: Number(
          data.patch_weight ?? defaultCoreSettings.patch_weight,
        ),
        impact_weight: Number(
          data.impact_weight ?? defaultCoreSettings.impact_weight,
        ),
        propagation_weights: {
          ...defaultCoreSettings.propagation_weights,
          ...(data.propagation_weights as Record<string, number> | undefined),
        },
        firewall_multipliers: {
          true: Number(
            (
              data.firewall_multipliers as Record<string, number> | undefined
            )?.true ?? defaultCoreSettings.firewall_multipliers.true,
          ),
          false: Number(
            (
              data.firewall_multipliers as Record<string, number> | undefined
            )?.false ?? defaultCoreSettings.firewall_multipliers.false,
          ),
        },
      }
      setServerSettings(merged)
      setDraftSettings(merged)
      pushToast('Settings reset to framework defaults.', 'success')
    } catch (caughtError) {
      pushToast(
        caughtError instanceof Error
          ? caughtError.message
          : 'Could not reset settings.',
        'error',
      )
    } finally {
      setSettingsLoading(false)
    }
  }

  const settingsDirty =
    JSON.stringify(serverSettings) !== JSON.stringify(draftSettings)

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Toasts items={toasts} onDismiss={dismissToast} />

      <ConfirmDialog
        pendingDataset={pendingDataset}
        onCancel={() => setPendingDataset(null)}
        onConfirm={() => void loadPresetTopology(pendingDataset!)}
      />

      <Header
        settingsButton={
          <button
            onClick={() => setSettingsOpen((open) => !open)}
            className="rounded-full border border-slate-700 bg-slate-950 px-4 py-2 text-sm text-slate-200 hover:border-cyan-500/50 hover:text-cyan-200"
            aria-expanded={settingsOpen}
          >
            Settings {settingsDirty ? '•' : ''}
          </button>
        }
        apiIndicator={
          <div className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-4 py-2 text-sm text-cyan-200">
            Backend API: {API_BASE_URL}
          </div>
        }
      >
        {settingsOpen ? (
          <SettingsPanel
            draftSettings={draftSettings}
            settingsDirty={settingsDirty}
            settingsLoading={settingsLoading}
            onUpdate={(updater) =>
              setDraftSettings((current) => updater(current))
            }
            onSave={() => void saveSettings()}
            onReset={() => void resetSettings()}
          />
        ) : null}
      </Header>

      <main className="mx-auto max-w-7xl space-y-6 p-6">
        <TopologySection
          selectedDataset={selectedDataset}
          uploadedFileName={uploadedFileName}
          assetCount={Object.keys(topology.assets).length}
          relationshipCount={topology.relationships.length}
          loading={loading}
          hasAssets={Object.keys(topology.assets).length > 0}
          onDatasetChange={requestPresetChange}
          onFileUpload={handleFileUpload}
          onRunAssessment={() => void runAssessment()}
        />

        <EvidencePanel
          assets={assets}
          evidence={evidence}
          onUpdateEvidence={updateEvidence}
        />

        <section className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
          <NetworkViewer
            ref={searchInputRef}
            nodeIds={nodeIds}
            nodeKindMap={nodeKindMap}
            edgeList={edgeList}
            combinedProbabilities={combinedProbabilities}
            isEvidenceNode={isEvidenceNode}
            selectedNode={selectedNode}
            colorMode={colorMode}
            matchingNodes={matchingNodes}
            neighborSet={neighborSet}
            attackPathNodes={attackPathNodes}
            showAttackPath={showAttackPath}
            attackPathEdgeKeys={attackPathEdgeKeys}
            setSelectedNode={setSelectedNode}
            onSearchChange={setNodeQuery}
            onColorModeChange={setColorMode}
            onAttackPathToggle={() => setShowAttackPath((v) => !v)}
          />

          <NodeDetails
            selectedNode={selectedNode}
            nodeKindMap={nodeKindMap}
            combinedProbabilities={combinedProbabilities}
            isEvidenceNode={isEvidenceNode}
            result={result}
            riskRanking={riskRanking}
            attackPathNodes={attackPathNodes}
          />
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          {result ? (
            <ResultsDashboard
              result={result}
              chartData={chartData}
              riskRanking={riskRanking}
              setSelectedNode={setSelectedNode}
            />
          ) : (
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
              <h2 className="text-xl font-semibold">Results Dashboard</h2>
              <p className="mt-4 text-slate-400">
                No assessment results yet. Load a topology, optionally mark
                evidence, then run the assessment.
              </p>
            </div>
          )}

          <ProbabilityChart
            chartData={chartData}
            setSelectedNode={setSelectedNode}
          />
        </section>

        <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <RiskPieChart pieData={pieData} />
          <BayesianResults result={result} />
        </section>

        <CptSection
          result={result}
          cptQuery={cptQuery}
          onCptQueryChange={setCptQuery}
        />

        <ReportsSection />
      </main>
    </div>
  )
}

