import { readFileSync } from 'node:fs'

// Graph result from the live API — exactly what the frontend renders from.
const graph = JSON.parse(readFileSync('/tmp/graph_result.json', 'utf8'))
const nodeIds = graph.nodes.map(n => n.id)
const nodeZoneMap = new Map(graph.nodes.filter(n => n.zone).map(n => [n.id, String(n.zone)]))
const nodePurdueMap = new Map(graph.nodes.filter(n => n.purdue_level).map(n => [n.id, String(n.purdue_level)]))
const edges = graph.edges.map(e => ({
  source: e.source, target: e.target,
  label: [e.relationship || e.type || 'connects-to', e.weight !== undefined ? `w=${e.weight}` : '', e.firewalled ? '🔒' : ''].filter(Boolean).join(' '),
}))

// ---- Copied verbatim from utils.ts / NetworkViewer.tsx ----
const PURDUE_ORDER = { 'Level 4': 0, 'Level 3': 1, 'Level 3.5': 2, 'Level 2': 3, 'Level 1': 4, 'Level 0': 5 }
const rankLevel = (level) => (level && PURDUE_ORDER[level] !== undefined ? PURDUE_ORDER[level] : 99)
const orderZonesByPurdue = (zones, zonePurdue, rank) =>
  [...new Set(zones)].sort((a, b) => { const ra = rank(zonePurdue(a)); const rb = rank(zonePurdue(b)); if (ra !== rb) return ra - rb; return a.localeCompare(b) })
function computeZonedPositions(nodeIds, edges, zoneOf, zoneOrder, columnStep = 330, rowStep = 220, nodeHeight = 76, maxRowsPerColumn = 10, zoneGap = 150) {
  const positions = new Map(); const bandExtents = new Map(); let columnX = 0
  zoneOrder.forEach((zone) => {
    const members = nodeIds.filter((id) => zoneOf(id) === zone)
    const localEdges = edges.filter(({ source, target }) => zoneOf(source) === zone && zoneOf(target) === zone)
    const outgoing = new Map(); const incomingCount = new Map()
    members.forEach((id) => { outgoing.set(id, []); incomingCount.set(id, 0) })
    localEdges.forEach(({ source, target }) => { if (!outgoing.has(source) || !incomingCount.has(target)) return; outgoing.get(source).push(target); incomingCount.set(target, (incomingCount.get(target) ?? 0) + 1) })
    const roots = members.filter((id) => (incomingCount.get(id) ?? 0) === 0)
    const queue = (roots.length ? roots : members.slice(0, 1)).map((id) => ({ id, depth: 0 }))
    const depth = new Map(); const visited = new Set()
    while (queue.length) { const { id, depth: d } = queue.shift(); if (visited.has(id)) continue; visited.add(id); depth.set(id, d); for (const next of outgoing.get(id) ?? []) if (!visited.has(next)) queue.push({ id: next, depth: d + 1 }) }
    let maxDepth = Math.max(0, ...members.map((id) => depth.get(id) ?? 0))
    members.forEach((id) => { if (!depth.has(id)) { maxDepth += 1; depth.set(id, maxDepth) } })
    const ordered = [...members].sort((a, b) => (depth.get(a) ?? 0) - (depth.get(b) ?? 0) || a.localeCompare(b))
    const rowsOf = new Map(); const subColumnOf = new Map(); const membersByDepth = new Map()
    ordered.forEach((id) => { const d = depth.get(id) ?? 0; const list = membersByDepth.get(d) ?? []; list.push(id); membersByDepth.set(d, list) })
    membersByDepth.forEach((ids) => { ids.forEach((id, index) => { rowsOf.set(id, index % maxRowsPerColumn); subColumnOf.set(id, Math.floor(index / maxRowsPerColumn)) }) })
    let bandBottom = 0; let maxColumnIndex = 0
    ordered.forEach((id) => {
      const d = depth.get(id) ?? 0; const row = rowsOf.get(id) ?? 0
      const subColumn = d + (subColumnOf.get(id) ?? 0)
      const x = 40 + subColumn * columnStep; const y = 46 + row * rowStep
      positions.set(id, { x: columnX + x, y }); bandBottom = Math.max(bandBottom, y + nodeHeight); maxColumnIndex = Math.max(maxColumnIndex, subColumn)
    })
    const width = 40 + (maxColumnIndex + 1) * columnStep + 24
    bandExtents.set(zone, { x: columnX, width, height: bandBottom + 24 }); columnX += width + zoneGap
  })
  return { positions, bandExtents }
}
const NODE_W = 184, NODE_H = 85
function estimateLabelPill(text) { const length = (text ?? '').length; return { w: Math.min(Math.max(length * 6.2 + 16, 50), 190), h: 22 } }
function edgeLabelPosition(source, target, nodePositions, labelText) {
  const s = nodePositions.get(source); const t = nodePositions.get(target)
  if (!s || !t) return undefined
  const sC = { x: s.x + NODE_W / 2, y: s.y + NODE_H / 2 }; const tC = { x: t.x + NODE_W / 2, y: t.y + NODE_H / 2 }
  const mid = { x: (sC.x + tC.x) / 2, y: (sC.y + tC.y) / 2 }
  const { w: pillW, h: pillH } = estimateLabelPill(labelText)
  const cards = [...nodePositions.values()].map((p) => ({ x: p.x, y: p.y, w: NODE_W, h: NODE_H }))
  const pillClear = (x, y) => !cards.some((c) => x + pillW/2 > c.x && x - pillW/2 < c.x + c.w && y + pillH/2 > c.y && y - pillH/2 < c.y + c.h)
  const overlapDepth = (x, y) => { let worst = 0; for (const c of cards) { const ox = Math.min(x + pillW/2, c.x + c.w) - Math.max(x - pillW/2, c.x); const oy = Math.min(y + pillH/2, c.y + c.h) - Math.max(y - pillH/2, c.y); if (ox > 0 && oy > 0) worst = Math.max(worst, Math.min(ox, oy)) } return worst }
  if (pillClear(mid.x, mid.y)) return { x: mid.x, y: mid.y, how: 'mid' }
  const candidates = []
  for (let i = 1; i < 40; i++) { const r = i / 40; candidates.push({ x: sC.x + (tC.x - sC.x) * r, y: sC.y + (tC.y - sC.y) * r, how: 'line' }) }
  const dx = tC.x - sC.x, dy = tC.y - sC.y, len = Math.hypot(dx, dy) || 1
  const px = -dy / len, py = dx / len
  for (const off of [30, 55, 80, 105, 130]) { candidates.push({ x: mid.x + px * off, y: mid.y + py * off, how: 'perp+' }); candidates.push({ x: mid.x - px * off, y: mid.y - py * off, how: 'perp-' }) }
  for (const c of candidates) if (pillClear(c.x, c.y)) return { x: c.x, y: c.y, how: c.how }
  let best = candidates[0], bestDepth = Infinity
  for (const c of candidates) { const d = overlapDepth(c.x, c.y); if (d < bestDepth) { bestDepth = d; best = c } }
  return { x: best.x, y: best.y, how: best.how + '(fb)', depth: bestDepth }
}

// ---- Run ----
const zoneOf = (id) => nodeZoneMap.get(id) ?? 'Unzoned'
const zonePurdueOf = (zone) => nodePurdueMap.get(zone) ?? null
// zone purdue: representative = min order over member nodes
const zonePurdueMap = new Map()
for (const id of nodeIds) {
  const zone = zoneOf(id); const level = nodePurdueMap.get(id) ?? null
  const existing = zonePurdueMap.get(zone) ?? null
  if (existing === null || (level !== null && rankLevel(level) < rankLevel(existing))) zonePurdueMap.set(zone, level)
}
const zoneOrder = orderZonesByPurdue(nodeIds.map(zoneOf), (z) => zonePurdueMap.get(z) ?? null, rankLevel)
const { positions } = computeZonedPositions(nodeIds, edges, zoneOf, zoneOrder)
const problems = []
for (const e of edges) {
  const lp = edgeLabelPosition(e.source, e.target, positions, e.label)
  if (!lp) continue
  const { w: pw } = estimateLabelPill(e.label); const ph = 22
  let worst = 0
  for (const c of positions.values()) {
    const ox = Math.min(lp.x + pw/2, c.x + 184) - Math.max(lp.x - pw/2, c.x)
    const oy = Math.min(lp.y + ph/2, c.y + 85) - Math.max(lp.y - ph/2, c.y)
    if (ox > 0 && oy > 0) worst = Math.max(worst, Math.min(ox, oy))
  }
  if (worst > 0) problems.push({ label: e.label, how: lp.how, worst: +worst.toFixed(0), src: e.source, tgt: e.target, lx: +lp.x.toFixed(0), ly: +lp.y.toFixed(0) })
}
problems.sort((a, b) => b.worst - a.worst)
console.log('edges:', edges.length, '| problems:', problems.length, '| zones:', zoneOrder.length)
for (const p of problems.slice(0, 20)) console.log(`  ${String(p.worst).padStart(3)}px [${p.how}] ${p.label}  (${p.src} → ${p.tgt}) @(${p.lx},${p.ly})`)
