import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

export default function RiskPieChart({
  pieData,
}: {
  pieData: Array<{ name: string; value: number }>
}) {
  const hasData = pieData.some((entry) => entry.value > 0)

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <h2 className="text-xl font-semibold">Risk Ranking</h2>
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
                label={false}
                labelLine={false}
              >
                <Cell fill="#fb7185" />
                <Cell fill="#f59e0b" />
                <Cell fill="#38bdf8" />
                <Cell fill="#34d399" />
              </Pie>
              <Tooltip
                formatter={(value: number) => [`${value} assets`, 'Count']}
                contentStyle={{
                  background: '#0f172a',
                  border: '1px solid rgba(56, 189, 248, 0.25)',
                  color: '#f8fafc',
                }}
                labelStyle={{ color: '#f8fafc', fontWeight: 700 }}
                itemStyle={{ color: '#f8fafc' }}
              />
              <Legend wrapperStyle={{ color: '#e2e8f0' }} />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-slate-500">
            Run an assessment to see the risk-level breakdown.
          </div>
        )}
      </div>
      {hasData ? (
        <div
          className="mt-2 flex flex-wrap justify-center gap-x-4 gap-y-2 text-xs"
          aria-label="Risk level counts"
        >
          {pieData.map((entry, index) => (
            <span key={entry.name} className="whitespace-nowrap text-slate-200">
              <span
                className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full"
                style={{
                  backgroundColor: [
                    '#fb7185',
                    '#f59e0b',
                    '#38bdf8',
                    '#34d399',
                  ][index],
                }}
              />
              {entry.name[0].toUpperCase() + entry.name.slice(1)}:{' '}
              {entry.value}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  )
}

