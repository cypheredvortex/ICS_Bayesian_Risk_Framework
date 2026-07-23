import type { CoreSettings, TopologyPayload, AssetState } from './types'

export const API_BASE_URL = '/api'

export const defaultTopology: TopologyPayload = {
  assets: {},
  relationships: [],
}

export const assetStateOrder: AssetState[] = ['Unknown', 'Compromised', 'Safe']

export const defaultCoreSettings: CoreSettings = {
  cvss_weight: 1.0,
  exposure_weight: 1.0,
  patch_weight: 1.0,
  impact_weight: 1.0,
  propagation_weights: {
    controls: 0.7,
    monitors: 0.2,
    actuates: 0.6,
    'connects-to': 0.5,
    'programs / operates': 0.8,
  },
  firewall_multipliers: { true: 0.3, false: 1.0 },
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

