import type { AssetState } from '../types'
import { assetStateOrder } from '../constants'

export default function EvidencePanel({
  assets,
  evidence,
  onUpdateEvidence,
}: {
  assets: [string, Record<string, unknown>][]
  evidence: Record<string, AssetState>
  onUpdateEvidence: (asset: string, state: AssetState) => void
}) {
  return (
    <section>
      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="text-xl font-semibold">Evidence Selection</h2>
        <div className="mt-4 max-h-72 space-y-3 overflow-y-auto pr-1">
          {assets.length === 0 ? (
            <p className="text-sm text-slate-400">
              Upload a topology to populate the evidence controls.
            </p>
          ) : (
            assets.map(([asset]) => (
              <div
                key={asset}
                className="flex flex-col gap-3 rounded-xl bg-slate-800 p-3 lg:flex-row lg:items-center lg:justify-between"
              >
                <span className="font-medium">{asset}</span>
                <div className="flex flex-wrap gap-2">
                  {assetStateOrder.map((state) => (
                    <button
                      key={state}
                      onClick={() => onUpdateEvidence(asset, state)}
                      className={`rounded px-3 py-1 text-sm transition ${
                        evidence[asset] === state
                          ? 'bg-cyan-500 text-slate-950'
                          : 'bg-slate-700 text-white hover:bg-slate-600'
                      }`}
                      aria-label={`Mark ${asset} as ${state}`}
                      aria-pressed={evidence[asset] === state}
                    >
                      {state}
                    </button>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  )
}

