import type { ReactNode } from 'react'

/** Shared design-system primitives. Every panel composes these so the
 *  application keeps one coherent visual language. */

export function Card({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return <section className={`card card-pad ${className}`}>{children}</section>
}

export type BadgeTone =
  | 'cyan'
  | 'slate'
  | 'emerald'
  | 'amber'
  | 'rose'
  | 'violet'

const badgeToneClass: Record<BadgeTone, string> = {
  cyan: 'badge-cyan',
  slate: 'badge-slate',
  emerald: 'badge-emerald',
  amber: 'badge-amber',
  rose: 'badge-rose',
  violet: 'badge-violet',
}

export function Badge({
  tone = 'slate',
  children,
  title,
}: {
  tone?: BadgeTone
  children: ReactNode
  title?: string
}) {
  return (
    <span className={`badge ${badgeToneClass[tone]}`} title={title}>
      {children}
    </span>
  )
}

export function StatusDot({ tone }: { tone: 'ok' | 'warn' | 'err' | 'idle' }) {
  const cls = {
    ok: 'status-dot-ok',
    warn: 'status-dot-warn',
    err: 'status-dot-err',
    idle: 'status-dot-idle',
  }[tone]
  return <span className={`status-dot ${cls}`} aria-hidden="true" />
}

export function Spinner({ label = 'Working…' }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-slate-400">
      <svg
        className="h-4 w-4 animate-spin text-cyan-400"
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden="true"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-90"
          fill="currentColor"
          d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
        />
      </svg>
      {label}
    </span>
  )
}

export function EmptyState({
  icon,
  title,
  hint,
}: {
  icon?: ReactNode
  title: string
  hint?: string
}) {
  return (
    <div className="flex h-full min-h-[160px] flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-800 bg-slate-950/40 p-6 text-center">
      {icon ? <span className="text-slate-500">{icon}</span> : null}
      <p className="text-sm font-medium text-slate-400">{title}</p>
      {hint ? <p className="max-w-sm text-xs leading-relaxed text-slate-500">{hint}</p> : null}
    </div>
  )
}

/** Label / value row for analytical metrics (monospace value). */
export function KvRow({
  label,
  value,
  hint,
  tone,
  className = '',
}: {
  label: string
  value: ReactNode
  hint?: string
  tone?: 'default' | 'cyan' | 'amber' | 'rose' | 'violet' | 'emerald'
  className?: string
}) {
  const toneClass =
    tone === 'cyan'
      ? 'text-cyan-300'
      : tone === 'amber'
        ? 'text-amber-300'
        : tone === 'rose'
          ? 'text-rose-300'
          : tone === 'violet'
            ? 'text-violet-300'
            : tone === 'emerald'
              ? 'text-emerald-300'
              : 'text-slate-100'
  return (
    <div className={className}>
      <div className="kv-row">
        <span className="kv-label">{label}</span>
        <span className={`kv-value ${toneClass}`}>{value}</span>
      </div>
      {hint ? <p className="pb-1 text-xs leading-relaxed text-slate-500">{hint}</p> : null}
    </div>
  )
}

