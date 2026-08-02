import { useCallback, useEffect, useState } from 'react'
import GrcTable from '../components/grc/GrcTable'
import type { Column } from '../components/grc/GrcTable'
import PageHeader from '../components/grc/PageHeader'
import { Modal } from '../components/grc/Modal'
import { GrcForm, GrcFormActions, GrcFormSection } from '../components/grc/GrcForm'
import type { FormFieldConfig } from '../components/grc/GrcForm'
import { useCrud } from '../hooks/useCrud'
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

const THREAT_FIELDS: FormFieldConfig[] = [
  { name: 'name', label: 'Threat Name', type: 'text', required: true },
  { name: 'threat_id', label: 'Threat ID', type: 'text', placeholder: 'e.g., T0886' },
  { name: 'source', label: 'Source', type: 'select', options: [
    { value: 'mitre_ics', label: 'MITRE ICS' },
    { value: 'stride', label: 'STRIDE' },
    { value: 'custom', label: 'Custom' },
  ]},
  { name: 'likelihood_rating', label: 'Likelihood', type: 'select', options: [
    { value: 'very_high', label: 'Very High' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' },
    { value: 'very_low', label: 'Very Low' },
  ]},
  { name: 'typical_impact', label: 'Typical Impact', type: 'select', options: [
    { value: 'safety', label: 'Safety' },
    { value: 'environmental', label: 'Environmental' },
    { value: 'operational', label: 'Operational' },
    { value: 'financial', label: 'Financial' },
  ]},
  { name: 'ics_impact', label: 'ICS Impact', type: 'select', options: [
    { value: 'loss_of_view', label: 'Loss of View' },
    { value: 'loss_of_control', label: 'Loss of Control' },
    { value: 'equipment_damage', label: 'Equipment Damage' },
    { value: 'safety_impact', label: 'Safety Impact' },
  ]},
  { name: 'description', label: 'Description', type: 'textarea' },
]

const VULN_FIELDS: FormFieldConfig[] = [
  { name: 'name', label: 'Vulnerability Name', type: 'text', required: true },
  { name: 'cve_id', label: 'CVE ID', type: 'text', placeholder: 'e.g., CVE-2024-0001' },
  { name: 'vulnerability_type', label: 'Type', type: 'text', placeholder: 'e.g., buffer_overflow' },
  { name: 'cvss_score', label: 'CVSS Score', type: 'number', min: 0, max: 10, step: 0.1 },
  { name: 'cvss_severity', label: 'CVSS Severity', type: 'select', options: [
    { value: 'none', label: 'None' },
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'critical', label: 'Critical' },
  ]},
  { name: 'exploit_available', label: 'Exploit Available', type: 'checkbox' },
  { name: 'patch_available', label: 'Patch Available', type: 'checkbox' },
  { name: 'affected_vendor', label: 'Affected Vendor', type: 'text' },
  { name: 'affected_product', label: 'Affected Product', type: 'text' },
  { name: 'affected_version', label: 'Affected Version', type: 'text' },
  { name: 'description', label: 'Description', type: 'textarea' },
]

const ACTOR_FIELDS: FormFieldConfig[] = [
  { name: 'name', label: 'Actor Name', type: 'text', required: true },
  { name: 'actor_type', label: 'Actor Type', type: 'select', options: [
    { value: 'nation_state', label: 'Nation State' },
    { value: 'criminal', label: 'Criminal' },
    { value: 'hacktivist', label: 'Hacktivist' },
    { value: 'insider', label: 'Insider' },
    { value: 'terrorist', label: 'Terrorist' },
  ]},
  { name: 'capability', label: 'Capability', type: 'select', options: [
    { value: 'advanced', label: 'Advanced' },
    { value: 'moderate', label: 'Moderate' },
    { value: 'basic', label: 'Basic' },
  ]},
  { name: 'motivation', label: 'Motivation', type: 'text' },
  { name: 'description', label: 'Description', type: 'textarea' },
  { name: 'targeting_sectors', label: 'Targeting Sectors', type: 'textarea' },
  { name: 'common_ttps', label: 'Common TTPs', type: 'textarea' },
]

export default function ThreatsPage() {
  const [threats, setThreats] = useState<Threat[]>([])
  const [categories, setCategories] = useState<ThreatCategory[]>([])
  const [actors, setActors] = useState<ThreatActor[]>([])
  const [vulns, setVulns] = useState<Vulnerability[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formValues, setFormValues] = useState<Record<string, unknown>>({})
  const [activeTab, setActiveTab] = useState<'threats' | 'actors' | 'vulns'>('threats')
  const crud = useCrud<Threat | ThreatActor | Vulnerability>()

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

  const handleCreateThreat = () => {
    setFormValues({ source: 'custom' })
    setActiveTab('threats')
    crud.openCreate()
  }

  const handleCreateActor = () => {
    setFormValues({})
    setActiveTab('actors')
    crud.openCreate()
  }

  const handleCreateVuln = () => {
    setFormValues({ exploit_available: false, patch_available: false })
    setActiveTab('vulns')
    crud.openCreate()
  }

const handleEdit = (item: Threat | ThreatActor | Vulnerability, tab: 'threats' | 'actors' | 'vulns') => {
    setActiveTab(tab)
    setFormValues({ ...(item as unknown as Record<string, unknown>) })
    crud.openEdit(item)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    crud.setSubmitting(true)
    crud.setError('')
    try {
      if (crud.mode === 'create') {
        if (activeTab === 'threats') {
          await threatApi.create(formValues as Partial<Threat>)
        } else if (activeTab === 'actors') {
          await threatApi.createActor(formValues as Partial<ThreatActor>)
        } else {
          await vulnerabilityApi.create(formValues as Partial<Vulnerability>)
        }
      } else if (crud.selected) {
        if (activeTab === 'threats') {
          await threatApi.update(crud.selected.id, formValues as Partial<Threat>)
        } else if (activeTab === 'actors') {
          await threatApi.updateActor(crud.selected.id, formValues as Partial<ThreatActor>)
        } else {
          await vulnerabilityApi.update(crud.selected.id, formValues as Partial<Vulnerability>)
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
      if (activeTab === 'threats') {
        await threatApi.remove(crud.selected.id)
      } else if (activeTab === 'actors') {
        await threatApi.removeActor(crud.selected.id)
      } else {
        await vulnerabilityApi.remove(crud.selected.id)
      }
      crud.close()
      await load()
    } catch (caught) {
      crud.setError(caught instanceof Error ? caught.message : 'Failed to delete.')
    } finally {
      crud.setSubmitting(false)
    }
  }

  const threatColumns: Column<Threat>[] = [
    {
      key: 'name',
      header: 'Threat',
      render: (t) => (
        <div className="flex items-center gap-2">
          <span className="font-medium">{t.name}</span>
          <button
            onClick={() => handleEdit(t, 'threats')}
            className="text-xs text-cyan-400 hover:text-cyan-200 hover:underline"
          >
            Edit
          </button>
        </div>
      ),
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
    {
      key: 'name',
      header: 'Actor',
      render: (a) => (
        <div className="flex items-center gap-2">
          <span className="font-medium">{a.name}</span>
          <button
            onClick={() => handleEdit(a, 'actors')}
            className="text-xs text-cyan-400 hover:text-cyan-200 hover:underline"
          >
            Edit
          </button>
        </div>
      ),
    },
    { key: 'actor_type', header: 'Type', render: (a) => a.actor_type ?? '—' },
    { key: 'capability', header: 'Capability', render: (a) => a.capability ?? '—' },
    { key: 'motivation', header: 'Motivation', render: (a) => a.motivation ?? '—' },
  ]

  const vulnColumns: Column<Vulnerability>[] = [
    {
      key: 'name',
      header: 'Vulnerability',
      render: (v) => (
        <div className="flex items-center gap-2">
          <span className="font-medium">{v.name}</span>
          <button
            onClick={() => handleEdit(v, 'vulns')}
            className="text-xs text-cyan-400 hover:text-cyan-200 hover:underline"
          >
            Edit
          </button>
        </div>
      ),
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

  const getFormFields = () => {
    if (activeTab === 'threats') return THREAT_FIELDS
    if (activeTab === 'actors') return ACTOR_FIELDS
    return VULN_FIELDS
  }

  const getModalTitle = () => {
    const prefix = crud.mode === 'create' ? 'Create' : 'Edit'
    if (activeTab === 'threats') return `${prefix} Threat`
    if (activeTab === 'actors') return `${prefix} Threat Actor`
    return `${prefix} Vulnerability`
  }

  return (
    <div>
      <PageHeader
        title="Threats & Vulnerabilities"
        description="Threat library, threat actors, and the vulnerability registry."
        action={
          <div className="flex items-center gap-2">
            <button
              onClick={handleCreateThreat}
              className="rounded-full bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500"
            >
              + Threat
            </button>
            <button
              onClick={handleCreateActor}
              className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-500/50 hover:text-cyan-200"
            >
              + Actor
            </button>
            <button
              onClick={handleCreateVuln}
              className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-500/50 hover:text-cyan-200"
            >
              + Vulnerability
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

      {/* Create/Edit Modal */}
      <Modal
        open={crud.open}
        onClose={crud.close}
        title={getModalTitle()}
      >
        <form onSubmit={handleSubmit}>
          <GrcFormSection title={activeTab === 'threats' ? 'Threat Details' : activeTab === 'actors' ? 'Actor Details' : 'Vulnerability Details'}>
            <GrcForm
              fields={getFormFields()}
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

