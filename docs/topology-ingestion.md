# Topology Ingestion: Supported Representations & Analyst Workflow

This document describes how the framework ingests ICS topology information,
which representations are meaningful for risk analysis, what the canonical
internal model requires, and how an analyst should prepare inputs. It matches
the actual implementation in `backend/importers.py`, `backend/topology.py`,
`backend/api.py` and the upload workflow in the web UI.

---

## 1. The canonical internal representation

Every input format is converted into one normalized model before analysis:

```jsonc
{
  "assets": {
    "<asset id>": {
      "id": "plc_1",
      "name": "PLC-01",
      "kind": "device",                 // device | human | physical
      "zone": "Level 1",                // optional (IEC 62443-style security zone)
      "purdue_level": "2",               // optional; "0".."5" plus "3.5" (industrial DMZ)
      "vendor": "...", "model": "...", "ip": "...",   // optional
      // device attributes (strictly validated):
      "cvss_type": 7.5,                 // effective CVSS v3.1 base score
      "exposed": true, "patched": false,
      "consequence_severity": 8.0,
      "vulnerabilities": [{ "cve_id": "...", "vector": "CVSS:3.1/..." }],
      // human attributes:
      "role": "operator", "awareness": 0.4, "privilege": "standard",
      // physical attributes:
      "p_base_override": 0.02
    }
  },
  "relationships": [
    ["source_id", "target_id", "connects-to", false, { "protocol": "modbus" }]
    // (source, target, type, firewalled, metadata)
  ]
}
```

- **Assets** are a map of id → attributes. An asset exists as long as it has a
  usable identifier; `kind` defaults to `device` and is otherwise inferred
  from the name.
- **Relationships** are directed `(source, target, type, firewalled,
  metadata)` tuples. The model only supports the relationship types that carry
  a configured Noisy-OR causal weight: `controls`, `monitors`, `actuates`,
  `connects-to`, `programs / operates`. Anything else is rejected with an
  actionable error (a typo must never silently become `connects-to`).

### 1.1 Required vs optional information

**Required for a meaningful assessment:**

| Information | Role in the model |
| --- | --- |
| Asset identifiers | Bayesian nodes. |
| At least one relationship if more than one asset | Bayesian edges; a graph with several assets and zero edges is rejected. |
| Acyclic directed structure | Bayesian networks require a DAG; cycles are rejected. |

**Strongly recommended (without them, the model still runs but uses defaults):**

| Information | Effect when missing |
| --- | --- |
| `kind` (or a name the heuristic can classify) | Defaults to `device`. |
| CVSS (`cvss_type` or `vulnerabilities`) | Intrinsic probability falls back to the physical `p_base_override` or a small default leak; severity-dependent risk is understated. |
| `exposed` / `patched` | Exposure/patch multipliers are not applied. |
| `consequence_severity` | Impact normalises to the model's default severity. |
| `zone` / `network` | No zone attribution; the asset is reported as *without zone*. Zones are advisory/structural — they do not change the Bayesian computation itself. |
| `purdue_level` | The asset is assigned a default Purdue level derived from its zone (see `backend/topology.py::ZONE_PURDUE_DEFAULTS`); the architecture audit notes the omission. |
| `firewalled` on links | The firewalled multiplier is not applied. |

The web UI shows an **attribute coverage** summary after upload (e.g.
"CVSS: 4/11, Exposure: 11/11") so gaps are visible *before* analysis.

---

## 2. Supported representations and their real-world standing

The framework distinguishes between "supported" (a parser exists) and
"commonly produced by ICS/security tools". They are not the same thing, and
the UI labels every format accordingly.

| Format | Category in UI | What it really is | Real-world standing |
| --- | --- | --- | --- |
| **JSON / YAML** | Native analysis format (recommended) | The canonical model expressed directly. | Best for reproducible, version-controlled assessments and machine-to-machine exchange. |
| **CSV / XLSX** | Inventory / tabular format (recommended) | Asset inventory + connection tables (header-driven columns; blank-row or sheet-separated tables; also a bare 2-column `source,target` connection list). | **Commonly used in practice.** ICS teams routinely maintain asset inventories and network connection matrices in Excel/CSV. This is the most realistic day-to-day input. |
| **GraphML** | Graph interchange format | XML graph format (yEd, Gephi, networkx). Nodes → assets, edges → relationships; node/edge attributes such as `kind`, `zone`, `cvss`, `firewalled`, `protocol`, `trust`, `mitre` are promoted. | Appropriate when the architecture already lives in graph tooling. Reasonable, but less common than spreadsheets in ICS security work. |
| **AML (AutomationML)** | Industrial engineering exchange (IEC 62714) | The IEC 62714 plant-engineering format used with tools such as TIA Portal. `InternalElement`s become assets; `Connection`/`InternalLink` elements become relationships. | **Genuinely an industrial standard** — but the parser covers a subset (names, manufacturer, device type, connections, protocols). Most engineering detail is ignored, so it is an *engineering interchange* input, not a security-native one. |
| **Generic XML** | Technical interchange fallback | Any XML document with asset/relationship containers (`assets`, `nodes`, `devices`, `items` … / `relationships`, `edges`, `links`, `connections` …). No standard schema is assumed. | **Not a standard professional workflow by itself.** Useful for converting ad-hoc exports from internal tools; otherwise prefer the structured formats. |
| **VSDX / VDX (Visio)** | Visualization / conversion format | Microsoft Visio diagram files. Shapes must be annotated with `asset,<id>,<type>,…` or `relationship,<source>,<target>,<type>,…` text, or carry custom properties (`ID`, `Name`, `Kind`, `Vendor`, `Model`). Legacy binary `.vsd` is rejected with conversion guidance. | **Diagrams are for humans.** A plain, un-annotated Visio drawing has no machine-readable structure, so this is only meaningful as a *controlled conversion workflow* where the analyst annotates shapes per the documented convention. Not a drop-in diagram import. |

**Decision taken:** no format was removed — all parsers have passing tests and
each is defensible in at least one real scenario. Instead, the UI and this
document make the *semantics* explicit:

- **First-class (recommended):** JSON, YAML, CSV, XLSX — structured and
  inventory data that is realistic for analysts to provide.
- **Interchange:** GraphML, AML — useful when the data originates in graph or
  plant-engineering tooling.
- **Conversion/visualization:** VSDX, VDX, generic XML — supported, but the
  analyst is told exactly what the file must contain (annotated shapes /
  custom properties / ad-hoc schema) before it can be analyzed.

---

## 3. Validation rules (what the backend enforces)

Applied to every upload, regardless of format:

- Asset attributes are **strictly validated**: `cvss_type` ∈ [0, 10],
  `consequence_severity` ∈ [0, 10], `awareness` ∈ [0, 1],
  `p_base_override` ∈ [0, 1], booleans must be boolean, vulnerability
  vectors must be valid CVSS v3.1 strings. Invalid values reject the upload
  with an actionable message.
- **Self-loops** are removed with a warning (spreadsheet authoring mistakes).
- **Duplicate edges** are collapsed with a warning.
- Relationships referencing **unknown assets** are rejected.
- **Unknown relationship types** are rejected.
- **Cycles** are rejected (Bayesian networks require a DAG).
- A topology with assets but **no relationships** is rejected (except a single
  isolated asset, which is a valid degenerate model).
- Multiple disconnected subgraphs are allowed and logged (independent
  submodels).
- Uploads are bounded: file size (default 50 MB), zip expansion ratio for
  `.xlsx`/`.vsdx` (default 200 MB), and XML entity expansion is not possible
  (ElementTree does not resolve DTD entities).

Every non-destructive change (removed self-loop, collapsed duplicate, skipped
unidentifiable record) is reported as a **warning** and shown in the
pre-analysis review step — inputs are never silently altered.

---

## 4. The upload → review → analyze workflow

The web UI implements the pipeline below. The backend is authoritative at
every step; the frontend only presents what the API returns.

```
Select topology file (or preset dataset)
        ↓
Parse (format-specific importer)
        ↓
Normalize + validate (strict attribute validation, DAG check)
        ↓
Return structural summary + warnings
        ↓
Analyst reviews: file identity, format category, validation status,
asset/relationship/zone counts, attribute coverage, warnings
        ↓
Analyst confirms → Run assessment
```

- `POST /upload-topology-file` parses the file and returns the normalized
  topology, counts, the structural summary (`zones`, `kinds`,
  `relationship_types`, `firewalled_relationships`, `field_coverage`,
  `assets_without_zone`, `purdue_levels`, `architecture_issues`,
  `architecture_issue_counts`) and the `warnings` list. The summary is
  computed from the normalized data — the UI never fabricates review numbers.
- The analyst reviews this summary **before** Bayesian inference runs, so a
  malformed or surprising topology is caught early. `architecture_issues` is
  the advisory ICS audit (see `docs/ics_architecture.md`): it tells the
  analyst whether the architecture is defensible (Purdue-inspired zoning,
  IEC 62443 zone/conduit thinking, SIS isolation, controlled Enterprise/OT
  boundary) before they trust the risk numbers.
- `POST /analyze` re-validates the supplied topology (the API is stateless)
  and returns the full assessment.

---

## 5. Recommended analyst workflow

1. **Prefer a spreadsheet or JSON inventory.** Export the asset register
   (id, name, kind, zone, CVSS, exposed, patched, consequence severity) and
   the connection matrix (source, target, type, firewalled) as CSV/XLSX/JSON.
2. **Check the pre-analysis summary.** Confirm asset/relationship counts,
   zone coverage and attribute coverage. Fix anything the warnings call out.
3. **Review the field coverage indicators.** If most assets lack CVSS or
   consequence severity, the assessment will run but risk scores will rely on
   defaults — treat results as provisional.
4. **Run the assessment**, inspect the risk register, then iterate: add
   evidence, re-run, compare posteriors.
5. **For diagram-only assets** (Visio drawings without annotation), convert to
   GraphML/JSON/CSV or annotate shapes with the documented `asset,` /
   `relationship,` markers first.

---

## 6. Known limitations (honest)

- **AML parsing is partial.** AutomationML files are read for structure
  (InternalElements, connections, protocols, manufacturer/device-type
  attributes); the rich engineering semantics of the format are not mapped to
  security attributes.
- **Visio requires annotation.** Standard Visio drawings do not carry
  machine-readable topology; only annotated shapes or custom properties are
  read.
- **Generic XML assumes a convention.** It scans for common container tags;
  a truly arbitrary XML document is unlikely to parse into a useful topology.
- **Zone and Purdue level are structural, not computational.** Zones
  (IEC 62443-style security boundaries) and Purdue levels (architectural
  hierarchy) are surfaced in the UI and drive the architecture audit, but the
  Bayesian model itself does not use zone boundaries as trust boundaries —
  firewall flags on relationships are the mechanism that reduces propagated
  risk. This is a deliberate modelling choice documented in
  `docs/ics_architecture.md`: the topology's architecture improves the
  *causal structure and auditability* of the model, while propagation
  parameters stay explicit and calibratable.
- **CSV/XLSX column aliases are limited** to a documented set
  (`backend/importers.py::_ASSET_FIELD_MAP` / `_REL_FIELD_MAP`). Unknown
  columns are ignored (and visible in the attribute-coverage review).
