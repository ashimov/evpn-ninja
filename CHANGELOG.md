# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.4] - 2026-05-24

### Security

- **Removed `.snyk.env` from version control** and broadened `.gitignore` (`*.env`, `.snyk.env`) to prevent committing local environment files.
- **Hardened export output generation against injection (defense-in-depth)**
  - Containerlab: the platform-derived `kind` is now sanitized before YAML interpolation, so an unknown platform string cannot inject YAML structure.
  - Containerlab and EVE-NG device-config generators now sanitize node names before embedding them in generated device configs.
- **Format-string hardening**: multi-homing interface naming uses literal substitution instead of `str.format()`, preventing format-string abuse of a caller-supplied template.

### Fixed

- **`export` resource limits (CWE-400)**: `--spines`/`--leaves` are now bounded and host IPs are materialized lazily, so a large CIDR (e.g. `/8`) can no longer exhaust memory.
- **`export` network parsing**: loopback/VTEP networks are parsed with `strict=False` to match CLI validation, avoiding an uncaught error when an address has host bits set.

## [1.0.3] - 2026-02-24

### Fixed

- Fixed `--version` displaying 1.0.1 instead of actual version (PyPI package metadata was correct)
- Modernized license field to SPDX expression format (PEP 639)
- Updated CI/CD: pypi-publish action compatibility, reusable workflow artifact handling

## [1.0.2] - 2026-02-24

### Added

- **Comprehensive Input Validation Across All Calculators**
  - Bandwidth: spine_count, leaf_count, uplink/downlink counts must be positive
  - eBGP: spine_count, leaf_count validation; P2P address space exhaustion check
  - EVPN: bgp_as (1-4294967295), l2_vni/l3_vni (1-16777215), vlan_id (1-4094) range checks; l3_vni/vrf_name mutual requirement
  - Multicast: vni_count positive, vni_start range (1-16777215), VNI range overflow detection (vni_start + vni_count > 16777215)
  - Multihoming: LACP port key 16-bit overflow (0-65535), ESI Type-0 48-bit overflow, Type-3 24-bit overflow, es_count/peers_per_es positive
  - Route Reflector: custom_cluster_count positive if provided
  - Topology: spine_count, leaf_count positive
  - VNI: count positive
  - Config: multicast_base validated as IPv4 multicast address (224.0.0.0-239.255.255.255)

- **Exporter Safety Improvements**
  - Node name collision detection in all three exporters (Containerlab, EVE-NG, GNS3), including host nodes
  - Containerlab: `_sanitize_name()` function to prevent YAML injection via node names
  - Containerlab: management network capacity validation using `IPv4Network.hosts()`
  - CLI: proper error on loopback/VTEP network exhaustion instead of silent fallback to hardcoded IPs

- **Shared Multicast Utility Module** (`_multicast_utils.py`)
  - Extracted duplicate `_calculate_multicast_group` from vni.py and multicast.py into shared module
  - Enhanced with multicast range validation (224.0.0.0-239.255.255.255)

- **CI/CD Improvements**
  - Dedicated lint job in CI (ruff check, ruff format, mypy)
  - Test coverage enforcement (70% minimum via `--cov-fail-under=70`)
  - `workflow_call` trigger on ci.yml for reusable workflows
  - CI gate job in publish.yml (runs full CI before publishing)
  - Manual `workflow_dispatch` ref input for publish.yml
  - GitHub Actions pinned to commit SHAs for supply chain security

- **Snyk Integration**
  - `requirements.txt` and `requirements-dev.txt` with pinned versions for Snyk Open Source scanning
  - `.snyk.env` for VS Code extension environment configuration
  - `defusedxml` added to dev dependencies for secure XML parsing in tests

- **Expanded Public API**
  - Exported `generate_ansible_playbook_template`, `export_nornir_groups`, `generate_nornir_config`, `generate_nornir_script_template` from exporters package

- **Interactive Mode Validation**
  - IPv4, multicast address, and CIDR format validators for interactive input
  - Graceful cancellation handling (Ctrl+C) throughout questionary prompts

### Fixed

- **Bandwidth Calculator**
  - Spine total bandwidth now correctly distributes load across spines (`leaf_count * leaf_uplink_bw / spine_count`)
  - Bisection bandwidth corrected to half-cut model (`leaf_count * leaf_uplink_bw / 2`)
  - Worst-case failure scenario now properly calculates uplinks lost per spine
  - ZeroDivisionError on zero spine/leaf/uplink/downlink counts

- **eBGP Calculator**
  - P2P link addressing now supports RFC 3021 /31 networks (uses `list(subnet)` instead of `subnet.hosts()`)
  - `base_asn=0` no longer silently skipped due to truthiness fix

- **EVPN Calculator**
  - L3 VNI vendor configs now correctly generated when `l3_vni=0` (truthiness fix)

- **Fabric Calculator**
  - Network capacity calculation correct for /31 and /32 networks
  - P2P /31 subnet generation uses RFC 3021 addressing

- **Multicast Calculator**
  - Groups used count calculated correctly upfront for SHARED and RANGE_BASED schemes

- **Multihoming Calculator**
  - ESI Type-0 format corrected to exactly 10 bytes per RFC 7432 (was generating 9 bytes)
  - ES-Import Route Target for Type-3 ESI now incorporates local discriminator bytes for uniqueness
  - PE loopback IP generation handles octet overflow (>254) by incrementing third octet

- **Route Reflector Calculator**
  - `custom_cluster_count=1` no longer ignored (truthiness fix: `if value:` -> `if value is not None:`)
  - Fallback IP generation avoids .0 network addresses
  - Total BGP sessions in design notes corrected to `clients_per_cluster * rrs_per_cluster * cluster_count`

- **Containerlab Exporter**
  - NXOS kind mapping corrected to `cisco_nxos9000v`
  - Host node names now included in collision detection

- **Ansible Exporter**
  - `None` values filtered from EVPN/fabric/VNI output instead of being written as `null`
  - Zero values (`bgp_as=0`, `asn=0`, `l3_vni=0`) no longer dropped from output
  - Spine/leaf nodes with missing `name` key get fallback names instead of KeyError

- **Config Module**
  - Unknown config keys now warned and filtered instead of causing instantiation errors
  - VNI scheme allowlist corrected (`sequential` not `flat`/`hierarchical`)
  - eBGP scheme allowlist corrected (removed invalid `public`)
  - Multicast scheme allowlist corrected (`range-based` not `range`)
  - Atomic file writes for `save_config` using tempfile + rename pattern
  - `import os` added (was missing — `os.close(fd)` in atomic writes would have failed)

- **CLI**
  - `_list_presets_callback` now respects `--config` parameter
  - Loopback/VTEP network exhaustion raises proper error instead of silent fallback

- **Tests**
  - Symlink traversal test skipped on Windows (`sys.platform == "win32"`)
  - XML parsing in test_exporters.py switched from `xml.etree.ElementTree` to `defusedxml.ElementTree`

### Changed

- Project status upgraded from "4 - Beta" to "5 - Production/Stable"
- Comprehensive code formatting with Ruff across all modules
- 439 unit tests (up from 340+ in v1.0.0)

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

[Unreleased]: https://github.com/ashimov/evpn-ninja/compare/v1.0.3...HEAD
[1.0.3]: https://github.com/ashimov/evpn-ninja/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/ashimov/evpn-ninja/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/ashimov/evpn-ninja/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/ashimov/evpn-ninja/releases/tag/v1.0.0
