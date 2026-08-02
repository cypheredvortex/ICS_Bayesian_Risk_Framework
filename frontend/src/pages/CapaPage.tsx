import { useCallback, useEffect, useState } from 'react'
import GrcTable from '../components/grc/GrcTable'
import type { Column } from '../components/grc/GrcTable'
import PageHeader from '../components/grc/PageHeader'
import { capaApi } from '../services/grc'
import type { ActionTask, CorrectiveAction, EffectivenessReview } from '../types/grc'

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
  if (value === 'critical') return 'rose'
  if (value === 'high') return 'rose'
  if (value === 'medium') return 'amber'
  if (value === 'low') return 'green'
  if (value === 'closed' || value === 'verified' || value === 'completed') return 'green'
  if (value === 'open' || value === 'in_progress' || value === 'implemented') return 'amber'
  if (value === 'effective') return 'green'
  if (value === 'partially_effective') return 'amber'
  if (value === 'not_effective') return 'rose'
  return 'slate'
}

export default function CapaPage() {
  const [actions, setActions] = useState<CorrectiveAction[]>([])
  const [tasks, setTasks] = useState<ActionTask[]>([])
  const [reviews, setReviews] = useState<EffectivenessReview[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const list = await capaApi.list().catch(() => [] as CorrectiveAction[])
      setActions(list)
      if (list.length > 0) {
        const id = list[0].id
        setSelectedId(id)
        await loadDetail(id)
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load corrective actions.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const loadDetail = async (id: number) => {
    setSelectedId(id)
    const [taskList, reviewList] = await Promise.all([
      capaApi.tasks(id).catch(() => [] as ActionTask[]),
      capaApi.reviews(id).catch(() => [] as EffectivenessReview[]),
    ])
    setTasks(taskList)
    setReviews(reviewList)
  }

  const columns: Column<CorrectiveAction>[] = [
    {
      key: 'title',
      header: 'Action',
      render: (a) => (
        <button
          onClick={() => void loadDetail(a.id)}
          className="text-left font-medium text-cyan-200 hover:underline"
        >
          {a.title}
        </button>
      ),
    },
    { key: 'action_id', header: 'Action ID', render: (a) => (a.action_id ? <Badge value={a.action_id} tone="cyan" /> : '—') },
    { key: 'action_type', header: 'Type', render: (a) => a.action_type ?? '—' },
    {
      key: 'priority',
      header: 'Priority',
      render: (a) => (a.priority ? <Badge value={a.priority} tone={statusTone(a.priority)} /> : '—'),
    },
    {
      key: 'status',
      header: 'Status',
      render: (a) => (a.status ? <Badge value={a.status} tone={statusTone(a.status)} /> : '—'),
    },
    {
      key: 'assigned_to_id',
      header: 'Assignee',
      render: (a) => a.assigned_to_id ?? '—',
    },
    { key: 'target_date', header: 'Target', render: (a) => a.target_date ?? '—' },
    {
      key: 'is_closed',
      header: 'Closed',
      render: (a) =>
        a.is_closed ? <Badge value="Closed" tone="green" /> : <Badge value="Open" tone="amber" />,
    },
  ]

  return (
    <div>
      <PageHeader
        title="Corrective Actions (CAPA)"
        description="Corrective and preventive action workflow with tasks and effectiveness reviews."
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
          Loading corrective actions…
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-rose-200">
          {error}
        </div>
      ) : (
        <div className="space-y-8">
          <GrcTable
            columns={columns}
            rows={actions}
            rowKey={(a) => a.id}
            emptyMessage="No corrective actions yet."
          />

          <div className="grid gap-6 xl:grid-cols-2">
            <section>
              <h3 className="mb-3 text-lg font-semibold">
                Action Tasks{' '}
                <span className="text-sm font-normal text-slate-400">
                  {selectedId ? `for action ${selectedId}` : ''}
                </span>
              </h3>
              <GrcTable
                columns={[
                  { key: 'title', header: 'Task', render: (t) => <span className="font-medium">{t.title}</span> },
                  { key: 'status', header: 'Status', render: (t) => (t.status ? <Badge value={t.status} tone={statusTone(t.status)} /> : '—') },
                  { key: 'due_date', header: 'Due', render: (t) => t.due_date ?? '—' },
                ]}
                rows={tasks}
                rowKey={(t) => t.id}
                emptyMessage="No tasks for this action."
              />
            </section>

            <section>
              <h3 className="mb-3 text-lg font-semibold">Effectiveness Reviews</h3>
              <GrcTable
                columns={[
                  { key: 'review_date', header: 'Date', render: (r) => r.review_date ?? '—' },
                  {
                    key: 'result',
                    header: 'Result',
                    render: (r) =>
                      r.result ? <Badge value={r.result} tone={statusTone(r.result)} /> : '—',
                  },
                  { key: 'findings', header: 'Findings', render: (r) => r.findings ?? '—' },
                ]}
                rows={reviews}
                rowKey={(r) => r.id}
                emptyMessage="No effectiveness reviews yet."
              />
            </section>
          </div>
        </div>
      )}
    </div>
  )
}

