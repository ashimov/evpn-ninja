"""MTU Calculator for VXLAN encapsulation."""

from dataclasses import dataclass
from enum import Enum


class UnderlayType(str, Enum):
    """Underlay network type."""
    IPV4 = "ipv4"
    IPV6 = "ipv6"


@dataclass
class LayerOverhead:
    """Overhead for a single layer."""
    name: str
    size: int
    description: str


@dataclass
class MTUResult:
    """MTU calculation result."""
    payload_size: int
    underlay_type: str
    outer_vlan_tags: int
    inner_vlan_tags: int
    layers: list[LayerOverhead]
    total_overhead: int
    total_frame_size: int
    required_mtu: int
    recommended_mtu: int


# Constants for layer sizes
ETHERNET_HEADER = 14  # Dst MAC (6) + Src MAC (6) + EtherType (2)
VLAN_TAG = 4          # 802.1Q tag
IPV4_HEADER = 20      # Standard IPv4 header
IPV6_HEADER = 40      # Standard IPv6 header
UDP_HEADER = 8        # UDP header
VXLAN_HEADER = 8      # VXLAN header
FCS = 4               # Frame Check Sequence


def calculate_mtu(
    payload_size: int = 1500,
    underlay_type: UnderlayType = UnderlayType.IPV4,
    outer_vlan_tags: int = 0,
    inner_vlan_tags: int = 0,
) -> MTUResult:
    """
    Calculate required MTU for VXLAN encapsulation.

    VXLAN Frame Structure:
    +------------------+
    | Outer Ethernet   |  14 bytes (+ 4 per VLAN tag)
    +------------------+
    | Outer IP         |  20 bytes (IPv4) or 40 bytes (IPv6)
    +------------------+
    | UDP              |  8 bytes (dst port 4789)
    +------------------+
    | VXLAN Header     |  8 bytes
    +------------------+
    | Inner Ethernet   |  14 bytes (+ 4 per VLAN tag)
    +------------------+
    | Inner Payload    |  Variable (original L3 packet)
    +------------------+
    | FCS              |  4 bytes
    +------------------+

    Args:
        payload_size: Size of the inner payload (default 1500)
        underlay_type: IPv4 or IPv6 underlay
        outer_vlan_tags: Number of VLAN tags on outer frame (0-2)
        inner_vlan_tags: Number of VLAN tags on inner frame (0-2)

    Returns:
        MTUResult with detailed breakdown
    """
    layers: list[LayerOverhead] = []

    # Outer Ethernet
    outer_eth_size = ETHERNET_HEADER + (outer_vlan_tags * VLAN_TAG)
    outer_eth_desc = "Dst MAC + Src MAC + EtherType"
    if outer_vlan_tags > 0:
        outer_eth_desc += f" + {outer_vlan_tags} VLAN tag(s)"
    layers.append(LayerOverhead("Outer Ethernet", outer_eth_size, outer_eth_desc))

    # Outer IP
    if underlay_type == UnderlayType.IPV4:
        layers.append(LayerOverhead("Outer IPv4", IPV4_HEADER, "Standard IPv4 header"))
    else:
        layers.append(LayerOverhead("Outer IPv6", IPV6_HEADER, "Standard IPv6 header"))

    # UDP
    layers.append(LayerOverhead("UDP", UDP_HEADER, "Source port + Dest port (4789) + Length + Checksum"))

    # VXLAN Header
    layers.append(LayerOverhead("VXLAN Header", VXLAN_HEADER, "Flags + Reserved + VNI + Reserved"))

    # Inner Ethernet
    inner_eth_size = ETHERNET_HEADER + (inner_vlan_tags * VLAN_TAG)
    inner_eth_desc = "Dst MAC + Src MAC + EtherType"
    if inner_vlan_tags > 0:
        inner_eth_desc += f" + {inner_vlan_tags} VLAN tag(s)"
    layers.append(LayerOverhead("Inner Ethernet", inner_eth_size, inner_eth_desc))

    # Inner Payload
    layers.append(LayerOverhead("Inner Payload", payload_size, "Original L3 packet (IP + data)"))

    # Calculate totals
    total_overhead = sum(layer.size for layer in layers[:-1])  # Exclude payload
    total_frame_size = sum(layer.size for layer in layers)

    # Required MTU is the size that the underlay needs to carry
    # This is from outer IP header to the end of the inner frame
    ip_header_size = IPV4_HEADER if underlay_type == UnderlayType.IPV4 else IPV6_HEADER
    required_mtu = (
        ip_header_size +
        UDP_HEADER +
        VXLAN_HEADER +
        ETHERNET_HEADER + (inner_vlan_tags * VLAN_TAG) +
        payload_size
    )

    # Recommended MTU adds some headroom
    recommended_mtu = ((required_mtu + 63) // 64) * 64  # Round up to nearest 64

    return MTUResult(
        payload_size=payload_size,
        underlay_type=underlay_type.value,
        outer_vlan_tags=outer_vlan_tags,
        inner_vlan_tags=inner_vlan_tags,
        layers=layers,
        total_overhead=total_overhead,
        total_frame_size=total_frame_size,
        required_mtu=required_mtu,
        recommended_mtu=recommended_mtu,
    )
