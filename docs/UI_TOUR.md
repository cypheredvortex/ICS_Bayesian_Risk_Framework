# UI Tour — ICS Bayesian Risk Assessment Framework

This document is the **single authoritative reference for the web user
interface** of the ICS Bayesian Risk Assessment Framework. It is a
reverse-engineered description of the application **as it is actually
implemented** (frontend components under `frontend/src/`, backed by the
FastAPI service in `backend/`). It exists so that:

- every on-screen label and every number can be traced to a definition;
- every technical term is defined (probability, severity, risk, and how they
  differ);
- every interaction and workflow is explained;
- the formulas shown or implied by the UI match the implementation exactly;
- the modelling assumptions and limitations that the UI surfaces are
  documented;
- no functionality is described that the application does not have.

> **Reading convention.** Labels in `code style` are exact strings shown in
> the interface. Where a value is computed by the backend, the implementing
> module is cited (`backend/risk.py` etc.). See
> [§17 Related documentation](#17-related-documentation) for the deeper
> methodological documents.

---

## Table of contents

- [1. Purpose of this document](#1-purpose-of-this-document)
- [2. Page anatomy](#2-page-anatomy)
- [3. Global elements](#3-global-elements)
- [4. Topology & Assessment card](#4-topology--assessment-card)
- [5. Network Viewer](#5-network-viewer)
- [6. Node Details card](#6-node-details-card)
- [7. Results Dashboard](#7-results-dashboard)
- [8. Charts: Compromise probability by asset / Assets by risk level](#8-charts-compromise-probability-by-asset--assets-by-risk-level)
- [9. Conditional Probability Tables](#9-conditional-probability-tables)
- [10. Header panels: Settings and Reports](#10-header-panels-settings-and-reports)
- [11. Glossary: every term defined](#11-glossary-every-term-defined)
- [12. Every formula, as implemented](#12-every-formula-as-implemented)
- [13. End-to-end workflows](#13-end-to-end-workflows)
- [14. Assumptions surfaced by the UI](#14-assumptions-surfaced-by-the-ui)
- [15. Limitations surfaced by the UI](#15-limitations-surfaced-by-the-ui)
- [16. Error handling and edge cases](#16-error-handling-and-edge-cases)
- [17. Related documentation](#17-related-documentation)

---

## 1. Purpose of this document

The UI is a decision-support workbench for ICS cyber-risk assessment. It
guides the analyst through a single pipeline: **import a topology → review it
→ optionally pin evidence → run a Bayesian assessment → inspect results →
export reports**.

This tour describes what the analyst sees at every step, what each element
means, and how each visible number is produced. It complements
`docs/USER_GUIDE.md` (a task-oriented manual) by being a **reference**: every
label, colour, icon, formula and interaction is catalogued here.

---

## 2. Page anatomy

The application is a single page (no routing). Top to bottom:

| # | Region | Component | Purpose |
| --- | --- | --- | --- |
| 1 | Header (always visible) | `Header.tsx` | Title, API status pill, `Settings` and `Reports` buttons, and the opened header panel |
| 2 | `Topology & Assessment` card | `TopologySection.tsx` | Upload/review/remove the topology; the `Evidence Selection` disclosure; `Run assessment` |
| 3 | Two-column grid | `NetworkViewer.tsx` + `NodeDetails.tsx` | The influence diagram and the details of the selected asset |
| 4 | Two-column grid | `ResultsDashboard.tsx` + `ProbabilityChart.tsx` | Decision-ready outputs and the probability / risk charts |

The two-column grids stack into a single column on narrow viewports (the
columns only apply at the `xl` breakpoint).
| 5 | `Conditional Probability Tables` card | `CptSection.tsx` | Per-node Noisy-OR CPTs of the Bayesian network |

The page works even while the backend is offline for display purposes, but
uploads, assessments and settings require the API. The header pill shows the
live status (see [§3.1](#31-header)).

---

## 3. Global elements

### 3.1 Header

- Tagline: `Bayesian Cyber-Risk Analysis` (small, cyan, letter-spaced).
- Title: `ICS Risk Assessment Framework`.
- **API status pill** (polled every 30 s from `GET /`): `Checking API…`,
  `API online`, or `API unreachable`. When unreachable, the Topology card
  additionally shows a rose banner: *"The backend API is currently
  unreachable. Topology uploads and assessments will fail until the service
  is available again."*
- **`Settings` button** — opens the Settings panel (see [§10.1](#101-settings-panel)).
  When the draft settings differ from what the server returned, the button
  shows a `•` marker.
- **`Reports` button** — opens the Reports panel ([§10.2](#102-reports-panel)).
- Only one header panel is open at a time: opening one closes the other.

### 3.2 Notifications (toasts)

Actions produce toasts in the top-right corner, auto-dismissing after 5 s
(`Toasts.tsx`). Tones: `success` (emerald, ✓), `error` (rose, ✕), `info`
(cyan, ℹ). Each toast has a dismiss (×) button. Examples:

- `Loaded <file>: N assets, M relationships.` (success)
- `Topology note: …` (info) — non-destructive normalisation notice.
- `Impossible evidence detected. … Affected nodes: …` (error).
- `Assessment complete — results are now on the dashboard.` (success)

### 3.3 Keyboard shortcuts

| Key | Action | Where defined |
| --- | --- | --- |
| `/` | Focus the node search box in the Network Viewer | `App.tsx` |
| `r` | Run the assessment | `App.tsx` |
| `Esc` | Close the Settings / Reports panels | `App.tsx` |

### 3.4 Shared design elements

- **Badges** (`ui.tsx`): small rounded chips coloured per tone — `cyan`,
  `slate`, `emerald`, `amber`, `rose`, `violet`.
- **Stat cards** (`stat-card`, `stat-label`, `stat-value`, `stat-hint`):
  metric blocks with a small uppercase label, a large monospace value and an
  explanatory hint.
- **Disclosures** (`details`/`summary`): expandable panels; the summary row is
  clickable and shows a chevron that rotates when open.
- **KvRow**: label/value rows (monospace values) with optional explanatory
  hints, used in Node Details and Bayesian Results.
- **Progress bars** (`progress-track` / `progress-fill`): cyan gradient fill.

---

## 4. Topology & Assessment card

The workflow entry point (`TopologySection.tsx`).

### 4.1 Initial state — dropzone

- Title `Topology & Assessment` with subtitle: *"Upload the ICS architecture
  to analyze. The framework converts it into assets, causal relationships and
  a Bayesian risk model."*
- A `Sample topology` button (top right) downloads a realistic SWAT
  water-treatment topology from the backend (`GET /api/datasets/swat_example`).
- The dropzone: *"Drag & drop a topology file, or click to browse"*, with the
  accepted extensions listed. It is keyboard accessible (Enter/Space opens the
  picker) and highlights while dragging over it.
- `Run assessment` is **disabled** until a topology with assets is loaded.
- Below, a status bar shows `No topology loaded yet. Upload a topology file
  to begin.` once a topology is present it reads `Active topology:
  <file> · N assets · M connections`.

**Accepted formats** (must match `backend/importers.py`):
`.json .yaml .yml .csv .xlsx .graphml .xml .aml .vsdx .vdx`.

### 4.2 Supported topology representations (disclosure)

The card includes an expandable `Supported topology representations` list
(`constants.ts::topologyFormats`) that honestly classifies each format — the
UI distinguishes *"supported by the framework"* from *"commonly produced by
ICS tools"*:

| Format | Category badge | Notes in the UI |
| --- | --- | --- |
| `.json / .yaml` | `Native analysis format` + `Recommended` | Canonical `assets` + `relationships` schema |
| `.csv / .xlsx` | `Inventory / tabular format` + `Recommended` | Header-driven asset/connection tables |
| `.graphml` | `Graph interchange format` | yEd / Gephi / networkx graphs; attributes promoted |
| `.aml` | `Industrial engineering exchange (IEC 62714)` | AutomationML; *partial coverage* (names, manufacturer, device type, connections, protocols) |
| `.xml` | `Technical interchange fallback` | Generic XML with asset/relationship containers |
| `.vsdx / .vdx` | `Visualization / conversion format` | Visio; shapes must be annotated or carry custom properties; legacy `.vsd` not supported |

### 4.3 Review panel after upload

After the backend validates the file (`POST /api/upload-topology-file`), the
dropzone is replaced by a review workspace:

- **File row**: filename (monospace), format badge, size badge, and a status
  badge: `Valid`, `Valid with warnings`, or `Loaded`.
- **Structural summary** (4 cells): `Assets` (detected asset records),
  `Relationships` (directed causal connections), `Zones` (distinct trust
  zones), `Without zone` (amber when *all* assets are unzoned).
- **`Attribute coverage`**: badges counting how many assets carry each
  attribute — `CVSS`, `Exposure`, `Patch state`, `Impact`, `Zone`,
  `Vulnerabilities` — e.g. `CVSS: 7/7`. A leading `✓` marks full coverage.
  See [§4.4](#44-how-the-attribute-coverage-badges-are-calculated) for how
  these counts are computed.
- **`Detected zones`**: violet badges with per-zone counts.
- **`Normalization warnings`** (amber, only when present): non-destructive
  adjustments (self-loops removed, duplicate edges collapsed, unidentifiable
  records skipped) — *nothing is silently dropped*.
- **`Replace file`** and **`Remove`** buttons. The hint reads: *"Replacing or
  removing clears the current assessment and evidence."* Removing returns to
  the empty state.

### 4.4 How the `Attribute coverage` badges are calculated

The badges count, per attribute, how many of the **normalized** assets carry
that attribute. The authoritative computation is
`backend/topology.py::build_topology_summary`; the frontend recomputes an
equivalent summary client-side as a fallback when an upload response omits it
(`utils.ts::deriveTopologySummary`). "Normalized" matters: the count runs
over the assets *after* validation, kind inference and field normalisation —
not over the raw file.

| Badge | Normalized field | An asset counts when … |
| --- | --- | --- |
| `CVSS` | `cvss_type` | the record has a `cvss_type` — declared directly, **or derived from a declared `vulnerabilities` list** (effective CVSS = max over the vulnerabilities). Device assets only. |
| `Exposure` | `exposed` | the asset **declared** `exposed` (true/false). |
| `Patch state` | `patched` | the asset **declared** `patched` (true/false). |
| `Impact` | `consequence_severity` | the asset declared a consequence severity (a value of `0` still counts — the field is present). |
| `Zone` | `zone` | the asset has a zone — declared, **or inferred from its name** (e.g. `corp_net` → `Corporate`, via the keyword table in `backend/topology.py`). |
| `Vulnerabilities` | `vulnerabilities` | the asset has a **non-empty** vulnerability list. |

The counting loop, exactly as implemented in `backend/topology.py`:

```python
for attrs in assets.values():
    for field in field_coverage:
        if field == "vulnerabilities":
            if attrs.get("vulnerabilities"):      # non-empty list
                field_coverage[field] += 1
        elif attrs.get(field) is not None:        # field present on the record
            field_coverage[field] += 1
```

The badge displays `label: n/total` (e.g. `CVSS: 5/7`), with a leading `✓`
when **every** asset carries that attribute (`n == total`). Its purpose is to
show, *before* running the assessment, which security-relevant attributes are
missing so the analyst can read the resulting probabilities with that in
mind.

Two things to keep in mind when reading the badges:

- **Coverage ≠ model defaults.** An asset that omits `exposed` / `patched`
  still receives the conservative model defaults (`exposed = true`,
  `patched = false`) — it just does not count as "covered".
- **Kind-dependent fields.** `CVSS`, `Exposure`, `Patch state` and
  `Vulnerabilities` apply to `device` assets only; `human` and `physical`
  assets never count toward them. A topology with mixed kinds can therefore
  never reach `✓` on those badges — that is expected, not an error.

### 4.5 Evidence Selection (disclosure inside the card)

`EvidencePanel.tsx`, embedded in the Topology card and collapsed by default.
The summary line shows the count, e.g. `3 of 7 assets marked` or
`optional — pin asset states before running`.

- A filter box (`Filter assets…`) and a `X of Y marked` badge.
- Assets are grouped by **zone** (`Unzoned` when no zone is declared).
- Each asset row has three state buttons — `Unknown`, `Compromised`, `Safe` —
  with the active state highlighted (rose for Compromised, emerald for Safe,
  slate for Unknown; `aria-pressed` reflects the state).

**What evidence means.** Evidence pins an asset to a known state. When the
assessment runs, pinned assets keep their state **exactly** (posterior = 1.0
for Compromised, 0.0 for Safe) and every other probability is recomputed from
them through the Bayesian network (`backend/inference.py`). `Unknown` means
"no evidence" and is not sent to the API.

---

## 5. Network Viewer

`NetworkViewer.tsx` renders the **Bayesian influence diagram** derived from
the topology using React Flow.

### 5.1 Controls

- **`Search nodes… ( / )`** — filters/highlights nodes; non-matching nodes are
  dimmed. `/` focuses it.
- **Colour-mode toggle** — `By risk` | `By asset type` (risk is the default).
- **`Attack path` toggle** (`aria-pressed`, on by default) — toggles the rose
  highlighting of the highest-priority attack path after an assessment. When
  on, a rose **`Attack path` indicator chip** is overlaid on the top-left of
  the canvas showing the route (`entry → target`) so the highlighted path
  cannot be missed.
- **`Edge labels` toggle** (`aria-pressed`, on by default) — shows/hides the
  relationship label on every edge. Labels default to ON so relationship
  types and causal weights are readable at a glance; hide them on dense
  graphs.
- **`Fullscreen` toggle** — expands the graph canvas to fill the screen (an
  in-canvas `Exit fullscreen` control stays reachable while fullscreen is
  active).

### 5.2 Nodes

Each node card shows the asset id, its kind label, and its probability value
(monospace, `0.000` format). The card's background colour depends on the mode:

- **By risk** — colour by the asset's **posterior probability** (not risk
  index): emerald `< 0.20`, cyan `0.20–0.45`, amber `0.45–0.70`, rose `≥ 0.70`
  (`utils.ts::getProbabilityColor`).
- **By asset type** — violet `human`, cyan `device`, amber `physical process`
  (`constants.ts::kindMeta`).

Node borders encode state:

| Border | Meaning |
| --- | --- |
| White glow / thick border | Currently selected node |
| Rose glow | On the highest-priority attack path |
| Dashed dark border | Pinned by evidence (shown with a 📌 pin in the node) |
| Dimmed (opacity 0.22) | Filtered out by the current search or not adjacent to the selection |

**Interactions:** click a node to select it (updates the Node Details card);
click the empty pane to clear the selection.

### 5.3 Edges

Directed edges carry labels like `connects-to w=0.50`, `controls 🔒 w=0.70`
— the relationship type, a 🔒 when the link is firewalled, and the
**Noisy-OR causal weight** `w` (a modelling parameter, *not* a conditional
probability). Labels are shown on every edge by default (the `Edge labels`
toggle hides them). Edges on the attack path are animated, thicker and rose,
with a stronger glow and arrowheads so they stand out from ordinary links.

The `How to read this network` disclosure explains:
> *"Edge labels show the relationship type and its Noisy-OR causal weight
> w — a modelling parameter, not a conditional probability. For one active
> parent, P(target = 1 | parent = 1) = 1 − (1 − leak)·(1 − w)."*

and:
> *"An attack path is a calculated sequence of directed links from a likely
> entry point to a high-risk asset; it prioritises investigation and is not
> proof that an attack occurred."*

### 5.4 Legend (below the canvas)

- `Posterior probability:` four swatches — `Low (< 0.20)`,
  `0.20 – 0.45`, `0.45 – 0.70`, `High (≥ 0.70)` — or the asset-kind swatches
  in kind mode.
- 📌 `evidence-pinned`
- a rose line `attack path`
- 🔒 `firewalled link`

The canvas itself provides a **minimap**, **zoom/pan controls**, and a dotted
grid background. The layout is layered left-to-right (upstream → downstream,
`utils.ts::computeLayeredPositions`).

### 5.5 Bayesian Results (disclosure)

Collapsed by default; the summary shows `N assets · X.XXX overall risk` (or
`run an assessment to populate`). Expanding shows (`BayesianResults.tsx`):

- `Evidence used` — the applied evidence chips (Compromised / Safe).
- `Assets`, `Connections`, `Run time` (seconds, 3 decimals), `Topology`.
- `Settings used` — the parameter snapshot of the run: mapping method, k, x₀,
  impact weight, and the active risk-threshold scale.
- `Non-default settings` (amber, only when present) — any model parameter that
  deviates from the framework defaults, listed by key.

---

## 6. Node Details card

`NodeDetails.tsx` shows the selected asset. Every value comes from the actual
assessment result — nothing is displayed that was not calculated. When no
node is selected the card shows: *"Select a node in the network to inspect its
probability, risk and relationship details."*

### 6.1 Asset identity

- Asset id and a clickable **asset-type chip** — the declared device type
  (e.g. `PLC`) when the topology names one, otherwise the kind badge
  (`Human`, `Device`, `Physical process`). Clicking the chip toggles the
  **"What this asset is"** panel, which shows the asset's display name (when
  it differs from the id), the **meaning of the abbreviation** (e.g.
  `PLC = Programmable Logic Controller`, derived from the explanation text),
  and a plain-language explanation of what the asset is and does. Clicking
  the asset id toggles the same panel.
- `Zone` badge when the topology provides one.
- Vendor / model / IP line — descriptive metadata from the topology; the UI
  treats it as informational only (it does not influence calculations).

### 6.2 Security context

- `CVSS (effective)` — the asset's effective CVSS v3.1 Base Score: the
  **maximum over its listed vulnerabilities** (`backend/cvss.py`), with a hint
  that it is *"severity, not probability"*. If the asset lists vulnerabilities,
  the count appears (`7.5 · 2 vuln.`).
- `Exposure` — `Exposed` / `Not exposed` (analyst-supplied boolean).
- `Patch state` — `Patched` / `Unpatched` (analyst-supplied boolean).
- **Vulnerabilities** list — CVE id or vector with its base score.

### 6.3 Bayesian analysis

- `Intrinsic probability` — the asset's starting compromise probability
  **before** network propagation or evidence (the Noisy-OR *leak*). Computed
  from the asset's own attributes (`backend/probability.py`).
- `Posterior` — the compromise probability **after** evidence and network
  dependencies (exact Variable Elimination). When the asset is pinned by
  evidence the hint says the value is set directly from the selected evidence.

### 6.4 Risk

- `Consequence impact` — `Impact = (consequence_severity/10) ×
  scope_multiplier × impact_weight` (hint: *"Normalised impact = severity/10 ×
  scope multiplier (0–1.4)"*).
- `Risk index` — `Posterior × Impact`. The hint is explicit: *"Risk index =
  posterior probability × impact. It is a ranking metric, not a probability."*
- `Risk level` — badge (`Critical`/`High`/`Moderate`/`Low`).
- `Risk rank` — position in the complete risk register (1 = highest).
- `On top attack path` — `Yes` (rose) / `No` (slate), whether the asset lies on
  the highest-scoring calculated path.

### 6.5 Relationships

- `Incoming causal relationships (n)` and `Outgoing causal relationships (n)`
  — the directed edges touching this asset, showing the neighbour and the
  relationship type (up to six shown). Each is a causal edge in the Bayesian
  network.

---

## 7. Results Dashboard

`ResultsDashboard.tsx` — the decision-ready outputs of the **latest** run.
Before any run, this card shows: *"No assessment results yet. Load a
topology, optionally mark evidence, then run the assessment."*

A badge in the header shows `N evidence items` or `No evidence`.

### 7.1 Overall Risk (worst case) and Risk Level

- `Overall Risk (worst case)` — the worst-case single-asset risk index
  (`backend/risk.py::compute_aggregate_risk` → `max_risk`), with the hint
  *"Highest single-asset risk index in the topology."*
- `Risk Level` — the qualitative level of that value, coloured by level, with
  the **active** threshold scale shown:
  `Low < 0.25 · Moderate 0.25–0.50 · High 0.50–0.75 · Critical ≥ 0.75`
  (values come from settings — they are never hardcoded).

### 7.2 Selected Evidence

Shown only when evidence was applied: *"N of M assets pinned to a known
state"*, with the explanation that pinned assets keep their assigned value
exactly and every other probability is recomputed. The evidence chips
(Compromised rose / Safe emerald) collapse beyond 8 items with a `+N more`
badge and a `Show all N evidence items` toggle.

### 7.3 Posterior probabilities

For every asset: a row with the asset id (📌 when pinned), a probability bar
and the value. The caption distinguishes the two cases:
*"Posterior compromise probability after applying N selected evidence items
and propagating through the Bayesian network."* Clicking a row selects the
asset in the Node Details card.

### 7.4 Risk Ranking by Asset

The **complete** ranking of every asset, ordered highest → lowest risk index
(1 = highest). Each row shows the rank (`#1`), the asset, and
`P 0.500 × 0.700 = 0.350` (probability × impact = risk index). The caption
explains: *"Risk index = posterior probability × normalised consequence
impact (severity/10 × scope). Probability and impact are shown separately so
the product is transparent."* Clicking a row selects the asset.

### 7.5 Highest-priority attack path

The modelled route with the highest combined propagation-and-target-risk
score (`backend/attack_paths.py`). The card shows:

- The path as a directed sequence, e.g.
  `vendor_remote_access → engineering_workstation → scada_server → plc_dosing`.
- A highlighted **Path score** block: a large rose `Path score` value
  (e.g. `0.358`), a `Top priority` badge, and the explanation: *"The score
  combines link propagation weights with destination risk to rank
  investigation targets. It prioritises investigation; it is not proof of a
  real intrusion."*
- `All calculated attack paths (n)` disclosure — every route meeting the
  model's minimum-propagation threshold and maximum-depth safeguards, each
  listed with its score. Caption: *"Ordered by score."*

When no path was calculated: *"No path was calculated. Mark an entry asset as
Compromised to analyse a specific scenario."*

### 7.6 Settings traceability

The Results Dashboard itself shows the risk threshold scale (7.1); the full
parameter snapshot (`settings_used`) appears in the Network Viewer's
**Bayesian Results** disclosure ([§5.5](#55-bayesian-results-disclosure)) and
in the exports. Non-default parameters used by the run are flagged there, so
the numbers on this dashboard can always be traced to the assumptions that
produced them.

---

## 8. Charts: Compromise probability by asset / Assets by risk level

`ProbabilityChart.tsx` — the right column of the results grid.

### 8.1 Compromise probability by asset (bar chart)

A bar chart of **posterior probabilities** (probability, not risk; `0–1` y
axis). Bars are coloured with the probability scale (§5.4).

- **Interaction:** clicking a bar selects that asset. The page scrolls the
  **Node Details** card into view so the analyst immediately sees the asset's
  details, the clicked bar is outlined in cyan, and a note appears under the
  chart: `Selected asset: <asset> — its details are shown in the Node Details
  panel above. Click the bar again to clear the selection.` Re-clicking the
  already-selected bar **clears the selection**: the cyan outline and the note
  disappear and the Node Details card returns to its empty state
  (`No asset selected`).
- The subtitle states: *"This chart shows probability, not the risk score.
  Click a bar to inspect that asset's details in the Node Details panel."*

### 8.2 Assets by risk level (pie chart + drill-down)

`RiskPieChart.tsx` — embedded below the bar chart. A donut of how many assets
fall into each risk level, classified with the **active thresholds**.

- Legend chips show counts and percentages, e.g. `Critical: 2 (29%)`.
- **Clicking a slice or a legend entry** lists the assets of that level
  (`Critical — 2 assets`), each row showing `P 0.900 × 0.900 = 0.810`
  (probability × impact = risk index). Clicking a row selects the asset.
- `Back to overview` returns to the legend. The subtitle says: *"Click a slice
  or legend entry to list the assets of that level."*
- Before any assessment: `No risk distribution — Run an assessment to see the
  risk-level breakdown.`

---

## 9. Conditional Probability Tables

`CptSection.tsx` — the final card. It lets the analyst inspect each node's
generated **Noisy-OR CPT**. The subtitle states the exact formula:
*"Each row is P(node compromised | parent states) = 1 − (1 − leak) · Π(1 − wᵢ)
over the active parents, where leak is the node's intrinsic probability and
wᵢ are the edge causal weights."*

- A search box (`Search node CPTs`) filters the node tables.
- Each node is an expandable disclosure showing `parents:` (or `none` for
  root nodes) and a table of `Parent states` → `P(compromised)` rows
  (e.g. `parent1=1, parent2=0` → `0.612`; root nodes show `Root node`).
- Before a run: `No CPTs generated yet — Run an assessment to generate CPTs
  for every node.`

---

## 10. Header panels: Settings and Reports

### 10.1 Settings panel

`SettingsPanel.tsx` — opened with the header `Settings` button. Settings are
stored **server-side** (`GET/PUT /settings`) and apply to every future run,
not just the current session. The panel subtitle states: *"Changing an
assumption changes the output."* Actions: `Reset to defaults` and
`Save changes` (disabled until a value changes; `Saved` when clean).

| Section | Controls | Defaults (from `backend/settings.py`) |
| --- | --- | --- |
| **Weights** | `Exposure weight`, `Patch weight`, `Impact weight` sliders (0–2) | 1.0 each |
| **CVSS → probability mapping (modelling assumption)** | `Mapping method` select (`logistic (recommended)` / `linear (legacy, not recommended)`), `Logistic slope k` (0.1–2), `Logistic midpoint x₀` (0–10) | logistic, k = 0.8, x₀ = 5.0 |
| **Risk thresholds (single source of truth)** | `Critical ≥` (min = high, max 1.4), `High ≥` (min = moderate, max = critical), `Moderate ≥` (0 – high) | 0.75 / 0.50 / 0.25 |
| **Noisy-OR causal weight by relationship type** | One slider (0–1) per type: `controls`, `monitors`, `actuates`, `connects-to`, `programs / operates` | 0.70 / 0.20 / 0.60 / 0.50 / 0.80 |
| **Firewall multiplier** | `Link is firewalled` (0 – not-firewalled value), `Link is not firewalled` (firewalled value – 1.5) | 0.30 / 1.00 |
| `Default values (framework defaults)` disclosure | JSON dump of `defaultCoreSettings` | — |

Explanatory text in the panel makes the modelling stance explicit, e.g.:
*"CVSS Base Score is a severity metric (0–10), not a probability. The
framework converts it into an intrinsic compromise probability with
P₀ = 1 / (1 + exp(−k·(CVSS − x₀)))… These parameters are expert defaults (not
empirically calibrated)."*

The panel also states that the **same thresholds** drive the backend
classification, the PDF colours and the dashboard — they are not hardcoded
anywhere else, and the backend enforces the ordering `critical > high >
moderate`.

#### What each setting does

All settings are **modelling assumptions**, not measurements: changing one
changes the output of the next run. This is what each control actually does.

**Weights (`Exposure weight`, `Patch weight`, `Impact weight`).**

- `Exposure weight` and `Patch weight` (default 1.0, slider 0–2) control how
  strongly an asset's exposure and patch state move its *intrinsic
  probability*, applied in log-odds space
  (`backend/probability.py`):

  ```
  logit(P) = logit(P₀) + Σ wᵢ · ln(Mᵢ)
  ```

  with multipliers `M_exposed = 1.3`, `M_not exposed = 0.3`, `M_patched =
  0.9`, `M_unpatched = 1.2`. A weight of **0 disables** that factor; a
  higher weight amplifies its effect.
- `Impact weight` (default 1.0) scales the consequence impact inside the risk
  formula (`Impact = (severity/10) × scope_multiplier × impact_weight`), so
  it is a risk-appetite knob: raising it raises every risk index uniformly.
  It is the one weight that can push risk indices above the nominal ~1.4
  bound (the slider reaches 2.0).

**CVSS → probability mapping (the key modelling assumption).** CVSS Base
Score is a *severity* metric (0–10), not a probability; this section chooses
the function that converts severity into an intrinsic probability:

- `logistic (recommended)` — `P₀ = 1 / (1 + exp(−k·(CVSS − x₀)))`. An
  S-curve: CVSS 5 → ≈ 0.50, CVSS 10 → ≈ 0.98 (never exactly 1), CVSS 0 → ≈
  0.02. `k` (default 0.8) is the steepness, `x₀` (default 5.0) the midpoint
  where P = 0.50.
- `linear (legacy, not recommended)` — `P₀ = CVSS / 10`. Kept only for
  backward compatibility; it is indefensible because it assigns P = 1.0
  (certainty) to a CVSS-10 vulnerability.

  These parameters are **expert defaults, not empirically calibrated** — the
  panel says so explicitly and recommends calibration against your own
  incident data.

**Risk thresholds (single source of truth).** `Critical ≥`, `High ≥`,
`Moderate ≥` (defaults 0.75 / 0.50 / 0.25) classify each asset's **risk
index** into a qualitative level. The same values drive the backend
classification, the dashboard, the pie chart and the PDF colours — nothing is
hardcoded elsewhere — and the backend rejects any configuration that breaks
`critical > high > moderate`.

**Noisy-OR causal weights (per relationship type).** Each relationship type
carries a causal weight `w` (defaults `controls` 0.70, `monitors` 0.20,
`actuates` 0.60, `connects-to` 0.50, `programs / operates` 0.80). This is
*not* a conditional probability; it is the Noisy-OR causal parameter used to
build the CPTs (`backend/cpt_generator.py`):

```
P(node = 1 | active parents) = 1 − (1 − leak) · Π (1 − wᵢ)
```

A higher weight means a compromised parent is more likely to compromise the
child along that link type. The same base weight feeds the edge weight shown
on the network (`w_edge = min(0.99, base × firewall × protocol × trust ×
mitre)`, `backend/graph_builder.py`).

**Firewall multiplier.** `Link is firewalled` (default 0.30) / `Link is not
firewalled` (default 1.00). A firewalled link's propagated risk is dampened
by 0.30 — a ~70% reduction, consistent with NIST SP 800-41 guidance. A
firewall can only *reduce* propagated risk: the backend rejects a
configuration where the firewalled value exceeds the not-firewalled value.

**Settings not editable in the panel.** The settings store also contains
`protocol_multipliers`, `trust_multipliers`, `mitre_multipliers`,
`exposure_multipliers` and `patch_multipliers` tables used by the pipeline
but deliberately not exposed as sliders (to keep the panel usable). They
appear in the `Default values (framework defaults)` disclosure and in the
`settings_used` snapshot recorded with every run.

### 10.2 Reports panel

`ReportsSection.tsx` — opened with the header `Reports` button. Subtitle:
*"Download the outputs of the latest assessment run. Every file is generated
from the same authoritative result — the dashboard, CSV and PDF always
agree."*

| Export | Purpose (as shown) | Enabled |
| --- | --- | --- |
| `Assessment report (PDF)` 📄 | Management/audit documentation | after a run |
| `Risk register (CSV)` 📊 | Analysis in spreadsheets/scripts | after a run |
| `Full results (JSON)` 🧩 | Machine-readable record, reproducibility | after a run |

Downloads are disabled until an assessment has been run. The endpoints are
`GET /api/reports/assessment.pdf`, `…/risk_table.csv`, `…/assessment.json`.

---

## 11. Glossary: every term defined

The UI consistently separates **severity**, **probability** and **risk**.
This glossary is the key to reading every screen.

| Term | Definition | UI examples |
| --- | --- | --- |
| **Asset** | A node in the topology: `device` (PLC, HMI, sensor, server…), `human` (operators, engineers…), or `physical process` (pump, valve…). | Network nodes, Node Details |
| **Relationship** | A directed causal edge `[source, target, type, firewalled]`; type ∈ `controls`, `monitors`, `actuates`, `connects-to`, `programs / operates`. Risk propagates source → target. | Edge labels |
| **CVSS Base Score** | Official FIRST CVSS v3.1 score (0–10) of a vulnerability. **Severity, not probability.** | `CVSS (effective)` in Node Details |
| **Effective CVSS** | The maximum Base Score over the asset's listed vulnerabilities (worst-case severity). | `CVSS (effective)` value |
| **Severity** | The 0–10 consequence/impact scale of a compromise. Distinct from likelihood. | `consequence_severity` (topology), `severity` in exports |
| **Intrinsic probability** | Model probability that the asset is compromised from its own attributes alone, before network propagation or evidence. The Noisy-OR *leak*. | Node Details → `Intrinsic probability` |
| **Posterior probability** | `P(asset = 1 | evidence)`: model probability after evidence propagates through the full Bayesian network (exact Variable Elimination). **This is what the charts and node colours show.** | Dashboard `Posterior probabilities`, bar chart, node values |
| **Evidence** | An analyst-pinned state (`Compromised` = 1, `Safe` = 0). Pinned assets keep their state exactly; everything else is recomputed. | Evidence chips, 📌 pin |
| **Propagation weight / causal weight w** | Noisy-OR causal parameter of an edge. *Not* `P(child=1 | parent=1)`; the implied single-parent conditional is `1 − (1 − leak)(1 − w)`. | Edge labels `w=0.50` |
| **Leak** | The intrinsic probability of a node, used as the Noisy-OR leak. | `How to read this network`, CPT section |
| **CPT** | Conditional Probability Table: `P(node=1 | parent states)` for every parent combination, generated by the Noisy-OR rule. | `Conditional Probability Tables` card |
| **Consequence impact** | `(consequence_severity/10) × scope_multiplier × impact_weight` — a normalised consequence score, **not a probability**. | Node Details → `Consequence impact` |
| **Scope multiplier** | `1 + (scope − 1) × 0.1`, from the analyst-supplied blast radius `scope ∈ [1, 5]` → `[1.0, 1.4]`. | Node Details hint, exports |
| **Risk index** | `Posterior × Impact` — the **ranking metric**. Bounded ≈ [0, 1.4] at the default `impact_weight` (the bound extends if that setting is raised). **Not a probability, not expected loss.** | `Risk Ranking by Asset`, Node Details |
| **Risk level** | `Critical` / `High` / `Moderate` / `Low`, from classifying the risk index with the active thresholds. | Risk badges, pie chart |
| **Risk rank** | Position in the risk register sorted by risk index (1 = highest). | Node Details → `Risk rank` |
| **Overall Risk (worst case)** | The maximum single-asset risk index (network-level worst case). | Dashboard |
| **Attack path** | A directed sequence from a likely entry point to a high-consequence target through the DAG. An **investigation priority, not proof of intrusion**. | `Highest-priority attack path` |
| **Path score** | `path_probability × target_risk_index`, with `path_probability = min(posterior along path)` (default "weakest link") or the product of posteriors (env `ATTACK_PATH_SCORING=product`). | `Path score` block |
| **Firewalled link** | A relationship dampened by the firewalled multiplier (default 0.30). | 🔒 on edges |

### Severity vs probability vs risk — the three distinctions

1. **Severity ≠ probability.** CVSS Base Score (0–10) and consequence severity
   (0–10) measure *impact potential*, never likelihood. The framework converts
   severity into a probability via an explicit, configurable mapping — it
   never treats `P = CVSS/10` as its primary model.
2. **Probability ≠ risk.** The posterior probability (0–1) answers "how
   likely is this asset compromised?". The risk index multiplies it by
   consequence impact to answer "how much should I care?". A high probability
   with negligible consequence can rank below a moderate probability with
   severe consequence.
3. **Risk index ≠ probability.** It is a bounded ranking index ([0, ~1.4]);
   the UI says so on every screen where it appears.

---

## 12. Every formula, as implemented

All formulas below match the code exactly. Variables are marked **you**
(supplied via topology or Settings) or **computed**.

### 12.1 CVSS v3.1 Base Score (per vulnerability) — `backend/cvss.py`

```
ISS            = 1 − (1−C)(1−I)(1−A)
Impact         = 6.42·ISS                                    (scope unchanged)
               = 7.52·(ISS−0.029) − 3.25·(ISS−0.02)¹⁵         (scope changed)
Exploitability = 8.22 · AV · AC · PR · UI
Base score     = Roundup(min(Impact + Exploitability, 10))       (scope unchanged)
               = Roundup(min(1.08·(Impact + Exploitability), 10)) (scope changed)
```

- **You:** the vector metrics. **Computed:** score (0–10, one decimal).

### 12.2 Effective CVSS (per asset) — `backend/cvss.py::effective_cvss_score`

```
Effective CVSS = max over the asset's vulnerability base scores
```

- **You:** the vulnerability list. **Computed:** the maximum (worst case).

### 12.3 Intrinsic probability (per asset) — `backend/probability.py`

**Device** (default logistic mapping; the legacy linear mapping exists only
for backward compatibility):

```
P₀ = 1 / (1 + exp(−k·(CVSS − x₀)))            k = 0.8, x₀ = 5.0 (defaults)
logit(P) = logit(P₀) + Σ wᵢ · ln(Mᵢ)          (exposure, patch, optional protocol/trust/MITRE)
P    = 1 / (1 + exp(−logit(P))), capped to [1e-6, 0.9995]
```

**Human:** `P₀ = R_role · (1 − awareness)` (phishing susceptibility by role,
reduced by awareness), then adjusted for privilege via the same log-odds
mechanism. **Physical:** `P = p_base_override` (expert override, capped).

- **You:** asset attributes and the settings (k, x₀, weights, multipliers).
  **Computed:** P.

### 12.4 Edge propagation weight — `backend/graph_builder.py::edge_weight`

```
w = min(0.99, base(rel_type) × firewall_mult × protocol_mult × trust_mult × mitre_mult)
```

- **You:** relationship type, firewalled flag, optional protocol/trust/MITRE
  metadata, and the multiplier tables in Settings. **Computed:** w.

### 12.5 Noisy-OR CPT rows — `backend/cpt_generator.py`

```
P(node = 1 | parent states) = 1 − (1 − leak) · Π (1 − wᵢ)
                                               over active parents
```

Root nodes (no parents): `P(node=1) = leak`. Every row normalises: `P(0) + P(1)
= 1`. **You:** the causal weights and the leak (intrinsic probability).
**Computed:** every row of the table.

### 12.6 Posterior probability — `backend/inference.py`

```
P(node = 1 | evidence) = exact Variable Elimination on the parameterised BN
```

Evidence nodes are pinned to their asserted state (0 or 1). **You:** the
evidence. **Computed:** the posterior.

### 12.7 Impact, risk index, level, rank — `backend/risk.py`

```
scope_multiplier = 1 + (scope − 1) × 0.1          scope ∈ [1, 5] → [1.0, 1.4]
Impact           = (consequence_severity / 10) × scope_multiplier × impact_weight
Risk index       = Posterior × Impact                          ≈ [0, 1.4] with the
                                                               default impact_weight = 1.0;
                                                               raising it extends the bound
Risk level       = Critical ≥ c · High ≥ h · Moderate ≥ m · Low < m
                   (defaults c=0.75, h=0.50, m=0.25; configurable in Settings)
Rank             = position sorted by Risk index, descending (1 = highest)
```

- **You:** `consequence_severity`, `scope`, and (in Settings) `impact_weight`
  and the thresholds. **Computed:** everything else.

### 12.8 Overall network risk — `backend/risk.py::compute_aggregate_risk`

```
Overall Risk = max(Risk index over all assets)      (worst case; also shown in the dashboard)
also reported: mean_risk, median_risk, per-level asset counts
```

### 12.9 Attack-path score — `backend/attack_paths.py`

```
path_probability = min( P(nodeᵢ = 1 | evidence) )        (default, weakest link)
                 = Π P(nodeᵢ = 1 | evidence)             (ATTACK_PATH_SCORING=product)
path_score       = path_probability × target_risk_index
```

Paths are ranked by score, descending, subject to a minimum edge-weight
threshold and a maximum depth. Entry points are evidence-compromised assets,
or DAG roots (no incoming edges) when no such evidence exists; targets are
assets with non-zero consequence severity.

---

## 13. End-to-end workflows

### 13.1 The assessment workflow

```
1. Upload a topology (drag & drop / click; or download the Sample topology)
2. Review the validated summary (counts, coverage, zones, warnings)
3. Optional: pin Evidence (Compromised / Safe) per asset
4. Run assessment           (button or press "r")
5. Inspect results          (dashboard, charts, network, CPTs)
6. Export                   (Reports panel: PDF, CSV, JSON)
```

Notes on the run (`App.tsx` → `POST /api/analyze`):
- The run is **stateless**: the topology is sent with every request.
- Replacing or removing the topology clears results, evidence and selections.
- The success toast `Assessment complete` confirms the run; the first graph
  node is auto-selected after a run.

### 13.2 Inspecting an asset

Any of these selects an asset and updates the **Node Details** card:

1. Click a node in the **Network Viewer**.
2. Click a row in the dashboard's **Posterior probabilities** list.
3. Click a row in the **Risk Ranking by Asset** list.
4. Click a **bar** in the *Compromise probability by asset* chart (also
   scrolls the Node Details card into view). Clicking the same bar again
   clears the selection and returns the Node Details card to its empty state.
5. Click a row in the pie-chart **drill-down** list.

### 13.3 The reports workflow

Open `Reports` → choose an export (PDF report / CSV register / JSON record) →
download. Downloads require a completed assessment. All three are generated
from the same authoritative result, so they always agree with the dashboard.

### 13.4 Changing model assumptions

Open `Settings` → adjust any slider/select → `Save changes`. The new values
are validated server-side and applied to the **next** run. `Reset to
defaults` restores the framework defaults. The `Bayesian Results` disclosure
flags any non-default settings used by a run.

---

## 14. Assumptions surfaced by the UI

The UI states these assumptions explicitly (see the Settings panel, Node
Details hints, and the network reading guide):

1. **CVSS is severity, not probability.** The logistic mapping
   `P₀ = 1/(1 + exp(−k·(CVSS − x₀)))` with expert defaults k = 0.8, x₀ = 5.0
   is a modelling assumption, *not empirically calibrated*. The legacy linear
   mapping is labelled `not recommended`.
2. **Exposure and patch are analyst-supplied booleans** with conservative
   defaults (`exposed = true`, `patched = false`) when the topology omits
   them; the framework computes their *effect* (multipliers in log-odds
   space), never their value.
3. **Edge weights are causal parameters** (Noisy-OR), not literal conditional
   probabilities; the UI explains the relationship
   `P(target=1 | parent=1) = 1 − (1 − leak)(1 − w)`.
4. **Noisy-OR semantics**: parents combine as `1 − (1 − leak)·Π(1 − wᵢ)`; the
   leak equals the intrinsic probability.
5. **Evidence is certain and exact.** Uncertain or partial evidence is not
   modelled.
6. **Risk thresholds are calibration placeholders** (defaults 0.25 / 0.50 /
   0.75), configurable in Settings and treated as the single source of truth.
7. **The risk index is a ranking metric** — the UI repeats this wherever the
   number appears.
8. **Attack paths prioritise investigation**, not proof of intrusion.

---

## 15. Limitations surfaced by the UI

- **No empirically calibrated probabilities**: every parameter is an expert
  default; organisations should calibrate against their own data.
- **Vulnerability data is analyst-supplied**: the framework never queries NVD
  or another live service; the `source` field is attribution metadata only.
- **Exact inference** (Variable Elimination) can be slow on very large or
  high-treewidth networks.
- **Binary asset states** only; no continuous or multi-state variables, no
  time dynamics.
- **Evidence is binary and certain** (Compromised / Safe / Unknown).
- **The leak is not separately tunable** — it equals the intrinsic
  probability (documented in `docs/model-assumptions.md`).
- **The risk index is bounded and relative** (≈ [0, 1.4]); it is not expected
  loss, not ALE, not a compliance score.
- **The firewall factor is a static per-link multiplier**; defence-in-depth
  interactions are not modelled.
- **Reports inherit the same definitions and assumptions** as the dashboard.

---

## 16. Error handling and edge cases

| Situation | What the UI shows | What to do |
| --- | --- | --- |
| Unsupported file extension | Error toast listing the supported formats | Convert the file (e.g. `.vsd` → `.vsdx` or JSON) |
| Invalid JSON / YAML / XML / malformed topology | Error toast with the backend message | Fix the file and re-upload |
| Cycle in the topology | Rejected with a clear message | Remove the cycle (Bayesian inference requires a DAG) |
| Unknown asset / invalid type / out-of-range value | Error toast naming the problem | Fix the offending asset/relationship |
| Non-destructive normalisation | Info toast (`Topology note: …`) + warnings in the review panel | Review; the input was adjusted safely and visibly |
| Impossible evidence (e.g. `p_base_override: 0` asserted Compromised) | `Impossible evidence detected` with the affected nodes; the run fails **before** inference | Remove or change that evidence and rerun |
| File too large | 413 error | Stay under `MAX_UPLOAD_SIZE_MB` |
| Backend unreachable | Header pill `API unreachable` + rose banner; uploads/assessments fail | Start the API, check CORS/proxy |
| Contradictory evidence | Backend rejects with a message (backend-only guard for API clients; the UI's three-button toggle already enforces a single state per asset) | Give each asset at most one state |
| No path calculated | `No path was calculated. Mark an entry asset as Compromised…` | Add Compromised evidence on an entry asset and rerun |
| Download without a run | Reports download buttons disabled | Run an assessment first |

---

## 17. Related documentation

The UI renders numbers produced by the backend; the methodological depth lives
in these documents:

- `docs/USER_GUIDE.md` — task-oriented manual for operating the platform.
- `docs/metric_catalog.md` — authoritative definitions/formulas for every
  metric, with scientific-status classification.
- `docs/model-assumptions.md` — the complete statement of modelling
  assumptions.
- `docs/parameter-provenance.md` — where every parameter value comes from.
- `docs/scientific_validation_report.md` — validation approach and results.
- `docs/topology-ingestion.md` / `docs/topology_formats.md` — the topology
  schema and format details behind the upload workflow.

*This tour is kept in sync with the implementation and the documents above.
If a label, formula or interaction in the UI differs from what is described
here, the implementation and this document are the authority — and the other
documents should be updated to match.*
