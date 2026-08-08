# ICS Bayesian Risk Framework

A generic Bayesian-Network-based quantitative risk assessment framework for
Industrial Control Systems (ICS). It converts a topology of assets and
relationships into a Bayesian Network, runs exact inference, and produces a
ranked risk register and executive report — while being explicit about which
parts of the model are mathematically exact and which are assumptions.

---

## Overview

The framework provides a complete pipeline for quantitative cyber-risk
assessment of ICS environments:

- **Topology import** — JSON, YAML, CSV, Excel, GraphML, XML/AML, VSDX, VDX
- **Bayesian Network construction** — DAG built from validated ICS relationships
- **Intrinsic probability** — CVSS severity → prior probability via an explicit logistic model
- **CPT generation** — Noisy-OR conditional probability tables
- **Inference** — exact Variable Elimination (pgmpy)
- **Risk scoring** — `Risk Index = P(compromised | evidence) × Impact`
- **Attack path analysis** — DAG-directed propagation paths
- **Visualisation** — network viewer, probability charts, CPT inspection
- **Reporting** — CSV risk register and PDF assessment report
- **Sensitivity analysis** — quantify how outputs respond to assumption changes

---

## Scientific honesty at a glance

- **CVSS v3.1 Base Scores** are computed with the **official FIRST equations**
  (`backend/cvss.py`). This part is exact.
- **CVSS is a severity metric, not a probability.** The framework converts
  severity into an intrinsic compromise probability with an explicit,
  configurable logistic model — never `P = CVSS / 10` (the linear mapping is
  retained only as a legacy, not-recommended option).
- **Vulnerability data is analyst-supplied.** The framework does **not**
  retrieve NVD data at runtime. A record with `"source": "NVD"` means "this
  vector was originally published by NVD and entered by an analyst"; it is
  not proof that NVD was queried.
- **No parameter is empirically calibrated.** Every numeric default is an
  expert judgment, a literature-consistent default, or a framework default.
  See `docs/parameter-provenance.md` for the full table.
- **The risk index is a ranking measure**, not a probability, not an ALE,
  and not an expected monetary loss.
- **Impossible evidence is never silently accepted.** Zero-probability
  evidence returns a structured `IMPOSSIBLE_EVIDENCE` diagnostic.

Authoritative documents: [`docs/model-assumptions.md`](docs/model-assumptions.md),
[`docs/parameter-provenance.md`](docs/parameter-provenance.md) and
[`docs/topology-ingestion.md`](docs/topology-ingestion.md) (supported topology
representations, format semantics and the analyst upload workflow).

---

## Quick start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for the frontend)

### Installation

```bash
# Clone the repository
git clone https://github.com/cypheredvortex/ICS_Bayesian_Risk_Framework.git
cd ICS_Bayesian_Risk_Framework

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate    # Windows

# Install Python dependencies
pip install -e .

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### CLI usage

```bash
# Run an assessment with the default topology
ics-risk

# Run with a specific topology and evidence
ics-risk --topology data/swat_example.json --evidence corp_net=1

# Start the API server
ics-risk-api
```

### API usage

```bash
# Start the API server
ics-risk-api

# In another terminal, run an assessment
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "topology": {"assets": {...}, "relationships": [...]},
    "evidence": [{"asset": "corp_net", "state": "Compromised"}]
  }'
```

### Frontend

```bash
cd frontend
npm run dev
```

The frontend runs on http://localhost:5173 and proxies API requests to
http://localhost:8000.

---

## Project structure

```
ICS_Bayesian_Risk_Framework/
├── backend/                 # Python package
│   ├── api.py              # FastAPI REST API
│   ├── cli.py              # CLI interface
│   ├── cvss.py             # Official CVSS v3.1 scoring
│   ├── probability.py      # Intrinsic probability (logistic mapping + log-odds context)
│   ├── cpt_generator.py    # Noisy-OR CPT generation
│   ├── inference.py        # Variable Elimination + impossible-evidence checks
│   ├── risk.py             # Risk index and level classification
│   ├── attack_paths.py     # DAG-directed attack path analysis
│   ├── sensitivity.py      # One-at-a-time sensitivity analysis
│   ├── importers.py        # Multi-format topology import + upload security
│   ├── topology.py         # Topology validation (non-destructive warnings)
│   └── database/           # SQLAlchemy persistence (settings, assessments)
├── frontend/               # React + Vite + Tailwind
│   ├── src/test/           # Vitest + Testing Library unit tests
│   └── e2e/                # Playwright browser workflow tests
├── data/                   # Preset topology datasets (analyst-supplied vulnerabilities)
├── tests/                  # Backend test suite (pytest)
├── docs/                   # Documentation (model assumptions, provenance, report)
├── pyproject.toml
└── .env.example
```

---

## Bayesian pipeline

```
Import Topology
    ↓
Validate (DAG, cycle rejection, non-destructive warnings)
    ↓
Intrinsic Probability (logistic CVSS → prior + log-odds context)
    ↓
Propagation (Noisy-OR causal weights per relationship type)
    ↓
CPT Generation (Noisy-OR with leak = intrinsic probability)
    ↓
Evidence (analyst-assigned states, impossible-evidence detection)
    ↓
Inference (exact Variable Elimination)
    ↓
Posterior Probabilities
    ↓
Risk Index = Posterior × Impact (ranking measure)
    ↓
Risk Register (CSV) + Assessment Report (PDF) + sensitivity analysis
```

---

## Key features

- **Multi-format topology import**: JSON, YAML, CSV, Excel, GraphML,
  XML/AML, VSDX, VDX (native legacy `.vsd` is explicitly rejected with
  guidance).
- **Official CVSS v3.1 engine**: parses vectors and computes Base Scores with
  the FIRST specification equations; per-asset analyst-supplied vulnerability
  lists (CVE + vector + optional source attribution).
- **Three asset types**: Device, Human, Physical.
- **Explicit CVSS→probability model**: logistic mapping (default) with
  additive log-odds contextual adjustment; parameters `k` and `x0` are
  configurable and documented as expert defaults.
- **Defensible risk model**: `Risk Index = posterior probability × normalised
  impact (severity/10 × scope)`, clearly separated from probability.
- **Evidence-based analysis**: mark assets as Compromised / Safe / Unknown;
  impossible evidence returns a structured diagnostic.
- **DAG-directed attack paths**: follow the causal direction of the network.
- **Sensitivity analysis**: one-at-a-time perturbation of `k`, `x0`,
  propagation weights, exposure/patch multipliers, with effects on intrinsic
  probability, posterior, risk index and network-level risk.
- **Professional reports**: CSV risk register (BOM) and PDF assessment
  reports using the same thresholds as the API.
- **Stateless REST API**: FastAPI with optional API-key auth, rate limiting,
  upload limits, request-ID tracing.
- **Persistence**: SQLAlchemy (SQLite by default, PostgreSQL-ready) for
  settings and assessment history; the analysis pipeline degrades gracefully
  when the database is unavailable.

---

## Topology schema

A topology is a JSON object with two sections: `assets` maps an asset ID to
its attributes; `relationships` lists directed links between assets.

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
        {"cve_id": "CVE-2021-44228",
         "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
         "source": "NVD"}
      ]
    },
    "Operator-01": {"kind": "human", "role": "operator", "awareness": 0.4, "privilege": "standard"}
  },
  "relationships": [
    ["Operator-01", "PLC-01", "controls", false]
  ]
}
```

- Asset kinds: `device` (`vulnerabilities`, `cvss_type`, `exposed`,
  `patched`, `consequence_severity`), `human` (`role`, `awareness`,
  `privilege`, `consequence_severity`), `physical` (`p_base_override`,
  `consequence_severity`).
- A relationship is `[source, target, type, firewalled]` with `type` ∈
  {controls, monitors, actuates, connects-to, programs / operates}.
- Validation rejects out-of-range values, unknown assets/types, and cycles.
  Deterministic, safe normalisation (e.g. self-loop removal, duplicate-edge
  de-duplication) is performed **with an explicit warning** surfaced in the
  API response; nothing is silently dropped. Malformed records that could
  materially alter the risk model are **rejected**.
- CSV/Excel/GraphML/XML/AML/VSDX/VDX equivalents are converted into this
  normalized schema.

Each supported representation has distinct real-world semantics (native,
inventory, interchange, visualization/conversion) — they are **not** treated
as equivalent. See [`docs/topology-ingestion.md`](docs/topology-ingestion.md)
for the format-by-format assessment and the upload → review → analyze
workflow.

---

## Configuration

Copy `.env.example` to `.env` and customise:

```bash
ICS_DB_URL=sqlite:///backend/data/ICSRiskFramework.db
CORS_ORIGINS=http://localhost:5173
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
MAX_UPLOAD_SIZE_MB=10
ICS_API_KEY=your-secret-key-here   # Optional: enables API authentication
```

Runtime analysis parameters (CVSS mapping, logistic `k`/`x0`, exposure/patch
weights and multipliers, propagation weights, firewall multipliers, risk
thresholds) are configured through `GET/PUT /settings` and the Settings panel
in the frontend. The backend validates every value; the frontend displays the
active values from the backend and never hardcodes thresholds or CVSS
parameters.

---

## Scientific methodology

### Vulnerability data and CVSS

Each device asset may declare a list of vulnerabilities:
`{cve_id, vector, source}` where `vector` is a CVSS v3.1 string.
`backend/cvss.py` implements the official FIRST CVSS v3.1 Base Score
equations — Impact `= 6.42·ISS` (scope unchanged) /
`7.52·(ISS−0.029)−3.25·(ISS−0.02)¹⁵` (scope changed),
Exploitability `= 8.22·AV·AC·PR·UI`, Base
`= Roundup(min(Impact + Exploitability, 10))`.

**Vulnerability source strategy:** vulnerability data is **analyst-supplied**.
The framework does not retrieve data from NVD or any other external service.
CVE identifiers are validated syntactically and CVSS vectors are parsed and
scored locally. The `source` field is optional attribution metadata (e.g.
`"NVD"`, `"vendor advisory"`, `"internal pentest"`). The API, UI, README and
reports make no claim of automatic NVD retrieval.

The asset's effective score is the **maximum** over its vulnerabilities; the
legacy single-number `cvss_type` field remains supported as a shortcut.

### CVSS → prior mapping

CVSS Base Score is a severity metric (0–10), not a probability. Direct linear
scaling `P = CVSS/10` is statistically indefensible (it implies a CVSS-10
vulnerability guarantees compromise) and is only available as a deprecated
legacy option.

The default mapping is a logistic (sigmoid) model, declared explicitly as a
modelling assumption:

```
P₀ = 1 / (1 + exp(−k·(CVSS − x₀)))
```

with default `k = 0.8`, `x₀ = 5.0`:

| CVSS | P₀   |
| ---: | ---: |
| 0    | ≈ 0.02 |
| 5    | ≈ 0.50 |
| 10   | ≈ 0.98 |

Note that CVSS 0 does not yield P = 0: an asset with no known severe
vulnerability still carries residual compromise risk. The parameters are
**expert defaults (not empirically calibrated)** and are configurable via
Settings (`cvss_mapping`, `cvss_logistic_params`).

### Context-factor adjustment

Contextual factors are combined additively in log-odds (logit) space:

```
logit(P) = logit(P₀) + Σ wᵢ · log(Mᵢ)
```

where `Mᵢ` are the multipliers from `backend/config.py` (exposure, patch,
protocol, trust, MITRE technique) and `wᵢ` are user-configurable weights.
This is the standard formulation in logistic regression and Bayesian
calibration.

### Propagation and Noisy-OR

Each directed edge carries a **Noisy-OR causal weight `w`** — a modelling
parameter, **not** the literal conditional probability
`P(target=1 | source=1)`. For a single active parent:

```
P(target=1 | parent=1) = 1 − (1 − leak) · (1 − w)
```

where `leak` is the target's intrinsic probability. With multiple active
parents, CPT rows are generated by the closed form:

```
P(node=1 | S) = 1 − (1 − leak) · Π_{i ∈ S}(1 − wᵢ)
```

A firewalled link applies the configured firewall multiplier (default 0.30,
~70% reduction, literature-consistent with NIST SP 800-41).

### Bayesian inference

The DAG is turned into a pgmpy `DiscreteBayesianNetwork` with binary nodes
(0 = safe, 1 = compromised) and Noisy-OR CPTs. Posterior probabilities are
computed with **exact Variable Elimination**. Evidence is applied as certain
states; zero-probability (impossible) evidence is detected before inference
and returned as a structured `IMPOSSIBLE_EVIDENCE` error with the affected
nodes.

### Risk index

```
Impact     = (consequence_severity / 10) × scope_multiplier
Risk Index = P(Compromised | evidence) × Impact
```

The risk index is a **bounded analytical/ranking measure** (~[0, 1.4]). It is
**not**:

- a probability,
- an Annualised Loss Expectancy (ALE),
- an expected monetary loss,
- a universally standardised risk score.

Risk levels are derived from the **single configurable threshold set**
(`risk_thresholds`, defaults `critical ≥ 0.75`, `high ≥ 0.50`,
`moderate ≥ 0.25`, `low < 0.25`). The same thresholds drive the backend
classification, the PDF report colours, and the frontend dashboard. The
network-level risk is the worst-case single-asset risk index; mean, median
and per-level counts are also reported.

### Attack path scoring

Paths follow the DAG direction (parent → child). Scoring uses Bayesian
posterior probabilities:

```
path_score = min(P(nodeᵢ=1 | evidence)) × target_risk_index
```

The minimum posterior represents the "weakest link". An alternative product
model is available via `ATTACK_PATH_SCORING=product`. A path is a modelled
route for investigation prioritisation; it is not proof of a real intrusion.

---

## Testing

### Backend

```bash
python -m pytest tests/ -q          # 221 tests
ruff check .                        # lint
mypy backend/ --ignore-missing-imports   # type check (must pass in CI)
```

The suite covers CVSS correctness, probability, propagation, Noisy-OR CPTs,
inference, evidence (including impossible-evidence diagnostics), risk and
dynamic thresholds, topology validation (non-destructive warnings), all import
formats, upload security, sensitivity analysis, performance benchmarks
(10/25/50/100 nodes), database-failure behaviour, persistence, reports, and
API-level end-to-end flows.

### Frontend unit tests

```bash
cd frontend
npm test        # Vitest + Testing Library (settings, evidence, risk, topology, results)
```

### Browser E2E

```bash
cd frontend
npx playwright install chromium
npx playwright test   # full browser workflow: upload → validate → assess → evidence → rerun → export
```

The Playwright test drives a real Chromium browser through the complete user
workflow: load a preset, run the assessment, inspect the network and metrics,
apply evidence, rerun inference, verify posterior/risk changes, and download
the risk register.

CI (`.github/workflows/ci.yml`) runs backend tests + lint + type check,
frontend unit tests + production build, and the Playwright E2E suite.

---

## Docker

```bash
docker compose up --build
```

Serves the frontend (nginx) → API → database stack. Health checks are
configured for the API and database services. Environment-driven
configuration replaces any development credentials; no secrets are committed.
See `Dockerfile`, `frontend/Dockerfile`, `frontend/.nginx.conf`, and
`docker-compose.yml`.

---

## Security

- Uploaded files: extension allow-list, size limits, zip-expansion limits,
  XML entity protection, safe temp-file handling, path-traversal defence.
- Optional API-key authentication, rate limiting, request-ID tracing.
- Structured error responses: no raw tracebacks are ever leaked to clients.
- Dependency audits (pip-audit / npm audit) should be run before releases;
  the repository documents findings in `ENGINEERING_AUDIT_REPORT.md`.

---

## Limitations

1. **No empirical calibration.** All parameters are expert judgments,
   literature-consistent defaults, or framework defaults. Organisations must
   calibrate against their own incident data.
2. **No live NVD retrieval.** Vulnerability data is analyst-supplied.
3. **Exact inference** may not scale to very large or high-treewidth
   networks; see `tests/test_performance.py` for measured timings.
4. **Binary node states only**; no continuous or multi-state assets.
5. **Evidence is certain**; uncertain or partial evidence is not modelled.
6. **Noisy-OR leak equals the intrinsic probability**; residual common-cause
   risk is not separately parameterised.
7. **The risk index is a ranking measure**, not expected loss.
8. **No monetary valuation** is modelled or reported.

See [`docs/model-assumptions.md`](docs/model-assumptions.md) for the complete
assumptions statement and
[`docs/parameter-provenance.md`](docs/parameter-provenance.md) for the full
parameter table.

---

## References

- Pearl, J. (1988). *Probabilistic Reasoning in Intelligent Systems.*
- Fenton, N. E., & Neil, M. (2012). *Risk Assessment and Decision Analysis with Bayesian Networks.* CRC Press.
- FIRST (2019). *CVSS v3.1 User Guide.* https://www.first.org/cvss/user-guide
- NIST SP 800-30 Rev. 1 — *Guide for Conducting Risk Assessments.*
- NIST SP 800-41 — *Guidelines on Firewalls and Firewall Policy.*
- NIST SP 800-82 Rev. 3 — *Guide to ICS Security.*
- IEC 62443-3-3 — *Industrial communication networks — Network and system security.*

## License

MIT License. See `LICENSE` for details.
