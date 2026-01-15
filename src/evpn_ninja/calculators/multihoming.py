"""EVPN Multi-homing Calculator.

Calculates ESI (Ethernet Segment Identifier), LACP system IDs,
and multi-homing topology parameters for EVPN deployments.
"""

from dataclasses import dataclass, field
from enum import Enum


class MultiHomingMode(str, Enum):
    """Multi-homing redundancy mode."""
    ACTIVE_ACTIVE = "active-active"      # All-Active: traffic on all links
    ACTIVE_STANDBY = "active-standby"    # Single-Active: one active link
    PORT_ACTIVE = "port-active"          # Per-port active (Cisco)


class ESIType(str, Enum):
    """ESI type according to RFC 7432."""
    TYPE_0 = "type-0"  # Arbitrary 9-octet value
    TYPE_1 = "type-1"  # LACP-based (auto-derived from LACP)
    TYPE_3 = "type-3"  # MAC-based (system MAC + local discriminator)


class LACPMode(str, Enum):
    """LACP operational mode."""
    ACTIVE = "active"
    PASSIVE = "passive"


@dataclass
class ESIConfig:
    """Ethernet Segment Identifier configuration."""
    esi: str                          # Full ESI value (10 bytes in hex)
    esi_type: str                     # ESI type (0, 1, or 3)
    short_esi: str                    # Last 3 bytes (common identifier)
    description: str                  # Human-readable description


@dataclass
class LACPConfig:
    """LACP configuration for multi-homing."""
    system_id: str                    # LACP system ID (MAC address)
    system_priority: int              # LACP system priority
    port_key: int                     # LACP port key
    mode: str                         # active/passive


@dataclass
class MultiHomingPeer:
    """Configuration for a multi-homing peer."""
    name: str
    loopback_ip: str
    interface: str
    lacp_config: LACPConfig


@dataclass
class EthernetSegment:
    """Ethernet Segment configuration."""
    es_id: int                        # Logical ES identifier
    name: str                         # ES name/description
    esi_config: ESIConfig             # ESI configuration
    mode: str                         # active-active/active-standby
    peers: list[MultiHomingPeer]      # PE switches in this ES
    df_election: str                  # DF election algorithm
    es_import_rt: str                 # ES-Import Route Target


@dataclass
class MultiHomingResult:
    """Multi-homing calculation result."""
    ethernet_segments: list[EthernetSegment]
    total_es_count: int
    total_pe_count: int
    redundancy_mode: str
    lacp_system_mac: str
    vendor_configs: dict[str, str] = field(default_factory=dict)


def generate_esi_type0(
    es_id: int,
    prefix: str = "00:00:00",
) -> ESIConfig:
    """
    Generate Type-0 ESI (arbitrary value).

    Type-0 ESI format: 00:XX:XX:XX:XX:XX:XX:XX:XX:XX
    Where first byte is 00 (type indicator) and rest is arbitrary.

    Args:
        es_id: Ethernet Segment identifier
        prefix: Optional prefix for ESI (3 bytes)

    Returns:
        ESIConfig with generated ESI
    """
    # Parse prefix
    prefix_parts = prefix.split(":")
    if len(prefix_parts) != 3:
        prefix_parts = ["00", "00", "00"]

    # Generate ESI: 00 + prefix (3 bytes) + es_id (5 bytes)
    es_id_hex = f"{es_id:010x}"  # 5 bytes = 10 hex chars
    es_id_parts = [es_id_hex[i:i+2] for i in range(0, 10, 2)]

    esi_parts = ["00"] + prefix_parts + es_id_parts
    esi = ":".join(esi_parts)
    short_esi = ":".join(es_id_parts[-3:])

    return ESIConfig(
        esi=esi,
        esi_type="type-0",
        short_esi=short_esi,
        description=f"Type-0 ESI for ES-{es_id}",
    )


def generate_esi_type1(
    lacp_port_key: int,
    lacp_system_mac: str,
) -> ESIConfig:
    """
    Generate Type-1 ESI (LACP-based).

    Type-1 ESI format: 01:SYSTEM_MAC:PORT_KEY:00:00
    Automatically derived from LACP parameters.

    Args:
        lacp_port_key: LACP port key (2 bytes)
        lacp_system_mac: LACP system MAC address

    Returns:
        ESIConfig with generated ESI
    """
    # Normalize MAC address
    mac_parts = lacp_system_mac.replace("-", ":").lower().split(":")
    if len(mac_parts) != 6:
        mac_parts = ["00", "00", "00", "00", "00", "01"]

    # Port key as 2 bytes
    port_key_hex = f"{lacp_port_key:04x}"
    port_key_parts = [port_key_hex[i:i+2] for i in range(0, 4, 2)]

    # ESI: 01 + MAC (6 bytes) + Port Key (2 bytes) + 00
    esi_parts = ["01"] + mac_parts + port_key_parts + ["00"]
    esi = ":".join(esi_parts)
    short_esi = ":".join(port_key_parts + ["00"])

    return ESIConfig(
        esi=esi,
        esi_type="type-1",
        short_esi=short_esi,
        description=f"Type-1 ESI (LACP-derived, port-key={lacp_port_key})",
    )


def generate_esi_type3(
    system_mac: str,
    local_discriminator: int,
) -> ESIConfig:
    """
    Generate Type-3 ESI (MAC-based).

    Type-3 ESI format: 03:SYSTEM_MAC:LOCAL_DISCRIM (3 bytes)
    Based on system MAC and local discriminator.

    Args:
        system_mac: System MAC address
        local_discriminator: Local discriminator value (3 bytes max)

    Returns:
        ESIConfig with generated ESI
    """
    # Normalize MAC address
    mac_parts = system_mac.replace("-", ":").lower().split(":")
    if len(mac_parts) != 6:
        mac_parts = ["00", "00", "00", "00", "00", "01"]

    # Local discriminator as 3 bytes
    discrim_hex = f"{local_discriminator:06x}"
    discrim_parts = [discrim_hex[i:i+2] for i in range(0, 6, 2)]

    # ESI: 03 + MAC (6 bytes) + Local Discriminator (3 bytes)
    esi_parts = ["03"] + mac_parts + discrim_parts
    esi = ":".join(esi_parts)
    short_esi = ":".join(discrim_parts)

    return ESIConfig(
        esi=esi,
        esi_type="type-3",
        short_esi=short_esi,
        description=f"Type-3 ESI (MAC-based, discriminator={local_discriminator})",
    )


def generate_es_import_rt(esi: str) -> str:
    """
    Generate ES-Import Route Target from ESI.

    ES-Import RT is derived from the ESI value (bytes 1-6).

    Args:
        esi: Full ESI value

    Returns:
        ES-Import Route Target string
    """
    # Extract bytes 1-6 from ESI (skip type byte)
    esi_parts = esi.split(":")
    if len(esi_parts) >= 7:
        rt_parts = esi_parts[1:7]
        return ":".join(rt_parts)
    return "00:00:00:00:00:00"


def calculate_multihoming(
    es_count: int = 1,
    peers_per_es: int = 2,
    mode: MultiHomingMode = MultiHomingMode.ACTIVE_ACTIVE,
    esi_type: ESIType = ESIType.TYPE_0,
    base_es_id: int = 1,
    system_mac: str = "00:00:00:00:00:01",
    lacp_port_key_start: int = 1,
    pe_loopback_base: str = "10.0.0.",
    interface_template: str = "Port-Channel{es_id}",
    df_algorithm: str = "modulus",
    vendors: list[str] | None = None,
) -> MultiHomingResult:
    """
    Calculate EVPN multi-homing parameters.

    This generates:
    - ESI values for each Ethernet Segment
    - LACP configuration for each PE
    - ES-Import Route Targets
    - Vendor-specific configurations

    Args:
        es_count: Number of Ethernet Segments
        peers_per_es: Number of PE peers per ES (typically 2)
        mode: Multi-homing redundancy mode
        esi_type: Type of ESI to generate
        base_es_id: Starting ES identifier
        system_mac: Base system MAC for ESI generation
        lacp_port_key_start: Starting LACP port key
        pe_loopback_base: Base IP for PE loopbacks
        interface_template: Template for interface names
        df_algorithm: DF election algorithm (modulus, hrw, preference)
        vendors: List of vendors to generate configs for

    Returns:
        MultiHomingResult with all configurations
    """
    ethernet_segments: list[EthernetSegment] = []
    pe_set: set[str] = set()

    for es_idx in range(es_count):
        es_id = base_es_id + es_idx
        lacp_port_key = lacp_port_key_start + es_idx

        # Generate ESI based on type
        if esi_type == ESIType.TYPE_0:
            esi_config = generate_esi_type0(es_id)
        elif esi_type == ESIType.TYPE_1:
            esi_config = generate_esi_type1(lacp_port_key, system_mac)
        else:  # TYPE_3
            esi_config = generate_esi_type3(system_mac, es_id)

        # Generate ES-Import RT
        es_import_rt = generate_es_import_rt(esi_config.esi)

        # Generate peer configurations
        peers: list[MultiHomingPeer] = []
        for peer_idx in range(peers_per_es):
            pe_name = f"PE-{es_idx * peers_per_es + peer_idx + 1}"
            pe_loopback = f"{pe_loopback_base}{es_idx * peers_per_es + peer_idx + 1}"
            interface = interface_template.format(es_id=es_id)

            lacp_config = LACPConfig(
                system_id=system_mac,
                system_priority=32768,  # Default priority
                port_key=lacp_port_key,
                mode=LACPMode.ACTIVE.value,
            )

            peers.append(MultiHomingPeer(
                name=pe_name,
                loopback_ip=pe_loopback,
                interface=interface,
                lacp_config=lacp_config,
            ))
            pe_set.add(pe_name)

        ethernet_segments.append(EthernetSegment(
            es_id=es_id,
            name=f"ES-{es_id}",
            esi_config=esi_config,
            mode=mode.value,
            peers=peers,
            df_election=df_algorithm,
            es_import_rt=es_import_rt,
        ))

    # Generate vendor configs if requested
    vendor_configs: dict[str, str] = {}
    if vendors:
        for vendor in vendors:
            vendor_lower = vendor.lower()
            if vendor_lower in ("arista", "eos"):
                vendor_configs["arista"] = _generate_arista_mh_config(
                    ethernet_segments, system_mac
                )
            elif vendor_lower in ("cisco", "nxos", "cisco_nxos"):
                vendor_configs["cisco_nxos"] = _generate_nxos_mh_config(
                    ethernet_segments, system_mac
                )
            elif vendor_lower in ("juniper", "junos"):
                vendor_configs["juniper"] = _generate_junos_mh_config(
                    ethernet_segments, system_mac
                )

    return MultiHomingResult(
        ethernet_segments=ethernet_segments,
        total_es_count=es_count,
        total_pe_count=len(pe_set),
        redundancy_mode=mode.value,
        lacp_system_mac=system_mac,
        vendor_configs=vendor_configs,
    )


def _generate_arista_mh_config(
    ethernet_segments: list[EthernetSegment],
    system_mac: str,
) -> str:
    """Generate Arista EOS multi-homing configuration."""
    lines = [
        "! Arista EOS EVPN Multi-homing Configuration",
        "!",
        "! LACP System Configuration",
        "lacp system-priority 32768",
        "!",
    ]

    for es in ethernet_segments:
        lines.extend([
            f"! Ethernet Segment: {es.name}",
            f"interface {es.peers[0].interface if es.peers else 'Port-Channel1'}",
            f"   description {es.name}",
            "   evpn ethernet-segment",
            f"      identifier {es.esi_config.esi.replace(':', ' ')}",
        ])

        if es.mode == "active-active":
            lines.append("      route-target import " + es.es_import_rt.replace(":", " "))
        else:
            lines.append("      designated-forwarder election algorithm preference")

        lines.extend([
            "   lacp system-id " + system_mac,
            "!",
        ])

    return "\n".join(lines)


def _generate_nxos_mh_config(
    ethernet_segments: list[EthernetSegment],
    system_mac: str,
) -> str:
    """Generate Cisco NX-OS multi-homing configuration."""
    lines = [
        "! Cisco NX-OS EVPN Multi-homing Configuration",
        "!",
        "evpn",
    ]

    for es in ethernet_segments:
        esi_parts = es.esi_config.esi.split(":")
        esi_formatted = ".".join([
            "".join(esi_parts[0:4]),
            "".join(esi_parts[4:8]),
            "".join(esi_parts[8:10]),
        ])

        lines.extend([
            f"  esi {esi_formatted}",
            f"    multi-homing {es.mode.replace('-', ' ')}",
            f"    df-election algorithm {es.df_election}",
            "!",
        ])

    for es in ethernet_segments:
        interface = es.peers[0].interface if es.peers else "port-channel1"
        lines.extend([
            f"interface {interface}",
            "  switchport",
            "  switchport mode trunk",
            f"  evpn ethernet-segment {es.es_id}",
            f"  lacp system-id {system_mac}",
            "!",
        ])

    return "\n".join(lines)


def _generate_junos_mh_config(
    ethernet_segments: list[EthernetSegment],
    system_mac: str,
) -> str:
    """Generate Juniper Junos multi-homing configuration."""
    lines = [
        "# Juniper Junos EVPN Multi-homing Configuration",
        "#",
        "set chassis aggregated-devices ethernet device-count 10",
        "",
    ]

    for es in ethernet_segments:
        interface = es.peers[0].interface if es.peers else "ae0"
        # Convert Port-Channel to ae
        if "Port-Channel" in interface:
            ae_num = interface.replace("Port-Channel", "")
            interface = f"ae{ae_num}"

        lines.extend([
            f"# Ethernet Segment: {es.name}",
            f"set interfaces {interface} esi {es.esi_config.esi.replace(':', ':')}",
        ])

        if es.mode == "active-active":
            lines.append(f"set interfaces {interface} esi all-active")
        else:
            lines.append(f"set interfaces {interface} esi single-active")

        lines.extend([
            f"set interfaces {interface} aggregated-ether-options lacp system-id {system_mac}",
            f"set interfaces {interface} aggregated-ether-options lacp active",
            "",
        ])

    return "\n".join(lines)
