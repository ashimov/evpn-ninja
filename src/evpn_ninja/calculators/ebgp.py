"""eBGP Underlay Calculator for leaf-spine fabrics (RFC 7938)."""

from dataclasses import dataclass
from enum import Enum
from ipaddress import IPv4Network


class ASNScheme(str, Enum):
    """ASN allocation scheme."""
    PRIVATE_2BYTE = "private-2byte"    # 64512-65534
    PRIVATE_4BYTE = "private-4byte"    # 4200000000-4294967294
    CUSTOM = "custom"                   # User-defined base


@dataclass
class DeviceASN:
    """ASN assignment for a device."""
    device_name: str
    device_role: str  # spine or leaf
    asn: int


@dataclass
class BGPSession:
    """BGP session between two devices."""
    device_a: str
    device_a_ip: str
    device_a_asn: int
    device_b: str
    device_b_ip: str
    device_b_asn: int


@dataclass
class EBGPUnderlayResult:
    """eBGP underlay calculation result."""
    scheme: str
    spine_count: int
    leaf_count: int
    base_asn: int
    spine_asn_range: str
    leaf_asn_range: str
    asn_assignments: list[DeviceASN]
    bgp_sessions: list[BGPSession]
    p2p_network: str
    total_sessions: int


# ASN ranges
PRIVATE_2BYTE_START = 64512
PRIVATE_2BYTE_END = 65534
PRIVATE_4BYTE_START = 4200000000
PRIVATE_4BYTE_END = 4294967294


def calculate_ebgp_underlay(
    spine_count: int = 2,
    leaf_count: int = 4,
    scheme: ASNScheme = ASNScheme.PRIVATE_4BYTE,
    base_asn: int | None = None,
    p2p_network: str = "10.0.100.0/22",
    spine_asn_same: bool = True,
) -> EBGPUnderlayResult:
    """
    Calculate eBGP underlay parameters for leaf-spine fabric.

    RFC 7938 recommends:
    - Each leaf has unique ASN (eBGP peering with spines)
    - Spines can share ASN or have unique ASNs
    - 4-byte private ASN range preferred for scale

    Args:
        spine_count: Number of spine switches
        leaf_count: Number of leaf switches
        scheme: ASN allocation scheme
        base_asn: Base ASN for custom scheme
        p2p_network: Network for P2P links (/31 per link)
        spine_asn_same: If True, all spines share same ASN

    Returns:
        EBGPUnderlayResult with ASN assignments and BGP sessions
    """
    # Determine base ASN
    if scheme == ASNScheme.PRIVATE_2BYTE:
        start_asn = base_asn if base_asn else PRIVATE_2BYTE_START
    elif scheme == ASNScheme.PRIVATE_4BYTE:
        start_asn = base_asn if base_asn else PRIVATE_4BYTE_START
    else:
        start_asn = base_asn if base_asn else 65000

    asn_assignments: list[DeviceASN] = []
    current_asn = start_asn

    # Assign ASNs to spines
    spine_asns: list[int] = []
    if spine_asn_same:
        # All spines share the same ASN
        spine_asn = current_asn
        for i in range(spine_count):
            asn_assignments.append(DeviceASN(
                device_name=f"spine-{i + 1}",
                device_role="spine",
                asn=spine_asn,
            ))
            spine_asns.append(spine_asn)
        current_asn += 1
    else:
        # Each spine has unique ASN
        for i in range(spine_count):
            asn_assignments.append(DeviceASN(
                device_name=f"spine-{i + 1}",
                device_role="spine",
                asn=current_asn,
            ))
            spine_asns.append(current_asn)
            current_asn += 1

    # Assign ASNs to leaves (each leaf has unique ASN)
    leaf_asns: list[int] = []
    leaf_start_asn = current_asn
    for i in range(leaf_count):
        asn_assignments.append(DeviceASN(
            device_name=f"leaf-{i + 1}",
            device_role="leaf",
            asn=current_asn,
        ))
        leaf_asns.append(current_asn)
        current_asn += 1

    # Generate BGP sessions and P2P IPs
    bgp_sessions: list[BGPSession] = []
    p2p_net = IPv4Network(p2p_network)
    p2p_subnets = list(p2p_net.subnets(new_prefix=31))

    link_idx = 0
    for leaf_idx in range(leaf_count):
        for spine_idx in range(spine_count):
            if link_idx < len(p2p_subnets):
                subnet = p2p_subnets[link_idx]
                hosts = list(subnet.hosts())
                if len(hosts) >= 2:
                    bgp_sessions.append(BGPSession(
                        device_a=f"leaf-{leaf_idx + 1}",
                        device_a_ip=str(hosts[0]),
                        device_a_asn=leaf_asns[leaf_idx],
                        device_b=f"spine-{spine_idx + 1}",
                        device_b_ip=str(hosts[1]),
                        device_b_asn=spine_asns[spine_idx],
                    ))
            link_idx += 1

    # Calculate ranges for display
    if spine_asn_same:
        spine_asn_range = str(start_asn)
    else:
        spine_asn_range = f"{start_asn}-{start_asn + spine_count - 1}"

    leaf_asn_range = f"{leaf_start_asn}-{leaf_start_asn + leaf_count - 1}"

    return EBGPUnderlayResult(
        scheme=scheme.value,
        spine_count=spine_count,
        leaf_count=leaf_count,
        base_asn=start_asn,
        spine_asn_range=spine_asn_range,
        leaf_asn_range=leaf_asn_range,
        asn_assignments=asn_assignments,
        bgp_sessions=bgp_sessions,
        p2p_network=p2p_network,
        total_sessions=len(bgp_sessions),
    )
