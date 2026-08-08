"""
sensitivity.py — Lightweight sensitivity analysis for model assumptions.

Purpose
-------
The framework's model parameters (logistic ``k``/``x0``, propagation
weights, exposure and patch multipliers) are *expert-configurable
assumptions*, not empirically calibrated constants.  This module lets an
analyst see how the assessment output moves when an assumption is varied,
making the model's dependence on its assumptions explicit.

It deliberately does NOT fabricate confidence intervals or statistical
significance: the output is a deterministic table of *output deltas* for a
set of one-at-a-time perturbations of the current settings.

Method
------
1. Run the full pipeline once with the current settings (baseline).
2. For each one-at-a-time variation, temporarily override the relevant
   setting, re-run the pipeline, and record the deltas.
3. Restore the original settings and return a structured report.

The pipeline used here mirrors ``backend/cli.run`` but performs no output
writing and no database persistence, keeping the analysis fast and
side-effect free.

Usage (CLI)
-----------
    python -m backend.sensitivity --topology data/swat_example.json

or programmatically::

    from backend.sensitivity import run_sensitivity
    report = run_sensitivity("data/swat_example.json")
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from backend.assets import load_topology
from backend.cpt_generator import parameterize
from backend.enrichment import enrich_graph
from backend.graph_builder import build_graph_skeleton
from backend.inference import compute_posteriors_with_evidence
from backend.probability import compute_base_probs
from backend.risk import build_risk_table, compute_aggregate_risk, risk_level_for
from backend.settings import temporary_settings

def _default_propagation() -> dict[str, float]:
    from backend.settings import DEFAULT_SETTINGS
    return dict(DEFAULT_SETTINGS["propagation_weights"])


# One-at-a-time perturbations of configurable model assumptions.  Each entry
# is (label, description, settings override).  Values are chosen to be
# meaningful but within the framework's validated ranges.
VARIATIONS: list[tuple[str, str, dict[str, Any]]] = [
    (
        "logistic_k_high",
        "CVSS→probability curve steeper (k=1.2)",
        {"cvss_logistic_params": {"k": 1.2}},
    ),
    (
        "logistic_k_low",
        "CVSS→probability curve flatter (k=0.4)",
        {"cvss_logistic_params": {"k": 0.4}},
    ),
    (
        "logistic_x0_shifted_down",
        "CVSS midpoint lowered (x0=4.0) — lower severities become more likely",
        {"cvss_logistic_params": {"x0": 4.0}},
    ),
    (
        "logistic_x0_shifted_up",
        "CVSS midpoint raised (x0=6.0) — lower severities become less likely",
        {"cvss_logistic_params": {"x0": 6.0}},
    ),
    (
        "propagation_weights_plus25pct",
        "All Noisy-OR causal weights ×1.25",
        {"propagation_weights": {k: v * 1.25 for k, v in _default_propagation().items()}},
    ),
    (
        "propagation_weights_minus25pct",
        "All Noisy-OR causal weights ×0.75",
        {"propagation_weights": {k: v * 0.75 for k, v in _default_propagation().items()}},
    ),
    (
        "exposure_effect_doubled",
        "Internet-facing exposure multiplier raised to 2.0",
        {"exposure_multipliers": {"true": 2.0, "false": 0.3}},
    ),
    (
        "patch_effect_stronger",
        "Fully-patched multiplier lowered to 0.5 (stronger mitigation)",
        {"patch_multipliers": {"true": 0.5, "false": 1.2}},
    ),
]


def _assess(
    assets: dict[str, dict],
    relationships: list,
    evidence: dict[str, int],
) -> dict[str, Any]:
    """Run the model pipeline (no persistence, no output writing)."""
    model, edge_weights = build_graph_skeleton(relationships, node_ids=assets.keys())
    base_probs = compute_base_probs(assets)
    model = parameterize(model, edge_weights, base_probs)
    posteriors, _ = compute_posteriors_with_evidence(model, evidence)
    risk_table = build_risk_table(posteriors, assets)
    aggregate = compute_aggregate_risk(risk_table)

    if risk_table.empty:
        top_asset = None
        top_risk = 0.0
    else:
        top_row = risk_table.iloc[0]
        top_asset = str(top_row["asset"])
        top_risk = float(top_row["risk"])

    return {
        "mean_intrinsic": round(float(sum(base_probs.values()) / len(base_probs)), 6) if base_probs else 0.0,
        "mean_posterior": round(float(sum(posteriors.values()) / len(posteriors)), 6) if posteriors else 0.0,
        "overall_risk": aggregate["max_risk"],
        "mean_risk": aggregate["mean_risk"],
        "risk_level": risk_level_for(aggregate["max_risk"]).lower(),
        "top_risk_asset": top_asset,
        "top_risk": round(top_risk, 6),
    }


def _deltas(baseline: dict[str, Any], varied: dict[str, Any]) -> dict[str, Any]:
    return {
        "delta_mean_intrinsic": round(varied["mean_intrinsic"] - baseline["mean_intrinsic"], 6),
        "delta_mean_posterior": round(varied["mean_posterior"] - baseline["mean_posterior"], 6),
        "delta_overall_risk": round(varied["overall_risk"] - baseline["overall_risk"], 6),
        "delta_mean_risk": round(varied["mean_risk"] - baseline["mean_risk"], 6),
        "delta_top_risk": round(varied["top_risk"] - baseline["top_risk"], 6),
    }


def run_sensitivity(
    topology: str | dict,
    evidence: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Run a one-at-a-time sensitivity analysis over model assumptions.

    Args:
        topology: Topology path or inline dict.
        evidence: Optional evidence map {node_id: 0|1}.

    Returns:
        A report with the baseline metrics, per-variation overrides and
        deltas, and a note that deltas are deterministic (not statistical).
    """
    if evidence is None:
        evidence = {}

    assets, relationships, warnings = load_topology(topology)
    normalized = enrich_graph(assets, relationships)
    assets = normalized["assets"]
    relationships = normalized["relationships"]

    baseline = _assess(assets, relationships, evidence)

    variations: list[dict[str, Any]] = []
    for label, description, overrides in VARIATIONS:
        with temporary_settings(overrides):
            varied = _assess(assets, relationships, evidence)
        variations.append({
            "label": label,
            "description": description,
            "overrides": overrides,
            "metrics": varied,
            "deltas": _deltas(baseline, varied),
        })

    return {
        "note": (
            "Deterministic one-at-a-time perturbation of model assumptions. "
            "Deltas show how the output moves when a single assumption is "
            "changed; they are NOT statistical confidence intervals and no "
            "empirical calibration is claimed."
        ),
        "topology_warnings": warnings,
        "evidence": evidence,
        "baseline": baseline,
        "variations": variations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-at-a-time sensitivity analysis for model assumptions."
    )
    parser.add_argument("--topology", default="data/swat_example.json")
    parser.add_argument("--evidence", action="append", default=[])
    args = parser.parse_args()

    evidence: dict[str, int] = {}
    for pair in args.evidence:
        node, value = pair.split("=")
        evidence[node] = int(value)

    report = run_sensitivity(args.topology, evidence)
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
