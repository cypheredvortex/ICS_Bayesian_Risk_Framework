import { describe, expect, it } from 'vitest'
import {
  assetDescription,
  assetTypeMeaning,
  relationshipColor,
} from '../utils'

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

describe('assetTypeMeaning', () => {
  it('expands the declared acronym from the explanation text', () => {
    const meaning = assetTypeMeaning(
      { type: 'PLC', name: 'Reactor Controller' },
      'plc_1',
      'device',
    )
    expect(meaning).toEqual({
      acronym: 'PLC',
      meaning: 'Programmable logic controller',
    })
  })

  it('matches multi-word declared types that contain the acronym', () => {
    const meaning = assetTypeMeaning({ type: 'DCS Controller' }, 'DCS-1', 'device')
    expect(meaning?.acronym).toBe('DCS')
    expect(meaning?.meaning).toBe('Distributed Control System')
  })

  it('returns null when the type has no acronym expansion', () => {
    // Plain-word types ("Actuator") have no parenthesised abbreviation.
    expect(assetTypeMeaning({ type: 'Actuator' }, 'ACT-1', 'physical')).toBeNull()
  })

  it('returns null when no explanation resolves', () => {
    expect(assetTypeMeaning({}, '???', 'unusual-kind')).toBeNull()
  })

  it('ignores acronyms that do not match the declared type', () => {
    // The dictionary text for "SENSOR" contains no parenthesised acronym
    // matching the declared type, so no meaning is fabricated.
    expect(assetTypeMeaning({ type: 'SENSOR' }, 'T-101', 'physical')).toBeNull()
  })

  it('rejects single-letter substrings that are not words of the type', () => {
    // "(H)" is a substring of "HMI" — a naive includes() match would accept
    // it. The acronym must be the whole type or one of its words.
    expect(
      assetTypeMeaning(
        { type: 'HMI', description: 'A human machine interface (H) panel' },
        'HMI-01',
        'device',
      ),
    ).toBeNull()
  })

  it('falls back to known acronym expansions not written parenthesised', () => {
    // The SCADA dictionary text never spells out the expansion, so the
    // regex cannot extract it — the known-acronym fallback supplies it.
    const meaning = assetTypeMeaning({ type: 'SCADA' }, 'SCADA-01', 'device')
    expect(meaning).toEqual({
      acronym: 'SCADA',
      meaning: 'Supervisory Control and Data Acquisition',
    })
  })

  it('does not fall back for names that merely contain a known acronym', () => {
    // "SCADA-01" as an asset name without a declared type is not itself the
    // acronym SCADA, so no meaning is fabricated from the name alone.
    expect(assetTypeMeaning({}, 'SCADA-01', 'device')).toBeNull()
  })

  it('falls back via the leading token of a multi-word declared type', () => {
    // "SCADA System" is a declared type, so its leading token SCADA
    // resolves the expansion even though the phrase is not the exact key.
    const meaning = assetTypeMeaning(
      { type: 'SCADA System' },
      'SCADA-01',
      'device',
    )
    expect(meaning).toEqual({
      acronym: 'SCADA',
      meaning: 'Supervisory Control and Data Acquisition',
    })
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
