"""Tests for MTU calculator."""

import pytest
from evpn_ninja.calculators.mtu import (
    UnderlayType,
    calculate_mtu,
    VXLAN_HEADER,
    UDP_HEADER,
    IPV4_HEADER,
    IPV6_HEADER,
    ETHERNET_HEADER,
    VLAN_TAG,
)


# Total VXLAN overhead for IPv4: Outer Eth (14) + IPv4 (20) + UDP (8) + VXLAN (8) + Inner Eth (14)
VXLAN_OVERHEAD_IPV4 = IPV4_HEADER + UDP_HEADER + VXLAN_HEADER + ETHERNET_HEADER


class TestMTUCalculator:
    """Test cases for MTU calculator."""

    def test_default_mtu_calculation(self):
        """Test MTU calculation with default parameters."""
        result = calculate_mtu(payload_size=1500)

        assert result.payload_size == 1500
        assert result.required_mtu > 1500
        assert result.recommended_mtu >= result.required_mtu

    def test_mtu_with_outer_vlan(self):
        """Test MTU calculation with outer VLAN tag."""
        result_no_vlan = calculate_mtu(payload_size=1500, outer_vlan_tags=0)
        result_one_vlan = calculate_mtu(payload_size=1500, outer_vlan_tags=1)

        # Outer VLAN doesn't affect required MTU (only the L2 frame on wire)
        # Required MTU is from outer IP to end
        assert result_one_vlan.total_frame_size == result_no_vlan.total_frame_size + VLAN_TAG

    def test_mtu_with_inner_vlan(self):
        """Test MTU calculation with inner VLAN tag."""
        result_no_vlan = calculate_mtu(payload_size=1500, inner_vlan_tags=0)
        result_one_vlan = calculate_mtu(payload_size=1500, inner_vlan_tags=1)

        # Inner VLAN adds 4 bytes to required MTU
        assert result_one_vlan.required_mtu == result_no_vlan.required_mtu + VLAN_TAG

    def test_mtu_with_both_vlans(self):
        """Test MTU calculation with both outer and inner VLAN tags."""
        result_base = calculate_mtu(payload_size=1500)
        result = calculate_mtu(
            payload_size=1500,
            outer_vlan_tags=1,
            inner_vlan_tags=1,
        )

        # Inner VLAN affects required MTU
        assert result.required_mtu == result_base.required_mtu + VLAN_TAG

    def test_mtu_with_qinq(self):
        """Test MTU calculation with Q-in-Q (double VLAN tags)."""
        result_base = calculate_mtu(payload_size=1500)
        result = calculate_mtu(
            payload_size=1500,
            outer_vlan_tags=2,
            inner_vlan_tags=0,
        )

        # Outer VLANs don't affect required MTU
        assert result.required_mtu == result_base.required_mtu
        assert result.total_frame_size == result_base.total_frame_size + 2 * VLAN_TAG

    def test_mtu_jumbo_frames(self):
        """Test MTU calculation with jumbo frame payload."""
        result = calculate_mtu(payload_size=9000)

        assert result.payload_size == 9000
        assert result.required_mtu > 9000

    def test_ipv6_underlay(self):
        """Test MTU calculation with IPv6 underlay."""
        result_ipv4 = calculate_mtu(payload_size=1500, underlay_type=UnderlayType.IPV4)
        result_ipv6 = calculate_mtu(payload_size=1500, underlay_type=UnderlayType.IPV6)

        # IPv6 header is 20 bytes larger than IPv4
        assert result_ipv6.required_mtu == result_ipv4.required_mtu + (IPV6_HEADER - IPV4_HEADER)

    def test_layers_breakdown(self):
        """Test that MTU breakdown contains all layers."""
        result = calculate_mtu(payload_size=1500)

        layer_names = [layer.name for layer in result.layers]
        assert any("Ethernet" in name for name in layer_names)
        assert any("IPv4" in name or "IP" in name for name in layer_names)
        assert any("UDP" in name for name in layer_names)
        assert any("VXLAN" in name for name in layer_names)

    def test_total_overhead(self):
        """Test total overhead calculation."""
        result = calculate_mtu(payload_size=1500)

        # Total overhead should be positive
        assert result.total_overhead > 0
        # Total frame = overhead + payload
        assert result.total_frame_size == result.total_overhead + result.payload_size

    def test_small_payload(self):
        """Test MTU calculation with small payload."""
        result = calculate_mtu(payload_size=64)

        assert result.payload_size == 64
        assert result.required_mtu > 64

    def test_recommended_mtu_alignment(self):
        """Test recommended MTU is aligned."""
        result = calculate_mtu(payload_size=1500)

        # Recommended MTU should be aligned to 64 bytes
        assert result.recommended_mtu % 64 == 0
