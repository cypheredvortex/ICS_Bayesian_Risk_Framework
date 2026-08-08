import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import App from '../App'
import NodeDetails from '../components/NodeDetails'
import {
  assessmentRoutes,
  defaultSettingsPayload,
  installFetchMock,
  sampleResult,
  uploadSmallTopology,
} from './helpers'

describe('Results states', () => {
  it('shows an empty state before any assessment', async () => {
    const restore = installFetchMock([
      { url: '/settings', method: 'GET', json: defaultSettingsPayload },
    ])
    render(<App />)
    expect(
      await screen.findByText(/No assessment results yet/),
    ).toBeInTheDocument()
    expect(screen.getByText(/Run an assessment to generate CPTs/)).toBeInTheDocument()
    restore()
  })

  it('shows a loading state while the assessment is running', async () => {
    const user = userEvent.setup()
    let release: (() => void) | undefined
    const gate = new Promise<void>((resolve) => {
      release = resolve
    })
    const restore = installFetchMock([
      { url: '/settings', method: 'GET', json: defaultSettingsPayload },
      {
        url: '/upload-topology-file',
        method: 'POST',
        json: {
          asset_count: 1,
          relationship_count: 0,
          topology: {
            assets: { plc_1: { kind: 'device' } },
            relationships: [],
          },
        },
      },
      {
        url: '/analyze',
        method: 'POST',
        handler: async () => {
          await gate
          return { status: 200, json: sampleResult }
        },
      },
    ])
    render(<App />)
    await uploadSmallTopology(user)
    await user.click(screen.getByRole('button', { name: 'Run assessment' }))
    expect(
      await screen.findByText(/Running Bayesian assessment/),
    ).toBeInTheDocument()
    release?.()
    await waitFor(() =>
      expect(
        screen.getByText(/results are now on the dashboard/),
      ).toBeInTheDocument(),
    )
    restore()
  })

  it('shows a clear error when the assessment fails and keeps no result', async () => {
    const user = userEvent.setup()
    const restore = installFetchMock([
      { url: '/settings', method: 'GET', json: defaultSettingsPayload },
      {
        url: '/upload-topology-file',
        method: 'POST',
        json: {
          asset_count: 1,
          relationship_count: 0,
          topology: {
            assets: { plc_1: { kind: 'device' } },
            relationships: [],
          },
        },
      },
      {
        url: '/analyze',
        method: 'POST',
        status: 400,
        json: { detail: 'Relationship (a -> b) references unknown source asset.' },
      },
    ])
    render(<App />)
    await uploadSmallTopology(user)
    await user.click(screen.getByRole('button', { name: 'Run assessment' }))
    expect(
      await screen.findByText(
        /Relationship \(a -> b\) references unknown source asset/,
      ),
    ).toBeInTheDocument()
    expect(screen.getByText(/No assessment results yet/)).toBeInTheDocument()
    restore()
  })

  it('surfaces impossible evidence with the affected nodes', async () => {
    const user = userEvent.setup()
    const restore = installFetchMock([
      { url: '/settings', method: 'GET', json: defaultSettingsPayload },
      {
        url: '/upload-topology-file',
        method: 'POST',
        json: {
          asset_count: 1,
          relationship_count: 0,
          topology: {
            assets: {
              valve: { kind: 'physical', p_base_override: 0 },
            },
            relationships: [],
          },
        },
      },
      {
        url: '/analyze',
        method: 'POST',
        status: 400,
        json: {
          detail:
            'The supplied evidence is impossible under the current model: P(valve=1 | other evidence) is exactly 0',
          error_code: 'IMPOSSIBLE_EVIDENCE',
          affected_nodes: ['valve'],
        },
      },
    ])
    render(<App />)
    const input = await screen.findByLabelText('Upload a topology file')
    const file = new File(
      [
        JSON.stringify({
          assets: { valve: { kind: 'physical', p_base_override: 0 } },
          relationships: [],
        }),
      ],
      'valve.json',
      { type: 'application/json' },
    )
    await user.upload(input, file)
    await screen.findByText(/Loaded valve.json/)
    await user.click(screen.getByRole('button', { name: 'Mark valve as Compromised' }))
    await user.click(screen.getByRole('button', { name: 'Run assessment' }))
    expect(
      await screen.findByText(/Impossible evidence detected/),
    ).toBeInTheDocument()
    expect(await screen.findByText(/Affected nodes: valve/)).toBeInTheDocument()
    restore()
  })

  it('renders the dashboard with intrinsic, posterior, impact and risk', async () => {
    const user = userEvent.setup()
    const restore = installFetchMock(assessmentRoutes())
    render(<App />)
    await uploadSmallTopology(user)
    await user.click(screen.getByRole('button', { name: 'Run assessment' }))
    expect(
      await screen.findByText(
        'Assessment complete — results are now on the dashboard.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByText('Overall Risk (worst case)')).toBeInTheDocument()
    expect(screen.getByText('Intrinsic probability')).toBeInTheDocument()
    restore()
  })
})

describe('NodeDetails', () => {
  it('displays intrinsic probability, posterior, impact and risk distinctly', () => {
    const riskRow = sampleResult.risk_scores[0]
    render(
      <NodeDetails
        selectedNode="plc_1"
        nodeKindMap={new Map([['plc_1', 'device']])}
        combinedProbabilities={new Map([['plc_1', 0.5]])}
        isEvidenceNode={() => false}
        result={sampleResult}
        riskRanking={[
          {
            asset: 'plc_1',
            risk: Number(riskRow.risk),
            probability: Number(riskRow['P(compromised|evidence)']),
            severity: Number(riskRow.severity),
            impact: Number(riskRow.impact),
          },
        ]}
        attackPathNodes={new Set()}
        edgeList={[{ source: 'plc_1', target: 'hmi_1', label: 'connects-to' }]}
      />,
    )
    expect(screen.getByText('CVSS (effective)')).toBeInTheDocument()
    expect(screen.getByText('Intrinsic probability')).toBeInTheDocument()
    expect(screen.getByText('Posterior')).toBeInTheDocument()
    expect(screen.getByText('Consequence impact')).toBeInTheDocument()
    expect(screen.getByText('Risk index')).toBeInTheDocument()
    expect(
      screen.getByText(
        /Risk index = posterior probability × impact\. It is a ranking metric, not a probability\./,
      ),
    ).toBeInTheDocument()
  })

  it('shows a hint when no node is selected', () => {
    render(
      <NodeDetails
        selectedNode={null}
        nodeKindMap={new Map()}
        combinedProbabilities={new Map()}
        isEvidenceNode={() => false}
        result={null}
        riskRanking={[]}
        attackPathNodes={new Set()}
        edgeList={[]}
      />,
    )
    expect(screen.getByText(/Select a node in the network/)).toBeInTheDocument()
  })
})
