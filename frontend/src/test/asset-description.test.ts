import { describe, expect, it } from 'vitest'
import { assetDescription, relationshipColor } from '../utils'

describe('assetDescription', () => {
  it('prefers the topology description field', () => {
    const text = assetDescription(
      { type: 'Firewall', description: 'Edge firewall for the plant' },
      'FW-1',
      'device',
    )
    expect(text).toBe('Edge firewall for the plant')
  })

  it('matches the declared type against the dictionary', () => {
    const text = assetDescription({ type: 'DCS Controller' }, 'DCS-1', 'device')
    expect(text).toMatch(/Distributed Control System/)
  })

  it('matches compact CSV-derived types', () => {
    // CSV/GraphML conversions compact types to "controlvalve".
    const text = assetDescription({ type: 'controlvalve' }, 'FCV-001', 'physical')
    expect(text).toMatch(/final control element/)
  })

  it('falls back to a name substring match', () => {
    const text = assetDescription({}, 'Pressure Transmitter (Reactor Feed)', 'device')
    expect(text).toMatch(/measures process pressure/)
  })

  it('resolves multi-word names with the longest key first', () => {
    const text = assetDescription({}, 'Safety Shutoff Valve (Feed)', 'physical')
    expect(text).toMatch(/safety instrumented system/)
  })

  it('uses the kind-level fallback for unknown assets', () => {
    const text = assetDescription({}, 'Quantum Widget 9000', 'device')
    expect(text).toMatch(/networked industrial or IT device/)
    expect(assetDescription({}, 'Mystery Thing', 'human')).toMatch(/operator, engineer or administrator/)
  })

  it('returns null when nothing matches and kind is unknown', () => {
    expect(assetDescription({}, '???', 'unusual-kind')).toBeNull()
  })

  it('matches acronyms as whole words only', () => {
    // "ct" (current transformer) must not match inside "actuator".
    const actuator = assetDescription({ type: 'Actuator' }, 'ACT-1', 'physical')
    expect(actuator).toMatch(/control signal into mechanical motion/)
    const ct = assetDescription({ type: 'CT' }, 'CT-1', 'device')
    expect(ct).toMatch(/current transformer/)
  })

  it('falls back to the kind description for an empty input', () => {
    expect(assetDescription(undefined, '', 'device')).toMatch(
      /networked industrial or IT device/,
    )
  })
})

describe('relationshipColor', () => {
  it('maps known relationship types to the semantic palette', () => {
    expect(relationshipColor('controls')).toBe('#C0392B')
    expect(relationshipColor('monitors')).toBe('#1F8A70')
    expect(relationshipColor('actuates')).toBe('#E67E22')
    expect(relationshipColor('connects-to')).toBe('#7F8C8D')
    expect(relationshipColor('programs / operates')).toBe('#8E44AD')
  })

  it('is case-insensitive', () => {
    expect(relationshipColor('Controls')).toBe('#C0392B')
  })

  it('falls back to a neutral slate for unknown types', () => {
    expect(relationshipColor('telnet-session')).toBe('#64748b')
    expect(relationshipColor(undefined)).toBe('#64748b')
  })
})
