"""Tests for the one-at-a-time sensitivity analysis module."""

from backend.sensitivity import VARIATIONS, run_sensitivity
from backend.settings import get_settings


def _device_topology(cvss: float = 8.0):
    """A small but non-trivial topology: internet-facing HMI -> PLC -> process."""
    return {
        "assets": {
            "corp_net": {
                "kind": "device",
                "cvss_type": 9.0,
                "exposed": True,
                "patched": False,
                "consequence_severity": 6.0,
            },
            "hmi": {
                "kind": "device",
                "cvss_type": cvss,
                "exposed": True,
                "patched": False,
                "consequence_severity": 7.0,
            },
            "plc_1": {
                "kind": "device",
                "cvss_type": cvss,
                "exposed": False,
                "patched": True,
                "consequence_severity": 9.0,
                "scope": 4,
            },
        },
        "relationships": [
            ["corp_net", "hmi", "connects-to", False],
            ["hmi", "plc_1", "programs / operates", True],
        ],
    }


class TestSensitivityReport:
    def test_report_has_baseline_and_variations(self):
        report = run_sensitivity(_device_topology())
        assert "baseline" in report
        assert "variations" in report
        assert report["note"]
        assert len(report["variations"]) == len(VARIATIONS)

    def test_baseline_metrics_are_populated(self):
        report = run_sensitivity(_device_topology())
        baseline = report["baseline"]
        for key in ("mean_intrinsic", "mean_posterior", "overall_risk", "mean_risk"):
            assert isinstance(baseline[key], float)

    def test_each_variation_reports_overrides_and_deltas(self):
        report = run_sensitivity(_device_topology())
        for variation in report["variations"]:
            assert variation["label"]
            assert variation["description"]
            assert isinstance(variation["overrides"], dict)
            assert "deltas" in variation
            for key in (
                "delta_mean_intrinsic",
                "delta_mean_posterior",
                "delta_overall_risk",
                "delta_mean_risk",
                "delta_top_risk",
            ):
                assert key in variation["deltas"]

    def test_changing_assumptions_changes_outputs(self):
        """The central message of the sensitivity analysis: model outputs
        respond to model assumptions."""
        report = run_sensitivity(_device_topology())
        changed = [
            v for v in report["variations"]
            if abs(v["deltas"]["delta_overall_risk"]) > 1e-9
        ]
        # The CVSS logistic variations and the propagation variations must
        # move the network-level risk for this CVSS-heavy topology.
        assert len(changed) >= 2

    def test_settings_are_restored_after_run(self):
        before = get_settings()
        run_sensitivity(_device_topology())
        after = get_settings()
        assert before == after

    def test_evidence_is_propagated(self):
        report = run_sensitivity(_device_topology(), evidence={"corp_net": 1})
        assert report["evidence"] == {"corp_net": 1}
        # Evidence raises the posterior mean above the no-evidence baseline.
        no_evidence = run_sensitivity(_device_topology())["baseline"]
        assert report["baseline"]["mean_posterior"] > no_evidence["mean_posterior"]
