# Parameter Provenance — ICS Bayesian Risk Framework

This table records, for every configurable model parameter: its meaning,
current default value, allowed range, provenance, calibration status, whether
it is configurable, and its sensitivity behaviour.

**Provenance classifications used**

| Classification          | Meaning                                                                 |
| ----------------------- | ----------------------------------------------------------------------- |
| Expert judgment         | Set by the framework authors based on security-domain reasoning         |
| Literature-derived      | Consistent with published guidance/standards (e.g. NIST SP 800-41,      |
|                         | NIST SP 800-82, IEC 62443) but not fitted to data                       |
| Framework default       | Arbitrary-but-reasonable starting value chosen for the tool             |
| Provenance not established | No reliable source; treat as placeholder                               |

> **Overarching calibration statement:** *none* of these parameters is
> empirically calibrated against incident data in this repository. Every value
> is an expert judgment, literature-consistent default, or framework default.
> Organisations must calibrate before operational use.

---

## Core CVSS → probability mapping

| Parameter | Meaning | Default | Range | Source | Classification | Calibration | Configurable | Sensitivity |
| --------- | ------- | ------: | ----: | ------ | -------------- | ----------- | ------------ | ----------- |
| `cvss_mapping` | Severity→probability function: `logistic` (recommended) or `linear` (legacy) | `logistic` | `logistic` \| `linear` | Framework design | Framework default | Not calibrated | Yes | High: mapping choice changes every intrinsic probability |
| `k` (`cvss_logistic_params.k`) | Logistic slope: steepness of the severity→probability curve at the midpoint | `0.8` | `> 0` (UI: 0.1–2) | Expert judgment | Expert judgment | Not calibrated | Yes | High: ±20% moves intrinsic probabilities materially |
| `x0` (`cvss_logistic_params.x0`) | Logistic midpoint: CVSS score at which P = 0.5 | `5.0` | `[0, 10]` | Expert judgment (centred on medium severity) | Expert judgment | Not calibrated | Yes | High: shifting x0 rescales all intrinsic probabilities |

## Intrinsic-probability contextual multipliers

| Parameter | Meaning | Default | Range | Source | Classification | Calibration | Configurable | Sensitivity |
| --------- | ------- | ------: | ----: | ------ | -------------- | ----------- | ------------ | ----------- |
| `exposure_weight` | Weight of the exposure log-odds adjustment | `1.0` | `≥ 0` | Framework default | Framework default | Not calibrated | Yes | Moderate |
| `exposure_multipliers.true` | Multiplier for internet-facing assets | `1.3` | `≥ 0` | Expert judgment | Expert judgment | Not calibrated | Yes | Moderate |
| `exposure_multipliers.false` | Multiplier for non-exposed assets | `0.3` | `≥ 0` | Expert judgment | Expert judgment | Not calibrated | Yes | Moderate |
| `patch_weight` | Weight of the patch log-odds adjustment | `1.0` | `≥ 0` | Framework default | Framework default | Not calibrated | Yes | Moderate |
| `patch_multipliers.true` | Multiplier for fully patched assets | `0.9` | `≥ 0` | Expert judgment | Expert judgment | Not calibrated | Yes | Moderate |
| `patch_multipliers.false` | Multiplier for unpatched assets | `1.2` | `≥ 0` | Expert judgment | Expert judgment | Not calibrated | Yes | Moderate |
| `protocol_multipliers` | Per-protocol factor (modbus 1.15, http 1.25, mqtt 1.20, …) | table | `≥ 0` | NIST SP 800-82 Rev. 3 (Stouffer et al.) reasoning about unauthenticated ICS protocols | Literature-derived | Not calibrated | Yes | Low–moderate |
| `trust_multipliers` | Purdue/zone-trust factor (high 0.70, low 1.35, none 1.50) | table | `≥ 0` | IEC 62443-3-3 / Purdue model concepts | Literature-derived | Not calibrated | Yes | Low–moderate |
| `mitre_multipliers` | Per-technique factor (T0886 1.20, T0855 1.25, …) | table | `≥ 0` | Frequency/impact of techniques in public ICS incident reporting (e.g. Dragos, Mandiant annual reports) | Literature-derived | Not calibrated | Yes | Low |
| `impact_weight` | Weight applied to consequence impact | `1.0` | `≥ 0` | Framework default | Framework default | Not calibrated | Yes | Moderate (affects risk index) |

## Propagation / Noisy-OR

| Parameter | Meaning | Default | Range | Source | Classification | Calibration | Configurable | Sensitivity |
| --------- | ------- | ------: | ----: | ------ | -------------- | ----------- | ------------ | ----------- |
| `propagation_weights` (edge `w`) | Noisy-OR causal weight per relationship type (`controls` 0.70, `actuates` 0.60, `connects-to` 0.50, `monitors` 0.20, `programs / operates` 0.80) | table | `[0, 1]` | Expert judgment | Expert judgment | Not calibrated | Yes | High: propagation weights drive posteriors and risk ranking |
| `firewall_multipliers.true` | Multiplier applied to propagation across a firewalled link | `0.30` | `≥ 0` (≤ false) | NIST SP 800-41 (properly configured firewalls block ~70 % of network-borne attacks) | Literature-derived | Not calibrated | Yes | Moderate–high |

## Risk model

| Parameter | Meaning | Default | Range | Source | Classification | Calibration | Configurable | Sensitivity |
| --------- | ------- | ------: | ----: | ------ | -------------- | ----------- | ------------ | ----------- |
| `risk_thresholds.critical` | Lower bound for the Critical risk level | `0.75` | `> high` | Expert judgment (standard 0.75 upper band) | Expert judgment | Not calibrated | Yes | High: level counts and colours change with thresholds |
| `risk_thresholds.high` | Lower bound for High | `0.50` | `> moderate, < critical` | Expert judgment | Expert judgment | Not calibrated | Yes | High |
| `risk_thresholds.moderate` | Lower bound for Moderate | `0.25` | `≥ 0, < high` | Expert judgment | Expert judgment | Not calibrated | Yes | High |
| scope multiplier | CVSS v3.1 scope factor in impact normalisation | per-vector | `1.0`/`1.5` | Official CVSS v3.1 spec | Empirical (specification constant) | n/a (fixed by spec) | No | Fixed by vector |
| `impact_weight` | Weight on consequence impact in the risk index | `1.0` | `≥ 0` | Framework default | Framework default | Not calibrated | Yes | Moderate |

## Fixed engineering constants (not analyst-configurable)

| Constant | Meaning | Value | Source |
| -------- | ------- | ----: | ------ |
| `P_BASE_CAP` | Soft cap for probabilities | `0.9995` | Framework design (avoid exact 0/1) |
| probability floor | Lower clamp | `1e-6` | Framework design |
| CVSS severity bands | Informational/Low/Medium/High/Critical | 0.0/0.1/4.0/7.0/9.0 | Official CVSS v3.1 spec |
| CVSS scope multipliers | Unchanged/Changed | 1.0/1.5 | Official CVSS v3.1 spec |

## Aggregated defaults (single source of truth)

All defaults above are defined in exactly one place:
`backend/settings.py::DEFAULT_SETTINGS`, with the static lookup tables in
`backend/config.py`. The API, PDF reports, CLI, and frontend all consume the
active values through `backend/settings.get_settings()`; the frontend
receives them via `GET /settings` and never hardcodes thresholds or CVSS
parameters.

---

*This document is part of the delivered repository and is kept in sync with
`docs/model-assumptions.md`, the README, and the internship report.*
