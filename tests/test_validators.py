"""Tests for validators module."""

from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network

import pytest
import typer

from evpn_ninja.validators import (
    ValidationError,
    ip_address_callback,
    ipv4_address_callback,
    multicast_callback,
    network_callback,
    networks_overlap,
    validate_asn,
    validate_ip_address,
    validate_ipv4_address,
    validate_ipv4_network,
    validate_ipv6_address,
    validate_ipv6_network,
    validate_mtu,
    validate_multicast_address,
    validate_network,
    validate_no_overlap,
    validate_port,
    validate_positive_int,
    validate_vlan_id,
    validate_vni,
)


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_validation_error_attributes(self) -> None:
        """Test ValidationError stores field, value, and reason."""
        err = ValidationError("IP address", "invalid", "not a valid address")
        assert err.field == "IP address"
        assert err.value == "invalid"
        assert err.reason == "not a valid address"

    def test_validation_error_message(self) -> None:
        """Test ValidationError string representation."""
        err = ValidationError("VNI", "999999999", "out of range")
        assert "Invalid VNI" in str(err)
        assert "999999999" in str(err)
        assert "out of range" in str(err)


class TestIPv4AddressValidation:
    """Tests for IPv4 address validation."""

    def test_valid_ipv4_address(self) -> None:
        """Test valid IPv4 addresses."""
        assert validate_ipv4_address("192.168.1.1") == IPv4Address("192.168.1.1")
        assert validate_ipv4_address("10.0.0.1") == IPv4Address("10.0.0.1")
        assert validate_ipv4_address("0.0.0.0") == IPv4Address("0.0.0.0")
        assert validate_ipv4_address("255.255.255.255") == IPv4Address("255.255.255.255")

    def test_invalid_ipv4_address(self) -> None:
        """Test invalid IPv4 addresses raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_ipv4_address("256.1.1.1")
        assert exc_info.value.field == "IP address"

        with pytest.raises(ValidationError):
            validate_ipv4_address("not-an-ip")

        with pytest.raises(ValidationError):
            validate_ipv4_address("192.168.1")

    def test_ipv6_rejected_as_ipv4(self) -> None:
        """Test IPv6 address rejected when IPv4 expected."""
        with pytest.raises(ValidationError):
            validate_ipv4_address("::1")

    def test_custom_field_name(self) -> None:
        """Test custom field name in error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_ipv4_address("invalid", field_name="loopback")
        assert exc_info.value.field == "loopback"


class TestIPv6AddressValidation:
    """Tests for IPv6 address validation."""

    def test_valid_ipv6_address(self) -> None:
        """Test valid IPv6 addresses."""
        assert validate_ipv6_address("::1") == IPv6Address("::1")
        assert validate_ipv6_address("2001:db8::1") == IPv6Address("2001:db8::1")
        assert validate_ipv6_address("fe80::1") == IPv6Address("fe80::1")

    def test_invalid_ipv6_address(self) -> None:
        """Test invalid IPv6 addresses raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_ipv6_address("not-an-ip")

        with pytest.raises(ValidationError):
            validate_ipv6_address("192.168.1.1")  # IPv4 rejected

    def test_custom_field_name(self) -> None:
        """Test custom field name in error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_ipv6_address("invalid", field_name="source")
        assert exc_info.value.field == "source"


class TestIPAddressValidation:
    """Tests for generic IP address validation (IPv4 or IPv6)."""

    def test_valid_ipv4(self) -> None:
        """Test valid IPv4 addresses."""
        result = validate_ip_address("192.168.1.1")
        assert isinstance(result, IPv4Address)

    def test_valid_ipv6(self) -> None:
        """Test valid IPv6 addresses."""
        result = validate_ip_address("::1")
        assert isinstance(result, IPv6Address)

    def test_invalid_address(self) -> None:
        """Test invalid addresses raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_ip_address("not-valid")


class TestIPv4NetworkValidation:
    """Tests for IPv4 network validation."""

    def test_valid_network(self) -> None:
        """Test valid IPv4 networks."""
        assert validate_ipv4_network("10.0.0.0/8") == IPv4Network("10.0.0.0/8")
        assert validate_ipv4_network("192.168.1.0/24") == IPv4Network("192.168.1.0/24")
        assert validate_ipv4_network("0.0.0.0/0") == IPv4Network("0.0.0.0/0")

    def test_host_bits_non_strict(self) -> None:
        """Test non-strict mode allows host bits."""
        result = validate_ipv4_network("192.168.1.5/24", strict=False)
        assert result == IPv4Network("192.168.1.0/24")

    def test_host_bits_strict(self) -> None:
        """Test strict mode rejects host bits."""
        with pytest.raises(ValidationError):
            validate_ipv4_network("192.168.1.5/24", strict=True)

    def test_invalid_network(self) -> None:
        """Test invalid networks raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_ipv4_network("not-a-network")

        with pytest.raises(ValidationError):
            validate_ipv4_network("300.168.1.0/24")  # Invalid octet


class TestIPv6NetworkValidation:
    """Tests for IPv6 network validation."""

    def test_valid_network(self) -> None:
        """Test valid IPv6 networks."""
        assert validate_ipv6_network("2001:db8::/32") == IPv6Network("2001:db8::/32")
        assert validate_ipv6_network("::/0") == IPv6Network("::/0")

    def test_host_bits_non_strict(self) -> None:
        """Test non-strict mode allows host bits."""
        result = validate_ipv6_network("2001:db8::1/64", strict=False)
        assert result == IPv6Network("2001:db8::/64")

    def test_host_bits_strict(self) -> None:
        """Test strict mode rejects host bits."""
        with pytest.raises(ValidationError):
            validate_ipv6_network("2001:db8::1/64", strict=True)

    def test_invalid_network(self) -> None:
        """Test invalid networks raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_ipv6_network("not-a-network")


class TestNetworkValidation:
    """Tests for generic network validation (IPv4 or IPv6)."""

    def test_valid_ipv4_network(self) -> None:
        """Test valid IPv4 networks."""
        result = validate_network("10.0.0.0/8")
        assert isinstance(result, IPv4Network)

    def test_valid_ipv6_network(self) -> None:
        """Test valid IPv6 networks."""
        result = validate_network("2001:db8::/32")
        assert isinstance(result, IPv6Network)

    def test_invalid_network(self) -> None:
        """Test invalid networks raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_network("invalid")


class TestMulticastAddressValidation:
    """Tests for multicast address validation."""

    def test_valid_multicast_addresses(self) -> None:
        """Test valid multicast addresses."""
        assert validate_multicast_address("224.0.0.1") == IPv4Address("224.0.0.1")
        assert validate_multicast_address("239.255.255.255") == IPv4Address("239.255.255.255")
        assert validate_multicast_address("239.1.1.0") == IPv4Address("239.1.1.0")

    def test_non_multicast_rejected(self) -> None:
        """Test non-multicast addresses are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            validate_multicast_address("192.168.1.1")
        assert "multicast range" in exc_info.value.reason

        with pytest.raises(ValidationError):
            validate_multicast_address("10.0.0.1")

    def test_invalid_address(self) -> None:
        """Test invalid addresses are rejected."""
        with pytest.raises(ValidationError):
            validate_multicast_address("not-an-ip")


class TestASNValidation:
    """Tests for ASN validation."""

    def test_valid_public_asn(self) -> None:
        """Test valid public ASNs."""
        assert validate_asn(1) == 1
        assert validate_asn(64495) == 64495
        assert validate_asn(65536) == 65536
        assert validate_asn(4199999999) == 4199999999

    def test_valid_private_asn(self) -> None:
        """Test valid private ASNs when allowed."""
        assert validate_asn(64512) == 64512
        assert validate_asn(65534) == 65534
        assert validate_asn(4200000000) == 4200000000
        assert validate_asn(4294967294) == 4294967294

    def test_private_asn_rejected_when_not_allowed(self) -> None:
        """Test private ASNs rejected when not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            validate_asn(64512, allow_private=False)
        assert "Private ASN" in exc_info.value.reason

        with pytest.raises(ValidationError):
            validate_asn(4200000000, allow_private=False)

    def test_reserved_asn_rejected(self) -> None:
        """Test reserved ASNs are rejected."""
        with pytest.raises(ValidationError):
            validate_asn(0, allow_reserved=False)

        with pytest.raises(ValidationError):
            validate_asn(65535, allow_reserved=False)

        with pytest.raises(ValidationError):
            validate_asn(64500, allow_reserved=False)  # Documentation range

    def test_reserved_asn_allowed_when_requested(self) -> None:
        """Test reserved ASNs allowed when explicitly permitted."""
        assert validate_asn(0, allow_reserved=True) == 0
        assert validate_asn(65535, allow_reserved=True) == 65535

    def test_out_of_range_asn(self) -> None:
        """Test out of range ASNs are rejected."""
        with pytest.raises(ValidationError):
            validate_asn(-1)

        with pytest.raises(ValidationError):
            validate_asn(4294967296)


class TestVNIValidation:
    """Tests for VNI validation."""

    def test_valid_vni(self) -> None:
        """Test valid VNI values."""
        assert validate_vni(1) == 1
        assert validate_vni(10000) == 10000
        assert validate_vni(16777215) == 16777215

    def test_invalid_vni(self) -> None:
        """Test invalid VNI values are rejected."""
        with pytest.raises(ValidationError):
            validate_vni(0)

        with pytest.raises(ValidationError):
            validate_vni(-1)

        with pytest.raises(ValidationError):
            validate_vni(16777216)


class TestVLANIDValidation:
    """Tests for VLAN ID validation."""

    def test_valid_vlan_id(self) -> None:
        """Test valid VLAN IDs."""
        assert validate_vlan_id(1) == 1
        assert validate_vlan_id(100) == 100
        assert validate_vlan_id(4094) == 4094

    def test_invalid_vlan_id(self) -> None:
        """Test invalid VLAN IDs are rejected."""
        with pytest.raises(ValidationError):
            validate_vlan_id(0)

        with pytest.raises(ValidationError):
            validate_vlan_id(4095)

        with pytest.raises(ValidationError):
            validate_vlan_id(-1)


class TestPortValidation:
    """Tests for port number validation."""

    def test_valid_port(self) -> None:
        """Test valid port numbers."""
        assert validate_port(1) == 1
        assert validate_port(80) == 80
        assert validate_port(443) == 443
        assert validate_port(65535) == 65535

    def test_invalid_port(self) -> None:
        """Test invalid port numbers are rejected."""
        with pytest.raises(ValidationError):
            validate_port(0)

        with pytest.raises(ValidationError):
            validate_port(65536)

        with pytest.raises(ValidationError):
            validate_port(-1)


class TestMTUValidation:
    """Tests for MTU validation."""

    def test_valid_mtu(self) -> None:
        """Test valid MTU values."""
        assert validate_mtu(68) == 68
        assert validate_mtu(1500) == 1500
        assert validate_mtu(9000) == 9000
        assert validate_mtu(65535) == 65535

    def test_invalid_mtu(self) -> None:
        """Test invalid MTU values are rejected."""
        with pytest.raises(ValidationError):
            validate_mtu(67)

        with pytest.raises(ValidationError):
            validate_mtu(65536)

        with pytest.raises(ValidationError):
            validate_mtu(-1)


class TestPositiveIntValidation:
    """Tests for positive integer validation."""

    def test_valid_positive_int(self) -> None:
        """Test valid positive integers."""
        assert validate_positive_int(1) == 1
        assert validate_positive_int(100) == 100
        assert validate_positive_int(999999) == 999999

    def test_zero_rejected(self) -> None:
        """Test zero is rejected."""
        with pytest.raises(ValidationError):
            validate_positive_int(0)

    def test_negative_rejected(self) -> None:
        """Test negative values are rejected."""
        with pytest.raises(ValidationError):
            validate_positive_int(-1)

    def test_max_value_enforced(self) -> None:
        """Test max_value parameter is enforced."""
        assert validate_positive_int(100, max_value=100) == 100

        with pytest.raises(ValidationError):
            validate_positive_int(101, max_value=100)

    def test_custom_field_name(self) -> None:
        """Test custom field name in error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_int(-1, field_name="count")
        assert exc_info.value.field == "count"


class TestNetworksOverlap:
    """Tests for networks_overlap function."""

    def test_overlapping_networks(self) -> None:
        """Test overlapping networks are detected."""
        net1 = IPv4Network("10.0.0.0/8")
        net2 = IPv4Network("10.1.0.0/16")
        assert networks_overlap(net1, net2) is True

    def test_non_overlapping_networks(self) -> None:
        """Test non-overlapping networks."""
        net1 = IPv4Network("10.0.0.0/8")
        net2 = IPv4Network("192.168.0.0/16")
        assert networks_overlap(net1, net2) is False

    def test_adjacent_networks(self) -> None:
        """Test adjacent networks do not overlap."""
        net1 = IPv4Network("10.0.0.0/24")
        net2 = IPv4Network("10.0.1.0/24")
        assert networks_overlap(net1, net2) is False

    def test_same_network(self) -> None:
        """Test same network overlaps with itself."""
        net1 = IPv4Network("10.0.0.0/24")
        net2 = IPv4Network("10.0.0.0/24")
        assert networks_overlap(net1, net2) is True


class TestValidateNoOverlap:
    """Tests for validate_no_overlap function."""

    def test_no_overlap(self) -> None:
        """Test non-overlapping networks pass validation."""
        networks = [
            ("loopback", IPv4Network("10.0.0.0/24")),
            ("vtep", IPv4Network("10.0.1.0/24")),
            ("p2p", IPv4Network("10.0.100.0/22")),
        ]
        # Should not raise
        validate_no_overlap(networks)

    def test_overlap_detected(self) -> None:
        """Test overlapping networks raise ValidationError."""
        networks = [
            ("loopback", IPv4Network("10.0.0.0/24")),
            ("vtep", IPv4Network("10.0.0.0/25")),  # Overlaps with loopback
        ]
        with pytest.raises(ValidationError) as exc_info:
            validate_no_overlap(networks)
        assert "overlap" in exc_info.value.reason.lower()

    def test_empty_list(self) -> None:
        """Test empty list passes validation."""
        validate_no_overlap([])

    def test_single_network(self) -> None:
        """Test single network passes validation."""
        networks = [("loopback", IPv4Network("10.0.0.0/24"))]
        validate_no_overlap(networks)


class TestTyperCallbacks:
    """Tests for Typer callback validators."""

    def test_ip_address_callback_valid(self) -> None:
        """Test IP address callback with valid input."""
        assert ip_address_callback("192.168.1.1") == "192.168.1.1"
        assert ip_address_callback("::1") == "::1"
        assert ip_address_callback("") == ""

    def test_ip_address_callback_invalid(self) -> None:
        """Test IP address callback with invalid input."""
        with pytest.raises(typer.BadParameter):
            ip_address_callback("invalid")

    def test_ipv4_address_callback_valid(self) -> None:
        """Test IPv4 address callback with valid input."""
        assert ipv4_address_callback("192.168.1.1") == "192.168.1.1"
        assert ipv4_address_callback("") == ""

    def test_ipv4_address_callback_invalid(self) -> None:
        """Test IPv4 address callback with invalid input."""
        with pytest.raises(typer.BadParameter):
            ipv4_address_callback("invalid")

    def test_network_callback_valid(self) -> None:
        """Test network callback with valid input."""
        assert network_callback("10.0.0.0/8") == "10.0.0.0/8"
        assert network_callback("") == ""

    def test_network_callback_invalid(self) -> None:
        """Test network callback with invalid input."""
        with pytest.raises(typer.BadParameter):
            network_callback("invalid")

    def test_multicast_callback_valid(self) -> None:
        """Test multicast callback with valid input."""
        assert multicast_callback("239.1.1.0") == "239.1.1.0"
        assert multicast_callback("") == ""

    def test_multicast_callback_invalid(self) -> None:
        """Test multicast callback with invalid input."""
        with pytest.raises(typer.BadParameter):
            multicast_callback("10.0.0.1")  # Not multicast

        with pytest.raises(typer.BadParameter):
            multicast_callback("invalid")
