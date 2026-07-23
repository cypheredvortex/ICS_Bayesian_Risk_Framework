"""
attack_paths.py

Identify high-risk propagation paths from compromised evidence nodes to
critical assets, using edge weights as propagation strength.
"""

from collections import deque
from typing import Any

_MIN_PATH_QUALITY = 0.05


def compute_attack_paths(
    relationships: list,
    edge_weights: dict[tuple[str, str], float],
    evidence_used: dict[str, int],
    risk_scores: list[dict[str, Any]],
    assets: dict,
    max_paths: int | None = None,
    max_depth: int = 12,
) -> list[dict[str, Any]]:
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

    consequence_targets = {
        node_id
        for node_id, attrs in assets.items()
        if float(attrs.get("consequence_severity", 0) or 0) > 0
    }
    target_set = (consequence_targets & set(risk_by_asset)) or set(risk_by_asset)

    ranked: list[dict[str, Any]] = []
    seen_signatures: set[tuple[str, ...]] = set()

    for source in sources:
        queue: deque[tuple[str, list[str], list[dict[str, Any]], float, int]] = deque()
        queue.append((source, [source], [], 1.0, 0))

        while queue:
            node, path, edges, weight_product, hops = queue.popleft()
            if len(path) > max_depth:
                continue

            if node in target_set and len(path) > 1:
                signature = tuple(path)
                if signature not in seen_signatures:
                    seen_signatures.add(signature)
                    propagation_quality = weight_product ** (1.0 / hops) if hops else 1.0
                    ranked.append(
                        {
                            "path": path,
                            "edges": edges,
                            "score": round(propagation_quality * risk_by_asset.get(node, 0.0), 6),
                            "propagation_score": round(propagation_quality, 6),
                            "target": node,
                            "target_risk": round(risk_by_asset.get(node, 0.0), 6),
                            "source": source,
                            "hops": hops,
                        }
                    )

            for neighbor, weight, rel_type in adjacency.get(node, []):
                if neighbor in path:
                    continue
                next_weight_product = weight_product * weight
                next_hops = hops + 1
                next_quality = next_weight_product ** (1.0 / next_hops)
                if next_quality < _MIN_PATH_QUALITY:
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
                        next_weight_product,
                        next_hops,
                    )
                )

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked if max_paths is None else ranked[:max_paths]


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
