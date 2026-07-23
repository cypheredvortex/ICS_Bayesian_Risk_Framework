"""
inference.py - Fully Parameterized BN to Posterior Probabilities.
"""

from pgmpy.inference import VariableElimination


class EvidenceError(ValueError):
    """Raised when evidence references invalid or unknown nodes."""


def _sanitize_evidence(model, evidence: dict) -> dict:
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
    posteriors, _ = compute_posteriors_with_evidence(model, evidence)
    return posteriors


def compute_posteriors_with_evidence(model, evidence: dict) -> tuple[dict, dict]:
    infer = VariableElimination(model)
    posteriors: dict[str, float] = {}
    sanitized = _sanitize_evidence(model, evidence)

    for node_id in model.nodes():
        if node_id in sanitized:
            continue
        result = infer.query(variables=[node_id], evidence=sanitized, show_progress=False)
        posteriors[node_id] = float(result.get_value(**{node_id: 1}))

    return posteriors, sanitized
