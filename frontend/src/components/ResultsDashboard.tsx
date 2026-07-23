import { formatProbability, formatEvidence, getRiskTone } from '../utils'
import type { ResultPayload } from '../types'

export default function ResultsDashboard({
  result,
  chartData,
  riskRanking,
  setSelectedNode,
}: {
  result: ResultPayload
  chartData: Array<{ asset: string; probability: number; pinned: boolean }>
  riskRanking: Array<{ asset: string; risk: number; probability: number }>
  setSelectedNode: (id: string) => void
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <h2 className="text-xl font-semibold">Results Dashboard</h2>
      <div className="mt-4 space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl bg-slate-800 p-4">
            <p className="text-sm text-slate-400">Overall Risk</p>
            <p className="mt-2 text-2xl font-semibold text-cyan-300">
              {formatProbability(result.summary.overall_risk)}
            </p>
            <p className="mt-1 text-xs text-slate-400">
              Average risk of the top 5 highest-risk assets — this stays
              comparable across topologies of different sizes, unlike a raw
              total.
            </p>
          </div>
          <div
            className={`rounded-xl border p-4 ${getRiskTone(result.summary.risk_level)}`}
          >
            <p className="text-sm">Risk Level</p>
            <p className="mt-2 text-2xl font-semibold uppercase">
              {result.summary.risk_level}
            </p>
            <p className="mt-1 text-xs">
              Same scale as the per-asset chart below: Low {'<'} 0.30 · Moderate
              0.30–0.799 · High 0.80–1.499 · Critical ≥ 1.50
            </p>
          </div>
        </div>

        <div className="rounded-xl bg-slate-800 p-4">
          <h3 className="font-semibold">Posterior probabilities</h3>
          <p className="mt-1 text-xs text-slate-400">
            Estimated compromise probability after evidence propagates through
            the Bayesian network.
          </p>
          <div className="mt-3 max-h-56 space-y-2 overflow-y-auto pr-1 text-sm">
            {chartData.map(({ asset, probability, pinned }) => (
              <button
                key={asset}
                onClick={() => setSelectedNode(asset)}
                className="flex w-full items-center justify-between rounded-lg bg-slate-900/70 px-3 py-2 text-left hover:bg-slate-900"
              >
                <span>
                  {asset}
                  {pinned ? ' 📌' : ''}
                </span>
                <span className="font-medium text-cyan-200">
                  {formatProbability(probability)}
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-xl bg-slate-800 p-4">
          <h3 className="font-semibold">Top high-risk assets</h3>
          <p className="mt-1 text-xs text-slate-400">
            Priorities by risk score: posterior probability × configured
            consequence impact.
          </p>
          <div className="mt-3 space-y-2 text-sm">
            {riskRanking.map((entry) => (
              <button
                key={entry.asset}
                onClick={() => setSelectedNode(entry.asset)}
                className="flex w-full items-center justify-between rounded-lg bg-slate-900/70 px-3 py-2 text-left hover:bg-slate-900"
              >
                <span>{entry.asset}</span>
                <span className="font-medium text-rose-300">
                  {formatProbability(entry.risk)}
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-xl bg-slate-800 p-4">
          <h3 className="font-semibold">Highest-priority attack path</h3>
          <p className="mt-3 break-words text-sm text-slate-300">
            {result.attack_paths?.length
              ? `${((result.attack_paths[0].path as string[] | undefined) ?? []).join(' → ')}`
              : 'No path was calculated. Mark an entry asset as Compromised to analyse a specific scenario.'}
          </p>
          {result.attack_paths?.length ? (
            <>
              <p className="mt-2 text-xs text-slate-400">
                Score{' '}
                {formatProbability(
                  Number(result.attack_paths[0].score ?? 0),
                )}
                : this modelled route combines link propagation weights and
                destination risk. It prioritises investigation; it is not proof
                of a real intrusion.
              </p>
              <details className="mt-3 rounded-lg border border-slate-700 bg-slate-950/60 p-3">
                <summary className="cursor-pointer text-sm font-semibold text-cyan-200">
                  All calculated attack paths ({result.attack_paths.length})
                </summary>
                <ol className="mt-3 max-h-64 space-y-2 overflow-y-auto pr-1 text-xs text-slate-300">
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
                <p className="mt-2 text-xs text-slate-400">
                  Ordered by score. The list includes every route meeting the
                  model's minimum propagation threshold and maximum-depth
                  safeguards.
                </p>
              </details>
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}

