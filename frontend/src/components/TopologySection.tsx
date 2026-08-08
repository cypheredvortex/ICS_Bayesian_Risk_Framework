import { useRef, useState } from 'react'
import { API_BASE_URL, topologyFormats } from '../constants'
import type { TopologyReviewInfo } from '../types'
import { formatBytes } from '../utils'
import { Badge, Spinner, StatusDot } from './ui'

const categoryTone: Record<string, 'emerald' | 'cyan' | 'violet' | 'amber'> = {
  Native: 'emerald',
  Inventory: 'cyan',
  Interchange: 'violet',
  Conversion: 'amber',
}

export default function TopologySection({
  uploadedFileName,
  review,
  parsing,
  apiOnline,
  loading,
  hasAssets,
  onFileUpload,
  onRemoveTopology,
  onRunAssessment,
  accept,
}: {
  uploadedFileName: string
  review: TopologyReviewInfo | null
  parsing: boolean
  apiOnline: boolean | null
  loading: boolean
  hasAssets: boolean
  onFileUpload: (event: React.ChangeEvent<HTMLInputElement>) => void
  onRemoveTopology: () => void
  onRunAssessment: () => void
  accept: string
}) {
  // The file input is intentionally rendered once, outside every conditional
  // branch, so the ref always points at a mounted element. That is what makes
  // "Replace file" work after an upload — and it lets the same file be chosen
  // again (handleFileUpload resets input.value after each change).
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragActive, setDragActive] = useState(false)

  const openFilePicker = () => inputRef.current?.click()

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setDragActive(false)
    const file = event.dataTransfer.files?.[0]
    if (!file || !inputRef.current) return
    const transfer = new DataTransfer()
    transfer.items.add(file)
    inputRef.current.files = transfer.files
    inputRef.current.dispatchEvent(new Event('change', { bubbles: true }))
  }

  const hasWarnings = Boolean(review?.warnings.length)
  const statusTone = !review
    ? null
    : hasWarnings
      ? ('warn' as const)
      : ('ok' as const)

  const coverage = review?.summary.field_coverage
  const zones = review?.summary.zones
  const assetCount = review?.assetCount ?? 0
  const relCount = review?.relationshipCount ?? 0

  return (
    <section className="card card-pad">
      {/* Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-500/10 text-cyan-300">
              <svg
                className="h-5 w-5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                <path d="M12 11v5M9.5 13.5h5" />
              </svg>
            </span>
            <div>
              <h2 className="card-title">Topology &amp; Assessment</h2>
              <p className="card-subtitle">
                Upload the ICS architecture to analyze. The framework converts
                it into assets, causal relationships and a Bayesian risk model.
              </p>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <a
            href={`${API_BASE_URL}/datasets/swat_example`}
            download
            className="btn btn-secondary btn-sm"
            title="Download a realistic SWAT water-treatment topology in the native JSON format to use as a reference"
          >
            <svg
              className="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
              <path d="M7 10l5 5 5-5" />
              <path d="M12 15V3" />
            </svg>
            Sample topology
          </a>
        </div>
      </div>

      {apiOnline === false ? (
        <div className="mt-4 flex items-start gap-3 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          <StatusDot tone="err" />
          <p>
            The backend API is currently unreachable. Topology uploads and
            assessments will fail until the service is available again.
          </p>
        </div>
      ) : null}

      {/* Upload / selected-file workspace */}
      <div className="mt-5">
        {parsing ? (
          <div className="flex min-h-[180px] flex-col items-center justify-center gap-3 rounded-2xl border border-cyan-500/30 bg-slate-950/60">
            <Spinner label="Parsing and validating topology…" />
            <p className="text-xs text-slate-500">
              Normalizing assets, relationships and zones against the
              framework schema.
            </p>
          </div>
        ) : review ? (
          <div className="overflow-hidden rounded-2xl border border-slate-700 bg-slate-950/60">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 px-4 py-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-semibold text-slate-100">
                  {review.fileName}
                </span>
                <Badge tone="cyan">{review.formatLabel}</Badge>
                {review.fileSize ? (
                  <Badge tone="slate">{formatBytes(review.fileSize)}</Badge>
                ) : null}
              </div>
              {statusTone ? (
                <span className="badge">
                  <StatusDot tone={statusTone} />
                  {statusTone === 'ok'
                    ? 'Valid'
                    : hasWarnings
                      ? 'Valid with warnings'
                      : 'Loaded'}
                </span>
              ) : null}
            </div>

            {/* Structural summary */}
            <div className="grid grid-cols-2 gap-px bg-slate-800 sm:grid-cols-4">
              {[
                ['Assets', assetCount, 'Detected asset records'],
                [
                  'Relationships',
                  relCount,
                  'Directed causal connections',
                ],
                [
                  'Zones',
                  Object.keys(zones ?? {}).length,
                  'Distinct trust zones',
                ],
                [
                  'Without zone',
                  review.summary.assets_without_zone,
                  'Assets not assigned to a zone',
                ],
              ].map(([label, value, hint]) => (
                <div key={String(label)} className="bg-slate-950/80 px-4 py-3">
                  <p className="section-label">{label}</p>
                  <p
                    className={`mt-1 font-mono text-xl font-semibold ${
                      label === 'Without zone' &&
                      Number(value) > 0 &&
                      Number(value) === assetCount
                        ? 'text-amber-300'
                        : 'text-slate-100'
                    }`}
                  >
                    {value}
                  </p>
                  <p className="mt-0.5 text-[11px] leading-snug text-slate-500">
                    {hint}
                  </p>
                </div>
              ))}
            </div>

            {/* Field coverage */}
            {coverage ? (
              <div className="border-t border-slate-800 px-4 py-3">
                <p className="section-label">Attribute coverage</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {[
                    ['CVSS', coverage.cvss_type, 'assets carry a CVSS severity or vulnerability list'],
                    ['Exposure', coverage.exposed, 'assets declare internet exposure'],
                    ['Patch state', coverage.patched, 'assets declare patching status'],
                    ['Impact', coverage.consequence_severity, 'assets declare consequence severity'],
                    ['Zone', coverage.zone, 'assets declare a zone'],
                    ['Vulnerabilities', coverage.vulnerabilities, 'assets carry CVE/vulnerability records'],
                  ].map(([label, count, hint]) => {
                    const n = Number(count)
                    return (
                      <span
                        key={String(label)}
                        className="badge"
                        title={String(hint)}
                      >
                        {n === assetCount ? '✓ ' : ''}
                        {label}: {n}/{assetCount}
                      </span>
                    )
                  })}
                </div>
              </div>
            ) : null}

            {/* Zones */}
            {zones && Object.keys(zones).length > 0 ? (
              <div className="border-t border-slate-800 px-4 py-3">
                <p className="section-label">Detected zones</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {Object.entries(zones).map(([zone, count]) => (
                    <Badge key={zone} tone="violet">
                      {zone} · {count}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : null}

            {/* Warnings */}
            {hasWarnings ? (
              <div className="border-t border-amber-500/20 bg-amber-500/5 px-4 py-3">
                <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-amber-300">
                  <StatusDot tone="warn" />
                  Normalization warnings
                </p>
                <ul className="mt-2 space-y-1.5">
                  {review.warnings.map((warning, index) => (
                    <li
                      key={index}
                      className="flex items-start gap-2 text-xs leading-relaxed text-amber-100/80"
                    >
                      <span aria-hidden="true">!</span>
                      <span>{warning}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {/* Replace / Remove */}
            <div className="flex flex-wrap items-center gap-2 border-t border-slate-800 bg-slate-950/40 px-4 py-3">
              <button
                onClick={openFilePicker}
                className="btn btn-secondary btn-sm"
              >
                <svg
                  className="h-4 w-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                  <path d="M7 10l5 5 5-5" />
                  <path d="M12 15V3" />
                </svg>
                Replace file
              </button>
              <button
                onClick={onRemoveTopology}
                className="btn btn-ghost btn-sm text-rose-300/90 hover:bg-rose-500/10 hover:text-rose-200"
              >
                Remove
              </button>
              <span className="ml-auto hidden text-[11px] text-slate-500 sm:inline">
                Replacing or removing clears the current assessment and
                evidence.
              </span>
            </div>
          </div>
        ) : (
          <div
            className={`dropzone ${dragActive ? 'dropzone-active' : ''}`}
            onDragOver={(event) => {
              event.preventDefault()
              setDragActive(true)
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            onClick={openFilePicker}
            role="button"
            tabIndex={0}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                openFilePicker()
              }
            }}
          >
            <span className="flex h-12 w-12 items-center justify-center rounded-full border border-slate-700 bg-slate-900 text-slate-300">
              <svg
                className="h-6 w-6"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                <path d="M17 8l-5-5-5 5" />
                <path d="M12 3v12" />
              </svg>
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-200">
                Drag &amp; drop a topology file, or click to browse
              </p>
              <p className="mt-1 text-xs text-slate-500">
                {accept.split(',').join(' · ')}
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="mt-4 flex flex-col gap-3 sm:flex-row">
        <button
          onClick={onRunAssessment}
          disabled={loading || parsing || !hasAssets}
          className="btn btn-primary flex-1 py-2.5"
          title="Shortcut: r"
        >
          {loading ? (
            <Spinner label="Running Bayesian assessment…" />
          ) : (
            <>
              <svg
                className="h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
              </svg>
              Run assessment
            </>
          )}
        </button>
        {!hasAssets ? (
          <p className="self-center text-xs text-slate-500">
            Load a topology before running the assessment.
          </p>
        ) : null}
      </div>

      {/* Active topology status bar */}
      <div
        className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-slate-800 bg-slate-950/80 px-4 py-3 text-sm text-slate-300"
        aria-live="polite"
      >
        {hasAssets ? (
          <span>
            Active topology:{' '}
            <strong className="font-semibold text-slate-100">
              {uploadedFileName}
            </strong>{' '}
            &middot; {assetCount || '—'} assets &middot; {relCount || '—'}{' '}
            connections
          </span>
        ) : (
          <span className="text-slate-400">
            No topology loaded yet. Upload a topology file to begin.
          </span>
        )}
      </div>

      {/* Supported topology representations — collapsed disclosure. The
          information is unchanged; it is tucked away so the card leads with
          the upload workflow instead of a wall of formats. */}
      <details className="details-card disclosure-no-marker mt-5">
        <summary className="details-summary">
          <span className="flex items-center gap-2.5">
            <svg
              className="details-chevron h-4 w-4 shrink-0 text-slate-400"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M9 18l6-6-6-6" />
            </svg>
            <span className="text-sm font-semibold text-slate-100">
              Supported topology representations
            </span>
          </span>
          <span className="hidden text-xs font-normal text-slate-500 sm:inline">
            {topologyFormats.length} formats — JSON, CSV/XLSX, GraphML,
            AutomationML, XML, Visio
          </span>
        </summary>
        <div className="details-panel border-t border-slate-800 px-4 py-3">
          <p className="text-xs leading-relaxed text-slate-500">
            The framework parses each format but does not treat them as
            equivalent. The category states what the file really is and what it
            needs to contain before analysis.
          </p>
          <ul className="mt-3 space-y-2.5">
            {topologyFormats.map((format) => (
              <li key={format.ext} className="text-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono font-semibold text-slate-200">
                    {format.ext}
                  </span>
                  <Badge tone={categoryTone[format.category]}>
                    {format.categoryLabel}
                  </Badge>
                  {format.recommended ? (
                    <Badge tone="emerald">Recommended</Badge>
                  ) : null}
                </div>
                <p className="mt-1 leading-relaxed text-slate-400">
                  {format.description}
                </p>
                {format.requires ? (
                  <p className="mt-0.5 text-slate-500">
                    <span className="font-semibold text-amber-300/90">
                      Requires:
                    </span>{' '}
                    {format.requires}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      </details>

      {/* Hidden file input — mounted once for both initial selection and
          replacement so no page refresh is ever needed. */}
      <input
        ref={inputRef}
        type="file"
        name="topology-file"
        accept={accept}
        onChange={onFileUpload}
        className="sr-only"
        aria-label="Upload a topology file"
      />
    </section>
  )
}
