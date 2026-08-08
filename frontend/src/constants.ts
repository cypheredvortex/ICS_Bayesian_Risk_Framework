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

// File extensions accepted by the file picker (must match backend/importers.py).
export const TOPOLOGY_ACCEPT =
  '.json,.yaml,.yml,.csv,.xlsx,.graphml,.xml,.aml,.vsdx,.vdx'

export const TOPOLOGY_ACCEPT_RE =
  /\.(json|ya?ml|csv|xlsx|graphml|xml|aml|vsdx|vdx)$/i

// Honest classification of every supported topology representation, based on
// the actual parsers in backend/importers.py. "Supported by the framework"
// and "commonly produced by ICS tools" are deliberately kept distinct: the
// UI tells the analyst what each file really is and what it needs to contain.
export type TopologyFormat = {
  ext: string
  label: string
  category: 'Native' | 'Inventory' | 'Interchange' | 'Conversion'
  categoryLabel: string
  recommended?: boolean
  description: string
  bestFor: string
  requires?: string
}

export const topologyFormats: TopologyFormat[] = [
  {
    ext: '.json / .yaml',
    label: 'JSON / YAML',
    category: 'Native',
    categoryLabel: 'Native analysis format',
    recommended: true,
    description:
      'Canonical structured representation: an assets map and a relationships list, expressed directly in the framework\u2019s normalized schema.',
    bestFor: 'Machine-readable architecture exchange, reproducible assessments, version control.',
  },
  {
    ext: '.csv / .xlsx',
    label: 'CSV / Excel',
    category: 'Inventory',
    categoryLabel: 'Inventory / tabular format',
    recommended: true,
    description:
      'Tabular asset inventory and connection tables. Header-driven columns (id, name, kind, zone, cvss, exposed, patched, consequence_severity, source, target, type, firewalled, \u2026); multiple tables can be separated by blank rows or sheets.',
    bestFor: 'Asset inventories and network connection matrices already maintained in spreadsheets \u2014 the most common way ICS teams keep this data.',
  },
  {
    ext: '.graphml',
    label: 'GraphML',
    category: 'Interchange',
    categoryLabel: 'Graph interchange format',
    description:
      'XML graph format used by yEd, Gephi and networkx. Nodes become assets, edges become relationships; node/edge attributes (kind, zone, cvss, firewalled, protocol, trust, mitre) are promoted.',
    bestFor: 'Importing a network graph modelled in standard graph tooling.',
  },
  {
    ext: '.aml',
    label: 'AutomationML',
    category: 'Interchange',
    categoryLabel: 'Industrial engineering exchange (IEC 62714)',
    description:
      'AutomationML \u2014 the IEC 62714 plant-engineering exchange format used with tools such as TIA Portal. InternalElements become assets; Connections/InternalLinks become relationships.',
    bestFor: 'Bringing an automation project\u2019s plant structure into the risk model.',
    requires:
      'Coverage is partial: only names, manufacturer, device type, connections and protocols are read; most engineering detail is ignored.',
  },
  {
    ext: '.xml',
    label: 'Generic XML',
    category: 'Conversion',
    categoryLabel: 'Technical interchange fallback',
    description:
      'Generic XML documents containing asset/relationship containers (assets, nodes, devices, components, items \u2026 and relationships, edges, links, connections). No standardized schema is assumed.',
    bestFor: 'Converting an ad-hoc XML export from an internal tool into a topology.',
  },
  {
    ext: '.vsdx / .vdx',
    label: 'Visio diagrams',
    category: 'Conversion',
    categoryLabel: 'Visualization / conversion format',
    description:
      'Microsoft Visio diagram files. Shapes must be annotated with asset\u2026 / relationship\u2026 text markers or carry custom properties (ID, Name, Kind, Vendor, Model) \u2014 a plain, un-annotated diagram has no machine-readable structure.',
    bestFor: 'Reusing an existing Visio architecture drawing that has been annotated per the documented convention.',
    requires:
      'Legacy binary .vsd is not supported \u2014 convert to .vsdx (Visio / LibreOffice) or export to GraphML/JSON/CSV first.',
  },
]

export const riskLevelMeta: Record<
  'critical' | 'high' | 'moderate' | 'low',
  { label: string; badge: 'rose' | 'amber' | 'cyan' | 'emerald'; hex: string }
> = {
  critical: { label: 'Critical', badge: 'rose', hex: '#fb7185' },
  high: { label: 'High', badge: 'amber', hex: '#f59e0b' },
  moderate: { label: 'Moderate', badge: 'cyan', hex: '#38bdf8' },
  low: { label: 'Low', badge: 'emerald', hex: '#34d399' },
}

export const kindMeta: Record<
  string,
  { label: string; badge: 'violet' | 'cyan' | 'amber' | 'slate'; hex: string }
> = {
  human: { label: 'Human', badge: 'violet', hex: '#a78bfa' },
  device: { label: 'Device', badge: 'cyan', hex: '#38bdf8' },
  physical: { label: 'Physical process', badge: 'amber', hex: '#f59e0b' },
}


