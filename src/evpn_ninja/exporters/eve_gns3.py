"""EVE-NG and GNS3 export functionality.

Generates lab topology files for EVE-NG and GNS3 network simulators.
"""

import json
import uuid
from typing import Any


# EVE-NG node templates for different platforms
EVE_TEMPLATES = {
    "eos": "veos",
    "arista": "veos",
    "nxos": "nxosv9k",
    "cisco_nxos": "nxosv9k",
    "iosxr": "xrv9k",
    "iosxe": "csr1000v",
    "junos": "vmx",
    "juniper": "vmx",
    "srlinux": "srlinux",
    "nokia": "sros",
    "cumulus": "cumulus",
    "vyos": "vyos",
    "linux": "linux",
}

# GNS3 node templates
GNS3_TEMPLATES = {
    "eos": "Arista vEOS",
    "arista": "Arista vEOS",
    "nxos": "Cisco NX-OSv 9000",
    "cisco_nxos": "Cisco NX-OSv 9000",
    "iosxr": "Cisco IOS XRv 9000",
    "iosxe": "Cisco CSR1000v",
    "junos": "Juniper vMX",
    "juniper": "Juniper vMX",
    "cumulus": "Cumulus VX",
    "vyos": "VyOS",
    "linux": "Alpine Linux",
}


def export_eve_ng_topology(
    spines: list[dict[str, Any]],
    leaves: list[dict[str, Any]],
    lab_name: str = "VXLAN_Fabric",
    platform: str = "eos",
    include_hosts: bool = False,
) -> str:
    """
    Generate EVE-NG lab topology (unl file format).

    EVE-NG uses XML-based .unl files for lab definitions.

    Args:
        spines: List of spine switch dicts
        leaves: List of leaf switch dicts
        lab_name: Name of the lab
        platform: Target platform
        include_hosts: Whether to add test hosts

    Returns:
        EVE-NG lab XML as string
    """
    template = EVE_TEMPLATES.get(platform, platform)

    # Calculate grid layout
    total_spines = len(spines)
    total_leaves = len(leaves)
    total_hosts = len(leaves) if include_hosts else 0

    # Start X/Y positions
    spine_y = 100
    leaf_y = 300
    host_y = 500
    start_x = 100
    x_spacing = 200

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<lab name="{lab_name}" id="{uuid.uuid4()}" version="1">',
        '  <topology>',
    ]

    node_id = 1
    node_ids = {}  # Map node name to ID

    # Add spine nodes
    for i, spine in enumerate(spines):
        name = spine.get("name", f"spine-{i + 1}")
        x = start_x + (i * x_spacing) + ((total_leaves - total_spines) * x_spacing // 2)
        loopback = spine.get("loopback", spine.get("ip", f"10.0.0.{i + 1}"))

        lines.extend([
            f'    <node id="{node_id}" name="{name}" type="qemu" template="{template}"',
            f'          left="{x}" top="{spine_y}" console="telnet" delay="0">',
            f'      <interface id="0" name="Mgmt" type="ethernet"/>',
        ])

        # Add interfaces for leaf connections
        for j in range(total_leaves):
            lines.append(f'      <interface id="{j + 1}" name="Eth{j + 1}" type="ethernet"/>')

        lines.extend([
            '    </node>',
        ])

        node_ids[name] = node_id
        node_id += 1

    # Add leaf nodes
    for i, leaf in enumerate(leaves):
        name = leaf.get("name", f"leaf-{i + 1}")
        x = start_x + (i * x_spacing)
        loopback = leaf.get("loopback", leaf.get("ip", f"10.0.0.{total_spines + i + 1}"))

        lines.extend([
            f'    <node id="{node_id}" name="{name}" type="qemu" template="{template}"',
            f'          left="{x}" top="{leaf_y}" console="telnet" delay="0">',
            f'      <interface id="0" name="Mgmt" type="ethernet"/>',
        ])

        # Add interfaces for spine connections
        for j in range(total_spines):
            lines.append(f'      <interface id="{j + 1}" name="Eth{j + 1}" type="ethernet"/>')

        # Add interface for host if needed
        if include_hosts:
            lines.append(f'      <interface id="{total_spines + 1}" name="Eth{total_spines + 1}" type="ethernet"/>')

        lines.extend([
            '    </node>',
        ])

        node_ids[name] = node_id
        node_id += 1

    # Add host nodes
    if include_hosts:
        for i, leaf in enumerate(leaves):
            host_name = f"host-{i + 1}"
            x = start_x + (i * x_spacing)

            lines.extend([
                f'    <node id="{node_id}" name="{host_name}" type="qemu" template="linux"',
                f'          left="{x}" top="{host_y}" console="telnet" delay="0">',
                '      <interface id="0" name="eth0" type="ethernet"/>',
                '    </node>',
            ])

            node_ids[host_name] = node_id
            node_id += 1

    lines.append('  </topology>')

    # Add networks (connections)
    lines.append('  <networks>')

    network_id = 1

    # Spine-Leaf connections
    for i, spine in enumerate(spines):
        spine_name = spine.get("name", f"spine-{i + 1}")
        spine_id = node_ids[spine_name]

        for j, leaf in enumerate(leaves):
            leaf_name = leaf.get("name", f"leaf-{j + 1}")
            leaf_id = node_ids[leaf_name]

            lines.extend([
                f'    <network id="{network_id}" name="p2p_{spine_name}_{leaf_name}" type="bridge">',
                f'      <member node="{spine_id}" interface="{j + 1}"/>',
                f'      <member node="{leaf_id}" interface="{i + 1}"/>',
                '    </network>',
            ])
            network_id += 1

    # Host connections
    if include_hosts:
        for i, leaf in enumerate(leaves):
            leaf_name = leaf.get("name", f"leaf-{i + 1}")
            leaf_id = node_ids[leaf_name]
            host_name = f"host-{i + 1}"
            host_id = node_ids[host_name]

            lines.extend([
                f'    <network id="{network_id}" name="host_{leaf_name}" type="bridge">',
                f'      <member node="{leaf_id}" interface="{total_spines + 1}"/>',
                f'      <member node="{host_id}" interface="0"/>',
                '    </network>',
            ])
            network_id += 1

    lines.extend([
        '  </networks>',
        '</lab>',
    ])

    return '\n'.join(lines)


def export_gns3_topology(
    spines: list[dict[str, Any]],
    leaves: list[dict[str, Any]],
    lab_name: str = "VXLAN_Fabric",
    platform: str = "eos",
    include_hosts: bool = False,
) -> str:
    """
    Generate GNS3 project topology (gns3 file format).

    GNS3 uses JSON-based .gns3 files for project definitions.

    Args:
        spines: List of spine switch dicts
        leaves: List of leaf switch dicts
        lab_name: Name of the lab
        platform: Target platform
        include_hosts: Whether to add test hosts

    Returns:
        GNS3 project JSON as string
    """
    template = GNS3_TEMPLATES.get(platform, platform)

    # Calculate grid layout
    total_spines = len(spines)
    total_leaves = len(leaves)

    spine_y = -200
    leaf_y = 0
    host_y = 200
    start_x = -400
    x_spacing = 200

    project = {
        "auto_close": True,
        "auto_open": False,
        "auto_start": False,
        "name": lab_name,
        "project_id": str(uuid.uuid4()),
        "scene_height": 1000,
        "scene_width": 2000,
        "topology": {
            "computes": [],
            "drawings": [],
            "links": [],
            "nodes": [],
        },
        "type": "topology",
        "version": "2.2.0",
    }

    nodes = project["topology"]["nodes"]
    links = project["topology"]["links"]
    node_ids = {}

    # Add spine nodes
    for i, spine in enumerate(spines):
        name = spine.get("name", f"spine-{i + 1}")
        x = start_x + (i * x_spacing) + ((total_leaves - total_spines) * x_spacing // 2)
        node_id = str(uuid.uuid4())

        node = {
            "compute_id": "local",
            "console": 5000 + i,
            "console_type": "telnet",
            "name": name,
            "node_id": node_id,
            "node_type": "qemu",
            "symbol": ":/symbols/router.svg",
            "template": template,
            "x": x,
            "y": spine_y,
            "z": 0,
            "properties": {},
            "label": {
                "rotation": 0,
                "style": "font-family: TypeWriter;font-size: 10.0;fill: #000000;",
                "text": name,
                "x": -20,
                "y": -25,
            },
            "ports": [],
        }

        # Add ports
        for j in range(total_leaves + 1):  # +1 for management
            node["ports"].append({
                "adapter_number": j,
                "port_number": 0,
                "name": f"Ethernet{j}",
            })

        nodes.append(node)
        node_ids[name] = node_id

    # Add leaf nodes
    for i, leaf in enumerate(leaves):
        name = leaf.get("name", f"leaf-{i + 1}")
        x = start_x + (i * x_spacing)
        node_id = str(uuid.uuid4())

        node = {
            "compute_id": "local",
            "console": 5100 + i,
            "console_type": "telnet",
            "name": name,
            "node_id": node_id,
            "node_type": "qemu",
            "symbol": ":/symbols/router.svg",
            "template": template,
            "x": x,
            "y": leaf_y,
            "z": 0,
            "properties": {},
            "label": {
                "rotation": 0,
                "style": "font-family: TypeWriter;font-size: 10.0;fill: #000000;",
                "text": name,
                "x": -20,
                "y": -25,
            },
            "ports": [],
        }

        # Add ports
        port_count = total_spines + 2  # spines + mgmt + host
        for j in range(port_count):
            node["ports"].append({
                "adapter_number": j,
                "port_number": 0,
                "name": f"Ethernet{j}",
            })

        nodes.append(node)
        node_ids[name] = node_id

    # Add host nodes
    if include_hosts:
        for i, leaf in enumerate(leaves):
            host_name = f"host-{i + 1}"
            x = start_x + (i * x_spacing)
            node_id = str(uuid.uuid4())

            node = {
                "compute_id": "local",
                "console": 5200 + i,
                "console_type": "telnet",
                "name": host_name,
                "node_id": node_id,
                "node_type": "qemu",
                "symbol": ":/symbols/computer.svg",
                "template": "Alpine Linux",
                "x": x,
                "y": host_y,
                "z": 0,
                "properties": {},
                "label": {
                    "rotation": 0,
                    "style": "font-family: TypeWriter;font-size: 10.0;fill: #000000;",
                    "text": host_name,
                    "x": -20,
                    "y": -25,
                },
                "ports": [{
                    "adapter_number": 0,
                    "port_number": 0,
                    "name": "eth0",
                }],
            }

            nodes.append(node)
            node_ids[host_name] = node_id

    # Add links - Spine to Leaf connections
    for i, spine in enumerate(spines):
        spine_name = spine.get("name", f"spine-{i + 1}")
        spine_id = node_ids[spine_name]

        for j, leaf in enumerate(leaves):
            leaf_name = leaf.get("name", f"leaf-{j + 1}")
            leaf_id = node_ids[leaf_name]

            link = {
                "link_id": str(uuid.uuid4()),
                "nodes": [
                    {
                        "adapter_number": j + 1,  # Skip management port
                        "node_id": spine_id,
                        "port_number": 0,
                    },
                    {
                        "adapter_number": i + 1,  # Skip management port
                        "node_id": leaf_id,
                        "port_number": 0,
                    },
                ],
            }
            links.append(link)

    # Add host links
    if include_hosts:
        for i, leaf in enumerate(leaves):
            leaf_name = leaf.get("name", f"leaf-{i + 1}")
            leaf_id = node_ids[leaf_name]
            host_name = f"host-{i + 1}"
            host_id = node_ids[host_name]

            link = {
                "link_id": str(uuid.uuid4()),
                "nodes": [
                    {
                        "adapter_number": total_spines + 1,  # Port after spine connections
                        "node_id": leaf_id,
                        "port_number": 0,
                    },
                    {
                        "adapter_number": 0,
                        "node_id": host_id,
                        "port_number": 0,
                    },
                ],
            }
            links.append(link)

    return json.dumps(project, indent=2)


def generate_eve_ng_startup_scripts(
    spines: list[dict[str, Any]],
    leaves: list[dict[str, Any]],
    platform: str = "eos",
    bgp_as: int = 65000,
) -> dict[str, str]:
    """
    Generate startup configuration scripts for EVE-NG nodes.

    Args:
        spines: List of spine switch dicts
        leaves: List of leaf switch dicts
        platform: Target platform
        bgp_as: BGP AS number

    Returns:
        Dictionary mapping node name to startup config
    """
    configs = {}

    # For now, just return placeholder configs
    # In a real implementation, these would be full configs
    for i, spine in enumerate(spines):
        name = spine.get("name", f"spine-{i + 1}")
        loopback = spine.get("loopback", spine.get("ip", f"10.0.0.{i + 1}"))

        if platform in ("eos", "arista"):
            configs[name] = f"""! {name} startup config
hostname {name}
interface Loopback0
   ip address {loopback}/32
!
"""
        elif platform in ("nxos", "cisco_nxos"):
            configs[name] = f"""! {name} startup config
hostname {name}
interface loopback0
  ip address {loopback}/32
!
"""

    for i, leaf in enumerate(leaves):
        name = leaf.get("name", f"leaf-{i + 1}")
        loopback = leaf.get("loopback", leaf.get("ip", f"10.0.0.{len(spines) + i + 1}"))
        vtep_ip = leaf.get("vtep_ip", f"10.0.1.{i + 1}")

        if platform in ("eos", "arista"):
            configs[name] = f"""! {name} startup config
hostname {name}
interface Loopback0
   ip address {loopback}/32
interface Loopback1
   ip address {vtep_ip}/32
!
"""
        elif platform in ("nxos", "cisco_nxos"):
            configs[name] = f"""! {name} startup config
hostname {name}
interface loopback0
  ip address {loopback}/32
interface loopback1
  ip address {vtep_ip}/32
!
"""

    return configs
