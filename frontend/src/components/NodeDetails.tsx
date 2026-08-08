import { formatProbability } from '../utils'

export default function NodeDetails({
  selectedNode,
  nodeKindMap,
  combinedProbabilities,
  isEvidenceNode,
  result,
  riskRanking,
  attackPathNodes,
}: {
  selectedNode: string | null
  nodeKindMap: Map<string, string>
  combinedProbabilities: Map<string, number>
  isEvidenceNode: (id: string) => boolean
  result: {
    base_probabilities?: Record<string, number>
    evidence_used?: Record<string, number>
    assets?: Record<string, Record<string, unknown>>
    risk_scores?: Array<Record<string, unknown>>
  } | null
  riskRanking: Array<{
    asset: string
    risk: number
    probability: number
    severity: number
    impact: number
  }>
  attackPathNodes: Set<string>
}) {
  const assetAttrs = result?.assets?.[selectedNode ?? '']
  const cvss = Number(assetAttrs?.cvss_type ?? 0)
  const vulnerabilities = Array.isArray(assetAttrs?.vulnerabilities)
    ? (assetAttrs?.vulnerabilities as Array<Record<string, unknown>>)
    : []
  const riskRow = (result?.risk_scores ?? []).find(
    (row) => row.asset === selectedNode,
  )
  const impact = Number(riskRow?.impact ?? 0)
  const riskIndex = Number(riskRow?.risk ?? 0)
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <h2 className="text-xl font-semibold">Node Details</h2>
      {selectedNode ? (
        <div className="mt-4 space-y-3 rounded-xl bg-slate-950/80 p-4 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Asset</span>
            <span className="font-semibold text-white">{selectedNode}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Kind</span>
            <span className="font-semibold text-white">
              {nodeKindMap.get(selectedNode) ?? '—'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">CVSS (effective)</span>
            <span className="font-semibold text-orange-200">
              {cvss > 0
                ? `${cvss.toFixed(1)}${vulnerabilities.length ? ` · ${vulnerabilities.length} vuln.` : ''}`
                : '—'}
            </span>
          </div>
          <p className="-mt-2 text-xs text-slate-400">
            Effective CVSS v3.1 base score = maximum over the asset's
            vulnerabilities (severity, not probability).
          </p>
          {vulnerabilities.length > 0 ? (
            <div className="-mt-1 space-y-1 rounded-lg bg-slate-900/60 p-2 text-xs">
              {vulnerabilities.map((vuln, index) => (
                <div
                  key={String(vuln.cve_id ?? vuln.vector ?? index)}
                  className="flex justify-between text-slate-300"
                >
                  <span>{String(vuln.cve_id ?? vuln.vector ?? 'Vulnerability')}</span>
                  <span className="font-mono text-cyan-200">
                    {Number(vuln.score ?? 0).toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          ) : null}
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Intrinsic probability</span>
            <span className="font-semibold text-violet-200">
              {result?.base_probabilities?.[selectedNode] === undefined
                ? '—'
                : formatProbability(result.base_probabilities[selectedNode])}
            </span>
          </div>
          <p className="-mt-2 text-xs text-slate-400">
            Starting compromise probability derived from this asset's own
            attributes before network propagation or selected evidence.
          </p>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Posterior</span>
            <span className="font-semibold text-cyan-300">
              {combinedProbabilities.has(selectedNode)
                ? formatProbability(combinedProbabilities.get(selectedNode)!)
                : '—'}
              {isEvidenceNode(selectedNode) ? ' (pinned by evidence)' : ''}
            </span>
          </div>
          <p className="-mt-2 text-xs text-slate-400">
            Probability that this asset is compromised after applying evidence
            and network dependencies. A pinned value comes directly from
            selected evidence.
          </p>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Consequence impact</span>
            <span className="font-semibold text-amber-200">
              {impact > 0 ? formatProbability(impact) : '—'}
            </span>
          </div>
          <p className="-mt-2 text-xs text-slate-400">
            Normalised impact = severity/10 × scope multiplier (0–1.4).
          </p>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Risk index</span>
            <span className="font-semibold text-rose-300">
              {riskIndex > 0 ? formatProbability(riskIndex) : '—'}
            </span>
          </div>
          <p className="-mt-2 text-xs text-slate-400">
            Risk index = posterior probability × impact. It is a ranking
            metric, not a probability.
          </p>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Risk rank</span>
            <span className="font-semibold text-white">
              {riskRanking.findIndex((entry) => entry.asset === selectedNode) +
                1 || '—'}
            </span>
          </div>
          <p className="-mt-2 text-xs text-slate-400">
            Position in the risk register (top 5 shown here).
          </p>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">On top attack path</span>
            <span
              className={`font-semibold ${
                attackPathNodes.has(selectedNode)
                  ? 'text-rose-300'
                  : 'text-slate-400'
              }`}
            >
              {attackPathNodes.has(selectedNode) ? 'Yes' : 'No'}
            </span>
          </div>
          <p className="-mt-2 text-xs text-slate-400">
            "Yes" means that this asset lies on the calculated path with the
            highest combined propagation-and-target-risk score for this run.
          </p>
        </div>
      ) : (
        <p className="mt-4 text-sm text-slate-400">
          Select a node in the network to inspect its probability details.
        </p>
      )}
    </div>
  )
}

