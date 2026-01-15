"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def default_mtu_params():
    """Default parameters for MTU calculator."""
    return {
        "payload_size": 1500,
        "outer_vlan_tags": 0,
        "inner_vlan_tags": 0,
    }


@pytest.fixture
def default_vni_params():
    """Default parameters for VNI calculator."""
    return {
        "base_vni": 10000,
        "tenant_id": 1,
        "start_vlan": 10,
        "count": 10,
        "multicast_base": "239.1.1.0",
    }


@pytest.fixture
def default_fabric_params():
    """Default parameters for fabric calculator."""
    return {
        "vtep_count": 4,
        "spine_count": 2,
        "vni_count": 100,
        "hosts_per_vtep": 50,
        "loopback_network": "10.0.0.0/24",
        "vtep_loopback_network": "10.0.1.0/24",
        "p2p_network": "10.0.100.0/22",
    }


@pytest.fixture
def default_evpn_params():
    """Default parameters for EVPN calculator."""
    return {
        "bgp_as": 65000,
        "loopback_ip": "10.0.0.1",
        "l2_vni": 10010,
        "vlan_id": 10,
    }


@pytest.fixture
def default_ebgp_params():
    """Default parameters for eBGP calculator."""
    return {
        "spine_count": 2,
        "leaf_count": 4,
        "p2p_network": "10.0.100.0/22",
    }


@pytest.fixture
def default_multicast_params():
    """Default parameters for multicast calculator."""
    return {
        "vni_start": 10000,
        "vni_count": 100,
        "base_group": "239.1.1.0",
        "vnis_per_group": 10,
    }
