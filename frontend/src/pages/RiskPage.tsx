import { useCallback, useEffect, useState } from 'react'
import GrcTable from '../components/grc/GrcTable'
import type { Column } from '../components/grc/GrcTable'
import PageHeader from '../components/grc/PageHeader'
import { riskApi } from '../services/grc'
import type {
  RiskAcceptance,
  RiskHistory,
  RiskItem,
  RiskScenario,
  RiskTreatmentPlan,
} from '../types/grc'

function Badge({
  value,
  tone = 'slate',
}: {
  value: string
  tone?: 'green' | 'amber' | 'rose' | 'slate' | 'cyan'
}) {
  const tones: Record<string, string> = {
    green: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
    amber: 'bg-amber-500/15 text-amber-300 ring-amber-500/30',
    rose: 'bg-rose-500/15 text-rose-300 ring-rose-500/30',
    slate: 'bg-slate-500/15 text-slate-300 ring-slate-500/30',
    cyan: 'bg-cyan-500/15 text-cyan-300 ring-cyan-500/30',
  }
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${tones[tone]}`}
    >
      {value}
    </span>
  )
}

function riskTone(value?: string | null): 'green' | 'amber' | 'rose' | 'slate' | 'cyan' {
  if (!value) return 'slate'
  if (value === 'critical') return 'rose'
  if (value === 'high') return 'rose'
  if (value === 'moderate' || value === 'medium') return 'amber'
  if (value === 'low') return 'green'
  return 'slate'
}

export default function RiskPage() {
  const [items, setItems] = useState<RiskItem[]>([])
  const [scenarios, setScenarios] = useState<RiskScenario[]>([])
  const [plans, setPlans] = useState<RiskTreatmentPlan[]>([])
  const [acceptances, setAcceptances] = useState<RiskAcceptance[]>([])
  const [history, setHistory] = useState<RiskHistory[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const list = await riskApi.list().catch(() => [] as RiskItem[])
      setItems(list)
      if (list.length > 0) {
        const id = list[0].id
        setSelectedId(id)
        const [scenariosList, plansList, acceptancesList, historyList] =
          await Promise.all([
            riskApi.scenarios(id).catch(() => [] as RiskScenario[]),
            riskApi.treatmentPlans(id).catch(() => [] as RiskTreatmentPlan[]),
            riskApi.acceptances(id).catch(() => [] as RiskAcceptance[]),
            riskApi.history(id).catch(() => [] as RiskHistory[]),
          ])
        setScenarios(scenariosList)
        setPlans(plansList)
        setAcceptances(acceptancesList)
        setHistory(historyList)
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load risk register.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const loadDetail = async (id: number) => {
    setSelectedId(id)
    const [scenariosList, plansList, acceptancesList, historyList] =
      await Promise.all([
        riskApi.scenarios(id).catch(() => [] as RiskScenario[]),
        riskApi.treatmentPlans(id).catch(() => [] as RiskTreatmentPlan[]),
        riskApi.acceptances(id).catch(() => [] as RiskAcceptance[]),
        riskApi.history(id).catch(() => [] as RiskHistory[]),
      ])
    setScenarios(scenariosList)
    setPlans(plansList)
    setAcceptances(acceptancesList)
    setHistory(historyList)
  }

  const columns: Column<RiskItem>[] = [
    {
      key: 'title',
      header: 'Risk',
      render: (r) => (
        <button
          onClick={() => void loadDetail(r.id)}
          className="text-left font-medium text-cyan-200 hover:underline"
        >
          {r.title}
        </button>
      ),
    },
    {
      key: 'risk_id',
      header: 'Risk ID',
      render: (r) => (r.risk_id ? <Badge value={r.risk_id} tone="cyan" /> : '—'),
    },
    {
      key: 'inherent_risk_level',
      header: 'Inherent',
      render: (r) =>
        r.inherent_risk_level ? (
          <Badge value={r.inherent_risk_level} tone={riskTone(r.inherent_risk_level)} />
        ) : (
          '—'
        ),
    },
    {
      key: 'residual_risk_level',
      header: 'Residual',
      render: (r) =>
        r.residual_risk_level ? (
          <Badge value={r.residual_risk_level} tone={riskTone(r.residual_risk_level)} />
        ) : (
          '—'
        ),
    },
    {
      key: 'bayesian_risk_level',
      header: 'Bayesian',
      render: (r) =>
        r.bayesian_risk_level ? (
          <Badge value={r.bayesian_risk_level} tone={riskTone(r.bayesian_risk_level)} />
        ) : (
          '—'
        ),
    },
    {
      key: 'treatment_strategy',
      header: 'Treatment',
      render: (r) =>
        r.treatment_strategy ? (
          <Badge value={r.treatment_strategy} tone={riskTone(r.treatment_strategy)} />
        ) : (
          '—'
        ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (r) =>
        r.status ? <Badge value={r.status} tone={riskTone(r.status)} /> : '—',
    },
    {
      key: 'is_accepted',
      header: 'Accepted',
      render: (r) =>
        r.is_accepted ? (
          <Badge value="Accepted" tone="green" />
        ) : (
          <Badge value="Pending" tone="slate" />
        ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Risk Register"
        description="Risk items with inherent/residual/Bayesian risk levels, treatment plans, acceptances, and history."
        action={
          <button
            onClick={() => void load()}
            className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-500/50 hover:text-cyan-200"
          >
            Refresh
          </button>
        }
      />

      {loading ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-8 text-center text-slate-400">
          Loading risk register…
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-rose-200">
          {error}
        </div>
      ) : (
        <div className="space-y-8">
          <GrcTable
            columns={columns}
            rows={items}
            rowKey={(r) => r.id}
            emptyMessage="No risk items registered."
          />

          {selectedId && (
            <div className="grid gap-6 xl:grid-cols-2">
              <section>
                <h3 className="mb-3 text-lg font-semibold">Risk Scenarios</h3>
                <GrcTable
                  columns={[
                    { key: 'name', header: 'Scenario', render: (s) => <span className="font-medium">{s.name}</span> },
                    { key: 'description', header: 'Description', render: (s) => s.description ?? '—' },
                  ]}
                  rows={scenarios}
                  rowKey={(s) => s.id}
                  emptyMessage="No scenarios for this risk."
                />
              </section>

              <section>
                <h3 className="mb-3 text-lg font-semibold">Treatment Plans</h3>
                <GrcTable
                  columns={[
                    { key: 'title', header: 'Plan', render: (p) => <span className="font-medium">{p.title}</span> },
                    {
                      key: 'treatment_option',
                      header: 'Option',
                      render: (p) => (p.treatment_option ? <Badge value={p.treatment_option} /> : '—'),
                    },
                    { key: 'target_date', header: 'Target Date', render: (p) => p.target_date ?? '—' },
                    { key: 'status', header: 'Status', render: (p) => (p.status ? <Badge value={p.status} /> : '—') },
                  ]}
                  rows={plans}
                  rowKey={(p) => p.id}
                  emptyMessage="No treatment plans for this risk."
                />
              </section>

              <section>
                <h3 className="mb-3 text-lg font-semibold">Risk Acceptances</h3>
                <GrcTable
                  columns={[
                    {
                      key: 'acceptance_type',
                      header: 'Type',
                      render: (a) => (a.acceptance_type ? <Badge value={a.acceptance_type} /> : '—'),
                    },
                    { key: 'justification', header: 'Justification', render: (a) => a.justification },
                    { key: 'expiration_date', header: 'Expires', render: (a) => a.expiration_date ?? '—' },
                    { key: 'status', header: 'Status', render: (a) => (a.status ? <Badge value={a.status} /> : '—') },
                  ]}
                  rows={acceptances}
                  rowKey={(a) => a.id}
                  emptyMessage="No acceptances recorded."
                />
              </section>

              <section>
                <h3 className="mb-3 text-lg font-semibold">Risk History</h3>
                <GrcTable
                  columns={[
                    { key: 'change_type', header: 'Change', render: (h) => (h.change_type ? <Badge value={h.change_type} tone="cyan" /> : '—') },
                    { key: 'change_reason', header: 'Reason', render: (h) => h.change_reason ?? '—' },
                    { key: 'created_at', header: 'Date', render: (h) => h.created_at ?? '—' },
                  ]}
                  rows={history}
                  rowKey={(h) => h.id}
                  emptyMessage="No history recorded yet."
                />
              </section>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

