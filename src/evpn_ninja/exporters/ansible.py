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
    if bgp_as is not None:
        inventory["all"]["children"]["fabric"]["vars"] = {
            "bgp_as": bgp_as,
        }

    # Add spines
    for i, spine in enumerate(spines):
        host_vars: dict[str, Any] = {
            "ansible_host": spine.get("ip", spine.get("loopback", "")),
            "role": "spine",
        }
        if "asn" in spine:
            host_vars["asn"] = spine["asn"]
        if "loopback" in spine:
            host_vars["loopback"] = spine["loopback"]

        spine_name = spine.get("name", f"spine-{i + 1}")
        inventory["all"]["children"]["fabric"]["children"]["spines"]["hosts"][spine_name] = (
            host_vars
        )

    # Add leaves
    for i, leaf in enumerate(leaves):
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

        leaf_name = leaf.get("name", f"leaf-{i + 1}")
        inventory["all"]["children"]["fabric"]["children"]["leaves"]["hosts"][leaf_name] = host_vars

    # Add extra groups
    if extra_groups:
        for group in extra_groups:
            group_data: dict[str, Any] = {"hosts": {}}
            for host in group.hosts:
                host_data: dict[str, Any] = {"ansible_host": host.ansible_host, "role": host.role}
                if host.asn is not None:
                    host_data["asn"] = host.asn
                if host.loopback is not None:
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
            vni_entry: dict[str, Any] = {
                "vlan_id": vni.get("vlan_id"),
                "vni": vni.get("vni_decimal", vni.get("vni")),
                "name": vni.get("name", f"VLAN{vni.get('vlan_id')}"),
            }
            if vni.get("multicast_group") is not None:
                vni_entry["multicast_group"] = vni["multicast_group"]
            vars_data["vxlan_vnis"].append(vni_entry)

    # EVPN parameters
    if evpn_params:
        evpn_data: dict[str, Any] = {}
        for key in ("l2_vni", "l2_rd", "l2_rt_import", "l2_rt_export"):
            val = evpn_params.get(key)
            if val is not None:
                evpn_data[key] = val
        vars_data["evpn"] = evpn_data
        if evpn_params.get("l3_vni") is not None:
            vars_data["evpn"]["l3_vni"] = evpn_params["l3_vni"]
            for l3_key in ("l3_rd", "l3_rt_import", "l3_rt_export"):
                val = evpn_params.get(l3_key)
                if val is not None:
                    vars_data["evpn"][l3_key] = val
            if evpn_params.get("vrf_name") is not None:
                vars_data["evpn"]["vrf"] = evpn_params["vrf_name"]

    # Fabric parameters
    if fabric_params:
        fabric_mapping: dict[str, str | tuple[str, ...]] = {
            "spine_count": "spine_count",
            "leaf_count": ("leaf_count", "vtep_count"),
            "replication_mode": "replication_mode",
            "loopback_network": "loopback_network",
            "vtep_network": "vtep_loopback_network",
            "p2p_network": "p2p_network",
        }
        fabric_data: dict[str, Any] = {}
        for out_key, src_key in fabric_mapping.items():
            if isinstance(src_key, tuple):
                val = next(
                    (fabric_params.get(k) for k in src_key if fabric_params.get(k) is not None),
                    None,
                )
            else:
                val = fabric_params.get(src_key)
            if val is not None:
                fabric_data[out_key] = val
        vars_data["fabric"] = fabric_data

    # BGP sessions
    if bgp_sessions:
        vars_data["bgp_neighbors"] = []
        for session in bgp_sessions:
            vars_data["bgp_neighbors"].append(
                {
                    "peer_ip": session.get("peer_ip", session.get("device_b_ip")),
                    "peer_as": session.get("peer_as", session.get("device_b_asn")),
                    "description": session.get("description", session.get("device_b")),
                }
            )

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
