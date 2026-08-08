import type { ReactNode } from 'react'
import { StatusDot } from './ui'

export default function Header({
  settingsButton,
  reportsButton,
  apiOnline,
  children,
}: {
  settingsButton: ReactNode
  reportsButton?: ReactNode
  apiOnline: boolean | null
  children: ReactNode
}) {
  return (
    <header className="border-b border-slate-800 bg-slate-950/70 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-6 sm:px-6">
        <div className="flex items-center gap-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-cyan-500/30 bg-cyan-500/10 shadow-[0_0_20px_rgba(34,211,238,0.12)]">
            <svg
              className="h-6 w-6 text-cyan-300"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <rect x="2.5" y="7" width="5" height="10" rx="1" />
              <rect x="9.5" y="4" width="5" height="16" rx="1" />
              <rect x="16.5" y="7" width="5" height="10" rx="1" />
              <path d="M5 12h4.5M14.5 12H19" />
            </svg>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cyan-300">
              Bayesian Cyber-Risk Analysis
            </p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-50 sm:text-[1.7rem]">
              ICS Risk Assessment Framework
            </h1>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <span
            className="badge badge-slate"
            title="Polled from the backend health endpoint every 30 s"
          >
            <StatusDot
              tone={
                apiOnline === null
                  ? 'idle'
                  : apiOnline
                    ? 'ok'
                    : 'err'
              }
            />
            {apiOnline === null
              ? 'Checking API…'
              : apiOnline
                ? 'API online'
                : 'API unreachable'}
          </span>
          {settingsButton}
          {reportsButton}
        </div>
      </div>
      {children}
    </header>
  )
}
