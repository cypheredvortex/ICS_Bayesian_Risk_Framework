"""
tests/test_topology_validation.py - Regression tests for topology
normalization and validation.
"""

import pytest

from backend.assets import load_topology
from backend.importers import load_topology_from_bytes
from backend.topology import (
    infer_asset_kind,
    normalize_asset,
    normalize_relationship,
    validate_graph,
)


def _topology(assets, relationships):
    return {"assets": assets, "relationships": relationships}


class TestSelfLoops:
    def test_self_loop_is_removed_not_rejected(self):
        assets = {"a": {"kind": "device"}, "b": {"kind": "device"}}
        rels = [("a", "a", "connects-to", False, {}), ("a", "b", "connects-to", False, {})]
        cleaned = validate_graph(assets, rels, "test")
        assert cleaned == [("a", "b", "connects-to", False, {})]

    def test_self_loop_does_not_trigger_false_cycle_error(self):
        # Regression: previously the self-loop was added to the graph after
        # being skipped in validation, producing a bogus "cycle" error.
        topology = _topology(
            {"a": {"kind": "device"}},
            [["a", "a", "connects-to", False]],
        )
        assets, rels = load_topology(topology)
        assert assets == {"a": {"id": "a", "name": "a", "kind": "device"}}
        assert rels == []


class TestDuplicateEdges:
    def test_duplicate_edges_are_deduplicated(self):
        assets = {"a": {"kind": "device"}, "b": {"kind": "device"}}
        rels = [
            ("a", "b", "connects-to", False, {}),
            ("a", "b", "connects-to", False, {}),
        ]
        cleaned = validate_graph(assets, rels, "test")
        assert len(cleaned) == 1


class TestCycles:
    def test_cycle_rejected(self):
        assets = {"a": {"kind": "device"}, "b": {"kind": "device"}}
        rels = [
            ("a", "b", "connects-to", False, {}),
            ("b", "a", "connects-to", False, {}),
        ]
        with pytest.raises(ValueError, match="cycles"):
            validate_graph(assets, rels, "test")


class TestRangeValidation:
    def test_cvss_out_of_range_rejected(self):
        with pytest.raises(ValueError, match=r"'cvss_type' must be in \[0\.0, 10\.0\]"):
            normalize_asset({"id": "plc", "kind": "device", "cvss_type": 15})

    def test_cvss_negative_rejected(self):
        with pytest.raises(ValueError, match=r"'cvss_type' must be in \[0\.0, 10\.0\]"):
            normalize_asset({"id": "plc", "kind": "device", "cvss_type": -1})

    def test_cvss_non_numeric_rejected(self):
        with pytest.raises(ValueError, match="'cvss_type' must be a number"):
            normalize_asset({"id": "plc", "kind": "device", "cvss_type": "high"})

    def test_consequence_severity_out_of_range_rejected(self):
        with pytest.raises(ValueError, match=r"'consequence_severity' must be in \[0\.0, 10\.0\]"):
            normalize_asset({"id": "plc", "kind": "device", "cvss_type": 5.0, "consequence_severity": 11})

    def test_awareness_out_of_range_rejected(self):
        with pytest.raises(ValueError, match=r"'awareness' must be in \[0\.0, 1\.0\]"):
            normalize_asset({"id": "op", "kind": "human", "role": "operator", "awareness": 1.5})

    def test_p_base_override_out_of_range_rejected(self):
        with pytest.raises(ValueError, match=r"'p_base_override' must be in \[0\.0, 1\.0\]"):
            normalize_asset({"id": "valve", "kind": "physical", "p_base_override": 2.0})


class TestVulnerabilities:
    def test_vulnerabilities_set_effective_cvss(self):
        asset = normalize_asset({
            "id": "scada",
            "kind": "device",
            "exposed": True,
            "patched": True,
            "vulnerabilities": [
                {"cve_id": "CVE-2014-0160", "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N"}
            ],
        })
        assert asset["cvss_type"] == pytest.approx(7.5)
        assert asset["vulnerabilities"][0]["cve_id"] == "CVE-2014-0160"

    def test_vulnerabilities_override_legacy_cvss_type(self):
        asset = normalize_asset({
            "id": "scada",
            "kind": "device",
            "cvss_type": 2.0,
            "vulnerabilities": [
                {"cve_id": "CVE-2021-44228", "score": 9.8}
            ],
        })
        assert asset["cvss_type"] == pytest.approx(9.8)

    def test_invalid_vulnerability_rejected(self):
        with pytest.raises(ValueError, match="not a CVSS v3.1 vector"):
            normalize_asset({
                "id": "scada",
                "kind": "device",
                "vulnerabilities": ["not-a-vector"],
            })


class TestKindInference:
    def test_engineering_workstation_is_device(self):
        # Regression: 'workstation' used to be a human keyword, so
        # Engineering_Workstation was misclassified as a human asset.
        assert infer_asset_kind("Engineering_Workstation") == "device"

    def test_operator_is_human(self):
        assert infer_asset_kind("Operator_Console") == "human"

    def test_plc_is_device(self):
        assert infer_asset_kind("PLC_01") == "device"


class TestEndToEndValidation:
    def test_inline_topology_with_vulnerabilities_loads(self):
        topology = _topology(
            {
                "scada": {
                    "kind": "device",
                    "exposed": True,
                    "patched": False,
                    "vulnerabilities": [
                        {"cve_id": "CVE-2021-44228", "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H"}
                    ],
                }
            },
            [],
        )
        assets, rels = load_topology(topology)
        assert assets["scada"]["cvss_type"] == pytest.approx(10.0)

    def test_invalid_cvss_in_payload_rejected(self):
        topology = _topology(
            {"plc": {"kind": "device", "cvss_type": 42}},
            [],
        )
        with pytest.raises(ValueError, match=r"'cvss_type' must be in \[0\.0, 10\.0\]"):
            load_topology(topology)

    def test_csv_upload_with_garbage_cvss_rejected(self):
        csv_bytes = b"asset,type,cvss_type\nPLC-1,PLC,banana\n"
        with pytest.raises(ValueError, match="'cvss_type' must be a number"):
            load_topology_from_bytes(csv_bytes, "topology.csv")

    def test_graphml_security_attributes_promoted_and_validated(self):
        # Regression: security attributes in GraphML were buried in metadata
        # (silently ignored). They must reach normalize_asset's strict
        # validation, matching the CSV/JSON paths.
        graphml = b"""<?xml version='1.0' encoding='utf-8'?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <key id="k1" for="node" attr.name="cvss_type" attr.type="string" />
  <key id="k2" for="node" attr.name="consequence_severity" attr.type="string" />
  <key id="k3" for="node" attr.name="kind" attr.type="string" />
  <graph edgedefault="directed">
    <node id="plc_1">
      <data key="k1">7.5</data>
      <data key="k2">9</data>
      <data key="k3">device</data>
    </node>
  </graph>
</graphml>"""
        topo = load_topology_from_bytes(graphml, "topology.graphml")
        assert topo["assets"]["plc_1"]["cvss_type"] == pytest.approx(7.5)
        assert topo["assets"]["plc_1"]["consequence_severity"] == pytest.approx(9.0)

    def test_graphml_out_of_range_cvss_rejected(self):
        graphml = b"""<?xml version='1.0' encoding='utf-8'?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <key id="k1" for="node" attr.name="cvss_type" attr.type="string" />
  <graph edgedefault="directed">
    <node id="plc_1">
      <data key="k1">99</data>
    </node>
  </graph>
</graphml>"""
        with pytest.raises(ValueError, match=r"'cvss_type' must be in \[0\.0, 10\.0\]"):
            load_topology_from_bytes(graphml, "topology.graphml")

    def test_unsupported_extension_rejected(self):
        with pytest.raises(ValueError, match="Unsupported topology format"):
            load_topology_from_bytes(b"x", "topology.xyz")


class TestRelationshipNormalization:
    def test_dict_relationship_normalizes(self):
        rel = normalize_relationship({"source": "a", "target": "b", "type": "connects-to"})
        assert rel == ("a", "b", "connects-to", False, {})

    def test_unknown_rel_type_is_preserved_for_validation(self):
        # A typo'd relationship type is preserved so validate_graph can
        # reject it with an actionable error instead of silently becoming a
        # generic "connects-to" edge.
        rel = normalize_relationship(["a", "b", "teleports-to", False])
        assert rel[2] == "teleports-to"

    def test_validate_graph_rejects_unknown_rel_type(self):
        assets = {"a": {"kind": "device"}, "b": {"kind": "device"}}
        rels = [("a", "b", "teleports-to", False, {})]
        with pytest.raises(ValueError, match="unknown relationship type"):
            validate_graph(assets, rels, "test")
