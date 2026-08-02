import { useCallback, useEffect, useState } from 'react'
import GrcTable from '../components/grc/GrcTable'
import type { Column } from '../components/grc/GrcTable'
import PageHeader from '../components/grc/PageHeader'
import { threatApi, vulnerabilityApi } from '../services/grc'
import type { Threat, ThreatActor, ThreatCategory, Vulnerability } from '../types/grc'

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

function severityTone(value: string): 'green' | 'amber' | 'rose' | 'slate' {
  if (value === 'critical') return 'rose'
  if (value === 'high') return 'rose'
  if (value === 'medium') return 'amber'
  if (value === 'low') return 'green'
  return 'slate'
}

export default function ThreatsPage() {
  const [threats, setThreats] = useState<Threat[]>([])
  const [categories, setCategories] = useState<ThreatCategory[]>([])
  const [actors, setActors] = useState<ThreatActor[]>([])
  const [vulns, setVulns] = useState<Vulnerability[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [threatList, catList, actorList, vulnList] = await Promise.all([
        threatApi.list().catch(() => [] as Threat[]),
        threatApi.categories().catch(() => [] as ThreatCategory[]),
        threatApi.actors().catch(() => [] as ThreatActor[]),
        vulnerabilityApi.list().catch(() => [] as Vulnerability[]),
      ])
      setThreats(threatList)
      setCategories(catList)
      setActors(actorList)
      setVulns(vulnList)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load threats.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const catName = (id?: number | null) =>
    categories.find((c) => c.id === id)?.name ?? '—'

  const threatColumns: Column<Threat>[] = [
    {
      key: 'name',
      header: 'Threat',
      render: (t) => <span className="font-medium">{t.name}</span>,
    },
    {
      key: 'threat_id',
      header: 'Threat ID',
      render: (t) => (t.threat_id ? <Badge value={t.threat_id} tone="cyan" /> : '—'),
    },
    {
      key: 'threat_category_id',
      header: 'Category',
      render: (t) => catName(t.threat_category_id),
    },
    {
      key: 'source',
      header: 'Source',
      render: (t) => t.source ?? '—',
    },
    {
      key: 'likelihood_rating',
      header: 'Likelihood',
      render: (t) =>
        t.likelihood_rating ? (
          <Badge value={t.likelihood_rating} tone={severityTone(t.likelihood_rating)} />
        ) : (
          '—'
        ),
    },
    {
      key: 'ics_impact',
      header: 'ICS Impact',
      render: (t) => t.ics_impact ?? '—',
    },
  ]

  const actorColumns: Column<ThreatActor>[] = [
    { key: 'name', header: 'Actor', render: (a) => <span className="font-medium">{a.name}</span> },
    { key: 'actor_type', header: 'Type', render: (a) => a.actor_type ?? '—' },
    { key: 'capability', header: 'Capability', render: (a) => a.capability ?? '—' },
    { key: 'motivation', header: 'Motivation', render: (a) => a.motivation ?? '—' },
  ]

  const vulnColumns: Column<Vulnerability>[] = [
    {
      key: 'name',
      header: 'Vulnerability',
      render: (v) => <span className="font-medium">{v.name}</span>,
    },
    { key: 'cve_id', header: 'CVE', render: (v) => v.cve_id ?? '—' },
    {
      key: 'cvss_severity',
      header: 'Severity',
      render: (v) =>
        v.cvss_severity ? (
          <Badge value={v.cvss_severity} tone={severityTone(v.cvss_severity)} />
        ) : (
          '—'
        ),
    },
    {
      key: 'cvss_score',
      header: 'CVSS',
      render: (v) => (typeof v.cvss_score === 'number' ? v.cvss_score.toFixed(1) : '—'),
    },
    { key: 'affected_product', header: 'Affected Product', render: (v) => v.affected_product ?? '—' },
    {
      key: 'patch_available',
      header: 'Patch',
      render: (v) =>
        v.patch_available ? <Badge value="Available" tone="green" /> : <Badge value="None" tone="rose" />,
    },
  ]

  return (
    <div>
      <PageHeader
        title="Threats & Vulnerabilities"
        description="Threat library, threat actors, and the vulnerability registry."
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
          Loading threats…
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-rose-200">
          {error}
        </div>
      ) : (
        <div className="space-y-8">
          <section>
            <h3 className="mb-3 text-lg font-semibold">
              Threat Library <span className="text-sm font-normal text-slate-400">({threats.length})</span>
            </h3>
            <GrcTable
              columns={threatColumns}
              rows={threats}
              rowKey={(t) => t.id}
              emptyMessage="No threats in the library yet."
            />
          </section>

          {actors.length > 0 ? (
            <section>
              <h3 className="mb-3 text-lg font-semibold">
                Threat Actors <span className="text-sm font-normal text-slate-400">({actors.length})</span>
              </h3>
              <GrcTable
                columns={actorColumns}
                rows={actors}
                rowKey={(a) => a.id}
                emptyMessage="No threat actors registered."
              />
            </section>
          ) : null}

          <section>
            <h3 className="mb-3 text-lg font-semibold">
              Vulnerability Registry <span className="text-sm font-normal text-slate-400">({vulns.length})</span>
            </h3>
            <GrcTable
              columns={vulnColumns}
              rows={vulns}
              rowKey={(v) => v.id}
              emptyMessage="No vulnerabilities registered."
            />
          </section>
        </div>
      )}
    </div>
  )
}

