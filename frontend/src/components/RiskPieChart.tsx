import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import { riskLevelMeta } from '../constants'
import { EmptyState } from './ui'

export default function RiskPieChart({
  pieData,
}: {
  pieData: Array<{ name: string; value: number }>
}) {
  const hasData = pieData.some((entry) => entry.value > 0)
  const total = pieData.reduce((sum, entry) => sum + entry.value, 0)

  return (
    <div className="card card-pad">
      <h2 className="card-title">Risk Ranking</h2>
      <p className="card-subtitle">
        Distribution of assets across risk levels, classified with the active
        thresholds from settings.
      </p>
      <div className="mt-4 h-72 w-full">
        {hasData ? (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={pieData}
                dataKey="value"
                nameKey="name"
                innerRadius={58}
                outerRadius={96}
                paddingAngle={3}
                stroke="#0f172a"
                strokeWidth={2}
                label={false}
                labelLine={false}
              >
                {pieData.map((entry) => {
                  const meta =
                    riskLevelMeta[entry.name as keyof typeof riskLevelMeta]
                  return <Cell key={entry.name} fill={meta?.hex ?? '#475569'} />
                })}
              </Pie>
              <Tooltip
                formatter={(value: number) => [`${value} assets`, 'Count']}
                contentStyle={{
                  background: '#0f172a',
                  borderRadius: '10px',
                  border: '1px solid #1e293b',
                  color: '#f8fafc',
                  fontSize: '12px',
                }}
                labelStyle={{ color: '#f8fafc', fontWeight: 700 }}
                itemStyle={{ color: '#f8fafc' }}
              />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <EmptyState
            title="No risk distribution"
            hint="Run an assessment to see the risk-level breakdown."
          />
        )}
      </div>
      {hasData ? (
        <div
          className="mt-2 flex flex-wrap justify-center gap-x-5 gap-y-2 text-xs"
          aria-label="Risk level counts"
        >
          {pieData.map((entry) => {
            const meta = riskLevelMeta[entry.name as keyof typeof riskLevelMeta]
            return (
              <span key={entry.name} className="whitespace-nowrap text-slate-300">
                <span
                  className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: meta?.hex ?? '#475569' }}
                />
                {meta?.label ?? entry.name}: {entry.value}
                <span className="text-slate-500">
                  {' '}
                  ({total ? Math.round((entry.value / total) * 100) : 0}%)
                </span>
              </span>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}
