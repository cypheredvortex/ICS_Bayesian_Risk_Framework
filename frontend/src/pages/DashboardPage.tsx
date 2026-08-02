import { useEffect, useState } from 'react'
import PageHeader from '../components/grc/PageHeader'
import { fetchDashboardSummary } from '../services/grc'
import type { DashboardSummary } from '../types/grc'

const EMPTY_SUMMARY: DashboardSummary = {
  organizations: 0,
  sites: 0,
  plants: 0,
  assets: 0,
  threats: 0,
  vulnerabilities: 0,
  controls: 0,
  risk_items: 0,
  open_risks: 0,
  frameworks: 0,
  audit_plans: 0,
  open_findings: 0,
  corrective_actions: 0,
  open_actions: 0,
}

function StatCard({
  label,
  value,
  tone = 'cyan',
}: {
  label: string
  value: number
  tone?: 'cyan' | 'emerald' | 'amber' | 'rose'
}) {
  const tones: Record<string, string> = {
    cyan: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-200',
    emerald: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200',
    amber: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
    rose: 'border-rose-500/30 bg-rose-500/10 text-rose-200',
  }
  return (
    <div className={`rounded-2xl border p-5 ${tones[tone]}`}>
      <p className="text-xs uppercase tracking-wider opacity-80">{label}</p>
      <p className="mt-2 text-3xl font-semibold">{value}</p>
    </div>
  )
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary>(EMPTY_SUMMARY)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let mounted = true
    const load = async () => {
      try {
        const data = await fetchDashboardSummary()
        if (mounted) setSummary(data)
      } catch (caught) {
        if (mounted) {
          setError(
            caught instanceof Error
              ? caught.message
              : 'Could not load dashboard summary.',
          )
        }
      } finally {
        if (mounted) setLoading(false)
      }
    }
    void load()
    return () => {
      mounted = false
    }
  }, [])

  return (
    <div>
      <PageHeader
        title="GRC Dashboard"
        description="High-level overview of your governance, risk, compliance, and audit posture."
      />

      {loading ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-8 text-center text-slate-400">
          Loading dashboard…
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-rose-200">
          {error}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Organizations" value={summary.organizations} />
          <StatCard label="Assets" value={summary.assets} tone="emerald" />
          <StatCard label="Threats" value={summary.threats} />
          <StatCard label="Vulnerabilities" value={summary.vulnerabilities} />
          <StatCard label="Controls" value={summary.controls} />
          <StatCard
            label="Risk Items"
            value={summary.risk_items}
            tone={summary.open_risks > 0 ? 'amber' : 'cyan'}
          />
          <StatCard label="Compliance Frameworks" value={summary.frameworks} />
          <StatCard
            label="Open Findings"
            value={summary.open_findings}
            tone={summary.open_findings > 0 ? 'rose' : 'emerald'}
          />
          <StatCard label="Audit Plans" value={summary.audit_plans} />
          <StatCard
            label="Corrective Actions"
            value={summary.corrective_actions}
            tone={summary.open_actions > 0 ? 'amber' : 'cyan'}
          />
        </div>
      )}
    </div>
  )
}

