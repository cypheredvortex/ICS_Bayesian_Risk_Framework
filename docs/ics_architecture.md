# ICS Architecture Reference

This document describes the ICS/OT architecture the framework expects,
represents, and audits. It is written for the sample topologies shipped in
`ics_topologies/` (especially `chemical_processing_plant/`) and for analysts
authoring their own topologies.

> **Wording choice:** the sample architectures are **Purdue-inspired**, not
> "Purdue-compliant". They incorporate OT security zoning and segmentation
> principles consistent with **IEC 62443** and **NIST SP 800-82**. Purdue is a
> reference architecture, not a rigid universal physical topology; security
> zones are the primary security concept, and Purdue levels are used for
> architectural hierarchy.

---

## 1. Two orthogonal concepts: Purdue level and security zone

The framework deliberately keeps two concepts separate:

| Concept | Meaning | How the framework uses it |
| --- | --- | --- |
| **Purdue level** | Position in the hierarchical ICS architecture (Enterprise → control → field → process). | Architectural metadata on every asset (`purdue_level`: `0`…`5`, plus `3.5` for the industrial DMZ). Used for layout (zone bands), summaries, and the architecture audit. It **never alters the Bayesian mathematics directly**. |
| **Security zone** (`zone`) | An IEC 62443-style security boundary: assets with shared security requirements that communicate through controlled conduits. | Grouping/segmentation metadata, displayed in the UI and used by the architecture audit to detect segmentation violations. |
| **Conduit** (relationship) | A controlled communication path between zones. | A directed relationship with a type, a `firewalled` flag, and optional `protocol`/`trust`/`transport` metadata — the causal edges of the Bayesian model. |

When an asset does not declare an explicit `purdue_level`, the framework
derives a sensible default from its zone name
(`backend/topology.py::ZONE_PURDUE_DEFAULTS`). An explicit per-asset level
always wins.

## 2. Purdue-inspired levels

| Level | Name | Typical assets |
| ----- | ---- | -------------- |
| **L5** | Enterprise / External | Internet edge, cloud/partner connectivity (rarely represented as assets). |
| **L4** | Enterprise IT / Business Systems | ERP, domain controllers, corporate file/email servers, enterprise switches, corporate firewalls. |
| **L3.5** | Industrial DMZ (IDMZ) | Jump/bastion server, OT data broker, historian replica, patch/update repository, secure file-transfer service, remote-access gateway. **No control-plane assets.** |
| **L3** | Site Operations | Operator/HMI stations, engineering workstations, OT historian, site operations servers, OT management systems. |
| **L2** | Area Control / Supervisory Control | DCS controllers, control-system switches, area controllers, SIS logic solvers (in their own zone). |
| **L1** | Basic Control / Field | Field sensors, transmitters (temperature, pressure, level, flow), control valves, pumps, actuators, remote RTUs. |
| **L0** | Physical Process | Reactor, distillation column, storage tanks, heat exchangers, process pumps, pipelines. |

The framework models the causal chain **cyber asset → controller → field
actuator/sensor → physical process → consequence**, which is why Level 0
physical assets matter for a cyber-risk model even though they are not
directly network-reachable.

## 3. The Industrial DMZ (L3.5)

The IDMZ is the controlled boundary between Enterprise IT and OT. In the
sample architectures it hosts only broker/proxy/jump/transfer services:

- **Jump / bastion server** — the only interactive access path for
  enterprise-side administrators into the OT environment.
- **OT data broker / historian replica** — one-way or mediated data exchange
  from the OT historian to enterprise consumers.
- **Patch / update repository** — validated content staged for OT
  maintenance.
- **Secure file-transfer service** — controlled file exchange.

The IDMZ **never** contains DCS controllers, operator stations, engineering
workstations, or field instruments. The audit flags any control-plane asset
inside a DMZ-named zone as an **error**.

```
Enterprise IT (L4)
      │  Corporate firewall
      ▼
Industrial DMZ (L3.5)   ← jump server, data broker, patch repo
      │  OT firewall
      ▼
Site Operations (L3)    ← HMI, engineering, historian
      │
      ▼
Control (L2)            ← DCS controllers
      │
      ▼
Field (L1) → Process (L0)
```

## 4. SIS architecture

Safety Instrumented Systems are represented as a **separate, protected
safety zone** with its own causal chain:

```
SIS sensors (dedicated transmitters)
      │  monitors
      ▼
Safety PLC / logic solver
      │  controls
      ▼
Final elements (safety / ESD valves)
      ▼
Safe state (process consequence)
```

- The SIS is isolated from the basic process control system (BPCS/DCS): the
  sample topology gives the Safety PLC its own zone and only a controlled
  interface (if any) to the DCS.
- The audit checks that a declared SIS exposes a complete chain — dedicated
  safety sensors, a logic solver, and final elements — and warns
  (`SIS_CHAIN_INCOMPLETE`) if not.
- SIS assets reachable from enterprise/DMZ networks are an **error**
  (`SIS_EXPOSED_TO_ENTERPRISE`).

## 5. Remote / tank-farm architecture

Remote OT (e.g. a storage/tank-farm environment) is modelled as its own
zone connected through a controlled conduit. The physical transport is made
explicit on the relationship (`transport`: `Ethernet`, `Leased line + VPN`,
`Radio`, …) instead of pretending everything is ordinary Ethernet:

```
DCS controller (Control, L2)
      │  connects-to, firewalled, transport: Leased line + VPN
      ▼
Remote switch → Remote RTU (Remote, L1)
                    ├── controls → remote pump
                    └── controls → remote valve
```

## 6. Relationship semantics

Relationship types are semantically distinct and map onto the Noisy-OR
causal weight table:

| Relationship | Meaning | Weight |
| --- | --- | --- |
| `programs / operates` | Engineering/operator interaction with a controller | 0.80 |
| `controls` | Controller → actuator / final element | 0.70 |
| `actuates` | Actuator → physical process | 0.60 |
| `connects-to` | Generic logical connectivity (incl. zone-to-zone conduits) | 0.50 |
| `monitors` | Sensor → controller / controller → HMI | 0.20 |

A relationship is **not** equivalent to physical network adjacency: an
enterprise user → DCS controller direct control edge is flagged by the audit
(`ENTERPRISE_CONTROLS_FIELD`) and realistic topologies express that path as
*user → enterprise services → firewall → IDMZ jump → OT firewall →
engineering workstation → DCS controller*. Firewalls, jump servers and
brokers are first-class assets because they change both the causal structure
and the propagation parameters.

## 7. How the topology feeds the Bayesian model

```
Asset (id, kind, zone, purdue_level, CVSS, exposure, patch state, …)
   ↓  intrinsic compromise probability (calibrated from CVSS severity +
      context — CVSS stays a severity metric, never a probability)
Relationship (source, target, type, firewalled, protocol, trust, mitre, transport)
   ↓  edge weight w = base(type) × firewall × protocol × trust × mitre
   ↓  (bounded ≤ 0.99, explicit and calibratable)
Noisy-OR CPTs  →  Bayesian network  →  inference  →  posterior P(compromised)
   ↓
Risk = posterior × impact(consequence_severity, scope)
```

Architecture metadata (zones, Purdue levels) does **not** enter the
mathematics directly. Its role is:

1. **Causal structure** — the audit and the sample topologies keep the
   graph a faithful, defensible representation of the real architecture, so
   the dependencies the Bayesian network encodes are the dependencies that
   actually exist.
2. **Auditability** — an analyst can see at upload time whether the
   architecture is segmented properly before trusting the numbers.
3. **Communication** — the UI groups the graph into Purdue-ordered zone
   bands and shows zones/levels on every node and in summaries.

## 8. Architecture audit rules

`backend/topology.py::audit_ics_architecture` runs on every parsed topology
and returns advisory findings with three severities. Structural validation is
the upload gatekeeper; the audit is review guidance.

| Severity | Code | Finding |
| --- | --- | --- |
| error | `CONTROL_ASSET_IN_DMZ` | Control-plane asset (controller, HMI, operator/engineering station, SCADA) inside an industrial DMZ. |
| error | `SIS_EXPOSED_TO_ENTERPRISE` | SIS asset reachable from enterprise/DMZ networks. |
| error | `ENTERPRISE_CONTROLS_FIELD` | Enterprise-zone asset directly `controls`/`actuates` a field/process asset. |
| warning | `ENTERPRISE_TO_FIELD_LINK` | Direct enterprise → field/process link. |
| warning | `MISSING_SECURITY_BOUNDARY` | Enterprise/OT traffic exists but no firewall-class asset is present. |
| warning | `DMZ_BYPASS_LINK` | Enterprise-level → control-level link bypassing the IDMZ. |
| warning | `SIS_CHAIN_INCOMPLETE` | SIS zone lacks sensors → logic solver → final elements. |
| info | `BOUNDARY_LINK_NOT_FIREWALLED` | Enterprise/OT boundary links not flagged `firewalled`. |
| info | `PURDUE_LEVEL_MISSING` | Assets without an explicit level (zone default used). |

## 9. The chemical processing plant (reference example)

`ics_topologies/chemical_processing_plant/chemical_processing_plant.json` is
the canonical reference: a continuous chemical process (reactor, distillation,
storage) on a DCS with a separated SIS, an Enterprise → IDMZ → OT boundary,
and a remote tank farm. It is the topology used by the end-to-end tests
(`tests/test_ics_architecture.py`) and exercises every level L5→L0 plus the
IDMZ and SIS zones. The other plants (water treatment, manufacturing, oil &
gas pipeline, electrical substation) follow the same conventions.
