import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import ResultsDashboard from '../components/ResultsDashboard'
import RiskPieChart from '../components/RiskPieChart'
import { formatProbability, riskLevelFor } from '../utils'
import { sampleResult } from './helpers'

const defaults = { critical: 0.75, high: 0.5, moderate: 0.25 }

describe('riskLevelFor', () => {
  it('classifies with the default thresholds', () => {
    expect(riskLevelFor(0.9, defaults)).toBe('critical')
    expect(riskLevelFor(0.75, defaults)).toBe('critical')
    expect(riskLevelFor(0.6, defaults)).toBe('high')
    expect(riskLevelFor(0.5, defaults)).toBe('high')
    expect(riskLevelFor(0.3, defaults)).toBe('moderate')
    expect(riskLevelFor(0.25, defaults)).toBe('moderate')
    expect(riskLevelFor(0.1, defaults)).toBe('low')
  })

  it('follows the active thresholds, never hardcoded constants', () => {
    const tuned = { critical: 0.4, high: 0.15, moderate: 0.1 }
    // 0.3 would be "moderate" under the defaults but "high" under the tuned
    // thresholds — proving classification is driven by configuration.
    expect(riskLevelFor(0.3, defaults)).toBe('moderate')
    expect(riskLevelFor(0.3, tuned)).toBe('high')
    expect(riskLevelFor(0.5, tuned)).toBe('critical')
    expect(riskLevelFor(0.12, tuned)).toBe('moderate')
    expect(riskLevelFor(0.05, tuned)).toBe('low')
  })

  it('treats risk as distinct from probability', () => {
    // A high probability does not imply a high risk index: risk = P × impact.
    const highProbability = 0.9
    const lowImpact = 0.1
    expect(riskLevelFor(highProbability * lowImpact, defaults)).toBe('low')
    expect(riskLevelFor(highProbability, defaults)).toBe('critical')
  })
})

describe('formatProbability', () => {
  it('formats to three decimals', () => {
    expect(formatProbability(0.123456)).toBe('0.123')
    expect(formatProbability(1)).toBe('1.000')
  })
})

describe('ResultsDashboard', () => {
  it('renders the risk level, posteriors and ranked assets', () => {
    render(
      <ResultsDashboard
        result={sampleResult}
        chartData={[{ asset: 'plc_1', probability: 0.5, pinned: false }]}
        riskRanking={[
          {
            asset: 'plc_1',
            risk: 0.25,
            probability: 0.5,
            severity: 5,
            impact: 0.5,
          },
        ]}
        thresholds={defaults}
        setSelectedNode={() => {}}
      />,
    )
    expect(screen.getByText('moderate')).toBeInTheDocument()
    // 'plc_1' appears in both the posteriors list and the risk ranking.
    expect(screen.getAllByText('plc_1').length).toBeGreaterThan(0)
    expect(screen.getByText('0.500')).toBeInTheDocument()
  })

  it('ranks every asset, not just the top five', () => {
    const riskScores = Array.from({ length: 8 }, (_, index) => ({
      asset: `asset_${index}`,
      'P(compromised|evidence)': (8 - index) / 10,
      severity: 5,
      impact: 0.5,
      risk: ((8 - index) / 10) * 0.5,
      risk_level: 'Moderate',
    }))
    const ranking = [...riskScores]
      .map((item) => ({
        asset: item.asset,
        risk: Number(item.risk),
        probability: Number(item['P(compromised|evidence)']),
        severity: Number(item.severity),
        impact: Number(item.impact),
      }))
      .sort((a, b) => b.risk - a.risk)

    render(
      <ResultsDashboard
        result={{
          ...sampleResult,
          summary: { ...sampleResult.summary, asset_count: 8 },
        }}
        chartData={[]}
        riskRanking={ranking}
        thresholds={defaults}
        setSelectedNode={() => {}}
      />,
    )
    // The section is now a complete ranking with a dynamic legend.
    expect(screen.getByText('Risk Ranking by Asset')).toBeInTheDocument()
    expect(screen.getByText('8 assets ranked')).toBeInTheDocument()
    // Every asset appears exactly once, with a visible rank.
    for (let index = 0; index < 8; index += 1) {
      expect(screen.getByText(`asset_${index}`)).toBeInTheDocument()
      expect(screen.getByText(`#${index + 1}`)).toBeInTheDocument()
    }
  })

  it('shows expandable evidence chips for large evidence sets', () => {
    const evidence = Object.fromEntries(
      Array.from({ length: 12 }, (_, index) => [`asset_${index}`, index % 2]),
    )
    render(
      <ResultsDashboard
        result={{
          ...sampleResult,
          summary: {
            ...sampleResult.summary,
            evidence_used: evidence,
            asset_count: 12,
          },
        }}
        chartData={[]}
        riskRanking={[]}
        thresholds={defaults}
        setSelectedNode={() => {}}
      />,
    )
    expect(screen.getByText('Selected Evidence')).toBeInTheDocument()
    expect(screen.getByText('12 evidence items')).toBeInTheDocument()
    // Collapsed: eight chips + a "more" badge, with a Show-all toggle.
    expect(screen.getByText('+4 more')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /Show all 12 evidence items/ }),
    ).toBeInTheDocument()
    // The posterior legend reflects the applied evidence count.
    expect(
      screen.getByText(
        /Posterior compromise probability after applying 12 selected evidence items/,
      ),
    ).toBeInTheDocument()
  })

  it('makes the highest-priority attack path score prominent', () => {
    const withAttackPaths = {
      ...sampleResult,
      attack_paths: [
        { source: 'hmi_1', path: ['hmi_1', 'plc_1'], score: 0.85 },
      ],
    }
    render(
      <ResultsDashboard
        result={withAttackPaths}
        chartData={[]}
        riskRanking={[]}
        thresholds={defaults}
        setSelectedNode={() => {}}
      />,
    )
    // The route itself (rendered both as the headline and inside the
    // "All calculated attack paths" list), a dedicated "Path score" stat
    // with the formatted score, and the priority badge are all visible.
    expect(screen.getByText('Highest-priority attack path')).toBeInTheDocument()
    expect(screen.getAllByText('hmi_1 → plc_1').length).toBeGreaterThan(0)
    expect(screen.getByText('Path score')).toBeInTheDocument()
    expect(screen.getByText('0.850')).toBeInTheDocument()
    expect(screen.getByText('Top priority')).toBeInTheDocument()
    // The explanation remains, phrased around the score it annotates.
    expect(
      screen.getByText(/combines link propagation weights with destination risk/),
    ).toBeInTheDocument()
  })

  it('shows the active threshold scale, not a hardcoded one', () => {
    render(
      <ResultsDashboard
        result={sampleResult}
        chartData={[]}
        riskRanking={[]}
        thresholds={{ critical: 0.6, high: 0.4, moderate: 0.2 }}
        setSelectedNode={() => {}}
      />,
    )
    expect(screen.getByText(/Critical ≥ 0.60/)).toBeInTheDocument()
    expect(screen.getByText(/Low < 0.20/)).toBeInTheDocument()
  })
})

describe('RiskPieChart drill-down', () => {
  const pieData = [
    { name: 'critical', value: 2 },
    { name: 'moderate', value: 1 },
  ]
  const assetsByRiskLevel = {
    critical: [
      { asset: 'plc_1', risk: 0.9, probability: 1, impact: 0.9 },
      { asset: 'hmi_1', risk: 0.8, probability: 0.9, impact: 0.889 },
    ],
    moderate: [
      { asset: 'sensor_1', risk: 0.3, probability: 0.5, impact: 0.6 },
    ],
  }

  it('lists the assets of a risk level after clicking its legend entry', async () => {
    const user = userEvent.setup()
    render(
      <RiskPieChart
        pieData={pieData}
        assetsByRiskLevel={assetsByRiskLevel}
        setSelectedNode={() => {}}
      />,
    )
    await user.click(screen.getByRole('button', { name: /Show Critical assets/ }))
    // The panel shows the category count and every asset with its risk index.
    expect(screen.getByText(/Critical — 2 assets/i)).toBeInTheDocument()
    expect(screen.getByText('plc_1')).toBeInTheDocument()
    expect(screen.getByText('hmi_1')).toBeInTheDocument()
    // The risk index appears in each row (as the "= X.XXX" product).
    expect(screen.getByText(/= 0\.900/)).toBeInTheDocument()
    expect(screen.queryByText('sensor_1')).not.toBeInTheDocument()

    // Back to overview restores the legend chips.
    await user.click(screen.getByRole('button', { name: /Back to overview/i }))
    expect(screen.queryByText(/Critical — 2 assets/i)).not.toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /Show Moderate assets/ }),
    ).toBeInTheDocument()
  })

  it('selects the asset in the network when a drill-down row is clicked', async () => {
    const onSelect = vi.fn()
    const user = userEvent.setup()
    render(
      <RiskPieChart
        pieData={pieData}
        assetsByRiskLevel={assetsByRiskLevel}
        setSelectedNode={onSelect}
      />,
    )
    await user.click(screen.getByRole('button', { name: /Show Critical assets/ }))
    await user.click(screen.getByRole('button', { name: /plc_1/ }))
    expect(onSelect).toHaveBeenCalledWith('plc_1')
  })

  it('stays read-only when no per-level data is provided', () => {
    render(<RiskPieChart pieData={pieData} />)
    expect(
      screen.getByRole('button', { name: /Show Critical assets/ }),
    ).toBeDisabled()
  })
})
