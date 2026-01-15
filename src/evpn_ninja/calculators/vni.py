"""VNI Allocation Calculator."""

from dataclasses import dataclass
from enum import Enum


class VNIScheme(str, Enum):
    """VNI allocation scheme."""
    VLAN_BASED = "vlan-based"      # VNI = base_vni + vlan_id
    TENANT_BASED = "tenant-based"  # VNI = tenant_id * 10000 + vlan_id
    SEQUENTIAL = "sequential"      # VNI = base_vni + index
    CUSTOM = "custom"              # VNI = base_vni + (vlan_id * multiplier)


@dataclass
class VNIEntry:
    """Single VNI allocation entry."""
    vlan_id: int
    vni_decimal: int
    vni_hex: str
    multicast_group: str


@dataclass
class VNIAllocationResult:
    """VNI allocation result."""
    scheme: str
    base_vni: int
    tenant_id: int | None
    start_vlan: int
    count: int
    multicast_base: str
    entries: list[VNIEntry]


def _calculate_multicast_group(base: str, index: int) -> str:
    """
    Calculate multicast group address for a VNI.

    Uses the 239.0.0.0/8 range for multicast-based BUM replication.

    Args:
        base: Base multicast address (e.g., "239.1.1.0")
        index: VNI index offset

    Returns:
        Calculated multicast group address

    Raises:
        ValueError: If the calculated address is outside valid multicast range
    """
    octets = [int(o) for o in base.split(".")]

    # Validate base is in multicast range (224.0.0.0 - 239.255.255.255)
    if octets[0] < 224 or octets[0] > 239:
        raise ValueError(f"Base address {base} is not in multicast range (224.x.x.x - 239.x.x.x)")

    # Add index to the last three octets (24-bit address space)
    total = (octets[1] << 16) + (octets[2] << 8) + octets[3] + index

    # Check for overflow (max 24-bit value)
    if total > 0xFFFFFF:
        raise ValueError(
            f"Multicast address overflow at index {index}. "
            f"Base {base} + {index} exceeds available 24-bit address space"
        )

    octets[3] = total & 0xFF
    octets[2] = (total >> 8) & 0xFF
    octets[1] = (total >> 16) & 0xFF
    return f"{octets[0]}.{octets[1]}.{octets[2]}.{octets[3]}"


def calculate_vni_allocation(
    scheme: VNIScheme = VNIScheme.VLAN_BASED,
    base_vni: int = 10000,
    tenant_id: int = 1,
    start_vlan: int = 10,
    count: int = 10,
    multicast_base: str = "239.1.1.0",
    multiplier: int = 1,
) -> VNIAllocationResult:
    """
    Calculate VNI allocation based on the selected scheme.

    Schemes:
    - VLAN_BASED: VNI = base_vni + vlan_id
      Example: base=10000, vlan=10 -> VNI=10010

    - TENANT_BASED: VNI = tenant_id * 10000 + vlan_id
      Example: tenant=5, vlan=10 -> VNI=50010

    - SEQUENTIAL: VNI = base_vni + index
      Example: base=10000, index=0,1,2 -> VNI=10000,10001,10002

    - CUSTOM: VNI = base_vni + (vlan_id * multiplier)
      Example: base=10000, vlan=10, mult=100 -> VNI=11000

    Args:
        scheme: Allocation scheme to use
        base_vni: Base VNI number (for VLAN_BASED, SEQUENTIAL, CUSTOM)
        tenant_id: Tenant identifier (for TENANT_BASED)
        start_vlan: Starting VLAN ID
        count: Number of VNIs to allocate
        multicast_base: Base multicast address for BUM replication
        multiplier: Multiplier for CUSTOM scheme

    Returns:
        VNIAllocationResult with the allocation table
    """
    entries: list[VNIEntry] = []

    for i in range(count):
        vlan_id = start_vlan + i

        # Calculate VNI based on scheme
        if scheme == VNIScheme.VLAN_BASED:
            vni = base_vni + vlan_id
        elif scheme == VNIScheme.TENANT_BASED:
            vni = (tenant_id * 10000) + vlan_id
        elif scheme == VNIScheme.SEQUENTIAL:
            vni = base_vni + i
        elif scheme == VNIScheme.CUSTOM:
            vni = base_vni + (vlan_id * multiplier)
        else:
            vni = base_vni + vlan_id  # Default to VLAN_BASED

        # VNI must be in valid range (1 - 16777215 / 0xFFFFFF)
        if vni < 1 or vni > 16777215:
            raise ValueError(
                f"VNI {vni} out of valid range (1-16777215). "
                f"Check base_vni={base_vni}, vlan_id={vlan_id}, scheme={scheme.value}"
            )

        # Calculate multicast group
        mcast_group = _calculate_multicast_group(multicast_base, i)

        entries.append(VNIEntry(
            vlan_id=vlan_id,
            vni_decimal=vni,
            vni_hex=f"0x{vni:06X}",
            multicast_group=mcast_group,
        ))

    return VNIAllocationResult(
        scheme=scheme.value,
        base_vni=base_vni,
        tenant_id=tenant_id if scheme == VNIScheme.TENANT_BASED else None,
        start_vlan=start_vlan,
        count=count,
        multicast_base=multicast_base,
        entries=entries,
    )
