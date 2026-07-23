import { API_BASE_URL } from '../constants'

export default function ReportsSection() {
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <h2 className="text-xl font-semibold">Reports</h2>
      <p className="mt-1 text-sm text-slate-400">
        Download the two decision-ready outputs from the latest assessment: a
        sortable risk register and an executive assessment report.
      </p>
      <div className="mt-4 flex flex-wrap gap-3">
        {([
          ['risk_table.csv', 'Download risk register (CSV)'],
          ['assessment.pdf', 'Download assessment report (PDF)'],
        ] as const).map(([file, label]) => (
          <a
            key={file}
            className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-cyan-500/50 hover:text-cyan-200"
            href={`${API_BASE_URL}/reports/${file}`}
            download
          >
            {label}
          </a>
        ))}
      </div>
    </section>
  )
}

