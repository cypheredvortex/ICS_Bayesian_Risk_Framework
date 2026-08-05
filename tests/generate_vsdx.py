"""
Generate a sample .vsdx topology file for testing the ICS Risk Assessment Framework.
"""

import os
import vsdx

def create_topology_vsdx(filename="example_topology.vsdx"):
    # Remove existing file if present to avoid conflicts
    if os.path.exists(filename):
        os.remove(filename)

    # Create a new Visio document (this creates a new file)
    doc = vsdx.VisioFile(filename)

    # Add a page
    page = doc.add_page("Topology")

    # Define assets (id, kind, cvss_type, exposed, patched, consequence_severity)
    assets = [
        ("CorpNet", "device", 5.0, True, True, 0.0),
        ("Firewall", "device", 4.5, False, True, 0.0),
        ("PLC", "device", 7.5, True, False, 0.8),
        ("HMI", "human", 0.0, False, False, 0.3),
        ("EngStation", "human", 0.0, False, False, 0.2),
        ("Sensor", "physical", 0.0, False, False, 0.0),
    ]

    # Positions for shapes
    positions = {
        "CorpNet": (50, 150),
        "Firewall": (250, 150),
        "PLC": (450, 100),
        "HMI": (450, 200),
        "EngStation": (450, 300),
        "Sensor": (650, 150),
    }

    # Add shapes for assets
    for asset_id, kind, cvss, exposed, patched, severity in assets:
        x, y = positions.get(asset_id, (100, 100))
        shape = page.add_shape(asset_id)
        shape.x = x
        shape.y = y
        shape.width = 120
        shape.height = 60

        if kind == "device":
            shape.text = f"asset,{asset_id},{kind},{cvss},{str(exposed).lower()},{str(patched).lower()},{severity}"
        elif kind == "human":
            if asset_id == "HMI":
                role, awareness, privilege = "operator", 0.5, "standard"
            else:
                role, awareness, privilege = "engineer", 0.6, "admin"
            shape.text = f"asset,{asset_id},{kind},{role},{awareness},{privilege},{severity}"
        elif kind == "physical":
            shape.text = f"asset,{asset_id},{kind},0.0,{severity}"

        if kind == "device":
            shape.fill_color = "rgb(56,189,248)"
        elif kind == "human":
            shape.fill_color = "rgb(167,139,250)"
        else:
            shape.fill_color = "rgb(245,158,11)"

    # Define relationships
    relationships = [
        ("CorpNet", "Firewall", "connects-to", False, "", "", ""),
        ("Firewall", "PLC", "connects-to", True, "modbus", "", ""),
        ("Firewall", "HMI", "connects-to", True, "", "high", ""),
        ("Firewall", "EngStation", "connects-to", True, "", "medium", ""),
        ("PLC", "Sensor", "actuates", False, "", "", ""),
    ]

    # Add connector label shapes
    for src, tgt, rel_type, firewalled, protocol, trust, mitre in relationships:
        connector_label = f"relationship,{src},{tgt},{rel_type},{str(firewalled).lower()},{protocol},{trust},{mitre}"
        src_x, src_y = positions.get(src, (0, 0))
        tgt_x, tgt_y = positions.get(tgt, (0, 0))
        mid_x = (src_x + tgt_x) / 2
        mid_y = (src_y + tgt_y) / 2
        label_shape = page.add_shape(f"conn_{src}_{tgt}")
        label_shape.x = mid_x - 60
        label_shape.y = mid_y - 20
        label_shape.width = 120
        label_shape.height = 40
        label_shape.text = connector_label
        label_shape.fill_color = "rgb(255,255,255)"

    # Save the document (the filename is already known from initialization)
    doc.save()
    print(f"✅ Generated {filename} successfully.")
    print(f"   Assets: {len(assets)}")
    print(f"   Relationships: {len(relationships)}")

if __name__ == "__main__":
    create_topology_vsdx()