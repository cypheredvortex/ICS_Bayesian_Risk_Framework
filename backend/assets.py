"""
assets.py - Public wrapper for normalized ICS topology ingestion.

This module preserves the old backend.assets public API while delegating to
backend.importers for format-agnostic normalization and topology extraction.
"""

from pathlib import Path

from backend.importers import load_topology as _load_topology, load_topology_from_bytes as _load_topology_from_bytes


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------

def load_topology(path: str | Path | dict) -> tuple[dict, list]:
    normalized = _load_topology(path)
    return normalized["assets"], normalized["relationships"]


def load_topology_from_bytes(content: bytes, filename: str) -> tuple[dict, list]:
    normalized = _load_topology_from_bytes(content, filename)
    return normalized["assets"], normalized["relationships"]
