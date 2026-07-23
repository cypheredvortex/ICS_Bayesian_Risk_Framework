import type { ReactNode } from 'react'

export default function Header({
  settingsButton,
  apiIndicator,
  children,
}: {
  settingsButton: ReactNode
  apiIndicator: ReactNode
  children: ReactNode
}) {
  return (
    <header className="border-b border-slate-800 bg-slate-900/80 p-6 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-cyan-300">
            SOC / Bayesian Risk Console
          </p>
          <h1 className="mt-2 text-3xl font-semibold">
            ICS Risk Assessment Framework
          </h1>
        </div>
        <div className="flex items-center gap-3">
          {settingsButton}
          {apiIndicator}
        </div>
      </div>
      {children}
    </header>
  )
}

