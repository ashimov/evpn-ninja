"""Tests for exporter modules."""

import json
from typing import Any

import pytest
import yaml

from evpn_ninja.exporters.ansible import (
    AnsibleGroup,
    AnsibleHost,
    export_ansible_inventory,
    export_ansible_vars,
    generate_ansible_playbook_template,
)
from evpn_ninja.exporters.containerlab import (
    CLAB_IMAGES,
    CLAB_KINDS,
    export_containerlab_topology,
    generate_containerlab_configs,
    generate_makefile,
)
from evpn_ninja.exporters.eve_gns3 import (
    EVE_TEMPLATES,
    GNS3_TEMPLATES,
    export_eve_ng_topology,
    export_gns3_topology,
    generate_eve_ng_startup_scripts,
)
from evpn_ninja.exporters.nornir import (
    export_nornir_defaults,
    export_nornir_groups,
    export_nornir_inventory,
    generate_nornir_config,
    generate_nornir_script_template,
)


# Sample fabric data for tests
@pytest.fixture
def sample_spines() -> list[dict[str, Any]]:
    """Sample spine data."""
    return [
        {"name": "spine-1", "ip": "10.0.0.1", "loopback": "10.0.0.1", "asn": 65000},
        {"name": "spine-2", "ip": "10.0.0.2", "loopback": "10.0.0.2", "asn": 65000},
    ]


@pytest.fixture
def sample_leaves() -> list[dict[str, Any]]:
    """Sample leaf data."""
    return [
        {"name": "leaf-1", "ip": "10.0.1.1", "loopback": "10.0.1.1", "vtep_ip": "10.0.2.1", "asn": 65001},
        {"name": "leaf-2", "ip": "10.0.1.2", "loopback": "10.0.1.2", "vtep_ip": "10.0.2.2", "asn": 65002},
    ]


# ============================================================================
# Ansible Exporter Tests
# ============================================================================
class TestAnsibleExporter:
    """Tests for Ansible exporter functions."""

    def test_ansible_host_dataclass(self) -> None:
        """Test AnsibleHost dataclass."""
        host = AnsibleHost(
            name="spine-1",
            ansible_host="10.0.0.1",
            role="spine",
            asn=65000,
            loopback="10.0.0.1",
        )
        assert host.name == "spine-1"
        assert host.ansible_host == "10.0.0.1"
        assert host.role == "spine"
        assert host.asn == 65000

    def test_ansible_group_dataclass(self) -> None:
        """Test AnsibleGroup dataclass."""
        host = AnsibleHost(name="spine-1", ansible_host="10.0.0.1", role="spine")
        group = AnsibleGroup(
            name="spines",
            hosts=[host],
            vars={"common_var": "value"},
        )
        assert group.name == "spines"
        assert len(group.hosts) == 1
        assert group.vars == {"common_var": "value"}

    def test_export_ansible_inventory(
        self, sample_spines: list[dict[str, Any]], sample_leaves: list[dict[str, Any]]
    ) -> None:
        """Test Ansible inventory generation."""
        result = export_ansible_inventory(sample_spines, sample_leaves)
        inventory = yaml.safe_load(result)

        # Check structure
        assert "all" in inventory
        assert "children" in inventory["all"]
        assert "fabric" in inventory["all"]["children"]

        # Check spines
        spines = inventory["all"]["children"]["fabric"]["children"]["spines"]["hosts"]
        assert "spine-1" in spines
        assert spines["spine-1"]["ansible_host"] == "10.0.0.1"
        assert spines["spine-1"]["role"] == "spine"

        # Check leaves
        leaves = inventory["all"]["children"]["fabric"]["children"]["leaves"]["hosts"]
        assert "leaf-1" in leaves
        assert leaves["leaf-1"]["vtep_ip"] == "10.0.2.1"

    def test_export_ansible_inventory_with_bgp_as(
        self, sample_spines: list[dict[str, Any]], sample_leaves: list[dict[str, Any]]
    ) -> None:
        """Test Ansible inventory with BGP AS (iBGP scenario)."""
        result = export_ansible_inventory(sample_spines, sample_leaves, bgp_as=65000)
        inventory = yaml.safe_load(result)

        # Check fabric-level vars
        assert inventory["all"]["children"]["fabric"]["vars"]["bgp_as"] == 65000

    def test_export_ansible_inventory_with_extra_groups(
        self, sample_spines: list[dict[str, Any]], sample_leaves: list[dict[str, Any]]
    ) -> None:
        """Test Ansible inventory with extra groups."""
        host = AnsibleHost(name="border-1", ansible_host="10.0.3.1", role="border", asn=65100)
        extra_group = AnsibleGroup(
            name="borders",
            hosts=[host],
            vars={"border_var": "value"},
        )

        result = export_ansible_inventory(sample_spines, sample_leaves, extra_groups=[extra_group])
        inventory = yaml.safe_load(result)

        # Check extra group
        assert "borders" in inventory["all"]["children"]
        assert "border-1" in inventory["all"]["children"]["borders"]["hosts"]

    def test_export_ansible_vars_vni(self) -> None:
        """Test Ansible vars with VNI allocations."""
        vni_allocations = [
            {"vlan_id": 10, "vni_decimal": 10010, "multicast_group": "239.1.1.0"},
            {"vlan_id": 20, "vni_decimal": 10020, "multicast_group": "239.1.1.1"},
        ]

        result = export_ansible_vars(vni_allocations=vni_allocations)
        vars_data = yaml.safe_load(result)

        assert "vxlan_vnis" in vars_data
        assert len(vars_data["vxlan_vnis"]) == 2
        assert vars_data["vxlan_vnis"][0]["vni"] == 10010

    def test_export_ansible_vars_evpn(self) -> None:
        """Test Ansible vars with EVPN params."""
        evpn_params = {
            "l2_vni": 10010,
            "l2_rd": "10.0.0.1:10010",
            "l2_rt_import": "65000:10010",
            "l2_rt_export": "65000:10010",
            "l3_vni": 50000,
            "l3_rd": "10.0.0.1:50000",
            "l3_rt_import": "65000:50000",
            "l3_rt_export": "65000:50000",
            "vrf_name": "TENANT-1",
        }

        result = export_ansible_vars(evpn_params=evpn_params)
        vars_data = yaml.safe_load(result)

        assert "evpn" in vars_data
        assert vars_data["evpn"]["l2_vni"] == 10010
        assert vars_data["evpn"]["l3_vni"] == 50000
        assert vars_data["evpn"]["vrf"] == "TENANT-1"

    def test_generate_ansible_playbook_template(self) -> None:
        """Test Ansible playbook template generation."""
        result = generate_ansible_playbook_template()

        assert "VXLAN/EVPN Deployment Playbook" in result
        assert "Configure Underlay Network" in result
        assert "Configure BGP Underlay" in result
        assert "Configure VXLAN/EVPN Overlay" in result


# ============================================================================
# Containerlab Exporter Tests
# ============================================================================
class TestContainerlabExporter:
    """Tests for Containerlab exporter functions."""

    def test_clab_kinds_mapping(self) -> None:
        """Test CLAB_KINDS mapping contains expected platforms."""
        assert CLAB_KINDS["eos"] == "ceos"
        assert CLAB_KINDS["srlinux"] == "srl"
        assert CLAB_KINDS["sonic"] == "sonic-vs"

    def test_clab_images_mapping(self) -> None:
        """Test CLAB_IMAGES mapping contains images."""
        assert "ceos" in CLAB_IMAGES
        assert "srl" in CLAB_IMAGES

    def test_export_containerlab_topology(
        self, sample_spines: list[dict[str, Any]], sample_leaves: list[dict[str, Any]]
    ) -> None:
        """Test Containerlab topology generation."""
        result = export_containerlab_topology(
            sample_spines, sample_leaves, lab_name="test-lab", platform="eos"
        )

        # Check basic structure
        assert "name: test-lab" in result
        assert "topology:" in result
        assert "nodes:" in result
        assert "links:" in result

        # Check nodes
        assert "spine-1:" in result
        assert "spine-2:" in result
        assert "leaf-1:" in result
        assert "leaf-2:" in result

        # Check kind
        assert "kind: ceos" in result

    def test_export_containerlab_topology_with_hosts(
        self, sample_spines: list[dict[str, Any]], sample_leaves: list[dict[str, Any]]
    ) -> None:
        """Test Containerlab topology with host nodes."""
        result = export_containerlab_topology(
            sample_spines,
            sample_leaves,
            lab_name="test-lab",
            include_hosts=True,
            hosts_per_leaf=1,
        )

        # Check host nodes exist
        assert "host-1:" in result
        assert "host-2:" in result
        assert "kind: linux" in result

    def test_export_containerlab_topology_srlinux(
        self, sample_spines: list[dict[str, Any]], sample_leaves: list[dict[str, Any]]
    ) -> None:
        """Test Containerlab topology for SR Linux."""
        result = export_containerlab_topology(
            sample_spines, sample_leaves, platform="srlinux"
        )

        assert "kind: srl" in result

    def test_generate_containerlab_configs_eos(
        self, sample_spines: list[dict[str, Any]], sample_leaves: list[dict[str, Any]]
    ) -> None:
        """Test Containerlab EOS config generation."""
        configs = generate_containerlab_configs(
            sample_spines, sample_leaves, platform="eos", bgp_as=65000
        )

        # Check spine config
        assert "spine-1" in configs
        assert "hostname spine-1" in configs["spine-1"]
        assert "Loopback0" in configs["spine-1"]
        assert "router bgp" in configs["spine-1"]

        # Check leaf config
        assert "leaf-1" in configs
        assert "interface Vxlan1" in configs["leaf-1"]
        assert "vxlan source-interface Loopback1" in configs["leaf-1"]

    def test_generate_containerlab_configs_srlinux(
        self, sample_spines: list[dict[str, Any]], sample_leaves: list[dict[str, Any]]
    ) -> None:
        """Test Containerlab SR Linux config generation."""
        configs = generate_containerlab_configs(
            sample_spines, sample_leaves, platform="srlinux"
        )

        assert "spine-1" in configs
        assert "set / system name host-name spine-1" in configs["spine-1"]

    def test_generate_makefile(self) -> None:
        """Test Makefile generation."""
        result = generate_makefile()

        assert "containerlab deploy" in result
        assert "containerlab destroy" in result
        assert ".PHONY" in result


# ============================================================================
# EVE-NG / GNS3 Exporter Tests
# ============================================================================
class TestEveGns3Exporter:
    """Tests for EVE-NG and GNS3 exporter functions."""

    def test_eve_templates_mapping(self) -> None:
        """Test EVE_TEMPLATES mapping."""
        assert EVE_TEMPLATES["eos"] == "veos"
        assert EVE_TEMPLATES["nxos"] == "nxosv9k"

    def test_gns3_templates_mapping(self) -> None:
        """Test GNS3_TEMPLATES mapping."""
        assert GNS3_TEMPLATES["eos"] == "Arista vEOS"
        assert GNS3_TEMPLATES["nxos"] == "Cisco NX-OSv 9000"

    def test_export_eve_ng_topology(
        self, sample_spines: list[dict[str, Any]], sample_leaves: list[dict[str, Any]]
    ) -> None:
        """Test EVE-NG topology generation."""
        result = export_eve_ng_topology(
            sample_spines, sample_leaves, lab_name="Test_Lab", platform="eos"
        )

        # Check XML structure
        assert '<?xml version="1.0"' in result
        assert '<lab name="Test_Lab"' in result
        assert "<topology>" in result
        assert "</topology>" in result
        assert "<networks>" in result
        assert "</networks>" in result

        # Check nodes
        assert 'name="spine-1"' in result
        assert 'name="leaf-1"' in result
        assert 'template="veos"' in result

    def test_export_eve_ng_topology_with_hosts(
        self, sample_spines: list[dict[str, Any]], sample_leaves: list[dict[str, Any]]
    ) -> None:
        """Test EVE-NG topology with hosts."""
        result = export_eve_ng_topology(
            sample_spines, sample_leaves, include_hosts=True
        )

        assert 'name="host-1"' in result
        assert 'name="host-2"' in result
        assert 'template="linux"' in result

    def test_export_gns3_topology(
        self, sample_spines: list[dict[str, Any]], sample_leaves: list[dict[str, Any]]
    ) -> None:
        """Test GNS3 topology generation."""
        result = export_gns3_topology(
            sample_spines, sample_leaves, lab_name="Test_Lab", platform="eos"
        )

        # Parse JSON
        project = json.loads(result)

        # Check structure
        assert project["name"] == "Test_Lab"
        assert "topology" in project
        assert "nodes" in project["topology"]
        assert "links" in project["topology"]

        # Check nodes
        nodes = project["topology"]["nodes"]
        node_names = [n["name"] for n in nodes]
        assert "spine-1" in node_names
        assert "spine-2" in node_names
        assert "leaf-1" in node_names
        assert "leaf-2" in node_names

        # Check links exist
        links = project["topology"]["links"]
        assert len(links) == 4  # 2 spines * 2 leaves

    def test_export_gns3_topology_with_hosts(
        self, sample_spines: list[dict[str, Any]], sample_leaves: list[dict[str, Any]]
    ) -> None:
        """Test GNS3 topology with hosts."""
        result = export_gns3_topology(
            sample_spines, sample_leaves, include_hosts=True
        )

        project = json.loads(result)
        node_names = [n["name"] for n in project["topology"]["nodes"]]

        assert "host-1" in node_names
        assert "host-2" in node_names

    def test_generate_eve_ng_startup_scripts(
        self, sample_spines: list[dict[str, Any]], sample_leaves: list[dict[str, Any]]
    ) -> None:
        """Test EVE-NG startup script generation."""
        configs = generate_eve_ng_startup_scripts(
            sample_spines, sample_leaves, platform="eos"
        )

        # Check configs exist
        assert "spine-1" in configs
        assert "leaf-1" in configs

        # Check content
        assert "hostname spine-1" in configs["spine-1"]
        assert "Loopback0" in configs["spine-1"]

    def test_generate_eve_ng_startup_scripts_nxos(
        self, sample_spines: list[dict[str, Any]], sample_leaves: list[dict[str, Any]]
    ) -> None:
        """Test EVE-NG startup scripts for NX-OS."""
        configs = generate_eve_ng_startup_scripts(
            sample_spines, sample_leaves, platform="nxos"
        )

        assert "spine-1" in configs
        assert "hostname spine-1" in configs["spine-1"]
        assert "loopback0" in configs["spine-1"]  # NX-OS uses lowercase


# ============================================================================
# Nornir Exporter Tests
# ============================================================================
class TestNornirExporter:
    """Tests for Nornir exporter functions."""

    def test_export_nornir_inventory(
        self, sample_spines: list[dict[str, Any]], sample_leaves: list[dict[str, Any]]
    ) -> None:
        """Test Nornir inventory generation."""
        result = export_nornir_inventory(sample_spines, sample_leaves)
        hosts = yaml.safe_load(result)

        # Check spines
        assert "spine-1" in hosts
        assert hosts["spine-1"]["hostname"] == "10.0.0.1"
        assert "spines" in hosts["spine-1"]["groups"]
        assert "fabric" in hosts["spine-1"]["groups"]
        assert hosts["spine-1"]["data"]["role"] == "spine"

        # Check leaves
        assert "leaf-1" in hosts
        assert hosts["leaf-1"]["data"]["vtep_ip"] == "10.0.2.1"

    def test_export_nornir_inventory_with_connection_options(
        self, sample_spines: list[dict[str, Any]], sample_leaves: list[dict[str, Any]]
    ) -> None:
        """Test Nornir inventory with connection options."""
        conn_opts = {"netmiko": {"extras": {"device_type": "arista_eos"}}}

        result = export_nornir_inventory(
            sample_spines, sample_leaves, connection_options=conn_opts
        )
        hosts = yaml.safe_load(result)

        assert hosts["spine-1"]["connection_options"] == conn_opts

    def test_export_nornir_groups(self) -> None:
        """Test Nornir groups generation."""
        result = export_nornir_groups(
            fabric_vars={"ntp_server": "10.0.0.100"},
            spine_vars={"role": "spine", "priority": 100},
            leaf_vars={"role": "leaf"},
        )
        groups = yaml.safe_load(result)

        assert "fabric" in groups
        assert "spines" in groups
        assert "leaves" in groups

        assert groups["fabric"]["data"]["ntp_server"] == "10.0.0.100"
        assert groups["spines"]["data"]["priority"] == 100

    def test_export_nornir_groups_defaults(self) -> None:
        """Test Nornir groups with default values."""
        result = export_nornir_groups()
        groups = yaml.safe_load(result)

        assert groups["spines"]["data"]["role"] == "spine"
        assert groups["leaves"]["data"]["role"] == "leaf"

    def test_export_nornir_defaults(self) -> None:
        """Test Nornir defaults generation."""
        result = export_nornir_defaults(
            username="admin", platform="eos", port=22
        )
        defaults = yaml.safe_load(result)

        assert defaults["username"] == "admin"
        assert defaults["platform"] == "eos"
        assert defaults["port"] == 22

        # Check default connection options
        assert "netmiko" in defaults["connection_options"]
        assert defaults["connection_options"]["netmiko"]["extras"]["device_type"] == "arista_eos"

    def test_export_nornir_defaults_custom_connection(self) -> None:
        """Test Nornir defaults with custom connection options."""
        custom_opts = {"scrapli": {"extras": {"auth_strict_key": True}}}

        result = export_nornir_defaults(connection_options=custom_opts)
        defaults = yaml.safe_load(result)

        assert defaults["connection_options"] == custom_opts

    def test_export_nornir_defaults_platform_mapping(self) -> None:
        """Test Nornir defaults for different platforms."""
        for platform, expected in [("nxos", "cisco_nxos"), ("iosxr", "cisco_xr")]:
            result = export_nornir_defaults(platform=platform)
            defaults = yaml.safe_load(result)
            assert defaults["connection_options"]["netmiko"]["extras"]["device_type"] == expected

    def test_generate_nornir_config(self) -> None:
        """Test Nornir config.yaml generation."""
        result = generate_nornir_config()

        assert "inventory:" in result
        assert "SimpleInventory" in result
        assert "host_file:" in result
        assert "runner:" in result

    def test_generate_nornir_script_template(self) -> None:
        """Test Nornir script template generation."""
        result = generate_nornir_script_template()

        assert "from nornir import InitNornir" in result
        assert "def configure_underlay" in result
        assert "def configure_bgp" in result
        assert "def configure_vxlan_evpn" in result
        assert "def verify_bgp_neighbors" in result
        assert "def main" in result
