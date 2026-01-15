"""Nornir export functionality.

Generates Nornir inventory files and defaults from calculator results.
"""

from typing import Any

import yaml


def export_nornir_inventory(
    spines: list[dict[str, Any]],
    leaves: list[dict[str, Any]],
    connection_options: dict[str, Any] | None = None,
) -> str:
    """
    Generate Nornir SimpleInventory hosts.yaml from fabric data.

    Args:
        spines: List of spine switch dicts with name, ip, asn
        leaves: List of leaf switch dicts with name, ip, asn
        connection_options: Nornir connection options

    Returns:
        Nornir hosts.yaml as YAML string

    Example output:
        spine-1:
          hostname: 10.0.0.1
          groups:
            - spines
          data:
            role: spine
            asn: 65000
        leaf-1:
          hostname: 10.0.1.1
          groups:
            - leaves
          data:
            role: leaf
            asn: 65001
    """
    hosts: dict[str, Any] = {}

    # Add spines
    for spine in spines:
        host_data: dict[str, Any] = {
            "hostname": spine.get("ip", spine.get("loopback", "")),
            "groups": ["spines", "fabric"],
            "data": {
                "role": "spine",
            },
        }
        if "asn" in spine:
            host_data["data"]["asn"] = spine["asn"]
        if "loopback" in spine:
            host_data["data"]["loopback"] = spine["loopback"]

        if connection_options:
            host_data["connection_options"] = connection_options

        hosts[spine["name"]] = host_data

    # Add leaves
    for leaf in leaves:
        host_data = {
            "hostname": leaf.get("ip", leaf.get("loopback", "")),
            "groups": ["leaves", "fabric"],
            "data": {
                "role": "leaf",
            },
        }
        if "asn" in leaf:
            host_data["data"]["asn"] = leaf["asn"]
        if "loopback" in leaf:
            host_data["data"]["loopback"] = leaf["loopback"]
        if "vtep_ip" in leaf:
            host_data["data"]["vtep_ip"] = leaf["vtep_ip"]

        if connection_options:
            host_data["connection_options"] = connection_options

        hosts[leaf["name"]] = host_data

    return yaml.dump(hosts, default_flow_style=False, sort_keys=False)


def export_nornir_groups(
    fabric_vars: dict[str, Any] | None = None,
    spine_vars: dict[str, Any] | None = None,
    leaf_vars: dict[str, Any] | None = None,
) -> str:
    """
    Generate Nornir SimpleInventory groups.yaml.

    Args:
        fabric_vars: Variables common to all fabric devices
        spine_vars: Variables specific to spines
        leaf_vars: Variables specific to leaves

    Returns:
        Nornir groups.yaml as YAML string
    """
    groups: dict[str, Any] = {
        "fabric": {
            "data": fabric_vars or {},
        },
        "spines": {
            "data": spine_vars or {"role": "spine"},
        },
        "leaves": {
            "data": leaf_vars or {"role": "leaf"},
        },
    }

    return yaml.dump(groups, default_flow_style=False, sort_keys=False)


def export_nornir_defaults(
    username: str = "admin",
    platform: str = "eos",
    port: int = 22,
    connection_options: dict[str, Any] | None = None,
) -> str:
    """
    Generate Nornir SimpleInventory defaults.yaml.

    Args:
        username: Default username
        platform: Default platform (eos, nxos, junos, etc.)
        port: Default connection port
        connection_options: Additional connection options

    Returns:
        Nornir defaults.yaml as YAML string
    """
    defaults: dict[str, Any] = {
        "username": username,
        "platform": platform,
        "port": port,
    }

    if connection_options:
        defaults["connection_options"] = connection_options
    else:
        # Default connection options for common plugins
        defaults["connection_options"] = {
            "napalm": {
                "extras": {
                    "optional_args": {
                        "transport": "ssh",
                    }
                }
            },
            "netmiko": {
                "extras": {
                    "device_type": _platform_to_netmiko(platform),
                }
            },
            "scrapli": {
                "extras": {
                    "auth_strict_key": False,
                }
            },
        }

    return yaml.dump(defaults, default_flow_style=False, sort_keys=False)


def _platform_to_netmiko(platform: str) -> str:
    """Convert Nornir platform to Netmiko device_type."""
    mapping = {
        "eos": "arista_eos",
        "nxos": "cisco_nxos",
        "nxos_ssh": "cisco_nxos",
        "iosxe": "cisco_xe",
        "iosxr": "cisco_xr",
        "junos": "juniper_junos",
        "linux": "linux",
        "huawei_vrp": "huawei",
    }
    return mapping.get(platform, platform)


def generate_nornir_config() -> str:
    """Generate sample Nornir config.yaml."""
    config = """---
# Nornir Configuration
# Generated by evpn-ninja

inventory:
  plugin: SimpleInventory
  options:
    host_file: "inventory/hosts.yaml"
    group_file: "inventory/groups.yaml"
    defaults_file: "inventory/defaults.yaml"

runner:
  plugin: threaded
  options:
    num_workers: 20

logging:
  enabled: True
  level: INFO
  log_file: "nornir.log"
"""
    return config


def generate_nornir_script_template() -> str:
    """Generate a sample Nornir Python script for VXLAN/EVPN deployment."""
    script = '''#!/usr/bin/env python3
"""
VXLAN/EVPN Deployment Script using Nornir
Generated by evpn-ninja
"""

from nornir import InitNornir
from nornir.core.filter import F
from nornir_napalm.plugins.tasks import napalm_configure, napalm_get
from nornir_utils.plugins.functions import print_result
from nornir_jinja2.plugins.tasks import template_file


def configure_underlay(task):
    """Configure underlay network (loopbacks, P2P links)."""
    # Generate config from Jinja2 template
    r = task.run(
        task=template_file,
        template="underlay.j2",
        path="templates/",
    )

    # Apply configuration
    task.run(
        task=napalm_configure,
        configuration=r.result,
        dry_run=False,
    )


def configure_bgp(task):
    """Configure BGP underlay."""
    r = task.run(
        task=template_file,
        template="bgp_underlay.j2",
        path="templates/",
    )

    task.run(
        task=napalm_configure,
        configuration=r.result,
        dry_run=False,
    )


def configure_vxlan_evpn(task):
    """Configure VXLAN/EVPN overlay."""
    r = task.run(
        task=template_file,
        template="vxlan_evpn.j2",
        path="templates/",
    )

    task.run(
        task=napalm_configure,
        configuration=r.result,
        dry_run=False,
    )


def verify_bgp_neighbors(task):
    """Verify BGP neighbor status."""
    r = task.run(
        task=napalm_get,
        getters=["bgp_neighbors"],
    )
    return r


def main():
    # Initialize Nornir
    nr = InitNornir(config_file="config.yaml")

    # Filter devices
    spines = nr.filter(F(groups__contains="spines"))
    leaves = nr.filter(F(groups__contains="leaves"))

    print("=" * 60)
    print("Phase 1: Configure Underlay Network")
    print("=" * 60)
    result = nr.run(task=configure_underlay)
    print_result(result)

    print("=" * 60)
    print("Phase 2: Configure BGP Underlay")
    print("=" * 60)
    result = nr.run(task=configure_bgp)
    print_result(result)

    print("=" * 60)
    print("Phase 3: Configure VXLAN/EVPN on Leaves")
    print("=" * 60)
    result = leaves.run(task=configure_vxlan_evpn)
    print_result(result)

    print("=" * 60)
    print("Verification: BGP Neighbors")
    print("=" * 60)
    result = nr.run(task=verify_bgp_neighbors)
    print_result(result)


if __name__ == "__main__":
    main()
'''
    return script
