"""
tests/test_ics_architecture.py - Tests for the Purdue-inspired ICS
architecture support: purdue_level normalization, the advisory architecture
audit (audit_ics_architecture), zone-derived level defaults, and the full
chemical-plant topology -> Bayesian analysis workflow.
"""

from pathlib import Path

import pytest

from backend.assets import load_topology
from backend.cli import run as run_framework
from backend.enrichment import enrich_asset
from backend.graph_builder import build_graph_skeleton, graph_to_dict
from backend.topology import (
    VALID_PURDUE_LEVELS,
    ZONE_PURDUE_DEFAULTS,
    audit_ics_architecture,
    build_topology_summary,
    infer_purdue_level,
    normalize_asset,
    validate_graph,
    zone_to_purdue_level,
)

CHEMICAL_PLANT = (
    Path(__file__).resolve().parent.parent
    / "ics_topologies"
    / "chemical_processing_plant"
    / "chemical_processing_plant.json"
)


def _find(issues, code):
    return [issue for issue in issues if issue["code"] == code]


class TestPurdueLevelNormalization:
    def test_valid_levels_are_accepted(self):
        for level in VALID_PURDUE_LEVELS:
            asset = normalize_asset({"id": f"a-{level}", "kind": "device", "purdue_level": level})
            assert asset["purdue_level"] == level

    def test_invalid_level_rejected(self):
        with pytest.raises(ValueError, match="'purdue_level' must be one of"):
            normalize_asset({"id": "a", "kind": "device", "purdue_level": "9"})

    def test_none_level_is_ignored(self):
        asset = normalize_asset({"id": "a", "kind": "device", "purdue_level": None})
        assert "purdue_level" not in asset

    def test_zone_default_mapping(self):
        # ZONE_PURDUE_DEFAULTS powers both infer_purdue_level and
        # enrichment; the DMZ (3.5) and enterprise (4) boundaries are the
        # critical entries.
        assert ZONE_PURDUE_DEFAULTS["idmz"] == "3.5"
        assert ZONE_PURDUE_DEFAULTS["enterprise"] == "4"
        assert ZONE_PURDUE_DEFAULTS["dcs"] == "2"
        assert ZONE_PURDUE_DEFAULTS["field"] == "1"
        assert ZONE_PURDUE_DEFAULTS["process"] == "0"

    def test_infer_from_zone(self):
        assert infer_purdue_level("some asset", {"zone": "Industrial DMZ"}) == "3.5"

    def test_enrichment_derives_level_from_zone(self):
        # An asset without an explicit level still gets one once enriched,
        # derived from its declared zone.
        asset = enrich_asset({"id": "dcs-1", "kind": "device", "zone": "DCS"})
        assert asset["purdue_level"] == "2"

    def test_explicit_level_wins_over_zone(self):
        asset = enrich_asset(
            {"id": "jump", "kind": "device", "zone": "DMZ", "purdue_level": "4"}
        )
        assert asset["purdue_level"] == "4"

    def test_unzoned_asset_keeps_no_level(self):
        # Regression: enrichment used to stamp a bogus "unknown" level on
        # assets with no recognisable zone, which poisoned summaries and
        # suppressed the PURDUE_LEVEL_MISSING audit finding.
        asset = enrich_asset({"id": "mystery", "kind": "device"})
        assert "purdue_level" not in asset

    def test_unknown_zone_keeps_no_level(self):
        asset = enrich_asset({"id": "x", "kind": "device", "zone": "Sector 7G"})
        assert "purdue_level" not in asset

    def test_multi_word_zone_maps_to_level(self):
        # "DCS Network" is not an exact ZONE_PURDUE_DEFAULTS key; the zone
        # fallback must substring-match so multi-word zones still resolve.
        assert zone_to_purdue_level("DCS Network") == "2"
        assert zone_to_purdue_level("Industrial DMZ") == "3.5"
        assert zone_to_purdue_level("Field Instruments") == "1"
        asset = enrich_asset({"id": "dcs", "kind": "device", "zone": "DCS Network"})
        assert asset["purdue_level"] == "2"


class TestAssetMetadataPreservation:
    """Display metadata (declared type, plain-language description) must
    survive normalization and feed the structural summary."""

    def test_type_and_description_are_preserved(self):
        asset = normalize_asset({
            "id": "fw-1",
            "kind": "device",
            "type": "Firewall",
            "description": "Enterprise-to-IDMZ boundary firewall",
        })
        assert asset["type"] == "Firewall"
        assert asset["description"] == "Enterprise-to-IDMZ boundary firewall"

    def test_kind_alias_type_is_not_duplicated(self):
        # CSV/GraphML importers set raw["type"] to the inferred kind; that
        # must not be duplicated as a device type.
        asset = normalize_asset({"id": "plc", "type": "device"})
        assert asset["kind"] == "device"
        assert "type" not in asset

    def test_category_also_preserved_as_type(self):
        asset = normalize_asset({"id": "hmi-1", "category": "HMI"})
        assert asset["type"] == "HMI"

    def test_empty_description_is_skipped(self):
        asset = normalize_asset({"id": "x", "kind": "device", "description": "  "})
        assert "description" not in asset

    def test_audit_uses_declared_type(self):
        # Regression: the audit read attrs.get("type") which normalization
        # used to drop, so type-based classification was always empty.
        assets = {
            "jump": {"id": "jump", "kind": "device", "type": "Jump Server", "zone": "DMZ"},
            "dcs": {"id": "dcs", "kind": "device", "type": "DCS Controller", "zone": "DMZ"},
        }
        rels = [("jump", "dcs", "connects-to", True, {})]
        issues = audit_ics_architecture(assets, rels)
        finding = _find(issues, "CONTROL_ASSET_IN_DMZ")[0]
        assert "dcs" in finding["assets"]

    def test_summary_coverage_includes_type_and_description(self):
        assets = {
            "fw": {"id": "fw", "kind": "device", "type": "Firewall", "description": "Boundary"},
            "sw": {"id": "sw", "kind": "device"},
        }
        rels = [("fw", "sw", "connects-to", False, {})]
        summary = build_topology_summary(assets, rels)
        assert summary["field_coverage"]["type"] == 1
        assert summary["field_coverage"]["description"] == 1


class TestArchitectureAudit:
    def test_control_asset_in_dmz_is_an_error(self):
        assets = {
            "jump": {"id": "jump", "kind": "device", "name": "Jump Server", "zone": "DMZ"},
            "dcs": {"id": "dcs", "kind": "device", "name": "DCS Controller", "zone": "DMZ"},
        }
        rels = [("jump", "dcs", "connects-to", True, {})]
        issues = audit_ics_architecture(assets, rels)
        assert _find(issues, "CONTROL_ASSET_IN_DMZ")[0]["severity"] == "error"
        assert "dcs" in _find(issues, "CONTROL_ASSET_IN_DMZ")[0]["assets"]

    def test_operator_station_in_dmz_is_an_error(self):
        # Regression: multi-word control-plane descriptors ("operator
        # station") cannot be represented as whole-word tokens and used to
        # slip through the DMZ rule.
        assets = {
            "jump": {"id": "jump", "kind": "device", "name": "Jump Server", "zone": "DMZ"},
            "op-station": {
                "id": "op-station",
                "kind": "device",
                "name": "Operator Station",
                "zone": "DMZ",
            },
            "eng-station": {
                "id": "eng-station",
                "kind": "device",
                "name": "Engineering Workstation",
                "zone": "DMZ",
            },
        }
        rels = [("jump", "op-station", "connects-to", True, {})]
        issues = audit_ics_architecture(assets, rels)
        finding = _find(issues, "CONTROL_ASSET_IN_DMZ")[0]
        assert finding["severity"] == "error"
        assert "op-station" in finding["assets"]
        assert "eng-station" in finding["assets"]

    def test_sis_exposed_to_enterprise_is_an_error(self):
        assets = {
            "ent-switch": {"id": "ent-switch", "kind": "device", "name": "Switch", "zone": "Enterprise"},
            "sis-plc": {"id": "sis-plc", "kind": "device", "name": "Safety PLC", "zone": "Enterprise"},
        }
        rels = [("ent-switch", "sis-plc", "connects-to", False, {})]
        issues = audit_ics_architecture(assets, rels)
        assert _find(issues, "SIS_EXPOSED_TO_ENTERPRISE")[0]["severity"] == "error"

    def test_enterprise_controlling_field_is_an_error(self):
        assets = {
            "erp": {"id": "erp", "kind": "device", "name": "ERP Server", "zone": "Enterprise", "purdue_level": "4"},
            "valve": {"id": "valve", "kind": "physical", "name": "Control Valve", "zone": "Field", "purdue_level": "1"},
        }
        rels = [("erp", "valve", "controls", False, {})]
        issues = audit_ics_architecture(assets, rels)
        assert _find(issues, "ENTERPRISE_CONTROLS_FIELD")[0]["severity"] == "error"

    def test_missing_security_boundary_is_a_warning(self):
        assets = {
            "erp": {"id": "erp", "kind": "device", "name": "ERP Server", "zone": "Enterprise"},
            "hmi": {"id": "hmi", "kind": "device", "name": "HMI", "zone": "Operations"},
        }
        rels = [("erp", "hmi", "connects-to", False, {})]
        issues = audit_ics_architecture(assets, rels)
        assert _find(issues, "MISSING_SECURITY_BOUNDARY")[0]["severity"] == "warning"

    def test_unfirewalled_boundary_link_is_info(self):
        assets = {
            "erp": {"id": "erp", "kind": "device", "name": "ERP Server", "zone": "Enterprise"},
            "fw": {"id": "fw", "kind": "device", "name": "OT Firewall", "zone": "Enterprise"},
            "hmi": {"id": "hmi", "kind": "device", "name": "HMI", "zone": "Operations"},
        }
        rels = [
            ("erp", "fw", "connects-to", False, {}),
            ("fw", "hmi", "connects-to", False, {}),
        ]
        issues = audit_ics_architecture(assets, rels)
        assert _find(issues, "BOUNDARY_LINK_NOT_FIREWALLED")[0]["severity"] == "info"

    def test_clean_segmented_architecture_has_no_errors(self):
        # A defensible architecture: Enterprise -> firewall -> DMZ ->
        # firewall -> operations -> DCS -> field -> process, with a separate
        # SIS chain and a firewalled remote RTU link.
        assets = {
            "ent-erp": {"id": "ent-erp", "kind": "device", "name": "ERP Server", "zone": "Enterprise", "purdue_level": "4"},
            "ent-fw": {"id": "ent-fw", "kind": "device", "name": "Corporate Firewall", "zone": "Enterprise", "purdue_level": "4"},
            "idmz-jump": {"id": "idmz-jump", "kind": "device", "name": "Jump Server", "zone": "Industrial DMZ", "purdue_level": "3.5"},
            "idmz-broker": {"id": "idmz-broker", "kind": "device", "name": "Data Broker", "zone": "Industrial DMZ", "purdue_level": "3.5"},
            "ot-fw": {"id": "ot-fw", "kind": "device", "name": "OT Firewall", "zone": "Operations", "purdue_level": "3"},
            "hmi": {"id": "hmi", "kind": "device", "name": "Operator Station", "zone": "Operations", "purdue_level": "3"},
            "eng": {"id": "eng", "kind": "device", "name": "Engineering Workstation", "zone": "Operations", "purdue_level": "3"},
            "dcs": {"id": "dcs", "kind": "device", "name": "DCS Controller", "zone": "DCS", "purdue_level": "2"},
            "sis-plc": {"id": "sis-plc", "kind": "device", "name": "Safety PLC", "zone": "SIS", "purdue_level": "2"},
            "sis-tx": {"id": "sis-tx", "kind": "device", "name": "Safety Transmitter", "zone": "SIS", "purdue_level": "1"},
            "sis-valve": {"id": "sis-valve", "kind": "physical", "name": "Safety Valve", "zone": "SIS", "purdue_level": "1"},
            "tx": {"id": "tx", "kind": "device", "name": "Pressure Transmitter", "zone": "Field", "purdue_level": "1"},
            "valve": {"id": "valve", "kind": "physical", "name": "Control Valve", "zone": "Field", "purdue_level": "1"},
            "reactor": {"id": "reactor", "kind": "physical", "name": "Reactor", "zone": "Process", "purdue_level": "0"},
            "rtu": {"id": "rtu", "kind": "device", "name": "Remote RTU", "zone": "Remote", "purdue_level": "1"},
            "rtu-pump": {"id": "rtu-pump", "kind": "physical", "name": "Remote Pump", "zone": "Remote", "purdue_level": "1"},
        }
        rels = [
            ("ent-erp", "ent-fw", "connects-to", True, {}),
            ("ent-fw", "idmz-jump", "connects-to", True, {}),
            ("idmz-jump", "ot-fw", "connects-to", True, {}),
            ("ot-fw", "hmi", "connects-to", True, {}),
            ("ot-fw", "eng", "connects-to", True, {}),
            ("eng", "dcs", "programs / operates", True, {}),
            ("hmi", "dcs", "monitors", False, {}),
            ("tx", "dcs", "monitors", False, {}),
            ("dcs", "valve", "controls", False, {}),
            ("valve", "reactor", "actuates", False, {}),
            ("sis-tx", "sis-plc", "monitors", False, {}),
            ("sis-plc", "sis-valve", "controls", False, {}),
            ("dcs", "rtu", "connects-to", True, {}),
            ("rtu", "rtu-pump", "controls", False, {}),
        ]
        validate_graph(assets, rels, "clean-arch")  # structurally valid DAG
        issues = audit_ics_architecture(assets, rels)
        errors = [i for i in issues if i["severity"] == "error"]
        assert errors == [], f"expected no architecture errors, got {errors}"


class TestFormatCoverageParity:
    """Every representation of the same topology must preserve the same
    semantic attributes as the canonical JSON: zones, declared type,
    description, Purdue level, and relationship security flags."""

    CHEMICAL_DIR = CHEMICAL_PLANT.parent
    FORMAT_SUFFIXES = [
        ".yaml", ".csv", ".xlsx", ".graphml", ".xml", ".aml", ".vdx", ".vsdx",
    ]

    @pytest.mark.parametrize("suffix", FORMAT_SUFFIXES)
    def test_every_format_matches_canonical_attribute_coverage(self, suffix):
        from backend.assets import load_topology

        canonical_path = CHEMICAL_PLANT
        format_path = self.CHEMICAL_DIR / f"chemical_processing_plant{suffix}"
        if not format_path.exists():
            pytest.skip(f"fixture {format_path.name} not present")

        canonical_assets, canonical_rels, _ = load_topology(canonical_path)
        assets, rels, warnings = load_topology(format_path)

        assert set(assets) == set(canonical_assets), f"{suffix}: asset IDs differ"
        assert len(rels) == len(canonical_rels), f"{suffix}: relationship count differs"
        assert warnings == [], f"{suffix}: unexpected warnings {warnings}"

        # Attribute coverage must be identical to the canonical JSON: zones,
        # declared type, description and security fields.
        for field in ("zone", "type", "description", "cvss_type"):
            canonical_have = {
                aid for aid, attrs in canonical_assets.items() if attrs.get(field)
            }
            format_have = {aid for aid, attrs in assets.items() if attrs.get(field)}
            assert format_have == canonical_have, (
                f"{suffix}: field '{field}' coverage differs "
                f"({len(format_have)} vs {len(canonical_have)})"
            )

        # Zone assignment parity: every asset lands in the same zone.
        canonical_zones = {aid: attrs.get("zone") for aid, attrs in canonical_assets.items()}
        format_zones = {aid: attrs.get("zone") for aid, attrs in assets.items()}
        assert format_zones == canonical_zones, f"{suffix}: zone assignments differ"

        # Relationship security metadata parity (firewalled flag + transport).
        def rel_edges(rels):
            return {
                (r[0], r[1]): (bool(r[3]), r[4].get("transport"))
                for r in rels
            }

        assert rel_edges(rels) == rel_edges(canonical_rels), f"{suffix}: relationship metadata differs"


class TestChemicalPlantPipeline:
    def test_canonical_chemical_plant_loads_clean(self):
        assert CHEMICAL_PLANT.exists(), "canonical chemical plant missing"
        assets, rels, warnings = load_topology(CHEMICAL_PLANT)
        assert len(assets) >= 25
        assert len(rels) >= 20
        assert warnings == [], f"unexpected normalization warnings: {warnings}"

        summary = build_topology_summary(assets, rels)
        # Every declared Purdue level from L5 to L0 must be represented.
        for level in ("5", "4", "3.5", "3", "2", "1", "0"):
            assert summary["purdue_levels"].get(level, 0) > 0, f"missing L{level}"

        issues = summary["architecture_issues"]
        errors = [i for i in issues if i["severity"] == "error"]
        assert errors == [], f"chemical plant has architecture errors: {errors}"

    def test_full_pipeline_runs_with_evidence(self):
        result = run_framework(
            str(CHEMICAL_PLANT),
            evidence={"CHEM-ENT-FW-001": 1},
            write_outputs=False,
            persist=False,
        )
        assert result["summary"]["asset_count"] >= 25
        assert len(result["risk_scores"]) == result["summary"]["asset_count"]
        assert len(result["cpts"]) > 0
        assert len(result["attack_paths"]) >= 1

        # Graph nodes must carry the zone/Purdue metadata the frontend uses
        # for its Purdue-ordered zone bands.
        graph_nodes = {node["id"]: node for node in result["graph"]["nodes"]}
        assert len(graph_nodes) == result["summary"]["asset_count"]
        zoned = [n for n in graph_nodes.values() if n.get("zone") and n.get("purdue_level")]
        assert len(zoned) == len(graph_nodes), "every node should carry zone + purdue_level"

    def test_graph_builder_preserves_zone_and_level(self):
        assets, rels, _ = load_topology(CHEMICAL_PLANT)
        model, edge_weights = build_graph_skeleton(rels, node_ids=list(assets))
        graph = graph_to_dict(model, edge_weights, rels, assets)
        assert len(graph["nodes"]) == len(assets)
        assert all("zone" in node and "purdue_level" in node for node in graph["nodes"])
        # Every relationship keeps its physical transport metadata where it
        # is declared (e.g. the remote tank-farm conduit).
        transports = {edge.get("transport") for edge in graph["edges"] if edge.get("transport")}
        assert transports, "expected at least one declared transport (remote conduit)"
