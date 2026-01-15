"""Tests for Fabric Parameters calculator."""

import pytest
from evpn_ninja.calculators.fabric import calculate_fabric_params, ReplicationMode


class TestFabricCalculator:
    """Test cases for Fabric Parameters calculator."""

    def test_basic_fabric_calculation(self):
        """Test basic fabric parameter calculation."""
        result = calculate_fabric_params(
            vtep_count=4,
            spine_count=2,
            vni_count=100,
            hosts_per_vtep=50,
        )

        assert result.vtep_count == 4
        assert result.spine_count == 2
        assert result.vni_count == 100

    def test_loopback_allocation(self):
        """Test loopback IP allocation."""
        result = calculate_fabric_params(
            vtep_count=4,
            spine_count=2,
            vni_count=100,
            hosts_per_vtep=50,
            loopback_network="10.0.0.0/24",
        )

        # Should have loopbacks for spines + VTEPs
        assert len(result.loopback_allocation.addresses) == 4 + 2

    def test_vtep_loopback_allocation(self):
        """Test VTEP loopback IP allocation."""
        result = calculate_fabric_params(
            vtep_count=4,
            spine_count=2,
            vni_count=100,
            hosts_per_vtep=50,
            vtep_loopback_network="10.0.1.0/24",
        )

        # Should have VTEP loopbacks for each VTEP
        assert len(result.vtep_loopback_allocation.addresses) == 4

    def test_p2p_link_calculation(self):
        """Test point-to-point link calculation."""
        result = calculate_fabric_params(
            vtep_count=4,
            spine_count=2,
            vni_count=100,
            hosts_per_vtep=50,
        )

        # Each VTEP connects to each spine
        expected_links = 4 * 2  # vtep_count * spine_count
        assert result.p2p_links_total == expected_links

    def test_estimates_calculation(self):
        """Test fabric estimates calculation."""
        result = calculate_fabric_params(
            vtep_count=4,
            spine_count=2,
            vni_count=100,
            hosts_per_vtep=50,
        )

        assert result.estimates.total_mac_entries == 4 * 50
        assert result.estimates.evpn_type3_routes == 100 * 4

    def test_bgp_sessions_estimate(self):
        """Test BGP sessions estimation."""
        result = calculate_fabric_params(
            vtep_count=4,
            spine_count=2,
            vni_count=100,
            hosts_per_vtep=50,
        )

        assert result.estimates.bgp_sessions_per_leaf > 0
        assert result.estimates.bgp_sessions_total > 0

    def test_large_fabric(self):
        """Test large fabric calculation."""
        result = calculate_fabric_params(
            vtep_count=100,
            spine_count=4,
            vni_count=4000,
            hosts_per_vtep=200,
        )

        assert result.vtep_count == 100
        assert result.spine_count == 4
        # P2P links should scale correctly
        assert result.p2p_links_total == 100 * 4

    def test_single_spine(self):
        """Test fabric with single spine (non-redundant)."""
        result = calculate_fabric_params(
            vtep_count=2,
            spine_count=1,
            vni_count=10,
            hosts_per_vtep=10,
        )

        assert result.spine_count == 1
        assert result.p2p_links_total == 2  # 2 VTEPs * 1 spine

    def test_custom_networks(self):
        """Test fabric with custom network ranges."""
        result = calculate_fabric_params(
            vtep_count=4,
            spine_count=2,
            vni_count=100,
            hosts_per_vtep=50,
            loopback_network="172.16.0.0/24",
            vtep_loopback_network="172.16.1.0/24",
            p2p_network="172.16.100.0/22",
        )

        # Verify loopbacks start from custom network
        assert any("172.16.0" in addr for addr in result.loopback_allocation.addresses)
        assert any("172.16.1" in addr for addr in result.vtep_loopback_allocation.addresses)

    def test_replication_mode_ingress(self):
        """Test ingress replication mode."""
        result = calculate_fabric_params(
            vtep_count=4,
            spine_count=2,
            vni_count=100,
            hosts_per_vtep=50,
            replication_mode=ReplicationMode.INGRESS,
        )

        assert result.replication_mode == "ingress"
        # BUM replication factor = vtep_count - 1 for ingress
        assert result.estimates.bum_replication_factor == 3

    def test_replication_mode_multicast(self):
        """Test multicast replication mode."""
        result = calculate_fabric_params(
            vtep_count=4,
            spine_count=2,
            vni_count=100,
            hosts_per_vtep=50,
            replication_mode=ReplicationMode.MULTICAST,
        )

        assert result.replication_mode == "multicast"
        # BUM replication factor = 1 for multicast
        assert result.estimates.bum_replication_factor == 1

    def test_evpn_type2_routes(self):
        """Test EVPN Type-2 routes calculation."""
        result = calculate_fabric_params(
            vtep_count=4,
            spine_count=2,
            vni_count=100,
            hosts_per_vtep=50,
        )

        # Type-2 routes = total_macs * (vtep_count - 1)
        total_macs = 4 * 50
        expected_type2 = total_macs * (4 - 1)
        assert result.estimates.evpn_type2_routes == expected_type2
