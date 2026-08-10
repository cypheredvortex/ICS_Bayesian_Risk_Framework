import { useState } from 'react'
import { Badge } from './ui'

const STATE_META = {
  1: {
    label: 'Compromised',
    chip: 'border-rose-500/40 bg-rose-500/10 text-rose-300',
    text: 'text-rose-300',
  },
  0: {
    label: 'Safe',
    chip: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
    text: 'text-emerald-300',
  },
} as const

/**
 * Compact, expandable evidence display.
 *
 * Handles any number of selected evidence items without breaking the parent
 * card layout: items render as wrapping chips (long names truncate with a
 * hover tooltip), and when the set exceeds `maxVisible` the list collapses
 * to a summary with a "Show all / Show fewer" toggle. When expanded, the
 * list scrolls inside a bounded container so a very large evidence set never
 * pushes the card beyond its natural height.
 */
export default function EvidenceList({
  evidence,
  emptyHint = 'No evidence was applied — probabilities come from the topology and configured assumptions.',
  maxVisible = 8,
}: {
  /** asset id → state (1 = Compromised, 0 = Safe), exactly as returned by the API */
  evidence: Record<string, number>
  emptyHint?: string
  /** how many chips are shown before the set becomes expandable */
  maxVisible?: number
}) {
  const [expanded, setExpanded] = useState(false)
  const entries = Object.entries(evidence)

  if (!entries.length) {
    return <p className="text-sm leading-relaxed text-slate-500">{emptyHint}</p>
  }

  const hiddenCount = Math.max(0, entries.length - maxVisible)
  const visible = expanded || hiddenCount === 0 ? entries : entries.slice(0, maxVisible)

  return (
    <div>
      {expanded ? (
        <div className="max-h-48 space-y-1.5 overflow-y-auto pr-1">
          {visible.map(([asset, state]) => {
            const meta = STATE_META[state === 1 ? 1 : 0]
            return (
              <div
                key={asset}
                className="flex items-center justify-between gap-3 rounded-lg bg-slate-900/70 px-3 py-1.5 text-xs"
              >
                <span className="min-w-0 truncate font-mono text-slate-200" title={asset}>
                  {asset}
                </span>
                <span
                  className={`shrink-0 text-[10px] font-semibold uppercase tracking-wide ${meta.text}`}
                >
                  {meta.label}
                </span>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-1.5">
          {visible.map(([asset, state]) => {
            const meta = STATE_META[state === 1 ? 1 : 0]
            return (
              <span
                key={asset}
                title={`${asset}: ${meta.label}`}
                className={`inline-flex min-w-0 max-w-full items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${meta.chip}`}
              >
                <span className="min-w-0 truncate font-mono">{asset}</span>
                <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide opacity-80">
                  {meta.label}
                </span>
              </span>
            )
          })}
          {hiddenCount > 0 ? (
            <Badge tone="cyan">+{hiddenCount} more</Badge>
          ) : null}
        </div>
      )}
      {hiddenCount > 0 ? (
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          className="mt-2 text-xs font-semibold text-cyan-300 transition-colors hover:text-cyan-200"
          aria-expanded={expanded}
        >
          {expanded
            ? `Show fewer (${maxVisible})`
            : `Show all ${entries.length} evidence items`}
        </button>
      ) : null}
    </div>
  )
}
