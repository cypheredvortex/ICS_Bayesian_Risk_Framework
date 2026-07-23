import type { CoreSettings } from '../types'
import { defaultCoreSettings } from '../constants'

export default function SettingsPanel({
  draftSettings,
  settingsDirty,
  settingsLoading,
  onUpdate,
  onSave,
  onReset,
}: {
  draftSettings: CoreSettings
  settingsDirty: boolean
  settingsLoading: boolean
  onUpdate: (updater: (prev: CoreSettings) => CoreSettings) => void
  onSave: () => void
  onReset: () => void
}) {
  return (
    <div className="mx-auto mt-4 max-w-7xl rounded-xl border border-slate-800 bg-slate-950/80 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
            Analysis Weighting
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            Stored server-side via GET/PUT /settings and applied to every future
            run — not just this session.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onReset}
            disabled={settingsLoading}
            className="rounded-md border border-slate-600 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-50"
          >
            Reset to defaults
          </button>
          <button
            onClick={onSave}
            disabled={settingsLoading || !settingsDirty}
            className="rounded-md bg-cyan-500 px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {settingsLoading ? 'Saving…' : settingsDirty ? 'Save changes' : 'Saved'}
          </button>
        </div>
      </div>

      <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-5">
        {(
          [
            ['cvss_weight', 'CVSS weight', 0, 2],
            ['exposure_weight', 'Exposure weight', 0, 2],
            ['patch_weight', 'Patch weight', 0, 2],
            ['impact_weight', 'Impact weight', 0, 2],
          ] as Array<[keyof Omit<CoreSettings, 'propagation_weights' | 'firewall_multipliers'>, string, number, number]>
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
              className="mt-2 w-full accent-cyan-500"
              aria-label={label}
            />
          </label>
        ))}
      </div>

      <div className="mt-6 border-t border-slate-800 pt-4">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Propagation weight by relationship type
        </h4>
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
                  className="mt-2 w-full accent-cyan-500"
                  aria-label={`Propagation weight for ${relType}`}
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
        <p className="mt-1 text-xs text-slate-500">
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
                  className="mt-2 w-full accent-cyan-500"
                  aria-label={`Firewall multiplier when ${flag}`}
                />
              </label>
            )
          })}
        </div>
      </div>
    </div>
  )
}

