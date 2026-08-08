import { API_BASE_URL } from '../constants'

export default function ReportsSection({ available = false }: { available?: boolean }) {
  const reportLinks = [
    ['risk_table.csv', 'Download risk register (CSV)'],
    ['assessment.pdf', 'Download assessment report (PDF)'],
  ] as const

  return (
    <section className="card card-pad">
      <h2 className="card-title">Reports</h2>
      <p className="card-subtitle">
        Download the two decision-ready outputs from the latest assessment: a
        sortable risk register and an executive assessment report.
      </p>
      <div className="mt-4 flex flex-wrap gap-3">
        {reportLinks.map(([file, label]) =>
          available ? (
            <a
              key={file}
              className="btn btn-secondary"
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
              className="btn btn-secondary opacity-40"
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
