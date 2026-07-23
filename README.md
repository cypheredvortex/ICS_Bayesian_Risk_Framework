# ICS Risk Assessment Framework

A **Generic Bayesian Network-Based Framework for Quantitative Risk Assessment of Industrial Control Systems (ICS)**.

## Overview

This framework provides a complete pipeline for quantitative cyber-risk assessment of ICS environments:

1. **Topology Import** - Load ICS topology from JSON, YAML, or CSV
2. **Bayesian Network Construction** - Build DAG from ICS asset relationships
3. **Intrinsic Probability** - Compute base compromise probabilities per asset type
4. **CPT Generation** - Generate Conditional Probability Tables via noisy-OR
5. **Inference** - Exact inference using Variable Elimination
6. **Risk Scoring** - Compute and rank asset risk scores
7. **Attack Path Analysis** - Identify high-risk propagation paths
8. **Visualization** - Generate graph diagrams and charts
9. **Reporting** - Export risk registers (CSV) and assessment reports (PDF)

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd ICS_Bayesian_Risk_Framework

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install Python dependencies
pip install -e .

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### CLI Usage

```bash
# Run assessment with default topology
python -m ics_risk_framework

# Run with specific topology and evidence
python -m ics_risk_framework --topology data/swat_example.json --evidence corp_net=1 --evidence hmi=1

# Run API server
ics-risk-api
# or: python -m uvicorn src.ics_risk_framework.api:app --reload
```

### API Usage

```bash
# Start the API server
ics-risk-api

# In another terminal, run an assessment
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "topology": <topology-json>,
    "evidence": [{"asset": "corp_net", "state": "Compromised"}]
  }'
```

### Frontend

```bash
cd frontend
npm run dev
```

The frontend runs on `http://localhost:5173` and proxies API requests to `http://localhost:8000`.

## Project Structure

```
ICS_Bayesian_Risk_Framework/
├── src/
│   └── ics_risk_framework/     # Python package
│       ├── __init__.py          # Public API exports
│       ├── __main__.py          # `python -m` entry point
│       ├── cli.py               # CLI interface
│       ├── api.py               # FastAPI REST API
│       ├── api_adapter.py       # HTTP-to-framework adapter
│       ├── schemas.py           # Pydantic request/response models
│       ├── config.py            # Constants and lookup tables
│       ├── settings.py          # Runtime-configurable settings
│       ├── assets.py            # Topology loading/validation
│       ├── probability.py       # Base probability computation
│       ├── graph_builder.py     # Bayesian network construction
│       ├── cpt_generator.py     # Noisy-OR CPT generation
│       ├── inference.py         # Variable Elimination inference
│       ├── risk.py              # Risk scoring and ranking
│       ├── attack_paths.py      # Attack path analysis
│       ├── outputs.py           # File writers (JSON, PNG, TXT)
│       └── database/            # Persistence layer
│           ├── config.py        # SQLAlchemy engine/session
│           ├── models.py        # ORM models
│           ├── repositories.py  # Repository pattern
│           └── services.py      # Assessment persistence service
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main React application
│   │   ├── main.tsx             # React entry point
│   │   └── styles.css           # Tailwind CSS styles
│   ├── index.html
│   ├── vite.config.ts
│   ├── package.json
│   └── tailwind.config.js
├── data/                        # Preset topology datasets
├── docs/                        # Documentation
├── tests/                       # Test suite
├── output/                      # Generated artifacts (gitignored)
├── alembic/                     # Database migrations
├── pyproject.toml               # Python project configuration
└── .env.example                 # Environment variable template
```

## Bayesian Pipeline

```
Import Topology (JSON/YAML/CSV)
       ↓
Graph Construction (DAG from asset relationships)
       ↓
Intrinsic Probability (per asset, Phase 3A)
       ↓
Propagation Probability (edge weights, Phase 2)
       ↓
CPT Generation (Noisy-OR, Phase 3B)
       ↓
Inference (Variable Elimination, Phase 4)
       ↓
Posterior Probabilities
       ↓
Risk Computation (Phase 5)
       ↓
Risk Table → Risk Register (CSV)
       ↓
Attack Path Analysis
       ↓
Visualization → Graph (PNG/JSON)
       ↓
Report Generation → Assessment Report (PDF)
```

## Key Features

- **Multi-format topology import**: JSON, YAML, CSV
- **Three asset types**: Device, Human, Physical
- **Configurable risk weights**: CVSS, exposure, patch, impact
- **Evidence-based analysis**: Mark assets as compromised/safe
- **Attack path analysis**: BFS-based path finding with geometric mean scoring
- **Professional reports**: CSV risk register with BOM, PDF assessment reports
- **REST API**: FastAPI with CORS support for web frontends
- **Database persistence**: SQLAlchemy with SQLite (PostgreSQL-ready)

## Configuration

Copy `.env.example` to `.env` and customize:

```bash
ICS_DB_URL=sqlite:///backend/data/ICSRiskFramework.db
CORS_ORIGINS=http://localhost:5173
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
MAX_UPLOAD_SIZE_MB=10
```

## License

MIT License. See LICENSE file for details.

