import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getProbabilityColor, formatProbability } from '../utils'
import { EmptyState } from './ui'
import RiskPieChart, { type RiskAssetRow } from './RiskPieChart'

export default function ProbabilityChart({
  chartData,
  setSelectedNode,
  pieData,
  assetsByRiskLevel,
}: {
  chartData: Array<{ asset: string; probability: number; pinned: boolean }>
  setSelectedNode: (id: string) => void
  // Risk-level distribution, rendered below the probability graph so the
  // Probability → Risk relationship is visually obvious.
  pieData: Array<{ name: string; value: number }>
  // Per-level asset lists powering the pie chart drill-down.
  assetsByRiskLevel?: Record<string, RiskAssetRow[]>
}) {
  return (
    <div className="card card-pad">
      <h2 className="card-title">Compromise probability by asset</h2>
      <p className="card-subtitle">
        Posterior probability for each asset after the current evidence is
        applied. This chart shows probability, not the risk score.
      </p>
      <div className="mt-4 h-80 w-full">
        {chartData.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              margin={{ top: 10, right: 12, left: 0, bottom: 24 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis
                dataKey="asset"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                angle={-24}
                textAnchor="end"
                height={52}
                axisLine={{ stroke: '#334155' }}
                tickLine={{ stroke: '#334155' }}
              />
              <YAxis
                domain={[0, 1]}
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                tickFormatter={(value: number) => value.toFixed(2)}
                label={{
                  value: 'Posterior probability (0–1)',
                  angle: -90,
                  position: 'insideLeft',
                  fill: '#94a3b8',
                  fontSize: 11,
                  fontWeight: 600,
                }}
                axisLine={{ stroke: '#334155' }}
                tickLine={{ stroke: '#334155' }}
              />
              <Tooltip
                cursor={{ fill: 'rgba(148, 163, 184, 0.08)' }}
                formatter={(value: number) => [
                  formatProbability(value),
                  'Posterior probability',
                ]}
                labelStyle={{ color: '#e2e8f0', fontWeight: 700 }}
                itemStyle={{ color: '#f8fafc', fontWeight: 700 }}
                contentStyle={{
                  background: '#0f172a',
                  borderRadius: '10px',
                  border: '1px solid #1e293b',
                  color: '#f8fafc',
                  fontSize: '12px',
                }}
              />
              <Bar
                dataKey="probability"
                name="Posterior Probability"
                radius={[5, 5, 0, 0]}
                onClick={(entry: { asset: string }) =>
                  setSelectedNode(entry.asset)
                }
                cursor="pointer"
              >
                {chartData.map((entry) => (
                  <Cell
                    key={entry.asset}
                    fill={getProbabilityColor(entry.probability)}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <EmptyState
            title="No probability data"
            hint="Run an assessment to populate this chart."
          />
        )}
      </div>

      {/* Risk ranking — the direct interpretation of the probabilities above:
          assets classified into risk levels with the active thresholds. */}
      <div className="mt-6 border-t border-slate-800 pt-6">
        <RiskPieChart
          pieData={pieData}
          embedded
          assetsByRiskLevel={assetsByRiskLevel}
          setSelectedNode={setSelectedNode}
        />
      </div>
    </div>
  )
}
