"""
inference.py - Fully Parameterized BN to Posterior Probabilities.
"""

from pgmpy.inference import VariableElimination


class EvidenceError(ValueError):
    """Raised when evidence references invalid or unknown nodes."""


class ImpossibleEvidenceError(EvidenceError):
    """Raised when the supplied evidence has zero probability under the model.

    Attributes:
        affected_nodes: The evidence nodes whose asserted state is impossible
            (P(state | other evidence) == 0) under the current parameterised
            network.
    """

    def __init__(self, message: str, affected_nodes: list[str] | None = None) -> None:
        super().__init__(message)
        self.affected_nodes = affected_nodes or []


def check_evidence_feasibility(
    model, base_probs: dict, evidence: dict,
) -> list[str]:
    """Detect evidence whose asserted state has exactly zero probability.

    Under the Noisy-OR parameterisation every state-1 probability is bounded
    below by the node's leak (base) probability, and state-0 probabilities are
    bounded below by 1 - 0.9995, so an evidence assignment can only be
    *exactly* impossible when a node whose base probability is exactly 0 is
    asserted compromised while its parents cannot raise that probability.
    (Physical-process assets with ``p_base_override = 0`` are the realistic
    case.)

    For every affected node an exact Variable Elimination query is run to
    confirm P(node=state | other evidence) == 0.0.

    Returns:
        Sorted list of evidence nodes whose asserted state is impossible.
        Empty list means the evidence is feasible.
    """
    if not evidence:
        return []

    # Only state=1 evidence on zero-base nodes can ever be exactly impossible.
    candidates = [
        node for node, value in evidence.items()
        if value == 1 and float(base_probs.get(node, 1.0)) == 0.0
    ]
    if not candidates:
        return []

    affected: list[str] = []
    infer = VariableElimination(model)
    for node in candidates:
        other = {n: v for n, v in evidence.items() if n != node}
        try:
            result = infer.query(variables=[node], evidence=other, show_progress=False)
            p1 = float(result.get_value(**{node: 1}))
        except Exception:
            # If pgmpy cannot answer (e.g. degenerate structure) do not block
            # the analysis on a diagnostic that cannot be computed.
            continue
        if p1 == 0.0:
            affected.append(node)
    return sorted(affected)


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
            posteriors[node_id] = float(sanitized[node_id])
            continue
        result = infer.query(variables=[node_id], evidence=sanitized, show_progress=False)
        posteriors[node_id] = float(result.get_value(**{node_id: 1}))

    return posteriors, sanitized
