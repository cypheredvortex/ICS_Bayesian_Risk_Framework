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
  selectedAsset,
}: {
  chartData: Array<{ asset: string; probability: number; pinned: boolean }>
  setSelectedNode: (id: string) => void
  // Risk-level distribution, rendered below the probability graph so the
  // Probability → Risk relationship is visually obvious.
  pieData: Array<{ name: string; value: number }>
  // Per-level asset lists powering the pie chart drill-down.
  assetsByRiskLevel?: Record<string, RiskAssetRow[]>
  // Currently inspected asset; its bar is outlined so the selection made
  // elsewhere (network, ranking, this chart) stays visible in the graph.
  selectedAsset?: string | null
}) {
  return (
    <div className="card card-pad">
      <h2 className="card-title">Compromise probability by asset</h2>
      <p className="card-subtitle">
        Posterior probability for each asset after the current evidence is
        applied. This chart shows probability, not the risk score. Click a bar
        to inspect that asset's details in the Node Details panel.
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
                {chartData.map((entry) => {
                  const isSelected = entry.asset === selectedAsset
                  return (
                    <Cell
                      key={entry.asset}
                      fill={getProbabilityColor(entry.probability)}
                      stroke={isSelected ? '#22d3ee' : 'transparent'}
                      strokeWidth={isSelected ? 2 : 0}
                      opacity={isSelected ? 1 : 0.9}
                    />
                  )
                })}
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

      {/* Feedback for the bar click: the Node Details panel lives above this
          section, so confirm the selection here even while it scrolls away. */}
      {selectedAsset ? (
        <p className="mt-3 text-xs leading-relaxed text-slate-400">
          Selected asset:{' '}
          <span className="font-mono font-semibold text-cyan-300">
            {selectedAsset}
          </span>{' '}
          — its details are shown in the Node Details panel above.
        </p>
      ) : null}

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
