import { formatProbability, getRiskTone, riskLevelFor } from '../utils'
import type { ResultPayload, RiskThresholds } from '../types'
import { riskLevelMeta } from '../constants'
import { Badge } from './ui'
import EvidenceList from './EvidenceList'

function formatThresholdScale(t: RiskThresholds): string {
  const f = (value: number) => value.toFixed(2)
  return `Low < ${f(t.moderate)} · Moderate ${f(t.moderate)}–${f(t.high)} · High ${f(t.high)}–${f(t.critical)} · Critical ≥ ${f(t.critical)}`
}

export default function ResultsDashboard({
  result,
  chartData,
  riskRanking,
  thresholds,
  selectedNode,
  setSelectedNode,
}: {
  result: ResultPayload
  chartData: Array<{ asset: string; probability: number; pinned: boolean }>
  riskRanking: Array<{
    asset: string
    risk: number
    probability: number
    severity: number
    impact: number
  }>
  thresholds: RiskThresholds
  // Currently inspected asset: the matching probability and ranking rows are
  // highlighted with the same selection language as the bar chart.
  selectedNode?: string | null
  setSelectedNode: (id: string) => void
}) {
  const levelMeta =
    riskLevelMeta[result.summary.risk_level as keyof typeof riskLevelMeta] ??
    riskLevelMeta.low

  const evidence = result.summary.evidence_used ?? {}
  const evidenceCount = Object.keys(evidence).length

  return (
    <div className="card card-pad">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="card-title">Results Dashboard</h2>
          <p className="card-subtitle">
            Decision-ready outputs from the latest assessment run.
          </p>
        </div>
        <Badge tone={evidenceCount ? 'cyan' : 'slate'}>
          {evidenceCount
            ? `${evidenceCount} evidence item${evidenceCount === 1 ? '' : 's'}`
            : 'No evidence'}
        </Badge>
      </div>

      <div className="mt-4 space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="stat-card">
            <p className="stat-label">Overall Risk (worst case)</p>
            <p className="stat-value text-cyan-300">
              {formatProbability(result.summary.overall_risk)}
            </p>
            <p className="stat-hint">
              {result.summary.overall_risk_basis ??
                'Highest single-asset risk index in the topology.'}
            </p>
          </div>
          <div className={`stat-card border ${getRiskTone(result.summary.risk_level)}`}>
            <p className="stat-label">Risk Level</p>
            <p className="stat-value uppercase" style={{ color: levelMeta.hex }}>
              {result.summary.risk_level}
            </p>
            <p className="stat-hint">
              Risk index = posterior probability × normalised impact. Active
              scale (from settings): {formatThresholdScale(thresholds)}
            </p>
          </div>
        </div>

        {evidenceCount ? (
          <div className="stat-card">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-semibold text-slate-200">Selected Evidence</h3>
              <span className="text-xs text-slate-500">
                {evidenceCount} of {result.summary.asset_count} assets pinned to
                a known state
              </span>
            </div>
            <p className="mt-1 text-xs leading-relaxed text-slate-500">
              These states were applied when the assessment ran. Pinned assets
              keep their assigned value exactly; every other probability is
              recomputed from them through the Bayesian network.
            </p>
            <div className="mt-3">
              <EvidenceList evidence={evidence} />
            </div>
          </div>
        ) : null}

        <div className="stat-card">
          <h3 className="font-semibold text-slate-200">Posterior probabilities</h3>
          <p className="mt-1 text-xs text-slate-500">
            {evidenceCount
              ? `Posterior compromise probability after applying ${evidenceCount} selected evidence item${evidenceCount === 1 ? '' : 's'} and propagating through the Bayesian network.`
              : 'Estimated compromise probability after evidence propagates through the Bayesian network.'}
          </p>
          <div className="mt-3 max-h-64 space-y-1.5 overflow-y-auto pr-1">
            {chartData.map(({ asset, probability, pinned }) => {
              const isSelected = asset === selectedNode
              return (
                <button
                  key={asset}
                  onClick={() => setSelectedNode(asset)}
                  data-selected={isSelected || undefined}
                  aria-pressed={isSelected}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition hover:bg-slate-900 ${
                    isSelected
                      ? 'bg-slate-900 ring-1 ring-cyan-400/60'
                      : 'bg-slate-900/70'
                  }`}
                >
                  <span
                    className={`w-36 truncate font-mono text-sm ${
                      isSelected ? 'text-cyan-200' : 'text-slate-200'
                    }`}
                  >
                    {asset}
                    {pinned ? ' 📌' : ''}
                  </span>
                  <span className="progress-track flex-1" aria-hidden="true">
                    <span
                      className="progress-fill"
                      style={{ width: `${Math.min(100, probability * 100)}%` }}
                    />
                  </span>
                  <span className="w-12 shrink-0 text-right font-mono text-sm font-semibold text-cyan-200">
                    {formatProbability(probability)}
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        <div className="stat-card">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-semibold text-slate-200">Risk Ranking by Asset</h3>
            <span className="text-xs text-slate-500">
              {riskRanking.length} asset{riskRanking.length === 1 ? '' : 's'} ranked
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Every asset, ordered from highest to lowest risk index (1 =
            highest). Risk index = posterior probability × normalised
            consequence impact (severity/10 × scope). Probability and impact
            are shown separately so the product is transparent.
          </p>
          <div className="mt-3 max-h-96 space-y-1.5 overflow-y-auto pr-1">
            {riskRanking.map((entry, index) => {
              const isSelected = entry.asset === selectedNode
              return (
              <button
                key={entry.asset}
                onClick={() => setSelectedNode(entry.asset)}
                data-selected={isSelected || undefined}
                aria-pressed={isSelected}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition hover:bg-slate-900 ${
                  isSelected
                    ? 'bg-slate-900 ring-1 ring-cyan-400/60'
                    : 'bg-slate-900/70'
                }`}
              >
                <span className="w-8 shrink-0 text-right font-mono text-xs font-semibold text-slate-500">
                  #{index + 1}
                </span>
                <span
                  className={`min-w-0 flex-1 truncate font-mono text-sm ${
                    isSelected ? 'text-cyan-200' : 'text-slate-200'
                  }`}
                >
                  {entry.asset}
                </span>
                {(() => {
                  const meta =
                    riskLevelMeta[riskLevelFor(entry.risk, thresholds)]
                  return (
                    <span
                      className="hidden shrink-0 whitespace-nowrap rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide sm:inline"
                      style={{
                        color: meta.hex,
                        borderColor: `${meta.hex}55`,
                        backgroundColor: `${meta.hex}14`,
                      }}
                    >
                      {meta.label}
                    </span>
                  )
                })()}
                <span className="shrink-0 whitespace-nowrap font-mono text-xs text-slate-400">
                  P {formatProbability(entry.probability)} ×{' '}
                  {formatProbability(entry.impact)}
                  <span className="ml-2 font-semibold text-rose-300">
                    = {formatProbability(entry.risk)}
                  </span>
                </span>
              </button>
              )
            })}
          </div>
        </div>

        <div className="stat-card">
          <h3 className="font-semibold text-slate-200">
            Highest-priority attack path
          </h3>
          {result.attack_paths?.length ? (
            <>
              <p className="mt-2 break-words font-mono text-sm font-medium leading-relaxed text-slate-100">
                {((result.attack_paths[0].path as string[] | undefined) ?? []).join(' → ')}
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-3 rounded-xl border border-rose-500/20 bg-rose-500/[0.06] px-4 py-3">
                <div>
                  <p className="stat-label">Path score</p>
                  <p className="mt-1 font-mono text-3xl font-bold tracking-tight text-rose-300">
                    {formatProbability(Number(result.attack_paths[0].score ?? 0))}
                  </p>
                </div>
                <div
                  className="hidden h-10 w-px bg-slate-700 sm:block"
                  aria-hidden="true"
                />
                <p className="min-w-0 flex-1 text-xs leading-relaxed text-slate-400">
                  The score combines link propagation weights with destination
                  risk to rank investigation targets. It prioritises
                  investigation; it is not proof of a real intrusion.
                </p>
                <Badge tone="rose">Top priority</Badge>
              </div>
              <details className="details-card mt-3">
                <summary className="details-summary">
                  All calculated attack paths ({result.attack_paths.length})
                </summary>
                <ol className="max-h-64 space-y-2 overflow-y-auto border-t border-slate-800 p-3 pr-1 text-xs text-slate-300">
                  {result.attack_paths.map((path, index) => (
                    <li
                      key={`${String(path.source ?? 'source')}-${index}`}
                      className="rounded-md bg-slate-900/80 p-2"
                    >
                      <span className="font-semibold text-slate-100">
                        {index + 1}.
                      </span>{' '}
                      {((path.path as string[] | undefined) ?? []).join(' → ')}
                      <span className="ml-2 text-cyan-200">
                        score {formatProbability(Number(path.score ?? 0))}
                      </span>
                    </li>
                  ))}
                </ol>
                <p className="mt-2 text-xs text-slate-500">
                  Ordered by score. The list includes every route meeting the
                  model's minimum propagation threshold and maximum-depth
                  safeguards.
                </p>
              </details>
            </>
          ) : (
            <p className="mt-2 text-sm text-slate-400">
              No path was calculated. Mark an entry asset as Compromised to
              analyse a specific scenario.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
