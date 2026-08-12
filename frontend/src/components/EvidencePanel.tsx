import { useMemo, useState } from 'react'
import type { AssetState } from '../types'
import { assetStateOrder } from '../constants'
import { Badge } from './ui'

export default function EvidencePanel({
  assets,
  evidence,
  onUpdateEvidence,
  onClearAll,
  embedded = false,
}: {
  assets: [string, Record<string, unknown>][]
  evidence: Record<string, AssetState>
  onUpdateEvidence: (asset: string, state: AssetState) => void
  // Resets every asset back to the Unknown state (single undo for the whole
  // selection — marking 30 assets off is tedious, unmarking them must not be).
  onClearAll?: () => void
  // When embedded, the panel drops its own card chrome and header so it can
  // live inside a parent disclosure (Topology & Assessment → Evidence
  // Selection). All state/logic is identical.
  embedded?: boolean
}) {
  const [query, setQuery] = useState('')

  const markedCount = useMemo(
    () =>
      Object.values(evidence).filter(
        (state) => state === 'Compromised' || state === 'Safe',
      ).length,
    [evidence],
  )

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return assets
    return assets.filter(([asset]) => asset.toLowerCase().includes(q))
  }, [assets, query])

  // Group by declared zone; assets without a zone fall into an "Unzoned" bucket.
  const grouped = useMemo(() => {
    const buckets = new Map<string, [string, Record<string, unknown>][]>()
    filtered.forEach((entry) => {
      const zone = entry[1]?.zone ? String(entry[1].zone) : 'Unzoned'
      if (!buckets.has(zone)) buckets.set(zone, [])
      buckets.get(zone)!.push(entry)
    })
    return Array.from(buckets.entries()).sort(([a], [b]) =>
      a.localeCompare(b),
    )
  }, [filtered])

  // Filter + counter toolbar, shared by both layouts.
  const toolbar = (
    <div className="flex flex-wrap items-center gap-2">
      <input
        name="evidence-filter"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Filter assets…"
        aria-label="Filter evidence assets"
        className="field field-sm w-44"
      />
      <Badge tone={markedCount > 0 ? 'cyan' : 'slate'}>
        {markedCount} of {assets.length} marked
      </Badge>
      {markedCount > 0 && onClearAll ? (
        <button
          type="button"
          onClick={onClearAll}
          className="btn btn-ghost btn-sm text-rose-300/90 hover:bg-rose-500/10 hover:text-rose-200"
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
            <path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6" />
            <path d="M10 11v6M14 11v6" />
          </svg>
          Clear all
        </button>
      ) : null}
    </div>
  )

  return (
    <div className={embedded ? undefined : 'card card-pad'}>
      {embedded ? (
        toolbar
      ) : (
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="card-title">Evidence Selection</h2>
            <p className="card-subtitle">
              Mark assets you know to be Compromised or Safe. These states are
              applied when you run the assessment and every compromise
              probability is recomputed from them.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">{toolbar}</div>
        </div>
      )}

      <div className="mt-4 max-h-80 space-y-4 overflow-y-auto pr-1">
        {assets.length === 0 ? (
          <p className="text-sm text-slate-500">
            Upload a topology to populate the evidence controls.
          </p>
        ) : grouped.length === 0 ? (
          <p className="text-sm text-slate-500">
            No assets match “{query}”.
          </p>
        ) : (
          grouped.map(([zone, entries]) => (
            <div key={zone}>
              <p className="mb-1.5 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                {zone}
                <span className="h-px flex-1 bg-slate-800" />
              </p>
              <div className="space-y-2">
                {entries.map(([asset]) => {
                  const current = evidence[asset]
                  return (
                    <div
                      key={asset}
                      className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-3 transition-colors hover:border-slate-700 lg:flex-row lg:items-center lg:justify-between"
                    >
                      <span className="font-mono text-sm font-semibold text-slate-200">
                        {asset}
                      </span>
                      <div
                        className="flex flex-wrap gap-1.5"
                        role="group"
                        aria-label={`Evidence state for ${asset}`}
                      >
                        {assetStateOrder.map((state) => {
                          const active = current === state
                          const tone =
                            state === 'Compromised'
                              ? 'border-rose-400/70 bg-rose-500/90 text-white'
                              : state === 'Safe'
                                ? 'border-emerald-400/70 bg-emerald-500/90 text-slate-950'
                                : 'border-slate-700 bg-slate-800 text-slate-300'
                          return (
                            <button
                              key={state}
                              onClick={() => onUpdateEvidence(asset, state)}
                              className={`rounded-md border px-3 py-1 text-xs font-semibold transition ${
                                active
                                  ? tone
                                  : 'border-slate-700 bg-slate-900 text-slate-400 hover:border-slate-500 hover:text-slate-200'
                              }`}
                              aria-label={`Mark ${asset} as ${state}`}
                              aria-pressed={active}
                            >
                              {state}
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
