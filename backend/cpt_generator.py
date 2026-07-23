"""
cpt_generator.py - Builds each node's CPT via noisy-OR.
"""

import itertools

from pgmpy.factors.discrete import TabularCPD


def noisy_or_cpt(node_id: str, model, edge_weights: dict, base_probs: dict) -> TabularCPD:
    parents = list(model.get_parents(node_id))
    p_base = base_probs[node_id]

    if not parents:
        return TabularCPD(
            variable=node_id,
            variable_card=2,
            values=[[1 - p_base], [p_base]],
            state_names={node_id: [0, 1]},
        )

    k = len(parents)
    weights = [edge_weights[(p, node_id)] for p in parents]

    p1_row = []
    for combo in itertools.product([0, 1], repeat=k):
        prod_term = 1.0
        for state, w in zip(combo, weights):
            if state == 1:
                prod_term *= (1 - w)
        p1_row.append(1 - (1 - p_base) * prod_term)

    p0_row = [1 - v for v in p1_row]

    return TabularCPD(
        variable=node_id,
        variable_card=2,
        values=[p0_row, p1_row],
        evidence=parents,
        evidence_card=[2] * k,
        state_names={n: [0, 1] for n in [node_id] + parents},
    )


def parameterize(model, edge_weights: dict, base_probs: dict):
    for node_id in model.nodes():
        cpd = noisy_or_cpt(node_id, model, edge_weights, base_probs)
        model.add_cpds(cpd)

    assert model.check_model()
    return model


def cpts_to_dict(model) -> dict:
    out = {}
    for node_id in model.nodes():
        cpd = model.get_cpds(node_id)
        parents = list(model.get_parents(node_id))
        k = len(parents)

        rows = []
        if k == 0:
            p1 = float(cpd.get_value(**{node_id: 1}))
            rows.append({"parent_state": {}, "p_compromised": round(p1, 6)})
        else:
            for combo in itertools.product([0, 1], repeat=k):
                parent_state = dict(zip(parents, combo))
                query_state = {node_id: 1, **parent_state}
                p1 = float(cpd.get_value(**query_state))
                rows.append({
                    "parent_state": {p: int(v) for p, v in parent_state.items()},
                    "p_compromised": round(p1, 6),
                })

        out[node_id] = {"parents": parents, "rows": rows}

    return out
