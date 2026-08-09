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

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

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


def main() -> None:
    total_issues = 0
    for folder in sorted(TOPOLOGIES.iterdir()):
        if not folder.is_dir() or folder.name not in gen.DRAWERS:
            continue
        canonical = gen.load_canonical(folder)
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

    print(f"\nTOTAL ISSUES: {total_issues}")
    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
