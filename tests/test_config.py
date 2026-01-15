"""Tests for config module."""

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from evpn_ninja.config import (
    BUILTIN_PRESETS,
    Config,
    EBGPDefaults,
    EVPNDefaults,
    FabricDefaults,
    MTUDefaults,
    MulticastDefaults,
    OutputSettings,
    Preset,
    VNIDefaults,
    get_preset,
    list_presets,
    load_config,
    load_params_from_file,
    save_config,
)


class TestDefaultDataclasses:
    """Tests for default dataclass values."""

    def test_mtu_defaults(self) -> None:
        """Test MTUDefaults has correct default values."""
        defaults = MTUDefaults()
        assert defaults.payload_size == 1500
        assert defaults.underlay_type == "ipv4"
        assert defaults.outer_vlan_tags == 0
        assert defaults.inner_vlan_tags == 0

    def test_vni_defaults(self) -> None:
        """Test VNIDefaults has correct default values."""
        defaults = VNIDefaults()
        assert defaults.base_vni == 10000
        assert defaults.scheme == "vlan-based"
        assert defaults.start_vlan == 10
        assert defaults.count == 10
        assert defaults.multicast_base == "239.1.1.0"

    def test_fabric_defaults(self) -> None:
        """Test FabricDefaults has correct default values."""
        defaults = FabricDefaults()
        assert defaults.vtep_count == 4
        assert defaults.spine_count == 2
        assert defaults.vni_count == 100
        assert defaults.hosts_per_vtep == 50
        assert defaults.replication_mode == "ingress"
        assert defaults.loopback_network == "10.0.0.0/24"
        assert defaults.vtep_loopback_network == "10.0.1.0/24"
        assert defaults.p2p_network == "10.0.100.0/22"

    def test_evpn_defaults(self) -> None:
        """Test EVPNDefaults has correct default values."""
        defaults = EVPNDefaults()
        assert defaults.bgp_as == 65000
        assert defaults.loopback_ip == "10.0.0.1"
        assert defaults.vendors == []

    def test_ebgp_defaults(self) -> None:
        """Test EBGPDefaults has correct default values."""
        defaults = EBGPDefaults()
        assert defaults.spine_count == 2
        assert defaults.leaf_count == 4
        assert defaults.scheme == "private-4byte"
        assert defaults.spine_asn_same is True
        assert defaults.p2p_network == "10.0.100.0/22"

    def test_multicast_defaults(self) -> None:
        """Test MulticastDefaults has correct default values."""
        defaults = MulticastDefaults()
        assert defaults.vni_start == 10000
        assert defaults.vni_count == 100
        assert defaults.scheme == "one-to-one"
        assert defaults.base_group == "239.1.1.0"
        assert defaults.vnis_per_group == 10

    def test_output_settings_defaults(self) -> None:
        """Test OutputSettings has correct default values."""
        settings = OutputSettings()
        assert settings.format == "table"
        assert settings.no_color is False
        assert settings.verbose is False

    def test_preset_defaults(self) -> None:
        """Test Preset has correct default values."""
        preset = Preset(name="test")
        assert preset.name == "test"
        assert preset.description == ""
        assert preset.fabric == {}
        assert preset.ebgp == {}
        assert preset.evpn == {}
        assert preset.vni == {}
        assert preset.multicast == {}


class TestConfigFromDict:
    """Tests for Config.from_dict method."""

    def test_empty_dict(self) -> None:
        """Test creating Config from empty dict."""
        config = Config.from_dict({})
        assert isinstance(config.mtu, MTUDefaults)
        assert isinstance(config.vni, VNIDefaults)
        assert isinstance(config.fabric, FabricDefaults)

    def test_with_mtu_defaults(self) -> None:
        """Test creating Config with MTU defaults."""
        data: dict[str, Any] = {
            "defaults": {
                "mtu": {
                    "payload_size": 9000,
                    "underlay_type": "ipv6",
                }
            }
        }
        config = Config.from_dict(data)
        assert config.mtu.payload_size == 9000
        assert config.mtu.underlay_type == "ipv6"

    def test_with_vni_defaults(self) -> None:
        """Test creating Config with VNI defaults."""
        data: dict[str, Any] = {
            "defaults": {
                "vni": {
                    "base_vni": 20000,
                    "scheme": "tenant-based",
                }
            }
        }
        config = Config.from_dict(data)
        assert config.vni.base_vni == 20000
        assert config.vni.scheme == "tenant-based"

    def test_with_output_settings(self) -> None:
        """Test creating Config with output settings."""
        data: dict[str, Any] = {
            "output": {
                "format": "json",
                "no_color": True,
                "verbose": True,
            }
        }
        config = Config.from_dict(data)
        assert config.output.format == "json"
        assert config.output.no_color is True
        assert config.output.verbose is True

    def test_with_presets(self) -> None:
        """Test creating Config with presets."""
        data: dict[str, Any] = {
            "presets": {
                "custom-dc": {
                    "description": "Custom datacenter",
                    "fabric": {"vtep_count": 8},
                    "ebgp": {"scheme": "private-2byte"},
                }
            }
        }
        config = Config.from_dict(data)
        assert "custom-dc" in config.presets
        preset = config.presets["custom-dc"]
        assert preset.name == "custom-dc"
        assert preset.description == "Custom datacenter"
        assert preset.fabric == {"vtep_count": 8}
        assert preset.ebgp == {"scheme": "private-2byte"}

    def test_all_sections(self) -> None:
        """Test creating Config with all sections."""
        data: dict[str, Any] = {
            "defaults": {
                "mtu": {"payload_size": 1400},
                "vni": {"base_vni": 15000},
                "fabric": {"vtep_count": 16},
                "evpn": {"bgp_as": 65001},
                "ebgp": {"spine_count": 4},
                "multicast": {"scheme": "shared"},
            },
            "output": {"format": "yaml"},
            "presets": {
                "test": {"description": "Test preset"}
            },
        }
        config = Config.from_dict(data)
        assert config.mtu.payload_size == 1400
        assert config.vni.base_vni == 15000
        assert config.fabric.vtep_count == 16
        assert config.evpn.bgp_as == 65001
        assert config.ebgp.spine_count == 4
        assert config.multicast.scheme == "shared"
        assert config.output.format == "yaml"
        assert "test" in config.presets


class TestLoadConfig:
    """Tests for load_config function."""

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        """Test loading from nonexistent file returns default config."""
        config = load_config(tmp_path / "nonexistent.yaml")
        assert isinstance(config, Config)
        assert config.mtu.payload_size == 1500  # Default value

    def test_valid_config_file(self, tmp_path: Path) -> None:
        """Test loading valid config file."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("""
defaults:
  mtu:
    payload_size: 9000
  vni:
    base_vni: 20000
output:
  format: json
""")
        config = load_config(config_path)
        assert config.mtu.payload_size == 9000
        assert config.vni.base_vni == 20000
        assert config.output.format == "json"

    def test_invalid_yaml_file(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test loading invalid YAML returns default config with warning."""
        config_path = tmp_path / "invalid.yaml"
        config_path.write_text("invalid: yaml: content: [")

        config = load_config(config_path)

        # Should return default config
        assert isinstance(config, Config)
        assert config.mtu.payload_size == 1500

        # Should print warning to stderr
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "Invalid YAML" in captured.err

    def test_empty_yaml_file(self, tmp_path: Path) -> None:
        """Test loading empty YAML file returns default config."""
        config_path = tmp_path / "empty.yaml"
        config_path.write_text("")

        config = load_config(config_path)
        assert isinstance(config, Config)

    def test_default_config_path(self) -> None:
        """Test load_config uses default path when none specified."""
        with patch("evpn_ninja.config.DEFAULT_CONFIG_PATH") as mock_path:
            mock_path.exists.return_value = False
            config = load_config()
            assert isinstance(config, Config)


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Test saving config and loading it back."""
        config_path = tmp_path / "config.yaml"

        config = Config()
        config.mtu.payload_size = 9000
        config.vni.base_vni = 25000
        config.output.format = "yaml"

        save_config(config, config_path)

        loaded = load_config(config_path)
        assert loaded.mtu.payload_size == 9000
        assert loaded.vni.base_vni == 25000
        assert loaded.output.format == "yaml"

    def test_save_with_presets(self, tmp_path: Path) -> None:
        """Test saving config with presets."""
        config_path = tmp_path / "config.yaml"

        config = Config()
        config.presets["test"] = Preset(
            name="test",
            description="Test preset",
            fabric={"vtep_count": 10},
        )

        save_config(config, config_path)

        loaded = load_config(config_path)
        assert "test" in loaded.presets
        assert loaded.presets["test"].description == "Test preset"
        assert loaded.presets["test"].fabric == {"vtep_count": 10}

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Test save_config creates parent directories."""
        config_path = tmp_path / "subdir" / "deep" / "config.yaml"

        config = Config()
        save_config(config, config_path)

        assert config_path.exists()

    def test_save_all_fields(self, tmp_path: Path) -> None:
        """Test saving config preserves all fields."""
        config_path = tmp_path / "config.yaml"

        config = Config()
        config.mtu = MTUDefaults(
            payload_size=1400,
            underlay_type="ipv6",
            outer_vlan_tags=1,
            inner_vlan_tags=2,
        )
        config.fabric = FabricDefaults(
            vtep_count=32,
            spine_count=4,
            vni_count=500,
            hosts_per_vtep=100,
            replication_mode="multicast",
            loopback_network="172.16.0.0/24",
            vtep_loopback_network="172.16.1.0/24",
            p2p_network="172.16.100.0/22",
        )

        save_config(config, config_path)

        loaded = load_config(config_path)
        assert loaded.mtu.payload_size == 1400
        assert loaded.mtu.underlay_type == "ipv6"
        assert loaded.mtu.outer_vlan_tags == 1
        assert loaded.mtu.inner_vlan_tags == 2
        assert loaded.fabric.vtep_count == 32
        assert loaded.fabric.spine_count == 4


class TestLoadParamsFromFile:
    """Tests for load_params_from_file function."""

    def test_valid_params_file(self, tmp_path: Path) -> None:
        """Test loading valid params file."""
        params_path = tmp_path / "params.yaml"
        params_path.write_text("""
vtep_count: 8
spine_count: 2
vni_count: 200
""")
        params = load_params_from_file(params_path)
        assert params["vtep_count"] == 8
        assert params["spine_count"] == 2
        assert params["vni_count"] == 200

    def test_empty_params_file(self, tmp_path: Path) -> None:
        """Test loading empty params file returns empty dict."""
        params_path = tmp_path / "params.yaml"
        params_path.write_text("")

        params = load_params_from_file(params_path)
        assert params == {}

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        """Test loading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_params_from_file(tmp_path / "nonexistent.yaml")

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        """Test loading invalid YAML raises YAMLError."""
        params_path = tmp_path / "invalid.yaml"
        params_path.write_text("invalid: yaml: [")

        with pytest.raises(yaml.YAMLError):
            load_params_from_file(params_path)


class TestPresetFunctions:
    """Tests for preset-related functions."""

    def test_get_preset_exists(self) -> None:
        """Test getting existing preset."""
        config = Config()
        config.presets["test"] = Preset(name="test", description="Test")

        preset = get_preset(config, "test")
        assert preset is not None
        assert preset.name == "test"

    def test_get_preset_not_exists(self) -> None:
        """Test getting nonexistent preset returns None."""
        config = Config()
        preset = get_preset(config, "nonexistent")
        assert preset is None

    def test_list_presets_empty(self) -> None:
        """Test listing presets when empty."""
        config = Config()
        presets = list_presets(config)
        assert presets == []

    def test_list_presets_multiple(self) -> None:
        """Test listing multiple presets."""
        config = Config()
        config.presets["a"] = Preset(name="a")
        config.presets["b"] = Preset(name="b")
        config.presets["c"] = Preset(name="c")

        presets = list_presets(config)
        assert set(presets) == {"a", "b", "c"}


class TestBuiltinPresets:
    """Tests for BUILTIN_PRESETS constant."""

    def test_builtin_presets_exist(self) -> None:
        """Test builtin presets are defined."""
        assert "small-dc" in BUILTIN_PRESETS
        assert "medium-dc" in BUILTIN_PRESETS
        assert "large-dc" in BUILTIN_PRESETS
        assert "multi-tenant" in BUILTIN_PRESETS
        assert "campus" in BUILTIN_PRESETS

    def test_small_dc_preset(self) -> None:
        """Test small-dc preset values."""
        preset = BUILTIN_PRESETS["small-dc"]
        assert preset.name == "small-dc"
        assert preset.fabric["spine_count"] == 2
        assert preset.fabric["vtep_count"] == 4
        assert preset.fabric["vni_count"] == 100

    def test_large_dc_preset(self) -> None:
        """Test large-dc preset values."""
        preset = BUILTIN_PRESETS["large-dc"]
        assert preset.name == "large-dc"
        assert preset.fabric["spine_count"] == 4
        assert preset.fabric["vtep_count"] == 64
        assert preset.fabric["vni_count"] == 4000

    def test_multi_tenant_preset(self) -> None:
        """Test multi-tenant preset values."""
        preset = BUILTIN_PRESETS["multi-tenant"]
        assert preset.vni["scheme"] == "tenant-based"

    def test_all_presets_have_descriptions(self) -> None:
        """Test all builtin presets have descriptions."""
        for name, preset in BUILTIN_PRESETS.items():
            assert preset.description, f"Preset {name} missing description"


class TestConfigReadError:
    """Tests for config file read errors."""

    @pytest.mark.skipif(sys.platform == "win32", reason="chmod doesn't work on Windows")
    def test_permission_denied(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test handling of permission denied error."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("test: value")
        config_path.chmod(0o000)

        try:
            config = load_config(config_path)

            # Should return default config
            assert isinstance(config, Config)

            # Should print warning
            captured = capsys.readouterr()
            assert "Warning" in captured.err
        finally:
            # Restore permissions for cleanup
            config_path.chmod(0o644)


class TestConfigValidation:
    """Tests for config validation."""

    def test_mtu_payload_size_negative_rejected(self) -> None:
        """Test that negative payload size is rejected."""
        from evpn_ninja.config import ConfigValidationError

        with pytest.raises(ConfigValidationError, match="payload_size must be positive"):
            MTUDefaults(payload_size=-1)

    def test_mtu_payload_size_zero_rejected(self) -> None:
        """Test that zero payload size is rejected."""
        from evpn_ninja.config import ConfigValidationError

        with pytest.raises(ConfigValidationError, match="payload_size must be positive"):
            MTUDefaults(payload_size=0)

    def test_mtu_invalid_underlay_type_rejected(self) -> None:
        """Test that invalid underlay type is rejected."""
        from evpn_ninja.config import ConfigValidationError

        with pytest.raises(ConfigValidationError, match="underlay_type must be one of"):
            MTUDefaults(underlay_type="invalid")

    def test_mtu_vlan_tags_out_of_range_rejected(self) -> None:
        """Test that vlan tags out of range are rejected."""
        from evpn_ninja.config import ConfigValidationError

        with pytest.raises(ConfigValidationError, match="outer_vlan_tags must be between"):
            MTUDefaults(outer_vlan_tags=3)

    def test_vni_invalid_scheme_rejected(self) -> None:
        """Test that invalid VNI scheme is rejected."""
        from evpn_ninja.config import ConfigValidationError

        with pytest.raises(ConfigValidationError, match="scheme must be one of"):
            VNIDefaults(scheme="invalid-scheme")

    def test_vni_base_vni_too_large_rejected(self) -> None:
        """Test that base_vni exceeding max is rejected."""
        from evpn_ninja.config import ConfigValidationError

        with pytest.raises(ConfigValidationError, match="base_vni must be between"):
            VNIDefaults(base_vni=16777216)

    def test_vni_start_vlan_out_of_range_rejected(self) -> None:
        """Test that start_vlan out of range is rejected."""
        from evpn_ninja.config import ConfigValidationError

        with pytest.raises(ConfigValidationError, match="start_vlan must be between"):
            VNIDefaults(start_vlan=5000)

    def test_fabric_invalid_replication_mode_rejected(self) -> None:
        """Test that invalid replication mode is rejected."""
        from evpn_ninja.config import ConfigValidationError

        with pytest.raises(ConfigValidationError, match="replication_mode must be one of"):
            FabricDefaults(replication_mode="invalid")

    def test_fabric_negative_hosts_rejected(self) -> None:
        """Test that negative hosts_per_vtep is rejected."""
        from evpn_ninja.config import ConfigValidationError

        with pytest.raises(ConfigValidationError, match="hosts_per_vtep must be non-negative"):
            FabricDefaults(hosts_per_vtep=-1)

    def test_evpn_bgp_as_too_large_rejected(self) -> None:
        """Test that BGP AS exceeding max is rejected."""
        from evpn_ninja.config import ConfigValidationError

        with pytest.raises(ConfigValidationError, match="bgp_as must be between"):
            EVPNDefaults(bgp_as=4294967296)

    def test_ebgp_invalid_scheme_rejected(self) -> None:
        """Test that invalid eBGP scheme is rejected."""
        from evpn_ninja.config import ConfigValidationError

        with pytest.raises(ConfigValidationError, match="scheme must be one of"):
            EBGPDefaults(scheme="invalid-asn-scheme")

    def test_multicast_invalid_scheme_rejected(self) -> None:
        """Test that invalid multicast scheme is rejected."""
        from evpn_ninja.config import ConfigValidationError

        with pytest.raises(ConfigValidationError, match="scheme must be one of"):
            MulticastDefaults(scheme="invalid-scheme")

    def test_output_invalid_format_rejected(self) -> None:
        """Test that invalid output format is rejected."""
        from evpn_ninja.config import ConfigValidationError

        with pytest.raises(ConfigValidationError, match="format must be one of"):
            OutputSettings(format="invalid")

    def test_config_from_dict_invalid_values_uses_defaults(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that invalid values in config file fall back to defaults."""
        data = {
            "defaults": {
                "mtu": {
                    "payload_size": -100,  # Invalid - negative
                }
            }
        }

        config = Config.from_dict(data)

        # Should use default values
        assert config.mtu.payload_size == 1500

        # Should print warning
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "Invalid configuration" in captured.err
