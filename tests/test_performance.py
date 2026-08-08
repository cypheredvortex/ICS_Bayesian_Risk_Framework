"""
tests/test_performance.py - Realistic performance benchmarks.

Bayesian inference can become expensive, so the framework records actual
timings and asserts generous ceilings for increasingly large topologies.
The bounds below are deliberately conservative (they pass on modest CI
hardware) while still catching pathological regressions such as accidental
exponential-time CPT construction or per-node full-network inference.

Timings are printed so the CI log documents the real numbers; the
assertions only guard against order-of-magnitude regressions.
"""

import time

import pytest

from backend.cli import run


def _chain_topology(n: int) -> dict:
    """A directed chain of n devices: 0 -> 1 -> ... -> n-1."""
    assets = {}
    relationships = []
    for i in range(n):
        assets[f"node_{i}"] = {
            "kind": "device",
            "cvss_type": 5.0 + (i % 5),
            "exposed": i == 0,
            "patched": False,
            "consequence_severity": 5.0,
        }
        if i > 0:
            relationships.append([f"node_{i-1}", f"node_{i}", "connects-to", False])
    return {"assets": assets, "relationships": relationships}


def _broad_topology(n: int) -> dict:
    """n leaf devices fed by one internet-facing root (fan-in = n - 1)."""
    assets = {
        "root": {
            "kind": "device",
            "cvss_type": 9.0,
            "exposed": True,
            "patched": False,
            "consequence_severity": 5.0,
        }
    }
    relationships = []
    for i in range(1, n):
        assets[f"leaf_{i}"] = {
            "kind": "device",
            "cvss_type": 5.0,
            "exposed": False,
            "patched": True,
            "consequence_severity": 5.0,
        }
        relationships.append(["root", f"leaf_{i}", "connects-to", False])
    return {"assets": assets, "relationships": relationships}


# (label, topology builder, node count, generous ceiling seconds for the full run)
CASES = [
    ("chain_10", _chain_topology, 10, 20.0),
    ("chain_25", _chain_topology, 25, 30.0),
    ("chain_50", _chain_topology, 50, 60.0),
    ("chain_100", _chain_topology, 100, 120.0),
    ("broad_25", _broad_topology, 25, 30.0),
]


@pytest.mark.parametrize("label, builder, n, ceiling", CASES)
def test_full_assessment_within_generous_ceiling(label, builder, n, ceiling, capsys):
    topology = builder(n)
    started = time.perf_counter()
    result = run(topology, evidence={}, write_outputs=False, persist=False)
    wall_time = time.perf_counter() - started

    timings = result["timings"]
    print(
        f"\n[{label}] nodes={n} build={timings['build_time_seconds']:.3f}s "
        f"inference={timings['inference_time_seconds']:.3f}s "
        f"total={timings['total_time_seconds']:.3f}s wall={wall_time:.3f}s"
    )

    assert len(result["posteriors"]) == n
    assert len(result["risk_scores"]) == n
    assert timings["total_time_seconds"] < ceiling
    assert wall_time < ceiling


def test_timings_are_recorded_per_stage():
    result = run(_chain_topology(10), evidence={}, write_outputs=False, persist=False)
    timings = result["timings"]
    assert timings["build_time_seconds"] >= 0
    assert timings["inference_time_seconds"] >= 0
    assert timings["total_time_seconds"] == pytest.approx(
        timings["build_time_seconds"] + timings["inference_time_seconds"],
        abs=1e-5,
    )
