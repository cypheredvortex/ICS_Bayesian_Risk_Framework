# ICS Risk Assessment Framework — User Guide

A practical, end-to-end manual for the **ICS Risk Assessment Framework**: what it
does, how to start it, how to run a Bayesian cyber-risk assessment of an
Industrial Control System (ICS) environment, and how to interpret and export the
results.

This guide describes the application as it is actually implemented. Where a
behaviour is a modelling assumption rather than an exact measurement, the guide
says so explicitly. It is written so that:

1. a new user can learn to operate the platform from scratch;
2. a technical user can follow the assessment workflow and understand each
   stage;
3. you can use it as a reference when explaining the platform to an internship
   mentor or reviewer.

---

## Table of contents

- [1. Application overview](#1-application-overview)
- [2. Starting the application](#2-starting-the-application)
- [3. The assessment workflow at a glance](#3-the-assessment-workflow-at-a-glance)
- [4. Topology import](#4-topology-import)
- [5. Topology review and visualization](#5-topology-review-and-visualization)
- [6. Evidence selection](#6-evidence-selection)
- [7. Running the assessment](#7-running-the-assessment)
- [8. Results Dashboard](#8-results-dashboard)
- [9. Legend — colours, icons and symbols](#9-legend--colours-icons-and-symbols)
- [10. Network viewer and node details](#10-network-viewer-and-node-details)
- [11. Reports](#11-reports)
- [12. Export formats](#12-export-formats)
- [13. Settings](#13-settings)
- [14. Error handling](#14-error-handling)
- [15. Interpreting the results responsibly](#15-interpreting-the-results-responsibly)

---

## 1. Application overview

The ICS Risk Assessment Framework is a **quantitative cyber-risk assessment
tool** for Industrial Control System environments. It converts a description of
your environment — assets (PLCs, HMIs, sensors, servers, operators, physical
processes) and the relationships between them — into a **Bayesian Network**,
runs exact probabilistic inference, and produces:

- a **compromise probability** for every asset (before and after evidence),
- a **risk index** and **risk level** for every asset,
- a **complete risk ranking** of all assets,
- **attack paths** for investigation prioritisation,
- **professional exports** (PDF report, CSV risk register, JSON full record).

The tool is a **decision-support aid**, not a guarantee of security. It helps an
analyst prioritise investigation and mitigation; it does not measure actual
intrusion, expected financial loss, or compliance.

### What problem it solves

ICS environments are hard to assess because a compromise can propagate between
assets (an operator workstation → a PLC → a physical process). The framework
models that propagation explicitly with a Bayesian network and quantifies each
asset's compromise probability given the topology, the asset's own attributes,
and any evidence you have (e.g. "we know the HMI was compromised").

### Intended users

- Cybersecurity / ICS risk analysts
- Operational technology (OT) engineers
- Students and interns documenting risk assessment methodology

---

## 2. Starting the application

### Prerequisites

- Python 3.11+
- Node.js 18+ (only for the web frontend)

### 2.1 Install dependencies

```bash
# Backend (from the project root)
python -m venv venv
# activate: venv\Scripts\activate on Windows, source venv/bin/activate on Linux/Mac
pip install -e .

# Frontend
cd frontend
npm install
cd ..
```

### 2.2 Start the backend API server

The backend is a FastAPI application that serves the analysis engine, the
settings store, and the report downloads.

```bash
ics-risk-api            # or: python -m uvicorn backend.api:app
```

- API base URL: **http://127.0.0.1:8000**
- Interactive API documentation: **http://127.0.0.1:8000/docs**

Environment variables (optional, see `README.md` / `.env.example`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | Bind address and port |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed browser origins |
| `ICS_DB_URL` | SQLite file | Persistence (settings, history) |
| `ICS_API_KEY` | *(empty = disabled)* | Enables API-key authentication |
| `MAX_UPLOAD_SIZE_MB` | `50` | Topology upload size limit |

### 2.3 Start the frontend

In a second terminal:

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies all `/api` requests
to `http://127.0.0.1:8000`, so no extra configuration is needed. The header
shows a live **API online** status pill.

### 2.4 Run everything with Docker

```bash
docker compose up --build
```

Serves the frontend (nginx, port **5173**), the API (port **8000**) and a
PostgreSQL database (port **5432**).

### 2.5 Run a one-shot assessment from the command line

The same engine powers the API, the web UI and the CLI:

```bash
ics-risk --topology data/swat_example.json --evidence corp_net=1
# equivalent: python -m backend  or  python main.py
```

Writes `output/` artifacts (graph, CPTs, posteriors, risk register CSV, summary).

---

## 3. The assessment workflow at a glance

```
Import topology            (upload a file or use the Sample topology)
      ↓
Validate topology          (DAG checks, cycle rejection, non-destructive warnings)
      ↓
Normalize topology         (self-loops removed, duplicate edges collapsed, records mapped)
      ↓
Build graph                (directed graph of assets and relationships)
      ↓
Select evidence (optional) (mark assets Compromised / Safe)
      ↓
Run assessment
      ↓
Build Bayesian Network     (Noisy-OR CPTs from asset attributes and link weights)
      ↓
Perform inference          (exact Variable Elimination)
      ↓
Calculate risk             (risk index = posterior × normalised impact, per asset)
      ↓
Review results             (Results Dashboard, charts, network viewer, CPTs)
      ↓
Generate / export report   (PDF report, CSV register, JSON record)
```

Every stage is implemented in the application; the UI guides you through the
first two stages in the **Topology & Assessment** card.

---

## 4. Topology import

### 4.1 Supported formats

The framework supports the following topology representations (the UI tells you
what each one really is and what it must contain):

| Format | Category | Notes |
| --- | --- | --- |
| `.json` / `.yaml` | Native | The canonical `assets` + `relationships` schema (see below) |
| `.csv` / `.xlsx` | Inventory | Header-driven asset and connection tables; multiple tables separated by blank rows (CSV) or sheets (XLSX) |
| `.graphml` | Graph interchange | yEd / Gephi / networkx graphs; node/edge attributes are promoted |
| `.aml` | AutomationML (IEC 62714) | Plant-engineering exchange (TIA Portal etc.); partial coverage — names, manufacturer, device type, connections and protocols are read |
| `.xml` | Generic XML | Ad-hoc XML exports with asset/relationship containers (assets, nodes, devices, links, edges, …) |
| `.vsdx` / `.vdx` | Visio diagrams | Shapes must be annotated (`asset…` / `relationship…` text markers) or carry custom properties; a plain diagram has no structure |

Legacy binary `.vsd` is **not** supported — convert it to `.vsdx` or export to
GraphML/JSON/CSV first.

### 4.2 The canonical topology schema

A topology is an object with two sections:

```json
{
  "assets": {
    "PLC-01": {
      "kind": "device",
      "exposed": true,
      "patched": false,
      "consequence_severity": 9,
      "scope": 4,
      "vulnerabilities": [
        {
          "cve_id": "CVE-2021-44228",
          "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
          "source": "NVD"
        }
      ]
    },
    "Operator-01": { "kind": "human", "role": "operator", "awareness": 0.4, "privilege": "standard" }
  },
  "relationships": [
    ["Operator-01", "PLC-01", "controls", false]
  ]
}
```

**Assets** — three kinds are supported:

- `device`: `vulnerabilities`, `cvss_type`, `exposed`, `patched`, `consequence_severity`, `scope`
- `human`: `role`, `awareness`, `privilege`, `consequence_severity`
- `physical`: `p_base_override`, `consequence_severity`, `scope`

`consequence_severity` is the analyst-supplied consequence of compromise on a
0–10 scale. `scope` (1–5) is the blast radius used by the risk model.

**Relationships** are directed links `[source, target, type, firewalled]` with
`type` one of `controls`, `monitors`, `actuates`, `connects-to`,
`programs / operates`. A relationship is a causal edge in the Bayesian network:
risk can propagate from source to target.

### 4.3 What makes a topology valid

- Every relationship must reference existing assets.
- Relationship types must be in the supported set.
- Values must be in range (e.g. `consequence_severity` 0–10, `scope` 1–5).
- The network must be a **DAG** — cycles are rejected, because Bayesian
  inference requires an acyclic graph.

Validation is strict where a problem would materially change the risk model
(these are **errors**), and lenient where a fix is safe:

- **Errors** (rejected with a clear message): cycles, unknown assets, invalid
  types, out-of-range values.
- **Non-destructive normalization** (performed **with an explicit warning**):
  self-loops removed, duplicate edges collapsed, unidentifiable records
  skipped. Nothing is silently dropped — warnings appear in the upload toast
  and in the topology review panel.

### 4.4 How to import in the UI

1. In the **Topology & Assessment** card, drag a file onto the drop zone or
   click to browse. Only supported extensions are accepted.
2. The backend parses and validates the file and shows a **review panel**:
   asset/relationship counts, per-zone and per-kind breakdowns, relationship
   types, firewalled links, attribute coverage, and any normalization warnings.
3. If the topology looks right, you can **Run assessment** immediately — or
   first select evidence (Section 6).

The same card lets you **remove** the current topology, which clears all
derived state (results, evidence, selections).

---

## 5. Topology review and visualization

- The review panel summarises the **normalized** topology: zones, asset kinds,
  relationship types, firewalled relationships and per-field attribute
  coverage. It shows exactly what the framework knows before analysis.
- The **Network Viewer** renders the graph with a layered layout (upstream →
  downstream). Nodes are coloured by **posterior probability** (risk mode) or
  by **asset type** (kind mode) — toggle with the colour-mode control. The
  minimap helps navigate large topologies.
- Use the **search box** (or press `/`) to find and highlight nodes.
- **Attack-path highlighting**: after an assessment, the highest-priority
  attack path is highlighted; toggle it on/off with the attack-path control.
- Select any node to inspect it in the **Node Details** panel (Section 10).

---

## 6. Evidence selection

**Evidence** is an asset you already know to be in a particular state:

- **Compromised** — you have reason to believe the asset is compromised.
- **Safe** — you have reason to believe the asset is not compromised.
- **Unknown** — no opinion (the default; unknown assets are simply not
  evidence).

Evidence is optional. To select it:

1. Expand the **Evidence Selection** section inside the Topology & Assessment
   card.
2. Use the filter box to find assets; they are grouped by zone.
3. Click **Compromised** or **Safe** for each asset you want to pin. The panel
   shows how many of the total assets are marked.

When the assessment runs:

- Evidence assets are **pinned**: their posterior probability equals the
  assigned value exactly (1.0 for Compromised, 0.0 for Safe).
- All other probabilities are **recomputed** from the evidence through the
  Bayesian network.
- **Impossible evidence** (e.g. marking an asset Compromised when the model
  gives it exactly zero probability of compromise under the other evidence) is
  **never silently accepted** — the run fails with a structured
  `Impossible evidence detected` diagnostic naming the affected assets. Remove
  or change that evidence and rerun.

The Results Dashboard shows the applied evidence (Section 8), and the posterior
probabilities legend reflects how many evidence items were used.

---

## 7. Running the assessment

Click **Run assessment** (or press **`r`**). The pipeline is:

1. **Load & normalize** the topology (validation + non-destructive warnings).
2. **Enrich** assets and relationships with context multipliers (exposure,
   patch, protocol, trust, MITRE technique).
3. **Build the graph** — a directed graph of assets and relationships.
4. **Compute intrinsic probabilities** — each asset's starting compromise
   probability from its own attributes (see below).
5. **Generate CPTs** — Noisy-OR conditional probability tables with the
   asset's intrinsic probability as the leak.
6. **Check evidence feasibility** — zero-probability evidence is rejected
   before inference.
7. **Infer posteriors** — exact **Variable Elimination** (pgmpy) computes every
   asset's posterior compromise probability given evidence.
8. **Compute risk** — the risk index and level per asset (Section 8), plus
   attack-path analysis.

The run is quick for typical topologies; the **Bayesian Results** panel shows
the total run time.

### Where the numbers come from (summary)

| Quantity | How it is computed |
| --- | --- |
| Intrinsic probability | Logistic mapping of effective CVSS v3.1 score: P₀ = 1 / (1 + exp(−k·(CVSS − x₀))), default k = 0.8, x₀ = 5.0, then adjusted by exposure/patch context in log-odds space |
| Effective CVSS | Official FIRST CVSS v3.1 equations; maximum over the asset's vulnerabilities (or the legacy `cvss_type` shortcut) |
| CPTs | Noisy-OR with leak = intrinsic probability; edge weights are configurable causal parameters, not literal probabilities |
| Posterior | Exact Variable Elimination given the selected evidence |
| Risk index | Posterior probability × normalised consequence impact (see Section 8) |

### Exposure, patch state and consequence impact — how they are calculated

**Exposure and patch state are analyst-supplied booleans** on each device
asset — the framework does not guess them. When a topology omits them, the
defaults are `exposed = true` and `patched = false` (the conservative choice:
assume reachable and unpatched unless told otherwise). What the framework
*calculates* is their **effect** on the intrinsic probability, through the
additive log-odds model:

    logit(P) = logit(P₀) + Σ wᵢ · log(Mᵢ)

| Factor | State | Default multiplier Mᵢ | Weight wᵢ |
| --- | --- | --- | --- |
| Exposure | `exposed = true` (reachable) | **1.3** | `exposure_weight` (default 1.0) |
| Exposure | `exposed = false` (not exposed) | **0.3** | `exposure_weight` |
| Patch | `patched = true` (fully patched) | **0.9** | `patch_weight` (default 1.0) |
| Patch | `patched = false` (unpatched) | **1.2** | `patch_weight` |

A multiplier above 1 shifts the logit up (higher compromise probability);
below 1 shifts it down. A weight of 0 disables the factor. The adjusted
probability is soft-capped so it is never exactly 0 or 1. Both the multipliers
and the weights are configurable in Settings (Section 13).

**Consequence impact** is fully calculated for every asset:

    Impact              = (consequence_severity / 10) × scope_multiplier × impact_weight
    scope_multiplier    = 1 + (scope − 1) × 0.1          (scope ∈ [1, 5] → [1.0, 1.4])

- `consequence_severity` (0–10) is **analyst-supplied** (10 = catastrophic
  loss of availability or safety); default 0.0 when omitted.
- `scope` (1–5) is the **analyst-supplied** blast radius of a compromise;
  default 1 (single asset).
- `impact_weight` is the calibration knob from Settings (default 1.0).

Impact is a normalised score in ≈ [0, 1.4] used only inside the risk index
`Risk = Posterior × Impact` — it is not a probability.

#### Where consequence_severity, scope and impact_weight come from

| Value | Where it comes from | Details |
| --- | --- | --- |
| `consequence_severity` (0–10) | **You — per asset in the topology** (default 0) | Your analyst judgement of how severe a compromise of that asset would be; 10 = catastrophic loss of availability or safety |
| `scope` (1–5) | **You — per asset in the topology** (default 1) | Your judgement of the blast radius; the framework derives `scope_multiplier = 1 + (scope − 1) × 0.1` from it |
| `impact_weight` | **Settings — global** (default 1.0) | An organisation-level calibration knob set in the Settings panel; applies to every asset in every run |

#### Inputs vs calculated — summary

| Quantity | Provided by you | Computed by the framework |
| --- | --- | --- |
| `exposed` (reachable or not) | ✅ topology (default `true`) | — |
| `patched` (patched or not) | ✅ topology (default `false`) | — |
| `consequence_severity` (0–10) | ✅ topology (default 0) | — |
| `scope` (1–5) | ✅ topology (default 1) | — |
| `scope_multiplier` | — | ✅ `1 + (scope − 1) × 0.1` from your `scope` |
| `impact_weight` | ✅ Settings (default 1.0) | — |
| Impact | — | ✅ `(severity/10) × scope_multiplier × impact_weight` |
| Risk index | — | ✅ `Posterior × Impact` |
| Risk level / rank | — | ✅ classified from the risk index with the active thresholds |

Exposure and patch state are never guessed or estimated — the framework takes
your values (or the documented defaults) and computes their effect on the
intrinsic probability. Impact is derived from your severity and scope values,
scaled by the global impact weight.

### Every formula, end to end

The complete chain of formulas the framework uses, in pipeline order. For each
formula the variables are marked **you** (supplied in the topology or Settings)
or **computed** (derived by the framework).

#### 1. CVSS v3.1 base score (per vulnerability)

Computed from the analyst-supplied vector (or taken as a numeric override):

    ISS            = 1 − (1−C)·(1−I)·(1−A)                          (impact sub-score)
    Impact         = 6.42·ISS            (scope unchanged)
                   = 7.52·(ISS−0.029) − 3.25·(ISS−0.02)¹⁵  (scope changed)
    Exploitability = 8.22 · AV · AC · PR · UI
    Base score     = Roundup(min(Impact + Exploitability, 10))        (scope unchanged)
                   = Roundup(min(1.08·(Impact + Exploitability), 10)) (scope changed)

- **You:** the vector metrics (AV, AC, PR, UI, S, C, I, A) in the topology.
- **Computed:** the base score (0–10) and its severity rating (Critical ≥ 9,
  High ≥ 7, Medium ≥ 4, Low > 0, None = 0).

#### 2. Effective CVSS (per asset)

    Effective CVSS = max(base score of each vulnerability)

- **You:** the vulnerability list.
- **Computed:** the maximum score — an asset is as severe as its worst
  vulnerability.

#### 3. Intrinsic probability (per asset, before propagation)

**Device:**

    P₀ = 1 / (1 + exp(−k·(CVSS − x₀)))      (logistic, default)
    P₀ = CVSS / 10                          (linear, legacy)

    logit(P) = logit(P₀) + Σ wᵢ·log(Mᵢ)     (exposure, patch, protocol, trust)
    P        = 1 / (1 + exp(−logit(P)))      (convert back, soft-capped < 1)

- **You:** `cvss` (from vulnerabilities), `exposed`, `patched`, optional
  `protocol` / `trust`; settings `k`, `x₀`, mapping, weights and multipliers.
- **Computed:** the adjusted probability P.

**Human:**

    P₀ = R_role × (1 − awareness)            then privilege-adjusted via log-odds

- **You:** `role`, `awareness` (0–1), `privilege`. **Computed:** P.

**Physical:**

    P₀ = p_base_override

- **You:** `p_base_override` (expert judgement). **Computed:** P (capped).

#### 4. Noisy-OR CPTs (per node, for every parent combination)

    P(node = 1 | parents) = 1 − (1 − p_base) · Π (1 − wᵢ)
                                              over active parents

- **You:** the causal weight `w` per relationship type (Settings); `p_base`
  comes from formula 3.
- **Computed:** each row of the conditional probability table.

#### 5. Posterior probability (per asset, after evidence)

    P(node = 1 | evidence) = exact Variable Elimination on the Bayesian network

- **You:** the evidence (`Compromised` / `Safe` on assets).
- **Computed:** the posterior in [0, 1]; evidence-pinned assets keep their
  assigned value exactly.

#### 6. Impact, risk index, level and rank (per asset)

    scope_multiplier = 1 + (scope − 1) × 0.1           (scope ∈ [1, 5])
    Impact           = (consequence_severity / 10) × scope_multiplier × impact_weight
    Risk index       = Posterior × Impact
    Risk level       = classification of Risk index against the thresholds
    Rank             = position in the list sorted by Risk index (descending)

- **You:** `consequence_severity`, `scope`; settings `impact_weight` and the
  risk thresholds.
- **Computed:** `scope_multiplier`, `Impact`, `Risk index`, level and rank.

#### 7. Attack-path score (per path)

    path_probability = min(P(nodeᵢ = 1 | evidence))        (weakest-link mode, default)
                    = Π P(nodeᵢ = 1 | evidence)            (product mode, optional)
    path_score       = path_probability × target_risk_index

- **You:** optionally `ATTACK_PATH_SCORING=product` (environment variable).
- **Computed:** path probability and score; paths are ranked by score.

#### 8. Overall network risk

    Overall Risk = max(Risk index over all assets)         (worst case)
    also reported: mean_risk, median_risk, per-level asset counts

- **Computed:** all of the above from the per-asset risk indices.

#### User inputs vs computed values — complete list

| Variable | Source |
| --- | --- |
| `exposed`, `patched` | **you** — topology (defaults: exposed, unpatched) |
| `consequence_severity` (0–10) | **you** — topology (default 0) |
| `scope` (1–5) | **you** — topology (default 1) |
| vulnerabilities / CVSS vectors | **you** — topology |
| human `role`, `awareness`, `privilege` | **you** — topology |
| physical `p_base_override` | **you** — topology |
| evidence (Compromised / Safe) | **you** — assessment step |
| `k`, `x₀`, mapping, weights, multipliers, thresholds | **you** — Settings (defaults provided) |
| CVSS base score, severity rating | **computed** (formula 1) |
| Effective CVSS | **computed** (formula 2) |
| Intrinsic probability | **computed** (formula 3) |
| CPTs | **computed** (formula 4) |
| Posterior probability | **computed** (formula 5) |
| `scope_multiplier`, Impact, Risk index, level, rank | **computed** (formula 6) |
| Attack-path probability and score | **computed** (formula 7) |
| Overall Risk, mean/median risk | **computed** (formula 8) |

These are modelling assumptions (expert defaults), not empirically calibrated
measurements — see Section 15.

---

## 8. Results Dashboard

The dashboard is the decision-ready output of the latest run.

### Overall Risk (worst case) and Risk Level

- **Overall Risk** is the **worst-case single-asset risk index** (the riskiest
  asset in the topology) — a defensible, size-independent network-level
  measure.
- **Risk Level** classifies that value with the **active thresholds** from
  settings (defaults: Critical ≥ 0.75, High ≥ 0.50, Moderate ≥ 0.25, Low <
  0.25). The displayed scale always reflects the configured thresholds.

### Selected Evidence

Lists the evidence items applied in this run as compact chips (Compromised /
Safe). With more than eight items the list collapses to a summary with a
**Show all** toggle; long asset names truncate with a hover tooltip. Pinned
assets keep their assigned value exactly.

### Posterior probabilities

For each asset, its **posterior compromise probability** after the applied
evidence propagates through the network — a genuine probability in [0, 1].
Evidence-pinned assets are marked with a pin (📌). The legend states how many
evidence items were applied.

### Risk Ranking by Asset

The **complete risk ranking** of every asset, ordered from highest to lowest
risk index (1 = highest). Each row shows the asset, its probability, its
impact, and the resulting risk index. The list is scrollable so large
topologies remain readable, and every row opens the asset in Node Details.

> The risk index is a **ranking metric**, not a probability:
>
> ```
> Impact     = (consequence_severity / 10) × scope_multiplier × impact_weight
>            scope_multiplier = 1 + (scope − 1) × 0.1   (scope ∈ [1,5])
> Risk Index = P(compromised | evidence) × Impact        (≈ [0, 1.4])
> ```

### Highest-priority attack path

The modelled route with the highest combined propagation-and-target-risk score.
It prioritises **investigation** — it is not proof of a real intrusion. Expand
**All calculated attack paths** to see every route meeting the model's
thresholds.

### Charts

- **Compromise probability by asset** — bar chart of posterior probabilities
  (probability, not risk).
- **Assets by risk level** — pie chart of how many assets fall into each risk
  level, classified with the active thresholds. It is interactive: click a
  slice or a legend entry to list the assets of that level with their ranks
  and risk indices (see Section 9).

### Settings used

A traceability section lists the **active parameters** that produced this run
(the `settings_used` snapshot) and flags every **non-default setting** with a
warning banner. If a value differs from the framework defaults, the banner
makes the deviation explicit — two runs can legitimately differ when the
active settings differ.

### CPT section

Inspect the full conditional probability tables of the Bayesian network
(filterable) to see exactly how each node's probability is derived from its
parents.

---

## 9. Legend — colours, icons and symbols

A quick reference for every colour, icon and label the interface uses, and what
it means. All colours and symbols come from the actual application; none imply
anything the framework does not calculate.

### Risk levels (risk ranking, pie chart, badges)

Colours classify each asset's **risk index** using the **active thresholds**
from Settings (defaults in parentheses):

| Colour | Level | Meaning |
| --- | --- | --- |
| Rose | **Critical** | Risk index ≥ critical threshold (≥ 0.75) — act first |
| Amber | **High** | Risk index ≥ high threshold (≥ 0.50) |
| Cyan | **Moderate** | Risk index ≥ moderate threshold (≥ 0.25) |
| Emerald | **Low** | Risk index below the moderate threshold (< 0.25) |

If you change the thresholds in Settings, the same values drive the ranking,
the pie chart and the PDF — the legend always reflects the current thresholds.

### Probability colours (bar chart, network nodes in risk mode)

A **separate** colour scale for the **posterior compromise probability**
(probability, not risk):

| Colour | Probability | Meaning |
| --- | --- | --- |
| Rose | ≥ 0.70 | Very likely compromised |
| Amber | 0.45 – 0.70 | Likely |
| Cyan | 0.20 – 0.45 | Possible |
| Emerald | < 0.20 | Unlikely |

### Asset kinds (network nodes in kind mode)

| Colour | Kind |
| --- | --- |
| Violet | Human (operators, engineers) |
| Cyan | Device (PLC, HMI, sensor, server) |
| Amber | Physical process |

### Evidence chips

| Chip | Meaning |
| --- | --- |
| Rose **Compromised** | Evidence pins the asset as compromised (posterior = 1.0) |
| Emerald **Safe** | Evidence pins the asset as safe (posterior = 0.0) |
| No chip (Unknown) | No opinion — the asset is not evidence |

### Icons and node markers (network viewer)

| Marker | Meaning |
| --- | --- |
| 📌 pin | Evidence-pinned asset — its probability is fixed at the assigned value |
| Rose glow around a node | Asset lies on the highest-priority attack path |
| White glow / thicker border | Currently selected node |
| Dashed border | Pinned by evidence |
| Dimmed node | Filtered out by the current search |

### Key numbers at a glance

| Label | Meaning |
| --- | --- |
| Intrinsic probability | Model probability of compromise from the asset's own attributes, **before** any propagation |
| Posterior probability | Same asset **after** evidence and network dependencies — the number the charts show |
| Impact | Consequence severity × scope multiplier × impact weight |
| Risk index | Posterior probability × Impact — the **ranking metric**, not a probability |
| Risk level | Risk index classified with the active thresholds |
| Overall Risk | Highest single-asset risk index in the topology (worst case) |

---

## 10. Network viewer and node details

Select any node in the network to open its **Node Details** card. Every value
shown there comes from the actual assessment results — nothing is displayed
that was not calculated. The card is organised in five blocks.

### Asset identity

- **Asset id and kind** — the node identifier from the topology and its kind
  (`device`, `human` or `physical process`), shown with its colour badge.
- **Zone** — the zone the asset belongs to (when the topology provides one).
- **Vendor / model / IP** — descriptive metadata from the topology (when
  present). It is informational only and does not influence the calculations.

### Security context

- **CVSS (effective)** — the asset's effective CVSS v3.1 Base Score: the
  **maximum over its vulnerabilities**. Scores are computed with the official
  FIRST v3.1 equations from the provided vectors (a numeric override is used
  only when no vector is given). This is a **severity** score (0–10), not a
  probability.
- **Exposure / Patch state** — analyst-supplied booleans (defaults: exposed,
  unpatched). The framework calculates their effect on the intrinsic
  probability through the log-odds model with the exposure/patch multipliers
  and weights — see Section 7, *Exposure, patch state and consequence impact*.
- **Vulnerabilities** — the validated list (CVE id or vector, and score) from
  which the effective CVSS is derived.

### Bayesian analysis

- **Intrinsic probability** — the asset's starting compromise probability
  **before** any network propagation or evidence, computed from its own
  attributes:
  - `device`: P₀ = 1 / (1 + exp(−k·(CVSS − x₀))) from the effective CVSS
    score (logistic mapping), then adjusted for exposure, patch, protocol
    and trust via the additive log-odds model
    `logit(P) = logit(P₀) + Σ wᵢ·log(Mᵢ)`.
  - `human`: P₀ = R_role × (1 − awareness) — the base phishing
    susceptibility for the role, reduced by the analyst-supplied awareness,
    then adjusted for privilege.
  - `physical`: P₀ = the `p_base_override` value supplied by the analyst
    (expert judgement; no CVSS involved).
- **Posterior** — the asset's compromise probability **after** applying the
  evidence and network dependencies, computed by exact **Variable
  Elimination** on the full Bayesian network. If the asset is pinned by
  evidence, the value is fixed at the assigned state (1.0 for Compromised,
  0.0 for Safe) and flagged.

### Risk

- **Consequence impact** — fully calculated from the analyst-supplied
  `consequence_severity` (0–10) and `scope` (1–5): `Impact =
  (consequence_severity / 10) × scope_multiplier × impact_weight`, with
  `scope_multiplier = 1 + (scope − 1) × 0.1` (range ≈ [0, 1.4]). See Section
  7, *Exposure, patch state and consequence impact*, for the step-by-step
  calculation.
- **Risk index** — `Risk index = Posterior × Impact`. A **ranking metric**,
  not a probability.
- **Risk level** — the risk index classified with the **active thresholds**
  from Settings (Critical / High / Moderate / Low).
- **Risk rank** — the asset's position in the **complete risk register**
  (1 = highest risk index).
- **On top attack path** — whether the asset lies on the modelled route with
  the highest combined propagation-and-target-risk score. It indicates an
  investigation priority, not proof of a real intrusion.

### Relationships

- **Incoming / outgoing causal relationships** — the directed links touching
  this asset. Each is a causal edge in the Bayesian network: risk can
  propagate from a source to a target. The relationship type is shown next to
  each neighbour.

---

## 11. Reports

Open **Reports** (header button, next to Settings) to download the outputs of
the latest assessment. Only one header panel is open at a time; press **Esc**
to close it. Three exports are offered (Section 12). The panel explains the
purpose and contents of each file, and downloads are disabled until an
assessment has been run.

All exports are generated from the **same authoritative result** as the
dashboard — the dashboard, the CSV, the PDF and the JSON record always agree.

---

## 12. Export formats

### PDF — assessment report (`assessment.pdf`)

- **Purpose:** management reporting, risk assessment documentation, audit
  evidence, mentor/reviewer presentation.
- **Contains:** executive summary and key metrics; the selected evidence
  (table that wraps long entries and spans pages); the model parameters used
  (traceability); the **complete risk register** (all assets, ranked, with
  probability, impact and risk level); attack-path analysis; methodology note.
- **When to use:** when you need a professional, presentable record of the
  assessment. Tables split across pages with repeating headers, so even large
  evidence sets and topologies stay readable.

### CSV — risk register (`risk_table.csv`)

- **Purpose:** data analysis — filtering, sorting, spreadsheet review, further
  processing.
- **Contains:** every asset with rank, posterior compromise probability,
  consequence severity, scope multiplier, impact, risk index and risk level
  (UTF-8 with BOM for Excel compatibility).
- **When to use:** when you want to analyse, transform or audit the
  asset-level results yourself.

### JSON — full results (`assessment.json`)

- **Purpose:** a complete machine-readable record of the run for archiving,
  reproducibility, comparison across runs, and interoperability with other
  tooling.
- **Contains:** the exact result the dashboard shows — assets, graph, CPTs,
  base and posterior probabilities, risk scores, attack paths, summary,
  evidence, timings and the settings snapshot that produced the run, plus a
  generation timestamp.
- **When to use:** when you need the full data behind a run, not a
  human-readable rendering of it.

**Why these three?** The CSV serves analysis, the PDF serves reporting, and the
JSON serves reproducibility/interoperability. Formats are not added for their
own sake — each has a distinct user-facing purpose, and the platform never
exports a field that was not actually calculated. **XLSX was considered and
deliberately not added**: the CSV register already opens directly in Excel and
covers spreadsheet analysis, filtering and re-processing, so an XLSX writer
would add a dependency with no user-facing benefit.

---

## 13. Settings

Open **Settings** (header button). Settings are stored **server-side**
(`GET/PUT /settings`) and applied to every future run — not just the current
session. They are **modelling assumptions**, not measurements: changing one
changes the output, so each parameter is documented below. Reset restores the
framework defaults; saving is disabled until a value actually changes.

### Weights (exposure, patch, impact)

- **Exposure weight** and **patch weight** (default **1.0**) control how
  strongly an asset's exposure and patch state influence its intrinsic
  probability. They are applied through the additive log-odds model
  `logit(P) = logit(P₀) + Σ wᵢ·log(Mᵢ)`, where Mᵢ is the corresponding
  multiplier (defaults: exposed 1.3 / not exposed 0.3; patched 0.9 /
  unpatched 1.2). A weight of 0 disables the factor; a higher weight
  amplifies its effect.
- **Impact weight** (default **1.0**) scales the consequence impact in the
  risk formula: `Impact = (severity/10) × scope_multiplier × impact_weight`.
  It is an organisation-level calibration knob for risk appetite.

### CVSS → probability mapping (modelling assumption)

CVSS Base Score is a **severity** metric (0–10), not a probability. The
framework must convert that score into an intrinsic compromise probability,
and this setting chooses **which mathematical function does the conversion**.

#### What each method is

- **logistic (recommended)** — applies the **sigmoid (S-curve) function**:
  `P₀ = 1 / (1 + exp(−k·(CVSS − x₀)))`, with slope `k` (default **0.8**) and
  midpoint `x₀` (default **5.0**). The curve is a smooth S: probabilities stay
  very low for weak scores, rise sharply around the midpoint, then **saturate**
  near 1.0 — but never exactly reach 1, because a CVSS-10 vulnerability makes
  compromise *highly likely*, not *certain*. It is the statistically
  defensible mapping used by default.
- **linear (legacy, not recommended)** — applies a **straight-line**
  function: `P₀ = CVSS / 10`. Every point on the scale increases the
  probability by the same amount (CVSS 2 → 0.2, CVSS 4 → 0.4, …). It is kept
  only for backward compatibility; it is indefensible because it assigns
  P = 1.0 (certainty) to a CVSS-10 vulnerability and gives no distinct
  behaviour at the extremes.

#### The difference at a glance

Both functions cross P = 0.50 at CVSS = 5 (with the default midpoint), but
they behave very differently away from the middle:

| CVSS score | Logistic P₀ (k=0.8, x₀=5) | Linear P₀ |
| --- | --- | --- |
| 0 | ≈ 0.02 (never exactly 0) | 0.00 |
| 2 | ≈ 0.08 | 0.20 |
| 4 | ≈ 0.31 | 0.40 |
| 5 | ≈ 0.50 | 0.50 |
| 6 | ≈ 0.69 | 0.60 |
| 8 | ≈ 0.92 | 0.80 |
| 10 | ≈ 0.98 (never exactly 1) | 1.00 |

Key differences:

- **Extremes:** linear forces P = 1.0 at CVSS 10 and P = 0 at CVSS 0;
  logistic saturates at ≈ 0.98 / ≈ 0.02 and never claims certainty or
  impossibility.
- **Sensitivity:** with logistic, small score changes matter most near the
  midpoint and least at the extremes (realistic); with linear, every point
  matters equally.
- **Shape:** logistic is an S-curve; linear is a straight line.
- **Tuning:** logistic has two knobs — `k` (steepness: a higher `k` makes the
  S-curve steeper, so scores near the midpoint separate more strongly) and
  `x₀` (midpoint: the CVSS value at which P = 0.50). Linear has no knobs.

These parameters are **expert defaults, not empirically calibrated** — an
organisation should calibrate `k`, `x₀` and the weights against its own
incident data.

### Risk thresholds

- **Critical ≥ / High ≥ / Moderate ≥** boundaries (defaults **0.75 / 0.50 /
  0.25**) classify each asset's risk index into a qualitative level. They are
  the **single source of truth**: the same values drive the backend
  classification, the dashboard, the pie chart and the PDF colours. The
  backend enforces the ordering critical > high > moderate.

### Noisy-OR causal weights

- Each relationship type (`controls`, `monitors`, `actuates`, `connects-to`,
  `programs / operates`) carries a causal weight `w` (default **0.2 – 0.8**).
  For a single active parent: `P(target = 1 | parent = 1) = 1 − (1 −
  leak)·(1 − w)`, where `leak` is the target's intrinsic probability. The
  weight is a **causal parameter, not a conditional probability** — higher
  values propagate more risk along that type of link.

### Firewall multiplier

- A firewalled relationship is dampened by the firewalled multiplier (default
  **0.3**; not firewalled **1.0**). A firewall can only **reduce** propagated
  risk, never increase it — the backend rejects a configuration where the
  firewalled value exceeds the non-firewalled value.

### Other server-side multipliers (not editable in the panel)

The settings store also contains context-multiplier tables used by the
pipeline but not exposed as sliders, to keep the panel usable:
`exposure_multipliers`, `patch_multipliers`, `protocol_multipliers` (e.g.
modbus 1.15, mqtt 1.20, http 1.25), `trust_multipliers` and
`mitre_multipliers`. They appear in the **Defaults reference** below and in
the settings snapshot recorded with every run.

### Defaults reference

The panel includes an expandable dump of the framework default values so you
can always compare the active configuration against the baseline.

---

## 14. Error handling

| Situation | What you see | What to do |
| --- | --- | --- |
| Unsupported file extension | Error toast listing supported formats | Convert the file (e.g. `.vsd` → `.vsdx` or JSON) |
| Invalid JSON / YAML / XML | Error toast with the parse message | Fix the file syntax |
| Cycle in the topology | Rejected with a clear message | Remove the cycle; Bayesian inference needs a DAG |
| Unknown asset / invalid type / out-of-range value | Rejected with a message naming the problem | Fix the asset or relationship |
| Non-destructive normalization (self-loop, duplicate edge, skipped record) | Info toast + warning in the review panel | Review; your input was adjusted safely and visibly |
| Impossible evidence | `Impossible evidence detected` diagnostic naming the affected assets | Remove or change that evidence and rerun |
| File too large | 413 error | Stay under the configured `MAX_UPLOAD_SIZE_MB` |
| Backend unreachable | Header shows "API unreachable" | Start `ics-risk-api` and check CORS / proxy |
| Download disabled | Reports buttons disabled | Run an assessment first |

The API returns structured errors with a `request_id`; the UI surfaces the
actionable message.

---

## 15. Interpreting the results responsibly

The framework is explicit about what it does and does **not** claim:

- **It calculates:** intrinsic and posterior compromise probabilities
  (Bayesian inference), a risk index (posterior × normalised impact), risk
  levels (configured thresholds), attack paths, and aggregate statistics.
- **It does not calculate:** expected financial loss, Annualised Loss
  Expectancy, confidence intervals, predictive accuracy, or compliance
  certification. No legend, report or export claims otherwise.
- **The risk index is a ranking measure**, not a probability and not a
  monetary figure.
- **Parameters are expert defaults, not empirically calibrated.** An
  organisation should calibrate `k`, `x₀`, weights and thresholds against its
  own incident data.
- **Vulnerability data is analyst-supplied.** The framework does not fetch NVD
  data at runtime; the `source` field is attribution metadata only.
- **Evidence is certain.** Uncertain or partial evidence is not modelled.

Use the results alongside domain expertise and other security assessments —
they prioritise investigation, they do not replace judgement.

For the complete scientific and methodological detail see
[`docs/scientific_validation_report.md`](scientific_validation_report.md),
[`docs/metric_catalog.md`](metric_catalog.md),
[`docs/model-assumptions.md`](model-assumptions.md) and
[`docs/parameter-provenance.md`](parameter-provenance.md).
