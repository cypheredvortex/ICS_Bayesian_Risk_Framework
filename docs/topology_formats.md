# Topology Upload Specification

This document is the **authoritative reference for uploading ICS topology files**
to the ICS Bayesian Risk Assessment Framework. Every claim below was verified
by running the files through the real application pipeline
(`import → normalize → validate → Bayesian network → risk calculation`) and by
cross-checking the parsed result against the canonical representation.

> **Rule: implementation → tested behaviour → documentation.** If a format is
> listed as *Supported*, it has been tested end-to-end on the sample
> topologies in `ics_topologies/`.

---

## 1. Format support summary

| Format          | Extension  | Supported | Notes                                                                 |
| --------------- | ---------- | --------- | --------------------------------------------------------------------- |
| JSON            | `.json`    | **Yes**   | Recommended; canonical format.                                        |
| YAML            | `.yaml`, `.yml` | **Yes** | Same schema as JSON.                                                  |
| CSV             | `.csv`     | **Yes**   | Single self-describing file (asset + relationship sections).          |
| XLSX            | `.xlsx`    | **Yes**   | Each sheet parsed like CSV; supports multiple sections per sheet.     |
| GraphML         | `.graphml` | **Yes**   | Nodes → assets, edges → relationships.                                |
| XML             | `.xml`     | **Yes**   | Generic container XML (`<assets>`/`<connections>` …).                 |
| AutomationML    | `.aml`     | **Yes**   | IEC 62714 `InternalElement` / `Connection` structures.                |
| Visio XML       | `.vdx`     | **Yes**   | Visio 2003–2010 XML; shape text must follow the marker convention.    |
| Visio Open XML  | `.vsdx`    | **Yes**   | Modern Visio package; same marker convention (see §7).                |
| Visio binary    | `.vsd`     | **No**     | Legacy binary container; conversion guidance is returned instead.     |

All formats converge on the **same canonical topology model** (see §3), so the
same semantics can be expressed in any supported format.

---

## 2. What the pipeline does with your file

```
File
 ├── format detection (by extension)
 ├── parser            → raw assets + relationships
 ├── normalization     → canonical model (ids, kinds, security attributes)
 ├── graph validation  → DAG check, reference check, type check
 ├── topology analysis → zones, kinds, relationship mix, field coverage,
 │                        Purdue levels, architecture audit (advisory)
 ├── Bayesian network  → CPT generation, inference
 └── risk calculation  → per-asset risk scores
```

A file may be *syntactically valid* (valid JSON/XML) yet still be rejected by
the framework if it does not describe a valid **topology** (e.g. duplicate
ids, connections to non-existent assets, cycles, unknown relationship types).

---

## 3. Canonical topology model

Every supported format is converted to the same internal representation:

```
Topology
 ├── assets          : id → { id, name, kind, type, description, zone,
 │                          purdue_level, vendor, model, ip, cvss_type,
 │                          exposed, patched, consequence_severity, … }
 ├── relationships   : (source, target, type, firewalled, metadata)
 ├── zones           : id → { id, name }          (optional, display aid)
 └── protocols       : id → { id, name }          (optional, display aid)
```

### 3.1 Assets — required

| Field | Type | Notes |
| ----- | ---- | ----- |
| `id`  | string | Unique identifier. Also accepted via `name`, `label`, `node`, `asset_id`, … |

Every asset **must** have a unique `id`. If `kind` is absent it is inferred
from the asset name (`device` / `human` / `physical`).

### 3.2 Assets — supported attributes

| Field | Applies to | Range | Notes |
| ----- | ---------- | ----- | ----- |
| `name` | all | text | Human-readable label (defaults to `id`). |
| `kind` | all | `device` / `human` / `physical` | Inferred from name if omitted. |
| `type` | all | text | Declared asset type (e.g. `PLC`, `Firewall`, `DCS Controller`). Display metadata: preserved through normalization, shown in the asset review and used for the "what is this asset?" explanation. A `type`/`category` that is a kind alias (`device`/`human`/`physical`) is consumed by kind inference and not duplicated. |
| `description` | all | text | Plain-language description of what the asset is/does. Display metadata, preserved through normalization; shown in the Node Details panel (authoritative over the type-dictionary fallback). |
| `zone` | all | text | Any zone name; used for reporting. |
| `purdue_level` | all | `0`…`5`, plus `3.5` | Purdue Enterprise Reference Architecture level. `3.5` is the industrial DMZ. Optional — when absent a default is derived from the zone. Architectural metadata only; it does not alter the Bayesian mathematics directly. |
| `vendor`, `model` | all | text | Optional. |
| `ip` | device | IPv4 text | Optional. |
| `cvss_type` | device | 0.0 – 10.0 | CVSS v3.1 base score shortcut. |
| `exposed` | device | bool | Internet-facing exposure. |
| `patched` | bool | bool | Patch status. |
| `consequence_severity` | all | 0.0 – 10.0 | Business impact of compromise. |
| `vulnerabilities` | device | list | List of CVE/vulnerability records. |
| `role` | human | text | `operator`, `engineer`, `admin`, `guest`… |
| `awareness` | human | 0.0 – 1.0 | Phishing awareness. |
| `privilege` | human | text | `standard`, `elevated`, `admin`. |
| `p_base_override` | physical | 0.0 – 1.0 | Direct base compromise probability. |

Numeric and boolean attributes are validated **strictly**: out-of-range values
or `"not-a-number"` strings cause the upload to be rejected with an actionable
error.

### 3.3 Relationships — required

| Field | Type | Notes |
| ----- | ---- | ----- |
| `source` | string | Must reference an existing asset id. |
| `target` | string | Must reference an existing asset id. |
| `type`   | string | One of the supported relationship types (below). |
| `firewalled` | bool | Optional; reduces propagation. |
| `protocol`, `trust`, `mitre_technique` | text | Optional; influence risk multipliers. |
| `transport` | text | Optional; physical transport of the link (e.g. `Ethernet`, `Leased line + VPN`, `Radio`). Display/conduit metadata that makes remote links explicit instead of pretending everything is ordinary Ethernet. |

Supported relationship types (default `connects-to`):

| Type | Propagation weight |
| ---- | ------------------ |
| `controls` | 0.70 |
| `monitors` | 0.20 |
| `actuates` | 0.60 |
| `connects-to` | 0.50 |
| `programs / operates` | 0.80 |

Unknown relationship types are **rejected**, not silently rewritten.

### 3.4 What makes a topology valid

1. **Every asset has a unique id.**
2. **Every relationship references existing assets** (source and target).
3. **Relationship types are supported.**
4. **The graph is acyclic** (Bayesian networks require a DAG).
5. **There is at least one relationship** if more than one asset exists.
6. Self-loops and duplicate edges are removed with an explicit warning.

Disconnected sub-graphs are allowed (they become independent submodels).

---

## 4. Per-format details

### 4.1 JSON — `.json`

**Supported: Yes** — the recommended, canonical format.

Structure:

```json
{
  "metadata": { "name": "...", "description": "...", "version": "1.0" },
  "zones": [ { "id": "Control", "name": "Control Network" } ],
  "assets": [
    {
      "id": "PLC-001",
      "name": "Intake PLC",
      "type": "PLC",
      "kind": "device",
      "zone": "Control",
      "vendor": "Allen-Bradley",
      "model": "ControlLogix 5580",
      "cvss_type": 8.1,
      "exposed": false,
      "patched": false,
      "consequence_severity": 9.0
    }
  ],
  "connections": [
    { "source": "PLC-001", "target": "SENSOR-001",
      "type": "monitors", "protocol": "Modbus TCP", "trust": "low" }
  ],
  "protocols": [ { "id": "modbustcp", "name": "Modbus TCP" } ]
}
```

Flexible alternatives are accepted: assets can be a **list** or a **dict keyed
by id**, and the asset container may be named `assets`, `nodes`, `devices`,
`components`, `items`, `elements` or `system_units`. Relationships may be under
`relationships`, `edges`, `links`, `connections`, `connections_list` or
`paths`. A bare list of assets (no container) also works.

**Limitations:** JSON must decode as an object or list; a top-level string or
number is rejected.

### 4.2 YAML — `.yaml`, `.yml`

**Supported: Yes.** The schema is identical to JSON (see §4.1). YAML comments
are allowed and ignored.

**Limitations:** must be parseable by a safe YAML parser; aliases/anchors are
resolved, arbitrary object instantiation is disabled.

### 4.3 CSV — `.csv`

**Supported: Yes.** One file, with **section groups** separated by blank
lines. Each section has a header row; the header decides whether the section
is parsed as assets or relationships.

```csv
id,name,type,kind,zone,cvss_type,exposed,patched,consequence_severity
PLC-001,Intake PLC,PLC,device,Control,8.1,false,false,9.0
SENSOR-001,Flow Sensor,Sensor,physical,Field,,,,,4.0

source,target,type,protocol,trust,firewalled
PLC-001,SENSOR-001,monitors,Modbus TCP,low,false
```

Recognised asset headers: `id`, `asset`, `name`, `label`, `asset_id`,
`assetname`, `node`, `node_id` (plus `type`, `kind`, `zone`, `vendor`,
`model`, `ip`, `cvss_type`, `exposed`, `patched`, `consequence_severity`,
`role`, `awareness`, `privilege`, `p_base_override`, …).

Recognised relationship headers: `source`/`from` and `target`/`to` (plus
`type`, `firewalled`, `protocol`, `trust`, `trust_level`, `mitre`, …).

**Limitations:**
- An **assets-only** CSV (no relationship section) is rejected: the framework
  requires a relationship, exactly like a partial spreadsheet export.
- A header-less CSV with two columns is parsed as relationships.
- The split inventory files shipped alongside the sample topologies
  (`*_assets.csv`, `*_connections.csv`, `*_zones.csv`, `*_protocols.csv`) are
  **supporting artifacts** documenting the asset register / connection matrix;
  they are not standalone topology files.

### 4.4 XLSX — `.xlsx`

**Supported: Yes.** Every worksheet is parsed like a CSV section (blank-row
separated groups, header-driven). Assets and relationships may live in the
same sheet or in different sheets.

**Limitations:** the workbook must contain at least one asset or relationship
group; the uncompressed expansion is capped (200 MB default) to block archive
bombs.

### 4.5 GraphML — `.graphml`

**Supported: Yes.**

```xml
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <graph id="topology" edgedefault="directed">
    <node id="PLC-001">
      <data key="label">Intake PLC</data>
      <data key="kind">device</data>
      <data key="zone">Control</data>
    </node>
    <edge source="PLC-001" target="SENSOR-001">
      <data key="type">monitors</data>
    </edge>
  </graph>
</graphml>
```

Node `id` becomes the asset id; `label`/`name` becomes the display name;
`kind`, `type`, `vendor`, `model`, `zone`, `ip` and the security attributes
(`cvss_type`, `exposed`, `patched`, `consequence_severity`, …) are promoted
when present on the node. Edge attributes `type`, `firewalled`, `protocol`,
`trust`/`trust_level`, `mitre_technique` are read from the edge data.

**Limitations:** networkx must be able to parse the document; unrecognised
node attributes are preserved in `metadata` (not dropped).

### 4.6 Generic XML — `.xml`

**Supported: Yes.** Container-oriented documents are recognised: assets under
`<assets>/<nodes>/<devices>/<components>/<items>/<system_units>/<internalelements>`
and relationships under
`<relationships>/<edges>/<links>/<connections>/<paths>`, with individual
`<asset>/<node>/<device>/<relationship>/<edge>/<connection>` elements.
Attributes and child elements become asset fields; `id` defaults to `name`
when absent.

```xml
<topology>
  <assets>
    <asset id="PLC-001" name="Intake PLC" kind="device" zone="Control"
           cvss_type="8.1" exposed="false" patched="false" />
  </assets>
  <connections>
    <connection source="PLC-001" target="SENSOR-001" type="monitors" />
  </connections>
</topology>
```

**Limitations:** at least one asset must be parseable; the document must be
well-formed XML. Documents whose root is `AdditionalMarkupLanguage` or
`AutomationML` are routed to the AML parser instead.

### 4.7 AutomationML — `.aml`

**Supported: Yes.** IEC 62714 (`CAEX`) documents:

- `<InternalElement Name="..." ID="...">` → one asset. **`ID` is preferred as
  the asset id; if absent, `Name` is used** (so ID-less legacy exports still
  parse).
- Child `<Attribute Name="...">text</Attribute>` elements become asset fields
  (lower-cased attribute names, e.g. `Kind`, `Zone`, `Cvss_type`).
- `<Connection>` / `<InternalLink>` elements with `<Source>` and `<Target>`
  children become relationships; `<Role>`/`<Type>` sets the relationship
  type, `<Protocol>` and `<Trust_level>` add metadata.

```xml
<AutomationML xmlns="http://www.automationml.org/schema/aml">
  <InstanceHierarchy Name="Water Treatment Plant">
    <InternalElement Name="Intake PLC" ID="PLC-001">
      <Attribute Name="kind">device</Attribute>
      <Attribute Name="type">PLC</Attribute>
      <Attribute Name="zone">Control</Attribute>
      <Attribute Name="cvss_type">8.1</Attribute>
      <Attribute Name="exposed">false</Attribute>
      <Attribute Name="patched">false</Attribute>
      <Attribute Name="consequence_severity">9.0</Attribute>
    </InternalElement>
    <InternalElement Name="Flow Sensor" ID="SENSOR-001">
      <Attribute Name="kind">physical</Attribute>
      <Attribute Name="type">Sensor</Attribute>
      <Attribute Name="zone">Field</Attribute>
      <Attribute Name="p_base_override">0.01</Attribute>
      <Attribute Name="consequence_severity">4.0</Attribute>
    </InternalElement>
  </InstanceHierarchy>
  <Connections>
    <Connection>
      <Source>PLC-001</Source>
      <Target>SENSOR-001</Target>
      <Type>monitors</Type>
      <Protocol>Modbus TCP</Protocol>
      <Trust_level>low</Trust_level>
    </Connection>
  </Connections>
</AutomationML>
```

**Limitations:** attribute values must be **direct text** between the opening
and closing `<Attribute>` tags (as shown above). A nested `<Attribute …><Value>…</Value></Attribute>`
form (common in some CAEX exports) is **not** read by the parser — only the
attribute's immediate text is captured — so such attributes are silently
ignored. Connection definitions placed **only in XML comments** are also
ignored (comments are not data). A document with assets but no parseable
connections will be rejected for lacking relationships.

---

## 5. Common reasons an upload is rejected

| Symptom | Cause |
| ------- | ----- |
| `Unsupported topology format` | Wrong or unknown extension (incl. `.vsd`). |
| `Invalid JSON` / `Invalid YAML` / `Invalid XML` | Syntax error in the file. |
| `no assets found` | Asset container missing or empty. |
| `asset '…' was skipped` | Asset record is not an object / has no usable id. |
| `Duplicate asset id` | Two assets share the same id (later one wins with a warning — check ids). |
| `references unknown source/target asset` | A connection points at an id that does not exist. |
| `unknown relationship type '…'` | Typo in `type`; use one of the supported types. |
| `topology contains cycles` | The graph has a loop; Bayesian networks require a DAG. |
| `topology contains assets but no relationships` | Assets present, no connections. |
| `'cvss_type' must be a number/in range` | Numeric attribute malformed or out of range. |
| `'exposed' must be a boolean` | Boolean attribute is not true/false/0/1/yes/no. |
| `CSV … could not detect assets or relationships` | Headers don't match recognised vocabulary. |
| `Excel topology file is empty` | No asset/relationship group found in any sheet. |
| `No asset shapes found in .vsdx/.vdx` | Visio shapes lack the marker text / properties (§7). |
| Archive bomb rejection | Zip-based upload expands beyond the configured limit. |

---

## 6. Validating your topology before upload

In addition to structural validation, the backend runs an **advisory ICS
architecture audit** on every parsed topology and returns the findings with
the upload summary. It never rejects a file — structural validation is the
gatekeeper — but it flags configurations that are not defensible against
Purdue-inspired / IEC 62443 / NIST SP 800-82 practice, e.g.:

| Severity | Example finding |
| -------- | --------------- |
| error | Control-plane asset (DCS controller, HMI, operator/engineering station) placed inside an industrial DMZ. |
| error | SIS asset reachable from enterprise/DMZ networks. |
| error | Enterprise-zone asset directly controlling/actuating a field or process asset. |
| warning | No firewall-class asset mediating the Enterprise/OT boundary. |
| warning | Direct Enterprise → control-level link bypassing the DMZ. |
| info | Boundary links not flagged `firewalled`, or assets without an explicit `purdue_level` (a zone default is used). |

See `docs/ics_architecture.md` for the full rule set and the architecture
reference.

The sample topologies in `ics_topologies/` are the reference datasets. A
convenience audit script drives **every file** through the real import
pipeline and reports import status, full-pipeline status and cross-format
consistency (identical asset ids and edges vs. the canonical JSON):

```bash
python tools/audit_topologies.py
```

The canonical JSON per folder is the single source of truth; the other
formats are generated from it (see `tools/generate_topologies.py`).

---

## 7. Microsoft Visio support — engineering decision

**Status: VSDX and VDX are both supported, with documented limitations.**

After testing the parser against real files, Visio support was kept in the
framework for two reasons:

1. **The parser works.** `.vdx` is plain XML and is parsed directly; `.vsdx`
   is parsed via the `vsdx` library with a raw-XML fallback scanner. Both are
   exercised end-to-end by the sample files and by the test suite.
2. **Generated files round-trip.** `tools/generate_topologies.py` produces
   `.vdx`/`.vsdx` files from the canonical JSON, and the audit confirms the
   imported result matches the canonical topology.

**However, both formats are treated as *experimental, marker-based* formats.**
Because there is no Microsoft Visio available to author files, the framework
cannot make arbitrary Visio documents work. The parser relies on a **shape
text convention** — each shape's text must carry machine-readable markers:

```    asset,<id>,<kind>,<cvss_type|role|p_base_override>,…[;key=value…]
    relationship,<source>,<target>,<type>,<firewalled>,<protocol>,<trust>,<mitre>[;transport=…]

The positional fields are compact (kind + security-relevant fields). An
optional ``;``-separated ``key=value`` tail carries the remaining canonical
attributes so the Visio representations preserve **the same attribute
coverage as every other format** (zone, declared type, description, name,
Purdue level, vendor/model/IP and link transport):
```

Examples:

```
asset,PLC-001,device,8.1,false,false,9.0;name=Intake PLC;zone=Control;type=PLC;desc=Intake process controller;purdue=2
asset,SENSOR-001,physical,0.01,4.0;name=Flow Sensor;zone=Field;type=Sensor;purdue=1
asset,OPERATOR-001,human,operator,0.4,standard,4.0;name=Control Room Operator;zone=Operations
relationship,PLC-001,SENSOR-001,monitors,false,Modbus TCP,low,T0855
relationship,PLC-001,RTU-001,connects-to,true,DNP3,low,;transport=Leased line + VPN
```

Fields after `kind` are interpreted per kind (device → `cvss_type, exposed,
patched, consequence_severity`; human → `role, awareness, privilege,
consequence_severity`; physical → `p_base_override, consequence_severity`).
The `;`-tail is parsed first, so description values may safely contain
commas and `=` (each chunk is split on its *first* `=`); only `;` inside a
value must be avoided (the generator replaces it with ` - ` defensively).
When both the positional fields and the tail carry a value, the tail wins. **Backward compatibility:** legacy files that
omit the tail (and very old samples that put a zone name in the security
position, ``asset,<id>,<kind>,<zone>``) still parse — a non-numeric third
field is treated as the zone. Shapes whose text is a plain asset name are
skipped with a warning.

**Why not legacy `.vsd`?** The binary Visio format cannot be parsed without a
Visio installation or a reverse-engineered reader; uploading a `.vsd` returns
conversion guidance (Save As `.vsdx`, LibreOffice convert, or export to
JSON/CSV/GraphML) instead of a misleading parse error.

**Practical recommendation for end users:** upload **JSON, YAML, CSV, XLSX,
GraphML, XML or AML** for reliability; use `.vdx`/`.vsdx` only for files
authored with the marker convention above. If you cannot add markers to your
Visio shapes, export the diagram to GraphML/JSON/CSV from Visio and upload
that instead.

---

## 8. Supported pipeline entry points

- **API:** `POST /api/topology` (upload) — binary content + filename.
- **CLI:** `python main.py --topology <file>` (or `-t`).
- **Library:** `backend.assets.load_topology(path_or_bytes)`.

All entry points share the same parsers, normalizers and validation described
in this document.
