import { useCallback, useEffect, useState } from 'react'
import GrcTable from '../components/grc/GrcTable'
import type { Column } from '../components/grc/GrcTable'
import PageHeader from '../components/grc/PageHeader'
import { Modal } from '../components/grc/Modal'
import { GrcForm, GrcFormActions, GrcFormSection } from '../components/grc/GrcForm'
import type { FormFieldConfig } from '../components/grc/GrcForm'
import { useCrud } from '../hooks/useCrud'
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

const PROGRAM_FIELDS: FormFieldConfig[] = [
  { name: 'name', label: 'Program Name', type: 'text', required: true },
  { name: 'program_type', label: 'Program Type', type: 'select', options: [
    { value: 'annual', label: 'Annual' },
    { value: 'quarterly', label: 'Quarterly' },
    { value: 'continuous', label: 'Continuous' },
    { value: 'ad_hoc', label: 'Ad-hoc' },
  ]},
  { name: 'status', label: 'Status', type: 'select', options: [
    { value: 'draft', label: 'Draft' },
    { value: 'active', label: 'Active' },
    { value: 'completed', label: 'Completed' },
    { value: 'archived', label: 'Archived' },
  ]},
  { name: 'start_date', label: 'Start Date', type: 'date' },
  { name: 'end_date', label: 'End Date', type: 'date' },
  { name: 'program_manager_id', label: 'Program Manager ID', type: 'number' },
  { name: 'description', label: 'Description', type: 'textarea' },
]

const PLAN_FIELDS: FormFieldConfig[] = [
  { name: 'title', label: 'Plan Title', type: 'text', required: true },
  { name: 'audit_type', label: 'Audit Type', type: 'select', options: [
    { value: 'internal', label: 'Internal' },
    { value: 'external', label: 'External' },
    { value: 'compliance', label: 'Compliance' },
    { value: 'ics_security', label: 'ICS Security' },
    { value: 'regulatory', label: 'Regulatory' },
  ]},
  { name: 'status', label: 'Status', type: 'select', options: [
    { value: 'draft', label: 'Draft' },
    { value: 'planned', label: 'Planned' },
    { value: 'scheduled', label: 'Scheduled' },
    { value: 'in_progress', label: 'In Progress' },
    { value: 'completed', label: 'Completed' },
    { value: 'cancelled', label: 'Cancelled' },
  ]},
  { name: 'start_date', label: 'Start Date', type: 'date' },
  { name: 'end_date', label: 'End Date', type: 'date' },
  { name: 'estimated_hours', label: 'Est. Hours', type: 'number', min: 0, step: 0.5 },
  { name: 'lead_auditor_id', label: 'Lead Auditor ID', type: 'number' },
  { name: 'audit_program_id', label: 'Audit Program ID', type: 'number' },
  { name: 'description', label: 'Description', type: 'textarea' },
  { name: 'scope', label: 'Scope', type: 'textarea' },
  { name: 'objectives', label: 'Objectives', type: 'textarea' },
  { name: 'criteria', label: 'Criteria', type: 'textarea' },
]

const FINDING_FIELDS: FormFieldConfig[] = [
  { name: 'audit_plan_id', label: 'Audit Plan ID', type: 'number', required: true },
  { name: 'title', label: 'Finding Title', type: 'text', required: true },
  { name: 'finding_id', label: 'Finding ID', type: 'text', placeholder: 'e.g., AUDIT-F-2024-0001' },
  { name: 'finding_type', label: 'Finding Type', type: 'select', options: [
    { value: 'non_conformity', label: 'Non-Conformity' },
    { value: 'observation', label: 'Observation' },
    { value: 'opportunity_for_improvement', label: 'Opportunity for Improvement' },
  ]},
  { name: 'severity', label: 'Severity', type: 'select', options: [
    { value: 'critical', label: 'Critical' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' },
    { value: 'informational', label: 'Informational' },
  ]},
  { name: 'status', label: 'Status', type: 'select', options: [
    { value: 'open', label: 'Open' },
    { value: 'acknowledged', label: 'Acknowledged' },
    { value: 'action_planned', label: 'Action Planned' },
    { value: 'verified', label: 'Verified' },
    { value: 'closed', label: 'Closed' },
  ]},
  { name: 'description', label: 'Description', type: 'textarea', required: true },
  { name: 'recommendation', label: 'Recommendation', type: 'textarea' },
  { name: 'root_cause', label: 'Root Cause', type: 'textarea' },
  { name: 'impact', label: 'Impact', type: 'textarea' },
  { name: 'criteria_reference', label: 'Criteria Reference', type: 'text' },
]

const EVIDENCE_FIELDS: FormFieldConfig[] = [
  { name: 'audit_plan_id', label: 'Audit Plan ID', type: 'number', required: true },
  { name: 'evidence_title', label: 'Evidence Title', type: 'text', required: true },
  { name: 'evidence_type', label: 'Evidence Type', type: 'select', options: [
    { value: 'document', label: 'Document' },
    { value: 'screenshot', label: 'Screenshot' },
    { value: 'log', label: 'Log' },
    { value: 'interview_notes', label: 'Interview Notes' },
    { value: 'config', label: 'Configuration' },
  ]},
  { name: 'filename', label: 'Filename', type: 'text' },
  { name: 'file_path', label: 'File Path', type: 'text' },
  { name: 'collected_by_id', label: 'Collected By ID', type: 'number' },
  { name: 'is_confidential', label: 'Confidential', type: 'checkbox' },
  { name: 'description', label: 'Description', type: 'textarea' },
]

const INTERVIEW_FIELDS: FormFieldConfig[] = [
  { name: 'audit_plan_id', label: 'Audit Plan ID', type: 'number', required: true },
  { name: 'interviewee_name', label: 'Interviewee Name', type: 'text', required: true },
  { name: 'interviewee_title', label: 'Interviewee Title', type: 'text' },
  { name: 'interviewee_department', label: 'Department', type: 'text' },
  { name: 'interviewer_id', label: 'Interviewer ID', type: 'number' },
  { name: 'interview_date', label: 'Interview Date', type: 'date' },
  { name: 'duration_minutes', label: 'Duration (min)', type: 'number', min: 0 },
  { name: 'topics_covered', label: 'Topics Covered', type: 'textarea' },
  { name: 'key_findings', label: 'Key Findings', type: 'textarea' },
  { name: 'notes', label: 'Notes', type: 'textarea' },
]

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
  const [formValues, setFormValues] = useState<Record<string, unknown>>({})
  const [formMode, setFormMode] = useState<'program' | 'plan' | 'finding' | 'evidence' | 'interview'>('program')
  const crud = useCrud<AuditProgram | AuditPlan | AuditFinding | AuditEvidence | AuditInterview>()

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

  const handleCreateProgram = () => {
    setFormValues({ status: 'draft' })
    setFormMode('program')
    crud.openCreate()
  }

  const handleCreatePlan = () => {
    setFormValues({ status: 'draft' })
    setFormMode('plan')
    crud.openCreate()
  }

  const handleCreateFinding = () => {
    setFormValues({ status: 'open', severity: 'medium', audit_plan_id: selectedPlanId })
    setFormMode('finding')
    crud.openCreate()
  }

  const handleCreateEvidence = () => {
    setFormValues({ is_confidential: false, audit_plan_id: selectedPlanId })
    setFormMode('evidence')
    crud.openCreate()
  }

  const handleCreateInterview = () => {
    setFormValues({ audit_plan_id: selectedPlanId })
    setFormMode('interview')
    crud.openCreate()
  }

  const handleEditProgram = (item: AuditProgram) => {
    setFormMode('program')
    setFormValues({ ...(item as unknown as Record<string, unknown>) })
    crud.openEdit(item)
  }

  const handleEditPlan = (item: AuditPlan) => {
    setFormMode('plan')
    setFormValues({ ...(item as unknown as Record<string, unknown>) })
    crud.openEdit(item)
  }

  const handleEditFinding = (item: AuditFinding) => {
    setFormMode('finding')
    setFormValues({ ...(item as unknown as Record<string, unknown>) })
    crud.openEdit(item)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    crud.setSubmitting(true)
    crud.setError('')
    try {
      if (formMode === 'program') {
        if (crud.mode === 'create') {
          await auditApi.createProgram(formValues as Partial<AuditProgram>)
        } else if (crud.selected) {
          await auditApi.updateProgram(crud.selected.id, formValues as Partial<AuditProgram>)
        }
      } else if (formMode === 'plan') {
        if (crud.mode === 'create') {
          await auditApi.createPlan(formValues as Partial<AuditPlan>)
        } else if (crud.selected) {
          await auditApi.updatePlan(crud.selected.id, formValues as Partial<AuditPlan>)
        }
      } else if (formMode === 'finding') {
        if (crud.mode === 'create') {
          await auditApi.createFinding(formValues as Partial<AuditFinding>)
        } else if (crud.selected) {
          await auditApi.updateFinding(crud.selected.id, formValues as Partial<AuditFinding>)
        }
      } else if (formMode === 'evidence') {
        if (crud.mode === 'create') {
          await auditApi.createEvidence(formValues as Partial<AuditEvidence>)
        }
      } else {
        if (crud.mode === 'create') {
          await auditApi.createInterview(formValues as Partial<AuditInterview>)
        }
      }
      crud.close()
      await load()
    } catch (caught) {
      crud.setError(caught instanceof Error ? caught.message : 'Failed to save.')
    } finally {
      crud.setSubmitting(false)
    }
  }

  const handleDelete = async () => {
    if (!crud.selected) return
    crud.setSubmitting(true)
    try {
      if (formMode === 'program') {
        await auditApi.removeProgram(crud.selected.id)
      } else if (formMode === 'plan') {
        await auditApi.removePlan(crud.selected.id)
      } else if (formMode === 'finding') {
        await auditApi.removeFinding(crud.selected.id)
      } else if (formMode === 'evidence') {
        await auditApi.removeEvidence(crud.selected.id)
      } else {
        await auditApi.removeInterview(crud.selected.id)
      }
      crud.close()
      await load()
    } catch (caught) {
      crud.setError(caught instanceof Error ? caught.message : 'Failed to delete.')
    } finally {
      crud.setSubmitting(false)
    }
  }

  const planColumns: Column<AuditPlan>[] = [
    {
      key: 'title',
      header: 'Audit Plan',
      render: (p) => (
        <div className="flex items-center gap-2">
          <button
            onClick={() => void loadPlanDetail(p.id)}
            className="text-left font-medium text-cyan-200 hover:underline"
          >
            {p.title}
          </button>
          <button
            onClick={() => handleEditPlan(p)}
            className="text-xs text-cyan-400 hover:text-cyan-200 hover:underline"
          >
            Edit
          </button>
        </div>
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
    {
      key: 'finding_id',
      header: 'Finding ID',
      render: (f) => (
        <div className="flex items-center gap-2">
          {f.finding_id ? <Badge value={f.finding_id} tone="cyan" /> : '—'}
          <button
            onClick={() => handleEditFinding(f)}
            className="text-xs text-cyan-400 hover:text-cyan-200 hover:underline"
          >
            Edit
          </button>
        </div>
      ),
    },
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
    {
      key: 'name',
      header: 'Program',
      render: (p) => (
        <div className="flex items-center gap-2">
          <span className="font-medium">{p.name}</span>
          <button
            onClick={() => handleEditProgram(p)}
            className="text-xs text-cyan-400 hover:text-cyan-200 hover:underline"
          >
            Edit
          </button>
        </div>
      ),
    },
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
          <div className="flex items-center gap-2">
            <button
              onClick={handleCreateProgram}
              className="rounded-full bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500"
            >
              + Program
            </button>
            <button
              onClick={handleCreatePlan}
              className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-500/50 hover:text-cyan-200"
            >
              + Plan
            </button>
            {selectedPlanId && (
              <>
                <button
                  onClick={handleCreateFinding}
                  className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-500/50 hover:text-cyan-200"
                >
                  + Finding
                </button>
                <button
                  onClick={handleCreateEvidence}
                  className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-500/50 hover:text-cyan-200"
                >
                  + Evidence
                </button>
                <button
                  onClick={handleCreateInterview}
                  className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-500/50 hover:text-cyan-200"
                >
                  + Interview
                </button>
              </>
            )}
            <button
              onClick={() => void load()}
              className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-500/50 hover:text-cyan-200"
            >
              Refresh
            </button>
          </div>
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

      {/* Create/Edit Modal */}
      <Modal
        open={crud.open}
        onClose={crud.close}
        title={
          formMode === 'program'
            ? `${crud.mode === 'create' ? 'Create' : 'Edit'} Audit Program`
            : formMode === 'plan'
              ? `${crud.mode === 'create' ? 'Create' : 'Edit'} Audit Plan`
              : formMode === 'finding'
                ? `${crud.mode === 'create' ? 'Create' : 'Edit'} Audit Finding`
                : formMode === 'evidence'
                  ? 'Create Evidence'
                  : 'Create Interview'
        }
      >
        <form onSubmit={handleSubmit}>
          <GrcFormSection
            title={
              formMode === 'program'
                ? 'Program Details'
                : formMode === 'plan'
                  ? 'Plan Details'
                  : formMode === 'finding'
                    ? 'Finding Details'
                    : formMode === 'evidence'
                      ? 'Evidence Details'
                      : 'Interview Details'
            }
          >
            <GrcForm
              fields={
                formMode === 'program'
                  ? PROGRAM_FIELDS
                  : formMode === 'plan'
                    ? PLAN_FIELDS
                    : formMode === 'finding'
                      ? FINDING_FIELDS
                      : formMode === 'evidence'
                        ? EVIDENCE_FIELDS
                        : INTERVIEW_FIELDS
              }
              values={formValues}
              onChange={(name, value) => setFormValues((prev) => ({ ...prev, [name]: value }))}
            />
          </GrcFormSection>

          {crud.error ? (
            <div className="mb-4 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">
              {crud.error}
            </div>
          ) : null}

          <GrcFormActions
            onCancel={crud.close}
            submitting={crud.submitting}
            submitLabel={crud.mode === 'create' ? 'Create' : 'Save Changes'}
            onDelete={crud.mode === 'edit' ? handleDelete : undefined}
            deleteLabel="Delete"
          />
        </form>
      </Modal>
    </div>
  )
}

