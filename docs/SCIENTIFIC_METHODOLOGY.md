# ICS Bayesian Risk Assessment Framework — Scientific & Mathematical Methodology

> **Status:** authoritative reference. Every formula, constant, default, and workflow described in this document was extracted from the current source code (backend modules `cvss.py`, `probability.py`, `graph_builder.py`, `cpt_generator.py`, `inference.py`, `risk.py`, `attack_paths.py`, `settings.py`, `config.py`, `topology.py`, `enrichment.py`, `sensitivity.py`) and verified by executing the actual pipeline. Where the implementation deviates from a textbook method, that deviation is documented explicitly. **The implementation is the source of truth.**

---

## 1. Introduction

### 1.1 Problem being solved

Industrial Control Systems (ICS) run physical processes — water treatment, power substations, manufacturing — whose compromise can produce consequences beyond data loss: physical damage, safety incidents, environmental harm. Risk assessment for such systems must therefore integrate:

| Dimension | Question it answers |
| --- | --- |
| **Severity** | How *bad* is a vulnerability's potential impact? (a property of the vulnerability) |
| **Likelihood** | How *likely* is an asset to be compromised? (a property of the asset in its environment) |
| **Propagation** | How does compromise of one asset *influence* others? (a property of the network) |
| **Uncertainty** | What do we *not* know, and how does evidence update belief? (a property of the model) |
| **Consequence** | What is the *worth* of protecting this asset? (a property of the process) |
| **Risk** | The *combination* of likelihood and consequence (the decision quantity) |

A conventional vulnerability score alone answers none of these jointly: a CVSS score of 9.8 on an HMI says nothing about whether the PLC behind it is reachable, whether the operator has been phished, or whether the pump it actuates is the crown jewel. This framework's scientific objective is to make all six dimensions computable in one internally consistent model.

### 1.2 Scientific objective

The framework estimates, for every asset:

> **P(asset is compromised | its intrinsic characteristics, its place in the network, and the evidence observed)** — the *posterior compromise probability* — and combines it with a *consequence impact* score to produce a **risk index** used to rank assets.

The Bayesian network is the mathematical engine: it turns a static ICS topology plus asset attributes into a joint probability distribution over compromise states, so that evidence entered anywhere in the network propagates to every other asset in a principled way (Bayes' rule), instead of being combined by ad-hoc rules.

### 1.3 Overall methodology

The implementation performs, in order:

```mermaid
flowchart TD
    A[ICS topology: assets + relationships] --> B[Normalize + validate: DAG, kinds, zones, defaults]
    B --> C[Per-asset effective CVSS v3.1 severity]
    C --> D[Severity → intrinsic probability via logistic mapping]
    D --> E[Contextual log-odds adjustment: exposure, patch, human, physical]
    E --> F[Intrinsic compromise probability p_base — the leak]
    B --> G[Per-edge propagation weight w = min(0.99, base × controls)]
    F --> H[CPT construction — Noisy-OR with leak p_base]
    G --> H
    H --> I[Bayesian network: DAG + CPTs]
    I --> J[Evidence: hard 0/1 observations]
    J --> K[Exact inference: Variable Elimination]
    K --> L[Posterior compromise probabilities]
    L --> M[Risk index = posterior × impact]
    B --> N[Impact = severity/10 × scope × weight]
    N --> M
    M --> O[Ranking, thresholds, aggregate risk]
    M --> P[Attack path analysis]
```

The next sections follow this chain stage by stage. Each stage defines its mathematical objects, gives the exact implemented equations, and states the assumptions they rest on.

### 1.4 Notation and conventions

- Binary compromise variable: `X_i ∈ {0, 1}` for asset `i` (`1` = compromised, `0` = not compromised).
- `P(X_i = 1)` without further conditioning is the **marginal** under the network; `P(X_i = 1 | E)` is the **posterior** given evidence `E`.
- All probabilities are soft-capped away from exact `0` and `1` (see §5.5) so that Bayesian updating remains reversible.
- All model parameters are runtime-configurable; defaults are quoted exactly as in `backend/settings.py` and `backend/config.py`.

---

## 2. Mathematical objects

| Symbol | Definition | Where it comes from | First used |
| --- | --- | --- | --- |
| `G = (V, E)` | Directed graph of the ICS topology; `V` = asset nodes, `E` = directed relationship edges | Topology import + validation | §3 |
| `Aᵢ` | Asset `i`; a record of normalized attributes (`kind`, `cvss_type`, `exposed`, `patched`, `consequence_severity`, `scope`, …) | Topology normalization + enrichment | §3 |
| `Vᵢ` | Set of vulnerability records on device asset `i` (CVE id + CVSS vector/score, analyst-supplied) | Topology | §4 |
| `Cᵢ` | **Effective CVSS v3.1 Base Score** of asset `i` = max over `Vᵢ` (0.0 if none) | `cvss.effective_cvss_score` | §4 |
| `Pᵢ` / `p_baseᵢ` | **Intrinsic compromise probability** of asset `i` (the Noisy-OR leak) | `probability.base_prob` | §5 |
| `wᵢⱼ` | **Propagation weight** of edge `(i → j)` — causal influence strength | `graph_builder.edge_weight` | §6 |
| `k`, `x₀` | Logistic curve steepness and midpoint | settings, defaults `0.8`, `5.0` | §5 |
| `w_exposure`, `w_patch` | User weights for exposure/patch log-odds factors | settings, default `1.0` | §5 |
| `θ_i` | CPT of node `i`: `P(X_i | Parents(X_i))` | `cpt_generator.noisy_or_cpt` | §8 |
| `E` | Evidence map `{node: 0|1}` — hard evidence only | analyst input | §10 |
| `P(X_i = 1 | E)` | Posterior compromise probability | `inference` (Variable Elimination) | §11 |
| `Sᵢ` | Consequence severity of asset `i`, user-supplied on a 0–10 scale | topology | §13 |
| `σ_i` | Scope multiplier `1 + (scope − 1)·0.1`, scope ∈ [1,5] → [1.0, 1.4] | `risk.m_scope` | §13 |
| `w_impact` | Organisation-level impact weight | settings, default `1.0` | §13 |
| `Iᵢ` | **Impact** = `(Sᵢ/10)·σᵢ·w_impact` | `risk.build_risk_table` | §13 |
| `Rᵢ` | **Risk index** = `P(X_i = 1|E) × Iᵢ` | `risk.build_risk_table` | §14 |
| `τ_c`, `τ_h`, `τ_m` | Risk thresholds: critical ≥ 0.75, high ≥ 0.50, moderate ≥ 0.25 | settings | §15 |

---

## 3. Stage 1 — ICS topology and asset representation

### 3.1 Why topology matters mathematically

Compromise is not independent across assets: a PLC reached through an HMI inherits risk from the HMI; a physical pump inherits risk from the PLC that actuates it. The topology supplies the **dependency skeleton** of the probabilistic model. Without it, each asset would be scored in isolation and the two most important ICS facts — *lateral movement* and *blast radius* — would be invisible. The framework encodes the topology as a **directed graph**

```
G = (V, E)
```

- `V` — the set of asset nodes. Each node is a binary Bayesian variable later on.
- `E` — the set of **directed** edges `source → target`, taken from the topology's relationships. Direction is causal and matches the relationship semantics (e.g. `hmi → plc`, `plc → pump`).

Directionality is not cosmetic: in the Bayesian network, compromise flows **parent → child** (cause → effect). An HMI compromised by a phishing e-mail is the *cause*; the PLC it can then be used to reach is the *effect*. Reversing an edge would invert the causal reading and produce nonsense (e.g. "compromising the PLC compromises the HMI").

### 3.2 Asset model

Each asset is normalized to a canonical record (`backend/topology.normalize_asset`) with an identifier, a name, and a **kind** — one of exactly three:

| Kind | Meaning | Model-relevant attributes |
| --- | --- | --- |
| `device` | Controllers, HMI, servers, network gear | `vulnerabilities`/`cvss_type`, `exposed`, `patched`, `consequence_severity`, `scope` |
| `human` | Operators, engineers, admins | `role`, `awareness`, `privilege`, `consequence_severity` |
| `physical` | Pumps, valves, tanks, sensors | `p_base_override`, `consequence_severity` |

Kind is taken from an explicit `kind`/`type`/`category` attribute when present, otherwise inferred heuristically from the asset name by whole-token keyword matching (human keywords first, then physical, then device; default `device`). Kind decides **which probability model** the asset uses (§5.1) — this is a modeling decision, not metadata.

**Defaulted attributes** (`backend/enrichment.enrich_asset`): when a field is absent, the framework fills in conservative defaults so the pipeline never stalls:

| Kind | Defaults injected |
| --- | --- |
| `device` | `cvss_type = 5.0`, `exposed = True`, `patched = False`, `consequence_severity = 5.0` |
| `human` | `role` inferred from name (default `operator`), `awareness = 0.35`, `privilege` mapped from role, `consequence_severity = 3.0` |
| `physical` | `p_base_override = 0.01`, `consequence_severity = 4.0` |

Zones (Purdue-level-like labels: `Level 0…3`, `DMZ`, `Corporate`, `Internet`, …) are detected from names or explicit attributes and retained as grouping metadata; they do not alter the mathematics directly but surface in reporting and coverage review.

### 3.3 Relationship model

Each relationship is normalized to a tuple `(source, target, rel_type, firewalled, metadata)`:

- `rel_type` ∈ the supported set, which doubles as the **edge-weight lookup key**:
  `controls`, `monitors`, `actuates`, `connects-to`, `programs / operates`.
- `firewalled` ∈ `{True, False}` — a binary security-control flag.
- `metadata` — optional `protocol`, `trust_level`, `mitre_technique` annotations that modulate the propagation weight (§6).

### 3.4 Validation (what is allowed into the model)

`backend/topology.validate_graph` enforces the mathematical prerequisites of a Bayesian network:

- Unknown asset references → **rejected** (error).
- Unknown relationship types → **rejected** (a typo must never silently become `connects-to`).
- Self-loops → **removed with a warning** (no causal information).
- Duplicate edges → **removed with a warning** (first occurrence wins).
- **Cycles → rejected**: a Bayesian network requires a Directed Acyclic Graph (DAG); a cycle would make the joint distribution ill-defined.
- Zero relationships with ≥ 2 assets → **rejected**.
- Multiple weakly-connected components → allowed with a warning (they become independent sub-models).

**Why validation is part of the methodology:** the probabilistic semantics of the whole pipeline are only coherent on a DAG whose edges are typed. Validation is the gate that guarantees the downstream math is well-posed.

---

## 4. Stage 2 — Vulnerabilities and CVSS v3.1

### 4.1 CVSS is severity, not probability

CVSS v3.1 (FIRST) produces a **Base Score in [0, 10]** that ranks the *severity of a vulnerability* under standard assumptions. It is **not** a compromise probability: a score of 9.8 does not mean "98 % chance of compromise" — no frequency or likelihood claim is attached to it. The framework respects this distinction at every stage: severity is a *model input*; probability is a *derived quantity* produced by an explicit, configurable mapping (§5).

### 4.2 Vulnerability ingestion

Vulnerabilities are **analyst-supplied**. The framework does **not** query NVD or any external feed; a `source` field on each record is descriptive provenance metadata only. Each vulnerability entry is either:

- a CVSS v3.1 vector string (`CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`), or
- a dict with a numeric `score` (used only when no vector is given; a vector is authoritative whenever present), optionally with `cve_id`.

### 4.3 The official CVSS v3.1 Base Score equations

`backend/cvss.py` implements the FIRST v3.1 specification verbatim. Metric weights (spec Tables 2–7):

| Metric | Values |
| --- | --- |
| `AV` Attack Vector | `N=0.85`, `A=0.62`, `L=0.55`, `P=0.20` |
| `AC` Attack Complexity | `L=0.77`, `H=0.44` |
| `PR` Privileges Required (scope unchanged) | `N=0.85`, `L=0.62`, `H=0.27` |
| `PR` Privileges Required (scope changed) | `N=0.85`, `L=0.68`, `H=0.50` |
| `UI` User Interaction | `N=0.85`, `R=0.62` |
| `C`,`I`,`A` Impact | `H=0.56`, `L=0.22`, `N=0.00` |

**Impact Sub-Score (ISS):**

```
ISS = 1 − (1 − C)·(1 − I)·(1 − A)
```

**Impact** (scope unchanged):

```
Impact = 6.42 · ISS
```

**Impact** (scope changed — the special-case equations):

```
Impact = 7.52·(ISS − 0.029) − 3.25·(ISS − 0.02)¹⁵
```

**Exploitability:**

```
Exploitability = 8.22 · AV · AC · PR · UI
```

**Base Score** with the official Roundup (smallest number to one decimal ≥ input):

```
Base (scope unchanged) = Roundup( min(Impact + Exploitability, 10) )
Base (scope changed)   = Roundup( min(1.08·(Impact + Exploitability), 10) )
```

The implementation's `_roundup` reproduces the FIRST reference behaviour exactly (rounding to 5 decimal places, then ceiling at 4), so scores match the canonical CVSS calculator (e.g. the vector above → **9.8**).

**Qualitative rating** (severity bands, `cvss.severity_rating`): `≥ 9.0` Critical, `≥ 7.0` High, `≥ 4.0` Medium, `> 0` Low, `0` None.

### 4.4 Effective CVSS per asset

An asset may carry several vulnerabilities. The model needs **one severity number** per device, computed as:

```
Cᵢ = max( score of v ), v ∈ Vᵢ          (0.0 when Vᵢ is empty)
```

**Rationale:** an attacker exploits the *weakest link*; the most severe exposed vulnerability dominates the exposure of the asset. The single numeric legacy field `cvss_type` on a device is treated as one implicit vulnerability (used only when no `vulnerabilities` list is present).

---

## 5. Stage 3+4+5 — From severity to intrinsic compromise probability

This is the heart of the methodology and is handled in `backend/probability.py`.

### 5.1 Why CVSS cannot be used directly as a probability

Two naive mappings are rejected:

1. **`P = CVSS/10` (linear)** is statistically indefensible: it implies a CVSS-10 vulnerability has compromise probability **1.0 (certainty)**, and a CVSS-0 has 0.0 (impossibility). Both violate the basic principle that no single vulnerability guarantees or precludes compromise (FIRST, 2019; Spring et al., 2021). The implementation keeps a `linear` mode **only for backward compatibility** and labels it "not recommended".
2. Arbitrary threshold tables would be unprincipled and non-monotonic in the wrong places.

### 5.2 The logistic calibration (default)

The default mapping is a **calibrated logistic (sigmoid) curve**:

```
P₀ = 1 / (1 + exp(−k·(Cᵢ − x₀)))
```

with defaults `k = 0.8`, `x₀ = 5.0` (both user-configurable via settings; `k > 0`, `x₀ ∈ [0,10]`).

| Quantity | Meaning |
| --- | --- |
| `Cᵢ` | effective CVSS Base Score in [0,10] (severity) |
| `k` | steepness — how strongly scores near the midpoint separate; higher `k` = sharper S-curve |
| `x₀` | midpoint — the CVSS value at which `P₀ = 0.5` exactly |
| `P₀` | the *unadjusted* compromise probability before contextual factors |

Anchor points with the defaults: `CVSS 0 → P₀ ≈ 0.018`, `CVSS 5 → P₀ = 0.500`, `CVSS 10 → P₀ ≈ 0.982`. Note that even the worst severity never reaches 1 and the best never reaches 0 — a deliberate property.

**Why logistic?** It is the canonical monotone mapping from an unbounded log-odds score to (0,1); it produces the `logit` scale that the contextual factors below operate on (making the whole model a logistic-regression-style composition); and its parameters give organisations a principled, auditable calibration knob. **What it does not mean:** `P₀` is not an empirically measured frequency; it is a *model-derived starting probability* whose curve parameters are expert defaults (see §22 classification).

### 5.3 Contextual factors — additive log-odds adjustment

Contextual factors enter the model on the **logit scale**, not by multiplying probabilities:

```
logit(P) = logit(P₀) + Σᵢ wᵢ · ln(Mᵢ)
P        = σ( logit(P) )        where σ(z) = 1/(1 + e⁻ᶻ)
```

- `Mᵢ` — a multiplier expressing the factor's directional effect (>1 increases probability, <1 decreases it).
- `wᵢ` — a user-configurable weight amplifying or dampening the factor; **`wᵢ = 0` disables the factor entirely**; a negative weight would invert it (validation requires weights ≥ 0).

This is the standard formulation of logistic regression and is the natural conjugate for Bayesian updating of binary probabilities (Gelman et al., 2020). **Why log-odds rather than `P × M`:** multiplicative adjustment of probabilities breaks the [0,1] bounds and has no principled semantics; additive adjustment of log-odds is monotone, bounded, and compositional.

**Device factors** (defaults from `settings.exposure_multipliers` / `patch_multipliers`, applied with weights `exposure_weight = 1.0`, `patch_weight = 1.0`):

| Factor | State | Multiplier `M` | Effect on probability |
| --- | --- | --- | --- |
| Exposure | `exposed = True` (default) | `1.3` | increase (internet-facing / network-reachable) |
| Exposure | `exposed = False` | `0.3` | strong decrease (air-gapped / isolated) |
| Patch state | `patched = True` | `0.9` | decrease (fully patched) |
| Patch state | `patched = False` (default) | `1.2` | increase (unpatched) |

Causal role: exposure governs *attack surface reachability*, patch state governs *vulnerability exploitability* — both are upstream causes of the compromise event, so both modify the intrinsic probability rather than the consequence.

Optionally, asset-level `protocol` / `trust` / `mitre` attributes are applied with weight `1.0` through the same mechanism (these are normally edge attributes, §6).

### 5.4 Human and physical assets

**Human** (phishing-susceptibility model):

```
P₀ = R_role · (1 − awareness)
```

- `R_role` — base phishing susceptibility by role: `operator 0.35`, `engineer 0.20`, `admin 0.15`, `guest 0.50`.
- `awareness ∈ [0,1]` — security awareness/education level; `awareness = 0.35` is the enrichment default; raising it lowers `P₀` linearly.

Then privilege is applied through the *same* log-odds mechanism with `M_privilege`: `standard 1.0`, `elevated 1.3`, `admin 1.5`.

**Physical** (expert override):

```
P₀ = p_base_override      (default 0.01, clamped to [0, 0.9995])
```

Physical compromise (valve tampering, pump sabotage) is typically assessed directly by domain experts rather than derived from CVSS — a physical process has no meaningful CVSS vector — hence a direct probability override.

### 5.5 Clamping — the soft caps

Every probability output passes through the same soft cap:

```
P ← max(1e-6, min(P_BASE_CAP, P))      with P_BASE_CAP = 0.9995
```

The lower cap keeps values above `0` so that conditioning on evidence can still *raise* a probability; the upper cap keeps values below `1` so that new mitigating evidence can still *lower* it (Bayesian updating must remain reversible — Pearl, 1988). The `logit` transform itself is additionally clamped to `[1e-12, 1−1e-12]` to avoid `ln(0)`.

### 5.6 The intrinsic compromise probability — definition

```
p_baseᵢ = P(Xᵢ = 1 | no parent evidence)  — the probability that asset i is
           compromised with no influence from any other node.
```

Pipeline inside one device asset:

```
Effective CVSS Cᵢ  →  P₀ = σ(k·(Cᵢ − x₀))  →  log-odds context adjustment
  →  soft caps  →  p_baseᵢ
```

**Semantic placement:** `p_base` is *not* the prior marginal of the node in the network (except for roots) and *not* a posterior. It is the **Noisy-OR leak probability** — the baseline chance of compromise that exists even when no parent is compromised (§8). The prior marginal `P(Xᵢ = 1)` is computed later by inference over the full network and can be much larger than `p_base` for a well-connected node (see the worked example, §19: `plc_1` has `p_base = 0.88271` but prior marginal ≈ `0.94924`).

---

## 6. Stage 6 — Propagation probability (edge weights)

### 6.1 Definition

For each directed edge `i → j` the framework computes a scalar **propagation weight** `wᵢⱼ ∈ (0, 0.99]` that parameterises *how strongly compromise of `i` pushes `j` toward compromise*.

### 6.2 Exact formula

`backend/graph_builder.edge_weight`:

```
wᵢⱼ = min( 0.99,
            w₀[rel_type] · m_firewall[firewalled]
              · m_protocol[protocol] · m_trust[trust] · m_mitre[mitre] )
```

Multipliers not matched by name fall back to `default`; the `0.99` ceiling keeps any single edge from *guaranteeing* propagation (again the reversibility principle).

**Base weight by relationship type** (`w₀`, configurable):

| rel_type | `w₀` |
| --- | --- |
| `programs / operates` | 0.80 |
| `controls` | 0.70 |
| `actuates` | 0.60 |
| `connects-to` | 0.50 |
| `monitors` | 0.20 |

**Firewall control** (reduce-only — validation forbids `firewalled` ever *increasing* risk):

| `firewalled` | `m_firewall` |
| --- | --- |
| `True` | 0.30 (≈70 % reduction, aligned with NIST SP 800-41 guidance) |
| `False` | 1.00 |

**Protocol multiplier** (`m_protocol`; protocols lacking native security get a mild increase, per NIST SP 800-82 Rev. 3):

| protocol | mult | protocol | mult |
| --- | --- | --- | --- |
| `http` | 1.25 | `dnp3` | 1.10 |
| `mqtt` | 1.20 | `s7comm` | 1.10 |
| `modbus` | 1.15 | `ethernet/ip` | 1.05 |
| | | `profinet` | 1.05 |
| | | `opc-ua` | 0.95 |
| `default` | 1.00 | | |

**Trust multiplier** (`m_trust`, derived from Purdue-model / IEC 62443 zone-trust concepts):

| trust | mult | | trust | mult |
| --- | --- | --- | --- | --- |
| `none` | 1.50 | | `medium` | 1.00 |
| `low` | 1.35 | | `default` | 1.00 |
| | | | `high` | 0.70 |

**MITRE ATT&CK for ICS technique multiplier** (`m_mitre`, based on observed frequency/impact in industrial incident reports — Dragos 2023, Mandiant 2023):

| technique | mult | | technique | mult |
| --- | --- | --- | --- | --- |
| `T0855` | 1.25 | | `T0831` | 1.10 |
| `T0886` | 1.20 | | `T0866` | 1.05 |
| `T0885` | 1.15 | | `default` | 1.00 |

### 6.3 Interpretation — and what it does NOT mean

`wᵢⱼ` is a **model parameter describing causal influence** in the Noisy-OR sense (§8): roughly, the *additional* chance that `j` becomes compromised if `i` is compromised and no other parent helps. It does **not** claim that an attacker has a literal `100·wᵢⱼ` percent chance of traversing that link in the real world. It encodes *relative* causal strength that is:

- **typed** (relationship semantics),
- **controlled** (firewall flag),
- **protocol/trust/technique-adjusted** (metadata),
- and **calibrated by the analyst** through settings if desired.

All default multiplier values are literature-grounded but **heuristic**; `backend/config.py` is explicit that organisations must calibrate them against their own incident data — they are not universal constants.

---

## 7. Stage 7 — Bayesian causal structure

### 7.1 Why a Bayesian network

A Bayesian network is a compact representation of a joint probability distribution over many binary variables:

```
BN = (G, Θ)
```

- `G` — the DAG from §3 (nodes = assets, edges = directed causal relationships, *after* validation).
- `Θ` — the set of Conditional Probability Tables (CPTs), one per node (§8).

It is used because it delivers exactly what the problem needs: exact, principled **evidence propagation**. Given any subset of observed states, the network computes the conditional distribution of every other node via Bayes' rule — no hand-rolled "risk scores get boosted if a neighbor is flagged" logic.

### 7.2 Mapping ICS → BN

| ICS concept | Bayesian concept |
| --- | --- |
| Asset | Node / random variable `Xᵢ` with states `{0, 1}` |
| Compromised / not compromised | States `1` / `0` |
| Relationship `i → j` | Directed edge `i → j` (parent → child) |
| Parents of a node | Direct causal influencers (neighbours that can compromise it) |
| Intrinsic probability `p_baseᵢ` | Leak parameter of node `i` |
| Propagation weight `wᵢⱼ` | Causal strength of parent `i` on child `j` |

The graph topology from the ICS file *is* the network structure — no Bayesian structure learning is performed. This is a deliberate choice: structure comes from engineering reality (who can reach whom), not from data mining.

### 7.3 Conditional independence

The defining property used by the inference engine: a node is conditionally independent of all non-descendants given its parents. The ICS reading: *whether the PLC is compromised depends on the HMI only through the HMI's direct causal influence on it; knowing the HMI's state fully screens off more distant nodes*. This property is what makes exact inference feasible and is exactly what Noisy-OR CPTs encode.

---

## 8. Stage 8 — CPT construction (Noisy-OR)

### 8.1 What a CPT is

For node `Xᵢ` with parents `P₁…Pₖ`, the CPT tabulates `P(Xᵢ = 1 | all 2ᵏ parent-state combinations)`. Each row is a conditional distribution over the child's two states (rows sum to 1), so the whole network defines one coherent joint distribution.

**Root nodes** (no parents) get a two-entry table:

```
P(Xᵢ = 1) = p_baseᵢ          P(Xᵢ = 0) = 1 − p_baseᵢ
```

**Non-root nodes** are filled by the **Noisy-OR** model (`backend/cpt_generator.noisy_or_cpt`):

```
P(Xᵢ = 1 | S) = 1 − (1 − p_baseᵢ) · Πⱼ∈S (1 − wⱼᵢ)
```

- `S` = the set of parents that are in state 1 in the current row,
- `p_baseᵢ` = the intrinsic (leak) probability of node `i`,
- `wⱼᵢ` = the propagation weight of edge `j → i`.

### 8.2 Intuition

Each *active* parent `j` contributes a factor `(1 − wⱼᵢ)`: the probability that parent `j` fails to compromise the child *by itself*. The child stays uncompromised only if **all** active parents fail *and* the baseline leak fails — hence the product. This yields:

- one parent active, weight `w`: `P = 1 − (1 − p_base)(1 − w) = p_base + w − p_base·w` — strictly larger than both `p_base` and `w` (the child can be compromised by the parent *or* by its own baseline);
- **the "explaining away" property is absent** (Noisy-OR is a *causal* aggregation — see §9);
- rows are automatically valid probability distributions (each in [0,1], complementary rows), so `pgmpy` model validation (`check_model()`) passes.

**Exact row example** (from the worked example, §19): for `plc_1` with one parent `hmi_ws` (`w = 0.575`, `p_base = 0.88271`):

```
P(plc = 1 | hmi = 0) = 0.88271              (leak only)
P(plc = 1 | hmi = 1) = 1 − (1−0.88271)(1−0.575) = 0.95015
```

---

## 9. Stage 9 — Noisy-OR assumptions and limitations

Noisy-OR rests on specific, *stated* assumptions. These are the scientific price of avoiding the exponential cost of fully general CPTs (which would need `2ᵏ` free parameters per node):

1. **Causal independence.** Each parent contributes to the child's compromise *independently*; there is no interaction or synergy between parents (e.g. "both must be compromised to matter" cannot be expressed).
2. **Single mechanism.** All causes act through the same mechanism — pushing the child from 0 to 1 — with no graded influence.
3. **No inhibition.** No parent can *prevent* compromise; the formula is monotone in every parent's state. (This is why the leak is never exactly 1 and weights never reach 1 — mitigation is expressed through the multipliers, not through CPT inhibition.)
4. **Binary states.** Every node is a two-state variable; there is no "compromised to degree d" state.

**Limitations:** the model cannot represent XOR-like relations, negative influences, or multi-valued states; interaction effects between parents are not captured. For the ICS ranking use-case these restrictions are acceptable and are documented in the report as explicit modelling assumptions rather than hidden defects.

---

## 10. Stage 10 — Evidence

### 10.1 Representation

Evidence is a map `{node: value}` with **hard evidence only**: `1` = "observed compromised", `0` = "observed safe". There is no soft/continuous evidence (no "70 % compromised"). The framework's semantic states — `Compromised` / `Safe` — map directly onto `1` / `0`.

### 10.2 Validation of evidence

`backend/inference._sanitize_evidence`:

- Values must be `0` or `1` (else error).
- Nodes must exist in the network (else error listing the valid nodes).

### 10.3 Impossible evidence

`backend/inference.check_evidence_feasibility` detects evidence that is *exactly impossible* under the model — `P(node = asserted state | other evidence) = 0` — before producing results, so the analyst never receives a misleading all-zero output. Because every state-1 probability is bounded below by the leak, the only realistic impossible case is **asserting `1` on a node with `p_base = 0` whose parents cannot raise it** (e.g. a physical asset with `p_base_override = 0`); each candidate is confirmed by an exact Variable Elimination query before being reported.

### 10.4 Prior vs evidence vs posterior

| Term | Definition | In this framework |
| --- | --- | --- |
| **Prior** | belief before observations | marginal `P(Xᵢ = 1)` from the parameterised network with `E = ∅` |
| **Evidence** | observations | hard `0/1` assertions on a subset of nodes |
| **Posterior** | belief after observations | `P(Xᵢ = 1 | E)` via Bayes' rule (exact inference, §11) |

An observed node's posterior is simply its asserted state (it is pinned; the network cannot override a hard observation).

---

## 11. Stage 11 — Bayesian inference (Variable Elimination)

### 11.1 The computation

`backend/inference.compute_posteriors_with_evidence` uses **exact inference by Variable Elimination** (`pgmpy.inference.VariableElimination`). For each unobserved node `Xᵢ` it computes:

```
P(Xᵢ = 1 | E) = Σ_{X∖{Xᵢ,E}} P(X₁,…,Xₙ, E) / P(E)
```

Bayes' theorem in its network form:

```
P(H | E) = P(E | H)·P(H) / P(E)
```

Variable Elimination works by exploiting the network's factorization — the joint distribution is the product of all CPTs — and summing out (eliminating) variables one at a time in a careful order, never materialising the full `2ⁿ` joint table. This is exact (no sampling error, no approximations).

### 11.2 What is eliminated

All variables that are neither queried nor observed are marginalised out. Eliminating a node removes it while *closing the edges of influence* between its neighbours (the operation combines and marginalises the factors that mention it). Because the network is small (tens to a few hundred nodes), exact VE is both feasible and preferable to approximate methods for a scientific-audit use-case.

### 11.3 Output

One scalar per node: `P(Xᵢ = 1 | E) ∈ [0, 1]`. The vector of posteriors is the primary output of the whole statistical engine — everything downstream (risk, ranking, attack paths) consumes it.

---

## 12. Stage 12 — Posterior compromise probability

### 12.1 Why posterior ≠ intrinsic

The intrinsic probability `p_baseᵢ` describes the asset *in isolation*. The posterior describes the asset *in its network, given evidence*. The difference is exactly the model's added value:

- A PLC with moderate `p_base` behind a highly-compromised HMI will show a **higher** posterior (evidence propagates along `hmi → plc`).
- An isolated server with high `p_base` may show a posterior **equal to** its prior when no evidence touches its neighbourhood (roots are pinned to their marginal).
- Evidence *mitigating* a parent lowers the child's posterior even if the child's own `p_base` is unchanged.

### 12.2 Quantity comparison table

| Quantity | Meaning | Computed before inference? | Influenced by evidence? | Bounded by |
| --- | --- | --- | --- | --- |
| CVSS `Cᵢ` | Vulnerability *severity* (0–10) | yes | no | 0–10 |
| Intrinsic probability `p_baseᵢ` | *Isolated* compromise probability (leak) | yes | no | [1e-6, 0.9995] |
| Propagation weight `wᵢⱼ` | Causal influence of `i` on `j` | yes | no | (0, 0.99] |
| Prior marginal `P(Xᵢ=1)` | Belief with no evidence (network-aware) | no | no | (0,1) |
| Posterior `P(Xᵢ=1|E)` | Belief given evidence | no | **yes** | (0,1) |
| Impact `Iᵢ` | Normalised consequence | no | indirectly (attributes only) | [0, 1.4·w_impact] |
| Risk index `Rᵢ` | Probability × impact | no | **indirectly** (via posterior) | [0, 1.4·w_impact] |

**Worked-example illustration** (§19): `plc_1` has `p_base = 0.88271`; with no evidence its marginal is `0.94924` (raised by its exposed parent); with evidence `hmi = 1` its posterior is `0.95015` (pinned-parent propagation). The posterior differs from the intrinsic probability in *both* cases — this is the Bayesian network at work.

---

## 13. Stage 13 — Impact / consequence

### 13.1 Definition

Impact is **not** the CVSS Impact Sub-Score and not a probability. It is a normalised consequence score derived from three factors (`backend/risk.build_risk_table`):

```
Iᵢ = (Sᵢ / 10) · σᵢ · w_impact
```

| Term | Meaning | Default / range |
| --- | --- | --- |
| `Sᵢ` | **Consequence severity** — analyst-supplied asset attribute, 0–10 (10 = catastrophic loss of availability/safety for the process) | user-provided; enrichment defaults: device 5.0, human 3.0, physical 4.0 |
| `σᵢ` | **Scope multiplier** — blast radius: `σ = 1 + (scope − 1)·0.1`, `scope ∈ [1,5] → σ ∈ [1.0, 1.4]`; `scope ≤ 0 → 0.9` (defensive) | `scope` user-provided, default 1 |
| `w_impact` | **Organisation-level impact weight** — risk-appetite / calibration knob | 1.0, configurable (≥ 0) |

Dividing `Sᵢ` by 10 normalises consequence to [0,1]; the scope multiplier then stretches it by blast radius. At defaults the maximum impact is `1.4` (severity 10, scope 5) — hence the risk-index ceiling in §14.

---

## 14. Stage 14 — Risk calculation

### 14.1 The risk index

```
Rᵢ = P(Xᵢ = 1 | E) × Iᵢ
```

The **risk index** is the product of a genuine probability (posterior) and a normalised consequence score. It is **not a probability** — it can exceed 1 — and it is **not** an expected monetary loss (no ALE, no currency). It is a bounded, interpretable, *ranking* quantity: with default settings `Rᵢ ∈ [0, 1.4]` (and up to `1.4·w_impact` when the impact weight is raised).

### 14.2 Why neither probability alone nor impact alone is risk

- **High probability ≠ highest risk:** an internet-exposed printer (`P ≈ 0.98`) with consequence severity 0 scores `R ≈ 0` and ranks below a moderately-likely (P = 0.5) safety PLC (severity 10 → `R = 0.7`).
- **High impact ≠ highest risk:** a critically important but unreachable pump (`P = 0.01`) scores `R = 0.014` despite severity 10.

The product formulation makes both dimensions necessary: the analyst's attention flows to assets that are *both* likely *and* consequential — exactly the decision-relevant set.

### 14.3 Interpretation caveats

- `Rᵢ` is a **model-derived indicator**, not a directly observed real-world loss frequency.
- Values ≥ 1.0 are possible and normal (probability up to 1 × impact up to 1.4); the risk *level* classification (§15) is unaffected by the 1.0 "apparent ceiling".

---

## 15. Stage 15 — Risk ranking, thresholds, aggregation

### 15.1 Ranking

Assets are sorted by `Rᵢ` **descending**; ranks are 1-based (`Rank 1` = highest risk). The rank is a pure ordering — it carries no magnitude information beyond the underlying risk index.

### 15.2 Thresholds and levels

Each risk index is classified into one of four qualitative levels with configurable thresholds (defaults):

```
Critical  if Rᵢ ≥ 0.75
High      if Rᵢ ≥ 0.50
Moderate  if Rᵢ ≥ 0.25
Low       if Rᵢ <  0.25
```

Validation enforces `critical > high > moderate`. These thresholds are **calibration placeholders, not a formal standard**: the implementation's own documentation notes that ISO 27005 and NIST SP 800-30 use qualitative likelihood/impact matrices, and that an organisation should tune thresholds to its risk appetite. The same values are the single source of truth for every surface that consumes them (backend classification, frontend dashboard and charts, PDF colouring), so nothing is hardcoded inconsistently.

### 15.3 Aggregate (network-level) metrics

`backend/risk.compute_aggregate_risk` reports:

| Metric | Definition | Why it is defensible |
| --- | --- | --- |
| `max_risk` | Worst-case single-asset risk index | The network's risk is the risk of its riskiest asset; **size-independent** |
| `mean_risk` | Arithmetic mean of risk indices | Context |
| `median_risk` | Median risk index | Robust summary |
| `level_counts` | Asset count per risk level | Distribution shape |
| `asset_count` | Number of assets | Denominator context |

### 15.4 Attack path scoring

`backend/attack_paths.py` finds directed paths through the Bayesian DAG from **entry points** (evidence-marked-compromised nodes, or DAG roots when no evidence marks any node) to **targets** (assets with `consequence_severity > 0`), following the causal direction (§3.1). Each path is scored:

```
path_prob   = min( P(Xᵢ = 1 | E) over nodes on the path )     [default "min"]
score       = path_prob × R_target
```

- The **minimum posterior along the path** is the "weakest link": if any node is unlikely to be compromised, the whole path is unlikely to be viable.
- Multiplying by the **target risk index** prioritises paths ending at high-value assets.
- An alternative `product` mode (`ATTACK_PATH_SCORING=product`) computes the probability that *every* node on the path is compromised, as a product of posteriors.
- Fallback (no posteriors supplied): geometric mean of edge weights.
- Pruning: edges with weight `< 0.05` are not traversed; maximum path depth 12 hops; paths are sorted by score descending.

The scoring uses **actual inferred posterior probabilities**, not raw edge weights — the same Bayesian engine that produced the risk register also ranks the attack paths.

---

## 16. Stage 16 — Sensitivity analysis (assumption auditing)

`backend/sensitivity.py` provides a deterministic **one-at-a-time** sensitivity analysis of the model's assumptions: run the pipeline at baseline, then re-run it with each perturbation and record deltas. The pre-defined perturbations cover the main assumption axes:

| Variation | Setting overridden |
| --- | --- |
| `logistic_k_high` / `logistic_k_low` | `k = 1.2` / `k = 0.4` |
| `logistic_x0_shifted_down` / `_up` | `x₀ = 4.0` / `x₀ = 6.0` |
| `propagation_weights_±25pct` | all Noisy-OR weights ×1.25 / ×0.75 |
| `exposure_effect_doubled` | exposure multiplier (exposed) = 2.0 |
| `patch_effect_stronger` | patch multiplier (patched) = 0.5 |

Reported metrics per variation: mean intrinsic probability, mean posterior, overall (max) risk, mean risk, top-asset risk, plus deltas versus baseline. The module **deliberately does not fabricate confidence intervals or significance**: deltas are deterministic output movements, and no empirical calibration is claimed (see §21–§23). Usage is CLI/module-level (`python -m backend.sensitivity --topology …`) — it is not exposed in the web UI.

---

## 17. Assumptions and scientific limitations

Every major model component rests on explicit assumptions. They are stated here so the methodology can be challenged where it deserves to be.

| Component | Assumptions | Practical consequence |
| --- | --- | --- |
| **CVSS v3.1** | Severity scores describe the *vulnerability* under standard assumptions; analyst-supplied vectors are correct and complete | Scores are inputs, never re-validated against an external feed |
| **Effective CVSS = max** | The worst vulnerability dominates an asset's exposure | An asset with one severe CVE is treated as fully exposed to that severity |
| **Logistic mapping** | Severity and compromise likelihood are monotonically related through a sigmoid; `k`, `x₀` chosen by default (`0.8`, `5.0`) | `P₀` is a model-derived starting probability, not a measured frequency; parameters are calibration placeholders |
| **Log-odds context factors** | Exposure and patch act multiplicatively on odds, independently, with fixed multipliers (`1.3/0.3`, `0.9/1.2`) | These multipliers are heuristic (literature-grounded) unless calibrated |
| **Propagation weights** | Link type, firewall, protocol, trust and MITRE technique combine multiplicatively; cap 0.99 | Weights are relative causal strengths, not real-world traversal probabilities |
| **Noisy-OR** | Causal independence of parents; single monotone mechanism; leak = `p_base` | No parent interactions, no inhibitory influences, no graded states |
| **Hard evidence only** | Observations are exact (0/1) | No soft evidence or measurement uncertainty in observations |
| **Exact VE inference** | Network structure (DAG) is correct and CPTs are valid | Inference is exact *given* the model; garbage-in/garbage-out applies to structure and parameters |
| **Risk index = P × I** | Consequence severity and scope are meaningful analyst inputs; risk is a product | Risk is a ranking indicator, not a monetary loss figure |
| **Thresholds** | 0.75/0.50/0.25 suit the organisation's risk appetite | Placeholder calibration; must be tuned, not treated as a standard |
| **Static model** | The network is a static snapshot; no time dynamics, no attack sequencing | Posterior is a single-snapshot belief |

**Overall caveat:** the framework produces *model-derived indicators* whose quality is bounded by the quality of its inputs and the validity of the assumptions above. Nothing in the pipeline fabricates empirical validity where none exists.

---

## 18. Empirical vs standardized vs derived vs calibrated vs heuristic vs user-provided

Scientific defensibility requires knowing the epistemic status of every quantity:

| Quantity | Status | Evidence basis |
| --- | --- | --- |
| CVSS v3.1 Base Score | **Standardized** | FIRST v3.1 specification equations (implemented verbatim) |
| Severity rating bands (9/7/4/0) | **Standardized** | FIRST qualitative bands |
| Effective CVSS per asset | **Derived** | max over analyst-supplied vulnerabilities |
| Logistic `P₀` | **Calibrated** | configurable curve (`k`, `x₀`); defaults are expert placeholders, *not* empirically fitted |
| Exposure/patch multipliers & weights | **Heuristic** (calibratable) | literature-grounded defaults in `config.py`; user-configurable |
| Human `R_role`, `M_privilege` | **Heuristic** | literature-grounded role table |
| Physical `p_base_override` | **User-provided** | analyst/expert direct assessment (default 0.01) |
| Propagation weights, firewall/protocol/trust/MITRE multipliers | **Heuristic** (calibratable) | NIST SP 800-41 / 800-82 Rev. 3, IEC 62443/Purdue, Dragos & Mandiant incident analyses — explicitly *defaults to calibrate* |
| CPTs | **Derived** | Noisy-OR formula from `p_base` + edge weights |
| Posteriors | **Derived** | exact Variable Elimination |
| Impact, risk index, aggregates, path scores | **Derived** | formulas above |
| Risk thresholds | **Heuristic** | calibration placeholders (0.75/0.50/0.25) |
| Evidence | **User-provided** | hard 0/1 observations |
| Vulnerability data | **User-provided** | analyst-supplied; `source` field is provenance only (no NVD fetch) |
| **Empirically observed quantities** | — | **none.** No real-world incident/frequency data is ingested anywhere in the pipeline |

The absence of empirical inputs is by design and is stated plainly: every probability is a model artefact derived from analyst inputs plus heuristic/calibrated parameters, and the system is explicitly documented as such.

---

## 19. Complete numerical flow — fully worked example

> **Illustrative example.** The numbers below were produced by executing the actual pipeline on the shown topology with default settings. They demonstrate the arithmetic, not empirical validation. Intermediate values are rounded for display, so hand-recomputation may differ from the pipeline-exact final values in the last decimals.

### 19.1 Topology

Three assets, two directed relationships:

| Asset | kind | Key attributes |
| --- | --- | --- |
| `hmi_ws` | device | vulnerability vector `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`, `exposed=true`, `patched=false`, `consequence_severity=8`, `scope=2` |
| `plc_1` | device | `cvss_type=8.8`, `exposed=false`, `patched=false`, `consequence_severity=9.5`, `scope=3` |
| `pump_1` | physical | `p_base_override=0.01`, `consequence_severity=10`, `scope=5` |

Edges: `hmi_ws → plc_1` (`connects-to`, not firewalled, `modbus`); `plc_1 → pump_1` (`actuates`, not firewalled, `profinet`).

### 19.2 Stage-by-stage numbers

**① CVSS.** `hmi_ws` vector → official Base Score **9.8** (rating Critical). `plc_1` effective CVSS = **8.8**.

**② Intrinsic probabilities** (`k=0.8, x₀=5.0`, weights `1.0`):

```
hmi_ws:  P₀ = σ(0.8·(9.8−5)) = σ(3.84) ≈ 0.9790
         logit = logit(0.9790) + 1.0·ln(1.3) [exposed] + 1.0·ln(1.2) [unpatched]
               ≈ 3.84 + 0.262 + 0.182 = 4.285
         p_base = σ(4.285) ≈ 0.98641                      → 0.986409
plc_1:   P₀ = σ(0.8·(8.8−5)) = σ(3.04) ≈ 0.9543
         logit = logit(0.9543) + 1.0·ln(0.3) [not exposed] + 1.0·ln(1.2) [unpatched]
               ≈ 3.04 − 1.204 + 0.182 = 2.018
         p_base = σ(2.018) ≈ 0.88271                      → 0.882710
pump_1:  p_base = p_base_override                          → 0.010000
```

**③ Propagation weights:**

```
w(hmi→plc) = min(0.99, 0.50·1.00·1.15·1.0·1.0)  = 0.575     (connects-to × modbus)
w(plc→pump) = min(0.99, 0.60·1.00·1.05·1.0·1.0) = 0.630     (actuates × profinet)
```

**④ CPTs (Noisy-OR):**

```
Root hmi_ws:            P(hmi=1) = 0.98641
plc_1 (parent hmi, w=0.575, p_base=0.88271):
   P(plc=1|hmi=0) = 0.88271
   P(plc=1|hmi=1) = 1 − (1−0.88271)(1−0.575)   = 0.95015
pump_1 (parent plc, w=0.630, p_base=0.01):
   P(pump=1|plc=0) = 0.01000
   P(pump=1|plc=1) = 1 − (1−0.01)(1−0.63)      = 0.63370
```

**⑤ Priors (no evidence, via VE):**

```
P(hmi=1)  = 0.98641        (root = p_base)
P(plc=1)  = 0.94924        (raised by the HMI: ≈ 0.95015·0.98641 + 0.88271·0.01359)
P(pump=1) = 0.60204        (raised strongly by the PLC path)
```

Note how the *intrinsic* probabilities (0.88271, 0.01) differ from the network *priors* (0.94924, 0.60204): the topology amplifies risk even before any evidence is entered.

**⑥ Evidence** `hmi_ws = 1` (observed compromised).

**⑦ Posteriors (exact VE):**

```
P(hmi=1|E)  = 1.00000   (pinned by hard evidence)
P(plc=1|E)  = 0.95015   (= the CPT row P(plc=1|hmi=1): only parent observed)
P(pump=1|E) = 0.63370·0.95015 + 0.01000·0.04985 = 0.60261
```

**⑧ Impact and risk** (impact weight 1.0; `σ = 1+(scope−1)·0.1`):

| Asset | P(posterior) | Severity | σ | Impact | **Risk** | Level |
| --- | --- | --- | --- | --- | --- | --- |
| `plc_1` | 0.95015 | 9.5 | 1.2 | 1.14000 | **1.08317** | Critical |
| `hmi_ws` | 1.00000 | 8.0 | 1.1 | 0.88000 | **0.88000** | Critical |
| `pump_1` | 0.60261 | 10.0 | 1.4 | 1.40000 | **0.84365** | Critical |

Observe: `pump_1` has the *highest* impact (1.4) and `hmi_ws` the *highest* probability (1.0), but `plc_1` ranks first because it balances both (0.95 × 1.14). Neither probability alone nor impact alone determines the rank — the product does.

**⑨ Aggregate:** `max_risk = 1.08317`, `mean_risk = 0.93561`, `median_risk = 0.88000`, `level_counts = {critical: 3, high: 0, moderate: 0, low: 0}`.

**⑩ Attack paths** (entry = `hmi_ws`):

```
hmi_ws → plc_1:          path_prob = min(1.00000, 0.95015) = 0.95015
                         score = 0.95015 × 1.08317 = 1.02918
hmi_ws → plc_1 → pump_1: path_prob = min(1.00000, 0.95015, 0.60261) = 0.60261
                         score = 0.60261 × 0.84365 = 0.50839
```

The two-hop path to the pump scores lower because its weakest link (`pump_1` posterior 0.60261) drags the whole path down — the weakest-link semantics in action.

---

## 20. Uncertainty

Where does uncertainty live, and what does the implementation do about it?

| Source of uncertainty | Handled by the framework as… | Mechanism |
| --- | --- | --- |
| Vulnerability severity | a point value per vulnerability | effective CVSS = max (no severity distribution) |
| Severity → probability | a point value | logistic curve with fixed `k`, `x₀` (no parameter distribution) |
| Contextual factors | point multipliers/weights | exposure/patch log-odds (no distributions) |
| Topology / connectivity | fixed DAG | structure is assumed correct after validation |
| Propagation weights | point values | multiplicative product, capped at 0.99 |
| CPT assumptions | point probabilities | Noisy-OR with fixed leak and weights |
| Evidence | hard, exact states | 0/1 only; no measurement noise model |
| Impact estimation | point values | severity/scope/weight product |
| **Model-parameter sensitivity** | **deterministic one-at-a-time deltas** | `backend/sensitivity.py` (§16) |

**The framework does not implement statistical uncertainty quantification** — no Monte Carlo, no credible intervals, no parameter distributions, no evidence uncertainty. What it does do:

1. Represents *epistemic uncertainty* about compromise **as probabilities** (the Bayesian formalism — the probability *is* the uncertainty representation).
2. Exposes the model's dependence on its assumptions through deterministic sensitivity deltas.
3. Guarantees exact (not approximate) inference, so the *only* uncertainty is model uncertainty, never inference error.

Claims of "confidence intervals" or "empirical calibration" are deliberately absent everywhere, including from the sensitivity module's own output notes.

---

## 21. Causality vs correlation

The directed edges of the Bayesian network represent **modelled causal influence**, not empirically established causation:

- Edge direction follows the engineering semantics of the topology (parent → child, cause → effect), so the network *encodes a causal hypothesis*: "compromise of `i` can cause compromise of `j`".
- The weights quantify the *strength* of that hypothesised influence under the Noisy-OR model.
- The topology itself contributes the structure; the analyst contributes the hypothesis; the inference engine merely propagates belief.

**Defensible reading:** the network computes what the model's causal assumptions *imply* about compromise given evidence — a coherent reasoning artefact. **Not defensible:** treating an edge as proof that a real-world causal attack path exists, or that the posterior is an observed frequency. The framework's own documentation consistently frames attack paths as "candidate paths" and risk as a "ranking metric".

---

## 22. The physical model and the probabilistic model

Two distinct models coexist:

```mermaid
flowchart LR
    A[Physical / logical ICS topology] --> B[Relationship extraction + normalization]
    B --> C[Probabilistic abstraction: weighted DAG]
    C --> D[Bayesian Network: DAG + Noisy-OR CPTs]
```

| Preserved in the abstraction | Abstracted away |
| --- | --- |
| Node identities and asset kinds | Exact network hardware details (ports, firmware versions) |
| Directionality of relationships (causal orientation) | The physical *mechanism* of influence — collapsed into one scalar weight `wᵢⱼ` |
| Severity, exposure, patch, zone, consequence attributes | Non-binary states — each asset reduced to a binary compromised/not variable |
| Consequence severity and scope (what a compromise *costs*) | Time dynamics — the network is a static snapshot |
| Evidence observations | Attack sequencing, defence-in-depth depth |

The abstraction is deliberate: it maps engineering data onto the smallest probability model that can still express lateral movement (edges), baseline susceptibility (leaks), evidence propagation (inference), and consequence (impact).

---

## 23. Master mathematical pipeline

```
Cᵢ  →  P₀ᵢ = σ(k·(Cᵢ − x₀))  →  logit(Pᵢ) = logit(P₀ᵢ) + Σ wᵢ·ln(Mᵢ)
    →  p_baseᵢ = clamp(Pᵢ, 1e-6, 0.9995)
    →  wᵢⱼ = min(0.99, w₀[type]·m_firewall·m_protocol·m_trust·m_mitre)
    →  P(Xᵢ=1|S) = 1 − (1−p_baseᵢ)·Π_{j∈S}(1−wⱼᵢ)
    →  BN = (G, Θ)
    →  P(Xᵢ=1|E) via Variable Elimination
    →  Iᵢ = (Sᵢ/10)·(1+(scope−1)·0.1)·w_impact
    →  Rᵢ = P(Xᵢ=1|E) · Iᵢ
    →  level(Rᵢ) via thresholds (0.75 / 0.50 / 0.25)
    →  Rank, max/mean/median, path scores = min(P over path) · R_target
```

Expanded, the complete chain of implemented equations:

```
1.  Cᵢ       = max over v∈Vᵢ of CVSSv3.1(v)                    [standardized]
2.  P₀ᵢ      = 1 / (1 + exp(−k·(Cᵢ − x₀)))                      [calibrated logistic]
3.  p_baseᵢ  = clamp( σ( logit(P₀ᵢ) + Σ wᵢ·ln(Mᵢ) ), 1e-6, 0.9995 )
4.  wᵢⱼ      = min( 0.99, w₀·m_firewall·m_protocol·m_trust·m_mitre )
5.  θᵢ(S)    = 1 − (1 − p_baseᵢ) · Π_{j∈S} (1 − wⱼᵢ)           [Noisy-OR CPT]
6.  P(Xᵢ=1|E) = VE query on BN(G, Θ) with hard evidence E
7.  Iᵢ       = (Sᵢ/10) · (1 + (scopeᵢ − 1)·0.1) · w_impact
8.  Rᵢ       = P(Xᵢ=1|E) · Iᵢ
9.  level    = Critical | High | Moderate | Low   via τ = 0.75 | 0.50 | 0.25
10. path     = min(P(n)=1|E over n∈path) · R_target            [or Π when ATTACK_PATH_SCORING=product]
```

---

## 24. Stage dependency table

| Stage | Input | Mathematical operation | Output | Used by |
| --- | --- | --- | --- | --- |
| Topology | raw ICS file | normalize, enrich, validate (DAG) | `G=(V,E)` + attributes | everything |
| CVSS | vulnerability vectors/scores | FIRST v3.1 equations | severity `Cᵢ` (0–10) | probability model |
| Severity→probability | `Cᵢ`, `k`, `x₀` | logistic `σ(k(C−x₀))` | base prob `P₀ᵢ` | intrinsic probability |
| Context | exposure, patch, human/physical attrs | additive log-odds `logit(P₀)+Σ w·ln(M)` + clamp | `p_baseᵢ` (leak) | CPT construction |
| Propagation | relationship type + controls + metadata | `min(0.99, w₀·m_firewall·m_protocol·m_trust·m_mitre)` | edge weight `wᵢⱼ` | CPT construction, attack paths |
| CPT | parents + `p_baseᵢ` + `wⱼᵢ` | Noisy-OR `1−(1−p_base)Π(1−w)` | CPT `θᵢ` | Bayesian network |
| Network | DAG + CPTs | pgmpy DiscreteBayesianNetwork | `BN=(G,Θ)` | inference |
| Evidence | hard 0/1 observations | feasibility check + sanitisation | `E` | inference |
| Inference | BN + evidence | exact Variable Elimination | posterior `P(Xᵢ=1|E)` | risk, attack paths |
| Impact | severity, scope, weight | `(S/10)·σ·w_impact` | impact `Iᵢ` | risk |
| Risk | posterior + impact | product `Rᵢ = P·I` | risk index | ranking, aggregation |
| Ranking | risk indices + thresholds | sort desc; threshold bands | Rank + level | dashboard, reports |
| Aggregation | risk table | max/mean/median/counts | network metrics | reports |
| Attack paths | posteriors + risk + DAG | weakest-link min × target risk | path scores | prioritisation |

---

## 25. Verification and reproducibility

- The mathematics above is enforced by **267 backend tests (pytest)**, of which **40 scientific-validation tests** recompute the key formulas *independently* (logistic mapping, log-odds adjustment, Noisy-OR CPT rows, inference by full joint-enumeration comparison, risk index) and check them against the implementation's outputs.
- Every assessment records a **settings snapshot** (`settings_used`) plus warnings for any non-default parameter, so two runs with the same topology but different settings visibly differ, and any result can be traced to the exact parameter set that produced it.
- The worked example in §19 was generated by executing the actual pipeline (not by hand arithmetic) and reproduces all downstream numbers exactly.

---

## 26. References cited by the implementation

- FIRST (2019). *CVSS v3.1 Specification & User Guide*. https://www.first.org/cvss/
- Pearl, J. (1988). *Probabilistic Reasoning in Intelligent Systems*. Morgan Kaufmann.
- Fenton, N. E., & Neil, M. (2012). *Risk Assessment and Decision Analysis with Bayesian Networks*. CRC Press.
- Gelman, A. et al. (2020). *Bayesian Data Analysis* (3rd ed.). Chapman & Hall/CRC.
- Spring, J. et al. (2021). *Practical Bayesian analysis of CVSS scores*. ACM CCS Workshop on Cyber-Physical Systems Security.
- NIST SP 800-41 (firewall risk reduction), NIST SP 800-82 Rev. 3 (ICS protocols), IEC 62443-3-3 / Purdue model (zone trust).
- Dragos (2023), Mandiant (2023) ICS incident analyses (MITRE ATT&CK for ICS technique frequencies).
- ISO/IEC 27005:2022; NIST SP 800-30 Rev. 1 (risk-assessment frameworks referenced for the threshold discussion).
