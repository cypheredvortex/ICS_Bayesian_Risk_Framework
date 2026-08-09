import { formatEvidence } from '../utils'
import type { ResultPayload } from '../types'
import { EmptyState, KvRow } from './ui'

export default function BayesianResults({
  result,
  embedded = false,
}: {
  result: ResultPayload | null
  // When embedded, the panel drops its card chrome and title so it can live
  // inside a parent disclosure (Network Viewer → Bayesian Results). All
  // content and logic are identical.
  embedded?: boolean
}) {
  const body = (
    <>
      <p className="card-subtitle">
        Run context and model outputs. Evidence is what you supplied;
        probabilities and rankings are calculated from that evidence and the
        topology.
      </p>
      <div className="mt-4">
        {result ? (
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-3">
            <div className="mt-1">
              <KvRow
                label="Evidence used"
                value={
                  <span className="max-w-[280px] break-words text-right">
                    {formatEvidence(result.evidence_used)}
                  </span>
                }
              />
              <KvRow label="Assets" value={result.summary.asset_count} />
              <KvRow
                label="Connections"
                value={result.summary.relationship_count}
              />
              <KvRow
                label="Run time"
                value={`${Number(result.timings?.total_time_seconds ?? 0).toFixed(3)}s`}
                tone="cyan"
              />
              <KvRow
                label="Topology"
                value={
                  <span className="max-w-[280px] truncate">
                    {result.summary.topology}
                  </span>
                }
              />
              {(() => {
                const snapshot = result.settings_used
                const logistic =
                  (snapshot?.cvss_logistic_params as
                    | { k?: number; x0?: number }
                    | undefined) ?? {}
                const thresholds = (snapshot?.risk_thresholds as
                  | { critical?: number; high?: number; moderate?: number }
                  | undefined) ?? {}
                const nonDefault = result.summary.non_default_settings ?? []
                const t = (value: number) => value.toFixed(2)
                if (!snapshot || Object.keys(snapshot).length === 0) return null
                return (
                  <>
                    <KvRow
                      label="Settings used"
                      value={
                        <span className="max-w-[280px] break-words text-right font-mono text-[11px]">
                          {String(snapshot.cvss_mapping ?? 'logistic')} · k=
                          {Number(logistic.k ?? 0.8)} · x0=
                          {Number(logistic.x0 ?? 5.0)} · impact_w=
                          {Number(snapshot.impact_weight ?? 1.0)}
                          <span className="block text-slate-500">
                            Low &lt; {t(thresholds.moderate ?? 0.25)} · Moderate{' '}
                            {t(thresholds.moderate ?? 0.25)}–
                            {t(thresholds.high ?? 0.5)} · High{' '}
                            {t(thresholds.high ?? 0.5)}–
                            {t(thresholds.critical ?? 0.75)} · Critical ≥{' '}
                            {t(thresholds.critical ?? 0.75)}
                          </span>
                        </span>
                      }
                      tone="violet"
                    />
                    {nonDefault.length > 0 ? (
                      <KvRow
                        label="Non-default settings"
                        value={
                          <span className="max-w-[280px] break-words text-right text-[11px] text-amber-300">
                            {nonDefault.map(([key]) => key).join(', ')}
                          </span>
                        }
                        tone="amber"
                      />
                    ) : null}
                  </>
                )
              })()}
            </div>
          </div>
        ) : (
          <EmptyState
            title="No assessment results"
            hint="Run an assessment to see the model context and outputs here."
          />
        )}
      </div>
    </>
  )

  if (embedded) {
    return <div>{body}</div>
  }
  return (
    <div className="card card-pad">
      <h2 className="card-title">Bayesian Results</h2>
      {body}
    </div>
  )
}
