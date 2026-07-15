from typing import Any

from main import run as run_framework


def analyze(topology: dict[str, Any], evidence: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """Adapter that translates HTTP input into the existing framework call."""
    evidence_map: dict[str, int] = {}
    for item in evidence or []:
        state = item.get("state", "Unknown").strip().lower()
        if state == "compromised":
            evidence_map[item["asset"]] = 1
        elif state == "safe":
            evidence_map[item["asset"]] = 0

    result = run_framework(topology=topology, evidence=evidence_map, write_outputs=False)
    return {
        "graph": result["graph"],
        "posteriors": result["posteriors"],
        "risk_scores": result["risk_scores"],
        "attack_paths": result["attack_paths"],
        "summary": result["summary"],
        "evidence_used": result["evidence_used"],
        "timings": result["timings"],
    }
