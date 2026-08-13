import { API_BASE_URL } from '../constants'

type ReportSpec = {
  file: string
  name: string
  icon: string
  purpose: string
  contains: string
  when: string
}

const reports: ReportSpec[] = [
  {
    file: 'assessment.pdf',
    name: 'Assessment report (PDF)',
    icon: '📄',
    purpose:
      'Human-readable report for management, audit and documentation — the document you hand to a reviewer or mentor.',
    contains:
      'Executive summary with the overall risk, risk-level distribution and the highest-risk assets, the model parameters used, the complete risk register (all assets, ranked), selected evidence, attack-path analysis and methodology notes.',
    when: 'Use when you need a professional, presentable record of the assessment.',
  },
  {
    file: 'risk_table.csv',
    name: 'Risk register (CSV)',
    icon: '📊',
    purpose:
      'Tabular risk register for analysis, filtering, sorting and further processing in spreadsheets or scripts.',
    contains:
      'Every asset with its rank, posterior compromise probability, consequence severity, impact and risk index, classified with the active thresholds.',
    when: 'Use when you want to analyse, sort, filter or transform the asset-level results yourself.',
  },
  {
    file: 'assessment.json',
    name: 'Full results (JSON)',
    icon: '🧩',
    purpose:
      'Complete machine-readable record of the assessment run for archiving, reproducibility and interoperability with other tools.',
    contains:
      'The exact same result the dashboard shows: topology, graph, CPTs, base and posterior probabilities, risk scores, attack paths, evidence and the settings snapshot that produced the run.',
    when: 'Use when you need to archive a run, compare runs, or feed the results into another system.',
  },
]

export default function ReportsSection({ available = false }: { available?: boolean }) {
  return (
    <div>
      <p className="text-sm leading-relaxed text-slate-400">
        Each export is generated from the same authoritative assessment result,
        so every file always matches the dashboard.
        {!available
          ? ' Run an assessment first to enable downloads.'
          : ''}
      </p>
      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        {reports.map((report) => (
          <div
            key={report.file}
            className="flex flex-col rounded-xl border border-slate-800 bg-slate-950/60 p-4 transition-colors hover:border-slate-700"
          >
            <div className="flex items-center gap-2.5">
              <span className="text-lg" aria-hidden="true">
                {report.icon}
              </span>
              <h4 className="font-semibold text-slate-200">{report.name}</h4>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-slate-400">
              {report.purpose}
            </p>
            <p className="mt-2 text-xs leading-relaxed text-slate-500">
              <span className="font-semibold text-slate-400">Contains:</span>{' '}
              {report.contains}
            </p>
            <p className="mt-1 flex-1 text-xs leading-relaxed text-slate-500">
              <span className="font-semibold text-slate-400">When to use:</span>{' '}
              {report.when}
            </p>
            <div className="mt-4">
              {available ? (
                <a
                  className="btn btn-secondary btn-sm w-full"
                  href={`${API_BASE_URL}/reports/${report.file}`}
                  download
                >
                  Download {report.name.split('(')[0].trim()}
                </a>
              ) : (
                <button
                  type="button"
                  disabled
                  className="btn btn-secondary btn-sm w-full opacity-40"
                >
                  Download {report.name.split('(')[0].trim()}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
