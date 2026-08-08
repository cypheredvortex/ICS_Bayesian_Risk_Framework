"""Tests for the risk table computation module."""

import pandas as pd
import pytest

from backend.risk import build_risk_table, risk_level_for, write_risk_table, m_scope


class TestMLikelihood:
    """Scope multiplier computation."""

    def test_default_scope_returns_one(self) -> None:
        attrs = {}
        assert m_scope(attrs) == 1.0

    def test_scope_1_returns_1(self) -> None:
        attrs = {"scope": 1}
        assert m_scope(attrs) == 1.0

    def test_scope_5_returns_1_4(self) -> None:
        attrs = {"scope": 5}
        assert m_scope(attrs) == 1.4

    def test_scope_0_returns_0_9(self) -> None:
        attrs = {"scope": 0}
        assert m_scope(attrs) == 0.9


class TestBuildRiskTable:
    """Risk table generation from posteriors and assets."""

    def test_single_asset_returns_valid_table(self) -> None:
        posteriors = {"PLC_01": 0.75}
        assets = {"PLC_01": {"consequence_severity": 2.0, "scope": 1}}
        df = build_risk_table(posteriors, assets)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert df.iloc[0]["asset"] == "PLC_01"
        assert df.iloc[0]["P(compromised|evidence)"] == 0.75

    def test_multiple_assets_sorted_by_risk_descending(self) -> None:
        posteriors = {"Asset_A": 0.9, "Asset_B": 0.1}
        assets = {
            "Asset_A": {"consequence_severity": 3.0, "scope": 2},
            "Asset_B": {"consequence_severity": 1.0, "scope": 1},
        }
        df = build_risk_table(posteriors, assets)
        assert df.iloc[0]["asset"] == "Asset_A"
        assert df.iloc[1]["asset"] == "Asset_B"
        # Risk Index = P x (severity/10) x scope_multiplier
        impact_a = (3.0 / 10.0) * 1.1
        impact_b = (1.0 / 10.0) * 1.0
        assert df.iloc[0]["risk"] == pytest.approx(0.9 * impact_a)
        assert df.iloc[1]["risk"] == pytest.approx(0.1 * impact_b)

    def test_risk_index_never_exceeds_bounded_range(self) -> None:
        posteriors = {"X": 1.0}
        assets = {"X": {"consequence_severity": 10.0, "scope": 5}}
        df = build_risk_table(posteriors, assets)
        # Impact = 1.0 * 1.4 = 1.4; Risk Index bounded above by ~1.4
        assert df.iloc[0]["impact"] == pytest.approx(1.4)
        assert df.iloc[0]["risk"] == pytest.approx(1.4)

    def test_empty_posteriors_returns_empty_table(self) -> None:
        df = build_risk_table({}, {})
        assert len(df) == 0

    def test_missing_severity_defaults_to_zero(self) -> None:
        posteriors = {"Asset_A": 0.5}
        assets = {"Asset_A": {}}
        df = build_risk_table(posteriors, assets)
        assert df.iloc[0]["risk"] == 0.0


class TestRiskLevel:
    """Risk level classification on the normalised risk index scale."""

    def test_critical_threshold(self) -> None:
        assert risk_level_for(0.9) == "Critical"
        assert risk_level_for(0.75) == "Critical"

    def test_high_threshold(self) -> None:
        assert risk_level_for(0.6) == "High"
        assert risk_level_for(0.5) == "High"

    def test_moderate_threshold(self) -> None:
        assert risk_level_for(0.4) == "Moderate"
        assert risk_level_for(0.25) == "Moderate"

    def test_low_below_moderate(self) -> None:
        assert risk_level_for(0.0) == "Low"
        assert risk_level_for(0.249) == "Low"


class TestWriteRiskTable:
    """CSV export of risk table."""

    def test_writes_csv_with_rank_and_risk_level(self, tmp_path) -> None:
        # Build a realistic register via build_risk_table so the Rank and
        # risk_level columns actually exist.
        df = build_risk_table({"Asset_A": 1.0}, {"Asset_A": {"consequence_severity": 8.0, "scope": 1}})
        path = write_risk_table(df, tmp_path / "risk_table.csv")
        assert path.exists()
        content = path.read_text(encoding="utf-8-sig")
        assert "Rank" in content
        assert "risk_level" in content
        assert "Critical" in content

    def test_empty_df_creates_header_only(self, tmp_path) -> None:
        df = pd.DataFrame(columns=["asset", "P(compromised|evidence)", "severity", "scope_mult", "impact", "risk"])
        path = write_risk_table(df, tmp_path / "empty_risk.csv")
        assert path.exists()
        content = path.read_text(encoding="utf-8-sig")
        assert content.strip() != ""

