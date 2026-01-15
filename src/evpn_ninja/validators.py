"""Input validators for IP addresses, networks, and other parameters.

This module provides validation functions for all user inputs including
IP addresses, CIDR networks, ASN numbers, VNI ranges, and multicast groups.
"""

from ipaddress import (
    IPv4Address,
    IPv4Network,
    IPv6Address,
    IPv6Network,
    ip_address,
    ip_network,
)
from typing import TypeVar

import typer


class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, field: str, value: str, reason: str) -> None:
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"Invalid {field}: {value} - {reason}")


# Type aliases
IPAddress = IPv4Address | IPv6Address
IPNetwork = IPv4Network | IPv6Network
T = TypeVar("T")


def validate_ipv4_address(value: str, field_name: str = "IP address") -> IPv4Address:
    """
    Validate and parse an IPv4 address.

    Args:
        value: String representation of IPv4 address
        field_name: Name of the field for error messages

    Returns:
        Validated IPv4Address object

    Raises:
        ValidationError: If the address is invalid
    """
    try:
        addr = IPv4Address(value)
        return addr
    except ValueError as e:
        raise ValidationError(field_name, value, str(e)) from e


def validate_ipv6_address(value: str, field_name: str = "IP address") -> IPv6Address:
    """
    Validate and parse an IPv6 address.

    Args:
        value: String representation of IPv6 address
        field_name: Name of the field for error messages

    Returns:
        Validated IPv6Address object

    Raises:
        ValidationError: If the address is invalid
    """
    try:
        addr = IPv6Address(value)
        return addr
    except ValueError as e:
        raise ValidationError(field_name, value, str(e)) from e


def validate_ip_address(value: str, field_name: str = "IP address") -> IPAddress:
    """
    Validate and parse an IP address (IPv4 or IPv6).

    Args:
        value: String representation of IP address
        field_name: Name of the field for error messages

    Returns:
        Validated IPv4Address or IPv6Address object

    Raises:
        ValidationError: If the address is invalid
    """
    try:
        return ip_address(value)
    except ValueError as e:
        raise ValidationError(field_name, value, str(e)) from e


def validate_ipv4_network(
    value: str, field_name: str = "network", strict: bool = False
) -> IPv4Network:
    """
    Validate and parse an IPv4 network in CIDR notation.

    Args:
        value: String representation of IPv4 network (e.g., "10.0.0.0/24")
        field_name: Name of the field for error messages
        strict: If True, host bits must be zero

    Returns:
        Validated IPv4Network object

    Raises:
        ValidationError: If the network is invalid
    """
    try:
        return IPv4Network(value, strict=strict)
    except ValueError as e:
        raise ValidationError(field_name, value, str(e)) from e


def validate_ipv6_network(
    value: str, field_name: str = "network", strict: bool = False
) -> IPv6Network:
    """
    Validate and parse an IPv6 network in CIDR notation.

    Args:
        value: String representation of IPv6 network
        field_name: Name of the field for error messages
        strict: If True, host bits must be zero

    Returns:
        Validated IPv6Network object

    Raises:
        ValidationError: If the network is invalid
    """
    try:
        return IPv6Network(value, strict=strict)
    except ValueError as e:
        raise ValidationError(field_name, value, str(e)) from e


def validate_network(
    value: str, field_name: str = "network", strict: bool = False
) -> IPNetwork:
    """
    Validate and parse an IP network (IPv4 or IPv6) in CIDR notation.

    Args:
        value: String representation of IP network
        field_name: Name of the field for error messages
        strict: If True, host bits must be zero

    Returns:
        Validated IPv4Network or IPv6Network object

    Raises:
        ValidationError: If the network is invalid
    """
    try:
        return ip_network(value, strict=strict)
    except ValueError as e:
        raise ValidationError(field_name, value, str(e)) from e


def validate_multicast_address(
    value: str, field_name: str = "multicast address"
) -> IPv4Address:
    """
    Validate an IPv4 multicast address (224.0.0.0 - 239.255.255.255).

    Args:
        value: String representation of multicast address
        field_name: Name of the field for error messages

    Returns:
        Validated IPv4Address object

    Raises:
        ValidationError: If the address is not a valid multicast address
    """
    addr = validate_ipv4_address(value, field_name)

    if not addr.is_multicast:
        raise ValidationError(
            field_name,
            value,
            "Must be in multicast range (224.0.0.0 - 239.255.255.255)",
        )

    return addr


def validate_asn(
    value: int,
    field_name: str = "ASN",
    allow_private: bool = True,
    allow_reserved: bool = False,
) -> int:
    """
    Validate a BGP Autonomous System Number.

    Args:
        value: ASN value to validate
        field_name: Name of the field for error messages
        allow_private: Allow private ASN ranges
        allow_reserved: Allow reserved ASN ranges

    Returns:
        Validated ASN value

    Raises:
        ValidationError: If the ASN is invalid
    """
    # ASN ranges
    # 0: Reserved
    # 1-64495: Public 2-byte
    # 64496-64511: Reserved for documentation
    # 64512-65534: Private 2-byte
    # 65535: Reserved
    # 65536-4199999999: Public 4-byte
    # 4200000000-4294967294: Private 4-byte
    # 4294967295: Reserved

    if value < 0 or value > 4294967295:
        raise ValidationError(field_name, str(value), "ASN must be 0-4294967295")

    reserved_ranges = [
        (0, 0, "Reserved"),
        (64496, 64511, "Reserved for documentation"),
        (65535, 65535, "Reserved"),
        (4294967295, 4294967295, "Reserved"),
    ]

    private_ranges = [
        (64512, 65534, "Private 2-byte"),
        (4200000000, 4294967294, "Private 4-byte"),
    ]

    for start, end, desc in reserved_ranges:
        if start <= value <= end:
            if not allow_reserved:
                raise ValidationError(
                    field_name, str(value), f"ASN {value} is {desc}"
                )

    is_private = False
    for start, end, _ in private_ranges:
        if start <= value <= end:
            is_private = True
            break

    if is_private and not allow_private:
        raise ValidationError(
            field_name, str(value), f"Private ASN {value} not allowed"
        )

    return value


def validate_vni(value: int, field_name: str = "VNI") -> int:
    """
    Validate a VXLAN Network Identifier.

    VNI must be in range 1-16777215 (24-bit).

    Args:
        value: VNI value to validate
        field_name: Name of the field for error messages

    Returns:
        Validated VNI value

    Raises:
        ValidationError: If the VNI is invalid
    """
    if value < 1 or value > 16777215:
        raise ValidationError(
            field_name, str(value), "VNI must be in range 1-16777215"
        )
    return value


def validate_vlan_id(value: int, field_name: str = "VLAN ID") -> int:
    """
    Validate a VLAN ID.

    VLAN ID must be in range 1-4094.

    Args:
        value: VLAN ID to validate
        field_name: Name of the field for error messages

    Returns:
        Validated VLAN ID

    Raises:
        ValidationError: If the VLAN ID is invalid
    """
    if value < 1 or value > 4094:
        raise ValidationError(
            field_name, str(value), "VLAN ID must be in range 1-4094"
        )
    return value


def validate_port(value: int, field_name: str = "port") -> int:
    """
    Validate a TCP/UDP port number.

    Port must be in range 1-65535.

    Args:
        value: Port number to validate
        field_name: Name of the field for error messages

    Returns:
        Validated port number

    Raises:
        ValidationError: If the port is invalid
    """
    if value < 1 or value > 65535:
        raise ValidationError(
            field_name, str(value), "Port must be in range 1-65535"
        )
    return value


def validate_mtu(value: int, field_name: str = "MTU") -> int:
    """
    Validate an MTU value.

    MTU must be in range 68-65535 (minimum IPv4 MTU to max).

    Args:
        value: MTU value to validate
        field_name: Name of the field for error messages

    Returns:
        Validated MTU value

    Raises:
        ValidationError: If the MTU is invalid
    """
    if value < 68 or value > 65535:
        raise ValidationError(
            field_name, str(value), "MTU must be in range 68-65535"
        )
    return value


def validate_positive_int(
    value: int, field_name: str = "value", max_value: int | None = None
) -> int:
    """
    Validate a positive integer.

    Args:
        value: Integer to validate
        field_name: Name of the field for error messages
        max_value: Maximum allowed value (optional)

    Returns:
        Validated integer

    Raises:
        ValidationError: If the value is invalid
    """
    if value < 1:
        raise ValidationError(field_name, str(value), "Must be a positive integer")

    if max_value is not None and value > max_value:
        raise ValidationError(
            field_name, str(value), f"Must be at most {max_value}"
        )

    return value


def networks_overlap(net1: IPNetwork, net2: IPNetwork) -> bool:
    """
    Check if two IP networks overlap.

    Args:
        net1: First network
        net2: Second network

    Returns:
        True if networks overlap, False otherwise
    """
    return net1.overlaps(net2)


def validate_no_overlap(
    networks: list[tuple[str, IPNetwork]], field_name: str = "networks"
) -> None:
    """
    Validate that a list of networks do not overlap.

    Args:
        networks: List of (name, network) tuples
        field_name: Name for error messages

    Raises:
        ValidationError: If any networks overlap
    """
    for i, (name1, net1) in enumerate(networks):
        for name2, net2 in networks[i + 1 :]:
            if networks_overlap(net1, net2):
                raise ValidationError(
                    field_name,
                    f"{name1} ({net1}) and {name2} ({net2})",
                    "Networks overlap",
                )


# Typer callback validators for CLI
def ip_address_callback(value: str) -> str:
    """Typer callback for IP address validation."""
    if value:
        try:
            validate_ip_address(value)
        except ValidationError as e:
            raise typer.BadParameter(str(e)) from e
    return value


def ipv4_address_callback(value: str) -> str:
    """Typer callback for IPv4 address validation."""
    if value:
        try:
            validate_ipv4_address(value)
        except ValidationError as e:
            raise typer.BadParameter(str(e)) from e
    return value


def network_callback(value: str) -> str:
    """Typer callback for network validation."""
    if value:
        try:
            validate_network(value)
        except ValidationError as e:
            raise typer.BadParameter(str(e)) from e
    return value


def multicast_callback(value: str) -> str:
    """Typer callback for multicast address validation."""
    if value:
        try:
            validate_multicast_address(value)
        except ValidationError as e:
            raise typer.BadParameter(str(e)) from e
    return value
