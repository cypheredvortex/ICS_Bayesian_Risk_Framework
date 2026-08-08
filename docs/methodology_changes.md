# Methodological changes and justifications

This document summarizes the methodological and corrective changes applied
during the scientific validation of the framework, and the justification for
each change. Each correction was applied only after verifying that the prior
implementation was weak, misleading, or mathematically unsound, and was
validated with unit tests.

## 1) Official CVSS v3.1 implementation (`backend/cvss.py`)

- **Files added:** `backend/cvss.py`; `tests/test_cvss.py`
- **Problem:** the framework accepted a single hard-coded numeric "CVSS" value
  per asset and never implemented the CVSS methodology itself. CVSS was also
  conceptually conflated with probability in places.
- **Change:** a dedicated module implements the official FIRST CVSS v3.1 Base
  Score equations (Impact = 6.42·ISS scope-unchanged or
  7.52·(ISS−0.029)−3.25·(ISS−0.02)¹⁵ scope-changed, Exploitability =
  8.22·AV·AC·PR·UI, Base = Roundup(min(Impact + Exploitability, 10))).
  Assets may now declare a `vulnerabilities` list `{cve_id, vector, source}`;
  each vector is scored with the published methodology (never a proprietary
  formula), and the asset's effective score is the maximum over its
  vulnerabilities. The legacy single-number `cvss_type` field remains
  supported as a shortcut for one implicit vulnerability.
- **Why:** CVSS is a *severity* scoring system (0–10), not a probability and
  not a risk. Replacing ad-hoc numbers with the official v3.1 equations makes
  every displayed score traceable to the FIRST specification.
- **Tests:** `tests/test_cvss.py` verifies the Base Score of published vectors
  (Heartbleed 7.5, Log4Shell 10.0, Shellshock 9.8, …), rejection of malformed /
  incomplete / CVSS v4.0 vectors, severity rating boundaries, vulnerability
  normalization (vector is authoritative over a provided numeric score), and
  effective-score = max semantics.

## 2) CVSS → probability is an explicit, configurable modelling assumption

- **Files modified:** `backend/probability.py`, `backend/settings.py`,
  `backend/config.py`
- **Change:** the default mapping is a calibrated logistic curve
  `P₀ = 1 / (1 + exp(−k·(CVSS − x₀)))` (k = 0.8, x₀ = 5.0), documented as a
  modelling assumption, with parameters exposed as first-class settings
  (`cvss_mapping`, `cvss_logistic_params`). A linear mapping remains available
  only for backward compatibility and is explicitly not recommended.
- **Why:** direct linear scaling P = CVSS/10 implies a CVSS-10 vulnerability
  guarantees compromise (P = 1.0), which is empirically indefensible. The
  logistic curve keeps probabilities strictly in (0, 1) — a CVSS-0 asset still
  carries residual compromise risk (unknown/zero-day vulnerabilities,
  misconfiguration) — and provides two parameters for organisation-level
  calibration against incident data.
- **Tests:** updated `tests/test_probability.py`, `tests/test_probability_odds.py`
  (CVSS-0 → small but non-zero probability), new settings validation tests for
  `cvss_mapping`/`cvss_logistic_params`.

## 3) Removed the dead "CVSS weight" setting

- **Files modified:** `backend/settings.py`, `backend/config.py`,
  `frontend/src/App.tsx`, `frontend/src/components/SettingsPanel.tsx`,
  `frontend/src/types.ts`, `frontend/src/constants.ts`
- **Problem:** the `cvss_weight` setting was exposed in the API and the UI but
  was never used by any computation — a dead knob.
- **Change:** removed. CVSS influence is already controlled by the logistic
  calibration parameters, which have a defensible interpretation.

## 4) Risk model normalised and clarified (`backend/risk.py`)

- **Files modified:** `backend/risk.py`, `backend/cli.py`, `backend/pdf_reports.py`,
  `frontend/src/App.tsx`, `frontend/src/components/ResultsDashboard.tsx`
- **Problem:** with the previous default consequence severity (1.0) the Risk
  Index was numerically equal to the posterior probability, collapsing
  "risk" and "probability" into one number. The network aggregate was a
  severity-weighted mean that double-counted severity.
- **Change:** Risk Index = P(compromised | evidence) × Impact with
  Impact = (consequence_severity / 10) × scope_multiplier. The index is bounded
  (≈ [0, 1.4]) and the UI shows Probability, Impact and Risk as separate
  columns. Default thresholds: Critical ≥ 0.75, High ≥ 0.50, Moderate ≥ 0.25,
  Low < 0.25 (configurable). The network-level risk is the worst-case
  single-asset index (max); mean, median and per-level counts are also
  reported. The severity-weighted mean was removed (it embedded severity twice).
- **Why:** a risk index must be transparently defined as a product of a
  probability and a consequence score, and must never be presented as if it
  were a probability.
- **Tests:** updated `tests/test_risk.py` (thresholds, bounded range,
  P × impact semantics).

## 5) Input validation hardened (`backend/topology.py`, `backend/importers.py`)

- **Change:** strict validation of CVSS ∈ [0, 10], consequence severity ∈
  [0, 10], awareness ∈ [0, 1], p_base_override ∈ [0, 1], with actionable
  error messages; CSV import now preserves cybersecurity columns
  (cvss_type, exposed, patched, consequence_severity, …) instead of silently
  dropping them; self-loops and duplicate edges are removed with a warning
  instead of triggering a false "cycle" error.
- **Why:** silently clamping or dropping invalid inputs hides data-quality
  problems; rejecting them with precise messages makes the framework
  trustworthy. The self-loop bug produced a misleading error on valid inputs.
- **Tests:** `tests/test_topology_validation.py` (regressions for self-loops,
  duplicate edges, out-of-range attributes, CSV garbage, kind inference).

## 6) Honest format support: legacy .vsd removed

- **Files modified:** `backend/importers.py`, `tests/test_api.py`
- **Problem:** the API advertised `.vsd` (binary Visio) support although it
  could only be parsed by shelling out to LibreOffice when installed — an
  unverifiable claim.
- **Change:** `.vsd` uploads are rejected with actionable conversion guidance
  (Visio "Save As" → .vsdx, or export to JSON/CSV/GraphML). `.vsdx` and `.vdx`
  remain genuinely supported.
- **Tests:** `tests/test_api.py` asserts a helpful 400 response for `.vsd`.

## 7) Noisy-OR CPT generation — verified and kept

- **Files inspected:** `backend/cpt_generator.py`
- **Analysis:** `noisy_or_cpt` implements
  P(child=1 | parents) = 1 − (1 − leak) · Πᵢ₊ (1 − qᵢ), where qᵢ are edge
  weights and `leak` = `p_base` (intrinsic probability). This matches standard
  Noisy-OR semantics (Pearl, 1988): every conditional distribution normalises
  to 1 and probabilities stay in [0, 1].
- **Tests:** `tests/test_noisyor_verification.py` (extreme weights, leak,
  monotonicity, analytic single-parent posterior match) and
  `tests/test_cpt_generator.py` (normalisation, model check).

## 8) Bayesian inference is genuine (pgmpy Variable Elimination)

- **Files inspected:** `backend/inference.py`
- **Analysis:** posteriors are produced by exact inference on the
  parameterised network; evidence is validated (unknown nodes / non-binary
  states rejected), and analytic checks confirm the posterior matches manual
  Bayes' rule computation for single-parent models. No shortcut "Bayesian"
  values are used.

## Notes on methodology and defensibility

- Noisy-OR is a well-established, interpretable causal parameterisation for
  binary causes under the independence-of-causal-influence assumption. It is
  standard in Bayesian Network literature (Pearl, 1988) and practical for ICS
  risk models where enumerating 2^k parent combinations is infeasible.
- `p_base` is used as the leak term (background cause probability): the
  intrinsic compromise probability due to factors independent of the modelled
  parents (internet-facing vulnerability, insider risk, unknown zero-days).
  This interpretation is documented in the UI and in the report.
- Edge weights are per-edge causal strengths q_i = P(child=1 | parent_i=1,
  other parents inactive), derived from a base propagation matrix calibrated
  by protocol/trust/firewall multipliers. Users must treat these as
  expert-configurable parameters and calibrate them to historical incident
  data when available.
- All probabilistic operations preserve normalisation and are validated by
  unit tests (CPT normalisation, analytic posterior checks, monotonicity,
  extreme-value behaviour).
- Remaining assumptions and limitations are stated explicitly in the README
  and in the technical report: the CVSS→probability curve, the consequence
  severity scale, the propagation weights and the risk thresholds are expert
  inputs, not universal constants.
