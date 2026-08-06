Methodological changes and justifications

This document summarizes the limited, targeted methodological changes applied during the Phase 1 scientific validation and the justification for each change. Each change was implemented only after verifying that the prior implementation was weak or could produce misleading probabilities, and after validating the correction with unit tests.

1) Combine contextual multipliers in the odds domain for device and human base probabilities

- Files modified: `backend/probability.py`
- Change: Rather than naively multiplying a linear CVSS-derived probability by exposure/patch multipliers, the implementation now:
  1. Maps CVSS to an initial base probability `p0` (configurable mapping: linear by default, optional logistic mapping for calibration).
  2. Converts `p0` to odds o = p0/(1-p0), multiplies odds by contextual multipliers (exposure, patch for devices; privilege for humans), and converts back to probability.
- Why: Multiplying probabilities directly can produce values that are not consistent with odds-based combination of independent risk multipliers and can distort the interpretation of `p0` as a prior. Combining multiplicative effects in odds space is consistent with Bayesian updating where independent multiplicative likelihood ratios multiply the prior odds (see e.g. Pearl, 1988; basic Bayesian updating in odds form).
- References:
  - Judea Pearl, "Probabilistic Reasoning in Intelligent Systems: Networks of Plausible Inference", Morgan Kaufmann, 1988. (Noisy-OR semantics and odds/likelihood reasoning.)
  - FIRST, "Common Vulnerability Scoring System (CVSS)" specification — CVSS is a severity metric, not a direct probability; mapping requires calibration.
  - NIST SP 800-30 for context on risk factors and calibration in risk assessments.
- Tests added: `tests/test_probability_odds.py`, `tests/test_human_odds.py` (monotonicity and edge-case checks). All pass.

2) Configurable CVSS→probability mapping

- Files modified: `backend/probability.py`
- Change: Added `cvss_mapping` setting with default `linear` and optional `logistic` mapping to permit calibration to empirical data or expert judgement.
- Why: CVSS provides a severity score (0-10); linear scaling is a pragmatic default but cannot be universally justified. A logistic mapping provides a small set of parameters (`k`, `x0`) to fit observed compromise probabilities when such data is available. Leaving this configurable makes the model defensible and reproducible.
- Tests: existing probability tests continue to pass.

3) Noisy-OR CPT generation verified and kept

- Files inspected: `backend/cpt_generator.py`
- Analysis: The `noisy_or_cpt` implements P(child=1 | parents) = 1 - (1 - leak) * Π_{i:parent_i=1} (1 - q_i), where q_i are edge weights and `leak` = `p_base`. This matches standard Noisy-OR semantics (see Pearl, 1988). The implementation preserves normalization and enumerates all parent states in the CPT.
- Tests added: `tests/test_noisyor_verification.py` verifying extreme weights, monotonicity, and that inference posterior matches the analytic posterior for single-parent case.

4) Allow disconnected components (independent submodels)

- Files modified: `backend/topology.py`
- Change: Topology validation no longer rejects multiple disconnected components; it logs a warning and proceeds. Disconnected components are independent Bayesian submodels and can be analyzed separately or jointly without violating probabilistic semantics.
- Why: Rejecting disconnected components is unnecessarily strict. Bayesian networks support disjoint subgraphs; rejecting them reduces the framework's practical robustness when users model multiple independent subsystems.
- Tests: full test suite run; no regressions.

5) Configurable risk thresholds

- Files modified: `backend/risk.py`
- Change: Risk level thresholds are now configurable via runtime settings rather than hard-coded constants.
- Why: Fixed thresholds are policy decisions and vary by organization/context. Making them configurable is more defensible and reproducible for industrial/academic users.

Notes on methodology and defensibility

- The framework uses Noisy-OR to parameterize combinatorial CPTs because Noisy-OR is a well-established, interpretable causal parameterization for binary causes with independence-of-causal-influence assumptions. This is standard in Bayesian Network literature (Pearl, 1988) and practical for ICS risk models where enumerating 2^k parent combinations is infeasible.

- The use of `p_base` as a leak term (background cause probability) is appropriate when `p_base` represents intrinsic compromise probability due to factors independent of modeled parents (e.g. internet-facing vulnerability, insider risk). This interpretation must be documented when presenting results.

- Edge weights are interpreted as per-edge causal strengths q_i = P(child=1 | parent_i=1, other parents inactive). These are derived from a base propagation matrix and calibrated by protocol/trust/firewall multipliers; users must treat these as expert-configurable parameters and, when possible, calibrate them to historical incident data.

- All probabilistic operations preserve normalization and have been validated with unit tests (CPT normalization, analytic posterior checks, monotonicity, extreme-value behavior).

If further empirical calibration or literature-driven parameter values are required (for e.g. mapping CVSS to priors or mapping relationship types to causal probabilities), the framework provides configuration hooks to store, version, and audit those parameters.
