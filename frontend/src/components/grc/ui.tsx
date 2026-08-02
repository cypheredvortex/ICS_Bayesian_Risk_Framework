// ═══════════════════════════════════════════════════════════════
// GRC & Audit Platform — Shared UI Kit
// Sophisticated design-system primitives used across all modules.
// ═══════════════════════════════════════════════════════════════

import type { ReactNode } from 'react'

// ── Badge ───────────────────────────────────────────────────────

export type Tone = 'green' | 'amber' | 'rose' | 'slate' | 'cyan' | 'violet' | 'blue'

export const TONE_CLASSES: Record<Tone, string> = {
  green: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
  amber: 'bg-amber-500/15 text-amber-300 ring-amber-500/30',
  rose: 'bg-rose-500/15 text-rose-300 ring-rose-500/30',
  slate: 'bg-slate-500/15 text-slate-300 ring-slate-500/30',
  cyan: 'bg-cyan-500/15 text-cyan-300 ring-cyan-500/30',
  violet: 'bg-violet-500/15 text-violet-300 ring-violet-500/30',
  blue: 'bg-blue-500/15 text-blue-300 ring-blue-500/30',
}

export function Badge({
  value,
  tone = 'slate',
  title,
}: {
  value: ReactNode
  tone?: Tone
  title?: string
}) {
  return (
    <span
      title={title}
      className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${TONE_CLASSES[tone]}`}
    >
      {value}
    </span>
  )
}

// ── Button ──────────────────────────────────────────────────────

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'success'

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary:
    'bg-cyan-600 text-white shadow-lg shadow-cyan-600/20 hover:bg-cyan-500 focus-visible:ring-cyan-500/50',
  secondary:
    'border border-slate-700 bg-slate-900 text-slate-200 hover:border-cyan-500/50 hover:text-cyan-200 focus-visible:ring-cyan-500/30',
  ghost:
    'text-slate-300 hover:bg-slate-800 hover:text-slate-100 focus-visible:ring-slate-500/30',
  danger:
    'bg-rose-600 text-white shadow-lg shadow-rose-600/20 hover:bg-rose-500 focus-visible:ring-rose-500/50',
  success:
    'bg-emerald-600 text-white shadow-lg shadow-emerald-600/20 hover:bg-emerald-500 focus-visible:ring-emerald-500/50',
}

export function Button({
  children,
  variant = 'primary',
  className = '',
  disabled,
  onClick,
  type = 'button',
  title,
}: {
  children: ReactNode
  variant?: ButtonVariant
  className?: string
  disabled?: boolean
  onClick?: () => void
  type?: 'button' | 'submit'
  title?: string
}) {
  return (
    <button
      type={type}
      title={title}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 disabled:cursor-not-allowed disabled:opacity-50 ${BUTTON_VARIANTS[variant]} ${className}`}
    >
      {children}
    </button>
  )
}

// ── Card ────────────────────────────────────────────────────────

export function Card({
  children,
  className = '',
  hover = false,
}: {
  children: ReactNode
  className?: string
  hover?: boolean
}) {
  return (
    <div
      className={`rounded-2xl border border-slate-800 bg-slate-900/70 backdrop-blur transition-shadow ${
        hover ? 'hover:border-slate-700 hover:shadow-xl hover:shadow-slate-950/50' : ''
      } ${className}`}
    >
      {children}
    </div>
  )
}

export function CardHeader({
  title,
  subtitle,
  action,
}: {
  title: string
  subtitle?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-800 px-5 py-4">
      <div>
        <h3 className="text-base font-semibold text-slate-100">{title}</h3>
        {subtitle ? <p className="mt-0.5 text-xs text-slate-400">{subtitle}</p> : null}
      </div>
      {action ? <div className="flex items-center gap-2">{action}</div> : null}
    </div>
  )
}

// ── StatCard ────────────────────────────────────────────────────

export function StatCard({
  label,
  value,
  tone = 'cyan',
  icon,
  sublabel,
  progress,
}: {
  label: string
  value: ReactNode
  tone?: Tone
  icon?: ReactNode
  sublabel?: ReactNode
  progress?: number // 0..100
}) {
  const accents: Record<Tone, string> = {
    cyan: 'from-cyan-500/20 to-cyan-500/0 text-cyan-300',
    green: 'from-emerald-500/20 to-emerald-500/0 text-emerald-300',
    amber: 'from-amber-500/20 to-amber-500/0 text-amber-300',
    rose: 'from-rose-500/20 to-rose-500/0 text-rose-300',
    slate: 'from-slate-500/20 to-slate-500/0 text-slate-300',
    violet: 'from-violet-500/20 to-violet-500/0 text-violet-300',
    blue: 'from-blue-500/20 to-blue-500/0 text-blue-300',
  }
  return (
    <Card className={`relative overflow-hidden bg-gradient-to-br ${accents[tone]}`}>
      <div className="p-5">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-slate-400">
            {label}
          </p>
          {icon ? <span className="text-xl opacity-80">{icon}</span> : null}
        </div>
        <p className="mt-2 text-3xl font-bold tracking-tight">{value}</p>
        {sublabel ? <p className="mt-1 text-xs text-slate-400">{sublabel}</p> : null}
        {typeof progress === 'number' ? (
          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full rounded-full bg-current transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
            />
          </div>
        ) : null}
      </div>
    </Card>
  )
}

// ── EmptyState / Spinner ────────────────────────────────────────

export function EmptyState({
  message,
  action,
}: {
  message: string
  action?: ReactNode
}) {
  return (
    <Card className="flex flex-col items-center justify-center gap-3 p-10 text-center">
      <div className="text-3xl opacity-40">📭</div>
      <p className="text-sm text-slate-400">{message}</p>
      {action ? <div className="mt-2">{action}</div> : null}
    </Card>
  )
}

export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 p-10">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-700 border-t-cyan-400" />
      <p className="text-sm text-slate-400">{label}</p>
    </div>
  )
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-rose-500/30 bg-rose-500/10 px-5 py-4 text-sm text-rose-200">
      <span>⚠️ {message}</span>
      {onRetry ? (
        <Button variant="secondary" onClick={onRetry} className="shrink-0">
          Retry
        </Button>
      ) : null}
    </div>
  )
}

// ── ProgressBar ─────────────────────────────────────────────────

export function ProgressBar({
  value,
  tone = 'cyan',
  label,
}: {
  value: number
  tone?: Tone
  label?: string
}) {
  const bar: Record<Tone, string> = {
    cyan: 'bg-cyan-500',
    green: 'bg-emerald-500',
    amber: 'bg-amber-500',
    rose: 'bg-rose-500',
    slate: 'bg-slate-500',
    violet: 'bg-violet-500',
    blue: 'bg-blue-500',
  }
  return (
    <div>
      {label ? (
        <div className="mb-1 flex items-center justify-between text-xs text-slate-400">
          <span>{label}</span>
          <span className="font-medium text-slate-300">{Math.round(value)}%</span>
        </div>
      ) : null}
      <div className="h-2 overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full ${bar[tone]} transition-all duration-500`}
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
    </div>
  )
}

// ── Segmented Tabs ──────────────────────────────────────────────

export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: Array<{ id: T; label: string; icon?: string; count?: number }>
  active: T
  onChange: (id: T) => void
}) {
  return (
    <div className="flex flex-wrap gap-1 rounded-xl border border-slate-800 bg-slate-900 p-1">
      {tabs.map((tab) => {
        const isActive = tab.id === active
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              isActive
                ? 'bg-cyan-600/20 text-cyan-200 ring-1 ring-cyan-500/30'
                : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
            }`}
          >
            {tab.icon ? <span>{tab.icon}</span> : null}
            {tab.label}
            {typeof tab.count === 'number' ? (
              <span
                className={`rounded-full px-1.5 py-0.5 text-[10px] ${
                  isActive ? 'bg-cyan-500/30 text-cyan-100' : 'bg-slate-800 text-slate-400'
                }`}
              >
                {tab.count}
              </span>
            ) : null}
          </button>
        )
      })}
    </div>
  )
}

