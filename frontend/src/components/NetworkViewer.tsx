import { forwardRef, useMemo } from 'react'
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
import { kindColors } from '../constants'
import { getProbabilityColor, computeLayeredPositions } from '../utils'

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
      const baseColor =
        colorMode === 'kind'
          ? (kindColors[kind] ?? '#94a3b8')
          : getProbabilityColor(probability)
      const dimmed =
        (matchingNodes && !matchingNodes.has(nodeId)) ||
        (neighborSet && !neighborSet.has(nodeId))
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
          boxShadow:
            selectedNode === nodeId
              ? '0 0 0 4px rgba(34,211,238,0.25)'
              : 'none',
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
          strokeWidth: onPath ? 2.5 : 1.5,
          opacity: dimmed ? 0.15 : 1,
        },
        labelStyle: { fill: '#cbd5e1', fontSize: 11 },
        labelBgStyle: { fill: '#0f172a', fillOpacity: 0.85 },
        markerEnd: {
          type: 'arrowclosed',
          color: onPath ? '#fb7185' : '#64748b',
        },
      }
    })
  }, [edgeList, showAttackPath, attackPathEdgeKeys, neighborSet])

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-semibold">Network Viewer</h2>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <input
            ref={searchInputRef}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Search nodes… ( / )"
            className="w-40 rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-slate-100 outline-none focus:border-cyan-500"
            aria-label="Search nodes"
          />
          <div
            className="flex overflow-hidden rounded-md border border-slate-700"
            role="group"
            aria-label="Color mode"
          >
            <button
              onClick={() => onColorModeChange('risk')}
              className={`px-2 py-1.5 ${
                colorMode === 'risk'
                  ? 'bg-cyan-500 text-slate-950'
                  : 'bg-slate-950 text-slate-300'
              }`}
            >
              By risk
            </button>
            <button
              onClick={() => onColorModeChange('kind')}
              className={`px-2 py-1.5 ${
                colorMode === 'kind'
                  ? 'bg-cyan-500 text-slate-950'
                  : 'bg-slate-950 text-slate-300'
              }`}
            >
              By asset type
            </button>
          </div>
          <button
            onClick={onAttackPathToggle}
            className={`rounded-md border px-2 py-1.5 ${
              showAttackPath
                ? 'border-rose-400/60 bg-rose-500/10 text-rose-200'
                : 'border-slate-700 bg-slate-950 text-slate-300'
            }`}
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
          <div className="flex h-full items-center justify-center text-sm text-slate-500">
            No topology to display yet — upload a file or load a preset.
          </div>
        )}
      </div>
      <p className="mt-2 text-xs text-slate-500">
        Colors:{' '}
        {colorMode === 'risk'
          ? 'blue (lower posterior probability) → amber → rose (higher posterior probability)'
          : 'purple = human, blue = device, amber = physical process'}. 📌
        marks evidence-pinned assets. An attack path is a calculated sequence of
        directed links from a likely entry point to a high-risk asset; it is not
        proof that an attack occurred.
        {showAttackPath && attackPathNodes.size
          ? ' The rose outline shows the highest-scoring calculated path in this assessment.'
          : ''}
      </p>
    </div>
  )
})

export default NetworkViewer

