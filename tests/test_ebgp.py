"""Tests for eBGP Underlay calculator."""

import pytest
from evpn_ninja.calculators.ebgp import (
    ASNScheme,
    calculate_ebgp_underlay,
    PRIVATE_2BYTE_START,
    PRIVATE_2BYTE_END,
    PRIVATE_4BYTE_START,
    PRIVATE_4BYTE_END,
)


class TestEBGPCalculator:
    """Test cases for eBGP Underlay calculator."""

    def test_basic_ebgp_calculation(self):
        """Test basic eBGP underlay calculation."""
        result = calculate_ebgp_underlay(
            spine_count=2,
            leaf_count=4,
        )

        spine_asns = [a for a in result.asn_assignments if a.device_role == "spine"]
        leaf_asns = [a for a in result.asn_assignments if a.device_role == "leaf"]

        assert len(spine_asns) == 2
        assert len(leaf_asns) == 4

    def test_private_2byte_asn(self):
        """Test 2-byte private ASN allocation."""
        result = calculate_ebgp_underlay(
            spine_count=2,
            leaf_count=4,
            scheme=ASNScheme.PRIVATE_2BYTE,
        )

        # 2-byte private ASN range: 64512-65534
        for asn in result.asn_assignments:
            assert PRIVATE_2BYTE_START <= asn.asn <= PRIVATE_2BYTE_END

    def test_private_4byte_asn(self):
        """Test 4-byte private ASN allocation."""
        result = calculate_ebgp_underlay(
            spine_count=2,
            leaf_count=4,
            scheme=ASNScheme.PRIVATE_4BYTE,
        )

        # 4-byte private ASN range: 4200000000-4294967294
        for asn in result.asn_assignments:
            assert PRIVATE_4BYTE_START <= asn.asn <= PRIVATE_4BYTE_END

    def test_custom_base_asn(self):
        """Test custom base ASN allocation."""
        result = calculate_ebgp_underlay(
            spine_count=2,
            leaf_count=4,
            scheme=ASNScheme.CUSTOM,
            base_asn=65100,
        )

        # ASNs should start from base
        assert result.base_asn == 65100
        assert result.asn_assignments[0].asn >= 65100

    def test_spine_same_asn(self):
        """Test all spines share same ASN."""
        result = calculate_ebgp_underlay(
            spine_count=4,
            leaf_count=4,
            spine_asn_same=True,
        )

        spine_asns = [a for a in result.asn_assignments if a.device_role == "spine"]
        spine_asn_values = {a.asn for a in spine_asns}
        assert len(spine_asn_values) == 1

    def test_spine_unique_asn(self):
        """Test each spine has unique ASN."""
        result = calculate_ebgp_underlay(
            spine_count=4,
            leaf_count=4,
            spine_asn_same=False,
        )

        spine_asns = [a for a in result.asn_assignments if a.device_role == "spine"]
        spine_asn_values = {a.asn for a in spine_asns}
        assert len(spine_asn_values) == 4

    def test_leaf_unique_asn(self):
        """Test each leaf has unique ASN."""
        result = calculate_ebgp_underlay(
            spine_count=2,
            leaf_count=4,
        )

        leaf_asns = [a for a in result.asn_assignments if a.device_role == "leaf"]
        leaf_asn_values = {a.asn for a in leaf_asns}
        assert len(leaf_asn_values) == 4

    def test_bgp_sessions_count(self):
        """Test BGP sessions are created correctly."""
        result = calculate_ebgp_underlay(
            spine_count=2,
            leaf_count=4,
        )

        # Each leaf connects to each spine
        expected_sessions = 2 * 4
        assert len(result.bgp_sessions) == expected_sessions
        assert result.total_sessions == expected_sessions

    def test_bgp_session_ips(self):
        """Test BGP sessions have valid IPs."""
        result = calculate_ebgp_underlay(
            spine_count=2,
            leaf_count=4,
            p2p_network="10.0.100.0/22",
        )

        for session in result.bgp_sessions:
            assert session.device_a_ip.startswith("10.0.")
            assert session.device_b_ip.startswith("10.0.")

    def test_asn_range_display(self):
        """Test ASN range strings are correct."""
        result = calculate_ebgp_underlay(
            spine_count=2,
            leaf_count=4,
            spine_asn_same=True,
        )

        # Spine ASN range should be single number when same
        assert "-" not in result.spine_asn_range

        # Leaf ASN range should be a range
        assert "-" in result.leaf_asn_range

    def test_large_fabric(self):
        """Test large fabric eBGP calculation."""
        result = calculate_ebgp_underlay(
            spine_count=4,
            leaf_count=100,
        )

        leaf_asns = [a for a in result.asn_assignments if a.device_role == "leaf"]
        assert len(leaf_asns) == 100
        assert len(result.bgp_sessions) == 4 * 100

    def test_scheme_value_stored(self):
        """Test scheme value is stored correctly."""
        result = calculate_ebgp_underlay(
            spine_count=2,
            leaf_count=4,
            scheme=ASNScheme.PRIVATE_4BYTE,
        )

        assert result.scheme == "private-4byte"

    def test_device_names(self):
        """Test device naming convention."""
        result = calculate_ebgp_underlay(
            spine_count=2,
            leaf_count=3,
        )

        device_names = [a.device_name for a in result.asn_assignments]
        assert "spine-1" in device_names
        assert "spine-2" in device_names
        assert "leaf-1" in device_names
        assert "leaf-2" in device_names
        assert "leaf-3" in device_names
