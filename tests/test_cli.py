"""Tests for CLI commands."""

import pytest
from typer.testing import CliRunner
from evpn_ninja.cli import app


runner = CliRunner()


class TestCLI:
    """Test cases for CLI commands."""

    def test_help(self):
        """Test help command."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "VXLAN" in result.stdout or "vxlan" in result.stdout.lower()

    def test_version(self):
        """Test version flag."""
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0

    def test_mtu_command(self):
        """Test MTU calculator command."""
        result = runner.invoke(app, ["mtu", "--payload", "1500"])
        assert result.exit_code == 0

    def test_mtu_with_vlans(self):
        """Test MTU command with VLAN options."""
        result = runner.invoke(app, [
            "mtu",
            "--payload", "1500",
            "--outer-vlans", "1",
            "--inner-vlans", "1",
        ])
        assert result.exit_code == 0

    def test_mtu_json_output(self):
        """Test MTU command with JSON output."""
        result = runner.invoke(app, [
            "mtu",
            "--payload", "1500",
            "--output", "json",
        ])
        assert result.exit_code == 0
        assert "{" in result.stdout

    def test_mtu_yaml_output(self):
        """Test MTU command with YAML output."""
        result = runner.invoke(app, [
            "mtu",
            "--payload", "1500",
            "--output", "yaml",
        ])
        assert result.exit_code == 0

    def test_vni_command(self):
        """Test VNI calculator command."""
        result = runner.invoke(app, [
            "vni",
            "--base-vni", "10000",
            "--tenant-id", "1",
            "--start-vlan", "10",
            "--count", "5",
        ])
        assert result.exit_code == 0

    def test_fabric_command(self):
        """Test Fabric calculator command."""
        result = runner.invoke(app, [
            "fabric",
            "--vteps", "4",
            "--spines", "2",
            "--vnis", "100",
            "--hosts", "50",
        ])
        assert result.exit_code == 0

    def test_evpn_command(self):
        """Test EVPN calculator command."""
        result = runner.invoke(app, [
            "evpn",
            "--as", "65000",
            "--loopback", "10.0.0.1",
            "--l2-vni", "10010",
            "--vlan", "10",
        ])
        assert result.exit_code == 0

    def test_evpn_with_vendor(self):
        """Test EVPN command with vendor option."""
        result = runner.invoke(app, [
            "evpn",
            "--as", "65000",
            "--loopback", "10.0.0.1",
            "--l2-vni", "10010",
            "--vlan", "10",
            "--vendor", "arista",
        ])
        assert result.exit_code == 0

    def test_ebgp_command(self):
        """Test eBGP calculator command."""
        result = runner.invoke(app, [
            "ebgp",
            "--spines", "2",
            "--leaves", "4",
        ])
        assert result.exit_code == 0

    def test_multicast_command(self):
        """Test Multicast calculator command."""
        result = runner.invoke(app, [
            "multicast",
            "--vni-start", "10000",
            "--vni-count", "10",
        ])
        assert result.exit_code == 0

    def test_no_color_option(self):
        """Test --no-color global option."""
        result = runner.invoke(app, [
            "--no-color",
            "mtu",
            "--payload", "1500",
        ])
        assert result.exit_code == 0

    def test_verbose_option(self):
        """Test --verbose option."""
        result = runner.invoke(app, [
            "-v",
            "mtu",
            "--payload", "1500",
        ])
        assert result.exit_code == 0

    def test_invalid_command(self):
        """Test invalid command."""
        result = runner.invoke(app, ["invalid_command"])
        assert result.exit_code != 0

    def test_mtu_help(self):
        """Test MTU command help."""
        result = runner.invoke(app, ["mtu", "--help"])
        assert result.exit_code == 0
        assert "payload" in result.stdout.lower()

    def test_vni_json_output(self):
        """Test VNI command with JSON output."""
        result = runner.invoke(app, [
            "vni",
            "--count", "3",
            "--output", "json",
        ])
        assert result.exit_code == 0
        assert "{" in result.stdout

    def test_fabric_json_output(self):
        """Test Fabric command with JSON output."""
        result = runner.invoke(app, [
            "fabric",
            "--vteps", "2",
            "--spines", "1",
            "--output", "json",
        ])
        assert result.exit_code == 0
        assert "{" in result.stdout
