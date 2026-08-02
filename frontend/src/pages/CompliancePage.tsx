import { useCallback, useEffect, useState } from 'react'
import GrcTable from '../components/grc/GrcTable'
import type { Column } from '../components/grc/GrcTable'
import PageHeader from '../components/grc/PageHeader'
import { Modal } from '../components/grc/Modal'
import { GrcForm, GrcFormActions, GrcFormSection } from '../components/grc/GrcForm'
import type { FormFieldConfig } from '../components/grc/GrcForm'
import { useCrud } from '../hooks/useCrud'
import { complianceApi } from '../services/grc'
import type {
  ComplianceAssessment,
  ComplianceFramework,
  ComplianceGap,
  ControlMapping,
  FrameworkRequirement,
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
  if (value === 'compliant') return 'green'
  if (value === 'partially_compliant') return 'amber'
  if (value === 'non_compliant') return 'rose'
  if (value === 'not_assessed') return 'slate'
  return 'slate'
}

const FRAMEWORK_FIELDS: FormFieldConfig[] = [
  { name: 'name', label: 'Framework Name', type: 'text', required: true, placeholder: 'e.g., ISO 27001, NIST CSF, IEC 62443' },
  { name: 'version', label: 'Version', type: 'text', required: true },
  { name: 'publisher', label: 'Publisher', type: 'text' },
  { name: 'domain', label: 'Domain', type: 'select', options: [
    { value: 'information_security', label: 'Information Security' },
    { value: 'ics_security', label: 'ICS Security' },
    { value: 'privacy', label: 'Privacy' },
  ]},
  { name: 'description', label: 'Description', type: 'textarea' },
]

const GAP_FIELDS: FormFieldConfig[] = [
  { name: 'requirement_id', label: 'Requirement ID', type: 'number', required: true },
  { name: 'gap_description', label: 'Gap Description', type: 'textarea', required: true },
  { name: 'severity', label: 'Severity', type: 'select', options: [
    { value: 'critical', label: 'Critical' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' },
  ]},
  { name: 'status', label: 'Status', type: 'select', options: [
    { value: 'open', label: 'Open' },
    { value: 'planned', label: 'Planned' },
    { value: 'remediated', label: 'Remediated' },
    { value: 'accepted', label: 'Accepted' },
  ]},
  { name: 'target_closure_date', label: 'Target Closure Date', type: 'date' },
  { name: 'remediation_plan', label: 'Remediation Plan', type: 'textarea' },
]

const ASSESSMENT_FIELDS: FormFieldConfig[] = [
  { name: 'framework_id', label: 'Framework ID', type: 'number', required: true },
  { name: 'organization_id', label: 'Organization ID', type: 'number' },
  { name: 'plant_id', label: 'Plant ID', type: 'number' },
  { name: 'assessment_date', label: 'Assessment Date', type: 'date' },
  { name: 'assessor_id', label: 'Assessor ID', type: 'number' },
  { name: 'overall_status', label: 'Status', type: 'select', options: [
    { value: 'compliant', label: 'Compliant' },
    { value: 'partially_compliant', label: 'Partially Compliant' },
    { value: 'non_compliant', label: 'Non-Compliant' },
    { value: 'not_assessed', label: 'Not Assessed' },
  ]},
  { name: 'compliance_percentage', label: 'Compliance %', type: 'number', min: 0, max: 100, step: 0.1 },
  { name: 'findings_summary', label: 'Findings Summary', type: 'textarea' },
]

export default function CompliancePage() {
  const [frameworks, setFrameworks] = useState<ComplianceFramework[]>([])
  const [requirements, setRequirements] = useState<FrameworkRequirement[]>([])
  const [mappings, setMappings] = useState<ControlMapping[]>([])
  const [gaps, setGaps] = useState<ComplianceGap[]>([])
  const [assessments, setAssessments] = useState<ComplianceAssessment[]>([])
  const [selectedName, setSelectedName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formValues, setFormValues] = useState<Record<string, unknown>>({})
  const [formMode, setFormMode] = useState<'framework' | 'gap' | 'assessment'>('framework')
  const crud = useCrud<ComplianceFramework | ComplianceGap | ComplianceAssessment>()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [frameworkList, mappingList, gapList, assessmentList] =
        await Promise.all([
          complianceApi.frameworks().catch(() => [] as ComplianceFramework[]),
          complianceApi.mappings().catch(() => [] as ControlMapping[]),
          complianceApi.gaps().catch(() => [] as ComplianceGap[]),
          complianceApi.assessments().catch(() => [] as ComplianceAssessment[]),
        ])
      setFrameworks(frameworkList)
      setMappings(mappingList)
      setGaps(gapList)
      setAssessments(assessmentList)

      if (frameworkList.length > 0 && !selectedName) {
        const first = frameworkList[0]
        setSelectedName(first.name)
        const reqs = await complianceApi
          .requirements(first.id)
          .catch(() => [] as FrameworkRequirement[])
        setRequirements(reqs)
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load compliance data.')
    } finally {
      setLoading(false)
    }
  }, [selectedName])

  useEffect(() => {
    void load()
  }, [load])

  const loadFramework = async (id: number, name: string) => {
    setSelectedName(name)
    const reqs = await complianceApi
      .requirements(id)
      .catch(() => [] as FrameworkRequirement[])
    setRequirements(reqs)
  }

  const handleCreateFramework = () => {
    setFormValues({})
    setFormMode('framework')
    crud.openCreate()
  }

  const handleCreateGap = () => {
    setFormValues({ status: 'open' })
    setFormMode('gap')
    crud.openCreate()
  }

  const handleCreateAssessment = () => {
    setFormValues({ overall_status: 'not_assessed' })
    setFormMode('assessment')
    crud.openCreate()
  }

  const handleEditFramework = (item: ComplianceFramework) => {
    setFormMode('framework')
    setFormValues({ ...(item as unknown as Record<string, unknown>) })
    crud.openEdit(item)
  }

  const handleEditGap = (item: ComplianceGap) => {
    setFormMode('gap')
    setFormValues({ ...(item as unknown as Record<string, unknown>) })
    crud.openEdit(item)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    crud.setSubmitting(true)
    crud.setError('')
    try {
      if (formMode === 'framework') {
        if (crud.mode === 'create') {
          await complianceApi.createFramework(formValues as Partial<ComplianceFramework>)
        }
      } else if (formMode === 'gap') {
        if (crud.mode === 'create') {
          await complianceApi.createGap(formValues as Partial<ComplianceGap>)
        } else if (crud.selected) {
          await complianceApi.updateGap(crud.selected.id, formValues as Partial<ComplianceGap>)
        }
      } else {
        if (crud.mode === 'create') {
          await complianceApi.createAssessment(formValues as Partial<ComplianceAssessment>)
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
      if (formMode === 'framework') {
        await complianceApi.removeFramework(crud.selected.id)
      } else if (formMode === 'gap') {
        await complianceApi.removeGap(crud.selected.id)
      }
      crud.close()
      await load()
    } catch (caught) {
      crud.setError(caught instanceof Error ? caught.message : 'Failed to delete.')
    } finally {
      crud.setSubmitting(false)
    }
  }

  const frameworkColumns: Column<ComplianceFramework>[] = [
    {
      key: 'name',
      header: 'Framework',
      render: (f) => (
        <div className="flex items-center gap-2">
          <button
            onClick={() => void loadFramework(f.id, f.name)}
            className="text-left font-medium text-cyan-200 hover:underline"
          >
            {f.name}
          </button>
          <button
            onClick={() => handleEditFramework(f)}
            className="text-xs text-cyan-400 hover:text-cyan-200 hover:underline"
          >
            Edit
          </button>
        </div>
      ),
    },
    { key: 'version', header: 'Version', render: (f) => f.version },
    { key: 'publisher', header: 'Publisher', render: (f) => f.publisher ?? '—' },
    { key: 'domain', header: 'Domain', render: (f) => f.domain ?? '—' },
    {
      key: 'is_active',
      header: 'Status',
      render: (f) =>
        f.is_active ? <Badge value="Active" tone="green" /> : <Badge value="Inactive" tone="slate" />,
    },
  ]

  const requirementColumns: Column<FrameworkRequirement>[] = [
    {
      key: 'requirement_id',
      header: 'Req ID',
      render: (r) => <Badge value={r.requirement_id} tone="cyan" />,
    },
    { key: 'title', header: 'Title', render: (r) => <span className="font-medium">{r.title}</span> },
    {
      key: 'requirement_type',
      header: 'Type',
      render: (r) => r.requirement_type ?? '—',
    },
    {
      key: 'weight_importance',
      header: 'Importance',
      render: (r) =>
        r.weight_importance ? (
          <Badge value={r.weight_importance} tone={statusTone(r.weight_importance)} />
        ) : (
          '—'
        ),
    },
  ]

  const gapColumns: Column<ComplianceGap>[] = [
    {
      key: 'gap_description',
      header: 'Gap',
      render: (g) => (
        <div className="flex items-center gap-2">
          <span className="font-medium">{g.gap_description}</span>
          <button
            onClick={() => handleEditGap(g)}
            className="text-xs text-cyan-400 hover:text-cyan-200 hover:underline"
          >
            Edit
          </button>
        </div>
      ),
    },
    { key: 'requirement_id', header: 'Requirement ID', render: (g) => g.requirement_id },
    {
      key: 'severity',
      header: 'Severity',
      render: (g) =>
        g.severity ? <Badge value={g.severity} tone={statusTone(g.severity)} /> : '—',
    },
    {
      key: 'status',
      header: 'Status',
      render: (g) =>
        g.status ? <Badge value={g.status} tone={statusTone(g.status)} /> : '—',
    },
    { key: 'target_closure_date', header: 'Target Closure', render: (g) => g.target_closure_date ?? '—' },
  ]

  const assessmentColumns: Column<ComplianceAssessment>[] = [
    { key: 'framework_id', header: 'Framework ID', render: (a) => a.framework_id },
    {
      key: 'overall_status',
      header: 'Status',
      render: (a) =>
        a.overall_status ? (
          <Badge value={a.overall_status} tone={statusTone(a.overall_status)} />
        ) : (
          '—'
        ),
    },
    {
      key: 'compliance_percentage',
      header: 'Compliance %',
      render: (a) =>
        typeof a.compliance_percentage === 'number'
          ? `${a.compliance_percentage.toFixed(1)}%`
          : '—',
    },
    { key: 'assessment_date', header: 'Assessment Date', render: (a) => a.assessment_date ?? '—' },
  ]

  return (
    <div>
      <PageHeader
        title="Compliance"
        description="Compliance frameworks, requirements, control mappings, gap analysis, and assessments."
        action={
          <div className="flex items-center gap-2">
            <button
              onClick={handleCreateFramework}
              className="rounded-full bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500"
            >
              + Framework
            </button>
            <button
              onClick={handleCreateGap}
              className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-500/50 hover:text-cyan-200"
            >
              + Gap
            </button>
            <button
              onClick={handleCreateAssessment}
              className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-500/50 hover:text-cyan-200"
            >
              + Assessment
            </button>
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
          Loading compliance data…
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-rose-200">
          {error}
        </div>
      ) : (
        <div className="space-y-8">
          <section>
            <h3 className="mb-3 text-lg font-semibold">Frameworks</h3>
            <GrcTable
              columns={frameworkColumns}
              rows={frameworks}
              rowKey={(f) => f.id}
              emptyMessage="No frameworks loaded."
            />
          </section>

          {requirements.length > 0 ? (
            <section>
              <h3 className="mb-3 text-lg font-semibold">
                Requirements: {selectedName}
                <span className="text-sm font-normal text-slate-400">
                  {' '}({requirements.length})
                </span>
              </h3>
              <GrcTable
                columns={requirementColumns}
                rows={requirements.slice(0, 50)}
                rowKey={(r) => r.id}
                emptyMessage="No requirements for this framework."
              />
            </section>
          ) : null}

          <div className="grid gap-6 xl:grid-cols-2">
            <section>
              <h3 className="mb-3 text-lg font-semibold">
                Control Mappings <span className="text-sm font-normal text-slate-400">({mappings.length})</span>
              </h3>
              <GrcTable
                columns={[
                  { key: 'control_id', header: 'Control ID', render: (m) => m.control_id },
                  { key: 'requirement_id', header: 'Requirement ID', render: (m) => m.requirement_id },
                  {
                    key: 'mapping_type',
                    header: 'Type',
                    render: (m) =>
                      m.mapping_type ? <Badge value={m.mapping_type} /> : '—',
                  },
                ]}
                rows={mappings.slice(0, 30)}
                rowKey={(m) => m.id}
                emptyMessage="No control mappings yet."
              />
            </section>

            <section>
              <h3 className="mb-3 text-lg font-semibold">
                Compliance Assessments{' '}
                <span className="text-sm font-normal text-slate-400">({assessments.length})</span>
              </h3>
              <GrcTable
                columns={assessmentColumns}
                rows={assessments}
                rowKey={(a) => a.id}
                emptyMessage="No assessments yet."
              />
            </section>
          </div>

          {gaps.length > 0 ? (
            <section>
              <h3 className="mb-3 text-lg font-semibold">
                Compliance Gaps <span className="text-sm font-normal text-slate-400">({gaps.length})</span>
              </h3>
              <GrcTable
                columns={gapColumns}
                rows={gaps}
                rowKey={(g) => g.id}
                emptyMessage="No compliance gaps recorded."
              />
            </section>
          ) : null}
        </div>
      )}

      {/* Create/Edit Modal */}
      <Modal
        open={crud.open}
        onClose={crud.close}
        title={
          formMode === 'framework'
            ? `${crud.mode === 'create' ? 'Create' : 'Edit'} Compliance Framework`
            : formMode === 'gap'
              ? `${crud.mode === 'create' ? 'Create' : 'Edit'} Compliance Gap`
              : 'Create Compliance Assessment'
        }
      >
        <form onSubmit={handleSubmit}>
          <GrcFormSection
            title={
              formMode === 'framework'
                ? 'Framework Details'
                : formMode === 'gap'
                  ? 'Gap Details'
                  : 'Assessment Details'
            }
          >
            <GrcForm
              fields={
                formMode === 'framework'
                  ? FRAMEWORK_FIELDS
                  : formMode === 'gap'
                    ? GAP_FIELDS
                    : ASSESSMENT_FIELDS
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

