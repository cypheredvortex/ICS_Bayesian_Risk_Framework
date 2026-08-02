import { useCallback, useEffect, useState } from 'react'
import GrcTable from '../components/grc/GrcTable'
import type { Column } from '../components/grc/GrcTable'
import PageHeader from '../components/grc/PageHeader'
import { assetApi, vulnerabilityApi, organizationApi } from '../services/grc'
import type {
  Asset,
  AssetCategory,
  Organization,
  Vulnerability,
} from '../types/grc'

function Badge({
  value,
  tone,
}: {
  value: string
  tone?: 'green' | 'amber' | 'rose' | 'slate'
}) {
  const tones: Record<string, string> = {
    green: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
    amber: 'bg-amber-500/15 text-amber-300 ring-amber-500/30',
    rose: 'bg-rose-500/15 text-rose-300 ring-rose-500/30',
    slate: 'bg-slate-500/15 text-slate-300 ring-slate-500/30',
  }
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${tones[tone ?? 'slate']}`}
    >
      {value}
    </span>
  )
}

export default function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([])
  const [categories, setCategories] = useState<AssetCategory[]>([])
  const [vulns, setVulns] = useState<Vulnerability[]>([])
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [assetList, categoryList, vulnList, orgList] = await Promise.all([
        assetApi.list().catch(() => [] as Asset[]),
        assetApi.categories().catch(() => [] as AssetCategory[]),
        vulnerabilityApi.list().catch(() => [] as Vulnerability[]),
        organizationApi.list().catch(() => [] as Organization[]),
      ])
      setAssets(assetList)
      setCategories(categoryList)
      setVulns(vulnList)
      setOrganizations(orgList)
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : 'Could not load assets.',
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const columns: Column<Asset>[] = [
    { key: 'name', header: 'Asset', render: (a) => <span className="font-medium">{a.name}</span> },
    {
      key: 'asset_type',
      header: 'Type',
      render: (a) => a.asset_type ?? '—',
    },
    {
      key: 'criticality',
      header: 'Criticality',
      render: (a) =>
        a.criticality ? (
          <Badge
            value={a.criticality}
            tone={
              a.criticality === 'critical'
                ? 'rose'
                : a.criticality === 'high'
                  ? 'amber'
                  : a.criticality === 'medium'
                    ? 'amber'
                    : 'green'
            }
          />
        ) : (
          '—'
        ),
    },
    {
      key: 'operational_status',
      header: 'Status',
      render: (a) => a.operational_status ?? '—',
    },
    {
      key: 'vendor',
      header: 'Vendor',
      render: (a) => a.vendor ?? '—',
    },
    {
      key: 'ip_address',
      header: 'IP',
      render: (a) => a.ip_address ?? '—',
    },
  ]

  return (
    <div>
      <PageHeader
        title="Asset Register"
        description="ICS asset register with classification, ownership, and vulnerability linkage."
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
          Loading assets…
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-rose-200">
          {error}
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
              <p className="text-xs uppercase tracking-wider text-slate-400">Assets</p>
              <p className="mt-2 text-3xl font-semibold">{assets.length}</p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
              <p className="text-xs uppercase tracking-wider text-slate-400">Categories</p>
              <p className="mt-2 text-3xl font-semibold">{categories.length}</p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
              <p className="text-xs uppercase tracking-wider text-slate-400">Organizations</p>
              <p className="mt-2 text-3xl font-semibold">{organizations.length}</p>
            </div>
          </div>

          <GrcTable
            columns={columns}
            rows={assets}
            rowKey={(a) => a.id}
            emptyMessage="No assets registered yet."
          />

          {vulns.length > 0 ? (
            <div>
              <h3 className="mb-3 text-lg font-semibold">Registered Vulnerabilities</h3>
              <GrcTable
                columns={[
                  {
                    key: 'name',
                    header: 'Vulnerability',
                    render: (v) => <span className="font-medium">{v.name}</span>,
                  },
                  {
                    key: 'cve_id',
                    header: 'CVE',
                    render: (v) => v.cve_id ?? '—',
                  },
                  {
                    key: 'cvss_severity',
                    header: 'Severity',
                    render: (v) => v.cvss_severity ?? '—',
                  },
                  {
                    key: 'cvss_score',
                    header: 'CVSS',
                    render: (v) =>
                      typeof v.cvss_score === 'number' ? v.cvss_score.toFixed(1) : '—',
                  },
                  {
                    key: 'exploit_available',
                    header: 'Exploit',
                    render: (v) =>
                      v.exploit_available ? (
                        <Badge value="Available" tone="rose" />
                      ) : (
                        <Badge value="None" tone="green" />
                      ),
                  },
                ]}
                rows={vulns}
                rowKey={(v) => v.id}
              />
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}

