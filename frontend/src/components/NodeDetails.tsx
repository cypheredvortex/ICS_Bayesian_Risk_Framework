import { useEffect, useState } from 'react'
import { assetDescription, formatProbability } from '../utils'
import { kindMeta, riskLevelMeta, purdueLevelMeta } from '../constants'
import { Badge, EmptyState, KvRow } from './ui'

export default function NodeDetails({
  selectedNode,
  nodeKindMap,
  combinedProbabilities,
  isEvidenceNode,
  result,
  riskRanking,
  attackPathNodes,
  edgeList,
  topologyAssets,
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
  edgeList: Array<{ source: string; target: string; label: string }>
  // The uploaded (normalized) topology assets — the authoritative source for
  // the asset's declared type/description before/without an assessment run.
  topologyAssets?: Record<string, Record<string, unknown>>
}) {
  // "What is this asset?" explanation: toggled from the asset name and reset
  // whenever the selection changes so stale text never lingers.
  const [showExplanation, setShowExplanation] = useState(false)
  useEffect(() => setShowExplanation(false), [selectedNode])

  // The result carries richer attributes once a run exists; the uploaded
  // topology is the fallback (and the only source before a run).
  const assetAttrs = {
    ...(topologyAssets?.[selectedNode ?? ''] ?? {}),
    ...(result?.assets?.[selectedNode ?? ''] ?? {}),
  }
  const cvss = Number(assetAttrs?.cvss_type ?? 0)
  const vulnerabilities = Array.isArray(assetAttrs?.vulnerabilities)
    ? (assetAttrs?.vulnerabilities as Array<Record<string, unknown>>)
    : []
  const riskRow = (result?.risk_scores ?? []).find(
    (row) => row.asset === selectedNode,
  )
  const impact = Number(riskRow?.impact ?? 0)
  const riskIndex = Number(riskRow?.risk ?? 0)
  const riskLevel = riskRow?.risk_level ? String(riskRow.risk_level) : null

  const incoming = selectedNode
    ? edgeList.filter((edge) => edge.target === selectedNode)
    : []
  const outgoing = selectedNode
    ? edgeList.filter((edge) => edge.source === selectedNode)
    : []

  // Plain-language explanation of what the asset is and does: the topology's
  // own `description` wins, then the asset-type dictionary, then a generic
  // kind-level fallback (see assetDescription in utils).
  const explanation =
    selectedNode && assetAttrs
      ? assetDescription(
          assetAttrs,
          String(assetAttrs.name ?? selectedNode),
          nodeKindMap.get(selectedNode) ?? 'device',
        )
      : null

  return (
    <div className="card card-pad rounded-2xl">
      <h2 className="card-title">Node Details</h2>
      {selectedNode ? (
        <div className="mt-4">
          {/* Identity */}
          <div className="rounded-xl border border-slate-800 bg-slate-950/70">
            <div className="border-b border-slate-800 px-4 py-2.5">
              <p className="section-label">Asset identity</p>
            </div>
            <div className="px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={() => setShowExplanation((value) => !value)}
                  disabled={!explanation}
                  className="group flex min-w-0 items-center gap-2 text-left"
                  aria-expanded={showExplanation}
                  title={
                    explanation
                      ? showExplanation
                        ? 'Hide what this asset is and does'
                        : 'Show what this asset is and does'
                      : undefined
                  }
                >
                  <span className="truncate font-mono text-base font-bold text-white transition group-hover:text-cyan-200">
                    {selectedNode}
                  </span>
                  {explanation ? (
                    <span
                      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition ${
                        showExplanation
                          ? 'border-cyan-400/60 bg-cyan-500/15 text-cyan-200'
                          : 'border-slate-700 bg-slate-900 text-slate-400 group-hover:border-cyan-400/40 group-hover:text-cyan-200'
                      }`}
                      aria-hidden="true"
                    >
                      <svg
                        className="h-3 w-3"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M12 8h.01M11 12h1v4h1" />
                        <circle cx="12" cy="12" r="10" />
                      </svg>
                    </span>
                  ) : null}
                </button>
                <Badge
                  tone={kindMeta[nodeKindMap.get(selectedNode) ?? 'device']?.badge ?? 'slate'}
                >
                  {kindMeta[nodeKindMap.get(selectedNode) ?? 'device']?.label ??
                    nodeKindMap.get(selectedNode) ??
                    '—'}
                </Badge>
              </div>

              {/* Expandable "what is this asset?" explanation. Lives inside
                  the identity block, defaults hidden, and never claims a
                  vendor/model the topology does not name.  Leads with the
                  asset's actual name (distinct from the ID) and its declared
                  type, then the plain-language explanation. */}
              {showExplanation && explanation ? (
                <div className="mt-2 rounded-lg border border-cyan-500/20 bg-cyan-500/[0.06] px-3 py-2">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-cyan-300/80">
                    What this asset is
                  </p>
                  {(() => {
                    const displayName = String(assetAttrs?.name ?? selectedNode)
                    // Only repeat the name when it differs from the clickable
                    // ID; otherwise the panel would show the ID twice.
                    return displayName === selectedNode ? null : (
                      <p className="mt-1.5 text-sm font-semibold text-white">
                        {displayName}
                      </p>
                    )
                  })()}
                  {assetAttrs?.type ? (
                    <p className="mt-0.5 text-[11px] font-medium uppercase tracking-wider text-cyan-300/80">
                      {String(assetAttrs.type)}
                    </p>
                  ) : null}
                  <p className="mt-1.5 text-xs leading-relaxed text-slate-300">
                    {explanation}
                  </p>
                </div>
              ) : null}
              {(assetAttrs?.zone || assetAttrs?.purdue_level) ? (
                <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                  {assetAttrs?.zone ? (
                    <span className="flex items-center gap-1.5">
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                        Zone
                      </span>
                      <Badge tone="violet">{String(assetAttrs.zone)}</Badge>
                    </span>
                  ) : null}
                  {assetAttrs?.purdue_level ? (
                    <span className="flex items-center gap-1.5">
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                        Purdue
                      </span>
                      <Badge tone="cyan">
                        L{String(assetAttrs.purdue_level)}
                      </Badge>
                    </span>
                  ) : null}
                  {assetAttrs?.purdue_level &&
                  purdueLevelMeta[String(assetAttrs.purdue_level)] ? (
                    <span className="text-[11px] text-slate-500">
                      {purdueLevelMeta[String(assetAttrs.purdue_level)].label}
                    </span>
                  ) : null}
                </div>
              ) : null}
              {(assetAttrs?.vendor || assetAttrs?.model || assetAttrs?.ip) ? (
                <p className="mt-2 font-mono text-[11px] text-slate-500">
                  {[assetAttrs?.vendor, assetAttrs?.model, assetAttrs?.ip]
                    .filter(Boolean)
                    .map(String)
                    .join(' · ')}
                </p>
              ) : null}
            </div>
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {/* Security context */}
            <div className="rounded-xl border border-slate-800 bg-slate-950/70 px-4 py-3">
              <p className="section-label">Security context</p>
              <div className="mt-2">
                <KvRow
                  label="CVSS (effective)"
                  value={
                    cvss > 0
                      ? `${cvss.toFixed(1)}${vulnerabilities.length ? ` · ${vulnerabilities.length} vuln.` : ''}`
                      : '—'
                  }
                  tone="amber"
                  hint="Effective CVSS v3.1 base score = maximum over the asset's vulnerabilities (severity, not probability)."
                />
                {assetAttrs?.exposed !== undefined ? (
                  <KvRow
                    label="Exposure"
                    value={assetAttrs.exposed ? 'Exposed' : 'Not exposed'}
                    tone={assetAttrs.exposed ? 'rose' : 'emerald'}
                  />
                ) : null}
                {assetAttrs?.patched !== undefined ? (
                  <KvRow
                    label="Patch state"
                    value={assetAttrs.patched ? 'Patched' : 'Unpatched'}
                    tone={assetAttrs.patched ? 'emerald' : 'amber'}
                  />
                ) : null}
                {vulnerabilities.length > 0 ? (
                  <div className="mt-1.5 space-y-1 rounded-lg bg-slate-900/70 p-2 text-xs">
                    {vulnerabilities.map((vuln, index) => (
                      <div
                        key={String(vuln.cve_id ?? vuln.vector ?? index)}
                        className="flex justify-between gap-2 text-slate-300"
                      >
                        <span className="truncate">
                          {String(vuln.cve_id ?? vuln.vector ?? 'Vulnerability')}
                        </span>
                        <span className="font-mono text-cyan-200">
                          {Number(vuln.score ?? 0).toFixed(1)}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>

            {/* Bayesian analysis */}
            <div className="rounded-xl border border-slate-800 bg-slate-950/70 px-4 py-3">
              <p className="section-label">Bayesian analysis</p>
              <div className="mt-2">
                <KvRow
                  label="Intrinsic probability"
                  value={
                    result?.base_probabilities?.[selectedNode] === undefined
                      ? '—'
                      : formatProbability(result.base_probabilities[selectedNode])
                  }
                  tone="violet"
                  hint="Starting compromise probability from this asset's own attributes before network propagation or evidence."
                />
                <KvRow
                  label="Posterior"
                  value={
                    combinedProbabilities.has(selectedNode)
                      ? formatProbability(combinedProbabilities.get(selectedNode)!)
                      : '—'
                  }
                  tone="cyan"
                  hint={
                    isEvidenceNode(selectedNode)
                      ? 'Pinned by evidence — value set directly from the selected evidence.'
                      : 'Probability of compromise after applying evidence and network dependencies.'
                  }
                />
              </div>
            </div>
          </div>

          {/* Risk */}
          <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/70 px-4 py-3">
            <p className="section-label">Risk</p>
            <div className="mt-2 grid gap-x-6 sm:grid-cols-2">
              <KvRow
                label="Consequence impact"
                value={impact > 0 ? formatProbability(impact) : '—'}
                tone="amber"
                hint="Normalised impact = severity/10 × scope multiplier (0–1.4)."
              />
              <KvRow
                label="Risk index"
                value={riskIndex > 0 ? formatProbability(riskIndex) : '—'}
                tone="rose"
                hint="Risk index = posterior probability × impact. It is a ranking metric, not a probability."
              />
              {riskLevel ? (
                <KvRow
                  label="Risk level"
                  value={
                    <Badge
                      tone={
                        riskLevelMeta[
                          riskLevel.toLowerCase() as keyof typeof riskLevelMeta
                        ]?.badge ?? 'slate'
                      }
                    >
                      {riskLevel}
                    </Badge>
                  }
                />
              ) : null}
              <KvRow
                label="Risk rank"
                value={
                  riskRanking.findIndex((entry) => entry.asset === selectedNode) +
                    1 || '—'
                }
                hint="Position in the complete risk register (1 = highest risk index)."
              />
              <KvRow
                label="On top attack path"
                value={
                  <span
                    className={
                      attackPathNodes.has(selectedNode)
                        ? 'text-rose-300'
                        : 'text-slate-400'
                    }
                  >
                    {attackPathNodes.has(selectedNode) ? 'Yes' : 'No'}
                  </span>
                }
                hint="Whether this asset lies on the calculated path with the highest combined propagation-and-target-risk score."
              />
            </div>
          </div>

          {/* Relationships */}
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-800 bg-slate-950/70 px-4 py-3">
              <p className="section-label">
                Incoming causal relationships ({incoming.length})
              </p>
              {incoming.length ? (
                <ul className="mt-2 space-y-1">
                  {incoming.slice(0, 6).map((edge, index) => (
                    <li
                      key={index}
                      className="flex items-center justify-between gap-2 text-xs text-slate-300"
                    >
                      <span className="truncate font-mono">{edge.source}</span>
                      <span className="shrink-0 text-slate-500">
                        → {edge.label.split(' ')[0]}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-xs text-slate-500">
                  No incoming relationships.
                </p>
              )}
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/70 px-4 py-3">
              <p className="section-label">
                Outgoing causal relationships ({outgoing.length})
              </p>
              {outgoing.length ? (
                <ul className="mt-2 space-y-1">
                  {outgoing.slice(0, 6).map((edge, index) => (
                    <li
                      key={index}
                      className="flex items-center justify-between gap-2 text-xs text-slate-300"
                    >
                      <span className="shrink-0 text-slate-500">
                        {edge.label.split(' ')[0]} →
                      </span>
                      <span className="truncate font-mono">{edge.target}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-xs text-slate-500">
                  No outgoing relationships.
                </p>
              )}
            </div>
          </div>
        </div>
      ) : (
        <EmptyState
          title="No asset selected"
          hint="Select a node in the network to inspect its probability, risk and relationship details."
        />
      )}
    </div>
  )
}
