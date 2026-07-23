import type { ResultPayload } from '../types'
import { formatProbability } from '../utils'

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
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">
            Conditional Probability Tables
          </h2>
          <p className="mt-1 text-sm text-slate-400">
            Inspect each node's generated Noisy-OR CPT. Each row is P(node
            compromised | parent states).
          </p>
        </div>
        <input
          value={cptQuery}
          onChange={(event) => onCptQueryChange(event.target.value)}
          placeholder="Search node CPTs"
          aria-label="Search conditional probability tables"
          className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-500"
        />
      </div>
      {result?.cpts ? (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          {Object.entries(result.cpts)
            .filter(([asset]) =>
              asset
                .toLowerCase()
                .includes(cptQuery.trim().toLowerCase()),
            )
            .map(([asset, cpt]) => (
              <details
                key={asset}
                className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950/60"
              >
                <summary className="cursor-pointer px-4 py-3 font-semibold text-slate-100 hover:bg-slate-800">
                  {asset}{' '}
                  <span className="ml-2 text-xs font-normal text-slate-400">
                    parents:{' '}
                    {cpt.parents.length
                      ? cpt.parents.join(', ')
                      : 'none'}
                  </span>
                </summary>
                <div className="max-h-60 overflow-auto border-t border-slate-800">
                  <table className="w-full text-left text-xs">
                    <thead className="sticky top-0 bg-slate-800 text-slate-300">
                      <tr>
                        <th className="p-3">Parent states</th>
                        <th className="p-3">P(compromised)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cpt.rows.map((row, index) => (
                        <tr
                          key={index}
                          className="border-t border-slate-800"
                        >
                          <td className="p-3 text-slate-300">
                            {Object.entries(row.parent_state)
                              .map(
                                ([parent, state]) =>
                                  `${parent}=${state}`,
                              )
                              .join(', ') || 'Root node'}
                          </td>
                          <td className="p-3 font-semibold text-cyan-200">
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
        <p className="mt-4 text-sm text-slate-500">
          Run an assessment to generate CPTs for every node.
        </p>
      )}
    </section>
  )
}

