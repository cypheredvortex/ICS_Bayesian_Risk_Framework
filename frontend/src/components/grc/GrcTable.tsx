import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { EmptyState, Spinner } from './ui'

export type Column<T> = {
  key: string
  header: string
  render?: (row: T) => ReactNode
  className?: string
  sortable?: boolean
  width?: string
}

export type SortState = { key: string; dir: 'asc' | 'desc' } | null

function valueOf<T>(row: T, key: string): string | number {
  const v = (row as Record<string, unknown>)[key]
  if (v === null || v === undefined) return ''
  if (typeof v === 'number') return v
  return String(v)
}

function isSortableValue(v: unknown): v is string | number {
  return typeof v === 'string' || typeof v === 'number'
}

function sortRows<T>(rows: T[], columns: Column<T>[], sort: SortState): T[] {
  if (!sort) return rows
  const col = columns.find((c) => c.key === sort.key)
  if (!col) return rows
  const dir = sort.dir === 'asc' ? 1 : -1
  return [...rows].sort((a, b) => {
    const va = isSortableValue(a[col.key as keyof T]) ? (a[col.key as keyof T] as string | number) : ''
    const vb = isSortableValue(b[col.key as keyof T]) ? (b[col.key as keyof T] as string | number) : ''
    if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * dir
    return String(va).localeCompare(String(vb)) * dir
  })
}

export default function GrcTable<T>({
  columns,
  rows,
  emptyMessage = 'No records found.',
  rowKey,
  onRowClick,
  actions,
  searchable = false,
  searchPlaceholder = 'Search…',
  searchKeys,
  pageSize = 10,
  loading = false,
  dense = false,
  emptyAction,
}: {
  columns: Column<T>[]
  rows: T[]
  emptyMessage?: string
  rowKey: (row: T) => string | number
  onRowClick?: (row: T) => void
  actions?: (row: T) => ReactNode
  searchable?: boolean
  searchPlaceholder?: string
  searchKeys?: (keyof T)[]
  pageSize?: number
  loading?: boolean
  dense?: boolean
  emptyAction?: ReactNode
}) {
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<SortState>(null)
  const [page, setPage] = useState(1)

  useEffect(() => {
    setPage(1)
  }, [query, sort])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return rows
    const keys = searchKeys ?? (columns.map((c) => c.key as keyof T) as (keyof T)[])
    return rows.filter((row) =>
      keys.some((key) => String(valueOf(row, String(key))).toLowerCase().includes(q)),
    )
  }, [rows, query, searchKeys, columns])

  const sorted = useMemo(() => sortRows(filtered, columns, sort), [filtered, columns, sort])

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize))
  const safePage = Math.min(page, totalPages)
  const pageRows = sorted.slice((safePage - 1) * pageSize, safePage * pageSize)

  const toggleSort = (col: Column<T>) => {
    if (!col.sortable) return
    setSort((current) => {
      if (!current || current.key !== col.key) return { key: col.key, dir: 'asc' }
      if (current.dir === 'asc') return { key: col.key, dir: 'desc' }
      return null
    })
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/70">
      {(searchable || actions) && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 px-4 py-3">
          {searchable ? (
            <div className="relative min-w-[220px] flex-1 sm:max-w-xs">
              <svg
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M21 21l-4.35-4.35M17 10a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={searchPlaceholder}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/80 py-2 pl-9 pr-3 text-sm text-slate-100 placeholder-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
              />
            </div>
          ) : (
            <div />
          )}
          <div className="flex items-center gap-2">
            {actions ? (
              <span className="text-xs text-slate-500">
                {sorted.length} {sorted.length === 1 ? 'record' : 'records'}
              </span>
            ) : null}
          </div>
        </div>
      )}

      {loading ? (
        <Spinner />
      ) : !sorted.length ? (
        <div className="p-4">
          <EmptyState message={emptyMessage} action={emptyAction} />
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900 text-xs uppercase tracking-wider text-slate-400">
                {columns.map((col) => {
                  const isSorted = sort?.key === col.key
                  return (
                    <th
                      key={col.key}
                      style={col.width ? { width: col.width } : undefined}
                      className={`px-4 py-3 font-medium ${
                        col.sortable ? 'cursor-pointer select-none hover:text-slate-200' : ''
                      } ${col.className ?? ''}`}
                      onClick={() => toggleSort(col)}
                    >
                      <span className="inline-flex items-center gap-1">
                        {col.header}
                        {isSorted ? (
                          <span className="text-cyan-400">
                            {sort?.dir === 'asc' ? '↑' : '↓'}
                          </span>
                        ) : null}
                      </span>
                    </th>
                  )
                })}
                {actions ? <th className="px-4 py-3 text-right font-medium">Actions</th> : null}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {pageRows.map((row) => {
                const key = rowKey(row)
                return (
                  <tr
                    key={key}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    className={`transition-colors ${
                      onRowClick ? 'cursor-pointer hover:bg-slate-800/40' : 'hover:bg-slate-800/20'
                    }`}
                  >
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        className={`px-4 ${dense ? 'py-2' : 'py-3'} ${col.className ?? ''}`}
                      >
                        {col.render
                          ? col.render(row)
                          : String((row as Record<string, unknown>)[col.key] ?? '—')}
                      </td>
                    ))}
                    {actions ? (
                      <td className={`px-4 ${dense ? 'py-2' : 'py-3'} text-right`}>
                        {actions(row)}
                      </td>
                    ) : null}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-slate-800 px-4 py-3">
          <p className="text-xs text-slate-500">
            Page {safePage} of {totalPages}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={safePage <= 1}
              className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 transition-colors hover:border-cyan-500/50 hover:text-cyan-200 disabled:cursor-not-allowed disabled:opacity-40"
            >
              ← Prev
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={safePage >= totalPages}
              className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 transition-colors hover:border-cyan-500/50 hover:text-cyan-200 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

