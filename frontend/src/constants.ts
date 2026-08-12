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

// Relationship-type colours mirror the PNG diagram generator's semantic
// palette (tools/generate_ics_diagrams.py REL_COLORS) so the network viewer
// and the rendered diagrams speak the same visual language: warm red = the
// strongest causal commands, teal = sensing/monitoring, amber = actuation,
// grey = plain connectivity, purple = engineering/programming access.
export const relationshipColors: Record<string, string> = {
  controls: '#C0392B',
  monitors: '#1F8A70',
  actuates: '#E67E22',
  'connects-to': '#7F8C8D',
  'programs / operates': '#8E44AD',
}

export const RELATIONSHIP_FALLBACK_COLOR = '#64748b'

// Generic, vendor-neutral descriptions of common ICS/OT asset types, shown in
// the Node Details panel when the user asks "what is this asset?".  The keys
// are compacted lowercase tokens ("control valve" -> "controlvalve") so CSV/
// GraphML-derived types like "controlvalve" match the same description as the
// spaced canonical form.  When the topology itself carries a `description`
// field that value wins; this dictionary is the fallback for assets without
// one.  No vendor or model claims are made unless the topology names them.
export const assetTypeDescriptions: Record<string, string> = {
  dcscontroller:
    'A Distributed Control System (DCS) controller executes control logic for a process area and coordinates field instruments and actuators to keep the process within its operating envelope.',
  dcs: 'A Distributed Control System (DCS) controller executes process control logic and coordinates the field instruments of a process area.',
  plc: 'A programmable logic controller (PLC) is an industrial computer that runs real-time control logic, reading sensors and driving actuators and final elements.',
  rtu: 'A remote terminal unit (RTU) gathers field measurements and executes control commands at a remote site, typically talking to a central SCADA system over a telemetry link.',
  remoteio: 'A remote I/O unit concentrates field wiring (sensors and actuators) and connects it back to a controller over a fieldbus or industrial network.',
  scada: 'A SCADA system collects telemetry from remote sites and lets operators issue supervisory commands, usually over DNP3, Modbus or OPC.',
  hmi: 'A human–machine interface (HMI) presents live process data to operators and provides the screens used to supervise and command the control system.',
  operatorstation: 'An operator station is an HMI workstation used by process operators in the control room to monitor and command the plant.',
  engineeringworkstation:
    'An engineering workstation is used to configure, program and commission control systems (controllers, HMIs, historians); it is one of the most privileged assets on an OT network.',
  workstation: 'A workstation is a desktop-class computer used for engineering, business or operations tasks on its network.',
  historian:
    'A historian is a time-series database that collects and stores process data from the control system for analysis, reporting and troubleshooting.',
  firewall:
    'A firewall is a network security device that filters traffic between zones according to policy, forming the controlled boundary between networks of different trust levels.',
  gateway:
    'A gateway mediates traffic or protocol conversion between two networks or systems, typically as a controlled conduit between zones.',
  databroker:
    'A data broker (for example an OPC UA gateway) exchanges process data between the OT network and higher-level systems without granting direct control access.',
  jumpserver:
    'A jump server (bastion) is a hardened access host in the industrial DMZ that mediates interactive remote access from enterprise networks into the OT environment.',
  patchserver:
    'A patch/update server stages and distributes validated software updates into the OT environment through the industrial DMZ.',
  domaincontroller:
    'A domain controller provides authentication and directory services (for example Active Directory) for a network domain.',
  erp: 'An ERP server hosts enterprise resource planning applications such as finance, supply chain and maintenance management.',
  server: 'A server is a general-purpose host providing services (databases, directories, applications) to clients on its network.',
  networkswitch:
    'A network switch forwards traffic between devices on a LAN segment; in OT it carries control traffic between controllers, HMIs and field devices.',
  switch: 'A network switch forwards traffic between devices on the same network segment.',
  router: 'A router forwards traffic between different networks and implements routing policy.',
  pressuretransmitter:
    'A pressure transmitter measures process pressure and transmits the measured value to a control or safety system.',
  temperaturetransmitter:
    'A temperature transmitter measures process temperature and transmits the measured value to a control or safety system.',
  flowtransmitter:
    'A flow transmitter measures process flow rate and transmits the measured value to a control system.',
  leveltransmitter:
    'A level transmitter measures the level of liquid or solids in a vessel and transmits the measured value to a control system.',
  transmitter:
    'A transmitter measures a process variable (pressure, temperature, flow, level) and sends the value to a control or safety system.',
  sensor: 'A sensor measures a physical quantity in the process and provides it to a controller, monitoring system or safety system.',
  controlvalve:
    'A control valve is a final control element that modulates process flow in response to a controller output signal.',
  valve: 'A valve controls or isolates the flow of process fluid in a line or vessel.',
  safetyvalve:
    'A safety valve is a final element of a safety instrumented system (SIS) that isolates flow or relieves pressure to bring the process to a safe state.',
  safetyshutoffvalve:
    'A safety shutoff valve is a final element of a safety instrumented system (SIS) that isolates flow to bring the process to a safe state on demand.',
  safetyplc:
    'A safety PLC (safety logic solver) executes the safety instrumented functions (SIFs) of a safety system independently of the basic process control system.',
  safetylogicsolver:
    'A safety logic solver executes safety instrumented functions and initiates the safe state of the process when a dangerous condition is detected.',
  safetydevice:
    'A safety device participates in the safety instrumented chain (sensors, logic solver, final elements) that protects the process from hazardous conditions.',
  pump: 'A pump moves process fluid; it is typically driven by a motor controlled by a contactor or variable-frequency drive.',
  motor: 'A motor converts electrical energy into mechanical motion; it drives pumps, fans, conveyors and other rotating equipment.',
  vfd: 'A variable-frequency drive (VFD) controls the speed and torque of an AC motor by varying the supply frequency.',
  actuator: 'An actuator converts a control signal into mechanical motion to position a valve, damper or other final control element.',
  positioner: 'A positioner precisely sets the opening of a control valve based on the controller signal and valve position feedback.',
  reactor: 'A reactor is a process vessel where a chemical reaction takes place under controlled temperature, pressure and feed conditions.',
  distillationcolumn:
    'A distillation column separates a liquid mixture into fractions by differences in boiling point.',
  storagetank: 'A storage tank holds feedstock, intermediate or product material in bulk.',
  heatexchanger: 'A heat exchanger transfers heat between process streams.',
  pipeline: 'A pipeline is a physical conduit that transports fluids between process units, stations or sites.',
  robot: 'A robot is an automated manipulator used for welding, assembly, handling or other repetitive production tasks.',
  ied: 'An intelligent electronic device (IED) is a microprocessor-based protection and control device used in electrical substations (for example a protection relay).',
  pmu: 'A phasor measurement unit (PMU) measures voltage and current phasors across the power grid at high rate for situational awareness.',
  mergingunit: 'A merging unit digitises instrument transformer signals (current and voltage) for IEC 61850 process-bus protection systems.',
  transformer: 'A transformer converts voltage levels in the electrical network, stepping transmission voltage down for distribution.',
  circuitbreaker:
    'A circuit breaker interrupts current flow to isolate faulty equipment and protect the electrical network.',
  disconnect: 'A disconnector (isolator) provides a visible isolation point in high-voltage switchgear for maintenance safety.',
  ct: 'A current transformer (CT) scales high primary current down to measurable levels for protection and metering.',
  vt: 'A voltage transformer (VT) scales high primary voltage down to measurable levels for protection and metering.',
  dispatcher:
    'A dispatcher is an operator at a utility or pipeline control centre who supervises the network and coordinates field operations.',
  operator: 'An operator is a human who monitors and commands the process from an HMI or control console.',
  engineer: 'An engineer is a human who configures, programs and maintains the control and automation systems.',
  supervisor: 'A supervisor is a human responsible for overseeing production or shift operations.',
}

// Fallback explanations by asset kind for assets the dictionary does not
// cover (or that carry no declared type).  Kept deliberately generic — never
// vendor or model specific.
export const kindFallbackDescriptions: Record<string, string> = {
  device:
    'A networked industrial or IT device participating in the architecture; its specific role is defined by the topology.',
  human:
    'A person (operator, engineer or administrator) whose role and privileges influence the compromise model.',
  physical:
    'A physical process asset (vessel, tank, pump or pipeline) — the process equipment whose safety and availability the control system protects.',
}

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

// Purdue Enterprise Reference Architecture levels, ordered from the most
// trusted/external (Level 5) down to the physical process (Level 0). Level
// 3.5 is the industrial DMZ boundary between Enterprise IT and OT. Used for
// zone-band layout, legend swatches and the zone/Purdue chips on nodes. The
// level is architectural metadata only — it never alters the Bayesian
// mathematics directly.
export const purdueLevelMeta: Record<
  string,
  { label: string; short: string; hex: string; order: number }
> = {
  '5': {
    label: 'Level 5 · Enterprise / External',
    short: 'L5',
    hex: '#94a3b8',
    order: 0,
  },
  '4': {
    label: 'Level 4 · Enterprise IT',
    short: 'L4',
    hex: '#4dabf7',
    order: 1,
  },
  '3.5': {
    label: 'Level 3.5 · Industrial DMZ',
    short: 'L3.5',
    hex: '#ffa94d',
    order: 2,
  },
  '3': {
    label: 'Level 3 · Site Operations',
    short: 'L3',
    hex: '#845ef7',
    order: 3,
  },
  '2': {
    label: 'Level 2 · Area Control',
    short: 'L2',
    hex: '#38d9a9',
    order: 4,
  },
  '1': {
    label: 'Level 1 · Field Instruments',
    short: 'L1',
    hex: '#f783ac',
    order: 5,
  },
  '0': {
    label: 'Level 0 · Physical Process',
    short: 'L0',
    hex: '#ffd43b',
    order: 6,
  },
}

// Zones that do not map to a Purdue level (e.g. unzoned assets) sort after
// every declared level and render with a neutral colour.
export const UNZONED_META = { short: '—', hex: '#475569', order: 99 }


