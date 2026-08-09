# Metric Catalog — ICS Bayesian Risk Framework

This catalog is the authoritative reference for every important number the
platform produces.  For each metric it documents: **definition, formula,
inputs, range, interpretation, source, validation, and scientific status**.

Scientific status classification (see `docs/scientific_validation_report.md`):

| Class | Meaning |
| ----- | ------- |
| **A — Scientifically defensible** | Strong theoretical/mathematical basis, correctly implemented. |
| **B — Defensible engineering model** | Reasonable model, partly based on explicit assumptions/expert judgment. |
| **C — Heuristic** | Operationally useful, but not a calibrated probability/risk measure. |
| **D — Invalid / misleading** | Interpretation or calculation not defensible. |

> **Overarching calibration statement.** No parameter in this framework is
> empirically calibrated against incident data. Every probability is a
> **modelled (model-conditional) probability**, not a statistically
> calibrated frequency. This is stated explicitly in every relevant section
> and must be repeated in any report derived from the platform.

---

## 1. CVSS v3.1 Base Score (per vulnerability)

| Field | Value |
| ----- | ----- |
| **Definition** | Official FIRST CVSS v3.1 Base Score of a single vulnerability, computed from its vector string. |
| **Formula** | Impact = 6.42·ISS (scope unchanged) or 7.52·(ISS−0.029) − 3.25·(ISS−0.02)¹⁵ (scope changed); Exploitability = 8.22·AV·AC·PR·UI; Base = Roundup(min(Impact + Exploitability, 10)) (×1.08 when scope changed). ISS = 1 − (1−C)(1−I)(1−A). |
| **Inputs** | CVSS v3.1 vector string (`CVSS:3.1/AV:…/A:H`). |
| **Range** | [0.0, 10.0], 1 decimal. |
| **Interpretation** | *Severity*, not probability and not risk. |
| **Source** | FIRST CVSS v3.1 specification (implemented in `backend/cvss.py`). |
| **Validation** | `tests/test_cvss.py`, `tests/test_scientific_validation.py` — official scores for Heartbleed (7.5), Log4Shell (10.0), Shellshock (9.8). |
| **Scientific status** | **A** — exact implementation of a published specification. |

## 2. Effective CVSS score (per asset)

| Field | Value |
| ----- | ----- |
| **Definition** | The asset's *effective* severity: the maximum Base Score over its listed vulnerabilities. |
| **Formula** | `effective = max(score_i)` over vulnerabilities. |
| **Inputs** | Validated vulnerability list (`cve_id`, `vector`, `score`, `source`). |
| **Range** | [0.0, 10.0]; 0.0 when no vulnerabilities are listed. |
| **Interpretation** | Worst-case severity across the asset's known vulnerabilities. **Not** a likelihood. Vulnerability *count* is deliberately not modelled (see report, Limitations). |
| **Source** | `backend/cvss.py::effective_cvss_score`. |
| **Validation** | `tests/test_cvss.py`, `tests/test_scientific_validation.py`. |
| **Scientific status** | **A** for the computation; **B** for the *max* aggregation rule (a documented modelling decision). |

## 3. Intrinsic Compromise Probability (per asset)

| Field | Value |
| ----- | ----- |
| **Definition** | Modelled probability that asset *i* is compromised due to its own attributes (vulnerability severity, exposure, patch state, and for humans role/awareness/privilege), **before** any network propagation or evidence. It is the Noisy-OR *leak* of the node. |
| **Formula (device)** | `p₀ = 1/(1 + exp(−k·(CVSS − x₀)))`; then `logit(p) = logit(p₀) + Σ wⱼ·ln(Mⱼ)` for exposure/patch (and optionally protocol/trust/MITRE); capped to [1e-6, 0.9995]. |
| **Formula (human)** | `p₀ = R_role·(1 − awareness)`, adjusted by privilege via log-odds. |
| **Formula (physical)** | `p = p_base_override` (expert override). |
| **Inputs** | Asset attributes (cvss_type / vulnerabilities, exposed, patched; role, awareness, privilege; p_base_override) + settings (k, x0, multipliers, weights). |
| **Range** | (0, 0.9995], never exactly 0 or 1 (except explicit `p_base_override: 0`). |
| **Interpretation** | A **modelled** probability for the assessment scenario. **No time horizon** is defined; it is not a frequency (e.g. per-year) estimate. |
| **Source** | `backend/probability.py`. |
| **Validation** | `tests/test_probability.py`, `tests/test_probability_odds.py`, `tests/test_scientific_validation.py` (independent logistic + log-odds recomputation). |
| **Scientific status** | **B** — defensible engineering model. The logistic CVSS→probability mapping and all multipliers are explicit, documented, configurable assumptions, **not empirically calibrated**. |

## 4. Edge propagation weight (per relationship)

| Field | Value |
| ----- | ----- |
| **Definition** | Noisy-OR causal weight `qᵢ` of edge `parent → child`: the strength of the causal influence of a compromised parent on a compromised child, all other parents inactive. |
| **Formula** | `q = base(rel_type) × firewall_mult × protocol_mult × trust_mult × mitre_mult`, capped at 0.99. |
| **Inputs** | Relationship type, firewalled flag, protocol/trust/MITRE metadata + settings tables. |
| **Range** | [0, 0.99]. |
| **Interpretation** | A causal weight, **not** literally `P(child=1 | parent=1)` (the implied single-parent conditional is `1 − (1−leak)(1−q)`). |
| **Source** | `backend/graph_builder.py::edge_weight`, tables in `backend/config.py`. |
| **Validation** | `tests/test_graph_builder.py`, `tests/test_noisyor_verification.py`. |
| **Scientific status** | **B** — expert-configured causal strengths grounded in literature-consistent defaults (NIST SP 800-41 for firewalls, NIST SP 800-82 for protocols, IEC 62443-3-3 for trust). Not empirically calibrated. |

## 5. Noisy-OR CPT rows — P(node=1 | parent states)

| Field | Value |
| ----- | ----- |
| **Definition** | Conditional probability that node `X` is compromised given the binary states of its parents. |
| **Formula** | `P(X=1 | S) = 1 − (1 − leak)·Π_{i∈S}(1 − qᵢ)` with `leak = intrinsic probability of X`. |
| **Inputs** | Parent set, edge weights, intrinsic probability. |
| **Range** | [0, 1]; every row normalises: P(0) + P(1) = 1. |
| **Interpretation** | Noisy-OR semantics: the child is compromised if the leak occurs or at least one active cause is not inhibited. Assumes causes are conditionally independent given the child's state. |
| **Source** | `backend/cpt_generator.py::noisy_or_cpt`. |
| **Validation** | `tests/test_noisyor_verification.py`, `tests/test_cpt_generator.py`, `tests/test_scientific_validation.py` (independent closed-form row-by-row check + normalisation over all parent configs). |
| **Scientific status** | **A** (implementation: exact closed form, normalised) / **B** (semantics: Noisy-OR is an explicit modelling choice). |

## 6. Posterior Compromise Probability (per asset)

| Field | Value |
| ----- | ----- |
| **Definition** | Modelled probability that asset *i* is compromised **given the evidence and the full Bayesian network**: `P(Xᵢ=1 | evidence)`, computed by exact Variable Elimination. |
| **Formula** | Exact marginal from the parameterised BN: `P(Xᵢ=1 | e) = Σ_{X\Xᵢ} P(X, e) / P(e)`. |
| **Inputs** | Parameterised network (CPTs) + hard evidence `{node: 0|1}`. |
| **Range** | [0, 1]; evidence nodes are pinned to their asserted state (0 or 1). |
| **Interpretation** | A posterior **model probability** for the assessment scenario, conditional on the evidence. Not a calibrated frequency; **no time horizon**. |
| **Source** | `backend/inference.py` (pgmpy VariableElimination). |
| **Validation** | `tests/test_inference.py`, `tests/test_noisyor_verification.py`, `tests/test_scientific_validation.py` (posteriors matched against **brute-force joint enumeration** for chain and collider structures, with and without evidence). |
| **Scientific status** | **A** (mathematics: exact inference) / **B** (interpretation: prior model + evidence are modelled, not empirical). |

## 7. Consequence Impact (per asset)

| Field | Value |
| ----- | ----- |
| **Definition** | Normalised consequence of compromise: user-supplied consequence severity on a 0–10 scale, normalised and scaled by the blast-radius scope multiplier. |
| **Formula** | `Impact = (consequence_severity / 10) × scope_multiplier × impact_weight`, with `scope_multiplier = 1 + (scope − 1) × 0.1` for `scope ∈ [1, 5]`. |
| **Inputs** | `consequence_severity` (0–10), `scope` (1–5), `impact_weight` setting. |
| **Range** | [0, ~1.4] with defaults (severity 10, scope 5, weight 1 → 1.4). |
| **Interpretation** | A normalised consequence score (severity×blast-radius), **not** a probability and not a monetary loss. |
| **Source** | `backend/risk.py::build_risk_table` / `m_scope`. |
| **Validation** | `tests/test_risk.py`, `tests/test_scientific_validation.py` (independent recomputation, scope-preservation regression). |
| **Scientific status** | **B** — a defensible consequence normalisation; the 0–10 severity scale and scope mapping are expert conventions, not a standard. |

## 8. Risk Index (per asset)

| Field | Value |
| ----- | ----- |
| **Definition** | The primary risk ranking metric: posterior probability × normalised consequence impact. A **relative ranking index**, not expected loss. |
| **Formula** | `Risk = P(compromised | evidence) × Impact`. |
| **Inputs** | Posterior probability, consequence severity, scope, impact_weight. |
| **Range** | [0, ~1.4] with defaults. |
| **Interpretation** | Higher = higher priority for investigation/mitigation. **Not** a probability, **not** ALE, **not** monetary. The product of a probability and a normalised consequence is bounded and interpretable only as an index. |
| **Source** | `backend/risk.py`. |
| **Validation** | `tests/test_risk.py`, `tests/test_scientific_validation.py`. |
| **Scientific status** | **B** — transparent, bounded, ranking-focused. Labels in UI/PDF consistently describe it as an index, never as a probability. |

## 9. Risk Level (per asset / network)

| Field | Value |
| ----- | ----- |
| **Definition** | Qualitative classification of the Risk Index into Low / Moderate / High / Critical. |
| **Formula** | Compare Risk Index against **single configurable thresholds**: Critical ≥ c, High ≥ h, Moderate ≥ m, Low < m (defaults 0.75 / 0.50 / 0.25). |
| **Inputs** | Risk Index, `risk_thresholds` setting. |
| **Range** | {Low, Moderate, High, Critical}. |
| **Interpretation** | Prioritisation bands. Thresholds are **engineering calibration placeholders**, not derived from a formal standard (ISO 27005/NIST SP 800-30 use qualitative matrices); they are documented as configurable. |
| **Source** | `backend/risk.py::risk_level_for`; single source of truth propagated to API, PDF, UI. |
| **Validation** | `tests/test_risk.py`, `tests/test_scientific_validation.py`. |
| **Scientific status** | **B** with an explicit caveat: arbitrary-but-reasonable thresholds, honestly labelled. |

## 10. Overall Network Risk

| Field | Value |
| ----- | ----- |
| **Definition** | Network-level summary of the risk register. |
| **Formula** | `overall_risk = max(risk index)` over assets; mean, median and per-level counts also reported. |
| **Inputs** | Risk register. |
| **Range** | [0, ~1.4]. |
| **Interpretation** | Worst-case single-asset risk (defensible, size-independent). Mean/median give context. No severity double-counting (severity is embedded per-asset only). |
| **Source** | `backend/risk.py::compute_aggregate_risk`. |
| **Validation** | `tests/test_risk.py`, `tests/test_scientific_validation.py`. |
| **Scientific status** | **B**. |

## 11. Attack-path score

| Field | Value |
| ----- | ----- |
| **Definition** | Priority score for a directed path from an entry node to a high-consequence target through the Bayesian DAG. |
| **Formula** | `score = path_prob × target_risk_index`, where `path_prob = min(posterior along path)` (default "weakest link") or the product of posteriors (`ATTACK_PATH_SCORING=product`). |
| **Inputs** | Posteriors, evidence entry points, target risk indices. |
| **Range** | [0, ~1.4]. |
| **Interpretation** | Prioritises investigation; **not** proof of a real intrusion and **not** a probability of the whole path being traversed (the default `min` is a weakest-link heuristic, not a joint probability). |
| **Source** | `backend/attack_paths.py`. |
| **Validation** | `tests/test_attack_paths.py`. |
| **Scientific status** | **C** — documented heuristic for triage. The alternative product mode is closer to a cumulative-path probability but still uses modelled posteriors. |

## 12. Settings snapshot (`settings_used`)

| Field | Value |
| ----- | ----- |
| **Definition** | The complete model-parameter set that produced a given run (k, x0, mapping, exposure/patch multipliers and weights, propagation weights, firewall/protocol/trust/MITRE tables, risk thresholds, impact weight). |
| **Formula** | Copy of active settings restricted to `DEFAULT_SETTINGS` keys. |
| **Inputs** | Active runtime settings. |
| **Range** | n/a. |
| **Interpretation** | **Traceability**: lets any reviewer reproduce or audit why a number has the value it has. Runs with non-default settings also surface a warning. |
| **Source** | `backend/settings.py::get_model_settings_snapshot`; recorded in the result dict, `metrics.json`, `summary.txt`, PDF "Model Parameters" section, and the API. |
| **Validation** | `tests/test_scientific_validation.py` (snapshot presence, exclusion of UI-only keys, non-default detection and warning). |
| **Scientific status** | **A** — this is a data-integrity mechanism; required for professional reproducibility. |

---

*This catalog is kept in sync with `docs/scientific_validation_report.md`,
`docs/model-assumptions.md`, `docs/parameter-provenance.md` and the README.*
