"""Ansible export functionality.

Generates Ansible inventory files and group_vars from calculator results.
"""

from dataclasses import dataclass
from typing import Any

import yaml


@dataclass
class AnsibleHost:
    """Ansible inventory host."""

    name: str
    ansible_host: str
    role: str
    asn: int | None = None
    loopback: str | None = None
    extra_vars: dict[str, Any] | None = None


@dataclass
class AnsibleGroup:
    """Ansible inventory group."""

    name: str
    hosts: list[AnsibleHost]
    children: list[str] | None = None
    vars: dict[str, Any] | None = None


def export_ansible_inventory(
    spines: list[dict[str, Any]],
    leaves: list[dict[str, Any]],
    bgp_as: int | None = None,
    extra_groups: list[AnsibleGroup] | None = None,
) -> str:
    """
    Generate Ansible inventory YAML from fabric data.

    Args:
        spines: List of spine switch dicts with name, ip, asn
        leaves: List of leaf switch dicts with name, ip, asn
        bgp_as: Common BGP AS number (if iBGP)
        extra_groups: Additional groups to include

    Returns:
        Ansible inventory as YAML string

    Example output:
        all:
          children:
            fabric:
              children:
                spines:
                  hosts:
                    spine-1:
                      ansible_host: 10.0.0.1
                      role: spine
                      asn: 65000
                leaves:
                  hosts:
                    leaf-1:
                      ansible_host: 10.0.1.1
                      role: leaf
                      asn: 65001
    """
    inventory: dict[str, Any] = {
        "all": {
            "children": {
                "fabric": {
                    "children": {
                        "spines": {"hosts": {}},
                        "leaves": {"hosts": {}},
                    }
                }
            }
        }
    }

    # Add fabric-wide vars if iBGP
    if bgp_as:
        inventory["all"]["children"]["fabric"]["vars"] = {
            "bgp_as": bgp_as,
        }

    # Add spines
    for spine in spines:
        host_vars: dict[str, Any] = {
            "ansible_host": spine.get("ip", spine.get("loopback", "")),
            "role": "spine",
        }
        if "asn" in spine:
            host_vars["asn"] = spine["asn"]
        if "loopback" in spine:
            host_vars["loopback"] = spine["loopback"]

        inventory["all"]["children"]["fabric"]["children"]["spines"]["hosts"][
            spine["name"]
        ] = host_vars

    # Add leaves
    for leaf in leaves:
        host_vars = {
            "ansible_host": leaf.get("ip", leaf.get("loopback", "")),
            "role": "leaf",
        }
        if "asn" in leaf:
            host_vars["asn"] = leaf["asn"]
        if "loopback" in leaf:
            host_vars["loopback"] = leaf["loopback"]
        if "vtep_ip" in leaf:
            host_vars["vtep_ip"] = leaf["vtep_ip"]

        inventory["all"]["children"]["fabric"]["children"]["leaves"]["hosts"][
            leaf["name"]
        ] = host_vars

    # Add extra groups
    if extra_groups:
        for group in extra_groups:
            group_data: dict[str, Any] = {"hosts": {}}
            for host in group.hosts:
                host_data: dict[str, Any] = {"ansible_host": host.ansible_host, "role": host.role}
                if host.asn:
                    host_data["asn"] = host.asn
                if host.loopback:
                    host_data["loopback"] = host.loopback
                if host.extra_vars:
                    host_data.update(host.extra_vars)
                group_data["hosts"][host.name] = host_data

            if group.vars:
                group_data["vars"] = group.vars
            if group.children:
                group_data["children"] = group.children

            inventory["all"]["children"][group.name] = group_data

    return yaml.dump(inventory, default_flow_style=False, sort_keys=False)


def export_ansible_vars(
    vni_allocations: list[dict[str, Any]] | None = None,
    evpn_params: dict[str, Any] | None = None,
    fabric_params: dict[str, Any] | None = None,
    bgp_sessions: list[dict[str, Any]] | None = None,
) -> str:
    """
    Generate Ansible group_vars YAML from calculator results.

    Args:
        vni_allocations: VNI allocation data
        evpn_params: EVPN parameters (RD, RT, etc.)
        fabric_params: Fabric parameters
        bgp_sessions: BGP session configurations

    Returns:
        Ansible vars as YAML string
    """
    vars_data: dict[str, Any] = {}

    # VNI allocations
    if vni_allocations:
        vars_data["vxlan_vnis"] = []
        for vni in vni_allocations:
            vars_data["vxlan_vnis"].append({
                "vlan_id": vni.get("vlan_id"),
                "vni": vni.get("vni_decimal", vni.get("vni")),
                "name": vni.get("name", f"VLAN{vni.get('vlan_id')}"),
                "multicast_group": vni.get("multicast_group"),
            })

    # EVPN parameters
    if evpn_params:
        vars_data["evpn"] = {
            "l2_vni": evpn_params.get("l2_vni"),
            "l2_rd": evpn_params.get("l2_rd"),
            "l2_rt_import": evpn_params.get("l2_rt_import"),
            "l2_rt_export": evpn_params.get("l2_rt_export"),
        }
        if evpn_params.get("l3_vni"):
            vars_data["evpn"]["l3_vni"] = evpn_params.get("l3_vni")
            vars_data["evpn"]["l3_rd"] = evpn_params.get("l3_rd")
            vars_data["evpn"]["l3_rt_import"] = evpn_params.get("l3_rt_import")
            vars_data["evpn"]["l3_rt_export"] = evpn_params.get("l3_rt_export")
            vars_data["evpn"]["vrf"] = evpn_params.get("vrf_name")

    # Fabric parameters
    if fabric_params:
        vars_data["fabric"] = {
            "spine_count": fabric_params.get("spine_count"),
            "leaf_count": fabric_params.get("leaf_count", fabric_params.get("vtep_count")),
            "replication_mode": fabric_params.get("replication_mode"),
            "loopback_network": fabric_params.get("loopback_network"),
            "vtep_network": fabric_params.get("vtep_loopback_network"),
            "p2p_network": fabric_params.get("p2p_network"),
        }

    # BGP sessions
    if bgp_sessions:
        vars_data["bgp_neighbors"] = []
        for session in bgp_sessions:
            vars_data["bgp_neighbors"].append({
                "peer_ip": session.get("peer_ip", session.get("device_b_ip")),
                "peer_as": session.get("peer_as", session.get("device_b_asn")),
                "description": session.get("description", session.get("device_b")),
            })

    return yaml.dump(vars_data, default_flow_style=False, sort_keys=False)


def generate_ansible_playbook_template() -> str:
    """Generate a sample Ansible playbook for VXLAN/EVPN deployment."""
    playbook = """---
# VXLAN/EVPN Deployment Playbook
# Generated by evpn-ninja

- name: Configure Underlay Network
  hosts: fabric
  gather_facts: no
  tasks:
    - name: Configure loopback interfaces
      include_role:
        name: network_loopbacks
      vars:
        loopback_ip: "{{ loopback }}"

    - name: Configure P2P links
      include_role:
        name: network_p2p
      when: role == 'leaf' or role == 'spine'

- name: Configure BGP Underlay
  hosts: fabric
  gather_facts: no
  tasks:
    - name: Configure BGP on spines
      include_role:
        name: bgp_spine
      when: role == 'spine'

    - name: Configure BGP on leaves
      include_role:
        name: bgp_leaf
      when: role == 'leaf'

- name: Configure VXLAN/EVPN Overlay
  hosts: leaves
  gather_facts: no
  tasks:
    - name: Configure VTEP interface
      include_role:
        name: vxlan_vtep
      vars:
        vtep_source: "{{ vtep_ip }}"

    - name: Configure L2 VNIs
      include_role:
        name: evpn_l2vni
      loop: "{{ vxlan_vnis }}"
      loop_control:
        loop_var: vni

    - name: Configure L3 VNI (VRF)
      include_role:
        name: evpn_l3vni
      when: evpn.l3_vni is defined

    - name: Configure BGP EVPN
      include_role:
        name: bgp_evpn
"""
    return playbook
