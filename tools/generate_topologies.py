"""
tools/generate_topologies.py - Derive every supported topology file format
from each folder's canonical JSON.

For every folder in ics_topologies/, this script reads the canonical
``<folder>.json`` and writes:

  * ``<folder>.yaml``        - YAML mirror of the canonical document
  * ``<folder>.csv``         - combined assets block + connections block
  * ``<folder>.xlsx``        - Assets and Connections worksheets
  * ``<folder>.graphml``     - node/edge graph with promoted attributes
  * ``<folder>.xml``         - generic Topology XML
  * ``<folder>.aml``         - AutomationML (ID-keyed InternalElements +
                               real Connection elements)
  * ``<folder>.vdx``         - Visio XML with annotated shapes
  * ``<folder>.vsdx``        - modern Visio package via the `vsdx` library
  * ``<folder>_assets.csv``  - split inventory artifact (assets only)
  * ``<folder>_connections.csv`` - split inventory artifact (links only)
  * ``<folder>_zones.csv``   - zone dictionary (supporting artifact)
  * ``<folder>_protocols.csv`` - protocol dictionary (supporting artifact)

The canonical JSON is the single source of truth; every output is generated
from it so all representations stay semantically consistent.

Run:  python tools/generate_topologies.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]
TOPOLOGIES = ROOT / "ics_topologies"

# Attributes that are part of the framework's normalized asset schema and are
# therefore written into every machine-readable representation.
ASSET_COLUMNS = [
    "id", "name", "kind", "type", "zone", "purdue_level", "description",
    "criticality", "vendor", "model", "ip", "cvss_type", "exposed",
    "patched", "consequence_severity", "role", "awareness", "privilege",
    "p_base_override",
]

CONNECTION_COLUMNS = [
    "source", "target", "type", "protocol", "direction", "trust",
    "firewalled", "transport",
]


def _text(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def load_canonical(folder: Path) -> dict:
    json_path = folder / f"{folder.name}.json"
    with json_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_yaml(canonical: dict, folder: Path) -> Path:
    import yaml

    path = folder / f"{folder.name}.yaml"
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(canonical, handle, sort_keys=False, default_flow_style=False, allow_unicode=True)
    return path


def write_combined_csv(canonical: dict, folder: Path) -> Path:
    path = folder / f"{folder.name}.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(ASSET_COLUMNS)
        for asset in canonical["assets"]:
            writer.writerow([_text(asset.get(col, "")) for col in ASSET_COLUMNS])
        writer.writerow([])
        writer.writerow(CONNECTION_COLUMNS)
        for conn in canonical["connections"]:
            writer.writerow([_text(conn.get(col, "")) for col in CONNECTION_COLUMNS])
    return path


def write_xlsx(canonical: dict, folder: Path) -> Path:
    import openpyxl

    path = folder / f"{folder.name}.xlsx"
    workbook = openpyxl.Workbook()
    assets_sheet = workbook.active
    assets_sheet.title = "Assets"
    assets_sheet.append(ASSET_COLUMNS)
    for asset in canonical["assets"]:
        assets_sheet.append([_text(asset.get(col, "")) for col in ASSET_COLUMNS])

    connections_sheet = workbook.create_sheet("Connections")
    connections_sheet.append(CONNECTION_COLUMNS)
    for conn in canonical["connections"]:
        connections_sheet.append([_text(conn.get(col, "")) for col in CONNECTION_COLUMNS])

    workbook.save(path)
    workbook.close()
    return path


def write_graphml(canonical: dict, folder: Path) -> Path:
    import networkx as nx

    path = folder / f"{folder.name}.graphml"
    graph = nx.DiGraph()
    for asset in canonical["assets"]:
        attrs = {col: asset.get(col) for col in ASSET_COLUMNS if asset.get(col) not in (None, "")}
        graph.add_node(asset["id"], **attrs)
    for conn in canonical["connections"]:
        attrs = {col: conn.get(col) for col in CONNECTION_COLUMNS if conn.get(col) not in (None, "")}
        graph.add_edge(conn["source"], conn["target"], **attrs)
    nx.write_graphml(graph, str(path))
    return path


def _xml_element(tag: str, children: list, attrs: dict | None = None) -> str:
    attr_str = "".join(f' {k}="{xml_escape(_text(v))}"' for k, v in (attrs or {}).items())
    body = "".join(children)
    return f"<{tag}{attr_str}>{body}</{tag}>"


def write_xml(canonical: dict, folder: Path) -> Path:
    path = folder / f"{folder.name}.xml"
    meta = canonical["metadata"]
    metadata = _xml_element("Metadata", [
        _xml_element("name", [xml_escape(meta.get("name", ""))]),
        _xml_element("description", [xml_escape(meta.get("description", ""))]),
        _xml_element("version", [xml_escape(meta.get("version", ""))]),
        _xml_element("created", [xml_escape(meta.get("created", ""))]),
    ])
    zones = _xml_element("Zones", [
        _xml_element("Zone", [
            _xml_element("id", [xml_escape(z["id"])]),
            _xml_element("name", [xml_escape(z.get("name", z["id"]))]),
            _xml_element("color", [xml_escape(z.get("color", ""))]),
            _xml_element("purdue_level", [xml_escape(z.get("purdue_level", ""))]),
        ])
        for z in canonical["zones"]
    ])
    assets = _xml_element("Assets", [
        _xml_element("Asset", [
            _xml_element(col, [xml_escape(_text(asset.get(col, "")))])
            for col in ASSET_COLUMNS
            if asset.get(col) not in (None, "")
        ])
        for asset in canonical["assets"]
    ])
    connections = _xml_element("Connections", [
        _xml_element("Connection", [
            _xml_element(col, [xml_escape(_text(conn.get(col, "")))])
            for col in CONNECTION_COLUMNS
            if conn.get(col) not in (None, "")
        ])
        for conn in canonical["connections"]
    ])
    protocols = _xml_element("Protocols", [
        _xml_element("Protocol", [
            _xml_element("id", [xml_escape(p["id"])]),
            _xml_element("name", [xml_escape(p.get("name", p["id"]))]),
            _xml_element("osi_layer", [xml_escape(p.get("osi_layer", ""))]),
        ])
        for p in canonical["protocols"]
    ])
    document = _xml_element(
        "Topology",
        [metadata, zones, assets, connections, protocols],
        attrs={"name": meta.get("name", folder.name)},
    )
    xml_decl = '<?xml version="1.0" encoding="utf-8"?>\n'
    path.write_text(xml_decl + document + "\n", encoding="utf-8")
    return path


def write_aml(canonical: dict, folder: Path) -> Path:
    path = folder / f"{folder.name}.aml"
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AutomationML xmlns="http://www.automationml.org/schema/aml">',
        "  <AdditionalInformation/>",
        f'  <InstanceHierarchy Name="{xml_escape(canonical["metadata"]["name"])}">',
    ]
    for asset in canonical["assets"]:
        lines.append(
            f'    <InternalElement Name="{xml_escape(asset["name"])}" ID="{xml_escape(asset["id"])}">'
        )
        for col in ASSET_COLUMNS:
            if col in ("id", "name"):
                continue
            if asset.get(col) not in (None, ""):
                lines.append(
                    f'      <Attribute Name="{xml_escape(col)}">{xml_escape(_text(asset[col]))}</Attribute>'
                )
        lines.append("    </InternalElement>")
    lines.append("  </InstanceHierarchy>")
    lines.append("  <Connections>")
    for conn in canonical["connections"]:
        lines.append("    <Connection>")
        lines.append(f"      <Source>{xml_escape(conn['source'])}</Source>")
        lines.append(f"      <Target>{xml_escape(conn['target'])}</Target>")
        lines.append(f"      <Type>{xml_escape(conn.get('type', 'connects-to'))}</Type>")
        lines.append(f"      <Protocol>{xml_escape(conn.get('protocol', ''))}</Protocol>")
        lines.append(f"      <Trust_level>{xml_escape(conn.get('trust', ''))}</Trust_level>")
        lines.append(f"      <Firewalled>{xml_escape(_text(conn.get('firewalled', False)))}</Firewalled>")
        lines.append(f"      <Transport>{xml_escape(conn.get('transport', ''))}</Transport>")
        lines.append("    </Connection>")
    lines.append("  </Connections>")
    lines.append("</AutomationML>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _annotation_value(value: object) -> str:
    """Sanitise a value for the Visio key=value tail.

    The backend parser splits the tail on ';' and on the first '=' of each
    chunk, so a ';' inside a value would silently corrupt the annotation.
    Values may contain commas and '=' safely; any ';' is replaced (none
    appear in the curated topologies, but this keeps the convention robust
    for hand-authored files).
    """
    return _text(value).replace(";", " - ")


def _asset_shape_tail(asset: dict) -> str:
    """Extended key=value tail appended to a Visio asset annotation.

    The positional annotation only round-trips the security attributes;
    these display/architectural fields (name, zone, type, description,
    Purdue level, vendor/model/IP) would otherwise be lost when a topology
    is loaded from .vdx/.vsdx.  Values may contain commas but not ';'
    (the backend parser splits the tail on ';'); see _annotation_value.
    """
    pairs = []
    for key, value in (
        ("name", asset.get("name")),
        ("zone", asset.get("zone")),
        ("type", asset.get("type")),
        ("desc", asset.get("description")),
        ("purdue", asset.get("purdue_level")),
        ("vendor", asset.get("vendor")),
        ("model", asset.get("model")),
        ("ip", asset.get("ip")),
    ):
        if value not in (None, ""):
            pairs.append(f"{key}={_annotation_value(value)}")
    return ";" + ";".join(pairs) if pairs else ""


def _asset_shape_text(asset: dict) -> str:
    kind = asset.get("kind", "device")
    if kind == "human":
        base = f"asset,{asset['id']},human,{asset.get('role', 'operator')},{asset.get('awareness', 0.35)},{asset.get('privilege', 'standard')},{asset.get('consequence_severity', 3.0)}"
    elif kind == "physical":
        base = f"asset,{asset['id']},physical,{asset.get('p_base_override', 0.01)},{asset.get('consequence_severity', 4.0)}"
    else:
        base = f"asset,{asset['id']},device,{asset.get('cvss_type', 5.0)},{_text(asset.get('exposed', True))},{_text(asset.get('patched', False))},{asset.get('consequence_severity', 5.0)}"
    return base + _asset_shape_tail(asset)


def _connection_shape_text(conn: dict) -> str:
    base = (
        f"relationship,{conn['source']},{conn['target']},{conn.get('type', 'connects-to')},"
        f"{_text(conn.get('firewalled', False))},{conn.get('protocol', '')},{conn.get('trust', '')},"
    )
    # Transport (e.g. "Leased line + VPN", "Radio") is conduit metadata the
    # framework preserves; carry it in the same key=value tail the parser
    # reads, so remote links stay explicit in every format.
    transport = conn.get("transport")
    if transport not in (None, ""):
        base += f";transport={_annotation_value(transport)}"
    return base


def _zone_band_layout(canonical: dict) -> dict[str, tuple[float, float]]:
    """Place assets in horizontal zone bands: first zone on top.

    Returns a dict mapping asset id -> (x, y) in diagram units.
    """
    positions: dict[str, tuple[float, float]] = {}
    zone_order = [z["id"] for z in canonical["zones"]]
    by_zone: dict[str, list[dict]] = {z: [] for z in zone_order}
    for asset in canonical["assets"]:
        by_zone.setdefault(asset.get("zone", zone_order[0] if zone_order else ""), []).append(asset)

    band_height = 170.0
    max_per_row = 9
    y = band_height
    for zone in zone_order:
        members = by_zone.get(zone, [])
        if not members:
            continue
        rows = [members[i : i + max_per_row] for i in range(0, len(members), max_per_row)]
        for row_index, row in enumerate(rows):
            spacing = 210.0
            x_start = 120.0
            for index, asset in enumerate(row):
                positions[asset["id"]] = (x_start + index * spacing, y + row_index * 160.0)
        y += band_height * len(rows)
    return positions


def write_vdx(canonical: dict, folder: Path) -> Path:
    path = folder / f"{folder.name}.vdx"
    positions = _zone_band_layout(canonical)
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<VisioDocument xmlns="http://schemas.microsoft.com/visio/2003/core">',
        "  <DocumentProperties>",
        f"    <Title>{xml_escape(canonical['metadata']['name'])}</Title>",
        "    <Creator>ICS Topology Generator</Creator>",
        f"    <Description>{xml_escape(canonical['metadata'].get('description', ''))}</Description>",
        "  </DocumentProperties>",
        "  <Pages>",
        f'    <Page ID="0" Name="{xml_escape(canonical["metadata"]["name"])}" Width="3000" Height="1600">',
        "      <Shapes>",
    ]
    shape_id = 1
    for asset in canonical["assets"]:
        x, y = positions.get(asset["id"], (100.0, 100.0))
        lines.extend(
            [
                f'        <Shape ID="{shape_id}" Type="Shape" NameU="{xml_escape(asset["id"])}">',
                f"          <X>{x}</X>",
                f"          <Y>{y}</Y>",
                "          <Width>150</Width>",
                "          <Height>60</Height>",
                "          <Text>",
                f"            {xml_escape(_asset_shape_text(asset))}",
                "          </Text>",
                "        </Shape>",
            ]
        )
        shape_id += 1
    for conn in canonical["connections"]:
        lines.extend(
            [
                f'        <Shape ID="{shape_id}" Type="Shape" NameU="conn_{xml_escape(conn["source"])}_{xml_escape(conn["target"])}">',
                "          <X>0</X>",
                "          <Y>0</Y>",
                "          <Width>0</Width>",
                "          <Height>0</Height>",
                "          <Text>",
                f"            {xml_escape(_connection_shape_text(conn))}",
                "          </Text>",
                "        </Shape>",
            ]
        )
        shape_id += 1
    lines.extend(["      </Shapes>", "    </Page>", "  </Pages>", "</VisioDocument>"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_vsdx(canonical: dict, folder: Path) -> Path:
    """Write a modern Visio .vsdx package.

    The .vsdx format is a ZIP of XML parts.  The package layout below mirrors
    ``tests/validation_files/topology.vsdx`` (the fixture the framework's
    parser is validated against): each shape carries a ``Text`` element with
    the documented ``asset,<id>,<kind>,...`` / ``relationship,...``
    annotation convention, which the import pipeline reads.
    """
    import zipfile

    path = folder / f"{folder.name}.vsdx"
    if path.exists():
        path.unlink()

    shape_xml = []
    for asset in canonical["assets"]:
        shape_xml.append(
            f"<Shape ID='{xml_escape(asset['id'])}'><Text>{xml_escape(_asset_shape_text(asset))}</Text></Shape>"
        )
    for conn in canonical["connections"]:
        shape_xml.append(
            f"<Shape ID='conn_{xml_escape(conn['source'])}_{xml_escape(conn['target'])}'>"
            f"<Text>{xml_escape(_connection_shape_text(conn))}</Text></Shape>"
        )

    page_name = canonical["metadata"]["name"]
    page1 = (
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<PageContents xmlns='http://schemas.microsoft.com/office/visio/2012/main'>"
        f"<Shapes>{''.join(shape_xml)}</Shapes></PageContents>"
    )
    parts = {
        "[Content_Types].xml": (
            "<?xml version='1.0' encoding='UTF-8'?>"
            "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'>"
            "<Default Extension='rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/>"
            "<Default Extension='xml' ContentType='application/xml'/>"
            "<Override PartName='/docProps/app.xml' ContentType='application/vnd.openxmlformats-officedocument.extended-properties+xml'/>"
            "<Override PartName='/visio/document.xml' ContentType='application/vnd.ms-visio.document.main+xml'/>"
            "<Override PartName='/visio/_rels/document.xml.rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/>"
            "<Override PartName='/visio/pages/pages.xml' ContentType='application/vnd.ms-visio.pages+xml'/>"
            "<Override PartName='/visio/pages/_rels/pages.xml.rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/>"
            "<Override PartName='/visio/pages/page1.xml' ContentType='application/vnd.ms-visio.page+xml'/>"
            "</Types>"
        ),
        "docProps/app.xml": (
            "<?xml version='1.0' encoding='UTF-8'?>"
            "<Properties xmlns='http://schemas.openxmlformats.org/officeDocument/2006/extended-properties' "
            "xmlns:vt='http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes'>"
            "<HeadingPairs><vt:vector size='2'><vt:variant><vt:lpstr>Pages</vt:lpstr></vt:variant>"
            "<vt:variant><vt:i4>1</vt:i4></vt:variant></vt:vector></HeadingPairs>"
            "<TitlesOfParts><vt:vector size='1'><vt:lpstr>Page-1</vt:lpstr></vt:vector></TitlesOfParts>"
            "</Properties>"
        ),
        "visio/document.xml": (
            "<?xml version='1.0' encoding='UTF-8'?>"
            "<Document xmlns='http://schemas.microsoft.com/office/visio/2012/main'/>"
        ),
        "visio/_rels/document.xml.rels": (
            "<?xml version='1.0' encoding='UTF-8'?>"
            "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'/>"
        ),
        "visio/pages/pages.xml": (
            "<?xml version='1.0' encoding='UTF-8'?>"
            "<Pages xmlns='http://schemas.microsoft.com/office/visio/2012/main'>"
            f"<Page ID='1' Name='{xml_escape(page_name)}' NameU='{xml_escape(page_name)}'>"
            "<Rel r:id='rId1' xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'/>"
            "</Page></Pages>"
        ),
        "visio/pages/_rels/pages.xml.rels": (
            "<?xml version='1.0' encoding='UTF-8'?>"
            "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>"
            "<Relationship Id='rId1' Type='http://schemas.microsoft.com/visio/2010/relationships/page' Target='page1.xml'/>"
            "</Relationships>"
        ),
        "visio/pages/page1.xml": page1,
    }
    with zipfile.ZipFile(str(path), "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in parts.items():
            archive.writestr(name, content)
    return path


def write_split_csvs(canonical: dict, folder: Path) -> None:
    assets_path = folder / f"{folder.name}_assets.csv"
    with assets_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(ASSET_COLUMNS)
        for asset in canonical["assets"]:
            writer.writerow([_text(asset.get(col, "")) for col in ASSET_COLUMNS])

    connections_path = folder / f"{folder.name}_connections.csv"
    with connections_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(CONNECTION_COLUMNS)
        for conn in canonical["connections"]:
            writer.writerow([_text(conn.get(col, "")) for col in CONNECTION_COLUMNS])

    zones_path = folder / f"{folder.name}_zones.csv"
    with zones_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "name", "color", "purdue_level"])
        for zone in canonical["zones"]:
            writer.writerow([
                zone["id"],
                zone.get("name", zone["id"]),
                zone.get("color", ""),
                zone.get("purdue_level", ""),
            ])

    protocols_path = folder / f"{folder.name}_protocols.csv"
    with protocols_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "name", "osi_layer"])
        for proto in canonical["protocols"]:
            writer.writerow([proto["id"], proto.get("name", proto["id"]), proto.get("osi_layer", "")])


def generate_folder(folder: Path) -> list[Path]:
    canonical = load_canonical(folder)
    outputs = [
        write_yaml(canonical, folder),
        write_combined_csv(canonical, folder),
        write_xlsx(canonical, folder),
        write_graphml(canonical, folder),
        write_xml(canonical, folder),
        write_aml(canonical, folder),
        write_vdx(canonical, folder),
    ]
    try:
        outputs.append(write_vsdx(canonical, folder))
    except Exception as exc:  # pragma: no cover
        print(f"  [WARN] vsdx generation failed for {folder.name}: {exc}")
    write_split_csvs(canonical, folder)
    return outputs


def main() -> None:
    folders = sorted(p for p in TOPOLOGIES.iterdir() if p.is_dir())
    for folder in folders:
        print(f"Generating {folder.name} ...")
        outputs = generate_folder(folder)
        for path in outputs:
            print(f"  {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
