import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import ProbabilityChart from '../components/ProbabilityChart'

// Note: the recharts BarChart itself does not render in jsdom (the ResizeObserver
// mock never reports dimensions), so these tests cover the component chrome that
// frames the chart: the interactivity hint and the selected-asset feedback.
describe('ProbabilityChart', () => {
  const chartData = [
    { asset: 'plc_1', probability: 0.5, pinned: false },
    { asset: 'hmi_1', probability: 0.2, pinned: false },
  ]

  it('hints that clicking a bar opens the Node Details panel', () => {
    render(
      <ProbabilityChart
        chartData={chartData}
        setSelectedNode={() => {}}
        pieData={[]}
      />,
    )
    expect(
      screen.getByText(/Click a bar to inspect that asset's details/),
    ).toBeInTheDocument()
  })

  it('confirms the selected asset and points to the Node Details panel', () => {
    render(
      <ProbabilityChart
        chartData={chartData}
        setSelectedNode={() => {}}
        pieData={[]}
        selectedAsset="plc_1"
      />,
    )
    expect(screen.getByText(/Selected asset:/)).toBeInTheDocument()
    expect(screen.getByText('plc_1')).toBeInTheDocument()
    expect(screen.getByText(/Node Details panel above/)).toBeInTheDocument()
  })

  it('shows the empty state when there is no probability data', () => {
    render(
      <ProbabilityChart chartData={[]} setSelectedNode={() => {}} pieData={[]} />,
    )
    expect(screen.getByText('No probability data')).toBeInTheDocument()
  })
})
