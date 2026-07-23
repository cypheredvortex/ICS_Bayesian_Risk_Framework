"""
FastAPI application for the ICS Risk Assessment Framework.

Production-hardened API with:
- Rate limiting
- Request ID tracing
- Structured error responses
- Pydantic response models
- Configurable CORS, upload limits
- Professional PDF report generation via reportlab
"""

import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text as sa_text

from backend.assets import load_topology, load_topology_from_bytes
from backend.api_adapter import analyze, OUTPUT_DIR
from backend.database.config import initialize_database, get_db_url, get_session_factory
from backend.logging_config import configure_logging, get_request_id, set_request_id
from backend.pdf_reports import generate_pdf_report
from backend.schemas import (
    AnalyzeRequest,
    DatasetInfo,
    ErrorResponse,
    HealthCheckResponse,
    SettingsUpdateRequest,
    TopologyUploadRequest,
    UploadTopologyFileResponse,
    UploadTopologyResponse,
)
from backend.settings import get_settings, reset_settings, update_settings

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_FILES: dict[str, Path] = {
    "risk_table.csv": OUTPUT_DIR / "risk_table.csv",
    "assessment.pdf": OUTPUT_DIR / "assessment.pdf",
}
DATASET_FILES: dict[str, Path] = {
    "swat_example": DATA_DIR / "swat_example.json",
    "building_automation": DATA_DIR / "building_automation.json",
    "power_substation": DATA_DIR / "power_substation.json",
    "water_treatment": DATA_DIR / "water_treatment.json",
}

# ---- Configuration from environment ----
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
API_VERSION = "1.0.0"
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

# Validate dataset names to prevent path traversal
_VALID_DATASET_NAMES = set(DATASET_FILES.keys())
_VALID_REPORT_NAMES = set(REPORT_FILES.keys())

# ---- Rate limiter ----
limiter = Limiter(key_func=get_remote_address)


def _sanitize_dataset_name(name: str) -> str:
    """Validate dataset name against known datasets to prevent path traversal."""
    if name not in _VALID_DATASET_NAMES:
        raise HTTPException(status_code=404, detail=f"Dataset '{name}' does not exist.")
    return name


def _sanitize_report_name(name: str) -> str:
    """Validate report file name against known reports."""
    if name not in _VALID_REPORT_NAMES:
        raise HTTPException(status_code=404, detail=f"Report '{name}' does not exist.")
    return name


# ---- Request ID middleware ----
async def _request_id_middleware(request: Request, call_next: Any) -> Any:
    """Inject a unique request ID for tracing."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    set_request_id(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: configure logging, initialize DB."""
    configure_logging()
    logger.info("Starting ICS Risk Assessment Framework API v%s", API_VERSION)
    logger.info("CORS origins: %s", CORS_ORIGINS)
    logger.info("Max upload size: %d MB", MAX_UPLOAD_SIZE_MB)
    logger.info("Rate limit: %d requests/minute", RATE_LIMIT_PER_MINUTE)
    logger.info("Database URL: %s", get_db_url())
    initialize_database()
    app.state.latest_result: dict[str, Any] = {}
    app.state.uploaded_topology: dict[str, Any] | None = None
    yield
    logger.info("Shutting down ICS Risk Assessment Framework API")


app = FastAPI(
    title="ICS Risk Assessment Framework",
    description="Bayesian Network-based quantitative risk assessment for Industrial Control Systems. "
    "Upload a topology, optionally provide evidence, and receive risk scores, attack paths, and reports.",
    version=API_VERSION,
    lifespan=lifespan,
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    contact={
        "name": "ICS Risk Framework Team",
        "url": "https://github.com/your-org/ics-risk-framework",
    },
    openapi_tags=[
        {"name": "Assessments", "description": "Run risk assessments and view results"},
        {"name": "Topologies", "description": "Upload and manage topology data"},
        {"name": "Settings", "description": "Configure runtime analysis parameters"},
        {"name": "Datasets", "description": "Pre-loaded topology datasets"},
        {"name": "Reports", "description": "Download assessment reports"},
        {"name": "System", "description": "Health check and system information"},
    ],
)

# ---- Middleware ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(_request_id_middleware)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ---- Exception handlers ----
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Return structured error responses for HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=exc.detail,
            error_code=f"HTTP_{exc.status_code}",
            request_id=get_request_id(),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all exception handler for unhandled errors."""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            detail="An internal error occurred. Please try again later.",
            error_code="INTERNAL_ERROR",
            request_id=get_request_id(),
        ).model_dump(),
    )


# ---- Endpoints ----

@app.get("/", response_model=HealthCheckResponse, tags=["System"])
def healthcheck():
    """Comprehensive health check with version, DB status, and endpoint info."""
    db_status = "unknown"
    try:
        factory = get_session_factory()
        session = factory()
        session.execute(sa_text("select 1"))
        session.close()
        db_status = "connected"
    except Exception as exc:
        db_status = f"error: {exc}"

    routes = sorted(
        [
            {"path": route.path, "methods": list(route.methods - {"HEAD", "OPTIONS"})}
            for route in app.routes
            if hasattr(route, "path") and route.path.startswith("/")
        ],
        key=lambda r: r["path"],
    )

    return HealthCheckResponse(
        status="ok",
        framework="ICS Risk Assessment Framework",
        version=API_VERSION,
        database=db_status,
        max_upload_size_mb=MAX_UPLOAD_SIZE_MB,
        endpoints=routes,
    )


@app.post(
    "/upload-topology",
    response_model=UploadTopologyResponse,
    tags=["Topologies"],
    summary="Upload topology as JSON payload",
)
@limiter.limit(f"{RATE_LIMIT_PER_MINUTE}/minute")
def upload_topology(request: Request, payload: TopologyUploadRequest):
    """Validate and store a topology payload for the session."""
    try:
        assets, relationships = load_topology(payload.topology)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    app.state.uploaded_topology = {
        "assets": assets,
        "relationships": [list(rel) for rel in relationships],
    }
    return UploadTopologyResponse(
        message="Topology uploaded successfully",
        asset_count=len(assets),
        relationship_count=len(relationships),
    )


@app.post(
    "/upload-topology-file",
    response_model=UploadTopologyFileResponse,
    tags=["Topologies"],
    summary="Upload topology from file (JSON, YAML, or CSV)",
)
@limiter.limit(f"{RATE_LIMIT_PER_MINUTE}/minute")
async def upload_topology_file(request: Request, file: UploadFile = File(...)):
    """Upload topology from JSON, YAML, or CSV file.

    Supported formats: .json, .yaml, .yml, .csv
    Maximum file size: {MAX_UPLOAD_SIZE_MB} MB
    """
    if file.size is not None and file.size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_SIZE_MB} MB.",
        )
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_SIZE_MB} MB.",
        )
    try:
        assets, relationships = load_topology_from_bytes(content, file.filename or "topology.json")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc

    topology = {
        "assets": assets,
        "relationships": [list(rel) for rel in relationships],
    }
    app.state.uploaded_topology = topology
    return UploadTopologyFileResponse(
        message=f"Topology file '{file.filename}' uploaded successfully",
        asset_count=len(assets),
        relationship_count=len(relationships),
        topology=topology,
    )


@app.post("/analyze", tags=["Assessments"], summary="Run a full Bayesian risk assessment")
@limiter.limit(f"{RATE_LIMIT_PER_MINUTE}/minute")
def analyze_endpoint(request: Request, payload: AnalyzeRequest):
    """Run the framework and regenerate all report artifacts.

    Accepts a topology and optional evidence, runs the full Bayesian pipeline,
    and returns structured results including risk scores, attack paths, and CPTs.
    """
    topology = payload.topology
    if not topology:
        raise HTTPException(status_code=400, detail="Topology payload is required.")
    try:
        result = analyze(
            topology,
            [entry.model_dump() for entry in payload.evidence],
            write_outputs=True,
            output_dir=OUTPUT_DIR,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Assessment execution failed: {exc}") from exc

    # Generate professional PDF report using reportlab
    try:
        generate_pdf_report(result, REPORT_FILES["assessment.pdf"])
    except Exception as exc:
        logger.warning("PDF reportlab generation failed: %s", exc)

    app.state.latest_result = result
    return result


@app.get("/settings", tags=["Settings"], summary="Get current runtime settings")
def read_settings():
    """Retrieve the current runtime settings with overrides."""
    return get_settings()


@app.put("/settings", tags=["Settings"], summary="Update runtime settings")
def write_settings(payload: SettingsUpdateRequest):
    """Update runtime settings. Validates all values before applying."""
    try:
        updated = update_settings(payload.settings)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return updated


@app.post("/settings/reset", tags=["Settings"], summary="Reset settings to defaults")
def reset_settings_endpoint():
    """Reset all runtime settings to framework defaults."""
    return reset_settings()


@app.get("/results", tags=["Assessments"], summary="Get latest assessment results")
def get_results():
    """Retrieve the latest assessment results."""
    return app.state.latest_result or {"message": "No analysis has been run yet."}


@app.get("/graph", tags=["Assessments"], summary="Get Bayesian network graph")
def get_graph():
    """Get the Bayesian network graph from the latest assessment."""
    if not app.state.latest_result:
        return {"nodes": [], "edges": []}
    return app.state.latest_result.get("graph", {"nodes": [], "edges": []})


@app.get("/datasets", response_model=DatasetInfo, tags=["Datasets"], summary="List available datasets")
def get_datasets():
    """List all available pre-loaded topology datasets."""
    return DatasetInfo(
        datasets=sorted(DATASET_FILES.keys()),
        paths={name: f"/datasets/{name}" for name in DATASET_FILES},
    )


@app.get("/datasets/{dataset_name}", tags=["Datasets"], summary="Download a dataset")
def get_dataset(dataset_name: str):
    """Download a pre-loaded topology dataset by name."""
    sanitized = _sanitize_dataset_name(dataset_name)
    file_path = DATASET_FILES[sanitized]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Requested dataset does not exist.")
    return FileResponse(file_path, media_type="application/json", filename=file_path.name)


@app.get("/reports", tags=["Reports"], summary="List available reports")
def get_reports():
    """List available downloadable report artifacts."""
    return {
        "risk_table": "/reports/risk_table.csv",
        "assessment_pdf": "/reports/assessment.pdf",
    }


@app.get("/reports/{report_name}", tags=["Reports"], summary="Download a report")
def download_report(report_name: str):
    """Download a generated report (risk table CSV or assessment PDF)."""
    sanitized = _sanitize_report_name(report_name)
    file_path = REPORT_FILES[sanitized]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Requested report does not exist.")

    media_type = {
        "risk_table.csv": "text/csv",
        "assessment.pdf": "application/pdf",
    }.get(report_name, "application/octet-stream")

    return FileResponse(file_path, media_type=media_type, filename=file_path.name)


def run_api() -> None:
    """Run the API server via uvicorn (used by `ics-risk-api` console_scripts entry point)."""
    import uvicorn
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(
        "backend.api:app",
        host=host,
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )

