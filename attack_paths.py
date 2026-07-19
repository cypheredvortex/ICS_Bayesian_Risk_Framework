"""
attack_paths.py

Identify high-risk propagation paths from compromised evidence nodes to
critical assets, using edge weights as propagation strength.
"""

from collections import deque
from typing import Any


def compute_attack_paths(
    relationships: list,
    edge_weights: dict[tuple[str, str], float],
    evidence_used: dict[str, int],
    risk_scores: list[dict[str, Any]],
    assets: dict,
    max_paths: int = 5,
    max_depth: int = 12,
) -> list[dict[str, Any]]:
    """
    Return ranked attack paths from compromised evidence sources toward
    high-risk assets.

    Each path:
      {
        "path": [node_ids...],
        "edges": [{"source", "target", "weight", "rel_type"}...],
        "score": float,
        "target": str,
        "target_risk": float,
      }
    """
    adjacency: dict[str, list[tuple[str, float, str]]] = {}
    destinations: set[str] = set()
    for rel in relationships:
        source, target, rel_type, _firewalled, _meta = _unpack_relationship(rel)
        weight = edge_weights.get((source, target), 0.0)
        adjacency.setdefault(source, []).append((target, weight, rel_type))
        destinations.add(target)

    sources = [node for node, state in evidence_used.items() if state == 1]
    if not sources:
        sources = [node for node in adjacency if node not in destinations]
    if not sources:
        return []

    risk_by_asset = {
        str(row.get("asset")): float(row.get("risk", 0.0))
        for row in risk_scores
    }
    targets = sorted(
        risk_by_asset.keys(),
        key=lambda asset_id: risk_by_asset.get(asset_id, 0.0),
        reverse=True,
    )[: max(3, min(8, len(risk_by_asset)))]
    target_set = set(targets)

    ranked: list[dict[str, Any]] = []
    seen_signatures: set[tuple[str, ...]] = set()

    for source in sources:
        queue: deque[tuple[str, list[str], list[dict[str, Any]], float]] = deque()
        queue.append((source, [source], [], 1.0))

        while queue:
            node, path, edges, reachability = queue.popleft()
            if len(path) > max_depth:
                continue

            if node in target_set and len(path) > 1:
                signature = tuple(path)
                if signature not in seen_signatures:
                    seen_signatures.add(signature)
                    ranked.append(
                        {
                            "path": path,
                            "edges": edges,
                            "score": round(reachability * risk_by_asset.get(node, 0.0), 6),
                            "propagation_score": round(reachability, 6),
                            "target": node,
                            "target_risk": round(risk_by_asset.get(node, 0.0), 6),
                            "source": source,
                        }
                    )

            for neighbor, weight, rel_type in adjacency.get(node, []):
                if neighbor in path:
                    continue
                next_reachability = reachability * weight
                if next_reachability < 0.01:
                    continue
                queue.append(
                    (
                        neighbor,
                        path + [neighbor],
                        edges + [
                            {
                                "source": node,
                                "target": neighbor,
                                "weight": round(weight, 6),
                                "rel_type": rel_type,
                            }
                        ],
                        next_reachability,
                    )
                )

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:max_paths]


def _unpack_relationship(relationship) -> tuple[str, str, str, bool, dict]:
    if len(relationship) < 4:
        raise ValueError("Each relationship must contain at least 4 fields.")
    source, target, rel_type, firewalled = relationship[:4]
    metadata = relationship[4] if len(relationship) > 4 else {}
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise ValueError(
            f"Relationship ({source} -> {target}): optional metadata must be a dict."
        )
    return source, target, rel_type, bool(firewalled), metadata
