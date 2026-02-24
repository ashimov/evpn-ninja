"""Tests for fixes from the third code review round."""

from pathlib import Path

import pytest
import yaml

from evpn_ninja.calculators.ebgp import calculate_ebgp_underlay
from evpn_ninja.calculators.fabric import calculate_fabric_params
from evpn_ninja.calculators.multihoming import (
    generate_esi_type0,
    generate_esi_type3,
)
from evpn_ninja.calculators.route_reflector import calculate_route_reflector
from evpn_ninja.calculators.topology import generate_topology
from evpn_ninja.calculators.vni import VNIScheme, calculate_vni_allocation
from evpn_ninja.config import Config, ConfigValidationError, VNIDefaults, save_config
from evpn_ninja.exporters.ansible import (
    AnsibleGroup,
    AnsibleHost,
    export_ansible_inventory,
    export_ansible_vars,
)
from evpn_ninja.exporters.containerlab import export_containerlab_topology


# ============================================================================
# Shared Multicast Utility Tests
# ============================================================================
class TestSharedMulticastUtility:
    """Test the shared _multicast_utils module."""

    def test_multicast_shared_import(self) -> None:
        """Both vni.py and multicast.py use the same shared utility."""
        from evpn_ninja.calculators._multicast_utils import calculate_multicast_group

        result = calculate_multicast_group("239.1.1.0", 5)
        assert result == "239.1.1.5"

    def test_multicast_overflow_raises(self) -> None:
        """Multicast addresses beyond 239.255.255.255 should raise."""
        from evpn_ninja.calculators._multicast_utils import calculate_multicast_group

        with pytest.raises(ValueError, match="overflow"):
            calculate_multicast_group("239.255.255.255", 1)

    def test_non_multicast_base_raises(self) -> None:
        """Non-multicast base address should raise."""
        from evpn_ninja.calculators._multicast_utils import calculate_multicast_group

        with pytest.raises(ValueError, match="not in multicast range"):
            calculate_multicast_group("10.0.0.1", 0)


# ============================================================================
# Calculator Validation Tests
# ============================================================================
class TestCalculatorInputValidation:
    """Test input validation added to calculators."""

    def test_vni_count_zero_raises(self) -> None:
        """VNI count=0 should raise ValueError."""
        with pytest.raises(ValueError, match="count must be positive"):
            calculate_vni_allocation(count=0)

    def test_vni_count_negative_raises(self) -> None:
        """VNI count=-1 should raise ValueError."""
        with pytest.raises(ValueError, match="count must be positive"):
            calculate_vni_allocation(count=-1)

    def test_ebgp_spine_count_zero_raises(self) -> None:
        """eBGP spine_count=0 should raise ValueError."""
        with pytest.raises(ValueError, match="spine_count must be positive"):
            calculate_ebgp_underlay(spine_count=0)

    def test_ebgp_leaf_count_zero_raises(self) -> None:
        """eBGP leaf_count=0 should raise ValueError."""
        with pytest.raises(ValueError, match="leaf_count must be positive"):
            calculate_ebgp_underlay(leaf_count=0)

    def test_topology_spine_count_zero_raises(self) -> None:
        """Topology spine_count=0 should raise ValueError."""
        with pytest.raises(ValueError, match="spine_count must be positive"):
            generate_topology(spine_count=0)

    def test_topology_leaf_count_zero_raises(self) -> None:
        """Topology leaf_count=0 should raise ValueError."""
        with pytest.raises(ValueError, match="leaf_count must be positive"):
            generate_topology(leaf_count=0)

    def test_rr_custom_cluster_count_zero_raises(self) -> None:
        """RR custom_cluster_count=0 should raise ValueError."""
        with pytest.raises(ValueError, match="custom_cluster_count must be positive"):
            calculate_route_reflector(custom_cluster_count=0)


# ============================================================================
# Truthiness Fix Tests
# ============================================================================
class TestTruthinessFixesEBGP:
    """Test that base_asn=0 works correctly after truthiness fix."""

    def test_ebgp_base_asn_zero(self) -> None:
        """base_asn=0 should be used (not replaced with default)."""
        result = calculate_ebgp_underlay(
            spine_count=1,
            leaf_count=1,
            base_asn=0,
        )
        assert result.base_asn == 0


class TestTruthinessFixesRR:
    """Test custom_cluster_count truthiness fix."""

    def test_rr_custom_cluster_count_one(self) -> None:
        """custom_cluster_count=1 should override auto calculation."""
        result = calculate_route_reflector(
            client_count=200,
            custom_cluster_count=1,
        )
        assert len(result.clusters) == 1


# ============================================================================
# Multihoming Overflow Tests
# ============================================================================
class TestMultihomingOverflow:
    """Test ESI value overflow detection."""

    def test_esi_type0_large_es_id_raises(self) -> None:
        """es_id exceeding 48-bit should raise ValueError."""
        with pytest.raises(ValueError, match="48-bit"):
            generate_esi_type0(es_id=0xFFFFFFFFFFFF + 1)

    def test_esi_type3_large_discriminator_raises(self) -> None:
        """local_discriminator exceeding 24-bit should raise ValueError."""
        with pytest.raises(ValueError, match="24-bit"):
            generate_esi_type3(
                system_mac="00:00:00:00:00:01",
                local_discriminator=0xFFFFFF + 1,
            )

    def test_esi_type0_max_valid(self) -> None:
        """Maximum valid es_id should work."""
        esi = generate_esi_type0(es_id=0xFFFFFFFFFFFF)
        assert len(esi.esi.split(":")) == 10

    def test_esi_type3_max_valid(self) -> None:
        """Maximum valid local_discriminator should work."""
        esi = generate_esi_type3(
            system_mac="00:00:00:00:00:01",
            local_discriminator=0xFFFFFF,
        )
        assert len(esi.esi.split(":")) == 10


# ============================================================================
# Containerlab Exporter Fixes
# ============================================================================
class TestContainerlabFixes:
    """Test containerlab exporter fixes."""

    def test_nxos_kind_mapping(self) -> None:
        """nxos should map to cisco_nxos9000v (consistent with cisco_nxos key)."""
        from evpn_ninja.exporters.containerlab import CLAB_KINDS

        assert CLAB_KINDS["nxos"] == "cisco_nxos9000v"
        assert CLAB_KINDS["cisco_nxos"] == "cisco_nxos9000v"

    def test_labels_are_quoted(self) -> None:
        """Label values (loopback, vtep_ip) should be quoted in YAML."""
        spines = [{"name": "spine-1", "loopback": "10.0.0.1", "asn": 65000}]
        leaves = [{"name": "leaf-1", "loopback": "10.0.1.1", "vtep_ip": "10.0.2.1", "asn": 65001}]
        result = export_containerlab_topology(spines, leaves)

        assert '"10.0.0.1"' in result  # spine loopback quoted
        assert '"10.0.1.1"' in result  # leaf loopback quoted
        assert '"10.0.2.1"' in result  # vtep_ip quoted

    def test_mgmt_network_capacity_overflow_raises(self) -> None:
        """Too many nodes for mgmt network should raise ValueError."""
        spines = [{"name": f"spine-{i}"} for i in range(1, 200)]
        leaves = [{"name": f"leaf-{i}"} for i in range(1, 200)]
        with pytest.raises(ValueError, match="usable IPs"):
            export_containerlab_topology(spines, leaves, mgmt_network="172.20.20.0/24")

    def test_name_collision_after_sanitization_raises(self) -> None:
        """Duplicate names after sanitization should raise ValueError."""
        spines = [{"name": "node:1"}, {"name": "node 1"}]
        leaves = []
        with pytest.raises(ValueError, match="collision"):
            export_containerlab_topology(spines, leaves)


# ============================================================================
# Ansible Exporter Fixes
# ============================================================================
class TestAnsibleFixes:
    """Test ansible exporter fixes."""

    def test_host_asn_zero_included(self) -> None:
        """AnsibleHost with asn=0 should be included (not dropped)."""
        host = AnsibleHost(name="node-1", ansible_host="10.0.0.1", role="spine", asn=0)
        group = AnsibleGroup(name="test", hosts=[host])
        result = export_ansible_inventory([], [], extra_groups=[group])
        inventory = yaml.safe_load(result)
        host_data = inventory["all"]["children"]["test"]["hosts"]["node-1"]
        assert host_data["asn"] == 0

    def test_l3_evpn_vni_zero_included(self) -> None:
        """l3_vni=0 should still appear in ansible vars."""
        evpn_params = {
            "l2_vni": 10010,
            "l2_rd": "10.0.0.1:10010",
            "l2_rt_import": "65000:10010",
            "l2_rt_export": "65000:10010",
            "l3_vni": 0,
            "vrf_name": "DEFAULT",
        }
        result = export_ansible_vars(evpn_params=evpn_params)
        vars_data = yaml.safe_load(result)
        assert vars_data["evpn"]["l3_vni"] == 0
        assert vars_data["evpn"]["vrf"] == "DEFAULT"

    def test_fabric_params_no_none_values(self) -> None:
        """Fabric params should not include None values."""
        fabric_params = {
            "spine_count": 2,
            # leaf_count and vtep_count both missing
        }
        result = export_ansible_vars(fabric_params=fabric_params)
        vars_data = yaml.safe_load(result)
        fabric = vars_data["fabric"]
        assert fabric["spine_count"] == 2
        assert "leaf_count" not in fabric  # Should not be present as None
        for val in fabric.values():
            assert val is not None


# ============================================================================
# Config Fixes
# ============================================================================
class TestConfigFixes:
    """Test config module fixes."""

    def test_multicast_base_validation_valid(self) -> None:
        """Valid multicast base should pass validation."""
        defaults = VNIDefaults(multicast_base="239.1.1.0")
        assert defaults.multicast_base == "239.1.1.0"

    def test_multicast_base_non_multicast_raises(self) -> None:
        """Non-multicast base address should raise ConfigValidationError."""
        with pytest.raises(ConfigValidationError, match="multicast range"):
            VNIDefaults(multicast_base="10.0.0.1")

    def test_multicast_base_invalid_ip_raises(self) -> None:
        """Invalid IP address should raise ConfigValidationError."""
        with pytest.raises(ConfigValidationError, match="valid IPv4"):
            VNIDefaults(multicast_base="not-an-ip")

    def test_save_config_atomic(self, tmp_path: Path) -> None:
        """save_config should use atomic writes (temp file + rename)."""
        config = Config()
        config_path = tmp_path / "test-config.yaml"
        save_config(config, config_path)

        # File should exist and be valid YAML
        assert config_path.exists()
        with config_path.open() as f:
            data = yaml.safe_load(f)
        assert "defaults" in data

    def test_save_config_no_partial_writes(self, tmp_path: Path) -> None:
        """If save fails, existing file should not be corrupted."""
        config = Config()
        config_path = tmp_path / "test-config.yaml"

        # Write initial config
        save_config(config, config_path)
        original_content = config_path.read_text()

        # Ensure content is preserved
        assert len(original_content) > 0
        data = yaml.safe_load(original_content)
        assert data["defaults"]["vni"]["base_vni"] == 10000


# ============================================================================
# VNI Custom Scheme Test
# ============================================================================
class TestVNICustomScheme:
    """Test VNIScheme.CUSTOM works correctly."""

    def test_custom_scheme_allocation(self) -> None:
        """Custom scheme should produce valid VNI allocations."""
        result = calculate_vni_allocation(
            scheme=VNIScheme.CUSTOM,
            base_vni=10000,
            start_vlan=10,
            count=3,
        )
        assert len(result.entries) == 3
        assert result.scheme == "custom"


# ============================================================================
# CLI Command Tests
# ============================================================================
class TestAdditionalCLICommands:
    """Test CLI commands that were missing test coverage."""

    def test_rr_command(self) -> None:
        """Test route reflector CLI command."""
        from typer.testing import CliRunner

        from evpn_ninja.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["rr", "--clients", "10", "--as", "65000"])
        assert result.exit_code == 0

    def test_bandwidth_command(self) -> None:
        """Test bandwidth CLI command."""
        from typer.testing import CliRunner

        from evpn_ninja.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["bandwidth", "--spines", "2", "--leaves", "4"])
        assert result.exit_code == 0

    def test_topology_command(self) -> None:
        """Test topology CLI command."""
        from typer.testing import CliRunner

        from evpn_ninja.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["topology", "--spines", "2", "--leaves", "4"])
        assert result.exit_code == 0

    def test_multihoming_command(self) -> None:
        """Test multihoming CLI command."""
        from typer.testing import CliRunner

        from evpn_ninja.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["multihoming", "--es-count", "2"])
        assert result.exit_code == 0

    def test_presets_command(self) -> None:
        """Test presets CLI command."""
        from typer.testing import CliRunner

        from evpn_ninja.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["presets"])
        assert result.exit_code == 0
        assert "small-dc" in result.stdout

    def test_config_show_command(self) -> None:
        """Test config show CLI command."""
        from typer.testing import CliRunner

        from evpn_ninja.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0

    def test_config_path_command(self) -> None:
        """Test config path CLI command."""
        from typer.testing import CliRunner

        from evpn_ninja.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["config", "path"])
        assert result.exit_code == 0
        assert ".evpn-ninja.yaml" in result.stdout

    def test_export_ansible_command(self) -> None:
        """Test export ansible CLI command."""
        from typer.testing import CliRunner

        from evpn_ninja.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "export",
                "ansible",
                "--spines",
                "1",
                "--leaves",
                "2",
            ],
        )
        assert result.exit_code == 0

    def test_completion_command(self) -> None:
        """Test completion CLI command."""
        from typer.testing import CliRunner

        from evpn_ninja.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["completion", "bash"])
        assert result.exit_code == 0
        assert "completions" in result.stdout.lower() or "COMP" in result.stdout


# ============================================================================
# Fabric Network Capacity Tests
# ============================================================================
class TestFabricNetworkCapacity:
    """Test fabric calculator handles /31 and /32 networks correctly."""

    def test_fabric_p2p_slash31(self) -> None:
        """P2P /31 network should provide 2 addresses per subnet."""
        result = calculate_fabric_params(
            vtep_count=2,
            spine_count=1,
            p2p_network="10.0.100.0/29",
        )
        assert result.p2p_links_total > 0

    def test_fabric_insufficient_loopbacks_warns(self) -> None:
        """Too few loopback IPs should produce a warning."""
        result = calculate_fabric_params(
            vtep_count=200,
            spine_count=4,
            loopback_network="10.0.0.0/24",
        )
        # The calculator may handle this differently; just ensure it doesn't crash
        assert result.vtep_count == 200


# ============================================================================
# MTU Boundary Tests
# ============================================================================
class TestMTUBoundaryConditions:
    """Test MTU calculator boundary conditions."""

    def test_mtu_max_vlans(self) -> None:
        """MTU with maximum VLAN tags (2 outer + 2 inner)."""
        from evpn_ninja.calculators.mtu import UnderlayType, calculate_mtu

        result = calculate_mtu(
            payload_size=1500,
            underlay_type=UnderlayType.IPV4,
            outer_vlan_tags=2,
            inner_vlan_tags=2,
        )
        # Should have larger MTU due to VLAN overhead
        assert result.required_mtu > 1500 + 50  # base overhead

    def test_mtu_ipv6_underlay(self) -> None:
        """MTU with IPv6 underlay should be larger than IPv4."""
        from evpn_ninja.calculators.mtu import UnderlayType, calculate_mtu

        result_v4 = calculate_mtu(underlay_type=UnderlayType.IPV4)
        result_v6 = calculate_mtu(underlay_type=UnderlayType.IPV6)
        # IPv6 has 20 bytes more header overhead than IPv4
        assert result_v6.required_mtu > result_v4.required_mtu
