ICS Bayesian Risk Framework
A Generic Bayesian Network-Based Framework for Quantitative Risk Assessment of Industrial Control Systems (ICS).
Overview
This framework provides a complete pipeline for quantitative cyber-risk assessment of ICS environments:
Topology Import — Load ICS topology from JSON, YAML, CSV, Excel, GraphML, XML/AML, or VSDX
Bayesian Network Construction — Build DAG from ICS asset relationships
Intrinsic Probability — Compute base compromise probabilities per asset type
CPT Generation — Generate Conditional Probability Tables via Noisy-OR
Inference — Exact inference using Variable Elimination
Risk Scoring — Compute and rank asset risk indices
Attack Path Analysis — Identify high-risk propagation paths (DAG-directed)
Visualization — Generate graph diagrams and charts
Reporting — Export risk registers (CSV) and assessment reports (PDF)
Quick Start
Prerequisites
Python 3.11+
Node.js 18+ (for frontend)
Installation
bash
# Clone the repository
git clone https://github.com/cypheredvortex/ICS_Bayesian_Risk_Framework.git
cd ICS_Bayesian_Risk_Framework

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate    # Windows

# Install Python dependencies
pip install -e .

# Install frontend dependencies
cd frontend
npm install
cd ..
CLI Usage
bash
# Run assessment with default topology
ics-risk

# Run with specific topology and evidence
ics-risk --topology data/swat_example.json --evidence corp_net=1

# Run API server
ics-risk-api
API Usage
bash
# Start the API server
ics-risk-api

# In another terminal, run an assessment
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "topology": {"assets": {...}, "relationships": [...]},
    "evidence": [{"asset": "corp_net", "state": "Compromised"}]
  }'
Frontend
bash
cd frontend
npm run dev
The frontend runs on http://localhost:5173 and proxies API requests to http://localhost:8000.
Project Structure
plain
ICS_Bayesian_Risk_Framework/
├── backend/                 # Python package
│   ├── api.py              # FastAPI REST API
│   ├── cli.py              # CLI interface
│   ├── probability.py      # Base probability (logistic CVSS mapping)
│   ├── cpt_generator.py    # Noisy-OR CPT generation
│   ├── inference.py        # Variable Elimination
│   ├── risk.py             # Risk index computation
│   ├── attack_paths.py     # DAG-directed attack path analysis
│   └── database/           # SQLAlchemy persistence
├── frontend/               # React + Vite + Tailwind
├── data/                   # Preset topology datasets
├── tests/                  # Test suite
├── docs/                   # Documentation
├── pyproject.toml
└── .env.example
Bayesian Pipeline
plain
Import Topology
    ↓
Validate DAG (cycle rejection)
    ↓
Intrinsic Probability (logistic CVSS → prior)
    ↓
Propagation Probability (edge weights)
    ↓
CPT Generation (Noisy-OR with leak probability)
    ↓
Inference (Variable Elimination)
    ↓
Posterior Probabilities
    ↓
Risk Index = Posterior × Impact
    ↓
Risk Register (CSV) + Assessment Report (PDF)
Key Features
Multi-format topology import: JSON, YAML, CSV, Excel, GraphML, XML/AML, VSDX
Three asset types: Device, Human, Physical
Calibrated base probabilities: Logistic CVSS mapping with additive log-odds context adjustment
Configurable risk weights: CVSS, exposure, patch, impact, propagation, firewall
Evidence-based analysis: Mark assets as compromised/safe
DAG-directed attack paths: Follows causal direction of the Bayesian network
Professional reports: CSV risk register with BOM, PDF assessment reports
Stateless REST API: FastAPI with optional API-key auth
Database persistence: SQLAlchemy with SQLite (PostgreSQL-ready)
Configuration
Copy .env.example to .env and customize:
bash
ICS_DB_URL=sqlite:///backend/data/ICSRiskFramework.db
CORS_ORIGINS=http://localhost:5173
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
MAX_UPLOAD_SIZE_MB=10
ICS_API_KEY=your-secret-key-here   # Optional: enables API authentication
Scientific Methodology
CVSS-to-Prior Mapping
CVSS Base Score is a severity metric (0–10), not a probability. Direct linear scaling P = CVSS/10 is statistically indefensible because it implies a CVSS-10 vulnerability guarantees compromise (P=1.0).
We use a calibrated logistic (sigmoid) mapping:
plain
P₀ = 1 / (1 + exp(−k·(CVSS − x₀)))
with default k=0.8, x₀=5.0. This produces:
CVSS 0  → P ≈ 0.02
CVSS 5  → P ≈ 0.50
CVSS 10 → P ≈ 0.98
Parameters are user-configurable via settings.
Context-Factor Adjustment
Rather than multiply odds by arbitrary constants raised to arbitrary exponents, we use an additive log-odds (logit) model:
plain
logit(P) = logit(P₀) + Σ wᵢ · log(Mᵢ)
where Mᵢ are the multipliers from config.py and wᵢ are user-configurable weights. This is the standard formulation in logistic regression and Bayesian calibration.
Risk Index
The quantity computed is a relative risk index, not an absolute quantitative risk measure (e.g. Annual Loss Expectancy). It is designed for ranking assets so analysts can prioritise investigation and mitigation.
plain
Risk Index = P(Compromised | evidence) × Impact
Default thresholds are calibration placeholders:
Critical ≥ 1.50
High ≥ 0.80
Moderate ≥ 0.30
Low < 0.30
Organisations should tune these against their own risk appetite and historical incident data.
Attack Path Scoring
Paths follow the DAG direction (parent → child). Scoring uses Bayesian posterior probabilities:
plain
path_score = min(P(nodeᵢ=1 | evidence)) × target_risk_index
The minimum posterior represents the "weakest link". Alternative product model available via ATTACK_PATH_SCORING=product.
References
Pearl, J. (1988). Probabilistic Reasoning in Intelligent Systems.
Fenton, N. E., & Neil, M. (2012). Risk Assessment and Decision Analysis with Bayesian Networks. CRC Press.
FIRST (2019). CVSS v3.1 User Guide. https://www.first.org/cvss/user-guide
NIST SP 800-30 Rev. 1 — Guide for Conducting Risk Assessments.
IEC 62443-3-3 — Industrial communication networks — Network and system security.
License
MIT License. See LICENSE file for details.