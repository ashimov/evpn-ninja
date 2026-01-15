"""Multicast Groups Calculator for VXLAN BUM replication."""

from dataclasses import dataclass
from enum import Enum
from ipaddress import IPv4Address


class MulticastScheme(str, Enum):
    """Multicast group allocation scheme."""
    ONE_TO_ONE = "one-to-one"      # One multicast group per VNI
    SHARED = "shared"              # Shared groups for multiple VNIs
    RANGE_BASED = "range-based"    # VNI ranges map to groups


@dataclass
class MulticastMapping:
    """VNI to multicast group mapping."""
    vni: int
    multicast_group: str
    vni_range_start: int | None = None
    vni_range_end: int | None = None


@dataclass
class MulticastPIMConfig:
    """PIM configuration for multicast underlay."""
    rp_address: str
    rp_group_range: str
    anycast_rp: bool
    anycast_rp_peers: list[str] | None


@dataclass
class MulticastResult:
    """Multicast calculation result."""
    scheme: str
    base_group: str
    vni_start: int
    vni_count: int
    groups_used: int
    mappings: list[MulticastMapping]
    pim_config: MulticastPIMConfig | None
    underlay_requirements: dict[str, str]


def _calculate_multicast_group(base: str, offset: int) -> str:
    """Calculate multicast group address with offset."""
    base_ip = IPv4Address(base)
    base_int = int(base_ip)
    new_int = base_int + offset

    # Ensure we stay in valid multicast range (224.0.0.0 - 239.255.255.255)
    if new_int > int(IPv4Address("239.255.255.255")):
        # Wrap around within the range
        new_int = int(IPv4Address("239.0.0.0")) + (new_int - int(IPv4Address("239.255.255.255")))

    return str(IPv4Address(new_int))


def calculate_multicast_groups(
    vni_start: int = 10000,
    vni_count: int = 100,
    scheme: MulticastScheme = MulticastScheme.ONE_TO_ONE,
    base_group: str = "239.1.1.0",
    vnis_per_group: int = 10,
    rp_address: str | None = None,
    anycast_rp: bool = False,
    anycast_rp_peers: list[str] | None = None,
) -> MulticastResult:
    """
    Calculate multicast group mappings for VXLAN BUM replication.

    Schemes:
    - ONE_TO_ONE: Each VNI gets unique multicast group
    - SHARED: Multiple VNIs share a multicast group
    - RANGE_BASED: VNI ranges map to specific groups

    Args:
        vni_start: Starting VNI number
        vni_count: Number of VNIs to allocate
        scheme: Multicast allocation scheme
        base_group: Base multicast group address (239.x.x.x recommended)
        vnis_per_group: VNIs per group for SHARED/RANGE_BASED schemes
        rp_address: PIM Rendezvous Point address
        anycast_rp: Use Anycast RP for redundancy
        anycast_rp_peers: List of Anycast RP peer addresses

    Returns:
        MulticastResult with mappings and configuration
    """
    mappings: list[MulticastMapping] = []
    groups_used = 0

    if scheme == MulticastScheme.ONE_TO_ONE:
        # Each VNI gets unique multicast group
        for i in range(vni_count):
            vni = vni_start + i
            mcast_group = _calculate_multicast_group(base_group, i)
            mappings.append(MulticastMapping(
                vni=vni,
                multicast_group=mcast_group,
            ))
            groups_used += 1

    elif scheme == MulticastScheme.SHARED:
        # Multiple VNIs share groups
        current_group_idx = 0
        for i in range(vni_count):
            vni = vni_start + i
            group_idx = i // vnis_per_group
            mcast_group = _calculate_multicast_group(base_group, group_idx)
            mappings.append(MulticastMapping(
                vni=vni,
                multicast_group=mcast_group,
            ))
            if group_idx >= groups_used:
                groups_used = group_idx + 1

    elif scheme == MulticastScheme.RANGE_BASED:
        # VNI ranges map to groups
        for group_idx in range((vni_count + vnis_per_group - 1) // vnis_per_group):
            range_start = vni_start + (group_idx * vnis_per_group)
            range_end = min(range_start + vnis_per_group - 1, vni_start + vni_count - 1)
            mcast_group = _calculate_multicast_group(base_group, group_idx)

            for vni in range(range_start, range_end + 1):
                mappings.append(MulticastMapping(
                    vni=vni,
                    multicast_group=mcast_group,
                    vni_range_start=range_start,
                    vni_range_end=range_end,
                ))
            groups_used += 1

    # PIM configuration
    pim_config = None
    if rp_address:
        # Calculate group range
        last_group = _calculate_multicast_group(base_group, groups_used - 1)
        group_range = f"{base_group}/24"  # Simplified, could be more precise

        pim_config = MulticastPIMConfig(
            rp_address=rp_address,
            rp_group_range=group_range,
            anycast_rp=anycast_rp,
            anycast_rp_peers=anycast_rp_peers,
        )

    # Underlay requirements
    underlay_requirements = {
        "PIM Mode": "PIM-SM (Sparse Mode) or PIM-BIDIR",
        "IGMP Version": "IGMPv2 or IGMPv3",
        "RP Placement": "On spine switches (recommended)",
        "MTU": "Standard (no VXLAN overhead on underlay multicast)",
        "Groups Required": str(groups_used),
        "Group Range": f"{base_group} - {_calculate_multicast_group(base_group, groups_used - 1)}",
    }

    return MulticastResult(
        scheme=scheme.value,
        base_group=base_group,
        vni_start=vni_start,
        vni_count=vni_count,
        groups_used=groups_used,
        mappings=mappings,
        pim_config=pim_config,
        underlay_requirements=underlay_requirements,
    )
