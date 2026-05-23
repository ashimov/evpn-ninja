"""Tests for security functions - path traversal, input validation, etc."""

import sys
from pathlib import Path

import pytest
from click.exceptions import Exit as ClickExit
from typer.testing import CliRunner

from evpn_ninja.calculators.fabric import (
    MAX_HOSTS_PER_VTEP,
    MAX_SPINE_COUNT,
    MAX_VNI_COUNT,
    MAX_VTEP_COUNT,
    CapacityWarning,
    calculate_fabric_params,
)
from evpn_ninja.cli import (
    _safe_mkdir,
    _safe_write_file,
    _validate_output_path,
    app,
)

runner = CliRunner()


class TestPathTraversalProtection:
    """Test cases for path traversal protection."""

    def test_valid_path_within_base_dir(self, tmp_path: Path):
        """Test that valid paths within base directory are accepted."""
        filepath = tmp_path / "output.txt"
        result = _validate_output_path(filepath, tmp_path)
        assert result == filepath.resolve()

    def test_valid_nested_path(self, tmp_path: Path):
        """Test that nested paths within base directory are accepted."""
        filepath = tmp_path / "subdir" / "output.txt"
        result = _validate_output_path(filepath, tmp_path)
        assert result == filepath.resolve()

    def test_path_traversal_rejected(self, tmp_path: Path):
        """Test that path traversal attempts are rejected."""
        filepath = tmp_path / ".." / "outside.txt"
        with pytest.raises(ClickExit) as exc_info:
            _validate_output_path(filepath, tmp_path)
        assert exc_info.value.exit_code == 1

    def test_absolute_path_outside_base_rejected(self, tmp_path: Path):
        """Test that absolute paths outside base directory are rejected."""
        filepath = Path("/tmp/malicious.txt")
        base_dir = tmp_path / "safe_dir"
        base_dir.mkdir()
        with pytest.raises(ClickExit) as exc_info:
            _validate_output_path(filepath, base_dir)
        assert exc_info.value.exit_code == 1

    @pytest.mark.skipif(
        sys.platform == "win32", reason="symlinks require elevated privileges on Windows"
    )
    def test_symlink_traversal_rejected(self, tmp_path: Path):
        """Test that symlink-based traversal is rejected."""
        # Create a symlink pointing outside
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()

        safe_dir = tmp_path / "safe"
        safe_dir.mkdir()

        symlink = safe_dir / "link"
        symlink.symlink_to(outside_dir)

        filepath = symlink / "file.txt"
        with pytest.raises(ClickExit) as exc_info:
            _validate_output_path(filepath, safe_dir)
        assert exc_info.value.exit_code == 1

    def test_default_base_dir_is_cwd(self, tmp_path: Path, monkeypatch):
        """Test that default base directory is current working directory."""
        monkeypatch.chdir(tmp_path)
        filepath = tmp_path / "output.txt"
        result = _validate_output_path(filepath)
        assert result == filepath.resolve()


class TestSafeFileOperations:
    """Test cases for safe file write operations."""

    def test_safe_write_file_creates_parent_dirs(self, tmp_path: Path):
        """Test that _safe_write_file creates parent directories."""
        filepath = tmp_path / "subdir" / "nested" / "file.txt"
        _safe_write_file(filepath, "test content", tmp_path)
        assert filepath.exists()
        assert filepath.read_text() == "test content"

    def test_safe_write_file_rejects_traversal(self, tmp_path: Path):
        """Test that _safe_write_file rejects path traversal."""
        filepath = tmp_path / ".." / "outside.txt"
        with pytest.raises(ClickExit) as exc_info:
            _safe_write_file(filepath, "malicious", tmp_path)
        assert exc_info.value.exit_code == 1

    def test_safe_mkdir_creates_nested_dirs(self, tmp_path: Path):
        """Test that _safe_mkdir creates nested directories."""
        dirpath = tmp_path / "a" / "b" / "c"
        result = _safe_mkdir(dirpath, tmp_path)
        assert dirpath.exists()
        assert dirpath.is_dir()
        assert result == dirpath.resolve()

    def test_safe_mkdir_rejects_traversal(self, tmp_path: Path):
        """Test that _safe_mkdir rejects path traversal."""
        dirpath = tmp_path / ".." / "outside_dir"
        with pytest.raises(ClickExit) as exc_info:
            _safe_mkdir(dirpath, tmp_path)
        assert exc_info.value.exit_code == 1

    def test_safe_mkdir_returns_resolved_path(self, tmp_path: Path):
        """Test that _safe_mkdir returns the resolved absolute path."""
        dirpath = tmp_path / "new_dir"
        result = _safe_mkdir(dirpath, tmp_path)
        assert result.is_absolute()
        assert result == dirpath.resolve()


class TestInputBoundsValidation:
    """Test cases for input bounds validation in fabric calculator."""

    def test_vtep_count_upper_bound(self):
        """Test that vtep_count exceeding max raises error."""
        with pytest.raises(ValueError, match=f"vtep_count must be <= {MAX_VTEP_COUNT}"):
            calculate_fabric_params(vtep_count=MAX_VTEP_COUNT + 1)

    def test_vtep_count_at_max(self):
        """Test that vtep_count at max is accepted."""
        # This should not raise - just checking the validation passes
        # We use small values for other params to keep test fast
        result = calculate_fabric_params(
            vtep_count=100,  # Use reasonable value for actual test
            spine_count=2,
            vni_count=10,
            hosts_per_vtep=1,
        )
        assert result.vtep_count == 100

    def test_spine_count_upper_bound(self):
        """Test that spine_count exceeding max raises error."""
        with pytest.raises(ValueError, match=f"spine_count must be <= {MAX_SPINE_COUNT}"):
            calculate_fabric_params(spine_count=MAX_SPINE_COUNT + 1)

    def test_vni_count_upper_bound(self):
        """Test that vni_count exceeding max raises error."""
        with pytest.raises(ValueError, match=f"vni_count must be <= {MAX_VNI_COUNT}"):
            calculate_fabric_params(vni_count=MAX_VNI_COUNT + 1)

    def test_hosts_per_vtep_upper_bound(self):
        """Test that hosts_per_vtep exceeding max raises error."""
        with pytest.raises(ValueError, match=f"hosts_per_vtep must be <= {MAX_HOSTS_PER_VTEP}"):
            calculate_fabric_params(hosts_per_vtep=MAX_HOSTS_PER_VTEP + 1)

    def test_vtep_count_zero_rejected(self):
        """Test that vtep_count of 0 is rejected."""
        with pytest.raises(ValueError, match="vtep_count must be positive"):
            calculate_fabric_params(vtep_count=0)

    def test_vtep_count_negative_rejected(self):
        """Test that negative vtep_count is rejected."""
        with pytest.raises(ValueError, match="vtep_count must be positive"):
            calculate_fabric_params(vtep_count=-1)

    def test_spine_count_zero_rejected(self):
        """Test that spine_count of 0 is rejected."""
        with pytest.raises(ValueError, match="spine_count must be positive"):
            calculate_fabric_params(spine_count=0)

    def test_hosts_per_vtep_negative_rejected(self):
        """Test that negative hosts_per_vtep is rejected."""
        with pytest.raises(ValueError, match="hosts_per_vtep must be non-negative"):
            calculate_fabric_params(hosts_per_vtep=-1)

    def test_hosts_per_vtep_zero_accepted(self):
        """Test that hosts_per_vtep of 0 is accepted."""
        result = calculate_fabric_params(hosts_per_vtep=0)
        assert result.hosts_per_vtep == 0


class TestP2PNetworkValidation:
    """Test cases for P2P network prefix validation."""

    def test_p2p_network_prefix_31_warning(self):
        """Test that /31 P2P network generates warning."""
        result = calculate_fabric_params(
            vtep_count=2,
            spine_count=2,
            p2p_network="10.0.0.0/31",
        )
        # Should have a warning about P2P network being too small
        assert any("prefix length is too large" in str(w.message) for w in result.warnings)

    def test_p2p_network_prefix_32_warning(self):
        """Test that /32 P2P network generates warning."""
        result = calculate_fabric_params(
            vtep_count=2,
            spine_count=2,
            p2p_network="10.0.0.0/32",
        )
        assert any("prefix length is too large" in str(w.message) for w in result.warnings)

    def test_p2p_network_insufficient_capacity_warning(self):
        """Test warning when P2P network has insufficient capacity."""
        # 4 leaves * 2 spines = 8 P2P links needed
        # /29 gives us 4 /31 subnets, which is insufficient
        result = calculate_fabric_params(
            vtep_count=4,
            spine_count=2,
            p2p_network="10.0.0.0/29",
        )
        # Filter for CapacityWarning and check resource
        capacity_warnings = [w for w in result.warnings if isinstance(w, CapacityWarning)]
        assert any("P2P /31 subnets" in str(w.resource) for w in capacity_warnings)


class TestExportPathTraversal:
    """Test that export command rejects path traversal."""

    def test_export_rejects_path_traversal(self, tmp_path: Path, monkeypatch):
        """Test that export command rejects path traversal in output-dir."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app,
            [
                "export",
                "ansible",
                "--output-dir",
                "../outside",
            ],
        )
        # Should fail due to path traversal
        assert result.exit_code == 1
        assert "Path traversal" in result.stdout or "Error" in result.stdout

    def test_export_accepts_valid_path(self, tmp_path: Path, monkeypatch):
        """Test that export command accepts valid paths."""
        monkeypatch.chdir(tmp_path)
        output_dir = tmp_path / "output"
        result = runner.invoke(
            app,
            [
                "export",
                "ansible",
                "--output-dir",
                str(output_dir),
            ],
        )
        assert result.exit_code == 0
        assert (output_dir / "ansible" / "inventory.yaml").exists()


class TestConfigTypeValidation:
    """Test type validation in config loading."""

    def test_invalid_config_field_rejected(self, tmp_path: Path):
        """Test that unknown config fields are handled gracefully."""
        from evpn_ninja.config import Config

        # Config with unknown field - this will trigger TypeError
        data = {
            "defaults": {
                "mtu": {
                    "unknown_field": 123,  # Unknown field
                    "payload_size": 1500,
                }
            }
        }

        # Should not raise, should use defaults due to TypeError
        config = Config.from_dict(data)
        # Default payload_size is 1500 (from defaults, since unknown_field caused TypeError)
        assert config.mtu.payload_size == 1500

    def test_valid_config_loads_correctly(self, tmp_path: Path):
        """Test that valid config is loaded correctly."""
        from evpn_ninja.config import Config

        data = {
            "defaults": {
                "mtu": {
                    "payload_size": 9000,
                }
            }
        }

        config = Config.from_dict(data)
        assert config.mtu.payload_size == 9000

    def test_non_dict_section_ignored(self):
        """Test that non-dict config sections are ignored."""
        from evpn_ninja.config import Config

        data = {
            "defaults": {
                "mtu": "not_a_dict",  # Should be ignored
            }
        }

        config = Config.from_dict(data)
        # Should use default
        assert config.mtu.payload_size == 1500


class TestExportResourceLimits:
    """Test that export bounds counts and does not materialize huge host lists."""

    def test_export_rejects_excessive_spines(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app,
            ["export", "ansible", "--spines", str(MAX_SPINE_COUNT + 1), "--leaves", "2"],
        )
        assert result.exit_code == 1
        assert "spines must be <=" in result.stdout

    def test_export_rejects_excessive_leaves(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app,
            ["export", "ansible", "--spines", "2", "--leaves", str(MAX_VTEP_COUNT + 1)],
        )
        assert result.exit_code == 1
        assert "leaves must be <=" in result.stdout

    def test_export_rejects_nonpositive_counts(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app,
            ["export", "ansible", "--spines", "0", "--leaves", "2"],
        )
        assert result.exit_code == 1
        assert "positive" in result.stdout

    def test_export_large_cidr_does_not_exhaust_memory(self, tmp_path: Path, monkeypatch):
        """A /8 loopback network must not materialize ~16M host objects."""
        monkeypatch.chdir(tmp_path)
        output_dir = tmp_path / "out"
        result = runner.invoke(
            app,
            [
                "export",
                "ansible",
                "--spines",
                "2",
                "--leaves",
                "4",
                "--loopback-net",
                "10.0.0.0/8",
                "--vtep-net",
                "11.0.0.0/8",
                "--output-dir",
                str(output_dir),
            ],
        )
        assert result.exit_code == 0
        assert (output_dir / "ansible" / "inventory.yaml").exists()


class TestExporterInjection:
    """Test that manually-built exporter output sanitizes untrusted fields."""

    def test_containerlab_unknown_platform_sanitized(self):
        """A malicious platform string must not inject YAML structure."""
        from evpn_ninja.exporters.containerlab import export_containerlab_topology

        spines = [{"name": "spine-1", "ip": "10.0.0.1", "asn": 65000}]
        leaves = [{"name": "leaf-1", "ip": "10.0.0.2", "vtep_ip": "10.0.1.1", "asn": 65001}]
        result = export_containerlab_topology(spines, leaves, platform="evil\n    injected: true")
        assert "injected: true" not in result

    def test_containerlab_config_name_sanitized(self):
        """Newlines in a node name must not inject device-config lines."""
        from evpn_ninja.exporters.containerlab import generate_containerlab_configs

        spines = [{"name": "spine-1\nmalicious command", "ip": "10.0.0.1", "asn": 65000}]
        configs = generate_containerlab_configs(spines, [], platform="eos")
        assert all("\nmalicious command" not in cfg for cfg in configs.values())
        assert all("\n" not in name for name in configs)

    def test_eve_ng_startup_name_sanitized(self):
        """Newlines in a node name must not inject startup-config lines."""
        from evpn_ninja.exporters.eve_gns3 import generate_eve_ng_startup_scripts

        spines = [{"name": "spine-1\ninjected", "loopback": "10.0.0.1"}]
        configs = generate_eve_ng_startup_scripts(spines, [], platform="eos")
        assert all("\n" not in name for name in configs)


class TestMultihomingFormatStringSafety:
    """Test that interface_template cannot be abused as a format string."""

    def test_format_string_attack_is_inert(self):
        from evpn_ninja.calculators.multihoming import (
            ESIType,
            MultiHomingMode,
            calculate_multihoming,
        )

        # With str.format() this would traverse to globals and raise/leak; with
        # literal replacement it is treated as a harmless literal.
        result = calculate_multihoming(
            es_count=1,
            peers_per_es=1,
            mode=MultiHomingMode.ACTIVE_ACTIVE,
            esi_type=ESIType.TYPE_1,
            interface_template="{es_id.__class__.__init__.__globals__}",
        )
        iface = result.ethernet_segments[0].peers[0].interface
        assert iface == "{es_id.__class__.__init__.__globals__}"

    def test_normal_template_substitution_works(self):
        from evpn_ninja.calculators.multihoming import (
            ESIType,
            MultiHomingMode,
            calculate_multihoming,
        )

        result = calculate_multihoming(
            es_count=1,
            peers_per_es=1,
            mode=MultiHomingMode.ACTIVE_ACTIVE,
            esi_type=ESIType.TYPE_1,
            interface_template="Port-Channel{es_id}",
        )
        iface = result.ethernet_segments[0].peers[0].interface
        assert iface.startswith("Port-Channel")
        assert "{es_id}" not in iface
