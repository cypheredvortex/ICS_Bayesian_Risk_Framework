import { forwardRef, useMemo } from 'react'
import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
  type NodeProps,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { kindColors, kindMeta } from '../constants'
import { getProbabilityColor, computeLayeredPositions, formatProbability } from '../utils'
import { EmptyState } from './ui'

type NetworkNodeData = {
  label: string
  kind: string
  probability: number
  pinned: boolean
  dimmed: boolean
  onPath: boolean
  colorMode: 'risk' | 'kind'
}

function NetworkNode({ data, selected }: NodeProps<Node<NetworkNodeData>>) {
  const baseColor =
    data.colorMode === 'kind'
      ? (kindColors[data.kind] ?? '#94a3b8')
      : getProbabilityColor(data.probability)
  const kindLabel = kindMeta[data.kind]?.label ?? data.kind

  const borderClass = selected
    ? 'border-white shadow-[0_0_0_4px_rgba(34,211,238,0.25)]'
    : data.onPath
      ? 'border-rose-400 shadow-[0_0_0_4px_rgba(251,113,133,0.15)]'
      : data.pinned
        ? 'border-slate-950 border-dashed'
        : 'border-white/15'

  return (
    <div
      className="w-[184px] transition-opacity duration-150"
      style={{ opacity: data.dimmed ? 0.22 : 1 }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: '#334155', width: 9, height: 9, border: '2px solid #020617' }}
      />
      <div
        className={`overflow-hidden rounded-xl border-2 ${borderClass} shadow-lg shadow-slate-950/50`}
        style={{ background: baseColor }}
      >
        <div className="px-3 pt-2 pb-1.5">
          <div className="flex items-start justify-between gap-2">
            <span className="truncate font-mono text-[13px] font-bold leading-tight text-slate-950">
              {data.label}
            </span>
            {data.pinned ? (
              <span
                className="shrink-0 text-[11px]"
                title="Pinned by evidence"
                aria-label={`${data.label} pinned by evidence`}
              >
                📌
              </span>
            ) : null}
          </div>
          <div className="mt-1.5 flex items-center justify-between gap-2">
            <span className="truncate text-[10px] font-semibold uppercase tracking-wider text-slate-900/70">
              {kindLabel}
            </span>
            <span className="rounded-md bg-slate-950/70 px-1.5 py-0.5 font-mono text-[11px] font-bold text-white">
              {formatProbability(data.probability)}
            </span>
          </div>
        </div>
      </div>
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: '#334155', width: 9, height: 9, border: '2px solid #020617' }}
      />
    </div>
  )
}

const nodeTypes = { network: NetworkNode }

const NetworkViewer = forwardRef<
  HTMLInputElement,
  {
    nodeIds: string[]
    nodeKindMap: Map<string, string>
    edgeList: Array<{ source: string; target: string; label: string }>
    combinedProbabilities: Map<string, number>
    isEvidenceNode: (id: string) => boolean
    selectedNode: string | null
    colorMode: 'risk' | 'kind'
    matchingNodes: Set<string> | null
    neighborSet: Set<string> | null
    attackPathNodes: Set<string>
    showAttackPath: boolean
    attackPathEdgeKeys: Set<string>
    setSelectedNode: (id: string | null) => void
    onSearchChange: (value: string) => void
    onColorModeChange: (mode: 'risk' | 'kind') => void
    onAttackPathToggle: () => void
  }
>(function NetworkViewer(
  {
    nodeIds,
    nodeKindMap,
    edgeList,
    combinedProbabilities,
    isEvidenceNode,
    selectedNode,
    colorMode,
    matchingNodes,
    neighborSet,
    attackPathNodes,
    showAttackPath,
    attackPathEdgeKeys,
    setSelectedNode,
    onSearchChange,
    onColorModeChange,
    onAttackPathToggle,
  },
  searchInputRef,
) {
  const nodePositions = useMemo(
    () => computeLayeredPositions(nodeIds, edgeList),
    [nodeIds, edgeList],
  )

  const networkNodes = useMemo<Node[]>(() => {
    return nodeIds.map((nodeId) => {
      const probability = combinedProbabilities.get(nodeId) ?? 0
      const kind = nodeKindMap.get(nodeId) ?? 'device'
      const dimmed = Boolean(
        (matchingNodes && !matchingNodes.has(nodeId)) ||
          (neighborSet && !neighborSet.has(nodeId)),
      )
      const onPath = attackPathNodes.has(nodeId)
      const position = nodePositions.get(nodeId) ?? { x: 0, y: 0 }

      return {
        id: nodeId,
        type: 'network',
        data: {
          label: nodeId,
          kind,
          probability,
          pinned: isEvidenceNode(nodeId),
          dimmed,
          onPath,
          colorMode,
        } satisfies NetworkNodeData,
        position,
      }
    })
  }, [
    nodeIds,
    combinedProbabilities,
    nodeKindMap,
    colorMode,
    matchingNodes,
    neighborSet,
    attackPathNodes,
    nodePositions,
    isEvidenceNode,
  ])

  const networkEdges = useMemo<Edge[]>(() => {
    return edgeList.map(({ source, target, label }, index) => {
      const onPath =
        showAttackPath && attackPathEdgeKeys.has(`${source}->${target}`)
      const dimmed = neighborSet
        ? !(neighborSet.has(source) && neighborSet.has(target))
        : false
      return {
        id: `${source}-${target}-${index}`,
        source,
        target,
        label,
        type: 'smoothstep',
        animated: onPath,
        style: {
          stroke: onPath ? '#fb7185' : '#64748b',
          strokeWidth: onPath ? 2.5 : 1.4,
          opacity: dimmed ? 0.12 : 1,
        },
        labelStyle: { fill: '#cbd5e1', fontSize: 10, fontWeight: 600 },
        labelBgStyle: { fill: '#0f172a', fillOpacity: 0.9 },
        markerEnd: {
          type: 'arrowclosed',
          color: onPath ? '#fb7185' : '#64748b',
        },
      }
    })
  }, [edgeList, showAttackPath, attackPathEdgeKeys, neighborSet])

  const legendSwatches =
    colorMode === 'risk'
      ? [
          ['#34d399', 'Low (< 0.20)'],
          ['#38bdf8', '0.20 – 0.45'],
          ['#f59e0b', '0.45 – 0.70'],
          ['#fb7185', 'High (≥ 0.70)'],
        ]
      : Object.entries(kindMeta).map(([kind, meta]) => [
          meta.hex,
          meta.label,
        ])

  return (
    <div className="card card-pad">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="card-title">Network Viewer</h2>
          <p className="card-subtitle">
            The Bayesian influence diagram derived from the topology. Select an
            asset to inspect its analytical detail.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            ref={searchInputRef}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Search nodes… ( / )"
            className="field field-sm w-44"
            aria-label="Search nodes"
          />
          <div
            className="flex overflow-hidden rounded-lg border border-slate-700"
            role="group"
            aria-label="Color mode"
          >
            <button
              onClick={() => onColorModeChange('risk')}
              className={`px-2.5 py-1.5 text-xs font-semibold transition ${
                colorMode === 'risk'
                  ? 'bg-cyan-500 text-slate-950'
                  : 'bg-slate-950 text-slate-300 hover:text-slate-100'
              }`}
            >
              By risk
            </button>
            <button
              onClick={() => onColorModeChange('kind')}
              className={`px-2.5 py-1.5 text-xs font-semibold transition ${
                colorMode === 'kind'
                  ? 'bg-cyan-500 text-slate-950'
                  : 'bg-slate-950 text-slate-300 hover:text-slate-100'
              }`}
            >
              By asset type
            </button>
          </div>
          <button
            onClick={onAttackPathToggle}
            className={`rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition ${
              showAttackPath
                ? 'border-rose-400/60 bg-rose-500/10 text-rose-200'
                : 'border-slate-700 bg-slate-950 text-slate-300 hover:text-slate-100'
            }`}
            aria-pressed={showAttackPath}
          >
            Attack path
          </button>
        </div>
      </div>

      <div className="h-[460px] overflow-hidden rounded-xl border border-slate-800 bg-slate-950">
        {nodeIds.length ? (
          <ReactFlowProvider>
            <ReactFlow
              nodes={networkNodes}
              edges={networkEdges}
              nodeTypes={nodeTypes}
              fitView
              fitViewOptions={{ padding: 0.2 }}
              minZoom={0.2}
              maxZoom={1.8}
              onNodeClick={(_, node) => setSelectedNode(String(node.id))}
              onPaneClick={() => setSelectedNode(null)}
              proOptions={{ hideAttribution: true }}
              colorMode="dark"
            >
              <MiniMap pannable zoomable nodeStrokeWidth={3} />
              <Controls showInteractive={false} />
              <Background gap={24} size={1.2} />
            </ReactFlow>
          </ReactFlowProvider>
        ) : (
          <EmptyState
            title="No topology to display yet"
            hint="Upload a topology file to populate the network."
          />
        )}
      </div>

      {/* Legend */}
      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-slate-400">
        <span className="flex items-center gap-1.5">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            {colorMode === 'risk' ? 'Posterior probability' : 'Asset type'}:
          </span>
          {legendSwatches.map(([color, label]) => (
            <span key={label} className="flex items-center gap-1">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: color }}
              />
              {label}
            </span>
          ))}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="text-slate-500">📌</span> evidence-pinned
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-4 rounded bg-rose-400" /> attack
          path
        </span>
        <span className="flex items-center gap-1.5">
          <span className="text-slate-500">🔒</span> firewalled link
        </span>
      </div>

      <details className="details-card mt-3">
        <summary className="details-summary">
          How to read this network
        </summary>
        <div className="border-t border-slate-800 px-4 py-3 text-xs leading-relaxed text-slate-400">
          <p>
            Edge labels show the relationship type and its{' '}
            <strong className="text-slate-300">
              Noisy-OR causal weight w
            </strong>{' '}
            — a modelling parameter, not a conditional probability. For one
            active parent, P(target = 1 | parent = 1) = 1 − (1 − leak)·(1 − w).
          </p>
          <p className="mt-2">
            An attack path is a calculated sequence of directed links from a
            likely entry point to a high-risk asset; it prioritises
            investigation and is not proof that an attack occurred.
            {showAttackPath && attackPathNodes.size
              ? ' The rose outline shows the highest-scoring calculated path in this assessment.'
              : ''}
          </p>
        </div>
      </details>
    </div>
  )
})

export default NetworkViewer
