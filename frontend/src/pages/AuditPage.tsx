import { useCallback, useEffect, useState } from 'react'
import GrcTable from '../components/grc/GrcTable'
import type { Column } from '../components/grc/GrcTable'
import PageHeader from '../components/grc/PageHeader'
import { auditApi } from '../services/grc'
import type {
  AuditEvidence,
  AuditFinding,
  AuditInterview,
  AuditPlan,
  AuditProcedure,
  AuditProgram,
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

function statusTone(value: string): 'green' | 'amber' | 'rose' | 'slate' | 'cyan' {
  if (value === 'critical' || value === 'high') return 'rose'
  if (value === 'medium') return 'amber'
  if (value === 'low') return 'green'
  if (value === 'open' || value === 'in_progress') return 'amber'
  if (value === 'closed' || value === 'verified') return 'green'
  if (value === 'planned' || value === 'scheduled') return 'cyan'
  return 'slate'
}

export default function AuditPage() {
  const [programs, setPrograms] = useState<AuditProgram[]>([])
  const [plans, setPlans] = useState<AuditPlan[]>([])
  const [procedures, setProcedures] = useState<AuditProcedure[]>([])
  const [findings, setFindings] = useState<AuditFinding[]>([])
  const [evidence, setEvidence] = useState<AuditEvidence[]>([])
  const [interviews, setInterviews] = useState<AuditInterview[]>([])
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [programList, planList, findingList, evidenceList, interviewList] =
        await Promise.all([
          auditApi.programs().catch(() => [] as AuditProgram[]),
          auditApi.plans().catch(() => [] as AuditPlan[]),
          auditApi.findings().catch(() => [] as AuditFinding[]),
          auditApi.evidence().catch(() => [] as AuditEvidence[]),
          auditApi.interviews().catch(() => [] as AuditInterview[]),
        ])
      setPrograms(programList)
      setPlans(planList)
      setFindings(findingList)
      setEvidence(evidenceList)
      setInterviews(interviewList)

      if (planList.length > 0) {
        const id = planList[0].id
        setSelectedPlanId(id)
        const procList = await auditApi.procedures(id).catch(() => [] as AuditProcedure[])
        setProcedures(procList)
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load audit data.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const loadPlanDetail = async (id: number) => {
    setSelectedPlanId(id)
    const procList = await auditApi.procedures(id).catch(() => [] as AuditProcedure[])
    setProcedures(procList)
  }

  const planColumns: Column<AuditPlan>[] = [
    {
      key: 'title',
      header: 'Audit Plan',
      render: (p) => (
        <button
          onClick={() => void loadPlanDetail(p.id)}
          className="text-left font-medium text-cyan-200 hover:underline"
        >
          {p.title}
        </button>
      ),
    },
    { key: 'audit_type', header: 'Type', render: (p) => p.audit_type ?? '—' },
    { key: 'criteria', header: 'Criteria', render: (p) => p.criteria ?? '—' },
    {
      key: 'status',
      header: 'Status',
      render: (p) => (p.status ? <Badge value={p.status} tone={statusTone(p.status)} /> : '—'),
    },
    { key: 'start_date', header: 'Start', render: (p) => p.start_date ?? '—' },
    { key: 'end_date', header: 'End', render: (p) => p.end_date ?? '—' },
  ]

  const findingColumns: Column<AuditFinding>[] = [
    { key: 'finding_id', header: 'Finding ID', render: (f) => (f.finding_id ? <Badge value={f.finding_id} tone="cyan" /> : '—') },
    { key: 'title', header: 'Finding', render: (f) => <span className="font-medium">{f.title}</span> },
    {
      key: 'severity',
      header: 'Severity',
      render: (f) => (f.severity ? <Badge value={f.severity} tone={statusTone(f.severity)} /> : '—'),
    },
    { key: 'finding_type', header: 'Type', render: (f) => f.finding_type ?? '—' },
    {
      key: 'status',
      header: 'Status',
      render: (f) => (f.status ? <Badge value={f.status} tone={statusTone(f.status)} /> : '—'),
    },
    { key: 'criteria_reference', header: 'Criteria', render: (f) => f.criteria_reference ?? '—' },
  ]

  const programColumns: Column<AuditProgram>[] = [
    { key: 'name', header: 'Program', render: (p) => <span className="font-medium">{p.name}</span> },
    { key: 'program_type', header: 'Type', render: (p) => p.program_type ?? '—' },
    {
      key: 'status',
      header: 'Status',
      render: (p) => (p.status ? <Badge value={p.status} tone={statusTone(p.status)} /> : '—'),
    },
    { key: 'start_date', header: 'Start', render: (p) => p.start_date ?? '—' },
    { key: 'end_date', header: 'End', render: (p) => p.end_date ?? '—' },
  ]

  return (
    <div>
      <PageHeader
        title="Audit Management"
        description="Audit programs, plans, procedures, findings, evidence, and interview records."
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
          Loading audit data…
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-rose-200">
          {error}
        </div>
      ) : (
        <div className="space-y-8">
          <section>
            <h3 className="mb-3 text-lg font-semibold">
              Audit Programs <span className="text-sm font-normal text-slate-400">({programs.length})</span>
            </h3>
            <GrcTable
              columns={programColumns}
              rows={programs}
              rowKey={(p) => p.id}
              emptyMessage="No audit programs yet."
            />
          </section>

          <section>
            <h3 className="mb-3 text-lg font-semibold">
              Audit Plans <span className="text-sm font-normal text-slate-400">({plans.length})</span>
            </h3>
            <GrcTable
              columns={planColumns}
              rows={plans}
              rowKey={(p) => p.id}
              emptyMessage="No audit plans yet."
            />
          </section>

          {selectedPlanId && procedures.length > 0 ? (
            <section>
              <h3 className="mb-3 text-lg font-semibold">
                Procedures (Plan {selectedPlanId}){' '}
                <span className="text-sm font-normal text-slate-400">({procedures.length})</span>
              </h3>
              <GrcTable
                columns={[
                  { key: 'title', header: 'Procedure', render: (p) => <span className="font-medium">{p.title}</span> },
                  { key: 'testing_method', header: 'Method', render: (p) => p.testing_method ?? '—' },
                  { key: 'sample_size', header: 'Sample', render: (p) => p.sample_size ?? '—' },
                  { key: 'expected_evidence', header: 'Expected Evidence', render: (p) => p.expected_evidence ?? '—' },
                ]}
                rows={procedures}
                rowKey={(p) => p.id}
                emptyMessage="No procedures for this plan."
              />
            </section>
          ) : null}

          <section>
            <h3 className="mb-3 text-lg font-semibold">
              Audit Findings <span className="text-sm font-normal text-slate-400">({findings.length})</span>
            </h3>
            <GrcTable
              columns={findingColumns}
              rows={findings}
              rowKey={(f) => f.id}
              emptyMessage="No audit findings yet."
            />
          </section>

          <div className="grid gap-6 xl:grid-cols-2">
            <section>
              <h3 className="mb-3 text-lg font-semibold">
                Evidence <span className="text-sm font-normal text-slate-400">({evidence.length})</span>
              </h3>
              <GrcTable
                columns={[
                  { key: 'evidence_title', header: 'Title', render: (e) => <span className="font-medium">{e.evidence_title}</span> },
                  { key: 'evidence_type', header: 'Type', render: (e) => e.evidence_type ?? '—' },
                  { key: 'filename', header: 'File', render: (e) => e.filename ?? '—' },
                ]}
                rows={evidence}
                rowKey={(e) => e.id}
                emptyMessage="No evidence collected yet."
              />
            </section>

            <section>
              <h3 className="mb-3 text-lg font-semibold">
                Interviews <span className="text-sm font-normal text-slate-400">({interviews.length})</span>
              </h3>
              <GrcTable
                columns={[
                  { key: 'interviewee_name', header: 'Interviewee', render: (i) => <span className="font-medium">{i.interviewee_name}</span> },
                  { key: 'interviewee_title', header: 'Title', render: (i) => i.interviewee_title ?? '—' },
                  { key: 'interview_date', header: 'Date', render: (i) => i.interview_date ?? '—' },
                ]}
                rows={interviews}
                rowKey={(i) => i.id}
                emptyMessage="No interviews recorded."
              />
            </section>
          </div>
        </div>
      )}
    </div>
  )
}

