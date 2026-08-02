import { useCallback, useEffect, useState } from 'react'
import GrcTable from '../components/grc/GrcTable'
import type { Column } from '../components/grc/GrcTable'
import PageHeader from '../components/grc/PageHeader'
import { adminApi, organizationApi } from '../services/grc'
import type { AuditLogEntry, Organization, Role, User } from '../types/grc'

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

function activeTone(value?: boolean): 'green' | 'rose' | 'slate' {
  if (value === true) return 'green'
  if (value === false) return 'rose'
  return 'slate'
}

export default function AdminPage() {
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [logs, setLogs] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [orgList, roleList, userList, logData] = await Promise.all([
        organizationApi.list().catch(() => [] as Organization[]),
        adminApi.listRoles().catch(() => [] as Role[]),
        adminApi.listUsers().catch(() => [] as User[]),
        adminApi.listAuditLogs(50).catch(() => ({ total: 0, logs: [] as AuditLogEntry[] })),
      ])
      setOrganizations(orgList)
      setRoles(roleList)
      setUsers(userList)
      setLogs(logData.logs)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load administration data.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const orgColumns: Column<Organization>[] = [
    { key: 'name', header: 'Organization', render: (o) => <span className="font-medium">{o.name}</span> },
    { key: 'industry_sector', header: 'Industry', render: (o) => o.industry_sector ?? '—' },
    { key: 'country', header: 'Country', render: (o) => o.country ?? '—' },
    {
      key: 'is_active',
      header: 'Status',
      render: (o) =>
        o.is_active ? <Badge value="Active" tone="green" /> : <Badge value="Inactive" tone="rose" />,
    },
  ]

  const userColumns: Column<User>[] = [
    {
      key: 'username',
      header: 'User',
      render: (u) => <span className="font-medium">{u.username}</span>,
    },
    { key: 'email', header: 'Email', render: (u) => u.email },
    { key: 'job_title', header: 'Title', render: (u) => u.job_title ?? '—' },
    {
      key: 'is_active',
      header: 'Status',
      render: (u) =>
        u.is_active ? (
          <Badge value="Active" tone="green" />
        ) : (
          <Badge value={u.is_locked ? 'Locked' : 'Inactive'} tone="rose" />
        ),
    },
  ]

  const roleColumns: Column<Role>[] = [
    { key: 'name', header: 'Role', render: (r) => <span className="font-medium">{r.name}</span> },
    { key: 'description', header: 'Description', render: (r) => r.description ?? '—' },
    {
      key: 'is_system_role',
      header: 'System',
      render: (r) =>
        r.is_system_role ? <Badge value="System" tone="cyan" /> : <Badge value="Custom" tone="slate" />,
    },
  ]

  const logColumns: Column<AuditLogEntry>[] = [
    {
      key: 'created_at',
      header: 'Timestamp',
      render: (l) => l.created_at ?? '—',
    },
    {
      key: 'action',
      header: 'Action',
      render: (l) => <Badge value={l.action} tone="cyan" />,
    },
    { key: 'entity_type', header: 'Entity', render: (l) => l.entity_type },
    { key: 'entity_id', header: 'Entity ID', render: (l) => l.entity_id ?? '—' },
    {
      key: 'user_id',
      header: 'User',
      render: (l) => l.user_id ?? '—',
    },
  ]

  return (
    <div>
      <PageHeader
        title="Administration"
        description="Organizations, users, roles, and the audit trail."
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
          Loading administration data…
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-rose-200">
          {error}
        </div>
      ) : (
        <div className="space-y-8">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
              <p className="text-xs uppercase tracking-wider text-slate-400">Organizations</p>
              <p className="mt-2 text-3xl font-semibold">{organizations.length}</p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
              <p className="text-xs uppercase tracking-wider text-slate-400">Users</p>
              <p className="mt-2 text-3xl font-semibold">{users.length}</p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
              <p className="text-xs uppercase tracking-wider text-slate-400">Roles</p>
              <p className="mt-2 text-3xl font-semibold">{roles.length}</p>
            </div>
          </div>

          <section>
            <h3 className="mb-3 text-lg font-semibold">Organizations</h3>
            <GrcTable
              columns={orgColumns}
              rows={organizations}
              rowKey={(o) => o.id}
              emptyMessage="No organizations registered."
            />
          </section>

          <section>
            <h3 className="mb-3 text-lg font-semibold">Users</h3>
            <GrcTable
              columns={userColumns}
              rows={users}
              rowKey={(u) => u.id}
              emptyMessage="No users registered."
            />
          </section>

          <section>
            <h3 className="mb-3 text-lg font-semibold">Roles</h3>
            <GrcTable
              columns={roleColumns}
              rows={roles}
              rowKey={(r) => r.id}
              emptyMessage="No roles registered."
            />
          </section>

          <section>
            <h3 className="mb-3 text-lg font-semibold">
              Audit Trail <span className="text-sm font-normal text-slate-400">({logs.length})</span>
            </h3>
            <GrcTable
              columns={logColumns}
              rows={logs}
              rowKey={(l) => l.id}
              emptyMessage="No audit log entries."
            />
          </section>
        </div>
      )}
    </div>
  )
}

