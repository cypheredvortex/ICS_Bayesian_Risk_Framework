import { datasets } from '../constants'

export default function TopologySection({
  selectedDataset,
  uploadedFileName,
  assetCount,
  relationshipCount,
  loading,
  hasAssets,
  onDatasetChange,
  onFileUpload,
  onRunAssessment,
}: {
  selectedDataset: string
  uploadedFileName: string
  assetCount: number
  relationshipCount: number
  loading: boolean
  hasAssets: boolean
  onDatasetChange: (value: string) => void
  onFileUpload: (event: React.ChangeEvent<HTMLInputElement>) => void
  onRunAssessment: () => void
}) {
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl shadow-slate-950/30">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Topology &amp; Assessment</h2>
          <p className="mt-2 text-slate-300">
            Choose a preset or upload a topology, then run a full Bayesian
            cyber-risk assessment.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200">
            <span>Preset dataset</span>
            <select
              className="bg-slate-950 text-slate-100 outline-none"
              value={selectedDataset}
              onChange={(event) => onDatasetChange(event.target.value)}
              aria-label="Select a predefined dataset"
            >
              {datasets.map((ds) => (
                <option key={ds.value} value={ds.value}>
                  {ds.label}
                </option>
              ))}
            </select>
          </label>
          <label className="cursor-pointer rounded-lg border border-slate-600 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-cyan-500/50 hover:text-cyan-200">
            Upload topology
            <input
              type="file"
              accept=".json,.yaml,.yml,.csv,application/json,text/yaml,text/csv"
              onChange={onFileUpload}
              className="sr-only"
              aria-label="Upload a topology file"
            />
          </label>
          <button
            onClick={onRunAssessment}
            disabled={loading || !hasAssets}
            className="rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
            title="Shortcut: r"
          >
            {loading ? 'Running…' : 'Run assessment'}
          </button>
        </div>
      </div>
      <div
        className="mt-4 rounded-xl bg-slate-950/80 px-4 py-3 text-sm text-slate-300"
        aria-live="polite"
      >
        {hasAssets ? (
          <span>
            Active topology:{' '}
            <strong className="text-slate-100">
              {uploadedFileName || 'Preset dataset'}
            </strong>{' '}
            &middot; {assetCount} assets &middot; {relationshipCount}{' '}
            connections
          </span>
        ) : (
          <span className="text-slate-400">
            Select a preset or upload a .json, .yaml/.yml, or .csv topology file
            to begin.
          </span>
        )}
      </div>
    </section>
  )
}

