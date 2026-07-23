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

export default function ProbabilityChart({
  chartData,
  setSelectedNode,
}: {
  chartData: Array<{ asset: string; probability: number; pinned: boolean }>
  setSelectedNode: (id: string) => void
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <h2 className="text-xl font-semibold">Compromise probability by asset</h2>
      <p className="mt-1 text-sm text-slate-400">
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
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="asset"
                tick={{ fill: '#e2e8f0', fontSize: 12 }}
                angle={-24}
                textAnchor="end"
                height={52}
                axisLine={{ stroke: '#64748b' }}
                tickLine={{ stroke: '#64748b' }}
              />
              <YAxis
                domain={[0, 1]}
                tick={{ fill: '#cbd5e1', fontSize: 12 }}
                label={{
                  value: 'Posterior probability (0–1)',
                  angle: -90,
                  position: 'insideLeft',
                  fill: '#f8fafc',
                  fontSize: 13,
                  fontWeight: 700,
                }}
                axisLine={{ stroke: '#64748b' }}
                tickLine={{ stroke: '#64748b' }}
              />
              <Tooltip
                formatter={(value: number) => [
                  formatProbability(value),
                  'Posterior probability',
                ]}
                labelStyle={{ color: '#e2e8f0' }}
                itemStyle={{ color: '#f8fafc', fontWeight: 700 }}
                contentStyle={{
                  background: '#0f172a',
                  borderRadius: '12px',
                  border: '1px solid rgba(56, 189, 248, 0.25)',
                  color: '#f8fafc',
                }}
              />
              <Bar
                dataKey="probability"
                name="Posterior Probability"
                radius={[6, 6, 0, 0]}
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
          <div className="flex h-full items-center justify-center text-sm text-slate-500">
            Run an assessment to populate this chart.
          </div>
        )}
      </div>
    </div>
  )
}

