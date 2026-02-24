"""Shared multicast group calculation utility.

Used by both vni.py and multicast.py to ensure consistent behavior.
"""

from ipaddress import IPv4Address


def calculate_multicast_group(base: str, offset: int) -> str:
    """
    Calculate multicast group address with offset.

    Uses the full 32-bit address for correct overflow detection against
    the multicast range boundary (239.255.255.255).

    Args:
        base: Base multicast address (e.g., "239.1.1.0")
        offset: Offset from the base address

    Returns:
        Calculated multicast group address

    Raises:
        ValueError: If base is not multicast or result exceeds 239.255.255.255
    """
    base_ip = IPv4Address(base)

    # Validate base is in multicast range (224.0.0.0 - 239.255.255.255)
    if not base_ip.is_multicast:
        raise ValueError(
            f"Base address {base} is not in multicast range (224.0.0.0 - 239.255.255.255)"
        )

    base_int = int(base_ip)
    new_int = base_int + offset

    # Ensure we stay in valid multicast range
    max_multicast = int(IPv4Address("239.255.255.255"))
    if new_int > max_multicast:
        raise ValueError(
            f"Multicast address overflow: base {base} + offset {offset} exceeds 239.255.255.255"
        )

    return str(IPv4Address(new_int))
