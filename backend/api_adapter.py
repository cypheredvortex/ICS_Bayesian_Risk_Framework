"""Adapter that translates HTTP input into the existing framework call."""
from pathlib import Path
from typing import Any

from backend.cli import run as run_framework

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"


def analyze(
    topology: dict[str, Any],
    evidence: list[dict[str, Any]] | None = None,
    write_outputs: bool = True,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Translate HTTP input into the framework call."""
    evidence_map: dict[str, int] = {}
    for item in evidence or []:
        asset = item.get("asset", "")
        state = item.get("state", "Unknown")
        if state in (1, "1"):
            value = 1
        elif state in (0, "0"):
            value = 0
        elif isinstance(state, str) and state.strip().lower() == "compromised":
            value = 1
        elif isinstance(state, str) and state.strip().lower() == "safe":
            value = 0
        elif isinstance(state, str) and state.strip().lower() == "unknown":
            continue
        else:
            raise ValueError(
                f"Evidence state for '{asset or 'unknown'}' must be "
                "Unknown, Compromised, Safe, 0, or 1."
            )
        if asset in evidence_map and evidence_map[asset] != value:
            raise ValueError(
                f"Contradictory evidence for asset '{asset}': both state "
                f"{evidence_map[asset]} and state {value} were supplied. "
                "Each asset can be assigned at most one state."
            )
        evidence_map[asset] = value

    result = run_framework(
        topology=topology,
        evidence=evidence_map,
        output_dir=output_dir or OUTPUT_DIR,
        write_outputs=write_outputs,
    )
    return {
        "assets": result["assets"],
        "graph": result["graph"],
        "base_probabilities": result["base_probabilities"],
        "posteriors": result["posteriors"],
        "cpts": result["cpts"],
        "risk_scores": result["risk_scores"],
        "attack_paths": result["attack_paths"],
        "summary": result["summary"],
        "evidence_used": result["evidence_used"],
        "timings": result["timings"],
        # Full model-parameter snapshot used for this run, so API consumers
        # can trace every output back to the exact settings that produced it.
        "settings_used": result.get("settings_used", {}),
        "artifacts": result.get("artifacts", {}),
        # Persistence status: whether the analysis run could be stored.  A
        # False value means the assessment itself succeeded but the database
        # was unavailable.
        "persistence": result.get("persistence", {"saved": False}),
    }
