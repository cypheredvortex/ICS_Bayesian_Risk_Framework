"""Regression tests for the network-topology diagram layout.

The generated ``<plant>.png`` diagrams must satisfy a hard visual invariant:
every asset node is fully contained inside the rectangle of the Purdue
level / security zone it is assigned to, with a visible margin from every
separator line.  A node that straddles a band boundary makes it ambiguous
which architectural level the asset belongs to, so this is enforced at the
layout-algorithm level (``_zone_band_positions`` in
``tools/generate_ics_diagrams.py``) and pinned down here for every topology
in ``ics_topologies/``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPOLOGIES = ROOT / "ics_topologies"

_spec = importlib.util.spec_from_file_location("gen", ROOT / "tools" / "generate_ics_diagrams.py")
gen = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(gen)


def _canonicals() -> list[tuple[str, dict]]:
    folders = sorted(p for p in TOPOLOGIES.iterdir() if p.is_dir())
    return [(folder.name, gen.load_canonical(folder)) for folder in folders]


def _node_margins(name: str, canonical: dict) -> dict[str, dict[str, float]]:
    """Per-asset margins (top/bottom/left/right) to its zone band edges."""
    positions, geometry = gen._zone_band_positions(canonical)
    band_edges = {
        zone: (
            x_anchor,
            x_anchor + gen.NET_BAND_W,
            y_centre - height / 2.0,
            y_centre + height / 2.0,
        )
        for zone, (x_anchor, y_centre, height) in geometry.items()
    }
    half_w, half_h = gen.NET_BOX_W / 2.0, gen.NET_NODE_H / 2.0
    margins: dict[str, dict[str, float]] = {}
    for asset in canonical["assets"]:
        x, y = positions[asset["id"]]
        zone = asset.get("zone", next(iter(geometry)))
        bx0, bx1, by0, by1 = band_edges[zone]
        margins[asset["id"]] = {
            "top": y + half_h - by0,  # node top above band top edge
            "bottom": by1 - (y - half_h),  # band bottom edge below node bottom
            "left": x - half_w - bx0,
            "right": bx1 - (x + half_w),
        }
    return margins


def test_every_node_fully_inside_its_zone_band() -> None:
    """The hard rule: whole node box inside its band, no touching/straddling."""
    guaranteed = gen.NET_BAND_PAD + gen.NET_ROW_STEP / 2.0 - gen.NET_NODE_H / 2.0
    for name, canonical in _canonicals():
        margins = _node_margins(name, canonical)
        assert margins, f"{name}: no assets to place"
        for asset_id, m in margins.items():
            assert m["top"] >= guaranteed - 1e-9, f"{name}: {asset_id} straddles the band TOP boundary"
            assert m["bottom"] >= guaranteed - 1e-9, f"{name}: {asset_id} straddles the band BOTTOM boundary"
            assert m["left"] >= 0.4, f"{name}: {asset_id} too close to the band LEFT edge"
            assert m["right"] >= 0.4, f"{name}: {asset_id} too close to the band RIGHT edge"


def test_bands_ordered_top_down_by_purdue_level() -> None:
    """Highest Purdue level (L5/L4) renders at the top, L0 at the bottom."""
    for name, canonical in _canonicals():
        zones = gen._ordered_zones(canonical)
        levels = [gen._zone_purdue(zone) for zone in zones]
        assert levels == sorted(levels, reverse=True), (
            f"{name}: zone bands are not ordered by Purdue level: {levels}"
        )
        _, geometry = gen._zone_band_positions(canonical)
        band_order = [z["id"] for z in zones if z["id"] in geometry]
        assert band_order, f"{name}: no zone bands were laid out"
        # Each band's centre must be strictly below the previous band's centre
        # (top-down coordinates grow downward), i.e. bands never overlap.
        centres = [geometry[z][1] for z in band_order]
        assert all(b > a for a, b in zip(centres, centres[1:])), (
            f"{name}: consecutive zone bands overlap vertically"
        )


def test_no_two_nodes_overlap() -> None:
    for name, canonical in _canonicals():
        positions, _ = gen._zone_band_positions(canonical)
        rects: list[tuple[str, tuple[float, float, float, float]]] = []
        for asset in canonical["assets"]:
            x, y = positions[asset["id"]]
            rects.append(
                (asset["id"], (x - gen.NET_BOX_W / 2, y - gen.NET_NODE_H / 2, gen.NET_BOX_W, gen.NET_NODE_H))
            )
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                aid, (ax0, ay0, aw, ah) = rects[i]
                bid, (bx0, by0, bw, bh) = rects[j]
                overlap_x = ax0 < bx0 + bw - 1e-9 and bx0 < ax0 + aw - 1e-9
                overlap_y = ay0 < by0 + bh - 1e-9 and by0 < ay0 + ah - 1e-9
                assert not (overlap_x and overlap_y), f"{name}: nodes {aid} and {bid} overlap"


def test_every_asset_belongs_to_a_declared_zone() -> None:
    for name, canonical in _canonicals():
        zone_ids = {z["id"] for z in canonical["zones"]}
        for asset in canonical["assets"]:
            assert asset.get("zone") in zone_ids, f"{name}: {asset['id']} in undeclared zone"


def test_all_topologies_render_to_png(tmp_path: Path) -> None:
    """Smoke test: every topology produces a non-empty PNG via the real path."""
    for name, canonical in _canonicals():
        out = tmp_path / f"{name}.png"
        gen.draw_network_topology(canonical, out)
        assert out.exists() and out.stat().st_size > 10_000, f"{name}: PNG missing or empty"
