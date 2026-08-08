import { useState } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import App from '../App'
import EvidencePanel from '../components/EvidencePanel'
import {
  assessmentRoutes,
  defaultSettingsPayload,
  installFetchMock,
  sampleResult,
  uploadSmallTopology,
} from './helpers'

// EvidencePanel is a controlled component: the parent owns the evidence
// state. Wrap it in a minimal harness so clicks actually re-render.
function EvidenceHarness({
  initial = {},
}: {
  initial?: Record<string, 'Unknown' | 'Safe' | 'Compromised'>
}) {
  const [evidence, setEvidence] = useState(initial)
  return (
    <EvidencePanel
      assets={[['plc_1', { kind: 'device' }]]}
      evidence={evidence}
      onUpdateEvidence={(asset, state) =>
        setEvidence((current) => ({ ...current, [asset]: state }))
      }
    />
  )
}

describe('EvidencePanel', () => {
  it('lists every asset with Unknown/Safe/Compromised controls', () => {
    render(
      <EvidencePanel
        assets={[['plc_1', { kind: 'device' }], ['hmi', { kind: 'device' }]]}
        evidence={{}}
        onUpdateEvidence={() => {}}
      />,
    )
    expect(screen.getByText('plc_1')).toBeInTheDocument()
    expect(screen.getByText('hmi')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /Unknown/ })).toHaveLength(2)
    expect(screen.getAllByRole('button', { name: /Compromised/ })).toHaveLength(2)
    expect(screen.getAllByRole('button', { name: /Safe/ })).toHaveLength(2)
  })

  it('marks an asset Compromised and updates state', async () => {
    const user = userEvent.setup()
    render(<EvidenceHarness />)
    await user.click(
      screen.getByRole('button', { name: 'Mark plc_1 as Compromised' }),
    )
    expect(
      screen.getByRole('button', { name: 'Mark plc_1 as Compromised' }),
    ).toHaveAttribute('aria-pressed', 'true')
  })

  it('allows returning an asset to Unknown', async () => {
    const user = userEvent.setup()
    render(<EvidenceHarness initial={{ plc_1: 'Compromised' }} />)
    await user.click(screen.getByRole('button', { name: 'Mark plc_1 as Unknown' }))
    expect(
      screen.getByRole('button', { name: 'Mark plc_1 as Unknown' }),
    ).toHaveAttribute('aria-pressed', 'true')
  })
})

describe('Evidence in the assessment flow', () => {
  it('sends selected evidence and reruns inference when evidence changes', async () => {
    const user = userEvent.setup()
    const analyzeHandler = vi.fn()
    const restore = installFetchMock([
      { url: '/settings', method: 'GET', json: defaultSettingsPayload },
      {
        url: '/upload-topology-file',
        method: 'POST',
        json: {
          asset_count: 1,
          relationship_count: 0,
          topology: {
            assets: { plc_1: { kind: 'device', cvss_type: 5.0 } },
            relationships: [],
          },
        },
      },
      {
        url: '/analyze',
        method: 'POST',
        handler: (init) => {
          analyzeHandler(init)
          return { status: 200, json: sampleResult }
        },
      },
    ])
    render(<App />)
    await uploadSmallTopology(user)

    // First run without evidence.
    await user.click(screen.getByRole('button', { name: 'Run assessment' }))
    await waitFor(() => expect(analyzeHandler).toHaveBeenCalledTimes(1))

    // Mark evidence and rerun — the payload must carry the evidence.
    await user.click(screen.getByRole('button', { name: 'Mark plc_1 as Compromised' }))
    await user.click(screen.getByRole('button', { name: 'Run assessment' }))
    await waitFor(() => expect(analyzeHandler).toHaveBeenCalledTimes(2))

    const calls = analyzeHandler.mock.calls as Array<[RequestInit?]>
    const lastInit = calls[calls.length - 1]?.[0]
    const lastBody = JSON.parse(String(lastInit?.body)) as {
      evidence: Array<{ asset: string; state: string }>
    }
    expect(lastBody.evidence).toEqual([{ asset: 'plc_1', state: 'Compromised' }])
    restore()
  })
})
