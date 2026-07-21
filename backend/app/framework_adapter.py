from typing import Any

from pathlib import Path

from main import run as run_framework

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"


def analyze(
    topology: dict[str, Any],
    evidence: list[dict[str, Any]] | None = None,
    write_outputs: bool = True,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Adapter that translates HTTP input into the existing framework call."""
    evidence_map: dict[str, int] = {}
    for item in evidence or []:
        state = item.get("state", "Unknown")
        if state in (1, "1"):
            evidence_map[item["asset"]] = 1
        elif state in (0, "0"):
            evidence_map[item["asset"]] = 0
        elif isinstance(state, str) and state.strip().lower() == "compromised":
            evidence_map[item["asset"]] = 1
        elif isinstance(state, str) and state.strip().lower() == "safe":
            evidence_map[item["asset"]] = 0
        elif isinstance(state, str) and state.strip().lower() == "unknown":
            continue
        else:
            raise ValueError(f"Evidence state for '{item.get('asset', 'unknown')}' must be Unknown, Compromised, Safe, 0, or 1.")

    result = run_framework(
        topology=topology,
        evidence=evidence_map,
        output_dir=output_dir or OUTPUT_DIR,
        write_outputs=write_outputs,
    )
    return {
        "graph": result["graph"],
        "base_probabilities": result["base_probabilities"],
        "posteriors": result["posteriors"],
        "cpts": result["cpts"],
        "risk_scores": result["risk_scores"],
        "attack_paths": result["attack_paths"],
        "summary": result["summary"],
        "evidence_used": result["evidence_used"],
        "timings": result["timings"],
        "artifacts": result.get("artifacts", {}),
    }
