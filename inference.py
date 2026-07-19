"""
inference.py  (PHASE 4)

Fully Parameterized BN -> Posterior Probabilities.
Generic BN math -- no custom formula, just pgmpy's exact inference.
"""

from pgmpy.inference import VariableElimination


class EvidenceError(ValueError):
    """Raised when evidence references invalid or unknown nodes."""


def _sanitize_evidence(model, evidence: dict) -> dict:
    """
    Validate and normalize evidence.

    Empty evidence is allowed and yields prior marginals for all nodes.
    Unknown nodes raise EvidenceError instead of silently substituting values.
    """
    if not evidence:
        return {}

    node_ids = set(model.nodes())
    valid_evidence: dict[str, int] = {}
    invalid_nodes: list[str] = []

    for node_id, value in evidence.items():
        if node_id not in node_ids:
            invalid_nodes.append(node_id)
            continue
        if int(value) not in (0, 1):
            raise EvidenceError(
                f"Evidence for node '{node_id}' must be 0 or 1, got {value!r}."
            )
        valid_evidence[node_id] = int(value)

    if invalid_nodes:
        raise EvidenceError(
            f"Unknown evidence nodes not present in the topology: {invalid_nodes}. "
            f"Valid nodes: {sorted(node_ids)}"
        )

    return valid_evidence


def compute_posteriors(model, evidence: dict) -> dict:
    """
    evidence: {node_id: 0 or 1}, e.g. {"local_hmi": 1}
    returns: {node_id: P(node=1 | evidence)} for every node NOT in evidence.
    """
    posteriors, _ = compute_posteriors_with_evidence(model, evidence)
    return posteriors


def compute_posteriors_with_evidence(model, evidence: dict) -> tuple[dict, dict]:
    """Same as compute_posteriors, but also returns the sanitized evidence used."""
    infer = VariableElimination(model)
    posteriors: dict[str, float] = {}
    sanitized = _sanitize_evidence(model, evidence)

    for node_id in model.nodes():
        if node_id in sanitized:
            continue
        result = infer.query(variables=[node_id], evidence=sanitized, show_progress=False)
        posteriors[node_id] = float(result.get_value(**{node_id: 1}))

    return posteriors, sanitized


if __name__ == "__main__":
    from assets import load_topology
    from graph_builder import build_graph_skeleton
    from probability import compute_base_probs
    from cpt_generator import parameterize

    assets, relationships = load_topology("data/swat_example.json")
    model, edge_weights = build_graph_skeleton(relationships, node_ids=assets.keys())
    base_probs = compute_base_probs(assets)
    model = parameterize(model, edge_weights, base_probs)

    evidence = {"local_hmi": 1}
    posteriors = compute_posteriors(model, evidence)

    print(f"Posteriors given evidence {evidence}:")
    for nid, p in posteriors.items():
        print(f"  P({nid}=1 | evidence) = {p:.3f}")
