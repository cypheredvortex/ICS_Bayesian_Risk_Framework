from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.app.framework_adapter import analyze
from backend.app.schemas import AnalyzeRequest, TopologyUploadRequest

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"
REPORT_FILES = {
    "summary.txt": OUTPUT_DIR / "summary.txt",
    "risk_table.csv": OUTPUT_DIR / "risk_table.csv",
    "metrics.json": OUTPUT_DIR / "metrics.json",
    "posteriors.json": OUTPUT_DIR / "posteriors.json",
    "assessment.pdf": OUTPUT_DIR / "assessment.pdf",
}


def _build_pdf_bytes(summary: str, metrics: dict[str, Any] | None = None, posteriors: dict[str, Any] | None = None) -> bytes:
    lines = [
        "ICS Bayesian Risk Assessment Report",
        "=" * 38,
        summary.strip()[:600],
    ]
    if metrics:
        lines.append(f"Asset count: {metrics.get('asset_count', 'n/a')}")
        lines.append(f"Relationship count: {metrics.get('relationship_count', 'n/a')}")
        lines.append(f"Risk row count: {metrics.get('risk_row_count', 'n/a')}")
    if posteriors:
        lines.append("Posterior probabilities:")
        for asset, value in posteriors.items():
            lines.append(f"- {asset}: {value}")

    text = "\n".join(lines)
    escaped = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    content = f"BT /F1 12 Tf 50 770 Td ({escaped}) Tj ET"
    header = b"%PDF-1.4\n"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length 71 >>\nstream\n" + content.encode("latin-1") + b"\nendstream",
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
    pdf_parts.append(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode("latin-1"))
    return b"".join(pdf_parts)


def _ensure_pdf_report() -> None:
    file_path = REPORT_FILES["assessment.pdf"]
    if file_path.exists():
        return

    summary = (OUTPUT_DIR / "summary.txt").read_text(encoding="utf-8") if (OUTPUT_DIR / "summary.txt").exists() else "No summary report available yet."
    metrics = {}
    if (OUTPUT_DIR / "metrics.json").exists():
        with (OUTPUT_DIR / "metrics.json").open(encoding="utf-8") as handle:
            metrics = json.load(handle)
    posteriors = {}
    if (OUTPUT_DIR / "posteriors.json").exists():
        with (OUTPUT_DIR / "posteriors.json").open(encoding="utf-8") as handle:
            posteriors = json.load(handle)

    file_path.write_bytes(_build_pdf_bytes(summary=summary, metrics=metrics, posteriors=posteriors))


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
    """Store a validated topology payload for the session."""
    try:
        assets = payload.topology.get("assets", {})
        relationships = payload.topology.get("relationships", [])
        if not isinstance(assets, dict) or not isinstance(relationships, list):
            raise ValueError("Topology must contain 'assets' and 'relationships'.")
    except Exception as exc:  # pragma: no cover - validation guard
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    app.state.uploaded_topology = payload.topology
    return {
        "message": "Topology uploaded successfully",
        "asset_count": len(assets),
        "relationship_count": len(relationships),
    }


@app.post("/analyze")
def analyze_endpoint(payload: AnalyzeRequest):
    """Run the existing framework and return the structured analysis result."""
    topology = payload.topology
    if not topology:
        raise HTTPException(status_code=400, detail="Topology payload is required.")

    try:
        result = analyze(topology, [entry.model_dump() for entry in payload.evidence])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Assessment execution failed: {exc}") from exc

    app.state.latest_result = result
    _ensure_pdf_report()
    return result


@app.get("/results")
def get_results():
    return app.state.latest_result or {"message": "No analysis has been run yet."}


@app.get("/graph")
def get_graph():
    if not app.state.latest_result:
        return {"nodes": [], "edges": []}
    return app.state.latest_result.get("graph", {"nodes": [], "edges": []})


@app.get("/reports")
def get_reports():
    return {
        "summary": "/reports/summary.txt",
        "risk_table": "/reports/risk_table.csv",
        "metrics": "/reports/metrics.json",
        "posteriors": "/reports/posteriors.json",
    }


@app.get("/reports/{report_name}")
def download_report(report_name: str):
    if report_name == "assessment.pdf":
        _ensure_pdf_report()

    file_path = REPORT_FILES.get(report_name)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Requested report does not exist.")

    media_type = {
        "summary.txt": "text/plain",
        "risk_table.csv": "text/csv",
        "metrics.json": "application/json",
        "posteriors.json": "application/json",
        "assessment.pdf": "application/pdf",
    }.get(report_name, "application/octet-stream")

    return FileResponse(file_path, media_type=media_type, filename=file_path.name)


@app.get("/")
def healthcheck():
    return {"status": "ok", "framework": "ICS Risk Assessment Framework"}
