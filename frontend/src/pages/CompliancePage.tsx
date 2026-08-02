import { useCallback, useEffect, useState } from 'react'
import GrcTable from '../components/grc/GrcTable'
import type { Column } from '../components/grc/GrcTable'
import PageHeader from '../components/grc/PageHeader'
import { complianceApi, controlApi } from '../services/grc'
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

export default function CompliancePage() {
  const [frameworks, setFrameworks] = useState<ComplianceFramework[]>([])
  const [requirements, setRequirements] = useState<FrameworkRequirement[]>([])
  const [mappings, setMappings] = useState<ControlMapping[]>([])
  const [gaps, setGaps] = useState<ComplianceGap[]>([])
  const [assessments, setAssessments] = useState<ComplianceAssessment[]>([])
  const [selectedName, setSelectedName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

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

  const frameworkColumns: Column<ComplianceFramework>[] = [
    {
      key: 'name',
      header: 'Framework',
      render: (f) => (
        <button
          onClick={() => void loadFramework(f.id, f.name)}
          className="text-left font-medium text-cyan-200 hover:underline"
        >
          {f.name}
        </button>
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
      render: (g) => <span className="font-medium">{g.gap_description}</span>,
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
    </div>
  )
}

