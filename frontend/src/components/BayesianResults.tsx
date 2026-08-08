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
