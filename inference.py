"""
inference.py  (PHASE 4)

Fully Parameterized BN -> Posterior Probabilities.
Generic BN math -- no custom formula, just pgmpy's exact inference.
"""

import warnings

from pgmpy.inference import VariableElimination


def _sanitize_evidence(model, evidence: dict) -> dict:
    """Filter out evidence nodes that are not in the model and use a fallback if needed."""
    if not evidence:
        default_node = next(iter(model.nodes()), None)
        if default_node is None:
            return {}
        return {default_node: 1}

    valid_evidence = {}
    invalid_nodes = []
    node_ids = set(model.nodes())

    for node_id, value in evidence.items():
        if node_id in node_ids:
            valid_evidence[node_id] = int(value)
        else:
            invalid_nodes.append(node_id)

    if not valid_evidence:
        default_node = next(iter(model.nodes()), None)
        if default_node is None:
            return {}
        warnings.warn(
            f"None of the provided evidence nodes {list(evidence.keys())} exist in the model. "
            f"Using {default_node}=1 as a fallback."
        )
        return {default_node: 1}

    if invalid_nodes:
        warnings.warn(f"Ignoring unknown evidence nodes for inference: {invalid_nodes}")

    return valid_evidence


def compute_posteriors(model, evidence: dict) -> dict:
    """
    evidence: {node_id: 0 or 1}, e.g. {"corp_net": 1}
    returns: {node_id: P(node=1 | evidence)} for every node NOT in evidence.
    Also returns the sanitized evidence actually used, via
    compute_posteriors_with_evidence, for callers that need to report it.
    """
    posteriors, _ = compute_posteriors_with_evidence(model, evidence)
    return posteriors


def compute_posteriors_with_evidence(model, evidence: dict) -> tuple[dict, dict]:
    """Same as compute_posteriors, but also returns the sanitized evidence used."""
    infer = VariableElimination(model)
    posteriors = {}
    sanitized = _sanitize_evidence(model, evidence)

    for node_id in model.nodes():
        if node_id in sanitized:
            continue
        result = infer.query(variables=[node_id], evidence=sanitized, show_progress=False)
        posteriors[node_id] = result.get_value(**{node_id: 1})

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

    evidence = {"corp_net": 1}
    posteriors = compute_posteriors(model, evidence)

    print(f"Posteriors given evidence {evidence}:")
    for nid, p in posteriors.items():
        print(f"  P({nid}=1 | evidence) = {p:.3f}")