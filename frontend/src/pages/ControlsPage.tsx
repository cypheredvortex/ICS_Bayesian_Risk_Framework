import { useCallback, useEffect, useState } from 'react'
import GrcTable from '../components/grc/GrcTable'
import type { Column } from '../components/grc/GrcTable'
import PageHeader from '../components/grc/PageHeader'
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

export default function ControlsPage() {
  const [controls, setControls] = useState<Control[]>([])
  const [categories, setCategories] = useState<ControlCategory[]>([])
  const [tests, setTests] = useState<ControlTest[]>([])
  const [evidence, setEvidence] = useState<ControlEvidence[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [controlList, categoryList] = await Promise.all([
        controlApi.list().catch(() => [] as Control[]),
        controlApi.categories().catch(() => [] as ControlCategory[]),
      ])
      setControls(controlList)
      setCategories(categoryList)

      // Load tests/evidence for first control if available
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

  const columns: Column<Control>[] = [
    {
      key: 'name',
      header: 'Control',
      render: (c) => <span className="font-medium">{c.name}</span>,
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
    </div>
  )
}

