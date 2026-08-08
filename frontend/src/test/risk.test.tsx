import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import ResultsDashboard from '../components/ResultsDashboard'
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
  it('renders the risk level, posteriors and top assets', () => {
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
    // 'plc_1' appears in both the posteriors list and the high-risk ranking.
    expect(screen.getAllByText('plc_1').length).toBeGreaterThan(0)
    expect(screen.getByText('0.500')).toBeInTheDocument()
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
