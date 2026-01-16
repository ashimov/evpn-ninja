<p align="center">
  <img src="assets/logo.png" alt="EVPN Ninja Logo" width="200"/>
</p>

<h1 align="center">EVPN Ninja</h1>

<p align="center">
  <strong>The Ultimate VXLAN/EVPN Fabric Planning & Configuration Tool</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/evpn-ninja/"><img src="https://img.shields.io/pypi/v/evpn-ninja?style=for-the-badge&logo=pypi&logoColor=white" alt="PyPI"></a>
  <a href="https://pypistats.org/packages/evpn-ninja"><img src="https://img.shields.io/pypi/dm/evpn-ninja?style=for-the-badge&logo=pypi&logoColor=white&label=downloads/month" alt="PyPI Downloads"></a>
  <a href="https://github.com/ashimov/evpn-ninja/releases"><img src="https://img.shields.io/github/downloads/ashimov/evpn-ninja/total?style=for-the-badge&logo=github&label=binary%20downloads" alt="GitHub Downloads"></a>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-commands">Commands</a> •
  <a href="#-supported-vendors">Vendors</a> •
  <a href="#-lab-export">Lab Export</a>
</p>

---

## Overview

**EVPN Ninja** is a powerful cross-platform CLI tool designed for network engineers to plan, calculate, and generate configurations for VXLAN/EVPN data center fabrics. Whether you're designing a small campus network or a large-scale multi-tenant datacenter, EVPN Ninja has you covered.

```
┌─────────────────────────────────────────────────────────────────┐
│  Plan → Calculate → Generate → Deploy                          │
│                                                                 │
│  ┌───────┐    ┌───────────┐    ┌──────────┐    ┌───────────┐  │
│  │Fabric │ => │ IP Plans  │ => │  Configs │ => │Containerlab│ │
│  │Design │    │ VNI/ASN   │    │ 18 Vendors│   │EVE-NG/GNS3│  │
│  └───────┘    └───────────┘    └──────────┘    └───────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### Calculators

| Calculator | Description |
|:-----------|:------------|
| **MTU** | Calculate VXLAN encapsulation overhead with detailed layer-by-layer breakdown |
| **VNI Allocation** | Plan VNI assignments using VLAN-based, tenant-based, or sequential schemes |
| **Fabric Parameters** | Generate complete IP addressing plans for leaf-spine topologies |
| **EVPN Parameters** | Calculate RD/RT values and generate production-ready vendor configs |
| **eBGP Underlay** | Design RFC 7938 compliant eBGP underlay with ASN allocation |
| **Multicast Groups** | Plan multicast group assignments for BUM traffic replication |
| **Route Reflector** | Calculate BGP RR placement and cluster configurations |
| **Bandwidth** | Estimate fabric bandwidth and oversubscription ratios |
| **Multi-homing** | Generate ESI, LACP, and ES-RT for EVPN multi-homing |
| **Topology** | Visualize fabric topology in ASCII or Graphviz DOT format |

### Key Capabilities

- **18 Vendor Support** — Generate configs for Arista, Cisco, Juniper, Nokia, and 14 more vendors
- **Lab Export** — Export to Containerlab, EVE-NG, and GNS3 for instant lab deployment
- **Presets** — Built-in presets for small, medium, and large datacenters
- **Config File** — Save your defaults in `~/.evpn-ninja.yaml`
- **Multiple Outputs** — Table, JSON, or YAML output for automation
- **IP Validation** — Automatic overlap and capacity checks for IP networks
- **Interactive Mode** — Guided wizard for beginners

---

## 📦 Installation

### From PyPI

```bash
pip install evpn-ninja
```

### From Source

```bash
git clone https://github.com/ashimov/evpn-ninja.git
cd evpn-ninja
pip install -e .
```

### Standalone Binary

Download prebuilt binaries from [GitHub Releases](https://github.com/ashimov/evpn-ninja/releases):

| Platform | File |
|:---------|:-----|
| Linux (x64) | `evpn-ninja-linux-amd64` |
| macOS (Intel) | `evpn-ninja-macos-amd64` |
| macOS (Apple Silicon) | `evpn-ninja-macos-arm64` |
| Windows (x64) | `evpn-ninja-windows-amd64.exe` |

```bash
# Linux/macOS: make executable and run
chmod +x evpn-ninja-*
./evpn-ninja-linux-amd64 --help
```

### Shell Completion

```bash
# Bash
evpn-ninja completion bash > ~/.evpn-ninja-complete.bash
echo "source ~/.evpn-ninja-complete.bash" >> ~/.bashrc

# Zsh
evpn-ninja completion zsh > ~/.evpn-ninja-complete.zsh
echo "source ~/.evpn-ninja-complete.zsh" >> ~/.zshrc

# Fish
evpn-ninja completion fish > ~/.config/fish/completions/evpn-ninja.fish
```

---

## 🚀 Quick Start

```bash
# Show all available commands
evpn-ninja --help

# Use a preset for quick calculations
evpn-ninja --preset large-dc fabric

# Calculate MTU requirements
evpn-ninja mtu --payload 1500 --underlay ipv4

# Generate EVPN configs for multiple vendors
evpn-ninja evpn --as 65000 --loopback 10.0.0.1 --l2-vni 10010 --vendor arista --vendor cisco-nxos

# Export to Containerlab for testing
evpn-ninja export containerlab --spines 2 --leaves 4 --platform eos --output-dir ./lab

# Interactive guided mode
evpn-ninja interactive
```

---

## 📖 Commands

### MTU Calculator

Calculate the required underlay MTU for VXLAN encapsulation with a detailed breakdown of each layer.

```bash
evpn-ninja mtu --payload 1500 --underlay ipv4 --outer-vlan 1
```

```
                              VXLAN MTU Breakdown
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Layer          ┃ Size (bytes) ┃ Description                                ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Outer Ethernet │ 14           │ Dst MAC + Src MAC + EtherType              │
│ Outer VLAN     │ 4            │ 802.1Q tag                                 │
│ Outer IPv4     │ 20           │ Standard IPv4 header                       │
│ UDP            │ 8            │ Source port + Dest port (4789) + Length    │
│ VXLAN Header   │ 8            │ Flags + Reserved + VNI + Reserved          │
│ Inner Ethernet │ 14           │ Dst MAC + Src MAC + EtherType              │
│ Inner Payload  │ 1500         │ Original L3 packet (IP + data)             │
└────────────────┴──────────────┴────────────────────────────────────────────┘

╭─────────────────────────────── Summary ────────────────────────────────╮
│   Required MTU        1554 bytes                                       │
│   Recommended MTU     1600 bytes                                       │
╰────────────────────────────────────────────────────────────────────────╯
```

### VNI Allocation

Plan VNI assignments using multiple allocation schemes.

```bash
# VLAN-based scheme
evpn-ninja vni --scheme vlan-based --base-vni 10000 --start-vlan 100 --count 5

# Tenant-based scheme
evpn-ninja vni --scheme tenant-based --tenant-id 5 --start-vlan 100 --count 3

# Output as JSON for automation
evpn-ninja vni --scheme vlan-based --base-vni 10000 --count 10 --output json
```

### Fabric Parameters

Generate complete IP addressing plans and resource estimates for leaf-spine fabrics.

```bash
evpn-ninja fabric --vteps 8 --spines 4 --vnis 500 --hosts 100 \
  --loopback-net 10.0.0.0/24 \
  --vtep-net 10.0.1.0/24 \
  --p2p-net 10.0.100.0/22
```

Features:
- Router loopback allocation
- VTEP (NVE) loopback allocation
- P2P /31 link addressing
- Resource estimates (MAC entries, EVPN routes, BGP sessions)
- **Automatic IP overlap and capacity validation**

### EVPN Parameters

Calculate RD/RT values and generate vendor-specific configurations.

```bash
# L2 VNI only
evpn-ninja evpn --as 65000 --loopback 10.0.0.1 --l2-vni 10010 --vlan 10 --vendor arista

# L2 + L3 VNI (symmetric IRB)
evpn-ninja evpn --as 65000 --loopback 10.0.0.1 \
  --l2-vni 10010 --vlan 10 \
  --l3-vni 50000 --vrf TENANT-A \
  --vendor arista --vendor cisco-nxos --vendor juniper
```

### eBGP Underlay

Design RFC 7938 compliant eBGP underlay with automatic ASN allocation.

```bash
evpn-ninja ebgp --spines 4 --leaves 16 --scheme private-4byte --p2p-net 10.0.100.0/22
```

ASN Schemes:
- `private-2byte` — 64512-65534
- `private-4byte` — 4200000000+ (recommended)
- `custom` — Specify base ASN

### Multi-homing

Calculate EVPN multi-homing parameters including ESI generation.

```bash
evpn-ninja multihoming --es-count 4 --peers 2 --mode active-active --vendor arista
```

Features:
- ESI Type-0, Type-1 (LACP), Type-3 (MAC-based)
- LACP system ID configuration
- DF election algorithm settings
- Vendor configs for Arista, Cisco, Juniper

### Route Reflector

Calculate BGP Route Reflector placement for EVPN overlay.

```bash
evpn-ninja rr --clients 16 --placement spine --redundancy pair
```

### Bandwidth Calculator

Estimate fabric bandwidth and oversubscription ratios.

```bash
evpn-ninja bandwidth --leaves 8 --spines 4 \
  --uplinks 4 --uplink-speed 100g --downlinks 48 --downlink-speed 25g
```

---

## 🏭 Supported Vendors

EVPN Ninja generates production-ready configurations for **18 vendors**:

| Vendor | Platform | Vendor | Platform |
|:-------|:---------|:-------|:---------|
| **Arista** | EOS | **Nokia** | SR Linux |
| **Cisco** | NX-OS | **Dell** | OS10 |
| **Cisco** | IOS-XE | **Cumulus** | Linux |
| **Cisco** | IOS-XR | **SONiC** | SONiC NOS |
| **Juniper** | Junos | **Extreme** | EXOS |
| **Huawei** | CE Series | **HPE** | Aruba CX |
| **MikroTik** | RouterOS 7 | **H3C** | Comware |
| **VyOS** | VyOS 1.4+ | **ZTE** | ZXROS |
| **Fortinet** | FortiOS | **Mellanox** | Onyx |

```bash
# Generate config for specific vendor
evpn-ninja evpn --as 65000 --loopback 10.0.0.1 --l2-vni 10010 --vendor nokia-srlinux

# Generate for multiple vendors at once
evpn-ninja evpn --as 65000 --loopback 10.0.0.1 --l2-vni 10010 \
  --vendor arista --vendor cisco-nxos --vendor juniper
```

---

## 🧪 Lab Export

Export your fabric design directly to network simulators for testing.

### Containerlab

```bash
evpn-ninja export containerlab \
  --spines 2 --leaves 4 \
  --platform eos \
  --lab-name my-fabric \
  --include-hosts \
  --output-dir ./containerlab

# Deploy the lab
cd containerlab && make deploy
```

### EVE-NG

```bash
evpn-ninja export eve-ng \
  --spines 2 --leaves 4 \
  --platform nxos \
  --lab-name evpn-test \
  --output-dir ./eve-ng
```

### GNS3

```bash
evpn-ninja export gns3 \
  --spines 2 --leaves 4 \
  --platform eos \
  --lab-name gns3-fabric \
  --output-dir ./gns3
```

### Export All Formats

```bash
evpn-ninja export all --spines 2 --leaves 4 --output-dir ./automation
```

This creates:
```
automation/
├── ansible/
│   ├── inventory.yaml
│   └── group_vars/
├── nornir/
│   ├── inventory/
│   └── config.yaml
├── containerlab/
│   ├── my-fabric.clab.yml
│   ├── configs/
│   └── Makefile
├── eve-ng/
│   └── my-fabric.unl
└── gns3/
    └── my-fabric.gns3
```

---

## ⚙️ Configuration

### Config File

Create a config file at `~/.evpn-ninja.yaml` to set your defaults:

```yaml
defaults:
  mtu:
    payload_size: 1500
    underlay_type: ipv4
  fabric:
    spine_count: 2
    vtep_count: 4
    loopback_network: "10.0.0.0/24"
    vtep_loopback_network: "10.0.1.0/24"
  evpn:
    bgp_as: 65000
    vendors:
      - arista
      - cisco-nxos

output:
  format: table
  no_color: false

presets:
  my-dc:
    fabric:
      spine_count: 4
      vtep_count: 32
      vni_count: 1000
    ebgp:
      scheme: private-4byte
```

```bash
# Initialize default config
evpn-ninja config init

# Show current config
evpn-ninja config show

# Use custom config file
evpn-ninja --config /path/to/config.yaml fabric
```

### Built-in Presets

```bash
# List available presets
evpn-ninja --list-presets

# Use a preset
evpn-ninja --preset large-dc fabric
evpn-ninja --preset small-dc ebgp
```

| Preset | Spines | Leaves | VNIs | Description |
|:-------|:------:|:------:|:----:|:------------|
| `small-dc` | 2 | 4 | 100 | Small datacenter |
| `medium-dc` | 2 | 16 | 500 | Medium datacenter |
| `large-dc` | 4 | 64 | 4000 | Large datacenter |
| `multi-tenant` | - | - | - | Multi-tenant with L3VNI per tenant |
| `campus` | 2 | 8 | 50 | Campus network |

---

## 📤 Output Formats

All commands support multiple output formats:

```bash
# Pretty tables (default)
evpn-ninja fabric --vteps 4 --spines 2 --output table

# JSON for automation/scripting
evpn-ninja fabric --vteps 4 --spines 2 --output json

# YAML for config files
evpn-ninja fabric --vteps 4 --spines 2 --output yaml

# Save to file
evpn-ninja fabric --vteps 4 --spines 2 --output json --save fabric.json
```

---

## 🛠️ Development

```bash
# Clone repository
git clone https://github.com/ashimov/evpn-ninja.git
cd evpn-ninja

# Install with dev dependencies
pip install -e ".[dev]"

# Run linter
ruff check src/

# Run formatter
ruff format src/

# Run type checker
mypy src/

# Run tests
pytest

# Run all checks
ruff check src/ && ruff format src/ && mypy src/ && pytest
```

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Berik Ashimov**

- Website: [ashimov.com](https://ashimov.com)
- GitHub: [@ashimov](https://github.com/ashimov)

---

<p align="center">
  <sub>Built with ❤️ for the network engineering community</sub>
</p>

<p align="center">
  <a href="https://ashimov.com/tools/evpn-ninja">Web Version</a> •
  <a href="https://github.com/ashimov/evpn-ninja/issues">Report Bug</a> •
  <a href="https://github.com/ashimov/evpn-ninja/issues">Request Feature</a>
</p>
