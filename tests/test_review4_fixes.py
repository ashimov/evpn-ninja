"""Tests for fixes from the fourth code review round."""

from pathlib import Path

import pytest
import yaml

from evpn_ninja.calculators.bandwidth import calculate_bandwidth
from evpn_ninja.calculators.multicast import calculate_multicast_groups
from evpn_ninja.calculators.multihoming import (
    calculate_multihoming,
    generate_esi_type1,
)
from evpn_ninja.config import Config
from evpn_ninja.exporters.containerlab import export_containerlab_topology
from evpn_ninja.exporters.eve_gns3 import export_eve_ng_topology, export_gns3_topology


# ============================================================================
# LACP Port Key Validation
# ============================================================================
class TestLACPPortKeyValidation:
    """Test LACP port key overflow detection in ESI type-1 generation."""

    def test_port_key_max_valid(self) -> None:
        """Maximum valid port key (65535) should work."""
        esi = generate_esi_type1(lacp_port_key=0xFFFF, lacp_system_mac="00:00:00:00:00:01")
        assert len(esi.esi.split(":")) == 10

    def test_port_key_overflow_raises(self) -> None:
        """Port key > 65535 should raise ValueError."""
        with pytest.raises(ValueError, match="16-bit"):
            generate_esi_type1(lacp_port_key=0x10000, lacp_system_mac="00:00:00:00:00:01")

    def test_port_key_negative_raises(self) -> None:
        """Negative port key should raise ValueError."""
        with pytest.raises(ValueError, match="16-bit"):
            generate_esi_type1(lacp_port_key=-1, lacp_system_mac="00:00:00:00:00:01")


# ============================================================================
# Multicast VNI Range Validation
# ============================================================================
class TestMulticastVNIRangeValidation:
    """Test VNI end range validation in multicast calculator."""

    def test_vni_range_overflow_raises(self) -> None:
        """vni_start + vni_count exceeding max VNI should raise."""
        with pytest.raises(ValueError, match="exceeds maximum VNI"):
            calculate_multicast_groups(vni_start=16777200, vni_count=100)

    def test_vni_range_max_valid(self) -> None:
        """Exactly at boundary should work."""
        result = calculate_multicast_groups(vni_start=16777215, vni_count=1)
        assert len(result.mappings) == 1


# ============================================================================
# Bandwidth Input Validation
# ============================================================================
class TestBandwidthInputValidation:
    """Test bandwidth calculator rejects invalid inputs."""

    def test_spine_count_zero_raises(self) -> None:
        """spine_count=0 should raise ValueError."""
        with pytest.raises(ValueError, match="spine_count must be positive"):
            calculate_bandwidth(spine_count=0)

    def test_leaf_count_zero_raises(self) -> None:
        """leaf_count=0 should raise ValueError."""
        with pytest.raises(ValueError, match="leaf_count must be positive"):
            calculate_bandwidth(leaf_count=0)

    def test_uplink_count_zero_raises(self) -> None:
        """uplink_count_per_leaf=0 should raise ValueError."""
        with pytest.raises(ValueError, match="uplink_count_per_leaf must be positive"):
            calculate_bandwidth(uplink_count_per_leaf=0)

    def test_downlink_count_zero_raises(self) -> None:
        """downlink_count_per_leaf=0 should raise ValueError."""
        with pytest.raises(ValueError, match="downlink_count_per_leaf must be positive"):
            calculate_bandwidth(downlink_count_per_leaf=0)


# ============================================================================
# Multihoming Input Validation
# ============================================================================
class TestMultihomingInputValidation:
    """Test multihoming calculator rejects invalid inputs."""

    def test_es_count_zero_raises(self) -> None:
        """es_count=0 should raise ValueError."""
        with pytest.raises(ValueError, match="es_count must be positive"):
            calculate_multihoming(es_count=0)

    def test_peers_per_es_zero_raises(self) -> None:
        """peers_per_es=0 should raise ValueError."""
        with pytest.raises(ValueError, match="peers_per_es must be positive"):
            calculate_multihoming(peers_per_es=0)


# ============================================================================
# EVE-NG/GNS3 Name Collision Detection
# ============================================================================
class TestEveGns3NameCollision:
    """Test duplicate name detection in EVE-NG/GNS3 exporters."""

    def test_eve_ng_duplicate_name_raises(self) -> None:
        """Duplicate spine/leaf names should raise ValueError in EVE-NG."""
        spines = [{"name": "router-1"}]
        leaves = [{"name": "router-1"}]
        with pytest.raises(ValueError, match="collision"):
            export_eve_ng_topology(spines, leaves)

    def test_gns3_duplicate_name_raises(self) -> None:
        """Duplicate spine/leaf names should raise ValueError in GNS3."""
        spines = [{"name": "router-1"}]
        leaves = [{"name": "router-1"}]
        with pytest.raises(ValueError, match="collision"):
            export_gns3_topology(spines, leaves)

    def test_eve_ng_host_name_collision_raises(self) -> None:
        """Leaf named 'host-1' collides with auto-generated host name."""
        spines = [{"name": "spine-1"}]
        leaves = [{"name": "host-1"}]
        with pytest.raises(ValueError, match="collision"):
            export_eve_ng_topology(spines, leaves, include_hosts=True)

    def test_eve_ng_no_collision_without_hosts(self) -> None:
        """Leaf named 'host-1' is fine when include_hosts=False."""
        spines = [{"name": "spine-1"}]
        leaves = [{"name": "host-1"}]
        result = export_eve_ng_topology(spines, leaves, include_hosts=False)
        assert "host-1" in result


# ============================================================================
# Containerlab Host Name Collision
# ============================================================================
class TestContainerlabHostNameCollision:
    """Test containerlab detects host node name collisions."""

    def test_leaf_named_host_collides_with_auto_host(self) -> None:
        """Leaf named 'host-1' should collide with auto-generated host."""
        spines = [{"name": "spine-1"}]
        leaves = [{"name": "host-1"}]
        with pytest.raises(ValueError, match="collision"):
            export_containerlab_topology(spines, leaves, include_hosts=True, hosts_per_leaf=1)

    def test_no_collision_without_hosts(self) -> None:
        """Leaf named 'host-1' is fine when include_hosts=False."""
        spines = [{"name": "spine-1"}]
        leaves = [{"name": "host-1"}]
        result = export_containerlab_topology(spines, leaves, include_hosts=False)
        assert "host-1" in result


# ============================================================================
# Config Unknown Keys Handling
# ============================================================================
class TestConfigUnknownKeysHandling:
    """Test that unknown config keys are filtered, not causing full fallback."""

    def test_unknown_key_preserves_valid_settings(self, tmp_path: Path) -> None:
        """A typo in one key should not discard valid settings."""
        config_data = {
            "defaults": {
                "vni": {
                    "base_vni": 50000,
                    "unknown_typo_key": "value",
                }
            }
        }
        config_path = tmp_path / "test.yaml"
        config_path.write_text(yaml.dump(config_data))

        config = Config.from_dict(config_data)
        # Valid key should be preserved, not reset to default
        assert config.vni.base_vni == 50000

    def test_all_unknown_keys_returns_defaults(self) -> None:
        """Section with only unknown keys should use defaults."""
        config_data = {
            "defaults": {
                "vni": {
                    "bad_key_1": "a",
                    "bad_key_2": "b",
                }
            }
        }
        config = Config.from_dict(config_data)
        # All keys unknown -> filtered to empty -> defaults
        assert config.vni.base_vni == 10000  # default value


# ============================================================================
# CLI Export Network Validation
# ============================================================================
class TestCLIExportNetworkValidation:
    """Test CLI export validates network capacity."""

    def test_export_small_loopback_raises(self) -> None:
        """Loopback network too small for devices should raise exit."""
        from typer.testing import CliRunner

        from evpn_ninja.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "export",
                "ansible",
                "--spines",
                "4",
                "--leaves",
                "8",
                "--loopback-net",
                "10.0.0.0/28",  # only 14 usable IPs, need 12
            ],
        )
        # Should succeed since 14 >= 12
        assert result.exit_code == 0

    def test_export_tiny_loopback_fails(self) -> None:
        """Loopback network with insufficient IPs should fail."""
        from typer.testing import CliRunner

        from evpn_ninja.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "export",
                "ansible",
                "--spines",
                "4",
                "--leaves",
                "8",
                "--loopback-net",
                "10.0.0.0/30",  # only 2 usable IPs, need 12
            ],
        )
        assert result.exit_code == 1
        assert "usable IPs" in result.stdout

    def test_export_tiny_vtep_fails(self) -> None:
        """VTEP network with insufficient IPs should fail."""
        from typer.testing import CliRunner

        from evpn_ninja.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "export",
                "ansible",
                "--spines",
                "2",
                "--leaves",
                "4",
                "--vtep-net",
                "10.0.1.0/30",  # only 2 usable IPs, need 4
            ],
        )
        assert result.exit_code == 1
        assert "usable IPs" in result.stdout
