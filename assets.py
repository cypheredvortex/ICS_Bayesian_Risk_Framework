"""
assets.py  (PHASE 1)

This is the only plant-specific handoff point in the pipeline. It doesn't
hold data itself anymore -- it loads and validates topology from a JSON
file, so swapping plants means swapping a JSON file, not editing code.

Expected JSON shape:
{
  "assets": {node_id: {kind, ...attrs}},
  "relationships": [[source, target, rel_type, firewalled], ...]
}
"""

import json
from pathlib import Path

from config import W0

VALID_KINDS = {"device", "human", "physical"}
VALID_REL_TYPES = set(W0.keys())

REQUIRED_DEVICE_KEYS = {"cvss_type", "exposed", "patched"}
REQUIRED_HUMAN_KEYS = {"role", "awareness", "privilege"}
REQUIRED_PHYSICAL_KEYS: set = set()  # p_base_override is optional, defaults to 0.0


def load_topology(path: str | Path | dict) -> tuple[dict, list]:
    """
    Load and validate assets + relationships from either a JSON file path or
    an in-memory topology dictionary.

    Returns (assets, relationships) in the same shape phase2-5 expect.
    Raises ValueError with a specific message on malformed input, rather
    than failing silently deep in Phase 3.
    """
    if isinstance(path, dict):
        raw = path
        source_label = "inline topology"
    else:
        path = Path(path)
        with open(path) as f:
            raw = json.load(f)
        source_label = str(path)

    if "assets" not in raw or "relationships" not in raw:
        raise ValueError(f"{source_label}: JSON must contain 'assets' and 'relationships' keys")

    assets = raw["assets"]
    relationships = [tuple(r) for r in raw["relationships"]]

    _validate_assets(assets)
    _validate_relationships(relationships, assets)

    return assets, relationships


def _validate_assets(assets: dict) -> None:
    for node_id, attrs in assets.items():
        kind = attrs.get("kind")
        if kind not in VALID_KINDS:
            raise ValueError(
                f"Asset '{node_id}': kind must be one of {VALID_KINDS}, got {kind!r}"
            )

        required = {
            "device": REQUIRED_DEVICE_KEYS,
            "human": REQUIRED_HUMAN_KEYS,
            "physical": REQUIRED_PHYSICAL_KEYS,
        }[kind]
        missing = required - attrs.keys()
        if missing:
            raise ValueError(f"Asset '{node_id}': missing required keys {missing}")


def _validate_relationships(relationships: list, assets: dict) -> None:
    for s, t, rel_type, firewalled in relationships:
        if s not in assets or t not in assets:
            raise ValueError(f"Relationship ({s} -> {t}): references unknown asset")
        if rel_type not in VALID_REL_TYPES:
            raise ValueError(
                f"Relationship ({s} -> {t}): rel_type '{rel_type}' not in {VALID_REL_TYPES}"
            )
        if not isinstance(firewalled, bool):
            raise ValueError(f"Relationship ({s} -> {t}): firewalled must be true/false")


if __name__ == "__main__":
    assets, relationships = load_topology("data/swat_example.json")
    print(f"Loaded {len(assets)} assets, {len(relationships)} relationships")
    for nid, attrs in assets.items():
        print(f"  {nid}: {attrs}")
