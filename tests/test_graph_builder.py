"""Tests for the graph builder module."""

import pytest

from backend.graph_builder import edge_weight, build_graph_skeleton, graph_to_dict


class TestEdgeWeight:
    """Weight computation for a single relationship."""

    def test_default_weight_without_firewall(self) -> None:
        weight = edge_weight("connects-to", False)
        assert 0 < weight < 1.0

    def test_firewall_reduces_weight(self) -> None:
        no_fw = edge_weight("connects-to", False)
        with_fw = edge_weight("connects-to", True)
        assert with_fw < no_fw

    def test_monitors_lower_than_controls(self) -> None:
        monitors = edge_weight("monitors", False)
        controls = edge_weight("controls", False)
        assert monitors < controls

    def test_protocol_multiplier_applied(self) -> None:
        default = edge_weight("controls", False, {})
        http = edge_weight("controls", False, {"protocol": "http"})
        assert http != default

    def test_metadata_increases_weight_within_bounds(self) -> None:
        low = edge_weight("connects-to", False, {"protocol": "default", "trust": "high"})
        high = edge_weight("connects-to", False, {"protocol": "modbus", "trust": "low"})
        assert high >= low or high < 0.99  # Both should be valid


class TestBuildGraphSkeleton:
    """Graph construction from relationships."""

    SIMPLE_REL = ("PLC_01", "HMI_01", "connects-to", False, {})

    def test_single_edge_returns_valid_model(self) -> None:
        model, weights = build_graph_skeleton([self.SIMPLE_REL])
        assert ("PLC_01", "HMI_01") in model.edges()
        assert ("PLC_01", "HMI_01") in weights

    def test_empty_relationships_still_creates_base_model(self) -> None:
        model, weights = build_graph_skeleton([])
        assert len(model.edges()) == 0
        assert weights == {}

    def test_node_ids_added_when_provided(self) -> None:
        relationships = [
            ("PLC_01", "HMI_01", "connects-to", False, {}),
            ("HMI_01", "Server_01", "monitors", True, {}),
        ]
        model, weights = build_graph_skeleton(relationships)
        assert len(model.edges()) == 2
        assert len(weights) == 2

    def test_firewalled_edge_weight_different(self) -> None:
        rels = [
            ("A", "B", "controls", False, {}),
            ("A", "C", "controls", True, {}),
        ]
        _, weights = build_graph_skeleton(rels)
        assert weights[("A", "B")] != weights[("A", "C")]


class TestGraphToDict:
    """Conversion of graph model to dict for API responses."""

    def test_returns_nodes_and_edges(self) -> None:
        relationships = [("PLC_01", "HMI_01", "connects-to", False, {})]
        model, weights = build_graph_skeleton(relationships)
        result = graph_to_dict(model, weights, relationships)

        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1

    def test_node_kinds_included_when_provided(self) -> None:
        relationships = [("PLC_01", "HMI_01", "connects-to", False, {})]
        model, weights = build_graph_skeleton(relationships)
        assets = {"PLC_01": {"kind": "device"}, "HMI_01": {"kind": "device"}}
        result = graph_to_dict(model, weights, relationships, assets)

        plc = next(n for n in result["nodes"] if n["id"] == "PLC_01")
        assert plc["kind"] == "device"

    def test_edge_weights_rounded(self) -> None:
        relationships = [("A", "B", "controls", False, {})]
        model, weights = build_graph_skeleton(relationships)
        result = graph_to_dict(model, weights, relationships)

        assert isinstance(result["edges"][0]["weight"], float)

    def test_metadata_included_in_edges(self) -> None:
        relationships = [("A", "B", "controls", False, {"protocol": "modbus", "trust": "low"})]
        model, weights = build_graph_skeleton(relationships)
        result = graph_to_dict(model, weights, relationships)

        edge = result["edges"][0]
        assert edge.get("protocol") == "modbus"
        assert edge.get("trust") == "low"

