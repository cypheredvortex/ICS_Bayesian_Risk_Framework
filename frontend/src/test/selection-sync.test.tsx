import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import NodeDetails from '../components/NodeDetails'
import ResultsDashboard from '../components/ResultsDashboard'
import RiskPieChart from '../components/RiskPieChart'
import { sampleResult } from './helpers'

const riskRow = sampleResult.risk_scores[0]
const riskRanking = [
  {
    asset: 'plc_1',
    risk: Number(riskRow.risk),
    probability: Number(riskRow['P(compromised|evidence)']),
    severity: Number(riskRow.severity),
    impact: Number(riskRow.impact),
  },
]
const chartData = [{ asset: 'plc_1', probability: 0.5, pinned: false }]

describe('NodeDetails asset explanation', () => {
  const baseProps = {
    nodeKindMap: new Map([['plc_1', 'device']]),
    combinedProbabilities: new Map([['plc_1', 0.5]]),
    isEvidenceNode: () => false,
    result: sampleResult,
    riskRanking,
    attackPathNodes: new Set<string>(),
    edgeList: [{ source: 'hmi_1', target: 'plc_1', label: 'monitors' }],
  }

  it('reveals the actual asset name + type before the explanation on click, and hides it again', async () => {
    const user = userEvent.setup()
    render(
      <NodeDetails
        {...baseProps}
        selectedNode="plc_1"
        topologyAssets={{
          plc_1: {
            kind: 'device',
            name: 'Reactor Controller',
            type: 'PLC',
            description: 'Programmable logic controller for the reaction unit',
          },
        }}
      />,
    )
    expect(screen.queryByText('What this asset is')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /plc_1/ }))
    expect(screen.getByText('What this asset is')).toBeInTheDocument()
    // The expansion leads with the asset's actual name (distinct from the
    // ID) and its declared type, then the explanation text.
    expect(screen.getByText('Reactor Controller')).toBeInTheDocument()
    expect(screen.getByText('PLC')).toBeInTheDocument()
    expect(
      screen.getByText(/Programmable logic controller for the reaction unit/),
    ).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /plc_1/ }))
    expect(screen.queryByText('What this asset is')).not.toBeInTheDocument()
  })

  it('falls back to the type dictionary and resets on asset switch', async () => {
    const user = userEvent.setup()
    const { rerender } = render(
      <NodeDetails
        {...baseProps}
        selectedNode="dcs_1"
        nodeKindMap={new Map([['dcs_1', 'device']])}
        topologyAssets={{ dcs_1: { kind: 'device', type: 'DCS Controller' } }}
      />,
    )
    await user.click(screen.getByRole('button', { name: /dcs_1/ }))
    expect(screen.getByText(/Distributed Control System \(DCS\) controller/)).toBeInTheDocument()

    // Switching the selected asset collapses the previous explanation.
    rerender(
      <NodeDetails
        {...baseProps}
        selectedNode="plc_1"
        topologyAssets={{ plc_1: { kind: 'device', type: 'PLC' } }}
      />,
    )
    expect(screen.queryByText('What this asset is')).not.toBeInTheDocument()
  })

  it('hides the toggle when no explanation can be resolved', () => {
    // An unknown kind with no declared type/description and an opaque id
    // resolves to no explanation, so the toggle is disabled.
    render(
      <NodeDetails
        {...baseProps}
        selectedNode="QW-9000"
        nodeKindMap={new Map([['QW-9000', 'gadget']])}
        topologyAssets={{ 'QW-9000': { kind: 'gadget' } }}
      />,
    )
    expect(screen.getByRole('button', { name: /QW-9000/ })).toBeDisabled()
  })
})

describe('Shared asset-selection state', () => {
  it('highlights the selected asset in the probability and ranking lists', () => {
    const onSelect = vi.fn()
    render(
      <ResultsDashboard
        result={sampleResult}
        chartData={chartData}
        riskRanking={riskRanking}
        thresholds={{ critical: 0.75, high: 0.5, moderate: 0.25 }}
        selectedNode="plc_1"
        setSelectedNode={onSelect}
      />,
    )
    const probabilityRow = screen.getAllByRole('button', { name: /plc_1/ })[0]
    expect(probabilityRow).toHaveAttribute('data-selected')
    expect(probabilityRow).toHaveAttribute('aria-pressed', 'true')
  })

  it('leaves unrelated rows unselected', () => {
    render(
      <ResultsDashboard
        result={sampleResult}
        chartData={chartData}
        riskRanking={riskRanking}
        thresholds={{ critical: 0.75, high: 0.5, moderate: 0.25 }}
        selectedNode="other_asset"
        setSelectedNode={() => {}}
      />,
    )
    const row = screen.getAllByRole('button', { name: /plc_1/ })[0]
    expect(row).not.toHaveAttribute('data-selected')
  })

  it('highlights the selected asset inside the risk-level drill-down', async () => {
    const user = userEvent.setup()
    render(
      <RiskPieChart
        pieData={[
          { name: 'critical', value: 1 },
          { name: 'high', value: 0 },
          { name: 'moderate', value: 0 },
          { name: 'low', value: 0 },
        ]}
        embedded
        assetsByRiskLevel={{
          critical: [{ asset: 'plc_1', risk: 0.8, probability: 0.5, impact: 0.5 }],
          high: [],
          moderate: [],
          low: [],
        }}
        selectedNode="plc_1"
        setSelectedNode={() => {}}
      />,
    )
    await user.click(screen.getByRole('button', { name: 'Show Critical assets' }))
    const row = screen.getByRole('button', { name: /plc_1/ })
    expect(row).toHaveAttribute('data-selected')
  })
})
