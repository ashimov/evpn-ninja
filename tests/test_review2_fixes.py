"""Tests for fixes from the second code review round."""

import json
import sys
from pathlib import Path

import pytest
import yaml

from evpn_ninja.calculators.ebgp import calculate_ebgp_underlay
from evpn_ninja.calculators.evpn import calculate_evpn_params
from evpn_ninja.calculators.multicast import calculate_multicast_groups
from evpn_ninja.calculators.multihoming import generate_esi_type0
from evpn_ninja.config import (
    Config,
    ConfigValidationError,
    EBGPDefaults,
    MulticastDefaults,
    save_config,
)
from evpn_ninja.exporters.ansible import export_ansible_vars
from evpn_ninja.exporters.containerlab import _sanitize_name, export_containerlab_topology
from evpn_ninja.exporters.eve_gns3 import export_gns3_topology


class TestESIType0TenBytes:
    """Test that Type-0 ESI is exactly 10 bytes per RFC 7432."""

    def test_esi_type0_is_10_bytes(self) -> None:
        """ESI must be 10 bytes: type(1) + prefix(3) + es_id(6)."""
        esi = generate_esi_type0(es_id=1)
        parts = esi.esi.split(":")
        assert len(parts) == 10, f"Expected 10 bytes, got {len(parts)}: {esi.esi}"

    def test_esi_type0_various_ids(self) -> None:
        """Test various ES IDs produce 10-byte ESIs."""
        for es_id in [1, 100, 255, 65535, 16777215]:
            esi = generate_esi_type0(es_id=es_id)
            assert len(esi.esi.split(":")) == 10

    def test_esi_type0_with_prefix(self) -> None:
        """Type-0 ESI with custom prefix still has 10 bytes."""
        esi = generate_esi_type0(es_id=42, prefix="aa:bb:cc")
        parts = esi.esi.split(":")
        assert len(parts) == 10
        assert parts[0] == "00"  # Type byte
        assert parts[1] == "aa"
        assert parts[2] == "bb"
        assert parts[3] == "cc"


class TestEVPNL3VNIConsistency:
    """Test l3_vni and vrf_name must be provided together."""

    def test_l3_vni_without_vrf_name_raises(self) -> None:
        """Providing l3_vni without vrf_name should raise ValueError."""
        with pytest.raises(ValueError, match="l3_vni and vrf_name must both be provided"):
            calculate_evpn_params(
                bgp_as=65000,
                loopback_ip="10.0.0.1",
                l2_vni=10010,
                vlan_id=10,
                l3_vni=50000,
                vrf_name=None,
            )

    def test_vrf_name_without_l3_vni_raises(self) -> None:
        """Providing vrf_name without l3_vni should raise ValueError."""
        with pytest.raises(ValueError, match="l3_vni and vrf_name must both be provided"):
            calculate_evpn_params(
                bgp_as=65000,
                loopback_ip="10.0.0.1",
                l2_vni=10010,
                vlan_id=10,
                l3_vni=None,
                vrf_name="TENANT-1",
            )

    def test_both_provided_is_valid(self) -> None:
        """Both l3_vni and vrf_name provided should succeed."""
        result = calculate_evpn_params(
            bgp_as=65000,
            loopback_ip="10.0.0.1",
            l2_vni=10010,
            vlan_id=10,
            l3_vni=50000,
            vrf_name="TENANT-1",
        )
        assert result.l3_vni == 50000
        assert result.vrf_name == "TENANT-1"
        assert result.l3_params is not None

    def test_both_omitted_is_valid(self) -> None:
        """Both l3_vni and vrf_name omitted should succeed."""
        result = calculate_evpn_params(
            bgp_as=65000,
            loopback_ip="10.0.0.1",
            l2_vni=10010,
            vlan_id=10,
        )
        assert result.l3_vni is None
        assert result.vrf_name is None
        assert result.l3_params is None


class TestEBGPP2PAddressExhaustion:
    """Test eBGP raises ValueError when P2P address space is exhausted."""

    def test_insufficient_p2p_space_raises(self) -> None:
        """Tiny P2P network for many links should raise ValueError."""
        with pytest.raises(ValueError, match="provides only"):
            calculate_ebgp_underlay(
                spine_count=4,
                leaf_count=16,
                p2p_network="10.0.0.0/28",  # Only 8 /31 subnets, need 64
            )

    def test_sufficient_p2p_space_works(self) -> None:
        """Adequate P2P network should work."""
        result = calculate_ebgp_underlay(
            spine_count=2,
            leaf_count=4,
            p2p_network="10.0.0.0/24",  # 128 /31 subnets, need 8
        )
        assert result.total_sessions == 8


class TestMulticastValidation:
    """Test multicast calculator input validation."""

    def test_negative_vni_count_raises(self) -> None:
        """Negative vni_count should raise ValueError."""
        with pytest.raises(ValueError, match="vni_count must be positive"):
            calculate_multicast_groups(vni_count=-1)

    def test_zero_vni_count_raises(self) -> None:
        """Zero vni_count should raise ValueError."""
        with pytest.raises(ValueError, match="vni_count must be positive"):
            calculate_multicast_groups(vni_count=0)

    def test_vni_start_too_low_raises(self) -> None:
        """vni_start=0 should raise ValueError."""
        with pytest.raises(ValueError, match="vni_start must be 1-16777215"):
            calculate_multicast_groups(vni_start=0)

    def test_vni_start_too_high_raises(self) -> None:
        """vni_start above max should raise ValueError."""
        with pytest.raises(ValueError, match="vni_start must be 1-16777215"):
            calculate_multicast_groups(vni_start=16777216)

    def test_zero_vnis_per_group_raises(self) -> None:
        """Zero vnis_per_group should raise ValueError."""
        with pytest.raises(ValueError, match="vnis_per_group must be positive"):
            calculate_multicast_groups(vnis_per_group=0)


class TestContainerlabSanitization:
    """Test containerlab YAML name sanitization."""

    def test_sanitize_normal_name(self) -> None:
        """Normal names should pass through unchanged."""
        assert _sanitize_name("spine-1") == "spine-1"
        assert _sanitize_name("leaf.node.1") == "leaf.node.1"

    def test_sanitize_special_chars(self) -> None:
        """Special characters should be replaced with hyphens."""
        assert _sanitize_name("spine 1") == "spine-1"
        assert _sanitize_name("node:test") == "node-test"

    def test_sanitize_yaml_injection(self) -> None:
        """YAML injection characters should be sanitized."""
        result = _sanitize_name("spine-1\nmalicious: true")
        assert "\n" not in result
        assert ":" not in result

    def test_sanitize_empty_becomes_node(self) -> None:
        """Empty name after sanitization becomes 'node'."""
        assert _sanitize_name("!!!") == "node"

    def test_sanitize_collapses_hyphens(self) -> None:
        """Multiple consecutive hyphens should collapse."""
        assert _sanitize_name("a---b") == "a-b"

    def test_topology_uses_sanitized_names(self) -> None:
        """Containerlab topology should sanitize node names."""
        spines = [{"name": "spine 1!"}]
        leaves = [{"name": "leaf:2"}]
        result = export_containerlab_topology(spines, leaves)
        assert "spine-1:" in result
        assert "leaf-2:" in result


class TestAnsibleNullFiltering:
    """Test ansible vars filter out None values."""

    def test_evpn_vars_without_none(self) -> None:
        """EVPN vars should not contain None values."""
        evpn_params = {
            "l2_vni": 10010,
            "l2_rd": "10.0.0.1:10010",
            # l2_rt_import and l2_rt_export missing → should not appear as None
        }
        result = export_ansible_vars(evpn_params=evpn_params)
        vars_data = yaml.safe_load(result)
        evpn = vars_data["evpn"]
        assert evpn["l2_vni"] == 10010
        assert evpn["l2_rd"] == "10.0.0.1:10010"
        assert "l2_rt_import" not in evpn
        assert "l2_rt_export" not in evpn

    def test_vni_alloc_without_multicast(self) -> None:
        """VNI allocations without multicast_group should omit the key."""
        vni_allocs = [
            {"vlan_id": 10, "vni_decimal": 10010},  # No multicast_group
        ]
        result = export_ansible_vars(vni_allocations=vni_allocs)
        vars_data = yaml.safe_load(result)
        assert "multicast_group" not in vars_data["vxlan_vnis"][0]


class TestGNS3LeafPorts:
    """Test GNS3 leaf port count depends on include_hosts."""

    def test_leaf_ports_without_hosts(self) -> None:
        """Without hosts, leaf ports = spines + mgmt (no host port)."""
        spines = [{"name": "spine-1"}, {"name": "spine-2"}]
        leaves = [{"name": "leaf-1"}]
        result = export_gns3_topology(spines, leaves, include_hosts=False)
        project = json.loads(result)
        leaf_node = next(n for n in project["topology"]["nodes"] if n["name"] == "leaf-1")
        # 2 spines + 1 mgmt = 3 ports
        assert len(leaf_node["ports"]) == 3

    def test_leaf_ports_with_hosts(self) -> None:
        """With hosts, leaf ports = spines + mgmt + host."""
        spines = [{"name": "spine-1"}, {"name": "spine-2"}]
        leaves = [{"name": "leaf-1"}]
        result = export_gns3_topology(spines, leaves, include_hosts=True)
        project = json.loads(result)
        leaf_node = next(n for n in project["topology"]["nodes"] if n["name"] == "leaf-1")
        # 2 spines + 1 mgmt + 1 host = 4 ports
        assert len(leaf_node["ports"]) == 4


class TestConfigSchemeAllowlists:
    """Test config scheme allowlists match actual enum values."""

    def test_multicast_range_based_valid(self) -> None:
        """'range-based' should be valid for multicast scheme."""
        defaults = MulticastDefaults(scheme="range-based")
        assert defaults.scheme == "range-based"

    def test_multicast_range_without_based_invalid(self) -> None:
        """'range' alone should be invalid (must be 'range-based')."""
        with pytest.raises(ConfigValidationError, match="scheme must be one of"):
            MulticastDefaults(scheme="range")

    def test_ebgp_public_scheme_invalid(self) -> None:
        """'public' should not be a valid eBGP scheme."""
        with pytest.raises(ConfigValidationError, match="scheme must be one of"):
            EBGPDefaults(scheme="public")

    def test_ebgp_custom_scheme_valid(self) -> None:
        """'custom' should be a valid eBGP scheme."""
        defaults = EBGPDefaults(scheme="custom")
        assert defaults.scheme == "custom"


class TestConfigSaveErrorHandling:
    """Test save_config error handling."""

    @pytest.mark.skipif(sys.platform == "win32", reason="chmod not reliable on Windows")
    def test_save_config_permission_error(self, tmp_path: Path) -> None:
        """save_config should raise PermissionError on read-only path."""
        read_only_dir = tmp_path / "readonly"
        read_only_dir.mkdir()
        config_path = read_only_dir / "config.yaml"

        read_only_dir.chmod(0o444)
        try:
            with pytest.raises(PermissionError):
                save_config(Config(), config_path)
        finally:
            read_only_dir.chmod(0o755)
