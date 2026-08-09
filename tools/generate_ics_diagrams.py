"""
tools/generate_ics_diagrams.py - Generate the two PNG visualizations for every
ICS folder in ics_topologies/ from its canonical JSON:

  * ``<folder>.png``          - network / logical topology (assets, zones,
                                connections, communication paths)
  * ``<folder>_ics_system.png`` - physical industrial process diagram (what
                                the system actually does)

Run:  python tools/generate_ics_diagrams.py
"""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parents[1]
TOPOLOGIES = ROOT / "ics_topologies"

# ---- palette ----
KIND_COLORS = {
    "device": "#4C78A8",
    "human": "#8E44AD",
    "physical": "#2E9E6B",
}
REL_COLORS = {
    "controls": "#C0392B",
    "monitors": "#1F8A70",
    "actuates": "#E67E22",
    "connects-to": "#7F8C8D",
    "programs / operates": "#8E44AD",
}
ZONE_COLORS = {
    "Internet": "#ff6b6b",
    "Enterprise": "#4dabf7",
    "DMZ": "#ffa94d",
    "Control": "#845ef7",
    "Field": "#20c997",
    "Utility": "#e599f7",
    "Substation": "#ffd43b",
    "Process": "#ff922b",
    "Protection": "#da77f2",
    "ShopFloor": "#845ef7",
    "Cell": "#fcc419",
    "Safety": "#da77f2",
    "ControlCenter": "#ff6b6b",
    "RemoteSite": "#ffa94d",
    "DCS": "#845ef7",
    "SIS": "#da77f2",
    "Remote": "#ff922b",
}


def load_canonical(folder: Path) -> dict:
    with (folder / f"{folder.name}.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _wrap(text: str, width: int) -> str:
    return "\n".join(textwrap.wrap(text, width) or [text])


def _zone_band_positions(canonical: dict, max_per_row: int = 6) -> dict[str, tuple[float, float]]:
    """Zone-band layout: first zone at the top, assets spread horizontally.

    Returns a dict mapping asset id -> (x, y) on a 0..10 horizontal scale with
    generous per-node spacing so labels do not collide.
    """
    positions: dict[str, tuple[float, float]] = {}
    zone_order = [z["id"] for z in canonical["zones"]]
    by_zone: dict[str, list[dict]] = {z: [] for z in zone_order}
    for asset in canonical["assets"]:
        by_zone.setdefault(asset.get("zone", zone_order[0] if zone_order else ""), []).append(asset)
    y = 0.0
    band_height = 1.0
    for zone in zone_order:
        members = by_zone.get(zone, [])
        if not members:
            continue
        rows = [members[i : i + max_per_row] for i in range(0, len(members), max_per_row)]
        for row_index, row in enumerate(rows):
            spacing = 1.18
            total = spacing * (len(row) - 1)
            x_start = (10.0 - total) / 2.0
            for index, asset in enumerate(row):
                positions[asset["id"]] = (x_start + index * spacing, y + row_index * band_height * 0.92)
        y += band_height * len(rows)
    return positions


def _box_extent(x: float, y: float, w: float, h: float) -> tuple[float, float, float, float]:
    return x - w / 2, y - h / 2, w, h


def _clipped_arrow(
    ax,
    p1: tuple[float, float],
    p2: tuple[float, float],
    *,
    color: str,
    lw: float,
    box_w: float,
    box_h: float,
    style: str = "-|>",
    zorder: int = 3,
):
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = (dx * dx + dy * dy) ** 0.5
    if length == 0:
        return
    # shrink start/end by the box half-extents (projected on the direction)
    start_frac = max(box_w / 2 / abs(dx) if abs(dx) > 1e-6 else 0, box_h / 2 / abs(dy) if abs(dy) > 1e-6 else 0)
    end_frac = start_frac
    margin = 0.04
    sx = x1 + dx * (start_frac / length)
    sy = y1 + dy * (start_frac / length)
    ex = x2 - dx * ((end_frac + margin) / length)
    ey = y2 - dy * ((end_frac + margin) / length)
    ax.add_patch(
        FancyArrowPatch(
            (sx, sy),
            (ex, ey),
            arrowstyle=style,
            mutation_scale=14,
            linewidth=lw,
            color=color,
            zorder=zorder,
            shrinkA=0,
            shrinkB=0,
        )
    )


def draw_network_topology(canonical: dict, out_path: Path) -> None:
    """Network / logical topology diagram with zone bands."""
    assets = canonical["assets"]
    connections = canonical["connections"]
    positions = _zone_band_positions(canonical)
    zone_order = [z["id"] for z in canonical["zones"]]
    by_zone = {z: [] for z in zone_order}
    for asset in assets:
        by_zone.setdefault(asset.get("zone", zone_order[0] if zone_order else ""), []).append(asset)

    box_w, box_h = 0.80, 0.66
    fig_w, fig_h = 24.0, 14.0
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    y_top = len(zone_order) * 1.42
    ax.set_xlim(-1.6, 11.6)
    ax.set_ylim(-1.1, y_top + 0.5)

    # zone bands
    for index, zone in enumerate(zone_order):
        band_y = y_top - (index + 1) * 1.42
        members = by_zone.get(zone, [])
        color = ZONE_COLORS.get(zone, "#CCCCCC")
        ax.add_patch(
            Rectangle(
                (-1.6, band_y - 0.10),
                13.2,
                1.42,
                facecolor=color,
                alpha=0.09,
                edgecolor=color,
                linewidth=1.6,
                zorder=0,
            )
        )
        zone_name = next(z["name"] for z in canonical["zones"] if z["id"] == zone)
        ax.text(
            -1.42,
            band_y + 0.55,
            f"{zone_name}  ({len(members)})",
            fontsize=14,
            fontweight="bold",
            color="#333333",
            ha="left",
            va="center",
            zorder=1,
        )

    # edges first (behind nodes)
    for conn in connections:
        p1 = positions.get(conn["source"])
        p2 = positions.get(conn["target"])
        if not p1 or not p2:
            continue
        rel_type = conn.get("type", "connects-to")
        color = REL_COLORS.get(rel_type, "#7F8C8D")
        _clipped_arrow(
            ax,
            (p1[0], y_top - p1[1]),
            (p2[0], y_top - p2[1]),
            color=color,
            lw=1.4,
            box_w=box_w,
            box_h=box_h,
            zorder=2,
        )

    # nodes
    for asset in assets:
        x, y_raw = positions[asset["id"]]
        y = y_top - y_raw
        kind = asset.get("kind", "device")
        color = KIND_COLORS.get(kind, "#4C78A8")
        rect = FancyBboxPatch(
            (x - box_w / 2, y - box_h / 2),
            box_w,
            box_h,
            boxstyle="round,pad=0.02",
            facecolor=color,
            alpha=0.92,
            edgecolor="#1a1a1a",
            linewidth=1.2,
            zorder=4,
        )
        ax.add_patch(rect)
        wrapped_name = _wrap(asset["name"], 13)
        ax.text(
            x,
            y + 0.10,
            wrapped_name,
            fontsize=9,
            fontweight="bold",
            color="white",
            ha="center",
            va="center",
            zorder=5,
            linespacing=1.1,
        )
        ax.text(
            x,
            y - 0.22,
            asset["id"],
            fontsize=7,
            color="#E8E8E8",
            ha="center",
            va="center",
            zorder=5,
            family="monospace",
        )

    ax.set_title(
        f"{canonical['metadata']['name']} — Network Topology",
        fontsize=26,
        fontweight="bold",
        pad=26,
    )
    ax.text(
        5.0,
        y_top + 0.22,
        f"{len(assets)} assets  •  {len(connections)} connections  •  "
        f"{len(zone_order)} zones",
        fontsize=13,
        ha="center",
        color="#555555",
    )
    ax.set_axis_off()

    # legend
    rel_patches = [mpatches.Patch(color=c, label=t) for t, c in REL_COLORS.items()]
    kind_patches = [mpatches.Patch(color=c, label=k.title()) for k, c in KIND_COLORS.items()]
    legend1 = ax.legend(
        handles=rel_patches,
        title="Relationship types",
        loc="lower left",
        bbox_to_anchor=(0.0, 0.0),
        fontsize=11,
        title_fontsize=12,
        framealpha=0.9,
    )
    ax.add_artist(legend1)
    ax.legend(
        handles=kind_patches,
        title="Asset kinds",
        loc="lower right",
        bbox_to_anchor=(1.0, 0.0),
        fontsize=11,
        title_fontsize=12,
        framealpha=0.9,
    )

    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------------------
# ICS system / process diagrams (hand-laid-out per industry)
# ---------------------------------------------------------------------------

# Box -> {text artists} ownership, used by tools/check_overlaps.py to
# distinguish intended title/sub-text inside a box from real collisions.
BOX_TEXT_OWNERSHIP: dict[int, set[int]] = {}

# Readability / spacing pass: every element is stretched away from the canvas
# centre (5, 5) so boxes, sensors and bands gain breathing room while keeping
# their relative topology.  Box dimensions scale with the same factors, so the
# larger boxes and larger fonts read clearly without re-laying-out every
# diagram by hand.
SCALE_X = 1.14
SCALE_Y = 1.20


def _tx(x: float) -> float:
    """Stretch an x coordinate away from the centre."""
    return 5.0 + (x - 5.0) * SCALE_X


def _ty(y: float) -> float:
    """Stretch a y coordinate away from the centre."""
    return 5.0 + (y - 5.0) * SCALE_Y


def _proc_box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    sub: str = "",
    *,
    facecolor: str = "#DCE9F7",
    edgecolor: str = "#2C5F8A",
    title_size: float = 15,
    sub_size: float = 11,
    text_color: str = "#1a1a1a",
    zorder: int = 4,
    rounded: bool = True,
):
    x, y = _tx(x), _ty(y)
    w, h = w * SCALE_X, h * SCALE_Y
    boxstyle = "round,pad=0.01" if rounded else "square,pad=0"
    rect = FancyBboxPatch(
        (x - w / 2, y - h / 2),
        w,
        h,
        boxstyle=boxstyle,
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=2.0,
        zorder=zorder,
    )
    ax.add_patch(rect)
    owners: set[int] = set()
    if title:
        t1 = ax.text(
            x,
            y + (0.14 if sub else 0.0),
            _wrap(title, 14),
            fontsize=title_size,
            fontweight="bold",
            ha="center",
            va="center",
            color=text_color,
            zorder=zorder + 1,
            linespacing=1.2,
        )
        owners.add(id(t1))
    if sub:
        t2 = ax.text(
            x,
            y - 0.38,
            _wrap(sub, 26),
            fontsize=sub_size,
            ha="center",
            va="center",
            color="#444444",
            zorder=zorder + 1,
            family="monospace",
        )
        owners.add(id(t2))
    BOX_TEXT_OWNERSHIP[id(rect)] = owners


def _process_arrow(
    ax,
    p1: tuple[float, float],
    p2: tuple[float, float],
    *,
    color: str = "#1F6FB2",
    lw: float = 3.2,
    style: str = "-|>",
    zorder: int = 3,
):
    ax.add_patch(
        FancyArrowPatch(
            (_tx(p1[0]), _ty(p1[1])),
            (_tx(p2[0]), _ty(p2[1])),
            arrowstyle=style,
            mutation_scale=22,
            linewidth=lw,
            color=color,
            zorder=zorder,
            shrinkA=0,
            shrinkB=0,
        )
    )


def _signal(
    ax,
    p1: tuple[float, float],
    p2: tuple[float, float],
    *,
    color: str = "#6B7280",
    lw: float = 1.4,
    style: str = "-",
    zorder: int = 2,
):
    ax.add_patch(
        FancyArrowPatch(
            (_tx(p1[0]), _ty(p1[1])),
            (_tx(p2[0]), _ty(p2[1])),
            arrowstyle="-",
            linewidth=lw,
            color=color,
            zorder=zorder,
            shrinkA=0,
            shrinkB=0,
            linestyle=style,
        )
    )


def _sensor_marker(ax, x: float, y: float, label: str, color: str = "#E9B949") -> None:
    x, y = _tx(x), _ty(y)
    ax.add_patch(
        mpatches.RegularPolygon(
            (x, y),
            numVertices=4,
            radius=0.20,
            orientation=0.785,
            facecolor=color,
            edgecolor="#5a4a12",
            linewidth=1.5,
            zorder=5,
        )
    )
    ax.text(x, y - 0.40, _wrap(label, 16), fontsize=9.5, ha="center", va="top", color="#333333", zorder=6)


def _layer_band(ax, x: float, y: float, w: float, h: float, label: str, color: str) -> None:
    x, y = _tx(x), _ty(y)
    w, h = w * SCALE_X, h * SCALE_Y
    ax.add_patch(
        Rectangle(
            (x - w / 2, y - h / 2),
            w,
            h,
            facecolor=color,
            alpha=0.10,
            edgecolor=color,
            linewidth=1.8,
            linestyle=(0, (4, 3)),
            zorder=0,
        )
    )
    # rotated label in a left gutter, clear of all boxes
    ax.text(
        x - w / 2 - 0.75 * SCALE_X,
        y,
        label,
        fontsize=13.5,
        fontweight="bold",
        color=color,
        ha="center",
        va="center",
        rotation=90,
        zorder=6,
        clip_on=False,
        bbox=dict(facecolor="white", alpha=0.9, edgecolor="none", pad=2),
    )


def _finish(fig, ax, path: Path, title: str, subtitle: str) -> None:
    # The stretch moves content beyond the original 0..10 window.
    ax.set_xlim(-1.8, 11.8)
    ax.set_ylim(-0.8, 11.0)
    ax.set_aspect("equal")
    ax.set_axis_off()
    fig.suptitle(title, fontsize=34, fontweight="bold", y=0.992, color="#111111")
    fig.text(0.5, 0.928, subtitle, fontsize=15.5, ha="center", color="#555555")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white", pad_inches=0.5)
    plt.close(fig)


def draw_water_system(canonical: dict, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(25.6, 14.4))
    # --- layers ---
    _layer_band(ax, 2.1, 8.0, 3.6, 2.4, "SUPERVISORY & CONTROL ROOM", "#845ef7")
    _layer_band(ax, 7.3, 8.0, 5.0, 2.4, "CONTROL NETWORK (Purdue L2)", "#4C78A8")
    _layer_band(ax, 5.0, 4.0, 9.6, 6.4, "WATER TREATMENT PROCESS (Purdue L0-L1)", "#2E9E6B")

    # --- control room (left) ---
    _proc_box(ax, 1.2, 8.8, 1.5, 0.9, "SCADA Server", "WTP-DMZ-SCADA-001", facecolor="#EFE7FB")
    _proc_box(ax, 3.0, 8.8, 1.4, 0.9, "Control Room\nOperator", "WTP-HUM-OPR-001", facecolor="#F0E6F7")
    _proc_box(ax, 2.1, 7.2, 1.9, 0.8, "HMI Console", "WTP-CTRL-HMI-001", facecolor="#EFE7FB")
    _proc_box(ax, 2.1, 6.0, 1.9, 0.8, "Control Switch", "WTP-CTRL-SW-001", facecolor="#DCE9F7")

    # --- process train (right, top to bottom) ---
    _proc_box(ax, 6.2, 8.8, 1.9, 1.0, "RAW WATER\nSOURCE", "", facecolor="#BFE3C0", edgecolor="#2F7D32")
    _process_arrow(ax, (7.15, 8.3), (7.15, 7.6), color="#1F6FB2")
    _proc_box(ax, 6.2, 7.4, 1.9, 0.9, "Intake Pumping", "PUMP-001 • VALVE-001", facecolor="#D8EFDA")
    _proc_box(ax, 8.4, 7.4, 1.7, 0.9, "Intake PLC", "WTP-CTRL-PLC-001", facecolor="#DCE9F7")
    _process_arrow(ax, (7.15, 6.95), (7.15, 6.2), color="#1F6FB2")
    _proc_box(ax, 6.2, 5.9, 1.9, 0.9, "Filtration\n(backwash)", "VALVE-002 • TURB-004", facecolor="#D8EFDA")
    _proc_box(ax, 8.4, 5.9, 1.7, 0.9, "Filtration PLC", "WTP-CTRL-PLC-002", facecolor="#DCE9F7")
    _process_arrow(ax, (7.15, 5.45), (7.15, 4.7), color="#1F6FB2")
    _proc_box(ax, 6.2, 4.4, 1.9, 0.9, "Chemical Dosing", "PUMP-001 • pH-003", facecolor="#D8EFDA")
    _proc_box(ax, 8.4, 4.4, 1.9, 0.9, "Dosing PLC", "WTP-CTRL-PLC-003", facecolor="#DCE9F7")
    _process_arrow(ax, (7.15, 3.95), (7.15, 3.2), color="#1F6FB2")
    _proc_box(ax, 6.2, 2.9, 1.9, 0.9, "Clearwell Storage", "TANK LEVEL", facecolor="#D8EFDA")
    _process_arrow(ax, (7.15, 2.45), (7.15, 1.7), color="#1F6FB2")
    _proc_box(ax, 6.2, 1.4, 1.9, 0.9, "Distribution\nPumping", "PUMP-002 • VFD-001", facecolor="#D8EFDA")
    _proc_box(ax, 8.4, 1.4, 1.9, 0.9, "Distribution PLC", "WTP-CTRL-PLC-004", facecolor="#DCE9F7")

    # --- field sensors ---
    _sensor_marker(ax, 4.6, 7.4, "Flow\nSENSOR-001")
    _sensor_marker(ax, 4.6, 5.9, "Turbidity\nSENSOR-004")
    _sensor_marker(ax, 4.6, 4.4, "pH\nSENSOR-003")
    _sensor_marker(ax, 4.6, 1.4, "Pressure\nSENSOR-002")

    # --- control signals ---
    for plc_x, plc_y, target_x, target_y in [
        (2.1, 6.0, 6.7, 7.4),   # control switch -> intake
        (2.1, 6.0, 6.7, 5.9),   # -> filtration
        (2.1, 6.0, 6.7, 4.4),   # -> dosing
        (2.1, 6.0, 6.7, 1.4),   # -> distribution
    ]:
        _signal(ax, (plc_x + 0.95, plc_y), (target_x - 0.95, target_y), color="#845ef7")
    _signal(ax, (3.0, 8.35), (3.0, 7.65), color="#8E44AD")
    _signal(ax, (2.1, 8.35), (1.95, 7.65), color="#6B7280")

    # PLC <-> process signals
    for plc_x, plc_y, dev_x, dev_y in [
        (8.4, 7.4, 7.1, 7.4), (8.4, 5.9, 7.1, 5.9),
        (8.4, 4.4, 7.1, 4.4), (8.4, 1.4, 7.1, 1.4),
    ]:
        _signal(ax, (plc_x - 0.85, plc_y), (dev_x + 0.95, dev_y), color="#4C78A8")

    # sensor signals
    for sx, sy, tx, ty in [(4.75, 7.4, 6.7, 7.4), (4.75, 5.9, 6.7, 5.9), (4.75, 4.4, 6.7, 4.4), (4.75, 1.4, 6.7, 1.4)]:
        _signal(ax, (sx, sy), (tx, ty), color="#E9B949")

    _finish(
        fig,
        ax,
        out_path,
        "Water Treatment Plant — Industrial Process",
        "Raw water intake → filtration → chemical dosing → storage → distribution  (Purdue reference model)",
    )


def draw_substation_system(canonical: dict, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(25.6, 14.4))
    _layer_band(ax, 2.0, 7.9, 3.4, 2.6, "UTILITY CONTROL CENTER", "#e599f7")
    _layer_band(ax, 8.2, 8.0, 3.4, 2.4, "SUBSTATION LAN (IEC 61850)", "#ffd43b")
    _layer_band(ax, 5.0, 3.7, 9.6, 5.9, "HIGH-VOLTAGE PROCESS / PROTECTION", "#ff922b")

    _proc_box(ax, 1.1, 8.45, 1.6, 0.9, "Substation\nFirewall", "SUB-FW-001", facecolor="#F3E9F9")
    _proc_box(ax, 2.85, 8.45, 1.5, 0.9, "Control Room\nDispatcher", "SUB-HUM-DSP-001", facecolor="#F0E6F7")
    _proc_box(ax, 2.0, 6.7, 1.9, 0.8, "SCADA Gateway", "SUB-SCADA-001", facecolor="#F3E9F9")
    _proc_box(ax, 2.0, 5.7, 1.9, 0.8, "Substation HMI", "SUB-HMI-001", facecolor="#F3E9F9")
    _proc_box(ax, 2.0, 4.7, 1.9, 0.8, "Substation Switch", "SUB-SW-001", facecolor="#DCE9F7")

    # power column (left of centre)
    power_x = 4.6
    _proc_box(ax, power_x, 8.6, 1.8, 0.9, "TRANSMISSION\nLINE (230 kV)", "", facecolor="#FDEBD0", edgecolor="#B9770E")
    _process_arrow(ax, (power_x + 0.9, 8.15), (power_x + 0.9, 7.5), color="#B9770E")
    _proc_box(ax, power_x, 7.2, 1.8, 0.9, "Circuit Breaker", "SUB-CB-001", facecolor="#FBE5C8")
    _process_arrow(ax, (power_x + 0.9, 6.75), (power_x + 0.9, 6.1), color="#B9770E")
    _proc_box(ax, power_x, 5.8, 1.8, 0.9, "Power Transformer\n100 MVA", "SUB-XFMR-001", facecolor="#FBE5C8")
    _process_arrow(ax, (power_x + 0.9, 5.35), (power_x + 0.9, 4.7), color="#B9770E")
    _proc_box(ax, power_x, 4.4, 1.8, 0.9, "Distribution Bus", "SUB-DIS-001", facecolor="#FBE5C8")
    for i, target_y in enumerate([3.5, 2.6, 1.7]):
        _process_arrow(ax, (power_x + 0.9, 3.95), (power_x + 0.9, target_y + 0.4), color="#B9770E")
        _proc_box(ax, power_x, target_y, 1.8, 0.8, f"Outgoing Feeder {i + 1}", "FEEDER", facecolor="#FBE5C8")

    # protection & instrumentation column (right)
    _proc_box(ax, 8.7, 7.6, 1.8, 1.0, "Protection IEDs\n(line/trsf/bus)", "SUB-IED-001..003", facecolor="#F5E1F7")
    _proc_box(ax, 8.7, 6.3, 1.6, 0.9, "Merging Unit", "SUB-MU-001", facecolor="#F5E1F7")
    _proc_box(ax, 8.7, 5.2, 1.6, 0.8, "PMU", "SUB-PMU-001", facecolor="#F5E1F7")
    _proc_box(ax, 8.7, 4.2, 1.6, 0.8, "RTU", "SUB-RTU-001", facecolor="#DCE9F7")

    # field instrumentation between the two columns
    _sensor_marker(ax, 6.2, 7.2, "VT\nSUB-VT-001")
    _sensor_marker(ax, 6.2, 5.8, "CT\nSUB-CT-001")
    _sensor_marker(ax, 6.2, 4.4, "Temp\nSENSOR-001")
    _sensor_marker(ax, 6.2, 3.4, "SF6\nSENSOR-002")
    for ty in [7.2, 5.8, 4.4, 3.4]:
        _signal(ax, (6.04, ty), (5.62, ty), color="#E9B949", style=(0, (3, 2)))
        _signal(ax, (6.36, ty), (7.9, 6.3), color="#E9B949", style=(0, (3, 2)))

    # control / protection signals
    _signal(ax, (3.0, 8.0), (2.95, 7.15), color="#8E44AD")
    _signal(ax, (2.0, 8.0), (2.0, 7.15), color="#6B7280")
    _signal(ax, (7.9, 7.6), (7.9, 6.75), color="#da77f2")
    _signal(ax, (7.9, 6.3), (7.9, 5.6), color="#da77f2")
    _signal(ax, (5.62, 7.2), (7.9, 6.6), color="#da77f2", style=(0, (3, 2)))
    _signal(ax, (5.62, 5.8), (7.9, 6.3), color="#da77f2", style=(0, (3, 2)))
    _signal(ax, (5.62, 4.4), (7.9, 6.0), color="#da77f2", style=(0, (3, 2)))

    # SCADA switch -> RTU, routed BELOW the power column (no box crossings)
    _signal(ax, (2.95, 4.7), (2.95, 1.2), color="#845ef7", style=(0, (5, 3)))
    _signal(ax, (2.95, 1.2), (8.35, 1.2), color="#845ef7", style=(0, (5, 3)))
    _signal(ax, (8.35, 1.2), (8.35, 4.2), color="#845ef7", style=(0, (5, 3)))
    # IEDs <-> RTU on the right side, clear of all boxes
    _signal(ax, (9.55, 7.1), (9.55, 4.6), color="#da77f2", style=(0, (3, 2)))

    _finish(
        fig,
        ax,
        out_path,
        "Electrical Substation — Industrial Process",
        "230 kV transmission → breaker → transformer → bus → feeders  (IEC 61850 protection & control)",
    )


def draw_manufacturing_system(canonical: dict, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(25.6, 14.4))
    _layer_band(ax, 2.0, 8.0, 3.4, 2.4, "SUPERVISORY (MES / ERP / SCADA)", "#4dabf7")
    _layer_band(ax, 7.5, 8.0, 4.6, 2.4, "SHOP FLOOR NETWORK", "#845ef7")
    _layer_band(ax, 5.0, 4.0, 9.6, 6.4, "PRODUCTION LINE (WELDING → ASSEMBLY → QC → PACK)", "#2E9E6B")

    _proc_box(ax, 1.1, 8.8, 1.7, 0.9, "MES Server", "MFG-ENT-MES-001", facecolor="#E1EEFB")
    _proc_box(ax, 3.0, 8.8, 1.6, 0.9, "Production\nSupervisor", "MFG-HUM-SUP-001", facecolor="#F0E6F7")
    _proc_box(ax, 2.0, 7.3, 1.9, 0.8, "SCADA Server", "MFG-SF-SCADA-001", facecolor="#E1EEFB")
    _proc_box(ax, 2.0, 6.2, 1.9, 0.8, "Production HMI", "MFG-SF-HMI-001", facecolor="#E1EEFB")
    _proc_box(ax, 2.0, 5.1, 1.9, 0.8, "Shop Floor Switch", "MFG-SF-SW-001", facecolor="#DCE9F7")

    # production line
    _proc_box(ax, 5.6, 8.5, 1.6, 0.9, "RAW MATERIAL\nSTOCK", "", facecolor="#BFE3C0", edgecolor="#2F7D32")
    _process_arrow(ax, (6.4, 8.05), (6.4, 7.4), color="#1F6FB2")
    _proc_box(ax, 5.6, 7.1, 1.6, 0.9, "Conveyor Feed", "VFD-001 • MOTOR-001", facecolor="#D8EFDA")
    _process_arrow(ax, (6.4, 6.65), (6.4, 6.0), color="#1F6FB2")
    _proc_box(ax, 5.6, 5.7, 1.7, 1.0, "Welding Cell 1", "ROBOT-001 • POS-001", facecolor="#D8EFDA")
    _proc_box(ax, 7.7, 5.7, 1.5, 0.9, "Cell 1 PLC", "MFG-CELL1-PLC-001", facecolor="#DCE9F7")
    _process_arrow(ax, (6.45, 5.2), (6.45, 4.5), color="#1F6FB2")
    _proc_box(ax, 5.6, 4.2, 1.7, 1.0, "Assembly Cell 2", "HMI-001 • ACT-001", facecolor="#D8EFDA")
    _proc_box(ax, 7.7, 4.2, 1.5, 0.9, "Cell 2 PLC", "MFG-CELL2-PLC-001", facecolor="#DCE9F7")
    _process_arrow(ax, (6.45, 3.7), (6.45, 3.0), color="#1F6FB2")
    _proc_box(ax, 5.6, 2.7, 1.6, 0.9, "Quality Control\n(vision)", "SENSOR-002", facecolor="#D8EFDA")
    _process_arrow(ax, (6.4, 2.25), (6.4, 1.6), color="#1F6FB2")
    _proc_box(ax, 5.6, 1.3, 1.6, 0.9, "Packaging", "PACK LINE", facecolor="#D8EFDA")

    # safety
    _proc_box(ax, 8.9, 3.1, 1.7, 1.0, "Safety PLC", "MFG-SAF-PLC-001", facecolor="#F5E1F7")
    _sensor_marker(ax, 8.9, 4.6, "Light Curtain\nSAF-LC-001")
    _sensor_marker(ax, 8.9, 1.9, "E-Stop\nSAF-ESTOP-001")
    _sensor_marker(ax, 4.1, 5.7, "Proximity\nSENSOR-001")

    _signal(ax, (2.95, 5.1), (6.6, 6.3), color="#845ef7")
    _signal(ax, (2.95, 5.1), (6.6, 4.8), color="#845ef7")
    _signal(ax, (3.0, 8.35), (2.95, 7.7), color="#8E44AD")
    _signal(ax, (2.0, 8.35), (2.0, 7.7), color="#6B7280")
    _signal(ax, (8.0, 5.7), (8.85, 4.1), color="#da77f2")
    _signal(ax, (8.0, 4.2), (8.85, 3.65), color="#da77f2")
    _signal(ax, (8.9, 3.6), (8.9, 2.45), color="#da77f2")
    _signal(ax, (7.7, 4.75), (4.3, 5.7), color="#E9B949")
    _signal(ax, (4.25, 5.7), (6.0, 5.7), color="#E9B949")

    _finish(
        fig,
        ax,
        out_path,
        "Manufacturing Plant — Industrial Process",
        "Raw material → welding cell → assembly → quality control → packaging  (automotive components)",
    )


def draw_pipeline_system(canonical: dict, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(25.6, 14.4))
    _layer_band(ax, 2.0, 8.0, 3.4, 2.4, "PIPELINE CONTROL CENTER", "#ff6b6b")
    _layer_band(ax, 5.0, 4.0, 9.6, 6.4, "PIPELINE (PUMP STATIONS • VALVE SITES • METERING)", "#2E9E6B")

    _proc_box(ax, 1.1, 8.8, 1.7, 0.9, "Control Center\nFirewall", "PIPE-CTR-FW-001", facecolor="#FDE8E8")
    _proc_box(ax, 3.0, 8.8, 1.6, 0.9, "Pipeline\nDispatcher", "PIPE-HUM-DSP-001", facecolor="#F0E6F7")
    _proc_box(ax, 2.0, 7.4, 1.9, 0.8, "SCADA Server", "PIPE-CTR-SCADA-001", facecolor="#FDE8E8")
    _proc_box(ax, 2.0, 6.3, 1.9, 0.8, "HMI Console", "PIPE-CTR-HMI-001", facecolor="#FDE8E8")
    _proc_box(ax, 2.0, 5.2, 1.9, 0.8, "Control Center Switch", "PIPE-CTR-SW-001", facecolor="#DCE9F7")

    # pipeline axis (horizontal)
    pipeline_y = 5.6
    ax.plot([4.1, 9.6], [pipeline_y, pipeline_y], color="#1F6FB2", linewidth=7, zorder=1, solid_capstyle="round")
    ax.text(9.75, pipeline_y, "flow →", fontsize=12, color="#1F6FB2", va="center", zorder=2)

    # stations
    _proc_box(ax, 4.9, 7.3, 1.8, 1.1, "Pump Station A", "PUMP-001 • VFD-001", facecolor="#D8EFDA")
    _proc_box(ax, 4.9, 5.9, 1.4, 0.8, "RTU A", "PIPE-RTU-001", facecolor="#DCE9F7")
    _proc_box(ax, 7.0, 7.3, 1.7, 1.0, "Block Valve Site", "VALVE-003", facecolor="#D8EFDA")
    _proc_box(ax, 7.0, 5.9, 1.4, 0.8, "RTU Valve", "PIPE-RTU-003", facecolor="#DCE9F7")
    _proc_box(ax, 9.0, 7.3, 1.8, 1.1, "Pump Station B", "PUMP-003 • VFD-002", facecolor="#D8EFDA")
    _proc_box(ax, 9.0, 5.9, 1.4, 0.8, "RTU B", "PIPE-RTU-002", facecolor="#DCE9F7")

    _proc_box(ax, 7.0, 2.4, 2.0, 1.15, "Custody Transfer\nMetering", "SENSOR-007 • SENSOR-008", facecolor="#D8EFDA")
    _proc_box(ax, 7.0, 1.3, 1.4, 0.8, "RTU Metering", "PIPE-RTU-004", facecolor="#DCE9F7")

    _sensor_marker(ax, 4.5, 4.6, "Pressure\nSENSOR-001")
    _sensor_marker(ax, 5.6, 4.6, "Flow\nSENSOR-002")
    _sensor_marker(ax, 6.8, 4.6, "Temp\nSENSOR-003")
    _sensor_marker(ax, 8.2, 4.6, "Pressure\nSENSOR-004")
    _sensor_marker(ax, 9.2, 4.6, "Flow\nSENSOR-005")
    _sensor_marker(ax, 7.0, 3.8, "Pressure\nSENSOR-006")

    # SCADA -> RTU comm links (DNP3)
    _signal(ax, (2.95, 7.4), (4.2, 7.4), color="#ff6b6b", style=(0, (5, 3)))
    _signal(ax, (2.95, 7.4), (6.3, 7.4), color="#ff6b6b", style=(0, (5, 3)))
    _signal(ax, (2.95, 7.4), (8.3, 7.4), color="#ff6b6b", style=(0, (5, 3)))
    _signal(ax, (2.95, 7.4), (6.3, 2.4), color="#ff6b6b", style=(0, (5, 3)))
    _signal(ax, (3.0, 8.35), (2.95, 7.8), color="#8E44AD")
    _signal(ax, (2.0, 8.35), (2.0, 7.8), color="#6B7280")
    _signal(ax, (4.9, 6.3), (4.9, 5.7), color="#4C78A8")
    _signal(ax, (7.0, 6.3), (7.0, 5.7), color="#4C78A8")
    _signal(ax, (9.0, 6.3), (9.0, 5.7), color="#4C78A8")
    _signal(ax, (7.0, 3.0), (7.0, 2.0), color="#4C78A8")

    _finish(
        fig,
        ax,
        out_path,
        "Oil & Gas Pipeline — Industrial Process",
        "Pump station A → block valve site → pump station B → custody metering  (SCADA over DNP3)",
    )


def draw_chemical_system(canonical: dict, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(25.6, 14.4))
    _layer_band(ax, 2.0, 8.0, 3.4, 2.4, "CONTROL ROOM (DCS)", "#845ef7")
    _layer_band(ax, 5.0, 4.0, 9.6, 6.4, "PROCESS UNITS (REACTOR • DISTILLATION • STORAGE)", "#2E9E6B")

    _proc_box(ax, 1.1, 8.8, 1.7, 0.9, "DCS Operator Station", "CHEM-DCS-OP-001", facecolor="#EFE7FB")
    _proc_box(ax, 3.0, 8.8, 1.5, 0.9, "Process\nOperator", "CHEM-HUM-OPR-001", facecolor="#F0E6F7")
    _proc_box(ax, 2.0, 7.3, 1.9, 0.8, "DCS Engineering St.", "CHEM-DCS-ENG-001", facecolor="#EFE7FB")
    _proc_box(ax, 2.0, 6.2, 1.9, 0.8, "DCS Switch", "CHEM-DCS-SW-001", facecolor="#DCE9F7")

    # process train
    _proc_box(ax, 5.2, 8.5, 1.5, 0.9, "FEEDSTOCK", "", facecolor="#BFE3C0", edgecolor="#2F7D32")
    _process_arrow(ax, (5.95, 8.05), (5.95, 7.4), color="#1F6FB2")
    _proc_box(ax, 5.2, 6.9, 1.7, 1.1, "Reactor", "TC-001 • PT-001 • CV-001", facecolor="#D8EFDA")
    _proc_box(ax, 7.4, 6.9, 1.5, 0.9, "DCS Controller\n(Reactor)", "CHEM-DCS-CTRL-001", facecolor="#DCE9F7")
    _process_arrow(ax, (6.0, 6.4), (6.0, 5.6), color="#1F6FB2")
    _proc_box(ax, 5.2, 5.1, 1.8, 1.1, "Distillation\nColumn", "TC-002 • PT-002 • CV-002", facecolor="#D8EFDA")
    _proc_box(ax, 7.4, 5.1, 1.7, 0.9, "DCS Controller\n(Distillation)", "CHEM-DCS-CTRL-002", facecolor="#DCE9F7")
    _process_arrow(ax, (6.05, 4.6), (6.05, 3.9), color="#1F6FB2")
    _proc_box(ax, 5.2, 3.4, 1.8, 1.1, "Product Storage\nTank Farm", "PUMP-001 • VALVE-001", facecolor="#D8EFDA")
    _proc_box(ax, 7.4, 3.4, 1.7, 0.9, "DCS Controller\n(Utilities)", "CHEM-DCS-CTRL-003", facecolor="#DCE9F7")
    _process_arrow(ax, (6.05, 2.9), (6.05, 2.2), color="#1F6FB2")
    _proc_box(ax, 5.2, 1.7, 1.8, 1.1, "Remote Tank Farm\n(rail loading)", "RTU-001 • PUMP-001", facecolor="#D8EFDA")

    # SIS (independent safety column, clearly separated from the DCS column)
    _proc_box(ax, 9.3, 3.4, 1.6, 1.0, "Safety PLC (SIS)", "CHEM-SIS-PLC-001", facecolor="#F5E1F7")
    _sensor_marker(ax, 9.3, 5.2, "ESD Switch\nSIS-ESD-001")
    _sensor_marker(ax, 9.3, 1.9, "ESD Relay\nSIS-RELAY-001")

    _signal(ax, (2.95, 6.2), (6.5, 6.9), color="#845ef7")
    _signal(ax, (2.95, 6.2), (6.5, 5.1), color="#845ef7")
    _signal(ax, (2.95, 6.2), (6.5, 3.4), color="#845ef7")
    _signal(ax, (2.95, 6.2), (6.5, 1.7), color="#845ef7")
    _signal(ax, (3.0, 8.35), (2.95, 7.7), color="#8E44AD")
    _signal(ax, (2.0, 8.35), (2.0, 7.7), color="#6B7280")
    _signal(ax, (8.15, 6.9), (9.25, 5.3), color="#da77f2")
    _signal(ax, (8.15, 5.1), (9.25, 4.35), color="#da77f2")
    _signal(ax, (9.3, 3.9), (9.3, 2.45), color="#da77f2")
    _signal(ax, (9.3, 4.5), (9.3, 5.3), color="#da77f2")
    _sensor_marker(ax, 3.9, 6.9, "TC / PT / LT")
    _sensor_marker(ax, 3.9, 5.1, "TC / PT / FT")

    _finish(
        fig,
        ax,
        out_path,
        "Chemical Processing Plant — Industrial Process",
        "Feedstock → reactor → distillation → storage → remote rail loading  (DCS with independent SIS)",
    )


DRAWERS = {
    "water_treatment_plant": draw_water_system,
    "electrical_substation": draw_substation_system,
    "manufacturing_plant": draw_manufacturing_system,
    "oil_&_gas_pipeline": draw_pipeline_system,
    "chemical_processing_plant": draw_chemical_system,
}


def main() -> None:
    folders = sorted(p for p in TOPOLOGIES.iterdir() if p.is_dir())
    for folder in folders:
        canonical = load_canonical(folder)
        topology_png = folder / f"{folder.name}.png"
        system_png = folder / f"{folder.name}_ics_system.png"
        print(f"Rendering {folder.name} ...")
        draw_network_topology(canonical, topology_png)
        drawer = DRAWERS.get(folder.name)
        if drawer is not None:
            drawer(canonical, system_png)
        else:
            print(f"  [WARN] no process-diagram drawer for {folder.name}")
        print(f"  {topology_png.relative_to(ROOT)}")
        print(f"  {system_png.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
