import type { ResultPayload } from '../types'
import { formatProbability } from '../utils'
import { EmptyState } from './ui'

export default function CptSection({
  result,
  cptQuery,
  onCptQueryChange,
}: {
  result: ResultPayload | null
  cptQuery: string
  onCptQueryChange: (value: string) => void
}) {
  return (
    <section className="card card-pad">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="card-title">Conditional Probability Tables</h2>
          <p className="card-subtitle">
            Inspect each node's generated Noisy-OR CPT. Each row is P(node
            compromised | parent states) = 1 − (1 − leak) · Π(1 − wᵢ) over the
            active parents, where leak is the node's intrinsic probability and
            wᵢ are the edge causal weights.
          </p>
        </div>
        <input
          value={cptQuery}
          onChange={(event) => onCptQueryChange(event.target.value)}
          placeholder="Search node CPTs"
          aria-label="Search conditional probability tables"
          className="field w-52"
        />
      </div>
      {result?.cpts ? (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          {Object.entries(result.cpts)
            .filter(([asset]) =>
              asset.toLowerCase().includes(cptQuery.trim().toLowerCase()),
            )
            .map(([asset, cpt]) => (
              <details key={asset} className="details-card">
                <summary className="details-summary">
                  <span className="font-mono">{asset}</span>
                  <span className="text-xs font-normal text-slate-400">
                    parents:{' '}
                    {cpt.parents.length ? cpt.parents.join(', ') : 'none'}
                  </span>
                </summary>
                <div className="max-h-60 overflow-auto border-t border-slate-800">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr>
                        <th className="table-th">Parent states</th>
                        <th className="table-th">P(compromised)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cpt.rows.map((row, index) => (
                        <tr key={index} className="transition-colors hover:bg-slate-900/60">
                          <td className="table-td font-mono text-slate-300">
                            {Object.entries(row.parent_state)
                              .map(([parent, state]) => `${parent}=${state}`)
                              .join(', ') || 'Root node'}
                          </td>
                          <td className="table-td font-semibold text-cyan-200">
                            {formatProbability(row.p_compromised)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            ))}
        </div>
      ) : (
        <div className="mt-4">
          <EmptyState
            title="No CPTs generated yet"
            hint="Run an assessment to generate CPTs for every node."
          />
        </div>
      )}
    </section>
  )
}
