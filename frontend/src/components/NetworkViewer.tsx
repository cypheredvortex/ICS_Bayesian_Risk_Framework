import { forwardRef, useEffect, useMemo, useRef, useState } from 'react'
import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  kindColors,
  kindMeta,
  purdueLevelMeta,
  relationshipColors,
  RELATIONSHIP_FALLBACK_COLOR,
  UNZONED_META,
} from '../constants'
import {
  getProbabilityColor,
  computeLayeredPositions,
  computeZonedPositions,
  orderZonesByPurdue,
  relationshipColor,
  formatProbability,
} from '../utils'
import type { ResultPayload } from '../types'
import { EmptyState } from './ui'
import BayesianResults from './BayesianResults'

type NetworkNodeData = {
  label: string
  kind: string
  probability: number
  pinned: boolean
  dimmed: boolean
  onPath: boolean
  colorMode: 'risk' | 'kind'
  // Zone / Purdue chips shown on the node card so the segmentation is
  // readable directly on the graph, not only in the zone bands.
  zone?: string
  purdueShort?: string
}

type ZoneBandData = {
  label: string
  level: string | null
  color: string
  width: number
  height: number
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
          {data.zone ? (
            <div className="mt-1 flex items-center justify-between gap-2 border-t border-slate-950/20 pt-1">
              <span
                className="truncate text-[9px] font-semibold uppercase tracking-wider text-slate-900/60"
                title={data.zone}
              >
                {data.zone}
              </span>
              {data.purdueShort ? (
                <span className="rounded bg-slate-950/60 px-1 py-px font-mono text-[9px] font-bold text-slate-100">
                  {data.purdueShort}
                </span>
              ) : null}
            </div>
          ) : null}
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

// Non-interactive decoration band behind one zone column: subtle tinted
// background, left accent edge and a header chip naming the zone and its
// Purdue level. Because it lives inside the ReactFlow viewport it tracks pan
// and zoom exactly like the nodes it frames.
function ZoneBand({ data }: NodeProps<Node<ZoneBandData>>) {
  return (
    <div
      className="pointer-events-none select-none overflow-hidden rounded-xl"
      style={{
        width: data.width,
        height: data.height,
        borderLeft: `3px solid ${data.color}`,
        background: `linear-gradient(to right, ${data.color}14 0%, ${data.color}08 55%, transparent 100%)`,
      }}
    >
      <div className="flex items-center gap-1.5 px-2.5 pt-2">
        <span
          className="inline-block h-2 w-2 shrink-0 rounded-sm"
          style={{ backgroundColor: data.color }}
        />
        <span className="truncate text-[10px] font-bold uppercase tracking-widest text-slate-400">
          {data.label}
        </span>
        {data.level ? (
          <span className="shrink-0 font-mono text-[10px] font-bold" style={{ color: data.color }}>
            {data.level}
          </span>
        ) : null}
      </div>
    </div>
  )
}

const nodeTypes = { network: NetworkNode, zoneband: ZoneBand }

// Edge styling constants: the relationship-type colour is the semantic
// signal; stroke width / opacity / animation carry the state (idle, hovered,
// relevant to the selection, on the attack path).
const EDGE_BASE_WIDTH = 1.5
const EDGE_EMPHASIS_WIDTH = 2.3
const EDGE_HOVER_WIDTH = 2.8
const PATH_WIDTH = 3.4
const ARROW_SIZE = 17
const PATH_ARROW_SIZE = 24

const FIT_PADDING = 0.16

// Re-fits the viewport whenever the node set or its layout changes (new
// upload, new assessment, zone metadata arriving), so the whole architecture
// is always visible on load without requiring a manual fit. Runs inside the
// ReactFlowProvider.
function FitOnChange({ signature }: { signature: string }) {
  const { fitView } = useReactFlow()
  const previous = useRef<string>('')
  useEffect(() => {
    if (!signature || signature === previous.current) return
    previous.current = signature
    // Defer one frame so ReactFlow has laid out the new nodes before
    // measuring the bounds.
    const frame = requestAnimationFrame(() => {
      void fitView({ padding: FIT_PADDING, duration: 350 })
    })
    return () => cancelAnimationFrame(frame)
  }, [signature, fitView])
  return null
}

// Zone chips rendered below the canvas (still inside the provider) so each
// chip can zoom the viewport to its zone's members — the analyst can focus
// on one security zone at a time without fighting pan/zoom.
function ZoneFocusChips({
  zoneOrder,
  colorOf,
  levelOf,
  nodeZoneMap,
  networkNodes,
}: {
  zoneOrder: string[]
  colorOf: (zone: string) => string
  levelOf: (zone: string) => string | null
  nodeZoneMap: Map<string, string>
  networkNodes: Node[]
}) {
  const { fitView } = useReactFlow()
  const [active, setActive] = useState<string | null>(null)

  const zoomToZone = (zone: string) => {
    const members = networkNodes.filter((node) => nodeZoneMap.get(node.id) === zone)
    if (!members.length) return
    setActive((current) => (current === zone ? null : zone))
    if (active !== zone) {
      // Defer so the clicked state paints before the animated zoom.
      requestAnimationFrame(() => {
        void fitView({ nodes: members, padding: 0.32, duration: 450, maxZoom: 1.2 })
      })
    } else {
      void fitView({ padding: FIT_PADDING, duration: 450 })
    }
  }

  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-slate-400">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
        Focus zone:
      </span>
      {zoneOrder.map((zone) => {
        const isActive = active === zone
        return (
          <button
            key={zone}
            type="button"
            onClick={() => zoomToZone(zone)}
            aria-pressed={isActive}
            className={`group flex items-center gap-1.5 rounded-full border px-2 py-0.5 transition ${
              isActive
                ? 'border-cyan-400/60 bg-cyan-500/10 text-cyan-200'
                : 'border-transparent text-slate-400 hover:border-slate-600 hover:bg-slate-800/60 hover:text-slate-200'
            }`}
            title={`Zoom to the ${zone} zone`}
          >
            <span
              className="inline-block h-2 w-2 shrink-0 rounded-sm"
              style={{ backgroundColor: colorOf(zone) }}
            />
            <span className="max-w-[170px] truncate">{zone}</span>
            <span className="font-mono text-[10px] text-slate-500">
              {levelOf(zone) && purdueLevelMeta[levelOf(zone) ?? '']
                ? levelOf(zone)
                : '—'}
            </span>
          </button>
        )
      })}
    </div>
  )
}

const NetworkViewer = forwardRef<
  HTMLInputElement,
  {
    nodeIds: string[]
    nodeKindMap: Map<string, string>
    edgeList: Array<{
      source: string
      target: string
      label: string
      relType?: string
      weight?: number
      firewalled?: boolean
    }>
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
    result?: ResultPayload | null
    // Zone / Purdue metadata for the banded layout (optional: when absent the
    // viewer falls back to the plain layered layout).
    nodeZoneMap?: Map<string, string>
    nodePurdueMap?: Map<string, string | null>
    zonePurdueMap?: Map<string, string | null>
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
    result,
    nodeZoneMap,
    nodePurdueMap,
    zonePurdueMap,
  },
  searchInputRef,
) {
  const canvasRef = useRef<HTMLDivElement>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  // Edge hover: the hovering edge id (for emphasis) plus the cursor position
  // for a fixed-position detail chip that never fights the pan/zoom canvas.
  const [hoveredEdge, setHoveredEdge] = useState<{
    id: string
    source: string
    target: string
    relType?: string
    weight?: number
    firewalled?: boolean
    x: number
    y: number
  } | null>(null)
  // When on, every edge shows its label permanently; otherwise labels appear
  // only for hovered / selected / attack-path edges (clarity without clutter).
  const [labelsForced, setLabelsForced] = useState(false)

  const rankLevel = (level: string | null) =>
    level && purdueLevelMeta[level] ? purdueLevelMeta[level].order : UNZONED_META.order

  // Zone-band layout: nodes grouped into vertical columns ordered by Purdue
  // level, causality preserved left-to-right within each zone. Falls back to
  // the plain layered layout when the topology carries no zone metadata.
  const zonedLayout = useMemo(() => {
    if (!nodeZoneMap || !nodeZoneMap.size || !zonePurdueMap) return null
    const zoneOf = (id: string) => nodeZoneMap.get(id) ?? 'Unzoned'
    const zonePurdueOf = (zone: string) => zonePurdueMap.get(zone) ?? null
    const zoneOrder = orderZonesByPurdue(nodeIds.map(zoneOf), zonePurdueOf, rankLevel)
    const { positions, bandExtents } = computeZonedPositions(
      nodeIds,
      edgeList,
      zoneOf,
      zoneOrder,
    )
    const colorOf = (zone: string) => {
      const level = zonePurdueOf(zone)
      return level && purdueLevelMeta[level] ? purdueLevelMeta[level].hex : UNZONED_META.hex
    }
    const levelOf = (zone: string) => zonePurdueOf(zone)
    return { positions, bandExtents, zoneOrder, colorOf, levelOf }
  }, [nodeIds, edgeList, nodeZoneMap, zonePurdueMap])

  const nodePositions = useMemo(
    () => zonedLayout?.positions ?? computeLayeredPositions(nodeIds, edgeList),
    [zonedLayout, nodeIds, edgeList],
  )

  const bandNodes = useMemo<Node[]>(() => {
    if (!zonedLayout) return []
    return Array.from(zonedLayout.bandExtents.entries()).map(([zone, ext]) => ({
      id: `zone-band-${zone}`,
      type: 'zoneband',
      position: { x: ext.x, y: 0 },
      data: {
        label: zone,
        level: zonedLayout.levelOf(zone),
        color: zonedLayout.colorOf(zone),
        width: ext.width,
        height: ext.height,
      } satisfies ZoneBandData,
      selectable: false,
      draggable: false,
      focusable: false,
      connectable: false,
      zIndex: -1,
    }))
  }, [zonedLayout])

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
      const zone = nodeZoneMap?.get(nodeId)
      const level = zone ? nodePurdueMap?.get(nodeId) : undefined

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
          zone,
          purdueShort:
            level && purdueLevelMeta[level] ? purdueLevelMeta[level].short : undefined,
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
    nodeZoneMap,
    nodePurdueMap,
  ])

  const networkEdges = useMemo<Edge[]>(() => {
    return edgeList.map(({ source, target, label, relType, weight, firewalled }, index) => {
      const id = `${source}-${target}-${index}`
      const onPath =
        showAttackPath && attackPathEdgeKeys.has(`${source}->${target}`)
      const dimmed = neighborSet
        ? !(neighborSet.has(source) && neighborSet.has(target))
        : false
      const emphasized = Boolean(
        neighborSet && neighborSet.has(source) && neighborSet.has(target),
      )
      const hovered = hoveredEdge?.id === id
      const baseColor = relationshipColor(relType)
      // Attack path overrides the type colour so it is impossible to miss
      // (rose, thick, animated, glowing); the label still names the type.
      const color = onPath ? '#fb7185' : baseColor
      const width = onPath
        ? PATH_WIDTH
        : hovered
          ? EDGE_HOVER_WIDTH
          : emphasized
            ? EDGE_EMPHASIS_WIDTH
            : EDGE_BASE_WIDTH
      const opacity = dimmed
        ? 0.08
        : onPath
          ? 1
          : hovered || emphasized
            ? 0.95
            : 0.6
      // Labels: hovered / relevant / attack-path edges always carry one;
      // the toolbar toggle makes every edge labelled.
      const labelled = labelsForced || onPath || hovered || emphasized
      return {
        id,
        source,
        target,
        label: labelled ? label : undefined,
        type: 'smoothstep',
        animated: onPath,
        style: {
          stroke: color,
          strokeWidth: width,
          opacity,
          ...(onPath
            ? { filter: 'drop-shadow(0 0 3px rgba(251,113,133,0.8))' }
            : {}),
        },
        labelStyle: { fill: '#cbd5e1', fontSize: 9.5, fontWeight: 600 },
        labelBgStyle: { fill: '#0f172a', fillOpacity: 0.92 },
        markerEnd: {
          type: 'arrowclosed',
          color,
          width: onPath ? PATH_ARROW_SIZE : ARROW_SIZE,
          height: onPath ? PATH_ARROW_SIZE : ARROW_SIZE,
        },
      }
    })
  }, [
    edgeList,
    showAttackPath,
    attackPathEdgeKeys,
    neighborSet,
    hoveredEdge,
    labelsForced,
  ])

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

  // Fullscreen toggle for the graph canvas. The fullscreen element is the
  // canvas wrapper, so the graph (not the page) is what fills the screen.
  useEffect(() => {
    const onFullscreenChange = () =>
      setIsFullscreen(Boolean(document.fullscreenElement))
    document.addEventListener('fullscreenchange', onFullscreenChange)
    return () =>
      document.removeEventListener('fullscreenchange', onFullscreenChange)
  }, [])

  const toggleFullscreen = () => {
    if (document.fullscreenElement) {
      void document.exitFullscreen()
    } else {
      void canvasRef.current?.requestFullscreen()
    }
  }

  // Re-fit when the node set changes OR the zone ordering/layout changes
  // (e.g. an assessment result arrives and refines the zone metadata while
  // node ids stay identical).
  const fitSignature = useMemo(
    () =>
      nodeIds.join('|') +
      '#' +
      (zonedLayout ? zonedLayout.zoneOrder.join('|') : 'layered'),
    [nodeIds, zonedLayout],
  )

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
            name="node-search"
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
          <button
            onClick={() => setLabelsForced((value) => !value)}
            className={`rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition ${
              labelsForced
                ? 'border-cyan-400/60 bg-cyan-500/10 text-cyan-200'
                : 'border-slate-700 bg-slate-950 text-slate-300 hover:text-slate-100'
            }`}
            aria-pressed={labelsForced}
            title="Show the relationship label on every edge (labels already appear on hover, selection and the attack path)"
          >
            Edge labels
          </button>
          <button
            onClick={toggleFullscreen}
            className={`rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition ${
              isFullscreen
                ? 'border-cyan-400/60 bg-cyan-500/10 text-cyan-200'
                : 'border-slate-700 bg-slate-950 text-slate-300 hover:text-slate-100'
            }`}
            aria-pressed={isFullscreen}
            title="Expand the topology to fullscreen"
          >
            {isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          </button>
        </div>
      </div>

      <ReactFlowProvider>
        <div
          ref={canvasRef}
          className="network-canvas relative h-[440px] overflow-hidden rounded-xl border border-slate-800 bg-slate-950 md:h-[520px]"
        >
          {/* Exit-fullscreen overlay: the fullscreen element is the canvas
              itself, so a control outside it would be unreachable while
              fullscreen is active. This one lives inside the element, above
              the flow pane, so the analyst can always leave fullscreen. */}
          {isFullscreen ? (
            <button
              onClick={toggleFullscreen}
              className="absolute right-3 top-3 z-20 rounded-lg border border-slate-600 bg-slate-950/90 px-2.5 py-1.5 text-xs font-semibold text-slate-200 shadow-lg transition hover:bg-slate-800"
            >
              Exit fullscreen
            </button>
          ) : null}
          {nodeIds.length ? (
            <ReactFlow
              nodes={[...bandNodes, ...networkNodes]}
              edges={networkEdges}
              nodeTypes={nodeTypes}
              fitView
              fitViewOptions={{ padding: FIT_PADDING }}
              minZoom={0.12}
              maxZoom={2.2}
              onNodeClick={(_, node) => {
                if (node.type === 'network') setSelectedNode(String(node.id))
              }}
              onPaneClick={() => {
                setSelectedNode(null)
                setHoveredEdge(null)
              }}
              onEdgeMouseEnter={(event, edge) => {
                const match = edgeList.find(
                  (item) =>
                    item.source === edge.source && item.target === edge.target,
                )
                setHoveredEdge({
                  id: String(edge.id),
                  source: String(edge.source),
                  target: String(edge.target),
                  relType: match?.relType,
                  weight: match?.weight,
                  firewalled: match?.firewalled,
                  x: event.clientX,
                  y: event.clientY,
                })
              }}
              onEdgeMouseMove={(event) =>
                setHoveredEdge((current) =>
                  current
                    ? { ...current, x: event.clientX, y: event.clientY }
                    : current,
                )
              }
              onEdgeMouseLeave={() => setHoveredEdge(null)}
              proOptions={{ hideAttribution: true }}
              colorMode="dark"
            >
              <FitOnChange signature={fitSignature} />
              <MiniMap pannable zoomable nodeStrokeWidth={3} />
              <Controls showInteractive={false} />
              <Background gap={24} size={1.2} />
            </ReactFlow>
          ) : (
            <EmptyState
              title="No topology to display yet"
              hint="Upload a topology file to populate the network."
            />
          )}
        </div>

        {/* Zone focus chips — inside the provider so each chip can zoom the
            viewport to its zone. */}
        {zonedLayout ? (
          <ZoneFocusChips
            zoneOrder={zonedLayout.zoneOrder}
            colorOf={zonedLayout.colorOf}
            levelOf={zonedLayout.levelOf}
            nodeZoneMap={nodeZoneMap ?? new Map()}
            networkNodes={networkNodes}
          />
        ) : null}
      </ReactFlowProvider>

      {/* Edge hover chip: fixed to the viewport so it tracks the cursor
          without disturbing the graph, and cleared on leave/pane click. */}
      {hoveredEdge ? (
        <div
          className="pointer-events-none fixed z-50 max-w-xs rounded-xl border border-slate-700 bg-slate-950/95 px-3 py-2 text-xs shadow-2xl shadow-black/50"
          style={{ left: hoveredEdge.x + 14, top: hoveredEdge.y + 14 }}
          role="tooltip"
        >
          <p className="flex items-center gap-1.5 font-semibold capitalize text-slate-100">
            <span
              className="inline-block h-2 w-2 shrink-0 rounded-full"
              style={{ backgroundColor: relationshipColor(hoveredEdge.relType) }}
            />
            {hoveredEdge.relType ?? 'relationship'}
            {hoveredEdge.firewalled ? (
              <span className="text-cyan-300" aria-label="firewalled link">
                🔒
              </span>
            ) : null}
          </p>
          <p className="mt-1 break-words font-mono text-[11px] leading-snug text-slate-400">
            {hoveredEdge.source} <span aria-hidden="true">→</span>{' '}
            {hoveredEdge.target}
          </p>
          {typeof hoveredEdge.weight === 'number' ? (
            <p className="mt-1 text-slate-400">
              Causal weight{' '}
              <span className="font-mono text-cyan-200">
                w = {hoveredEdge.weight.toFixed(2)}
              </span>{' '}
              — the Noisy-OR strength of this link.
            </p>
          ) : null}
          <p className="mt-1 text-[11px] text-slate-500">
            Hover to inspect · labels show on hover, selection and the attack
            path.
          </p>
        </div>
      ) : null}

      {/* Legend */}
      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-slate-400">
        <span className="flex flex-wrap items-center gap-1.5">
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
        <span className="flex flex-wrap items-center gap-x-1.5 gap-y-1">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            Relationship:
          </span>
          {Object.entries(relationshipColors).map(([rel, color]) => (
            <span key={rel} className="flex items-center gap-1">
              <span
                className="inline-block h-0.5 w-4 rounded"
                style={{ backgroundColor: color }}
              />
              {rel}
            </span>
          ))}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-4 rounded bg-rose-400" />
          attack path (animated, glowing)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="text-slate-500">📌</span> evidence-pinned
        </span>
        <span className="flex items-center gap-1.5">
          <span className="text-slate-500">🔒</span> firewalled link
        </span>
      </div>

      <details className="details-card disclosure-no-marker mt-3">
        <summary className="details-summary">
          <span className="flex items-center gap-2.5">
            <svg
              className="details-chevron h-4 w-4 shrink-0 text-slate-400"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M9 18l6-6-6-6" />
            </svg>
            <span className="text-sm font-semibold text-slate-100">
              How to read this network
            </span>
          </span>
        </summary>
        <div className="border-t border-slate-800 px-4 py-3 text-xs leading-relaxed text-slate-400">
          <p>
            Columns are security zones ordered by their Purdue-inspired level
            (Enterprise → Industrial DMZ → Operations → Control → Field →
            Process). A zone is an IEC 62443-style security boundary; a Purdue
            level is an architectural hierarchy — the two are distinct
            concepts the framework keeps separate. The topology always loads
            fitted to the viewport; use the zone chips to zoom into a single
            zone, or the controls / wheel to zoom and pan.
          </p>
          <p className="mt-2">
            Edge colour encodes the{' '}
            <strong className="text-slate-300">relationship type</strong>
            (controls in red, monitors in teal, actuates in amber, connects-to
            in grey, programs/operates in purple). Arrows show the direction.
            Hover an edge for its source, target and causal weight; selecting
            a node highlights its relationships and de-emphasises the rest.
            The rose, animated edges are the calculated attack path.
          </p>
          <p className="mt-2">
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

      {/* Bayesian Results — the model context and outputs for the current
          run, tucked below the reading guide so the graph stays the primary
          content. Collapsed by default like the other disclosure sections. */}
      <details className="details-card disclosure-no-marker mt-3">
        <summary className="details-summary">
          <span className="flex items-center gap-2.5">
            <svg
              className="details-chevron h-4 w-4 shrink-0 text-slate-400"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M9 18l6-6-6-6" />
            </svg>
            <span className="text-sm font-semibold text-slate-100">
              Bayesian Results
            </span>
          </span>
          <span className="hidden text-xs font-normal text-slate-500 sm:inline">
            {result
              ? `${result.summary.asset_count} assets · ${formatProbability(result.summary.overall_risk)} overall risk`
              : 'run an assessment to populate'}
          </span>
        </summary>
        <div className="details-panel border-t border-slate-800 px-4 py-3">
          <BayesianResults result={result ?? null} embedded />
        </div>
      </details>
    </div>
  )
})

export default NetworkViewer
