"""Configuration file support for EVPN Ninja.

Supports loading default settings from ~/.evpn-ninja.yaml or a custom config file.
Also supports loading calculation parameters from YAML files.

Example ~/.evpn-ninja.yaml:
```yaml
defaults:
  mtu:
    payload_size: 1500
    underlay_type: ipv4
  vni:
    base_vni: 10000
    scheme: vlan-based
  fabric:
    spine_count: 2
    vtep_count: 4
    replication_mode: ingress
  evpn:
    bgp_as: 65000
    vendors:
      - arista
      - cisco-nxos

output:
  format: table
  no_color: false

presets:
  small-dc:
    fabric:
      spine_count: 2
      vtep_count: 4
      vni_count: 100
    ebgp:
      scheme: private-4byte
  large-dc:
    fabric:
      spine_count: 4
      vtep_count: 64
      vni_count: 4000
```
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import sys

import yaml


DEFAULT_CONFIG_PATH = Path.home() / ".evpn-ninja.yaml"


@dataclass
class MTUDefaults:
    """Default settings for MTU calculator."""

    payload_size: int = 1500
    underlay_type: str = "ipv4"
    outer_vlan_tags: int = 0
    inner_vlan_tags: int = 0


@dataclass
class VNIDefaults:
    """Default settings for VNI calculator."""

    base_vni: int = 10000
    scheme: str = "vlan-based"
    start_vlan: int = 10
    count: int = 10
    multicast_base: str = "239.1.1.0"


@dataclass
class FabricDefaults:
    """Default settings for Fabric calculator."""

    vtep_count: int = 4
    spine_count: int = 2
    vni_count: int = 100
    hosts_per_vtep: int = 50
    replication_mode: str = "ingress"
    loopback_network: str = "10.0.0.0/24"
    vtep_loopback_network: str = "10.0.1.0/24"
    p2p_network: str = "10.0.100.0/22"


@dataclass
class EVPNDefaults:
    """Default settings for EVPN calculator."""

    bgp_as: int = 65000
    loopback_ip: str = "10.0.0.1"
    vendors: list[str] = field(default_factory=list)


@dataclass
class EBGPDefaults:
    """Default settings for eBGP calculator."""

    spine_count: int = 2
    leaf_count: int = 4
    scheme: str = "private-4byte"
    spine_asn_same: bool = True
    p2p_network: str = "10.0.100.0/22"


@dataclass
class MulticastDefaults:
    """Default settings for Multicast calculator."""

    vni_start: int = 10000
    vni_count: int = 100
    scheme: str = "one-to-one"
    base_group: str = "239.1.1.0"
    vnis_per_group: int = 10


@dataclass
class OutputSettings:
    """Output settings."""

    format: str = "table"
    no_color: bool = False
    verbose: bool = False


@dataclass
class Preset:
    """A named preset with pre-configured settings."""

    name: str
    description: str = ""
    fabric: dict[str, Any] = field(default_factory=dict)
    ebgp: dict[str, Any] = field(default_factory=dict)
    evpn: dict[str, Any] = field(default_factory=dict)
    vni: dict[str, Any] = field(default_factory=dict)
    multicast: dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    """Main configuration container."""

    mtu: MTUDefaults = field(default_factory=MTUDefaults)
    vni: VNIDefaults = field(default_factory=VNIDefaults)
    fabric: FabricDefaults = field(default_factory=FabricDefaults)
    evpn: EVPNDefaults = field(default_factory=EVPNDefaults)
    ebgp: EBGPDefaults = field(default_factory=EBGPDefaults)
    multicast: MulticastDefaults = field(default_factory=MulticastDefaults)
    output: OutputSettings = field(default_factory=OutputSettings)
    presets: dict[str, Preset] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create Config from dictionary."""
        config = cls()

        defaults = data.get("defaults", {})

        if "mtu" in defaults:
            config.mtu = MTUDefaults(**defaults["mtu"])
        if "vni" in defaults:
            config.vni = VNIDefaults(**defaults["vni"])
        if "fabric" in defaults:
            config.fabric = FabricDefaults(**defaults["fabric"])
        if "evpn" in defaults:
            config.evpn = EVPNDefaults(**defaults["evpn"])
        if "ebgp" in defaults:
            config.ebgp = EBGPDefaults(**defaults["ebgp"])
        if "multicast" in defaults:
            config.multicast = MulticastDefaults(**defaults["multicast"])

        if "output" in data:
            config.output = OutputSettings(**data["output"])

        if "presets" in data:
            for name, preset_data in data["presets"].items():
                config.presets[name] = Preset(
                    name=name,
                    description=preset_data.get("description", ""),
                    fabric=preset_data.get("fabric", {}),
                    ebgp=preset_data.get("ebgp", {}),
                    evpn=preset_data.get("evpn", {}),
                    vni=preset_data.get("vni", {}),
                    multicast=preset_data.get("multicast", {}),
                )

        return config


def load_config(path: Path | None = None) -> Config:
    """
    Load configuration from file.

    Args:
        path: Path to config file. If None, uses ~/.vxlan.yaml

    Returns:
        Config object with loaded settings
    """
    config_path = path or DEFAULT_CONFIG_PATH

    if not config_path.exists():
        return Config()

    try:
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        return Config.from_dict(data)
    except yaml.YAMLError as e:
        print(f"Warning: Invalid YAML in config file {config_path}: {e}", file=sys.stderr)
        print("Using default configuration.", file=sys.stderr)
        return Config()
    except OSError as e:
        print(f"Warning: Cannot read config file {config_path}: {e}", file=sys.stderr)
        print("Using default configuration.", file=sys.stderr)
        return Config()


def save_config(config: Config, path: Path | None = None) -> None:
    """
    Save configuration to file.

    Args:
        config: Config object to save
        path: Path to save to. If None, uses ~/.vxlan.yaml
    """
    config_path = path or DEFAULT_CONFIG_PATH

    data: dict[str, Any] = {
        "defaults": {
            "mtu": {
                "payload_size": config.mtu.payload_size,
                "underlay_type": config.mtu.underlay_type,
                "outer_vlan_tags": config.mtu.outer_vlan_tags,
                "inner_vlan_tags": config.mtu.inner_vlan_tags,
            },
            "vni": {
                "base_vni": config.vni.base_vni,
                "scheme": config.vni.scheme,
                "start_vlan": config.vni.start_vlan,
                "count": config.vni.count,
                "multicast_base": config.vni.multicast_base,
            },
            "fabric": {
                "vtep_count": config.fabric.vtep_count,
                "spine_count": config.fabric.spine_count,
                "vni_count": config.fabric.vni_count,
                "hosts_per_vtep": config.fabric.hosts_per_vtep,
                "replication_mode": config.fabric.replication_mode,
                "loopback_network": config.fabric.loopback_network,
                "vtep_loopback_network": config.fabric.vtep_loopback_network,
                "p2p_network": config.fabric.p2p_network,
            },
            "evpn": {
                "bgp_as": config.evpn.bgp_as,
                "loopback_ip": config.evpn.loopback_ip,
                "vendors": config.evpn.vendors,
            },
            "ebgp": {
                "spine_count": config.ebgp.spine_count,
                "leaf_count": config.ebgp.leaf_count,
                "scheme": config.ebgp.scheme,
                "spine_asn_same": config.ebgp.spine_asn_same,
                "p2p_network": config.ebgp.p2p_network,
            },
            "multicast": {
                "vni_start": config.multicast.vni_start,
                "vni_count": config.multicast.vni_count,
                "scheme": config.multicast.scheme,
                "base_group": config.multicast.base_group,
                "vnis_per_group": config.multicast.vnis_per_group,
            },
        },
        "output": {
            "format": config.output.format,
            "no_color": config.output.no_color,
            "verbose": config.output.verbose,
        },
    }

    if config.presets:
        data["presets"] = {}
        for name, preset in config.presets.items():
            data["presets"][name] = {
                "description": preset.description,
                "fabric": preset.fabric,
                "ebgp": preset.ebgp,
                "evpn": preset.evpn,
                "vni": preset.vni,
                "multicast": preset.multicast,
            }

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def load_params_from_file(path: Path) -> dict[str, Any]:
    """
    Load calculation parameters from a YAML file.

    This allows users to specify complex parameters in a file
    instead of passing them all on the command line.

    Args:
        path: Path to YAML file with parameters

    Returns:
        Dictionary of parameters

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If file is not valid YAML
    """
    with open(path) as f:
        return yaml.safe_load(f) or {}


def get_preset(config: Config, preset_name: str) -> Preset | None:
    """
    Get a preset by name.

    Args:
        config: Config object
        preset_name: Name of the preset

    Returns:
        Preset object or None if not found
    """
    return config.presets.get(preset_name)


def list_presets(config: Config) -> list[str]:
    """
    List available preset names.

    Args:
        config: Config object

    Returns:
        List of preset names
    """
    return list(config.presets.keys())


# Built-in presets for common scenarios
BUILTIN_PRESETS: dict[str, Preset] = {
    "small-dc": Preset(
        name="small-dc",
        description="Small datacenter (2 spines, 4 leaves, 100 VNIs)",
        fabric={"spine_count": 2, "vtep_count": 4, "vni_count": 100},
        ebgp={"spine_count": 2, "leaf_count": 4, "scheme": "private-4byte"},
    ),
    "medium-dc": Preset(
        name="medium-dc",
        description="Medium datacenter (2 spines, 16 leaves, 500 VNIs)",
        fabric={"spine_count": 2, "vtep_count": 16, "vni_count": 500},
        ebgp={"spine_count": 2, "leaf_count": 16, "scheme": "private-4byte"},
    ),
    "large-dc": Preset(
        name="large-dc",
        description="Large datacenter (4 spines, 64 leaves, 4000 VNIs)",
        fabric={"spine_count": 4, "vtep_count": 64, "vni_count": 4000},
        ebgp={"spine_count": 4, "leaf_count": 64, "scheme": "private-4byte"},
    ),
    "multi-tenant": Preset(
        name="multi-tenant",
        description="Multi-tenant with L3VNI per tenant",
        vni={"scheme": "tenant-based", "base_vni": 10000},
        evpn={"bgp_as": 65000},
    ),
    "campus": Preset(
        name="campus",
        description="Campus network with fewer VNIs",
        fabric={"spine_count": 2, "vtep_count": 8, "vni_count": 50},
        ebgp={"spine_count": 2, "leaf_count": 8, "scheme": "private-2byte"},
    ),
}
