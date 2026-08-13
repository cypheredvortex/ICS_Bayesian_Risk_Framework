import { describe, expect, it } from 'vitest'
import {
  computeLayeredPositions,
  computeZonedPositions,
  orderZonesByPurdue,
} from '../utils'

const rankLevel = (level: string | null) =>
  level && ['5', '4', '3.5', '3', '2', '1', '0'].includes(level)
    ? ['5', '4', '3.5', '3', '2', '1', '0'].indexOf(level)
    : 99

describe('orderZonesByPurdue', () => {
  it('deduplicates repeated zone names (one per node)', () => {
    const zonePurdue = (zone: string) =>
      ({ Enterprise: '4', Field: '1', Control: '2' })[zone] ?? null
    // Callers pass nodeIds.map(zoneOf) which repeats each zone per member.
    const result = orderZonesByPurdue(
      ['Enterprise', 'Enterprise', 'Field', 'Control', 'Enterprise', 'Field'],
      zonePurdue,
      rankLevel,
    )
    expect(result).toEqual(['Enterprise', 'Control', 'Field'])
  })

  it('orders by Purdue level top-down, unknown levels last', () => {
    const zonePurdue = (zone: string) =>
      ({ Process: '0', IDMZ: '3.5', Unknown: null })[zone] ?? null
    const result = orderZonesByPurdue(
      ['Unknown', 'Process', 'IDMZ'],
      zonePurdue,
      rankLevel,
    )
    expect(result).toEqual(['IDMZ', 'Process', 'Unknown'])
  })
})

describe('computeZonedPositions', () => {
  // A dense zone (16 members at the same BFS depth) must wrap into several
  // sub-columns of maxRowsPerColumn rows instead of one huge stack — and
  // every node must get a unique position (no overlap).
  it('wraps dense layers into sub-columns with unique positions', () => {
    const members = Array.from({ length: 16 }, (_, i) => `field_${i}`)
    const nodeIds = [...members]
    const zoneOf = () => 'Field'
    const { positions } = computeZonedPositions(
      nodeIds,
      [],
      zoneOf,
      ['Field'],
    )

    const keys = [...positions.keys()]
    expect(keys.length).toBe(16)
    // All positions unique.
    const unique = new Set(keys.map((id) => JSON.stringify(positions.get(id))))
    expect(unique.size).toBe(16)

    // Rows within [0, maxRowsPerColumn). rowStep matches the spacing
    // constant computeZonedPositions defaults to (220).
    const ys = [...positions.values()].map((p) => p.y)
    const rows = new Set(ys)
    rows.forEach((y) => {
      expect((y - 46) / 220).toBeLessThan(10)
      expect((y - 46) / 220).toBeGreaterThanOrEqual(0)
    })
    // 16 members in 10-row columns => 2 sub-columns.
    const xs = new Set([...positions.values()].map((p) => p.x))
    expect(xs.size).toBe(2)
  })

  it('lays causal chains left-to-right within a zone', () => {
    const nodeIds = ['sis_sensor', 'sis_solver', 'sis_valve']
    const zoneOf = () => 'SIS'
    const { positions } = computeZonedPositions(
      nodeIds,
      [
        { source: 'sis_sensor', target: 'sis_solver' },
        { source: 'sis_solver', target: 'sis_valve' },
      ],
      zoneOf,
      ['SIS'],
    )
    const sensor = positions.get('sis_sensor')!
    const solver = positions.get('sis_solver')!
    const valve = positions.get('sis_valve')!
    expect(solver.x).toBeGreaterThan(sensor.x)
    expect(valve.x).toBeGreaterThan(solver.x)
  })

  it('stacks multiple zones as separate bands without runaway width', () => {
    const nodeIds = ['a1', 'a2', 'b1']
    const zoneOf = (id: string) => (id.startsWith('a') ? 'ZoneA' : 'ZoneB')
    const { positions, bandExtents } = computeZonedPositions(
      nodeIds,
      [],
      zoneOf,
      ['ZoneA', 'ZoneB'],
    )
    // Zone B band starts after Zone A's band, not thousands of px away.
    const bandA = bandExtents.get('ZoneA')!
    const bandB = bandExtents.get('ZoneB')!
    expect(bandB.x).toBeGreaterThanOrEqual(bandA.x + bandA.width)
    expect(bandB.x).toBeLessThan(1000)
    const maxX = Math.max(...[...positions.values()].map((p) => p.x))
    expect(maxX).toBeLessThan(1000)

    // Level bands are separated by the zone-gap constant so the Purdue
    // hierarchy reads as distinct columns and cross-zone edge labels
    // ("connects-to (firewalled)", ~139px) fit in the gap (default 150px).
    expect(bandB.x - (bandA.x + bandA.width)).toBe(150)
    // Within a zone, rows sit one rowStep apart (default 220px) so edges and
    // labels between vertically stacked assets stay readable.
    expect(positions.get('a1')!.y).toBe(46)
    expect(positions.get('a2')!.y - positions.get('a1')!.y).toBe(220)
  })
})

describe('computeLayeredPositions', () => {
  it('still produces bounded positions for the fallback layout', () => {
    const positions = computeLayeredPositions(
      ['a', 'b', 'c', 'd'],
      [
        { source: 'a', target: 'b' },
        { source: 'b', target: 'c' },
        { source: 'b', target: 'd' },
      ],
    )
    const xs = [...positions.values()].map((p) => p.x)
    expect(Math.max(...xs)).toBeLessThan(2000)
    expect(positions.get('a')!.x).toBeLessThan(positions.get('b')!.x)
    expect(positions.get('b')!.x).toBeLessThan(positions.get('c')!.x)
  })
})
