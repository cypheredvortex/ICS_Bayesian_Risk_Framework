"""
attack_paths.py — Attack path analysis following the Bayesian DAG.

Methodology
-----------
An "attack path" in this framework is a directed path through the
Bayesian network from an evidence-compromised entry node (or a natural
entry point with high base probability) to a high-consequence target.

CRITICAL DESIGN DECISION:  We follow the DAG direction.
--------------------------------------------------------
The previous implementation treated relationships as undirected edges,
which is incorrect for a causal Bayesian network.  Compromise flows
from parent to child (cause → effect).  Reversing the direction would
imply that compromising a PLC causes the HMI to be compromised, which
violates the causal semantics encoded in the CPTs.

Scoring
-------
Each path is scored using the Bayesian posterior probabilities of the
nodes along it, not a heuristic geometric mean of edge weights:

    path_score =  min( P(nodeᵢ=1 | evidence) )  ×  target_risk_index

The minimum posterior along the path represents the "weakest link" —
if any node is unlikely to be compromised, the whole path is unlikely
to be viable.  Multiplying by the target risk index prioritises paths
that lead to high-value assets.

This is more defensible than geometric-mean edge weights because it
uses the actual inferred probabilities from the Bayesian network rather
than raw propagation weights.

Alternative interpretation (documented for users):
If you prefer a product-of-probabilities model (cumulative probability
that every node on the path is compromised), set the environment
variable ATTACK_PATH_SCORING=product.  The default is "min" (weakest
link).

References
----------
• Pearl, J. (1988). Probabilistic Reasoning in Intelligent Systems.
• Poolsapassit, N. & Ray, I. (2019). "Investigating the use of Bayesian
  networks for security risk assessment."  Journal of Information
  Security and Applications.
"""

import os
from collections import deque
from typing import Any

_MIN_PATH_QUALITY = 0.05
_MAX_DEPTH_DEFAULT = 12


def _unpack_relationship(relationship) -> tuple[str, str, str, bool, dict]:
    """Unpack a relationship tuple or dict into canonical components."""
    if isinstance(relationship, dict):
        source = str(relationship.get("source", ""))
        target = str(relationship.get("target", ""))
        rel_type = str(relationship.get("type", "connects-to"))
        firewalled = bool(relationship.get("firewalled", False))
        metadata = relationship.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        return source, target, rel_type, firewalled, metadata

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


def compute_attack_paths(
    relationships: list,
    edge_weights: dict[tuple[str, str], float],
    evidence_used: dict[str, int],
    risk_scores: list[dict[str, Any]],
    assets: dict,
    posteriors: dict[str, float] | None = None,
    max_paths: int | None = None,
    max_depth: int = _MAX_DEPTH_DEFAULT,
) -> list[dict[str, Any]]:
    """Compute directed attack paths through the Bayesian DAG.

    Args:
        relationships: Normalised relationship tuples or dicts.
        edge_weights: Propagation weights per (source, target).
        evidence_used: Evidence map {node_id: 0|1}.
        risk_scores: Risk register rows (for target risk lookup).
        assets: Asset attribute dict.
        posteriors: Posterior probabilities from Bayesian inference.
        max_paths: Maximum number of paths to return (None = all).
        max_depth: Maximum path length (hops).

    Returns:
        List of path dicts, sorted by score descending.
    """
    # Build directed adjacency (parent → child)
    adjacency: dict[str, list[tuple[str, float, str]]] = {}
    for rel in relationships:
        source, target, rel_type, _firewalled, _meta = _unpack_relationship(rel)
        if not source or not target:
            continue
        weight = edge_weights.get((source, target), 0.0)
        adjacency.setdefault(source, []).append((target, weight, rel_type))

    # Entry points: evidence-marked-as-compromised, or high-base-prob roots
    sources = [node for node, state in evidence_used.items() if state == 1]
    if not sources:
        # Fallback: use nodes with no incoming edges (DAG roots) as likely
        # entry points — these are typically the internet-facing or human
        # assets that an adversary would reach first.
        all_targets = set()
        for rel in relationships:
            src, tgt, *_ = _unpack_relationship(rel)
            if tgt:
                all_targets.add(tgt)
        sources = [node for node in adjacency if node not in all_targets]
    if not sources:
        return []

    # Risk lookup
    risk_by_asset = {
        str(row.get("asset")): float(row.get("risk", row.get("risk_index", 0.0)))
        for row in risk_scores
    }

    # Target set: assets with non-zero consequence severity
    consequence_targets = {
        node_id
        for node_id, attrs in assets.items()
        if float(attrs.get("consequence_severity", 0) or 0) > 0
    }
    target_set = (consequence_targets & set(risk_by_asset)) or set(risk_by_asset)

    scoring_mode = os.getenv("ATTACK_PATH_SCORING", "min").lower()

    ranked: list[dict[str, Any]] = []
    seen_signatures: set[tuple[str, ...]] = set()

    for source in sources:
        queue: deque[tuple[str, list[str], list[dict[str, Any]], int]] = deque()
        queue.append((source, [source], [], 0))

        while queue:
            node, path, edges, hops = queue.popleft()
            if len(path) > max_depth:
                continue

            if node in target_set and len(path) > 1:
                signature = tuple(path)
                if signature in seen_signatures:
                    continue
                seen_signatures.add(signature)

                # Compute path score from posteriors (if available) or edge weights
                if posteriors:
                    path_probs = [posteriors.get(n, 0.0) for n in path]
                    if scoring_mode == "product":
                        path_prob = 1.0
                        for pp in path_probs:
                            path_prob *= pp
                    else:  # default "min" (weakest link)
                        path_prob = min(path_probs) if path_probs else 0.0
                else:
                    # Fallback to edge-weight geometric mean when posteriors
                    # are not supplied (backward compatibility)
                    weights = [edge_weights.get((path[i], path[i+1]), 0.0)
                               for i in range(len(path)-1)]
                    path_prob = (_geometric_mean(weights) if weights else 0.0)

                target_risk = risk_by_asset.get(node, 0.0)
                score = path_prob * target_risk

                ranked.append({
                    "path": path,
                    "edges": edges,
                    "score": round(score, 6),
                    "path_probability": round(path_prob, 6),
                    "target": node,
                    "target_risk": round(target_risk, 6),
                    "source": source,
                    "hops": hops,
                })

            for neighbor, weight, rel_type in adjacency.get(node, []):
                if neighbor in path:
                    continue  # No cycles — DAG guarantee
                next_hops = hops + 1
                # Pruning: if the edge weight itself is tiny, skip.
                if weight < _MIN_PATH_QUALITY:
                    continue
                queue.append((
                    neighbor,
                    path + [neighbor],
                    edges + [{
                        "source": node,
                        "target": neighbor,
                        "weight": round(weight, 6),
                        "rel_type": rel_type,
                    }],
                    next_hops,
                ))

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked if max_paths is None else ranked[:max_paths]


def _geometric_mean(values: list[float]) -> float:
    """Geometric mean of a list of positive numbers."""
    if not values:
        return 0.0
    product = 1.0
    for v in values:
        product *= max(v, 1e-12)
    return product ** (1.0 / len(values))