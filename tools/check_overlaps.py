"""
tools/check_overlaps.py - Deterministic layout QA for generated ICS diagrams.

Renders each process-diagram layout with matplotlib and measures, in display
pixels, the actual bounding boxes of every text and box patch, then reports
any text-text or text-box overlaps that exceed a tolerance.

Texts drawn by _proc_box inside their own box (title/sub) are expected to sit
inside it; the ownership map BOX_TEXT_OWNERSHIP (populated by the generator)
lets us skip those and flag only genuine collisions.

Run:  python tools/check_overlaps.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("gen", ROOT / "tools" / "generate_ics_diagrams.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

import matplotlib  # noqa: E402  (backend must be "Agg" before pyplot import)

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

TOPOLOGIES = ROOT / "ics_topologies"


def rects_overlap(a, b, tol=2.0):
    """Return overlap area in display px (0 if separated by >tol px)."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0 = max(ax0, bx0) + tol
    iy0 = max(ay0, by0) + tol
    ix1 = min(ax1, bx1) - tol
    iy1 = min(ay1, by1) - tol
    if ix1 > ix0 and iy1 > iy0:
        return (ix1 - ix0) * (iy1 - iy0)
    return 0.0


def check_network_diagram(folder: Path) -> int:
    """QA one ``<folder>.png`` network-topology diagram.

    The network diagram is drawn by ``draw_network_topology`` (which owns its
    own savefig/close), so we capture the figure by monkeypatching savefig,
    then measure text/text, text/box and box/box overlaps exactly like the
    process diagrams.  Node-name and node-id texts are drawn inside their own
    boxes, so every text in the axes is treated as owned by the box patch it
    sits on (matched by centre distance) — everything else is a genuine
    collision.
    """
    canonical = gen.load_canonical(folder)
    captured: dict = {}

    def fake_savefig(fig, path, **kwargs):
        captured["fig"] = fig
        captured["axes"] = fig.axes

    original_savefig = gen.plt.Figure.savefig
    gen.plt.Figure.savefig = fake_savefig  # type: ignore[method-assign]
    try:
        gen.draw_network_topology(canonical, Path("/tmp/unused.png"))
    finally:
        gen.plt.Figure.savefig = original_savefig  # type: ignore[method-assign]

    if "fig" not in captured:
        print(f"  [{folder.name}] WARN: network diagram did not render")
        return 0
    fig = captured["fig"]
    ax = captured["axes"][0]
    # The savefig interception captures the figure before its canvas is
    # finalised, so attach an Agg canvas explicitly for pixel-accurate
    # text/box measurement.
    if not isinstance(fig.canvas, matplotlib.backends.backend_agg.FigureCanvasAgg):
        fig.canvas = matplotlib.backends.backend_agg.FigureCanvasAgg(fig)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    texts: list[tuple[int, str, tuple[float, float, float, float]]] = []
    for t in ax.texts:
        bb = t.get_window_extent(renderer=renderer)
        texts.append((id(t), t.get_text()[:26].replace("\n", " "), (bb.x0, bb.y0, bb.x1, bb.y1)))
    boxes: list[tuple[int, tuple[float, float, float, float], tuple[float, float]]] = []
    for p in ax.patches:
        if isinstance(p, matplotlib.patches.FancyBboxPatch):
            bb = p.get_window_extent(renderer=renderer)
            boxes.append((id(p), (bb.x0, bb.y0, bb.x1, bb.y1), (bb.x0 + bb.width / 2, bb.y0 + bb.height / 2)))
    # Zone bands are plain Rectangles; every node box must sit fully inside
    # exactly one band, with a visible margin from every band edge.
    bands: list[tuple[int, tuple[float, float, float, float]]] = []
    for p in ax.patches:
        if isinstance(p, matplotlib.patches.Rectangle):
            bb = p.get_window_extent(renderer=renderer)
            bands.append((id(p), (bb.x0, bb.y0, bb.x1, bb.y1)))

    def text_in_box(text_bb: tuple[float, float, float, float], box_bb: tuple[float, float, float, float]) -> bool:
        """True when the text's centre lies inside the box."""
        tx0, ty0, tx1, ty1 = text_bb
        bx0, by0, bx1, by1 = box_bb
        cx, cy = (tx0 + tx1) / 2.0, (ty0 + ty1) / 2.0
        return bx0 <= cx <= bx1 and by0 <= cy <= by1

    issues = 0
    # text vs text (node labels must never collide with each other)
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            area = rects_overlap(texts[i][2], texts[j][2])
            if area > 300:
                issues += 1
                print(f"  [{folder.name}] NET TEXT-TEXT '{texts[i][1]}' <-> '{texts[j][1]}'  overlap_px={area:.0f}")
    # text vs box (a text may only overlap a box that contains its centre, i.e.
    # the label drawn inside its own node box)
    for t_id, t_name, t_bb in texts:
        for b_id, b_bb, b_centre in boxes:
            area = rects_overlap(t_bb, b_bb)
            if area <= 1400:
                continue
            if text_in_box(t_bb, b_bb):
                continue  # label drawn inside its own node box
            issues += 1
            print(f"  [{folder.name}] NET TEXT-BOX '{t_name}'  overlap_px={area:.0f}")
    # box vs box (never in a clean layout)
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            area = rects_overlap(boxes[i][1], boxes[j][1])
            if area > 400:
                issues += 1
                print(f"  [{folder.name}] NET BOX-BOX (box#{i} <-> box#{j})  overlap_px={area:.0f}")

    # --- Hard invariant: every node box fully inside its zone band. ---
    # Convert window (pixel) extents to data coordinates so the margin
    # thresholds are dpi-independent.  The generator guarantees a node-edge
    # to band-edge margin of NET_BAND_PAD + NET_ROW_STEP/2 - NET_NODE_H/2
    # (~0.7 data units) vertically and >= 1.8 horizontally; anything below
    # 0.4 means a node straddles or touches a separator line.
    inv = ax.transData.inverted()

    def to_data(rect: tuple[float, float, float, float]):
        (x0, y0), (x1, y1) = inv.transform([(rect[0], rect[1]), (rect[2], rect[3])])
        return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

    band_data = [to_data(bb) for _, bb in bands]
    min_margin = 0.4
    if band_data:
        for b_id, b_bb, _b_centre in boxes:
            n = to_data(b_bb)
            ncx, ncy = (n[0] + n[2]) / 2.0, (n[1] + n[3]) / 2.0
            members = [b for b in band_data if b[0] <= ncx <= b[2] and b[1] <= ncy <= b[3]]
            if len(members) == 0:
                issues += 1
                print(f"  [{folder.name}] NET CONTAINMENT: node outside all zone bands")
            elif len(members) > 1:
                issues += 1
                print(f"  [{folder.name}] NET CONTAINMENT: node inside {len(members)} zone bands")
            else:
                bx0, by0, bx1, by1 = members[0]
                m = min(n[0] - bx0, bx1 - n[2], n[1] - by0, by1 - n[3])
                if m < min_margin:
                    issues += 1
                    print(f"  [{folder.name}] NET CONTAINMENT: node {m:.2f} units from band edge (min {min_margin})")
        # bands themselves must never overlap each other
        for i in range(len(band_data)):
            for j in range(i + 1, len(band_data)):
                a, b = band_data[i], band_data[j]
                if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                    issues += 1
                    print(f"  [{folder.name}] NET CONTAINMENT: zone bands overlap each other")

    print(f"{folder.name}.png: {len(texts)} texts, {len(boxes)} boxes, {len(bands)} bands, {issues} issues")
    plt.close(fig)
    return issues


def main() -> int:
    total_issues = 0
    for folder in sorted(TOPOLOGIES.iterdir()):
        if not folder.is_dir():
            continue
        canonical = gen.load_canonical(folder)
        if folder.name in gen.DRAWERS:
            drawer = gen.DRAWERS[folder.name]
            # id() values are only stable within one render; drop any mappings
            # left behind by the previous folder's figures.
            gen.BOX_TEXT_OWNERSHIP.clear()

            captured: dict = {}

            def fake_finish(fig, ax, path, title, subtitle):
                captured["fig"] = fig
                captured["ax"] = ax

            original_finish = gen._finish
            gen._finish = fake_finish
            try:
                drawer(canonical, Path("/tmp/unused.png"))
            finally:
                gen._finish = original_finish

            fig, ax = captured["fig"], captured["ax"]
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()

            texts: list[tuple[int, str, tuple[float, float, float, float]]] = []
            for t in ax.texts:
                bb = t.get_window_extent(renderer=renderer)
                texts.append((id(t), t.get_text()[:26].replace("\n", " "), (bb.x0, bb.y0, bb.x1, bb.y1)))
            boxes: list[tuple[int, tuple[float, float, float, float]]] = []
            for p in ax.patches:
                if isinstance(p, matplotlib.patches.FancyBboxPatch):
                    bb = p.get_window_extent(renderer=renderer)
                    boxes.append((id(p), (bb.x0, bb.y0, bb.x1, bb.y1)))

            issues = 0
            # text vs text
            for i in range(len(texts)):
                for j in range(i + 1, len(texts)):
                    area = rects_overlap(texts[i][2], texts[j][2])
                    if area > 500:
                        issues += 1
                        print(f"  [{folder.name}] TEXT-TEXT '{texts[i][1]}' <-> '{texts[j][1]}'  overlap_px={area:.0f}")
            # text vs box (skip owned title/sub texts)
            for t_id, t_name, t_bb in texts:
                for b_id, b_bb in boxes:
                    if t_id in gen.BOX_TEXT_OWNERSHIP.get(b_id, set()):
                        continue  # intended: this text lives inside its own box
                    area = rects_overlap(t_bb, b_bb)
                    if area > 1400:
                        issues += 1
                        print(f"  [{folder.name}] TEXT-BOX '{t_name}'  overlap_px={area:.0f}")
            # box vs box (must never happen in a clean layout)
            for i in range(len(boxes)):
                for j in range(i + 1, len(boxes)):
                    area = rects_overlap(boxes[i][1], boxes[j][1])
                    if area > 400:
                        issues += 1
                        print(f"  [{folder.name}] BOX-BOX (box#{i} <-> box#{j})  overlap_px={area:.0f}")

            total_issues += issues
            print(f"{folder.name}: {len(texts)} texts, {len(boxes)} boxes, {issues} issues")
            plt.close(fig)

        # Network-topology diagram QA for every folder (the process drawers
        # above do not cover it).
        total_issues += check_network_diagram(folder)

    print(f"\nTOTAL ISSUES: {total_issues}")
    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
