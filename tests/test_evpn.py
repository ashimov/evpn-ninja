"""Tests for EVPN Parameters calculator."""

import pytest
from evpn_ninja.calculators.evpn import (
    Vendor,
    calculate_evpn_params,
)


class TestEVPNCalculator:
    """Test cases for EVPN Parameters calculator."""

    def test_basic_evpn_calculation(self):
        """Test basic EVPN parameter calculation."""
        result = calculate_evpn_params(
            bgp_as=65000,
            loopback_ip="10.0.0.1",
            l2_vni=10010,
            vlan_id=10,
        )

        assert result.bgp_as == 65000
        assert result.loopback_ip == "10.0.0.1"
        assert result.l2_vni == 10010

    def test_route_distinguisher_format(self):
        """Test Route Distinguisher format."""
        result = calculate_evpn_params(
            bgp_as=65000,
            loopback_ip="10.0.0.1",
            l2_vni=10010,
            vlan_id=10,
        )

        # RD should be IP:VNI format
        assert "10.0.0.1" in result.l2_params.route_distinguisher
        assert "10010" in result.l2_params.route_distinguisher

    def test_route_target_format(self):
        """Test Route Target format."""
        result = calculate_evpn_params(
            bgp_as=65000,
            loopback_ip="10.0.0.1",
            l2_vni=10010,
            vlan_id=10,
        )

        # RT should be ASN:VNI format
        assert "65000" in result.l2_params.route_target_import
        assert "10010" in result.l2_params.route_target_import
        assert result.l2_params.route_target_import == result.l2_params.route_target_export

    def test_l3_vni_configuration(self):
        """Test L3 VNI configuration."""
        result = calculate_evpn_params(
            bgp_as=65000,
            loopback_ip="10.0.0.1",
            l2_vni=10010,
            vlan_id=10,
            l3_vni=50001,
            vrf_name="TENANT1",
        )

        assert result.l3_vni == 50001
        assert result.vrf_name == "TENANT1"
        assert result.l3_params is not None
        assert result.l3_params.vni_type == "L3"

    def test_arista_config_generation(self):
        """Test Arista EOS config generation."""
        result = calculate_evpn_params(
            bgp_as=65000,
            loopback_ip="10.0.0.1",
            l2_vni=10010,
            vlan_id=10,
            vendors=[Vendor.ARISTA],
        )

        arista_config = next((c for c in result.configs if c.vendor == "arista"), None)
        assert arista_config is not None
        assert "vlan 10" in arista_config.config.lower()
        assert "vxlan" in arista_config.config.lower()

    def test_cisco_nxos_config_generation(self):
        """Test Cisco NX-OS config generation."""
        result = calculate_evpn_params(
            bgp_as=65000,
            loopback_ip="10.0.0.1",
            l2_vni=10010,
            vlan_id=10,
            vendors=[Vendor.CISCO_NXOS],
        )

        nxos_config = next((c for c in result.configs if c.vendor == "cisco-nxos"), None)
        assert nxos_config is not None
        assert "vlan 10" in nxos_config.config.lower()

    def test_juniper_config_generation(self):
        """Test Juniper config generation."""
        result = calculate_evpn_params(
            bgp_as=65000,
            loopback_ip="10.0.0.1",
            l2_vni=10010,
            vlan_id=10,
            vendors=[Vendor.JUNIPER],
        )

        juniper_config = next((c for c in result.configs if c.vendor == "juniper"), None)
        assert juniper_config is not None
        assert "set" in juniper_config.config

    def test_huawei_config_generation(self):
        """Test Huawei CE config generation."""
        result = calculate_evpn_params(
            bgp_as=65000,
            loopback_ip="10.0.0.1",
            l2_vni=10010,
            vlan_id=10,
            vendors=[Vendor.HUAWEI_CE],
        )

        huawei_config = next((c for c in result.configs if c.vendor == "huawei-ce"), None)
        assert huawei_config is not None
        assert "bridge-domain" in huawei_config.config.lower()

    def test_nokia_config_generation(self):
        """Test Nokia SR Linux config generation."""
        result = calculate_evpn_params(
            bgp_as=65000,
            loopback_ip="10.0.0.1",
            l2_vni=10010,
            vlan_id=10,
            vendors=[Vendor.NOKIA_SRLINUX],
        )

        nokia_config = next((c for c in result.configs if c.vendor == "nokia-srlinux"), None)
        assert nokia_config is not None
        assert "set /" in nokia_config.config

    def test_cumulus_config_generation(self):
        """Test Cumulus/NVIDIA config generation."""
        result = calculate_evpn_params(
            bgp_as=65000,
            loopback_ip="10.0.0.1",
            l2_vni=10010,
            vlan_id=10,
            vendors=[Vendor.CUMULUS],
        )

        cumulus_config = next((c for c in result.configs if c.vendor == "cumulus"), None)
        assert cumulus_config is not None
        assert "auto" in cumulus_config.config.lower() or "vxlan" in cumulus_config.config.lower()

    def test_all_vendors_generate_config(self):
        """Test all vendors generate valid config."""
        result = calculate_evpn_params(
            bgp_as=65000,
            loopback_ip="10.0.0.1",
            l2_vni=10010,
            vlan_id=10,
            vendors=list(Vendor),
        )

        assert len(result.configs) == len(Vendor)
        for config in result.configs:
            assert config.config is not None
            assert len(config.config) > 0

    def test_default_vendors_all(self):
        """Test default generates all vendor configs."""
        result = calculate_evpn_params(
            bgp_as=65000,
            loopback_ip="10.0.0.1",
            l2_vni=10010,
            vlan_id=10,
        )

        # Default should generate all vendors
        assert len(result.configs) == len(Vendor)

    def test_l2_params_vni_type(self):
        """Test L2 params have correct VNI type."""
        result = calculate_evpn_params(
            bgp_as=65000,
            loopback_ip="10.0.0.1",
            l2_vni=10010,
            vlan_id=10,
        )

        assert result.l2_params.vni_type == "L2"

    def test_evi_equals_vni(self):
        """Test EVI equals VNI."""
        result = calculate_evpn_params(
            bgp_as=65000,
            loopback_ip="10.0.0.1",
            l2_vni=10010,
            vlan_id=10,
        )

        assert result.l2_params.evi == 10010
