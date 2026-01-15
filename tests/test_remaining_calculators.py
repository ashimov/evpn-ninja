"""Tests for remaining calculator modules (bandwidth, multihoming, route_reflector, topology)."""

import pytest

from evpn_ninja.calculators.bandwidth import (
    BandwidthResult,
    FailureScenario,
    LinkSpeed,
    OversubscriptionAnalysis,
    calculate_bandwidth,
)
from evpn_ninja.calculators.multihoming import (
    ESIType,
    LACPMode,
    MultiHomingMode,
    calculate_multihoming,
    generate_es_import_rt,
    generate_esi_type0,
    generate_esi_type1,
    generate_esi_type3,
)
from evpn_ninja.calculators.route_reflector import (
    RRPlacement,
    RRRedundancy,
    RouteReflectorResult,
    calculate_route_reflector,
)
from evpn_ninja.calculators.topology import (
    TopologyResult,
    generate_topology,
)


# ============================================================================
# Bandwidth Calculator Tests
# ============================================================================
class TestLinkSpeed:
    """Tests for LinkSpeed enum."""

    def test_link_speed_values(self) -> None:
        """Test LinkSpeed enum values."""
        assert LinkSpeed.GE_1.value == "1g"
        assert LinkSpeed.GE_10.value == "10g"
        assert LinkSpeed.GE_25.value == "25g"
        assert LinkSpeed.GE_100.value == "100g"
        assert LinkSpeed.GE_400.value == "400g"

    def test_link_speed_gbps_property(self) -> None:
        """Test LinkSpeed gbps property."""
        assert LinkSpeed.GE_1.gbps == 1
        assert LinkSpeed.GE_10.gbps == 10
        assert LinkSpeed.GE_25.gbps == 25
        assert LinkSpeed.GE_100.gbps == 100
        assert LinkSpeed.GE_400.gbps == 400


class TestBandwidthCalculator:
    """Tests for bandwidth calculator."""

    def test_calculate_bandwidth_basic(self) -> None:
        """Test basic bandwidth calculation."""
        result = calculate_bandwidth(
            spine_count=2,
            leaf_count=4,
            uplink_speed=LinkSpeed.GE_100,
            uplink_count_per_leaf=2,
            downlink_speed=LinkSpeed.GE_25,
            downlink_count_per_leaf=48,
        )

        assert isinstance(result, BandwidthResult)
        assert result.spine_count == 2
        assert result.leaf_count == 4
        assert result.uplink_speed == "100g"
        assert result.downlink_speed == "25g"

    def test_bandwidth_calculation_values(self) -> None:
        """Test bandwidth calculation values."""
        result = calculate_bandwidth(
            spine_count=2,
            leaf_count=4,
            uplink_speed=LinkSpeed.GE_100,
            uplink_count_per_leaf=2,
            downlink_speed=LinkSpeed.GE_25,
            downlink_count_per_leaf=48,
        )

        # Leaf uplink: 2 * 100G = 200G
        assert result.leaf_uplink_bandwidth_gbps == 200

        # Leaf downlink: 48 * 25G = 1200G
        assert result.leaf_downlink_bandwidth_gbps == 1200

        # Spine total: 4 leaves * 100G = 400G
        assert result.spine_total_bandwidth_gbps == 400

        # Bisection: 4 leaves * 200G = 800G
        assert result.fabric_bisection_bandwidth_gbps == 800

    def test_oversubscription_analysis(self) -> None:
        """Test oversubscription ratio calculation."""
        result = calculate_bandwidth(
            spine_count=2,
            leaf_count=4,
            uplink_speed=LinkSpeed.GE_100,
            uplink_count_per_leaf=2,
            downlink_speed=LinkSpeed.GE_25,
            downlink_count_per_leaf=48,
        )

        oversub = result.leaf_oversubscription
        assert isinstance(oversub, OversubscriptionAnalysis)
        assert oversub.downlink_bandwidth_gbps == 1200
        assert oversub.uplink_bandwidth_gbps == 200
        assert oversub.oversubscription_ratio == 6.0  # 1200/200
        assert oversub.is_non_blocking is False

    def test_non_blocking_fabric(self) -> None:
        """Test non-blocking fabric detection."""
        result = calculate_bandwidth(
            spine_count=4,
            leaf_count=4,
            uplink_speed=LinkSpeed.GE_100,
            uplink_count_per_leaf=4,
            downlink_speed=LinkSpeed.GE_25,
            downlink_count_per_leaf=16,  # 16 * 25 = 400G
        )

        # 4 * 100G = 400G uplink, 16 * 25G = 400G downlink
        assert result.leaf_oversubscription.is_non_blocking is True
        assert result.leaf_oversubscription.oversubscription_ratio == 1.0

    def test_ecmp_paths_calculation(self) -> None:
        """Test ECMP path calculation."""
        result = calculate_bandwidth(
            spine_count=4,
            leaf_count=4,
            uplink_count_per_leaf=4,
        )
        assert result.ecmp_paths == 4

        # When uplinks < spines
        result = calculate_bandwidth(
            spine_count=4,
            leaf_count=4,
            uplink_count_per_leaf=2,
        )
        assert result.ecmp_paths == 2

    def test_failure_scenarios(self) -> None:
        """Test failure scenario generation."""
        result = calculate_bandwidth(
            spine_count=2,
            leaf_count=4,
            uplink_count_per_leaf=2,
        )

        scenarios = result.failure_scenarios
        assert len(scenarios) > 0
        assert all(isinstance(s, FailureScenario) for s in scenarios)

        # Check for spine failure scenario
        spine_failure = next((s for s in scenarios if "spine failure" in s.scenario.lower()), None)
        assert spine_failure is not None
        assert spine_failure.still_operational is True

    def test_recommendations_generated(self) -> None:
        """Test recommendations are generated."""
        result = calculate_bandwidth()
        assert len(result.recommendations) > 0


# ============================================================================
# Multi-homing Calculator Tests
# ============================================================================
class TestESIGeneration:
    """Tests for ESI generation functions."""

    def test_generate_esi_type0(self) -> None:
        """Test Type-0 ESI generation."""
        esi = generate_esi_type0(es_id=1)

        assert esi.esi_type == "type-0"
        assert esi.esi.startswith("00:")
        # ESI format: type(1) + prefix(3) + es_id(5) = 9 bytes
        assert len(esi.esi.split(":")) == 9

    def test_generate_esi_type0_with_prefix(self) -> None:
        """Test Type-0 ESI with custom prefix."""
        esi = generate_esi_type0(es_id=1, prefix="aa:bb:cc")

        parts = esi.esi.split(":")
        assert parts[0] == "00"  # Type byte
        assert parts[1] == "aa"
        assert parts[2] == "bb"
        assert parts[3] == "cc"

    def test_generate_esi_type1(self) -> None:
        """Test Type-1 ESI generation (LACP-based)."""
        esi = generate_esi_type1(
            lacp_port_key=100,
            lacp_system_mac="00:11:22:33:44:55",
        )

        assert esi.esi_type == "type-1"
        assert esi.esi.startswith("01:")
        parts = esi.esi.split(":")
        assert len(parts) == 10

        # MAC should be in the ESI
        assert "00" in parts[1:7]

    def test_generate_esi_type3(self) -> None:
        """Test Type-3 ESI generation (MAC-based)."""
        esi = generate_esi_type3(
            system_mac="00:11:22:33:44:55",
            local_discriminator=100,
        )

        assert esi.esi_type == "type-3"
        assert esi.esi.startswith("03:")
        parts = esi.esi.split(":")
        assert len(parts) == 10

    def test_generate_es_import_rt(self) -> None:
        """Test ES-Import Route Target generation."""
        esi = "00:aa:bb:cc:dd:ee:ff:00:01:02"
        rt = generate_es_import_rt(esi)

        # Should extract bytes 1-6
        assert rt == "aa:bb:cc:dd:ee:ff"

    def test_generate_es_import_rt_invalid(self) -> None:
        """Test ES-Import RT with invalid ESI."""
        rt = generate_es_import_rt("invalid")
        assert rt == "00:00:00:00:00:00"


class TestMultiHomingEnums:
    """Tests for multi-homing enums."""

    def test_multihoming_mode_values(self) -> None:
        """Test MultiHomingMode enum values."""
        assert MultiHomingMode.ACTIVE_ACTIVE.value == "active-active"
        assert MultiHomingMode.ACTIVE_STANDBY.value == "active-standby"
        assert MultiHomingMode.PORT_ACTIVE.value == "port-active"

    def test_esi_type_values(self) -> None:
        """Test ESIType enum values."""
        assert ESIType.TYPE_0.value == "type-0"
        assert ESIType.TYPE_1.value == "type-1"
        assert ESIType.TYPE_3.value == "type-3"

    def test_lacp_mode_values(self) -> None:
        """Test LACPMode enum values."""
        assert LACPMode.ACTIVE.value == "active"
        assert LACPMode.PASSIVE.value == "passive"


class TestMultiHomingCalculator:
    """Tests for multi-homing calculator."""

    def test_calculate_multihoming_basic(self) -> None:
        """Test basic multi-homing calculation."""
        result = calculate_multihoming(
            es_count=2,
            peers_per_es=2,
            mode=MultiHomingMode.ACTIVE_ACTIVE,
        )

        assert result.total_es_count == 2
        assert result.total_pe_count == 4  # 2 ES * 2 peers
        assert result.redundancy_mode == "active-active"
        assert len(result.ethernet_segments) == 2

    def test_calculate_multihoming_type0(self) -> None:
        """Test multi-homing with Type-0 ESI."""
        result = calculate_multihoming(
            es_count=1,
            esi_type=ESIType.TYPE_0,
        )

        assert result.ethernet_segments[0].esi_config.esi_type == "type-0"

    def test_calculate_multihoming_type1(self) -> None:
        """Test multi-homing with Type-1 ESI."""
        result = calculate_multihoming(
            es_count=1,
            esi_type=ESIType.TYPE_1,
        )

        assert result.ethernet_segments[0].esi_config.esi_type == "type-1"

    def test_calculate_multihoming_type3(self) -> None:
        """Test multi-homing with Type-3 ESI."""
        result = calculate_multihoming(
            es_count=1,
            esi_type=ESIType.TYPE_3,
        )

        assert result.ethernet_segments[0].esi_config.esi_type == "type-3"

    def test_calculate_multihoming_with_vendors(self) -> None:
        """Test multi-homing with vendor config generation."""
        result = calculate_multihoming(
            es_count=1,
            vendors=["arista", "cisco_nxos", "juniper"],
        )

        assert "arista" in result.vendor_configs
        assert "cisco_nxos" in result.vendor_configs
        assert "juniper" in result.vendor_configs

        # Check Arista config content
        assert "EVPN Multi-homing" in result.vendor_configs["arista"]
        assert "evpn ethernet-segment" in result.vendor_configs["arista"]

    def test_ethernet_segment_structure(self) -> None:
        """Test Ethernet Segment structure."""
        result = calculate_multihoming(
            es_count=1,
            peers_per_es=2,
            df_algorithm="modulus",
        )

        es = result.ethernet_segments[0]
        assert es.es_id == 1
        assert es.name == "ES-1"
        assert len(es.peers) == 2
        assert es.df_election == "modulus"
        assert es.es_import_rt is not None

    def test_peer_configuration(self) -> None:
        """Test peer configuration structure."""
        result = calculate_multihoming(
            es_count=1,
            peers_per_es=2,
            system_mac="00:11:22:33:44:55",
        )

        peer = result.ethernet_segments[0].peers[0]
        assert peer.name == "PE-1"
        assert peer.lacp_config.system_id == "00:11:22:33:44:55"
        assert peer.lacp_config.mode == "active"


# ============================================================================
# Route Reflector Calculator Tests
# ============================================================================
class TestRREnums:
    """Tests for Route Reflector enums."""

    def test_rr_placement_values(self) -> None:
        """Test RRPlacement enum values."""
        assert RRPlacement.SPINE.value == "spine"
        assert RRPlacement.DEDICATED.value == "dedicated"
        assert RRPlacement.BORDER.value == "border"

    def test_rr_redundancy_values(self) -> None:
        """Test RRRedundancy enum values."""
        assert RRRedundancy.SINGLE.value == "single"
        assert RRRedundancy.PAIR.value == "pair"
        assert RRRedundancy.CLUSTER.value == "cluster"


class TestRouteReflectorCalculator:
    """Tests for Route Reflector calculator."""

    def test_calculate_rr_basic(self) -> None:
        """Test basic RR calculation."""
        result = calculate_route_reflector(
            client_count=10,
            bgp_as=65000,
        )

        assert isinstance(result, RouteReflectorResult)
        assert result.bgp_as == 65000
        assert result.total_clients == 10

    def test_calculate_rr_pair_redundancy(self) -> None:
        """Test RR pair redundancy."""
        result = calculate_route_reflector(
            client_count=10,
            redundancy=RRRedundancy.PAIR,
        )

        # Pair = 2 RRs per cluster
        assert result.total_rr_nodes >= 2
        assert result.redundancy == "pair"

    def test_calculate_rr_single_redundancy(self) -> None:
        """Test single RR (no redundancy)."""
        result = calculate_route_reflector(
            client_count=10,
            redundancy=RRRedundancy.SINGLE,
        )

        assert result.redundancy == "single"
        # Should have warning in design notes
        assert any("no redundancy" in note.lower() for note in result.design_notes)

    def test_calculate_rr_cluster_redundancy(self) -> None:
        """Test RR cluster redundancy."""
        result = calculate_route_reflector(
            client_count=10,
            redundancy=RRRedundancy.CLUSTER,
        )

        # Cluster = 3 RRs per cluster
        assert result.total_rr_nodes >= 3
        assert result.redundancy == "cluster"

    def test_rr_spine_placement(self) -> None:
        """Test RR spine placement."""
        result = calculate_route_reflector(
            client_count=10,
            placement=RRPlacement.SPINE,
        )

        assert result.placement == "spine"
        # Check node naming
        assert any("spine-rr" in c.members[0].name for c in result.clusters)

    def test_rr_dedicated_placement(self) -> None:
        """Test RR dedicated placement."""
        result = calculate_route_reflector(
            client_count=10,
            placement=RRPlacement.DEDICATED,
        )

        assert result.placement == "dedicated"
        # Check node naming
        assert any("rr-" in c.members[0].name for c in result.clusters)

    def test_rr_cluster_structure(self) -> None:
        """Test RR cluster structure."""
        result = calculate_route_reflector(
            client_count=10,
            redundancy=RRRedundancy.PAIR,
        )

        assert len(result.clusters) >= 1
        cluster = result.clusters[0]
        assert cluster.cluster_id is not None
        assert len(cluster.members) == 2  # Pair

    def test_rr_peer_groups(self) -> None:
        """Test RR peer groups generation."""
        result = calculate_route_reflector(client_count=10)

        peer_group_names = [pg.name for pg in result.peer_groups]
        assert "EVPN-CLIENTS" in peer_group_names
        assert "RR-PEERS" in peer_group_names

        # Client peer group should be RR client
        client_pg = next(pg for pg in result.peer_groups if pg.name == "EVPN-CLIENTS")
        assert client_pg.route_reflector_client is True

    def test_rr_config_template(self) -> None:
        """Test RR config template generation."""
        result = calculate_route_reflector(
            client_count=10,
            bgp_as=65000,
        )

        assert "router bgp 65000" in result.config_template
        assert "route-reflector-client" in result.config_template
        assert "l2vpn evpn" in result.config_template

    def test_rr_design_notes(self) -> None:
        """Test RR design notes."""
        result = calculate_route_reflector(client_count=10)

        assert len(result.design_notes) > 0
        # Should mention cluster-id
        assert any("cluster" in note.lower() for note in result.design_notes)

    def test_rr_auto_cluster_scaling(self) -> None:
        """Test automatic cluster count scaling."""
        # Small fabric - 1 cluster
        result = calculate_route_reflector(client_count=30)
        assert len(result.clusters) == 1

        # Medium fabric - 2 clusters
        result = calculate_route_reflector(client_count=100)
        assert len(result.clusters) == 2

        # Large fabric - more clusters
        result = calculate_route_reflector(client_count=300)
        assert len(result.clusters) >= 3

    def test_rr_custom_cluster_count(self) -> None:
        """Test custom cluster count override."""
        result = calculate_route_reflector(
            client_count=10,
            custom_cluster_count=3,
        )

        assert len(result.clusters) == 3


# ============================================================================
# Topology Calculator Tests
# ============================================================================
class TestTopologyCalculator:
    """Tests for topology visualization calculator."""

    def test_generate_topology_basic(self) -> None:
        """Test basic topology generation."""
        result = generate_topology(
            spine_count=2,
            leaf_count=4,
        )

        assert isinstance(result, TopologyResult)
        assert result.spine_count == 2
        assert result.leaf_count == 4

    def test_ascii_art_generation(self) -> None:
        """Test ASCII art contains expected elements."""
        result = generate_topology(
            spine_count=2,
            leaf_count=4,
        )

        ascii_art = result.ascii_art
        assert "Spine 1" in ascii_art
        assert "Spine 2" in ascii_art
        assert "Leaf 1" in ascii_art
        assert "Leaf 4" in ascii_art
        assert "Spines: 2" in ascii_art
        assert "Leaves: 4" in ascii_art

    def test_graphviz_dot_generation(self) -> None:
        """Test Graphviz DOT output."""
        result = generate_topology(
            spine_count=2,
            leaf_count=4,
        )

        dot = result.graphviz_dot
        assert "digraph LeafSpine" in dot
        assert "spine1" in dot
        assert "spine2" in dot
        assert "leaf1" in dot
        assert "leaf4" in dot
        assert "cluster_spines" in dot
        assert "cluster_leaves" in dot

    def test_graphviz_with_speeds(self) -> None:
        """Test Graphviz includes link speeds."""
        result = generate_topology(
            spine_count=2,
            leaf_count=4,
            uplink_speed="100G",
            downlink_speed="25G",
        )

        dot = result.graphviz_dot
        assert "100G" in dot
        assert "25G" in dot

    def test_topology_link_count(self) -> None:
        """Test link count in ASCII art."""
        result = generate_topology(
            spine_count=2,
            leaf_count=4,
        )

        # 2 spines * 4 leaves = 8 links
        assert "Links: 8" in result.ascii_art

    def test_large_topology(self) -> None:
        """Test larger topology generation."""
        result = generate_topology(
            spine_count=4,
            leaf_count=16,
        )

        assert result.spine_count == 4
        assert result.leaf_count == 16
        assert "Links: 64" in result.ascii_art  # 4 * 16
        assert "spine4" in result.graphviz_dot
        assert "leaf16" in result.graphviz_dot
