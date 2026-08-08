import type { CoreSettings, TopologyPayload, AssetState } from './types'

export const API_BASE_URL = '/api'

export const defaultTopology: TopologyPayload = {
  assets: {},
  relationships: [],
}

export const assetStateOrder: AssetState[] = ['Unknown', 'Compromised', 'Safe']

// Fallback values used only until the backend /settings payload arrives
// (and if the backend is unreachable). They mirror
// backend/settings.py::DEFAULT_SETTINGS exactly; once the API responds,
// mergeSettingsFromApi() in App.tsx replaces them with the server values,
// so the backend remains the single source of truth.
export const defaultCoreSettings: CoreSettings = {
  exposure_weight: 1.0,
  patch_weight: 1.0,
  impact_weight: 1.0,
  // CVSS → probability mapping is an explicit, configurable modelling
  // assumption. k = logistic slope, x0 = logistic midpoint.
  cvss_mapping: 'logistic',
  cvss_logistic_params: { k: 0.8, x0: 5.0 },
  propagation_weights: {
    controls: 0.7,
    monitors: 0.2,
    actuates: 0.6,
    'connects-to': 0.5,
    'programs / operates': 0.8,
  },
  firewall_multipliers: { true: 0.3, false: 1.0 },
  risk_thresholds: { critical: 0.75, high: 0.5, moderate: 0.25 },
}

export const kindColors: Record<string, string> = {
  human: '#a78bfa',
  device: '#38bdf8',
  physical: '#f59e0b',
}

export const datasets = [
  { value: 'swat_example', label: 'SWAT Example' },
  { value: 'building_automation', label: 'Building Automation' },
  { value: 'power_substation', label: 'Power Substation' },
  { value: 'water_treatment', label: 'Water Treatment' },
]

