import type { CoreSettings } from '../types'
import { defaultCoreSettings } from '../constants'

export default function SettingsPanel({
  draftSettings,
  onUpdate,
}: {
  draftSettings: CoreSettings
  onUpdate: (updater: (prev: CoreSettings) => CoreSettings) => void
}) {
  const { risk_thresholds: t } = draftSettings

  return (
    <div>
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-5">
        {(
          [
            ['exposure_weight', 'Exposure weight', 0, 2],
            ['patch_weight', 'Patch weight', 0, 2],
            ['impact_weight', 'Impact weight', 0, 2],
          ] as Array<[keyof Omit<CoreSettings, 'propagation_weights' | 'firewall_multipliers' | 'cvss_mapping' | 'cvss_logistic_params' | 'risk_thresholds'>, string, number, number]>
        ).map(([key, label, min, max]) => (
          <label key={key} className="text-xs text-slate-300">
            <div className="flex items-center justify-between">
              <span>{label}</span>
              <span className="font-mono text-cyan-300">
                {draftSettings[key].toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min={min}
              max={max}
              step={0.01}
              value={draftSettings[key]}
              onChange={(event) =>
                onUpdate((current) => ({
                  ...current,
                  [key]: Number(event.target.value),
                }))
              }
              className="mt-2 w-full"
              aria-label={label}
            />
          </label>
        ))}
      </div>

      <div className="mt-6 border-t border-slate-800 pt-4">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          CVSS → probability mapping (modelling assumption)
        </h4>
        <p className="mt-1 max-w-3xl text-xs leading-relaxed text-slate-500">
          CVSS Base Score is a <em>severity</em> metric (0–10), not a
          probability. The framework converts it into an intrinsic compromise
          probability with P₀ = 1 / (1 + exp(−k·(CVSS − x₀))), where k is the
          logistic slope and x₀ the midpoint. These parameters are expert
          defaults (not empirically calibrated); an organisation should
          calibrate them against its own incident data. The legacy linear
          mapping (P = CVSS/10) is kept only for backward compatibility and is
          not recommended.
        </p>
        <div className="mt-3 grid gap-4 sm:grid-cols-3 lg:max-w-2xl">
          <label className="text-xs text-slate-300">
            <div className="flex items-center justify-between">
              <span>Mapping method</span>
              <span className="font-mono text-cyan-300">
                {draftSettings.cvss_mapping}
              </span>
            </div>
            <select
              value={draftSettings.cvss_mapping}
              onChange={(event) =>
                onUpdate((current) => ({
                  ...current,
                  cvss_mapping: event.target.value === 'linear' ? 'linear' : 'logistic',
                }))
              }
              className="field mt-2"
              aria-label="CVSS to probability mapping method"
            >
              <option value="logistic">logistic (recommended)</option>
              <option value="linear">linear (legacy, not recommended)</option>
            </select>
          </label>
          <label className="text-xs text-slate-300">
            <div className="flex items-center justify-between">
              <span>Logistic slope k</span>
              <span className="font-mono text-cyan-300">
                {draftSettings.cvss_logistic_params.k.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min={0.1}
              max={2}
              step={0.05}
              value={draftSettings.cvss_logistic_params.k}
              onChange={(event) =>
                onUpdate((current) => ({
                  ...current,
                  cvss_logistic_params: {
                    ...current.cvss_logistic_params,
                    k: Number(event.target.value),
                  },
                }))
              }
              className="mt-2 w-full"
              aria-label="Logistic slope k"
            />
          </label>
          <label className="text-xs text-slate-300">
            <div className="flex items-center justify-between">
              <span>Logistic midpoint x₀</span>
              <span className="font-mono text-cyan-300">
                {draftSettings.cvss_logistic_params.x0.toFixed(1)}
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={10}
              step={0.1}
              value={draftSettings.cvss_logistic_params.x0}
              onChange={(event) =>
                onUpdate((current) => ({
                  ...current,
                  cvss_logistic_params: {
                    ...current.cvss_logistic_params,
                    x0: Number(event.target.value),
                  },
                }))
              }
              className="mt-2 w-full"
              aria-label="Logistic midpoint x0"
            />
          </label>
        </div>
      </div>

      <div className="mt-6 border-t border-slate-800 pt-4">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Risk thresholds (single source of truth)
        </h4>
        <p className="mt-1 max-w-3xl text-xs leading-relaxed text-slate-500">
          The same thresholds drive the backend classification, the PDF report
          colours and this dashboard — they are not hardcoded anywhere else.
          Sliders keep the required ordering critical &gt; high &gt; moderate;
          the backend rejects any configuration that violates it.
        </p>
        <div className="mt-3 grid gap-4 sm:grid-cols-3 lg:max-w-2xl">
          <label className="text-xs text-slate-300">
            <div className="flex items-center justify-between">
              <span>Critical ≥</span>
              <span className="font-mono text-rose-300">
                {t.critical.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min={t.high}
              max={1.4}
              step={0.01}
              value={t.critical}
              onChange={(event) =>
                onUpdate((current) => ({
                  ...current,
                  risk_thresholds: {
                    ...current.risk_thresholds,
                    critical: Number(event.target.value),
                  },
                }))
              }
              className="mt-2 w-full"
              aria-label="Critical risk threshold"
            />
          </label>
          <label className="text-xs text-slate-300">
            <div className="flex items-center justify-between">
              <span>High ≥</span>
              <span className="font-mono text-amber-300">
                {t.high.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min={t.moderate}
              max={t.critical}
              step={0.01}
              value={t.high}
              onChange={(event) =>
                onUpdate((current) => ({
                  ...current,
                  risk_thresholds: {
                    ...current.risk_thresholds,
                    high: Number(event.target.value),
                  },
                }))
              }
              className="mt-2 w-full"
              aria-label="High risk threshold"
            />
          </label>
          <label className="text-xs text-slate-300">
            <div className="flex items-center justify-between">
              <span>Moderate ≥</span>
              <span className="font-mono text-cyan-300">
                {t.moderate.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={t.high}
              step={0.01}
              value={t.moderate}
              onChange={(event) =>
                onUpdate((current) => ({
                  ...current,
                  risk_thresholds: {
                    ...current.risk_thresholds,
                    moderate: Number(event.target.value),
                  },
                }))
              }
              className="mt-2 w-full"
              aria-label="Moderate risk threshold"
            />
          </label>
        </div>
      </div>

      <div className="mt-6 border-t border-slate-800 pt-4">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Noisy-OR causal weight by relationship type
        </h4>
        <p className="mt-1 max-w-3xl text-xs leading-relaxed text-slate-500">
          Each directed edge carries a causal weight w (not a conditional
          probability). For a single active parent, P(target = 1 | parent = 1)
          = 1 − (1 − leak)·(1 − w), where leak is the target's intrinsic
          probability. Weights are expert-configurable parameters.
        </p>
        <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {Object.entries(draftSettings.propagation_weights).map(
            ([relType, value]) => (
              <label key={relType} className="text-xs text-slate-300">
                <div className="flex items-center justify-between">
                  <span className="truncate" title={relType}>
                    {relType}
                  </span>
                  <span className="font-mono text-cyan-300">
                    {value.toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.01}
                  value={value}
                  onChange={(event) =>
                    onUpdate((current) => ({
                      ...current,
                      propagation_weights: {
                        ...current.propagation_weights,
                        [relType]: Number(event.target.value),
                      },
                    }))
                  }
                  className="mt-2 w-full"
                  aria-label={`Causal weight for ${relType}`}
                />
              </label>
            ),
          )}
        </div>
      </div>

      <div className="mt-6 border-t border-slate-800 pt-4">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Firewall multiplier
        </h4>
        <p className="mt-1 text-xs leading-relaxed text-slate-500">
          A firewall can only reduce propagated risk, never increase it — the
          "firewalled" slider is capped at the "not firewalled" value.
        </p>
        <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:w-1/2">
          {(['true', 'false'] as const).map((flag) => {
            const min =
              flag === 'false'
                ? draftSettings.firewall_multipliers.true
                : 0
            const max =
              flag === 'true'
                ? draftSettings.firewall_multipliers.false
                : 1.5
            return (
              <label key={flag} className="text-xs text-slate-300">
                <div className="flex items-center justify-between">
                  <span>
                    Link is {flag === 'true' ? 'firewalled' : 'not firewalled'}
                  </span>
                  <span className="font-mono text-cyan-300">
                    {draftSettings.firewall_multipliers[flag].toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min={min}
                  max={max}
                  step={0.01}
                  value={draftSettings.firewall_multipliers[flag]}
                  onChange={(event) =>
                    onUpdate((current) => ({
                      ...current,
                      firewall_multipliers: {
                        ...current.firewall_multipliers,
                        [flag]: Number(event.target.value),
                      },
                    }))
                  }
                  className="mt-2 w-full"
                  aria-label={`Firewall multiplier when ${flag}`}
                />
              </label>
            )
          })}
        </div>
      </div>

      <details className="details-card mt-6">
        <summary className="details-summary">
          Default values (framework defaults)
        </summary>
        <pre className="overflow-x-auto border-t border-slate-800 p-3 text-xs leading-relaxed text-slate-300">
          {JSON.stringify(defaultCoreSettings, null, 2)}
        </pre>
      </details>
    </div>
  )
}
