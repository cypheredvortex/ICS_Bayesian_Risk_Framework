import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import App from '../App'
import { defaultSettingsPayload, installFetchMock, smallTopology } from './helpers'
import { deriveTopologySummary } from '../utils'

describe('Topology pre-analysis review', () => {
  it('shows backend warnings and the structural summary after upload', async () => {
    const user = userEvent.setup()
    const restore = installFetchMock([
      { url: '/settings', method: 'GET', json: defaultSettingsPayload },
      {
        url: '/upload-topology-file',
        method: 'POST',
        json: {
          asset_count: 1,
          relationship_count: 0,
          warnings: [
            'topology.json: relationship (plc_1 -> plc_1) is a self-loop and was removed.',
          ],
          summary: {
            zones: { 'Level 1': 1 },
            assets_without_zone: 0,
            kinds: { device: 1 },
            relationship_types: {},
            firewalled_relationships: 0,
            field_coverage: {
              cvss_type: 1,
              exposed: 0,
              patched: 0,
              consequence_severity: 1,
              zone: 1,
              vulnerabilities: 0,
            },
          },
          topology: smallTopology,
        },
      },
    ])
    render(<App />)
    const input = await screen.findByLabelText('Upload a topology file')
    const file = new File([JSON.stringify(smallTopology)], 'topo.json', {
      type: 'application/json',
    })
    await user.upload(input, file)

    // Review panel: validation status, zones and the backend warning. The
    // warning text also appears in a toast, so match any occurrence.
    expect(await screen.findByText('Valid with warnings')).toBeInTheDocument()
    expect(screen.getByText('Normalization warnings')).toBeInTheDocument()
    expect(
      screen.getAllByText(/self-loop and was removed/).length,
    ).toBeGreaterThan(0)
    expect(screen.getByText('Level 1 · 1')).toBeInTheDocument()
    expect(screen.getByText(/CVSS: 1\/1/)).toBeInTheDocument()
    restore()
  })

  it('derives a structural summary for preset datasets served as raw JSON', async () => {
    const user = userEvent.setup()
    const restore = installFetchMock([
      { url: '/settings', method: 'GET', json: defaultSettingsPayload },
      {
        url: '/datasets/power_substation',
        method: 'GET',
        json: {
          assets: {
            plc_a: { kind: 'device', zone: 'Level 0' },
            hmi_a: { kind: 'device', zone: 'Level 2' },
          },
          relationships: [['plc_a', 'hmi_a', 'connects-to', false]],
        },
      },
      {
        url: '/upload-topology',
        method: 'POST',
        json: { asset_count: 2, relationship_count: 1, warnings: [] },
      },
    ])
    render(<App />)
    const select = await screen.findByLabelText('Select a predefined dataset')
    await user.selectOptions(select, 'power_substation')

    // Preset datasets have no backend summary: the app derives one from the
    // returned topology and shows detected zones before analysis. The text
    // "Preset dataset" also labels the dataset selector, so match broadly.
    expect(
      (await screen.findAllByText('Preset dataset')).length,
    ).toBeGreaterThan(0)
    expect(await screen.findByText('Level 0 · 1')).toBeInTheDocument()
    expect(screen.getByText('Level 2 · 1')).toBeInTheDocument()
    restore()
  })
})

describe('deriveTopologySummary', () => {
  it('counts zones, kinds, relationship types and field coverage', () => {
    const summary = deriveTopologySummary({
      assets: {
        plc_1: { kind: 'device', zone: 'Level 1', cvss_type: 7.5 },
        hmi_1: { kind: 'device', cvss_type: 5.0 },
        operator: { kind: 'human', zone: 'Corporate' },
      },
      relationships: [
        ['hmi_1', 'plc_1', 'connects-to', true],
        ['operator', 'hmi_1', 'controls', false],
      ],
    })
    expect(summary.zones).toEqual({ Corporate: 1, 'Level 1': 1 })
    expect(summary.assets_without_zone).toBe(1)
    expect(summary.kinds).toEqual({ device: 2, human: 1 })
    expect(summary.relationship_types).toEqual({
      'connects-to': 1,
      controls: 1,
    })
    expect(summary.firewalled_relationships).toBe(1)
    expect(summary.field_coverage.cvss_type).toBe(2)
  })
})
