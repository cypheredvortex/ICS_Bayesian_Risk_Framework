import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { AssetState, TopologyReviewInfo, TopologyUploadResult } from './types'
import type {
  TopologyPayload,
  ResultPayload,
  CoreSettings,
  ToastItem,
} from './types'
import {
  API_BASE_URL,
  TOPOLOGY_ACCEPT,
  TOPOLOGY_ACCEPT_RE,
  defaultTopology,
  defaultCoreSettings,
  topologyFormats,
} from './constants'
import { deriveTopologySummary, parseErrorBody, parseErrorDetail, riskLevelFor } from './utils'
import type { RiskThresholds } from './types'
import Toasts from './components/Toasts'
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
import { Card } from './components/ui'

// Merge the server-side settings payload into a complete CoreSettings,
// falling back to framework defaults for any key the API does not return.
// This keeps the frontend free of its own copies of cvss parameters and
// risk thresholds: whatever the backend says is authoritative.
function mergeSettingsFromApi(data: Record<string, unknown>): CoreSettings {
  const logistic = (data.cvss_logistic_params as
    | { k?: number; x0?: number }
    | undefined) ?? {}
  const thresholds = (data.risk_thresholds as
    | Partial<RiskThresholds>
    | undefined) ?? {}
  return {
    exposure_weight: Number(
      data.exposure_weight ?? defaultCoreSettings.exposure_weight,
    ),
    patch_weight: Number(
      data.patch_weight ?? defaultCoreSettings.patch_weight,
    ),
    impact_weight: Number(
      data.impact_weight ?? defaultCoreSettings.impact_weight,
    ),
    cvss_mapping:
      data.cvss_mapping === 'linear' ? 'linear' : 'logistic',
    cvss_logistic_params: {
      k: Number(logistic.k ?? defaultCoreSettings.cvss_logistic_params.k),
      x0: Number(logistic.x0 ?? defaultCoreSettings.cvss_logistic_params.x0),
    },
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
    risk_thresholds: {
      critical: Number(
        thresholds.critical ?? defaultCoreSettings.risk_thresholds.critical,
      ),
      high: Number(
        thresholds.high ?? defaultCoreSettings.risk_thresholds.high,
      ),
      moderate: Number(
        thresholds.moderate ?? defaultCoreSettings.risk_thresholds.moderate,
      ),
    },
  }
}

function formatLabelFor(fileName: string): string {
  const extension = '.' + (fileName.split('.').pop()?.toLowerCase() ?? '')
  for (const fmt of topologyFormats) {
    if (fmt.ext.toLowerCase().split(' / ').includes(extension)) {
      // Return the single extension when the family has several (e.g.
      // '.json' instead of 'JSON / YAML') so the badge stays precise.
      const single = fmt.label
        .split(' / ')
        .find((part) => part.toLowerCase() === extension)
      return single ?? fmt.label
    }
  }
  return extension.slice(1).toUpperCase()
}

export default function App() {
  const [topology, setTopology] = useState<TopologyPayload>(defaultTopology)
  const [evidence, setEvidence] = useState<Record<string, AssetState>>({})
  const [result, setResult] = useState<ResultPayload | null>(null)
  const [uploadedFileName, setUploadedFileName] = useState('')
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

  // Topology Assessment workspace state
  const [review, setReview] = useState<TopologyReviewInfo | null>(null)
  const [parsing, setParsing] = useState(false)
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)

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
        const merged: CoreSettings = mergeSettingsFromApi(data)
        setServerSettings(merged)
        setDraftSettings(merged)
      } catch {
        // Backend may not be reachable yet on first paint; sliders keep
        // sensible defaults and Save will surface the real error.
      }
    }
    void loadSettings()
  }, [])

  // Lightweight API reachability check (polled) for the header status pill.
  useEffect(() => {
    let cancelled = false
    const check = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/`)
        if (!cancelled) setApiOnline(response.ok)
      } catch {
        if (!cancelled) setApiOnline(false)
      }
    }
    void check()
    const interval = window.setInterval(check, 30_000)
    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
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
      severity: Number(item.severity ?? 0),
      impact: Number(item.impact ?? 0),
    }))
  }, [result])

  const edgeList = useMemo(() => {
    if (result?.graph?.edges?.length) {
      return result.graph.edges.map((edge) => ({
        source: edge.source,
        target: edge.target,
        label: `${edge.rel_type}${edge.firewalled ? ' 🔒' : ''}${typeof edge.weight === 'number' ? ` w=${edge.weight.toFixed(2)}` : ''}`,
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

  // Active risk thresholds come from the backend (serverSettings). The
  // risk index is P(compromised) x normalised consequence impact, bounded
  // ~[0, 1.4]; the exact class boundaries are whatever the backend uses.
  const riskThresholds = serverSettings.risk_thresholds

  const pieData = useMemo(() => {
    const counts = { critical: 0, high: 0, moderate: 0, low: 0 }
    for (const item of result?.risk_scores ?? []) {
      const risk = Number(item.risk ?? 0)
      counts[riskLevelFor(risk, riskThresholds)] += 1
    }
    return Object.entries(counts).map(([name, value]) => ({ name, value }))
  }, [result, riskThresholds])

  // Clear everything derived from an analysis so no stale assessment,
  // selection or evidence outlives the topology that produced it.
  const resetDerivedState = () => {
    setResult(null)
    setSelectedNode(null)
    setEvidence({})
  }

  const applyTopology = (
    parsed: TopologyPayload,
    sourceName: string,
    reviewInfo: TopologyReviewInfo,
  ) => {
    setReview(reviewInfo)
    setUploadedFileName(sourceName)
    setTopology(parsed)
    resetDerivedState()
  }

  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Support the full set of backend-supported topology formats
    if (!TOPOLOGY_ACCEPT_RE.test(file.name)) {
      pushToast(
        'Unsupported file type. Upload a .json, .yaml/.yml, .csv, .xlsx, .graphml, .xml, .aml, .vsdx, or .vdx topology file.',
        'error',
      )
      event.target.value = ''
      return
    }

    setParsing(true)
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
      const data = (await response.json()) as TopologyUploadResult
      const summary = data.summary ?? deriveTopologySummary(data.topology)
      applyTopology(data.topology, file.name, {
        fileName: file.name,
        fileSize: file.size,
        formatLabel: formatLabelFor(file.name),
        assetCount: data.asset_count,
        relationshipCount: data.relationship_count,
        warnings: data.warnings ?? [],
        summary,
        source: 'upload',
      })
      pushToast(
        `Loaded ${file.name}: ${data.asset_count} assets, ${data.relationship_count} relationships.`,
        'success',
      )
      // Surface non-destructive normalization notices (self-loops removed,
      // duplicate edges collapsed, unidentifiable records skipped) so input
      // changes are never silent.
      if (data.warnings?.length) {
        pushToast(
          `Topology note: ${data.warnings.slice(0, 2).join(' ')}`,
          'info',
        )
      }
    } catch (caughtError) {
      pushToast(
        caughtError instanceof Error ? caughtError.message : 'Invalid topology file.',
        'error',
      )
    } finally {
      setParsing(false)
      event.target.value = ''
    }
  }

  const removeTopology = () => {
    // Returning to the empty state clears everything derived from the
    // previous topology: review/validation data, results and evidence.
    setReview(null)
    setUploadedFileName('')
    setTopology(defaultTopology)
    resetDerivedState()
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
        // Impossible/contradictory evidence must be surfaced as a clear
        // diagnostic, never as a silent all-zero result.
        const { message, errorCode, affectedNodes } = await parseErrorBody(
          response,
          'Assessment request failed.',
        )
        if (errorCode === 'IMPOSSIBLE_EVIDENCE') {
          const nodes = affectedNodes?.length
            ? ` Affected nodes: ${affectedNodes.join(', ')}.`
            : ''
          pushToast(`Impossible evidence detected. ${message}${nodes}`, 'error')
        } else {
          pushToast(message, 'error')
        }
        return
      }
      const data = (await response.json()) as ResultPayload
      setResult(data)
      setSelectedNode(data.graph.nodes[0]?.id ?? null)
      // Surface non-destructive topology warnings so input changes are never
      // silent.
      const warnings = data.summary?.topology_warnings ?? []
      if (warnings.length) {
        pushToast(
          `Topology note: ${warnings.slice(0, 2).join(' ')}`,
          'info',
        )
      }
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
      const merged: CoreSettings = mergeSettingsFromApi(data)
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
      const merged: CoreSettings = mergeSettingsFromApi(data)
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
    <div className="min-h-screen text-slate-100">
      <Toasts items={toasts} onDismiss={dismissToast} />

      <Header
        settingsButton={
          <button
            onClick={() => setSettingsOpen((open) => !open)}
            className="btn btn-secondary btn-sm"
            aria-expanded={settingsOpen}
          >
            <svg
              className="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M12 15a3 3 0 100-6 3 3 0 000 6z" />
              <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 110 4h-.09a1.65 1.65 0 00-1.51 1z" />
            </svg>
            Settings {settingsDirty ? '•' : ''}
          </button>
        }
        apiOnline={apiOnline}
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

      <main className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6">
        <TopologySection
          uploadedFileName={uploadedFileName}
          review={review}
          parsing={parsing}
          apiOnline={apiOnline}
          loading={loading}
          hasAssets={Object.keys(topology.assets).length > 0}
          onFileUpload={handleFileUpload}
          onRemoveTopology={removeTopology}
          onRunAssessment={() => void runAssessment()}
          // Restrict the file picker to the formats the backend truly supports
          accept={TOPOLOGY_ACCEPT}
        />

        <EvidencePanel
          assets={assets}
          evidence={evidence}
          onUpdateEvidence={updateEvidence}
        />

        <section className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
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
            edgeList={edgeList}
          />
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          {result ? (
            <ResultsDashboard
              result={result}
              chartData={chartData}
              riskRanking={riskRanking}
              thresholds={serverSettings.risk_thresholds}
              setSelectedNode={setSelectedNode}
            />
          ) : (
            <Card>
              <h2 className="card-title">Results Dashboard</h2>
              <p className="card-subtitle">
                No assessment results yet. Load a topology, optionally mark
                evidence, then run the assessment.
              </p>
            </Card>
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

        <ReportsSection available={Boolean(result)} />
      </main>
    </div>
  )
}
