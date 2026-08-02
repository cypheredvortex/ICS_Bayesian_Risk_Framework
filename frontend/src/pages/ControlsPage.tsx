import { useCallback, useEffect, useState } from 'react'
import GrcTable from '../components/grc/GrcTable'
import type { Column } from '../components/grc/GrcTable'
import PageHeader from '../components/grc/PageHeader'
import { Modal } from '../components/grc/Modal'
import { GrcForm, GrcFormActions, GrcFormSection } from '../components/grc/GrcForm'
import type { FormFieldConfig } from '../components/grc/GrcForm'
import { useCrud } from '../hooks/useCrud'
import { controlApi } from '../services/grc'
import type { Control, ControlCategory, ControlTest, ControlEvidence } from '../types/grc'

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
  if (value === 'implemented') return 'green'
  if (value === 'partially') return 'amber'
  if (value === 'planned') return 'cyan'
  if (value === 'not_implemented') return 'rose'
  return 'slate'
}

const CONTROL_FIELDS: FormFieldConfig[] = [
  { name: 'name', label: 'Control Name', type: 'text', required: true },
  { name: 'control_id', label: 'Control ID', type: 'text', placeholder: 'e.g., AC-1, ICS-01' },
  { name: 'control_type', label: 'Control Type', type: 'select', options: [
    { value: 'preventive', label: 'Preventive' },
    { value: 'detective', label: 'Detective' },
    { value: 'corrective', label: 'Corrective' },
    { value: 'deterrent', label: 'Deterrent' },
  ]},
  { name: 'implementation_status', label: 'Implementation Status', type: 'select', options: [
    { value: 'implemented', label: 'Implemented' },
    { value: 'partially', label: 'Partially Implemented' },
    { value: 'planned', label: 'Planned' },
    { value: 'not_implemented', label: 'Not Implemented' },
  ]},
  { name: 'effectiveness_rating', label: 'Effectiveness', type: 'select', options: [
    { value: 'very_high', label: 'Very High' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' },
    { value: 'very_low', label: 'Very Low' },
  ]},
  { name: 'automation_level', label: 'Automation Level', type: 'select', options: [
    { value: 'automated', label: 'Automated' },
    { value: 'semi_automated', label: 'Semi-Automated' },
    { value: 'manual', label: 'Manual' },
  ]},
  { name: 'frequency', label: 'Frequency', type: 'select', options: [
    { value: 'continuous', label: 'Continuous' },
    { value: 'daily', label: 'Daily' },
    { value: 'weekly', label: 'Weekly' },
    { value: 'monthly', label: 'Monthly' },
    { value: 'quarterly', label: 'Quarterly' },
    { value: 'annually', label: 'Annually' },
  ]},
  { name: 'evidence_required', label: 'Evidence Required', type: 'checkbox' },
  { name: 'evidence_description', label: 'Evidence Description', type: 'textarea' },
  { name: 'description', label: 'Description', type: 'textarea' },
  { name: 'last_reviewed_date', label: 'Last Reviewed', type: 'date' },
  { name: 'next_review_date', label: 'Next Review', type: 'date' },
]

export default function ControlsPage() {
  const [controls, setControls] = useState<Control[]>([])
  const [categories, setCategories] = useState<ControlCategory[]>([])
  const [tests, setTests] = useState<ControlTest[]>([])
  const [evidence, setEvidence] = useState<ControlEvidence[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formValues, setFormValues] = useState<Record<string, unknown>>({})
  const crud = useCrud<Control>()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [controlList, categoryList] = await Promise.all([
        controlApi.list().catch(() => [] as Control[]),
        controlApi.categories().catch(() => [] as ControlCategory[]),
      ])
      setControls(controlList)
      setCategories(categoryList)

      if (controlList.length > 0) {
        const first = controlList[0].id
        const [testList, evidenceList] = await Promise.all([
          controlApi.tests(first).catch(() => [] as ControlTest[]),
          controlApi.evidence(first).catch(() => [] as ControlEvidence[]),
        ])
        setTests(testList)
        setEvidence(evidenceList)
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load controls.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const handleCreate = () => {
    setFormValues({ evidence_required: false })
    crud.openCreate()
  }

  const handleEdit = (control: Control) => {
    setFormValues({ ...(control as unknown as Record<string, unknown>) })
    crud.openEdit(control)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    crud.setSubmitting(true)
    crud.setError('')
    try {
      if (crud.mode === 'create') {
        await controlApi.create(formValues as Partial<Control>)
      } else if (crud.selected) {
        await controlApi.update(crud.selected.id, formValues as Partial<Control>)
      }
      crud.close()
      await load()
    } catch (caught) {
      crud.setError(caught instanceof Error ? caught.message : 'Failed to save control.')
    } finally {
      crud.setSubmitting(false)
    }
  }

  const handleDelete = async () => {
    if (!crud.selected) return
    crud.setSubmitting(true)
    try {
      await controlApi.remove(crud.selected.id)
      crud.close()
      await load()
    } catch (caught) {
      crud.setError(caught instanceof Error ? caught.message : 'Failed to delete control.')
    } finally {
      crud.setSubmitting(false)
    }
  }

  const columns: Column<Control>[] = [
    {
      key: 'name',
      header: 'Control',
      render: (c) => (
        <div className="flex items-center gap-2">
          <span className="font-medium">{c.name}</span>
          <button
            onClick={() => handleEdit(c)}
            className="text-xs text-cyan-400 hover:text-cyan-200 hover:underline"
          >
            Edit
          </button>
        </div>
      ),
    },
    {
      key: 'control_id',
      header: 'Control ID',
      render: (c) => (c.control_id ? <Badge value={c.control_id} tone="cyan" /> : '—'),
    },
    {
      key: 'control_type',
      header: 'Type',
      render: (c) => c.control_type ?? '—',
    },
    {
      key: 'implementation_status',
      header: 'Implementation',
      render: (c) =>
        c.implementation_status ? (
          <Badge value={c.implementation_status} tone={statusTone(c.implementation_status)} />
        ) : (
          '—'
        ),
    },
    {
      key: 'effectiveness_rating',
      header: 'Effectiveness',
      render: (c) =>
        c.effectiveness_rating ? (
          <Badge value={c.effectiveness_rating} tone={statusTone(c.effectiveness_rating)} />
        ) : (
          '—'
        ),
    },
    {
      key: 'automation_level',
      header: 'Automation',
      render: (c) => c.automation_level ?? '—',
    },
    {
      key: 'frequency',
      header: 'Frequency',
      render: (c) => c.frequency ?? '—',
    },
  ]

  return (
    <div>
      <PageHeader
        title="Control Library"
        description="Security controls catalog with implementation status, effectiveness, testing, and evidence."
        action={
          <div className="flex items-center gap-2">
            <button
              onClick={handleCreate}
              className="rounded-full bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500"
            >
              + Create Control
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
          Loading controls…
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-rose-200">
          {error}
        </div>
      ) : (
        <div className="space-y-8">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
              <p className="text-xs uppercase tracking-wider text-slate-400">Controls</p>
              <p className="mt-2 text-3xl font-semibold">{controls.length}</p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
              <p className="text-xs uppercase tracking-wider text-slate-400">Categories</p>
              <p className="mt-2 text-3xl font-semibold">{categories.length}</p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
              <p className="text-xs uppercase tracking-wider text-slate-400">Tests (first control)</p>
              <p className="mt-2 text-3xl font-semibold">{tests.length}</p>
            </div>
          </div>

          <GrcTable
            columns={columns}
            rows={controls}
            rowKey={(c) => c.id}
            emptyMessage="No controls in the library yet."
          />

          {tests.length > 0 ? (
            <section>
              <h3 className="mb-3 text-lg font-semibold">Control Tests</h3>
              <GrcTable
                columns={[
                  { key: 'test_date', header: 'Date', render: (t) => t.test_date ?? '—' },
                  { key: 'test_method', header: 'Method', render: (t) => t.test_method ?? '—' },
                  {
                    key: 'result',
                    header: 'Result',
                    render: (t) =>
                      t.result ? (
                        <Badge value={t.result} tone={statusTone(t.result)} />
                      ) : (
                        '—'
                      ),
                  },
                  { key: 'tester_id', header: 'Tester ID', render: (t) => t.tester_id ?? '—' },
                ]}
                rows={tests}
                rowKey={(t) => t.id}
              />
            </section>
          ) : null}

          {evidence.length > 0 ? (
            <section>
              <h3 className="mb-3 text-lg font-semibold">Control Evidence</h3>
              <GrcTable
                columns={[
                  {
                    key: 'filename',
                    header: 'File',
                    render: (e) => <span className="font-medium">{e.filename}</span>,
                  },
                  { key: 'evidence_type', header: 'Type', render: (e) => e.evidence_type ?? '—' },
                  { key: 'description', header: 'Description', render: (e) => e.description ?? '—' },
                ]}
                rows={evidence}
                rowKey={(e) => e.id}
              />
            </section>
          ) : null}
        </div>
      )}

      {/* Create/Edit Modal */}
      <Modal
        open={crud.open}
        onClose={crud.close}
        title={crud.mode === 'create' ? 'Create Control' : 'Edit Control'}
      >
        <form onSubmit={handleSubmit}>
          <GrcFormSection title="Control Details">
            <GrcForm
              fields={CONTROL_FIELDS}
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
            submitLabel={crud.mode === 'create' ? 'Create Control' : 'Save Changes'}
            onDelete={crud.mode === 'edit' ? handleDelete : undefined}
            deleteLabel="Delete Control"
          />
        </form>
      </Modal>
    </div>
  )
}

