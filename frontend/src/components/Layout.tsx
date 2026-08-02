import type { ReactNode } from 'react'
import { useAuth } from '../authStore'

export type NavItem = {
  id: string
  label: string
  icon: string
}

export const NAV_ITEMS: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: '📊' },
  { id: 'bayesian', label: 'Bayesian Analysis', icon: '🧠' },
  { id: 'assets', label: 'Assets', icon: '📋' },
  { id: 'threats', label: 'Threats & Vulnerabilities', icon: '🦠' },
  { id: 'controls', label: 'Controls', icon: '🛡️' },
  { id: 'risk', label: 'Risk Management', icon: '📈' },
  { id: 'compliance', label: 'Compliance', icon: '📚' },
  { id: 'audit', label: 'Audit', icon: '🔍' },
  { id: 'capa', label: 'Corrective Actions', icon: '✅' },
  { id: 'admin', label: 'Administration', icon: '⚙️' },
]

function UserFooter() {
  const { user, logout, hasPermission } = useAuth()

  return (
    <div className="space-y-2">
      {user && (
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-cyan-500/20 text-cyan-300 text-xs font-bold">
            {user.first_name?.[0] || user.username[0]?.toUpperCase() || '?'}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate font-medium text-slate-300">
              {user.first_name
                ? `${user.first_name} ${user.last_name ?? ''}`
                : user.username}
            </p>
            <p className="truncate text-slate-500">
              {user.role_name ?? 'No role'}
              {hasPermission('*') ? ' (admin)' : ''}
            </p>
          </div>
        </div>
      )}
      <button
        onClick={() => void logout()}
        className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
      >
        <span>🚪</span>
        Sign out
      </button>
    </div>
  )
}

export default function Layout({
  active,
  onNavigate,
  children,
}: {
  active: string
  onNavigate: (id: string) => void
  children: ReactNode
}) {
  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      {/* Sidebar */}
      <aside className="flex w-64 shrink-0 flex-col border-r border-slate-800 bg-slate-900/80">
        <div className="border-b border-slate-800 p-5">
          <p className="text-xs uppercase tracking-[0.24em] text-cyan-300">
            GRC & Audit Platform
          </p>
          <h1 className="mt-1 text-lg font-semibold leading-tight">
            ICS Governance, Risk & Compliance
          </h1>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {NAV_ITEMS.map((item) => {
            const isActive = active === item.id
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-cyan-500/15 text-cyan-200 ring-1 ring-cyan-500/30'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-slate-100'
                }`}
                aria-current={isActive ? 'page' : undefined}
              >
                <span className="text-base" aria-hidden>
                  {item.icon}
                </span>
                {item.label}
              </button>
            )
          })}
        </nav>
        <div className="border-t border-slate-800 p-4">
          <UserFooter />
        </div>
      </aside>

      {/* Main content */}
      <main className="min-w-0 flex-1 p-6">
        <div className="mx-auto max-w-7xl">{children}</div>
      </main>
    </div>
  )
}
