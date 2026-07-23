import { formatEvidence } from '../utils'
import type { ResultPayload } from '../types'

export default function BayesianResults({
  result,
}: {
  result: ResultPayload | null
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <h2 className="text-xl font-semibold">Bayesian Results</h2>
      <p className="mt-1 text-sm text-slate-400">
        Run context and model outputs. Evidence is what you supplied;
        probabilities and rankings are calculated from that evidence and the
        topology.
      </p>
      <div className="mt-4 rounded-xl bg-slate-950/80 p-4 text-sm">
        {result ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Evidence used</span>
              <span className="max-w-[65%] text-right font-semibold text-white">
                {formatEvidence(result.evidence_used)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Assets</span>
              <span className="font-semibold text-white">
                {result.summary.asset_count}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Connections</span>
              <span className="font-semibold text-white">
                {result.summary.relationship_count}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Run time</span>
              <span className="font-semibold text-white">
                {Number(result.timings?.total_time_seconds ?? 0).toFixed(3)}s
              </span>
            </div>
          </div>
        ) : (
          <p className="text-slate-400">No assessment results available.</p>
        )}
      </div>
    </div>
  )
}

