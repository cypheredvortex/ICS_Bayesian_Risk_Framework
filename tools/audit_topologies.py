"""
tools/audit_topologies.py - Audit every topology file in ics_topologies/
through the REAL application pipeline (import -> normalize -> validate ->
Bayesian network -> inference -> risk) and verify cross-format consistency
(identical asset ids and relationship edges vs the canonical JSON).

Run:  python tools/audit_topologies.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.assets import load_topology  # noqa: E402
from backend.cli import run as run_framework  # noqa: E402

TOPOLOGIES = ROOT / "ics_topologies"
MAIN_FORMATS = {".json", ".yaml", ".yml", ".csv", ".xlsx", ".graphml", ".xml", ".aml", ".vdx", ".vsdx"}
# Split inventory files are *supporting artifacts*: they document the asset
# register, connection matrix, zones and protocols separately.  They are not
# standalone topology files (an assets-only list has no relationships and is
# intentionally rejected by the framework, like a partial spreadsheet export).
SUPPORTING_SUFFIXES = ("_assets.csv", "_connections.csv", "_zones.csv", "_protocols.csv")


def canonical_signature(canonical: dict) -> tuple[set[str], set[tuple[str, str]], dict[str, str], dict[tuple[str, str], str]]:
    """Reference signature: asset ids, edge pairs, per-asset kind, per-edge type.

    Kind and relationship type are the semantic attributes every supported
    format is required to round-trip (zones/vendor/model are display metadata
    carried by the data formats but not by the compact Visio marker format).
    """
    asset_ids = {asset["id"] for asset in canonical["assets"]}
    edges = {(conn["source"], conn["target"]) for conn in canonical["connections"]}
    kinds = {asset["id"]: asset.get("kind", "device") for asset in canonical["assets"]}
    edge_types = {(conn["source"], conn["target"]): conn.get("type", "connects-to") for conn in canonical["connections"]}
    return asset_ids, edges, kinds, edge_types


def audit_file(path: Path, folder: str) -> dict:
    """Run import + full pipeline for a single file."""
    entry = {"file": path.name, "folder": folder, "import": "FAIL", "pipeline": "N/A",
             "assets": 0, "relationships": 0, "error": "", "warnings": []}
    try:
        assets, relationships, warnings = load_topology(path)
    except Exception as exc:
        entry["error"] = f"{type(exc).__name__}: {exc}"
        entry["import"] = "FAIL"
        return entry
    entry["import"] = "PASS"
    entry["assets"] = len(assets)
    entry["relationships"] = len(relationships)
    entry["warnings"] = warnings
    entry["asset_ids"] = set(assets.keys())
    entry["edges"] = {(rel[0], rel[1]) for rel in relationships}
    entry["kinds"] = {aid: attrs.get("kind", "device") for aid, attrs in assets.items()}
    entry["edge_types"] = {(rel[0], rel[1]): rel[2] for rel in relationships}
    try:
        result = run_framework(path, evidence={}, write_outputs=False, persist=False)
        entry["pipeline"] = "PASS"
        entry["risk_assets"] = len(result["risk_scores"])
        entry["posteriors"] = len(result["posteriors"])
    except Exception as exc:
        entry["pipeline"] = "FAIL"
        entry["pipeline_error"] = f"{type(exc).__name__}: {exc}"
    return entry


def main() -> None:
    folders = sorted(p for p in TOPOLOGIES.iterdir() if p.is_dir())
    results: list[dict] = []
    consistency: list[str] = []

    for folder in folders:
        canonical_path = folder / f"{folder.name}.json"
        with canonical_path.open("r", encoding="utf-8") as handle:
            import json

            canonical = json.load(handle)
        ref_assets, ref_edges, ref_kinds, ref_edge_types = canonical_signature(canonical)

        for path in sorted(folder.iterdir()):
            suffix = path.suffix.lower()
            if suffix not in MAIN_FORMATS or path.name.endswith(SUPPORTING_SUFFIXES):
                continue
            entry = audit_file(path, folder.name)
            results.append(entry)
            if entry["import"] == "PASS":
                missing_assets = ref_assets - entry["asset_ids"]
                extra_assets = entry["asset_ids"] - ref_assets
                missing_edges = ref_edges - entry["edges"]
                extra_edges = entry["edges"] - ref_edges
                kind_diffs = {
                    aid for aid in entry["asset_ids"] & ref_assets
                    if entry["kinds"].get(aid) != ref_kinds.get(aid)
                }
                type_diffs = {
                    edge for edge in entry["edges"] & ref_edges
                    if entry["edge_types"].get(edge) != ref_edge_types.get(edge)
                }
                if missing_assets or extra_assets or missing_edges or extra_edges or kind_diffs or type_diffs:
                    entry["consistency"] = "MISMATCH"
                    entry["missing_assets"] = sorted(missing_assets)
                    entry["extra_assets"] = sorted(extra_assets)
                    entry["missing_edges"] = sorted(missing_edges)
                    entry["extra_edges"] = sorted(extra_edges)
                    entry["kind_diffs"] = sorted(kind_diffs)
                    entry["type_diffs"] = sorted(type_diffs)
                    consistency.append(
                        f"{folder.name}/{path.name}: assets +{len(extra_assets)}/-{len(missing_assets)} "
                        f"edges +{len(extra_edges)}/-{len(missing_edges)} "
                        f"kinds {len(kind_diffs)} type-diffs {len(type_diffs)}"
                    )
                else:
                    entry["consistency"] = "MATCH"

    print(f"{'FOLDER':<28}{'FILE':<42}{'IMP':<5}{'PIPE':<5}{'A':<4}{'R':<4}{'CONS':<8} NOTES")
    print("-" * 140)
    for r in results:
        notes = r.get("error") or r.get("pipeline_error", "")
        notes = notes or ("; ".join(r["warnings"][:1]) if r.get("warnings") else "")
        print(f"{r['folder']:<28}{r['file']:<42}{r['import']:<5}{r['pipeline']:<5}"
              f"{r['assets']:<4}{r['relationships']:<4}{r.get('consistency', 'n/a'):<8} {notes[:60]}")

    print()
    passed_import = [r for r in results if r["import"] == "PASS"]
    passed_pipe = [r for r in results if r["pipeline"] == "PASS"]
    mismatches = [r for r in results if r.get("consistency") == "MISMATCH"]
    print(f"MAIN FORMAT FILES TESTED: {len(results)}")
    print(f"IMPORT PASS: {len(passed_import)}   IMPORT FAIL: {len(results) - len(passed_import)}")
    print(f"PIPELINE PASS: {len(passed_pipe)}   PIPELINE FAIL/N/A: {len(results) - len(passed_pipe)}")
    print(f"CROSS-FORMAT CONSISTENCY: {len(results) - len(mismatches)} MATCH, {len(mismatches)} MISMATCH")
    if consistency:
        print("MISMATCHES:")
        for line in consistency:
            print(f"  {line}")


if __name__ == "__main__":
    main()
