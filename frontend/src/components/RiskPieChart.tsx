import { useState } from 'react'
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import { riskLevelMeta } from '../constants'
import { formatProbability } from '../utils'
import { EmptyState } from './ui'

export type RiskAssetRow = {
  asset: string
  risk: number
  probability: number
  impact: number
}

export default function RiskPieChart({
  pieData,
  embedded = false,
  assetsByRiskLevel,
  setSelectedNode,
}: {
  pieData: Array<{ name: string; value: number }>
  // When embedded, the chart drops its card chrome so it can live inside the
  // Compromise probability card, directly below the probability graph.
  embedded?: boolean
  // Per-level asset lists (with risk indices) enabling the drill-down. When
  // omitted the chart stays read-only.
  assetsByRiskLevel?: Record<string, RiskAssetRow[]>
  setSelectedNode?: (id: string) => void
}) {
  const [selected, setSelected] = useState<string | null>(null)

  const hasData = pieData.some((entry) => entry.value > 0)
  const total = pieData.reduce((sum, entry) => sum + entry.value, 0)
  const interactive = Boolean(assetsByRiskLevel)

  const selectLevel = (name: string) => {
    if (!interactive) return
    setSelected((previous) => (previous === name ? null : name))
  }

  const selectedMeta = selected
    ? riskLevelMeta[selected as keyof typeof riskLevelMeta]
    : null
  const selectedAssets =
    selected && assetsByRiskLevel ? (assetsByRiskLevel[selected] ?? []) : []

  return (
    <div className={embedded ? undefined : 'card card-pad'}>
      <h2 className="card-title">Assets by Risk Level</h2>
      {hasData ? (
        <p className="card-subtitle">
          Distribution of {total} asset{total === 1 ? '' : 's'} across risk
          levels, classified with the active thresholds from settings.
          {interactive
            ? ' Click a slice or legend entry to list the assets of that level.'
            : ''}
        </p>
      ) : null}
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
                onClick={(entry: { name?: string }) =>
                  selectLevel(String(entry.name ?? ''))
                }
                cursor={interactive ? 'pointer' : 'default'}
              >
                {pieData.map((entry) => {
                  const meta =
                    riskLevelMeta[entry.name as keyof typeof riskLevelMeta]
                  // Keep the selected slice fully opaque and softly dim the
                  // others so the focus transition reads as deliberate.
                  return (
                    <Cell
                      key={entry.name}
                      fill={meta?.hex ?? '#475569'}
                      opacity={selected && selected !== entry.name ? 0.3 : 1}
                    />
                  )
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
        selected && selectedMeta ? (
          // Drilled-down detail panel. The key forces a fresh mount when the
          // selection switches, replaying the entrance animation smoothly.
          <div
            key={selected}
            className="details-panel mt-3 rounded-xl border border-slate-800 bg-slate-950/60 p-3"
            aria-label={`${selectedMeta.label} assets`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-300">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: selectedMeta.hex }}
                  aria-hidden="true"
                />
                {selectedMeta.label} — {selectedAssets.length} asset
                {selectedAssets.length === 1 ? '' : 's'}
              </p>
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="btn btn-ghost btn-sm"
              >
                <svg
                  className="h-3.5 w-3.5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M19 12H5M12 19l-7-7 7-7" />
                </svg>
                Back to overview
              </button>
            </div>
            <div className="mt-2 max-h-56 space-y-1.5 overflow-y-auto pr-1">
              {selectedAssets.length ? (
                selectedAssets.map((item, index) => (
                  <button
                    key={item.asset}
                    type="button"
                    onClick={() => setSelectedNode?.(item.asset)}
                    disabled={!setSelectedNode}
                    className="flex w-full items-center gap-3 rounded-lg bg-slate-900/70 px-3 py-2 text-left transition hover:bg-slate-900 disabled:cursor-default"
                  >
                    <span className="w-7 shrink-0 text-right font-mono text-xs text-slate-500">
                      #{index + 1}
                    </span>
                    <span className="min-w-0 flex-1 truncate font-mono text-sm text-slate-200">
                      {item.asset}
                    </span>
                    <span className="shrink-0 whitespace-nowrap font-mono text-xs text-slate-400">
                      P {formatProbability(item.probability)} ×{' '}
                      {formatProbability(item.impact)}
                      <span className="ml-2 font-semibold text-rose-300">
                        = {formatProbability(item.risk)}
                      </span>
                    </span>
                  </button>
                ))
              ) : (
                <p className="text-sm text-slate-500">
                  No assets in this category.
                </p>
              )}
            </div>
          </div>
        ) : (
          <div
            className="mt-2 flex flex-wrap justify-center gap-x-2 gap-y-2 text-xs"
            aria-label="Risk level counts"
          >
            {pieData.map((entry) => {
              const meta = riskLevelMeta[entry.name as keyof typeof riskLevelMeta]
              const active = selected === entry.name
              return (
                <button
                  key={entry.name}
                  type="button"
                  onClick={() => selectLevel(String(entry.name))}
                  disabled={!interactive}
                  aria-label={`Show ${meta?.label ?? entry.name} assets`}
                  aria-pressed={active}
                  className={`whitespace-nowrap rounded-full px-2.5 py-1 font-medium transition disabled:cursor-default ${
                    active
                      ? 'bg-slate-800 text-slate-100 ring-1 ring-slate-500'
                      : 'text-slate-300 hover:bg-slate-800/70 hover:text-slate-100'
                  }`}
                >
                  <span
                    className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full align-[-1px]"
                    style={{ backgroundColor: meta?.hex ?? '#475569' }}
                    aria-hidden="true"
                  />
                  {meta?.label ?? entry.name}: {entry.value}
                  <span className="text-slate-500">
                    {' '}
                    ({total ? Math.round((entry.value / total) * 100) : 0}%)
                  </span>
                </button>
              )
            })}
          </div>
        )
      ) : null}
    </div>
  )
}
