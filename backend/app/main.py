from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
import json

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from assets import load_topology, load_topology_from_bytes
from backend.app.framework_adapter import analyze, OUTPUT_DIR
from backend.app.schemas import AnalyzeRequest, SettingsUpdateRequest, TopologyUploadRequest
from settings import get_settings, reset_settings, update_settings

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
REPORT_FILES = {
    "summary.txt": OUTPUT_DIR / "summary.txt",
    "risk_table.csv": OUTPUT_DIR / "risk_table.csv",
    "metrics.json": OUTPUT_DIR / "metrics.json",
    "posteriors.json": OUTPUT_DIR / "posteriors.json",
    "graph.json": OUTPUT_DIR / "graph.json",
    "graph.png": OUTPUT_DIR / "graph.png",
    "cpts.json": OUTPUT_DIR / "cpts.json",
    "assessment.pdf": OUTPUT_DIR / "assessment.pdf",
}
DATASET_FILES = {
    "swat_example": DATA_DIR / "swat_example.json",
    "building_automation": DATA_DIR / "building_automation.json",
    "power_substation": DATA_DIR / "power_substation.json",
    "water_treatment": DATA_DIR / "water_treatment.json",
}


def _build_pdf_bytes(result: dict[str, Any] | None = None) -> bytes:
    summary = result.get("summary", {}) if result else {}
    posteriors = result.get("posteriors", {}) if result else {}
    risk_scores = result.get("risk_scores", []) if result else []
    attack_paths = result.get("attack_paths", []) if result else []

    lines = [
        "ICS Bayesian Risk Assessment Report",
        "=" * 42,
        f"Overall risk: {summary.get('overall_risk', 'n/a')}",
        f"Risk level: {summary.get('risk_level', 'n/a')}",
        f"Assets: {summary.get('asset_count', 'n/a')}",
        f"Relationships: {summary.get('relationship_count', 'n/a')}",
        f"Evidence used: {summary.get('evidence_used', {})}",
        "",
        "Top risk assets:",
    ]
    for row in risk_scores[:5]:
        lines.append(
            f"- {row.get('asset')}: risk={row.get('risk')} "
            f"P={row.get('P(compromised|evidence)')}"
        )

    lines.append("")
    lines.append("Posterior probabilities:")
    for asset, value in list(posteriors.items())[:12]:
        lines.append(f"- {asset}: {round(float(value), 4)}")

    if attack_paths:
        lines.append("")
        lines.append("Critical attack path:")
        path = attack_paths[0]
        lines.append(" -> ".join(path.get("path", [])))
        lines.append(f"Score: {path.get('score')}")

    text = "\n".join(lines)[:3500]
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = f"BT /F1 11 Tf 40 780 Td ({escaped}) Tj ET"
    header = b"%PDF-1.4\n"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content) + 20} >>\nstream\n{content}\nendstream".encode("latin-1"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf_parts = [header]
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(b"".join(pdf_parts)))
        pdf_parts.append(f"{index} 0 obj\n".encode("latin-1"))
        pdf_parts.append(obj + b"\nendobj\n")
    xref_start = len(b"".join(pdf_parts))
    pdf_parts.append(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf_parts.append(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf_parts.append(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf_parts.append(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode(
            "latin-1"
        )
    )
    return b"".join(pdf_parts)


def _write_pdf_report(result: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FILES["assessment.pdf"].write_bytes(_build_pdf_bytes(result))


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.latest_result: dict[str, Any] = {}
    app.state.uploaded_topology: dict[str, Any] | None = None
    yield


app = FastAPI(title="ICS Risk Assessment Framework", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/upload-topology")
def upload_topology(payload: TopologyUploadRequest):
    """Validate and store a topology payload for the session."""
    try:
        assets, relationships = load_topology(payload.topology)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    app.state.uploaded_topology = {
        "assets": assets,
        "relationships": [list(rel) for rel in relationships],
    }
    return {
        "message": "Topology uploaded successfully",
        "asset_count": len(assets),
        "relationship_count": len(relationships),
    }


@app.post("/upload-topology-file")
async def upload_topology_file(file: UploadFile = File(...)):
    """Upload topology from JSON, YAML, or CSV."""
    content = await file.read()
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
    return {
        "message": f"Topology file '{file.filename}' uploaded successfully",
        "asset_count": len(assets),
        "relationship_count": len(relationships),
        "topology": topology,
    }


@app.post("/analyze")
def analyze_endpoint(payload: AnalyzeRequest):
    """Run the framework and regenerate all report artifacts."""
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

    _write_pdf_report(result)
    app.state.latest_result = result
    return result


@app.get("/settings")
def read_settings():
    return get_settings()


@app.put("/settings")
def write_settings(payload: SettingsUpdateRequest):
    try:
        updated = update_settings(payload.settings)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return updated


@app.post("/settings/reset")
def reset_settings_endpoint():
    return reset_settings()


@app.get("/results")
def get_results():
    return app.state.latest_result or {"message": "No analysis has been run yet."}


@app.get("/graph")
def get_graph():
    if not app.state.latest_result:
        return {"nodes": [], "edges": []}
    return app.state.latest_result.get("graph", {"nodes": [], "edges": []})


@app.get("/datasets")
def get_datasets():
    return {
        "datasets": sorted(DATASET_FILES.keys()),
        "paths": {name: f"/datasets/{name}" for name in DATASET_FILES},
    }


@app.get("/datasets/{dataset_name}")
def get_dataset(dataset_name: str):
    file_path = DATASET_FILES.get(dataset_name)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Requested dataset does not exist.")
    return FileResponse(file_path, media_type="application/json", filename=file_path.name)


@app.get("/reports")
def get_reports():
    return {
        "summary": "/reports/summary.txt",
        "risk_table": "/reports/risk_table.csv",
        "metrics": "/reports/metrics.json",
        "posteriors": "/reports/posteriors.json",
        "graph": "/reports/graph.json",
        "graph_image": "/reports/graph.png",
        "cpts": "/reports/cpts.json",
        "assessment_pdf": "/reports/assessment.pdf",
    }


@app.get("/reports/{report_name}")
def download_report(report_name: str):
    file_path = REPORT_FILES.get(report_name)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Requested report does not exist. Run an assessment first.")

    media_type = {
        "summary.txt": "text/plain",
        "risk_table.csv": "text/csv",
        "metrics.json": "application/json",
        "posteriors.json": "application/json",
        "graph.json": "application/json",
        "cpts.json": "application/json",
        "graph.png": "image/png",
        "assessment.pdf": "application/pdf",
    }.get(report_name, "application/octet-stream")

    return FileResponse(file_path, media_type=media_type, filename=file_path.name)


@app.get("/")
def healthcheck():
    return {"status": "ok", "framework": "ICS Risk Assessment Framework"}
