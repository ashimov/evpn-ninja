"""Tests for VNI calculator."""

import pytest
from evpn_ninja.calculators.vni import (
    VNIScheme,
    calculate_vni_allocation,
)


class TestVNICalculator:
    """Test cases for VNI calculator."""

    def test_basic_allocation(self):
        """Test basic VNI allocation."""
        result = calculate_vni_allocation(
            base_vni=10000,
            tenant_id=1,
            start_vlan=10,
            count=5,
        )

        assert len(result.entries) == 5
        assert result.entries[0].vni_decimal == 10010
        assert result.entries[0].vlan_id == 10

    def test_vlan_based_scheme(self):
        """Test VLAN-based VNI allocation."""
        result = calculate_vni_allocation(
            scheme=VNIScheme.VLAN_BASED,
            base_vni=10000,
            start_vlan=100,
            count=3,
        )

        # VNI = base_vni + vlan_id
        assert result.entries[0].vni_decimal == 10100
        assert result.entries[1].vni_decimal == 10101
        assert result.entries[2].vni_decimal == 10102

    def test_tenant_based_scheme(self):
        """Test tenant-based VNI allocation."""
        result = calculate_vni_allocation(
            scheme=VNIScheme.TENANT_BASED,
            tenant_id=5,
            start_vlan=10,
            count=3,
        )

        # VNI = tenant_id * 10000 + vlan_id
        assert result.entries[0].vni_decimal == 50010
        assert result.entries[1].vni_decimal == 50011
        assert result.entries[2].vni_decimal == 50012

    def test_sequential_scheme(self):
        """Test sequential VNI allocation."""
        result = calculate_vni_allocation(
            scheme=VNIScheme.SEQUENTIAL,
            base_vni=20000,
            start_vlan=100,
            count=3,
        )

        # VNI = base_vni + index
        assert result.entries[0].vni_decimal == 20000
        assert result.entries[1].vni_decimal == 20001
        assert result.entries[2].vni_decimal == 20002

    def test_multicast_group_assignment(self):
        """Test multicast group assignment for VNIs."""
        result = calculate_vni_allocation(
            base_vni=10000,
            tenant_id=1,
            start_vlan=10,
            count=3,
            multicast_base="239.1.1.0",
        )

        # Each VNI should have a multicast group
        for entry in result.entries:
            assert entry.multicast_group is not None
            assert entry.multicast_group.startswith("239.")

    def test_vni_range_validation(self):
        """Test VNI range is within valid bounds."""
        result = calculate_vni_allocation(
            base_vni=10000,
            tenant_id=1,
            start_vlan=10,
            count=100,
        )

        for entry in result.entries:
            # VNI must be in range 1-16777215
            assert 1 <= entry.vni_decimal <= 16777215

    def test_tenant_isolation(self):
        """Test VNI allocation for different tenants."""
        result_t1 = calculate_vni_allocation(
            scheme=VNIScheme.TENANT_BASED,
            tenant_id=1,
            start_vlan=10,
            count=5,
        )
        result_t2 = calculate_vni_allocation(
            scheme=VNIScheme.TENANT_BASED,
            tenant_id=2,
            start_vlan=10,
            count=5,
        )

        # Different tenants should get different VNIs
        t1_vnis = {e.vni_decimal for e in result_t1.entries}
        t2_vnis = {e.vni_decimal for e in result_t2.entries}
        assert t1_vnis.isdisjoint(t2_vnis)

    def test_result_metadata(self):
        """Test result metadata is correct."""
        result = calculate_vni_allocation(
            scheme=VNIScheme.VLAN_BASED,
            base_vni=10000,
            tenant_id=1,
            start_vlan=10,
            count=10,
        )

        assert result.scheme == "vlan-based"
        assert result.base_vni == 10000
        assert result.start_vlan == 10
        assert result.count == 10

    def test_sequential_vlan_mapping(self):
        """Test VLANs are mapped sequentially."""
        result = calculate_vni_allocation(
            base_vni=10000,
            tenant_id=1,
            start_vlan=100,
            count=5,
        )

        vlans = [e.vlan_id for e in result.entries]
        assert vlans == [100, 101, 102, 103, 104]

    def test_vni_hex_format(self):
        """Test VNI hex format is correct."""
        result = calculate_vni_allocation(
            base_vni=10000,
            start_vlan=10,
            count=1,
        )

        # VNI 10010 = 0x271A
        entry = result.entries[0]
        assert entry.vni_hex.startswith("0x")
        assert int(entry.vni_hex, 16) == entry.vni_decimal

    def test_large_allocation(self):
        """Test large VNI allocation."""
        result = calculate_vni_allocation(
            base_vni=10000,
            tenant_id=1,
            start_vlan=10,
            count=1000,
        )

        assert len(result.entries) == 1000
