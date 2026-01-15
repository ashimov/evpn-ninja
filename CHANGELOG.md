# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-01-15

### Added

- **MTU Calculator**: Calculate required MTU for VXLAN encapsulation with detailed layer breakdown
  - Support for IPv4/IPv6 underlay
  - Inner and outer VLAN tag options
  - Recommended MTU calculation

- **VNI Allocation**: Multiple allocation schemes for VNI planning
  - VLAN-based: `VNI = base_vni + vlan_id`
  - Tenant-based: `VNI = tenant_id * 10000 + vlan_id`
  - Sequential: `VNI = base_vni + index`
  - Custom: `VNI = base_vni + (vlan_id * multiplier)`
  - Automatic multicast group assignment

- **Fabric Parameters**: Comprehensive fabric planning calculator
  - Leaf-spine topology IP planning
  - Router loopback allocation
  - VTEP loopback allocation
  - P2P link addressing (/31)
  - Resource estimation (MAC entries, EVPN routes, BGP sessions)
  - BUM replication factor calculation

- **EVPN Parameters**: Route Distinguisher and Route Target calculation
  - Automatic RD/RT generation
  - L2 and L3 VNI support
  - Vendor configuration generation:
    - Arista EOS
    - Cisco NX-OS
    - Juniper Junos

- **CLI Interface**: Full-featured command-line interface
  - Subcommands for each calculator
  - Multiple output formats: table, JSON, YAML
  - Interactive mode with guided input

### Technical

- Python 3.10+ support
- Type hints throughout codebase
- Comprehensive pyproject.toml configuration
- Ruff linter and formatter configuration
- Mypy strict type checking

[Unreleased]: https://github.com/ashimov/vxlan-calculator/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/ashimov/vxlan-calculator/releases/tag/v1.0.0
