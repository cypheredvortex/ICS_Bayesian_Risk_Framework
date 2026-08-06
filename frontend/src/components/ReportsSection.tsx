import { API_BASE_URL } from '../constants'

export default function ReportsSection({ available = false }: { available?: boolean }) {
  const reportLinks = [
    ['risk_table.csv', 'Download risk register (CSV)'],
    ['assessment.pdf', 'Download assessment report (PDF)'],
  ] as const

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <h2 className="text-xl font-semibold">Reports</h2>
      <p className="mt-1 text-sm text-slate-400">
        Download the two decision-ready outputs from the latest assessment: a
        sortable risk register and an executive assessment report.
      </p>
      <div className="mt-4 flex flex-wrap gap-3">
        {reportLinks.map(([file, label]) =>
          available ? (
            <a
              key={file}
              className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-cyan-500/50 hover:text-cyan-200"
              href={`${API_BASE_URL}/reports/${file}`}
              download
            >
              {label}
            </a>
          ) : (
            <button
              key={file}
              type="button"
              disabled
              className="rounded-lg border border-slate-700 bg-slate-800/90 px-4 py-2 text-sm font-semibold text-slate-500 cursor-not-allowed"
            >
              {label}
            </button>
          ),
        )}
      </div>
      {!available ? (
        <p className="mt-3 text-sm text-slate-500">
          Run an assessment first to enable report downloads.
        </p>
      ) : null}
    </section>
  )
}

