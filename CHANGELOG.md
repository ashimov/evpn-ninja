# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2026-01-16

### Added

- **Security Hardening**
  - Path traversal protection for all file operations (`_validate_output_path`, `_safe_write_file`, `_safe_mkdir`)
  - Input bounds validation for fabric calculator with MAX constants
  - Symlink traversal detection and rejection

- **Configuration Validation**
  - `ConfigValidationError` exception class for config errors
  - `__post_init__` validators for all config dataclasses
  - Validation helpers: `_validate_positive`, `_validate_non_negative`, `_validate_range`, `_validate_choice`
  - Graceful fallback to defaults on invalid configuration

- **Architecture Improvements**
  - Refactored global state to use `typer.Context` with `AppState` dataclass
  - Cleaner dependency injection pattern for CLI commands
  - Improved testability and maintainability

### Fixed

- Division by zero when P2P network prefix length >= 31
- Error handling for file permission errors in export operations
- Type validation bypass in config loading

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
  - IP overlap and capacity validation

- **EVPN Parameters**: Route Distinguisher and Route Target calculation
  - Automatic RD/RT generation
  - L2 and L3 VNI support
  - Vendor configuration generation (18 vendors supported)

- **eBGP Underlay**: RFC 7938 compliant eBGP underlay design
  - ASN allocation schemes (private-2byte, private-4byte, custom)
  - Automatic BGP session calculation

- **Multicast Groups**: BUM traffic replication planning
  - One-to-one, shared, and range schemes
  - PIM RP configuration

- **Route Reflector**: BGP RR placement calculator
  - Spine and dedicated RR placement options
  - Cluster configuration

- **Bandwidth Calculator**: Fabric bandwidth estimation
  - Oversubscription ratio calculation
  - Failure scenario analysis

- **Multi-homing**: EVPN multi-homing parameters
  - ESI Type-0, Type-1, Type-3 support
  - LACP configuration
  - DF election settings

- **Topology Visualization**: ASCII and Graphviz DOT output

- **Lab Export**: Export to automation and simulation tools
  - Ansible inventory and playbooks
  - Nornir inventory and scripts
  - Containerlab topology files
  - EVE-NG lab files
  - GNS3 project files

- **CLI Interface**: Full-featured command-line interface
  - Subcommands for each calculator
  - Multiple output formats: table, JSON, YAML
  - Interactive mode with guided input
  - Shell completion (bash, zsh, fish, powershell)
  - Configuration file support (`~/.evpn-ninja.yaml`)
  - Built-in presets (small-dc, medium-dc, large-dc, campus, multi-tenant)

### Technical

- Python 3.10+ support
- Type hints throughout codebase
- Comprehensive pyproject.toml configuration
- Ruff linter and formatter configuration
- Mypy strict type checking
- 340+ unit tests

[Unreleased]: https://github.com/ashimov/evpn-ninja/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/ashimov/evpn-ninja/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/ashimov/evpn-ninja/releases/tag/v1.0.0
