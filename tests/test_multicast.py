"""Tests for Multicast Groups calculator."""

import pytest
from evpn_ninja.calculators.multicast import (
    MulticastScheme,
    calculate_multicast_groups,
)


class TestMulticastCalculator:
    """Test cases for Multicast Groups calculator."""

    def test_basic_multicast_calculation(self):
        """Test basic multicast group calculation."""
        result = calculate_multicast_groups(
            vni_start=10000,
            vni_count=10,
        )

        assert result.vni_start == 10000
        assert result.vni_count == 10
        assert len(result.mappings) == 10

    def test_one_to_one_scheme(self):
        """Test one-to-one multicast mapping."""
        result = calculate_multicast_groups(
            vni_start=10000,
            vni_count=5,
            scheme=MulticastScheme.ONE_TO_ONE,
        )

        # Each VNI gets unique group
        assert result.groups_used == 5
        groups = {m.multicast_group for m in result.mappings}
        assert len(groups) == 5

    def test_shared_scheme(self):
        """Test shared multicast group scheme."""
        result = calculate_multicast_groups(
            vni_start=10000,
            vni_count=20,
            scheme=MulticastScheme.SHARED,
            vnis_per_group=5,
        )

        # 20 VNIs / 5 per group = 4 groups
        assert result.groups_used == 4
        groups = {m.multicast_group for m in result.mappings}
        assert len(groups) == 4

    def test_range_based_scheme(self):
        """Test range-based multicast mapping."""
        result = calculate_multicast_groups(
            vni_start=10000,
            vni_count=25,
            scheme=MulticastScheme.RANGE_BASED,
            vnis_per_group=10,
        )

        # 25 VNIs / 10 per group = 3 groups (ceiling)
        assert result.groups_used == 3

        # Check range info is populated
        for mapping in result.mappings:
            assert mapping.vni_range_start is not None
            assert mapping.vni_range_end is not None

    def test_multicast_group_range(self):
        """Test multicast groups are in valid range."""
        result = calculate_multicast_groups(
            vni_start=10000,
            vni_count=100,
            base_group="239.1.1.0",
        )

        for mapping in result.mappings:
            # Should be in 239.x.x.x range
            assert mapping.multicast_group.startswith("239.")

    def test_custom_base_group(self):
        """Test custom base multicast group."""
        result = calculate_multicast_groups(
            vni_start=10000,
            vni_count=5,
            base_group="239.100.0.0",
        )

        # First group should be the base
        assert result.mappings[0].multicast_group == "239.100.0.0"

    def test_pim_configuration(self):
        """Test PIM configuration generation."""
        result = calculate_multicast_groups(
            vni_start=10000,
            vni_count=10,
            rp_address="10.0.0.1",
        )

        assert result.pim_config is not None
        assert result.pim_config.rp_address == "10.0.0.1"

    def test_anycast_rp(self):
        """Test Anycast RP configuration."""
        result = calculate_multicast_groups(
            vni_start=10000,
            vni_count=10,
            rp_address="10.0.0.1",
            anycast_rp=True,
            anycast_rp_peers=["10.0.0.2", "10.0.0.3"],
        )

        assert result.pim_config is not None
        assert result.pim_config.anycast_rp is True
        assert result.pim_config.anycast_rp_peers == ["10.0.0.2", "10.0.0.3"]

    def test_underlay_requirements(self):
        """Test underlay requirements are documented."""
        result = calculate_multicast_groups(
            vni_start=10000,
            vni_count=10,
        )

        assert "PIM Mode" in result.underlay_requirements
        assert "IGMP Version" in result.underlay_requirements
        assert "Groups Required" in result.underlay_requirements

    def test_large_allocation(self):
        """Test large multicast allocation."""
        result = calculate_multicast_groups(
            vni_start=10000,
            vni_count=1000,
            scheme=MulticastScheme.ONE_TO_ONE,
        )

        assert len(result.mappings) == 1000
        assert result.groups_used == 1000

    def test_vni_mapping_sequential(self):
        """Test VNIs are mapped sequentially."""
        result = calculate_multicast_groups(
            vni_start=10000,
            vni_count=5,
        )

        vnis = [m.vni for m in result.mappings]
        assert vnis == [10000, 10001, 10002, 10003, 10004]
