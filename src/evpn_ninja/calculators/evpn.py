"""EVPN Parameters Calculator with vendor config generation."""

from dataclasses import dataclass
from enum import Enum


class Vendor(str, Enum):
    """Network equipment vendor."""
    ARISTA = "arista"
    CISCO_NXOS = "cisco-nxos"
    CISCO_IOSXE = "cisco-iosxe"
    CISCO_IOSXR = "cisco-iosxr"
    JUNIPER = "juniper"
    HUAWEI_CE = "huawei-ce"
    NOKIA_SRLINUX = "nokia-srlinux"
    CUMULUS = "cumulus"
    SONIC = "sonic"
    DELL_OS10 = "dell-os10"
    ARUBA_CX = "aruba-cx"
    EXTREME_EXOS = "extreme-exos"
    MIKROTIK = "mikrotik"
    VYOS = "vyos"
    FORTINET = "fortinet"
    H3C = "h3c"
    ZTE = "zte"
    MELLANOX = "mellanox"


@dataclass
class EVPNParameters:
    """Calculated EVPN parameters."""
    route_distinguisher: str
    route_target_import: str
    route_target_export: str
    evi: int
    vni_type: str  # L2 or L3


@dataclass
class VendorConfig:
    """Vendor-specific configuration."""
    vendor: str
    config: str


@dataclass
class EVPNResult:
    """EVPN calculation result."""
    bgp_as: int
    loopback_ip: str
    l2_vni: int
    vlan_id: int
    l3_vni: int | None
    vrf_name: str | None
    l2_params: EVPNParameters
    l3_params: EVPNParameters | None
    configs: list[VendorConfig]


def _calculate_rd(loopback_ip: str, vni: int) -> str:
    """
    Calculate Route Distinguisher.

    Format: Type 1 - IP:VNI (loopback:vni)
    """
    return f"{loopback_ip}:{vni}"


def _calculate_rt(bgp_as: int, vni: int) -> str:
    """
    Calculate Route Target.

    Format: AS:VNI
    """
    return f"{bgp_as}:{vni}"


def _generate_arista_config(
    bgp_as: int,
    loopback_ip: str,
    l2_vni: int,
    vlan_id: int,
    l2_params: EVPNParameters,
    l3_vni: int | None = None,
    vrf_name: str | None = None,
    l3_params: EVPNParameters | None = None,
) -> str:
    """Generate Arista EOS configuration."""
    config = f"""! Arista EOS VXLAN/EVPN Configuration
!
! VLAN Configuration
vlan {vlan_id}
   name VXLAN_L2VNI_{l2_vni}
!
! VXLAN Interface
interface Vxlan1
   vxlan source-interface Loopback1
   vxlan udp-port 4789
   vxlan vlan {vlan_id} vni {l2_vni}"""

    if l3_vni and vrf_name:
        config += f"""
   vxlan vrf {vrf_name} vni {l3_vni}"""

    config += f"""
!
! BGP EVPN Configuration
router bgp {bgp_as}
   !
   vlan {vlan_id}
      rd {l2_params.route_distinguisher}
      route-target both {l2_params.route_target_import}
      redistribute learned"""

    if l3_vni and vrf_name and l3_params:
        config += f"""
   !
   vrf {vrf_name}
      rd {l3_params.route_distinguisher}
      route-target import evpn {l3_params.route_target_import}
      route-target export evpn {l3_params.route_target_export}"""

    return config


def _generate_cisco_nxos_config(
    bgp_as: int,
    loopback_ip: str,
    l2_vni: int,
    vlan_id: int,
    l2_params: EVPNParameters,
    l3_vni: int | None = None,
    vrf_name: str | None = None,
    l3_params: EVPNParameters | None = None,
) -> str:
    """Generate Cisco NX-OS configuration."""
    config = f"""! Cisco NX-OS VXLAN/EVPN Configuration
!
! Enable features
feature nv overlay
feature vn-segment-vlan-based
feature bgp
feature nv overlay evpn
!
! VLAN to VNI mapping
vlan {vlan_id}
  name VXLAN_L2VNI_{l2_vni}
  vn-segment {l2_vni}
!"""

    if l3_vni and vrf_name:
        config += f"""
! VRF Configuration
vrf context {vrf_name}
  vni {l3_vni}
  rd {l3_params.route_distinguisher if l3_params else f'{loopback_ip}:{l3_vni}'}
  address-family ipv4 unicast
    route-target both {l3_params.route_target_import if l3_params else f'{bgp_as}:{l3_vni}'}
    route-target both {l3_params.route_target_export if l3_params else f'{bgp_as}:{l3_vni}'} evpn
!"""

    config += f"""
! NVE Interface
interface nve1
  no shutdown
  host-reachability protocol bgp
  source-interface loopback1
  member vni {l2_vni}
    ingress-replication protocol bgp"""

    if l3_vni and vrf_name:
        config += f"""
  member vni {l3_vni} associate-vrf"""

    config += f"""
!
! EVPN Configuration
evpn
  vni {l2_vni} l2
    rd {l2_params.route_distinguisher}
    route-target import {l2_params.route_target_import}
    route-target export {l2_params.route_target_export}
!
! BGP Configuration
router bgp {bgp_as}
  address-family l2vpn evpn"""

    return config


def _generate_juniper_config(
    bgp_as: int,
    loopback_ip: str,
    l2_vni: int,
    vlan_id: int,
    l2_params: EVPNParameters,
    l3_vni: int | None = None,
    vrf_name: str | None = None,
    l3_params: EVPNParameters | None = None,
) -> str:
    """Generate Juniper Junos configuration."""
    config = f"""# Juniper Junos VXLAN/EVPN Configuration
#
# VLAN Configuration
set vlans VLAN{vlan_id} vlan-id {vlan_id}
set vlans VLAN{vlan_id} vxlan vni {l2_vni}
set vlans VLAN{vlan_id} vxlan ingress-node-replication
#
# Switch Options (EVPN)
set switch-options vtep-source-interface lo0.0
set switch-options route-distinguisher {l2_params.route_distinguisher}
set switch-options vrf-target target:{l2_params.route_target_import}
#
# EVPN Protocol
set protocols evpn encapsulation vxlan
set protocols evpn extended-vni-list {l2_vni}
#
# BGP Configuration
set protocols bgp group EVPN-OVERLAY type internal
set protocols bgp group EVPN-OVERLAY local-address {loopback_ip}
set protocols bgp group EVPN-OVERLAY family evpn signaling"""

    if l3_vni and vrf_name and l3_params:
        config += f"""
#
# L3 VRF Configuration
set routing-instances {vrf_name} instance-type vrf
set routing-instances {vrf_name} route-distinguisher {l3_params.route_distinguisher}
set routing-instances {vrf_name} vrf-target target:{l3_params.route_target_import}
set routing-instances {vrf_name} protocols evpn ip-prefix-routes advertise direct-nexthop
set routing-instances {vrf_name} protocols evpn ip-prefix-routes encapsulation vxlan
set routing-instances {vrf_name} protocols evpn ip-prefix-routes vni {l3_vni}"""

    return config


def _generate_huawei_ce_config(
    bgp_as: int,
    loopback_ip: str,
    l2_vni: int,
    vlan_id: int,
    l2_params: EVPNParameters,
    l3_vni: int | None = None,
    vrf_name: str | None = None,
    l3_params: EVPNParameters | None = None,
) -> str:
    """Generate Huawei CloudEngine configuration."""
    config = f"""# Huawei CloudEngine VXLAN/EVPN Configuration
#
# Bridge Domain Configuration
bridge-domain {vlan_id}
 vxlan vni {l2_vni}
#
# VLAN Configuration
vlan {vlan_id}
#
# NVE Interface
interface Nve1
 source {loopback_ip}
 vni {l2_vni} head-end peer-list protocol bgp"""

    if l3_vni and vrf_name:
        config += f"""
 vni {l3_vni} associate-vrf"""

    config += f"""
#
# EVPN Instance
evpn vpn-instance evpn1 bd-mode
 route-distinguisher {l2_params.route_distinguisher}
 vpn-target {l2_params.route_target_import} export-extcommunity
 vpn-target {l2_params.route_target_import} import-extcommunity
#
# BGP Configuration
bgp {bgp_as}
 peer {loopback_ip} as-number {bgp_as}
 #
 l2vpn-family evpn
  peer {loopback_ip} enable"""

    if l3_vni and vrf_name and l3_params:
        config += f"""
#
# VRF Configuration
ip vpn-instance {vrf_name}
 ipv4-family
  route-distinguisher {l3_params.route_distinguisher}
  vpn-target {l3_params.route_target_import} export-extcommunity evpn
  vpn-target {l3_params.route_target_import} import-extcommunity evpn
 vxlan vni {l3_vni}"""

    return config


def _generate_nokia_srlinux_config(
    bgp_as: int,
    loopback_ip: str,
    l2_vni: int,
    vlan_id: int,
    l2_params: EVPNParameters,
    l3_vni: int | None = None,
    vrf_name: str | None = None,
    l3_params: EVPNParameters | None = None,
) -> str:
    """Generate Nokia SR Linux configuration."""
    config = f"""# Nokia SR Linux VXLAN/EVPN Configuration
#
# Tunnel Interface
set / tunnel-interface vxlan1
set / tunnel-interface vxlan1 vxlan-interface 1
set / tunnel-interface vxlan1 vxlan-interface 1 type bridged
set / tunnel-interface vxlan1 vxlan-interface 1 ingress vni {l2_vni}
#
# Network Instance (MAC-VRF)
set / network-instance mac-vrf-{vlan_id}
set / network-instance mac-vrf-{vlan_id} type mac-vrf
set / network-instance mac-vrf-{vlan_id} interface ethernet-1/1.{vlan_id}
set / network-instance mac-vrf-{vlan_id} vxlan-interface vxlan1.1
set / network-instance mac-vrf-{vlan_id} protocols
set / network-instance mac-vrf-{vlan_id} protocols bgp-evpn
set / network-instance mac-vrf-{vlan_id} protocols bgp-evpn bgp-instance 1
set / network-instance mac-vrf-{vlan_id} protocols bgp-evpn bgp-instance 1 admin-state enable
set / network-instance mac-vrf-{vlan_id} protocols bgp-evpn bgp-instance 1 vxlan-interface vxlan1.1
set / network-instance mac-vrf-{vlan_id} protocols bgp-evpn bgp-instance 1 evi {l2_params.evi}
set / network-instance mac-vrf-{vlan_id} protocols bgp-evpn bgp-instance 1 ecmp 2
set / network-instance mac-vrf-{vlan_id} protocols bgp-vpn
set / network-instance mac-vrf-{vlan_id} protocols bgp-vpn bgp-instance 1
set / network-instance mac-vrf-{vlan_id} protocols bgp-vpn bgp-instance 1 route-distinguisher rd {l2_params.route_distinguisher}
set / network-instance mac-vrf-{vlan_id} protocols bgp-vpn bgp-instance 1 route-target export-rt target:{l2_params.route_target_export}
set / network-instance mac-vrf-{vlan_id} protocols bgp-vpn bgp-instance 1 route-target import-rt target:{l2_params.route_target_import}"""

    if l3_vni and vrf_name and l3_params:
        config += f"""
#
# IP-VRF Configuration
set / network-instance {vrf_name}
set / network-instance {vrf_name} type ip-vrf
set / network-instance {vrf_name} protocols
set / network-instance {vrf_name} protocols bgp-evpn
set / network-instance {vrf_name} protocols bgp-evpn bgp-instance 1
set / network-instance {vrf_name} protocols bgp-evpn bgp-instance 1 admin-state enable
set / network-instance {vrf_name} protocols bgp-evpn bgp-instance 1 vxlan-interface vxlan1.{l3_vni}
set / network-instance {vrf_name} protocols bgp-evpn bgp-instance 1 evi {l3_params.evi}
set / network-instance {vrf_name} protocols bgp-vpn
set / network-instance {vrf_name} protocols bgp-vpn bgp-instance 1
set / network-instance {vrf_name} protocols bgp-vpn bgp-instance 1 route-distinguisher rd {l3_params.route_distinguisher}
set / network-instance {vrf_name} protocols bgp-vpn bgp-instance 1 route-target export-rt target:{l3_params.route_target_export}
set / network-instance {vrf_name} protocols bgp-vpn bgp-instance 1 route-target import-rt target:{l3_params.route_target_import}"""

    return config


def _generate_cumulus_config(
    bgp_as: int,
    loopback_ip: str,
    l2_vni: int,
    vlan_id: int,
    l2_params: EVPNParameters,
    l3_vni: int | None = None,
    vrf_name: str | None = None,
    l3_params: EVPNParameters | None = None,
) -> str:
    """Generate Cumulus Linux / NVIDIA configuration."""
    config = f"""# Cumulus Linux / NVIDIA VXLAN/EVPN Configuration
# /etc/network/interfaces

# Loopback
auto lo
iface lo inet loopback
    address {loopback_ip}/32
    vxlan-local-tunnelip {loopback_ip}

# VLAN-aware bridge
auto bridge
iface bridge
    bridge-ports vni{l2_vni}
    bridge-vids {vlan_id}
    bridge-vlan-aware yes

# VXLAN VNI
auto vni{l2_vni}
iface vni{l2_vni}
    bridge-access {vlan_id}
    vxlan-id {l2_vni}
    bridge-learning off
    bridge-arp-nd-suppress on"""

    if l3_vni and vrf_name:
        config += f"""

# L3 VNI for VRF
auto {vrf_name}
iface {vrf_name}
    vrf-table auto

auto vni{l3_vni}
iface vni{l3_vni}
    vxlan-id {l3_vni}
    bridge-learning off
    bridge-access {l3_vni}

auto bridge
iface bridge
    bridge-ports vni{l2_vni} vni{l3_vni}"""

    config += f"""

# /etc/frr/frr.conf
router bgp {bgp_as}
 bgp router-id {loopback_ip}
 neighbor SPINE peer-group
 neighbor SPINE remote-as external
 !
 address-family l2vpn evpn
  neighbor SPINE activate
  advertise-all-vni
 exit-address-family"""

    if l3_vni and vrf_name:
        config += f"""
 !
 vrf {vrf_name}
  vni {l3_vni}
  rd {l3_params.route_distinguisher if l3_params else f'{loopback_ip}:{l3_vni}'}
  route-target export {l3_params.route_target_export if l3_params else f'{bgp_as}:{l3_vni}'}
  route-target import {l3_params.route_target_import if l3_params else f'{bgp_as}:{l3_vni}'}
 exit-vrf"""

    return config


def _generate_cisco_iosxe_config(
    bgp_as: int,
    loopback_ip: str,
    l2_vni: int,
    vlan_id: int,
    l2_params: EVPNParameters,
    l3_vni: int | None = None,
    vrf_name: str | None = None,
    l3_params: EVPNParameters | None = None,
) -> str:
    """Generate Cisco IOS-XE (Catalyst 9000) configuration."""
    config = f"""! Cisco IOS-XE VXLAN/EVPN Configuration (Catalyst 9000)
!
! VLAN Configuration
vlan {vlan_id}
 name VXLAN_L2VNI_{l2_vni}
!
! L2VNI Configuration
l2vpn evpn instance {l2_vni} vlan-based
 encapsulation vxlan
 rd {l2_params.route_distinguisher}
 route-target export {l2_params.route_target_export}
 route-target import {l2_params.route_target_import}
!"""

    if l3_vni and vrf_name:
        config += f"""
! VRF Configuration
vrf definition {vrf_name}
 rd {l3_params.route_distinguisher if l3_params else f'{loopback_ip}:{l3_vni}'}
 !
 address-family ipv4
  route-target export {l3_params.route_target_export if l3_params else f'{bgp_as}:{l3_vni}'}
  route-target import {l3_params.route_target_import if l3_params else f'{bgp_as}:{l3_vni}'}
  route-target export {l3_params.route_target_export if l3_params else f'{bgp_as}:{l3_vni}'} evpn
  route-target import {l3_params.route_target_import if l3_params else f'{bgp_as}:{l3_vni}'} evpn
 exit-address-family
!
! L3VNI Configuration
l2vpn evpn instance {l3_vni} vlan-based
 encapsulation vxlan
!"""

    config += f"""
! NVE Interface
interface nve1
 no ip address
 source-interface Loopback1
 host-reachability protocol bgp
 member vni {l2_vni} ingress-replication"""

    if l3_vni and vrf_name:
        config += f"""
 member vni {l3_vni} vrf {vrf_name}"""

    config += f"""
!
! BGP Configuration
router bgp {bgp_as}
 bgp router-id {loopback_ip}
 !
 address-family l2vpn evpn
  neighbor SPINE activate
  neighbor SPINE send-community extended
 exit-address-family
!"""

    return config


def _generate_cisco_iosxr_config(
    bgp_as: int,
    loopback_ip: str,
    l2_vni: int,
    vlan_id: int,
    l2_params: EVPNParameters,
    l3_vni: int | None = None,
    vrf_name: str | None = None,
    l3_params: EVPNParameters | None = None,
) -> str:
    """Generate Cisco IOS-XR configuration."""
    config = f"""!! Cisco IOS-XR VXLAN/EVPN Configuration
!!
!! L2VPN EVPN Configuration
l2vpn
 bridge group VXLAN
  bridge-domain BD{vlan_id}
   vni {l2_vni}
   evi {l2_params.evi}
   !
  !
 !
!
evpn
 evi {l2_params.evi}
  bgp
   rd {l2_params.route_distinguisher}
   route-target import {l2_params.route_target_import}
   route-target export {l2_params.route_target_export}
  !
  advertise-mac
  !
 !
!"""

    if l3_vni and vrf_name and l3_params:
        config += f"""
!! VRF Configuration
vrf {vrf_name}
 rd {l3_params.route_distinguisher}
 address-family ipv4 unicast
  import route-target
   {l3_params.route_target_import}
  !
  export route-target
   {l3_params.route_target_export}
  !
 !
!"""

    config += f"""
!! BGP Configuration
router bgp {bgp_as}
 bgp router-id {loopback_ip}
 !
 address-family l2vpn evpn
 !
 neighbor-group EVPN-PEERS
  remote-as {bgp_as}
  update-source Loopback0
  address-family l2vpn evpn
  !
 !
!"""

    return config


def _generate_sonic_config(
    bgp_as: int,
    loopback_ip: str,
    l2_vni: int,
    vlan_id: int,
    l2_params: EVPNParameters,
    l3_vni: int | None = None,
    vrf_name: str | None = None,
    l3_params: EVPNParameters | None = None,
) -> str:
    """Generate SONiC configuration (config_db.json format)."""
    config = f"""// SONiC VXLAN/EVPN Configuration
// Apply using: sudo config load config_db.json

{{
  "VLAN": {{
    "Vlan{vlan_id}": {{
      "vlanid": "{vlan_id}"
    }}
  }},
  "VXLAN_TUNNEL": {{
    "vtep1": {{
      "src_ip": "{loopback_ip}"
    }}
  }},
  "VXLAN_TUNNEL_MAP": {{
    "vtep1|map_{l2_vni}_Vlan{vlan_id}": {{
      "vlan": "Vlan{vlan_id}",
      "vni": "{l2_vni}"
    }}
  }},
  "VXLAN_EVPN_NVO": {{
    "nvo1": {{
      "source_vtep": "vtep1"
    }}
  }}
}}

// FRR Configuration (/etc/frr/frr.conf)
router bgp {bgp_as}
 bgp router-id {loopback_ip}
 no bgp default ipv4-unicast
 neighbor SPINE peer-group
 neighbor SPINE remote-as external
 !
 address-family l2vpn evpn
  neighbor SPINE activate
  advertise-all-vni
  vni {l2_vni}
   rd {l2_params.route_distinguisher}
   route-target import {l2_params.route_target_import}
   route-target export {l2_params.route_target_export}
  exit-vni
 exit-address-family"""

    if l3_vni and vrf_name:
        config += f"""
 !
 vrf {vrf_name}
  vni {l3_vni}
 exit-vrf"""

    return config


def _generate_dell_os10_config(
    bgp_as: int,
    loopback_ip: str,
    l2_vni: int,
    vlan_id: int,
    l2_params: EVPNParameters,
    l3_vni: int | None = None,
    vrf_name: str | None = None,
    l3_params: EVPNParameters | None = None,
) -> str:
    """Generate Dell OS10 configuration."""
    config = f"""! Dell OS10 VXLAN/EVPN Configuration
!
! VLAN Configuration
interface vlan {vlan_id}
 description VXLAN_L2VNI_{l2_vni}
 no shutdown
!
! NVE Interface
interface nve 1
 source-interface loopback 1
 member-vni {l2_vni}
  ingress-replication
  remote-vtep-list
 !
!"""

    if l3_vni and vrf_name:
        config += f"""
! VRF Configuration
ip vrf {vrf_name}
 rd {l3_params.route_distinguisher if l3_params else f'{loopback_ip}:{l3_vni}'}
 route-target import {l3_params.route_target_import if l3_params else f'{bgp_as}:{l3_vni}'}
 route-target export {l3_params.route_target_export if l3_params else f'{bgp_as}:{l3_vni}'}
!
interface nve 1
 member-vni {l3_vni} associate-vrf
!"""

    config += f"""
! EVPN Configuration
evpn
 evi {l2_params.evi}
  rd {l2_params.route_distinguisher}
  route-target import {l2_params.route_target_import}
  route-target export {l2_params.route_target_export}
  vni {l2_vni}
 !
!
! BGP Configuration
router bgp {bgp_as}
 router-id {loopback_ip}
 !
 address-family l2vpn evpn
  advertise-all-vni
 exit-address-family
!"""

    return config


def _generate_aruba_cx_config(
    bgp_as: int,
    loopback_ip: str,
    l2_vni: int,
    vlan_id: int,
    l2_params: EVPNParameters,
    l3_vni: int | None = None,
    vrf_name: str | None = None,
    l3_params: EVPNParameters | None = None,
) -> str:
    """Generate Aruba AOS-CX configuration."""
    config = f"""! Aruba AOS-CX VXLAN/EVPN Configuration
!
! VLAN Configuration
vlan {vlan_id}
    name VXLAN_L2VNI_{l2_vni}
!
! VXLAN Configuration
interface vxlan 1
    source ip {loopback_ip}
    no shutdown
    vni {l2_vni}
        vlan {vlan_id}
!"""

    if l3_vni and vrf_name:
        config += f"""
! VRF Configuration
vrf {vrf_name}
    rd {l3_params.route_distinguisher if l3_params else f'{loopback_ip}:{l3_vni}'}
    route-target import {l3_params.route_target_import if l3_params else f'{bgp_as}:{l3_vni}'} evpn
    route-target export {l3_params.route_target_export if l3_params else f'{bgp_as}:{l3_vni}'} evpn
!
interface vxlan 1
    vni {l3_vni}
        vrf {vrf_name}
        routing
!"""

    config += f"""
! EVPN Configuration
evpn
    vni {l2_vni}
        rd {l2_params.route_distinguisher}
        route-target import {l2_params.route_target_import}
        route-target export {l2_params.route_target_export}
!
! BGP Configuration
router bgp {bgp_as}
    bgp router-id {loopback_ip}
    address-family l2vpn evpn
        neighbor SPINE activate
        neighbor SPINE send-community extended
    exit-address-family
!"""

    return config


def _generate_extreme_exos_config(
    bgp_as: int,
    loopback_ip: str,
    l2_vni: int,
    vlan_id: int,
    l2_params: EVPNParameters,
    l3_vni: int | None = None,
    vrf_name: str | None = None,
    l3_params: EVPNParameters | None = None,
) -> str:
    """Generate Extreme Networks EXOS configuration."""
    config = f"""# Extreme EXOS VXLAN/EVPN Configuration
#
# VLAN Configuration
create vlan "VXLAN_{l2_vni}" tag {vlan_id}
#
# VXLAN Configuration
create virtual-network "VN_{l2_vni}" flooding standard
configure virtual-network "VN_{l2_vni}" vxlan vni {l2_vni}
configure virtual-network "VN_{l2_vni}" add vlan "VXLAN_{l2_vni}"
#
# OSPF Interface (loopback)
configure ospf add vlan "Loopback" area 0.0.0.0 passive
#
# VXLAN VTEP
configure virtual-network local-endpoint ipaddress {loopback_ip}
configure virtual-network "VN_{l2_vni}" remote-endpoint vxlan ipaddress <remote-vtep>
#
# BGP Configuration
configure bgp AS-number {bgp_as}
configure bgp router-id {loopback_ip}
#
# EVPN Configuration
configure bgp evpn l2vpn add vni {l2_vni}
configure bgp evpn l2vpn vni {l2_vni} rd {l2_params.route_distinguisher}
configure bgp evpn l2vpn vni {l2_vni} route-target both add {l2_params.route_target_import}
#"""

    if l3_vni and vrf_name:
        config += f"""
# VRF Configuration
create vr "{vrf_name}"
configure vr "{vrf_name}" add protocol bgp
configure bgp vr "{vrf_name}" AS-number {bgp_as}
configure bgp evpn l3vpn add vni {l3_vni}
#"""

    config += """
# Enable BGP
enable bgp
"""

    return config


def _generate_mikrotik_config(
    bgp_as: int,
    loopback_ip: str,
    l2_vni: int,
    vlan_id: int,
    l2_params: EVPNParameters,
    l3_vni: int | None = None,
    vrf_name: str | None = None,
    l3_params: EVPNParameters | None = None,
) -> str:
    """Generate MikroTik RouterOS 7 configuration."""
    config = f"""# MikroTik RouterOS 7 VXLAN/EVPN Configuration
#
# Bridge Configuration
/interface bridge
add name=bridge1 vlan-filtering=yes

/interface bridge port
add bridge=bridge1 interface=ether1

/interface bridge vlan
add bridge=bridge1 tagged=bridge1 vlan-ids={vlan_id}

# VXLAN Interface
/interface vxlan
add name=vxlan{l2_vni} vni={l2_vni} port=4789 local-address={loopback_ip}

/interface bridge port
add bridge=bridge1 interface=vxlan{l2_vni} pvid={vlan_id}

# Loopback Address
/ip address
add address={loopback_ip}/32 interface=lo

# BGP Configuration
/routing bgp template
add name=evpn-peer as={bgp_as} router-id={loopback_ip}

/routing bgp connection
add name=spine1 template=evpn-peer remote.address=<SPINE_IP> local.role=ebgp \\
    address-families=l2vpn-evpn

# EVPN Instance
/routing bgp evpn
add name=evpn1 vni={l2_vni} rd={l2_params.route_distinguisher} \\
    import.route-targets={l2_params.route_target_import} \\
    export.route-targets={l2_params.route_target_export}"""

    if l3_vni and vrf_name:
        config += f"""

# VRF Configuration
/ip vrf
add name={vrf_name}

/routing bgp evpn
add name=evpn-l3 vni={l3_vni} rd={l3_params.route_distinguisher if l3_params else f'{loopback_ip}:{l3_vni}'} \\
    import.route-targets={l3_params.route_target_import if l3_params else f'{bgp_as}:{l3_vni}'} \\
    export.route-targets={l3_params.route_target_export if l3_params else f'{bgp_as}:{l3_vni}'}"""

    return config


def _generate_vyos_config(
    bgp_as: int,
    loopback_ip: str,
    l2_vni: int,
    vlan_id: int,
    l2_params: EVPNParameters,
    l3_vni: int | None = None,
    vrf_name: str | None = None,
    l3_params: EVPNParameters | None = None,
) -> str:
    """Generate VyOS 1.4/1.5 configuration."""
    config = f"""# VyOS 1.4/1.5 VXLAN/EVPN Configuration
#
# Loopback Interface
set interfaces loopback lo address {loopback_ip}/32

# Bridge Configuration
set interfaces bridge br100
set interfaces bridge br100 member interface eth1

# VXLAN Interface
set interfaces vxlan vxlan{l2_vni}
set interfaces vxlan vxlan{l2_vni} vni {l2_vni}
set interfaces vxlan vxlan{l2_vni} source-address {loopback_ip}
set interfaces vxlan vxlan{l2_vni} port 4789

# Add VXLAN to Bridge
set interfaces bridge br100 member interface vxlan{l2_vni}

# BGP Configuration
set protocols bgp system-as {bgp_as}
set protocols bgp parameters router-id {loopback_ip}
set protocols bgp neighbor <SPINE_IP> remote-as external
set protocols bgp neighbor <SPINE_IP> address-family l2vpn-evpn

# EVPN Configuration
set protocols bgp address-family l2vpn-evpn advertise-all-vni
set protocols bgp address-family l2vpn-evpn vni {l2_vni} rd {l2_params.route_distinguisher}
set protocols bgp address-family l2vpn-evpn vni {l2_vni} route-target import {l2_params.route_target_import}
set protocols bgp address-family l2vpn-evpn vni {l2_vni} route-target export {l2_params.route_target_export}"""

    if l3_vni and vrf_name:
        config += f"""

# VRF Configuration
set vrf name {vrf_name}
set vrf name {vrf_name} vni {l3_vni}
set protocols bgp address-family l2vpn-evpn vni {l3_vni} rd {l3_params.route_distinguisher if l3_params else f'{loopback_ip}:{l3_vni}'}
set protocols bgp address-family l2vpn-evpn vni {l3_vni} route-target import {l3_params.route_target_import if l3_params else f'{bgp_as}:{l3_vni}'}
set protocols bgp address-family l2vpn-evpn vni {l3_vni} route-target export {l3_params.route_target_export if l3_params else f'{bgp_as}:{l3_vni}'}"""

    return config


def _generate_fortinet_config(
    bgp_as: int,
    loopback_ip: str,
    l2_vni: int,
    vlan_id: int,
    l2_params: EVPNParameters,
    l3_vni: int | None = None,
    vrf_name: str | None = None,
    l3_params: EVPNParameters | None = None,
) -> str:
    """Generate Fortinet FortiGate/FortiSwitch configuration."""
    config = f"""# Fortinet FortiSwitch VXLAN/EVPN Configuration
# FortiOS 7.x
#
config system interface
    edit "loopback1"
        set vdom "root"
        set ip {loopback_ip} 255.255.255.255
        set type loopback
    next
end

config system interface
    edit "vxlan{l2_vni}"
        set vdom "root"
        set type vxlan
        set interface "port1"
        set remote-ip 0.0.0.0
        set vni {l2_vni}
        set dstport 4789
    next
end

config switch vlan
    edit {vlan_id}
        set description "VXLAN_L2VNI_{l2_vni}"
    next
end

config router bgp
    set as {bgp_as}
    set router-id {loopback_ip}
    config neighbor
        edit "<SPINE_IP>"
            set remote-as <SPINE_AS>
            set capability-default-originate enable
            set capability-graceful-restart enable
        next
    end
    config evpn
        set evi {l2_params.evi}
        set rd {l2_params.route_distinguisher}
        set import-rt {l2_params.route_target_import}
        set export-rt {l2_params.route_target_export}
    end
end"""

    if l3_vni and vrf_name:
        config += f"""

config vdom
    edit "{vrf_name}"
    next
end

config router bgp
    set vdom "{vrf_name}"
    config evpn
        set evi {l3_params.evi if l3_params else l3_vni}
        set rd {l3_params.route_distinguisher if l3_params else f'{loopback_ip}:{l3_vni}'}
        set import-rt {l3_params.route_target_import if l3_params else f'{bgp_as}:{l3_vni}'}
        set export-rt {l3_params.route_target_export if l3_params else f'{bgp_as}:{l3_vni}'}
    end
end"""

    return config


def _generate_h3c_config(
    bgp_as: int,
    loopback_ip: str,
    l2_vni: int,
    vlan_id: int,
    l2_params: EVPNParameters,
    l3_vni: int | None = None,
    vrf_name: str | None = None,
    l3_params: EVPNParameters | None = None,
) -> str:
    """Generate H3C Comware V7 configuration."""
    config = f"""# H3C Comware V7 VXLAN/EVPN Configuration
#
# VLAN Configuration
vlan {vlan_id}
 description VXLAN_L2VNI_{l2_vni}
#
# VSI Configuration (Virtual Switch Instance)
vsi vsi{l2_vni}
 vxlan {l2_vni}
 evpn encapsulation vxlan
  route-distinguisher {l2_params.route_distinguisher}
  vpn-target {l2_params.route_target_import} import-extcommunity
  vpn-target {l2_params.route_target_export} export-extcommunity
#
# Loopback Interface
interface LoopBack0
 ip address {loopback_ip} 32
#
# VXLAN Tunnel Interface
interface Vsi-interface{l2_vni}
 ip binding vpn-instance {vrf_name if vrf_name else 'default'}
#
# NVE Interface
interface Nve1
 source {loopback_ip}
 vni {l2_vni} head-end peer-list protocol bgp"""

    if l3_vni and vrf_name:
        config += f"""
 vni {l3_vni} associate-vrf
#
# VPN Instance Configuration
ip vpn-instance {vrf_name}
 route-distinguisher {l3_params.route_distinguisher if l3_params else f'{loopback_ip}:{l3_vni}'}
 vpn-target {l3_params.route_target_import if l3_params else f'{bgp_as}:{l3_vni}'} import-extcommunity evpn
 vpn-target {l3_params.route_target_export if l3_params else f'{bgp_as}:{l3_vni}'} export-extcommunity evpn
 vxlan vni {l3_vni}"""

    config += f"""
#
# BGP Configuration
bgp {bgp_as}
 router-id {loopback_ip}
 peer <SPINE_IP> as-number <SPINE_AS>
 #
 address-family l2vpn evpn
  peer <SPINE_IP> enable
  peer <SPINE_IP> advertise encap-type vxlan
#"""

    return config


def _generate_zte_config(
    bgp_as: int,
    loopback_ip: str,
    l2_vni: int,
    vlan_id: int,
    l2_params: EVPNParameters,
    l3_vni: int | None = None,
    vrf_name: str | None = None,
    l3_params: EVPNParameters | None = None,
) -> str:
    """Generate ZTE ZXROS configuration."""
    config = f"""! ZTE ZXROS VXLAN/EVPN Configuration
!
! VLAN Configuration
vlan {vlan_id}
 name VXLAN_L2VNI_{l2_vni}
!
! Bridge Domain Configuration
bridge-domain {vlan_id}
 vxlan vni {l2_vni}
!
! Loopback Interface
interface loopback 1
 ip address {loopback_ip}/32
!
! NVE Interface
interface nve 1
 source {loopback_ip}
 vni {l2_vni} ingress-replication protocol bgp"""

    if l3_vni and vrf_name:
        config += f"""
 vni {l3_vni} associate-vrf"""

    config += f"""
!
! EVPN Instance
evpn instance {l2_params.evi}
 route-distinguisher {l2_params.route_distinguisher}
 route-target import {l2_params.route_target_import}
 route-target export {l2_params.route_target_export}
!"""

    if l3_vni and vrf_name and l3_params:
        config += f"""
! VRF Configuration
ip vrf {vrf_name}
 rd {l3_params.route_distinguisher}
 route-target import {l3_params.route_target_import} evpn
 route-target export {l3_params.route_target_export} evpn
!"""

    config += f"""
! BGP Configuration
router bgp {bgp_as}
 bgp router-id {loopback_ip}
 !
 address-family l2vpn evpn
  neighbor <SPINE_IP> activate
  neighbor <SPINE_IP> send-community extended
 exit-address-family
!"""

    return config


def _generate_mellanox_config(
    bgp_as: int,
    loopback_ip: str,
    l2_vni: int,
    vlan_id: int,
    l2_params: EVPNParameters,
    l3_vni: int | None = None,
    vrf_name: str | None = None,
    l3_params: EVPNParameters | None = None,
) -> str:
    """Generate Mellanox/NVIDIA Onyx configuration."""
    config = f"""## Mellanox/NVIDIA Onyx VXLAN/EVPN Configuration
##
## VLAN Configuration
vlan {vlan_id}
   name VXLAN_L2VNI_{l2_vni}
exit

## Loopback Interface
interface loopback 1
   ip address {loopback_ip}/32
exit

## NVE Interface
interface nve 1
   nve vni {l2_vni} vlan {vlan_id}
   nve vni {l2_vni} nve-vtep-group 1
   nve vtep-group 1 remote-ip <REMOTE_VTEP>
   nve vxlan source interface loopback 1
exit"""

    if l3_vni and vrf_name:
        config += f"""

## VRF Configuration
vrf definition {vrf_name}
   rd {l3_params.route_distinguisher if l3_params else f'{loopback_ip}:{l3_vni}'}
   route-target import {l3_params.route_target_import if l3_params else f'{bgp_as}:{l3_vni}'} evpn
   route-target export {l3_params.route_target_export if l3_params else f'{bgp_as}:{l3_vni}'} evpn
exit

interface nve 1
   nve vni {l3_vni} vrf {vrf_name}
exit"""

    config += f"""

## BGP Configuration
router bgp {bgp_as}
   router-id {loopback_ip}
   !
   neighbor SPINE peer-group
   neighbor SPINE remote-as external
   neighbor <SPINE_IP> peer-group SPINE
   !
   address-family l2vpn evpn
      neighbor SPINE activate
      neighbor SPINE route-reflector-client
   exit-address-family
   !
   evpn vni {l2_vni}
      rd {l2_params.route_distinguisher}
      route-target import {l2_params.route_target_import}
      route-target export {l2_params.route_target_export}
   exit
exit
"""

    return config


def calculate_evpn_params(
    bgp_as: int = 65000,
    loopback_ip: str = "10.0.0.1",
    l2_vni: int = 10010,
    vlan_id: int = 10,
    l3_vni: int | None = None,
    vrf_name: str | None = None,
    vendors: list[Vendor] | None = None,
) -> EVPNResult:
    """
    Calculate EVPN parameters and generate vendor configurations.

    EVPN Parameters calculated:
    - Route Distinguisher (RD): IP:VNI format
    - Route Target (RT): AS:VNI format
    - EVI (EVPN Instance): derived from VNI

    Args:
        bgp_as: BGP Autonomous System number
        loopback_ip: VTEP loopback IP address
        l2_vni: Layer 2 VNI for the VLAN
        vlan_id: VLAN ID to map to VNI
        l3_vni: Layer 3 VNI for VRF (optional)
        vrf_name: VRF name for L3 VNI (optional)
        vendors: List of vendors to generate configs for (default: all)

    Returns:
        EVPNResult with parameters and configs
    """
    if vendors is None:
        vendors = list(Vendor)  # All vendors by default

    # Calculate L2 EVPN parameters
    l2_params = EVPNParameters(
        route_distinguisher=_calculate_rd(loopback_ip, l2_vni),
        route_target_import=_calculate_rt(bgp_as, l2_vni),
        route_target_export=_calculate_rt(bgp_as, l2_vni),
        evi=l2_vni,  # EVI often equals VNI
        vni_type="L2",
    )

    # Calculate L3 EVPN parameters if provided
    l3_params = None
    if l3_vni and vrf_name:
        l3_params = EVPNParameters(
            route_distinguisher=_calculate_rd(loopback_ip, l3_vni),
            route_target_import=_calculate_rt(bgp_as, l3_vni),
            route_target_export=_calculate_rt(bgp_as, l3_vni),
            evi=l3_vni,
            vni_type="L3",
        )

    # Generate vendor configs
    configs: list[VendorConfig] = []

    config_generators = {
        Vendor.ARISTA: _generate_arista_config,
        Vendor.CISCO_NXOS: _generate_cisco_nxos_config,
        Vendor.CISCO_IOSXE: _generate_cisco_iosxe_config,
        Vendor.CISCO_IOSXR: _generate_cisco_iosxr_config,
        Vendor.JUNIPER: _generate_juniper_config,
        Vendor.HUAWEI_CE: _generate_huawei_ce_config,
        Vendor.NOKIA_SRLINUX: _generate_nokia_srlinux_config,
        Vendor.CUMULUS: _generate_cumulus_config,
        Vendor.SONIC: _generate_sonic_config,
        Vendor.DELL_OS10: _generate_dell_os10_config,
        Vendor.ARUBA_CX: _generate_aruba_cx_config,
        Vendor.EXTREME_EXOS: _generate_extreme_exos_config,
        Vendor.MIKROTIK: _generate_mikrotik_config,
        Vendor.VYOS: _generate_vyos_config,
        Vendor.FORTINET: _generate_fortinet_config,
        Vendor.H3C: _generate_h3c_config,
        Vendor.ZTE: _generate_zte_config,
        Vendor.MELLANOX: _generate_mellanox_config,
    }

    for vendor in vendors:
        generator = config_generators.get(vendor)
        if generator:
            config = generator(
                bgp_as=bgp_as,
                loopback_ip=loopback_ip,
                l2_vni=l2_vni,
                vlan_id=vlan_id,
                l2_params=l2_params,
                l3_vni=l3_vni,
                vrf_name=vrf_name,
                l3_params=l3_params,
            )
            configs.append(VendorConfig(vendor=vendor.value, config=config))

    return EVPNResult(
        bgp_as=bgp_as,
        loopback_ip=loopback_ip,
        l2_vni=l2_vni,
        vlan_id=vlan_id,
        l3_vni=l3_vni,
        vrf_name=vrf_name,
        l2_params=l2_params,
        l3_params=l3_params,
        configs=configs,
    )
