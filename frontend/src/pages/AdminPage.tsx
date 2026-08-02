import { useCallback, useEffect, useState } from 'react'
import GrcTable from '../components/grc/GrcTable'
import type { Column } from '../components/grc/GrcTable'
import PageHeader from '../components/grc/PageHeader'
import { Modal } from '../components/grc/Modal'
import { GrcForm, GrcFormActions, GrcFormSection } from '../components/grc/GrcForm'
import type { FormFieldConfig } from '../components/grc/GrcForm'
import { useCrud } from '../hooks/useCrud'
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

const ORG_FIELDS: FormFieldConfig[] = [
  { name: 'name', label: 'Organization Name', type: 'text', required: true },
  { name: 'legal_name', label: 'Legal Name', type: 'text' },
  { name: 'registration_number', label: 'Registration Number', type: 'text' },
  { name: 'tax_id', label: 'Tax ID', type: 'text' },
  { name: 'industry_sector', label: 'Industry Sector', type: 'text' },
  { name: 'address_line1', label: 'Address', type: 'text' },
  { name: 'city', label: 'City', type: 'text' },
  { name: 'state', label: 'State/Province', type: 'text' },
  { name: 'postal_code', label: 'Postal Code', type: 'text' },
  { name: 'country', label: 'Country', type: 'text' },
  { name: 'website', label: 'Website', type: 'text' },
  { name: 'phone', label: 'Phone', type: 'text' },
  { name: 'email', label: 'Email', type: 'text' },
]

const USER_FIELDS: FormFieldConfig[] = [
  { name: 'username', label: 'Username', type: 'text', required: true },
  { name: 'email', label: 'Email', type: 'text', required: true },
  { name: 'password', label: 'Password', type: 'text', required: true, hint: 'Minimum 8 characters' },
  { name: 'first_name', label: 'First Name', type: 'text' },
  { name: 'last_name', label: 'Last Name', type: 'text' },
  { name: 'job_title', label: 'Job Title', type: 'text' },
  { name: 'phone', label: 'Phone', type: 'text' },
  { name: 'role_id', label: 'Role ID', type: 'number' },
  { name: 'organization_id', label: 'Organization ID', type: 'number' },
]

const ROLE_FIELDS: FormFieldConfig[] = [
  { name: 'name', label: 'Role Name', type: 'text', required: true },
  { name: 'description', label: 'Description', type: 'textarea' },
  { name: 'is_system_role', label: 'System Role', type: 'checkbox' },
]

export default function AdminPage() {
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [logs, setLogs] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formValues, setFormValues] = useState<Record<string, unknown>>({})
  const [formMode, setFormMode] = useState<'org' | 'user' | 'role'>('org')
  const crud = useCrud<Organization | User | Role>()

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

  const handleCreateOrg = () => {
    setFormValues({})
    setFormMode('org')
    crud.openCreate()
  }

  const handleCreateUser = () => {
    setFormValues({})
    setFormMode('user')
    crud.openCreate()
  }

  const handleCreateRole = () => {
    setFormValues({ is_system_role: false })
    setFormMode('role')
    crud.openCreate()
  }

  const handleEditOrg = (item: Organization) => {
    setFormMode('org')
    setFormValues({ ...(item as unknown as Record<string, unknown>) })
    crud.openEdit(item)
  }

  const handleEditUser = (item: User) => {
    setFormMode('user')
    const { password, ...rest } = item as unknown as Record<string, unknown>
    setFormValues(rest)
    crud.openEdit(item)
  }

  const handleEditRole = (item: Role) => {
    setFormMode('role')
    setFormValues({ ...(item as unknown as Record<string, unknown>) })
    crud.openEdit(item)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    crud.setSubmitting(true)
    crud.setError('')
    try {
      if (formMode === 'org') {
        if (crud.mode === 'create') {
          await organizationApi.create(formValues as Partial<Organization>)
        } else if (crud.selected) {
          await organizationApi.update(crud.selected.id, formValues as Partial<Organization>)
        }
      } else if (formMode === 'user') {
        if (crud.mode === 'create') {
          await adminApi.createUser(formValues as Partial<User> & { password: string })
        } else if (crud.selected) {
          await adminApi.updateUser(crud.selected.id, formValues as Partial<User>)
        }
      } else {
        if (crud.mode === 'create') {
          await adminApi.createRole(formValues as Partial<Role>)
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
      if (formMode === 'org') {
        await organizationApi.remove(crud.selected.id)
      } else if (formMode === 'user') {
        await adminApi.updateUser(crud.selected.id, { is_active: false } as Partial<User>)
      }
      crud.close()
      await load()
    } catch (caught) {
      crud.setError(caught instanceof Error ? caught.message : 'Failed to delete.')
    } finally {
      crud.setSubmitting(false)
    }
  }

  const orgColumns: Column<Organization>[] = [
    {
      key: 'name',
      header: 'Organization',
      render: (o) => (
        <div className="flex items-center gap-2">
          <span className="font-medium">{o.name}</span>
          <button
            onClick={() => handleEditOrg(o)}
            className="text-xs text-cyan-400 hover:text-cyan-200 hover:underline"
          >
            Edit
          </button>
        </div>
      ),
    },
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
      render: (u) => (
        <div className="flex items-center gap-2">
          <span className="font-medium">{u.username}</span>
          <button
            onClick={() => handleEditUser(u)}
            className="text-xs text-cyan-400 hover:text-cyan-200 hover:underline"
          >
            Edit
          </button>
        </div>
      ),
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
          <div className="flex items-center gap-2">
            <button
              onClick={handleCreateOrg}
              className="rounded-full bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500"
            >
              + Organization
            </button>
            <button
              onClick={handleCreateUser}
              className="rounded-full bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500"
            >
              + User
            </button>
            <button
              onClick={handleCreateRole}
              className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-500/50 hover:text-cyan-200"
            >
              + Role
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

      {/* Create/Edit Modal */}
      <Modal
        open={crud.open}
        onClose={crud.close}
        title={
          formMode === 'org'
            ? `${crud.mode === 'create' ? 'Create' : 'Edit'} Organization`
            : formMode === 'user'
              ? `${crud.mode === 'create' ? 'Create' : 'Edit'} User`
              : `${crud.mode === 'create' ? 'Create' : 'Edit'} Role`
        }
      >
        <form onSubmit={handleSubmit}>
          <GrcFormSection
            title={
              formMode === 'org'
                ? 'Organization Details'
                : formMode === 'user'
                  ? 'User Details'
                  : 'Role Details'
            }
          >
            <GrcForm
              fields={
                formMode === 'org'
                  ? ORG_FIELDS
                  : formMode === 'user'
                    ? USER_FIELDS
                    : ROLE_FIELDS
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

