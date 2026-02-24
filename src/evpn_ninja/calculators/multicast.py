"""Multicast Groups Calculator for VXLAN BUM replication."""

from dataclasses import dataclass
from enum import Enum

from evpn_ninja.calculators._multicast_utils import calculate_multicast_group


class MulticastScheme(str, Enum):
    """Multicast group allocation scheme."""

    ONE_TO_ONE = "one-to-one"  # One multicast group per VNI
    SHARED = "shared"  # Shared groups for multiple VNIs
    RANGE_BASED = "range-based"  # VNI ranges map to groups


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
    if vni_count <= 0:
        raise ValueError(f"vni_count must be positive, got {vni_count}")
    if vni_start < 1 or vni_start > 16777215:
        raise ValueError(f"vni_start must be 1-16777215, got {vni_start}")
    if vni_start + vni_count - 1 > 16777215:
        raise ValueError(
            f"vni_start ({vni_start}) + vni_count ({vni_count}) - 1 = {vni_start + vni_count - 1} "
            f"exceeds maximum VNI 16777215"
        )

    mappings: list[MulticastMapping] = []

    if vnis_per_group <= 0:
        raise ValueError(f"vnis_per_group must be positive, got {vnis_per_group}")

    if scheme == MulticastScheme.ONE_TO_ONE:
        groups_used = vni_count
        for i in range(vni_count):
            vni = vni_start + i
            mcast_group = calculate_multicast_group(base_group, i)
            mappings.append(
                MulticastMapping(
                    vni=vni,
                    multicast_group=mcast_group,
                )
            )

    elif scheme == MulticastScheme.SHARED:
        groups_used = (vni_count + vnis_per_group - 1) // vnis_per_group
        for i in range(vni_count):
            vni = vni_start + i
            group_idx = i // vnis_per_group
            mcast_group = calculate_multicast_group(base_group, group_idx)
            mappings.append(
                MulticastMapping(
                    vni=vni,
                    multicast_group=mcast_group,
                )
            )

    elif scheme == MulticastScheme.RANGE_BASED:
        groups_used = (vni_count + vnis_per_group - 1) // vnis_per_group
        for group_idx in range(groups_used):
            range_start = vni_start + (group_idx * vnis_per_group)
            range_end = min(range_start + vnis_per_group - 1, vni_start + vni_count - 1)
            mcast_group = calculate_multicast_group(base_group, group_idx)

            for vni in range(range_start, range_end + 1):
                mappings.append(
                    MulticastMapping(
                        vni=vni,
                        multicast_group=mcast_group,
                        vni_range_start=range_start,
                        vni_range_end=range_end,
                    )
                )
    else:
        groups_used = 0

    # PIM configuration
    pim_config = None
    if rp_address:
        group_range = f"{base_group}/24"  # Simplified group range

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
        "Group Range": f"{base_group} - {calculate_multicast_group(base_group, groups_used - 1) if groups_used > 0 else base_group}",
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
