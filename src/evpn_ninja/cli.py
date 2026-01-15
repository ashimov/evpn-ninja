"""EVPN Ninja - VXLAN/EVPN Fabric Calculator CLI."""

from pathlib import Path
from typing import Annotated, Any, Optional
import json

import typer
import yaml
from rich.console import Console

from evpn_ninja import __version__
from evpn_ninja.output import (
    OutputFormat,
    output_json,
    output_yaml,
    output_table,
    output_key_value,
    output_config,
    console,
    configure_console,
)
from evpn_ninja.config import (
    Config,
    load_config,
    save_config,
    get_preset,
    list_presets,
    BUILTIN_PRESETS,
    DEFAULT_CONFIG_PATH,
)
from evpn_ninja.calculators.mtu import calculate_mtu, UnderlayType
from evpn_ninja.calculators.vni import calculate_vni_allocation, VNIScheme
from evpn_ninja.calculators.fabric import calculate_fabric_params, ReplicationMode
from evpn_ninja.calculators.evpn import calculate_evpn_params, Vendor
from evpn_ninja.calculators.ebgp import calculate_ebgp_underlay, ASNScheme
from evpn_ninja.calculators.multicast import calculate_multicast_groups, MulticastScheme
from evpn_ninja.calculators.route_reflector import (
    calculate_route_reflector,
    RRPlacement,
    RRRedundancy,
)
from evpn_ninja.calculators.bandwidth import calculate_bandwidth, LinkSpeed
from evpn_ninja.calculators.topology import generate_topology
from evpn_ninja.calculators.multihoming import (
    calculate_multihoming,
    MultiHomingMode,
    ESIType,
)
from evpn_ninja.validators import (
    ipv4_address_callback,
    network_callback,
    multicast_callback,
)

app = typer.Typer(
    name="evpn-ninja",
    help="EVPN Ninja - VXLAN/EVPN fabric calculator for VNI allocation, fabric planning, EVPN parameters, MTU calculation",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Global state for options
_no_color = False
_verbose = False
_config: Config = Config()
_active_preset: str | None = None


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"evpn-ninja v{__version__}")
        raise typer.Exit()


def _list_presets_callback(value: bool) -> None:
    """List available presets and exit."""
    if value:
        console.print("[bold]Built-in Presets:[/bold]")
        for name, preset in BUILTIN_PRESETS.items():
            console.print(f"  [cyan]{name}[/cyan]: {preset.description}")

        if _config.presets:
            console.print("\n[bold]User Presets:[/bold]")
            for name, preset in _config.presets.items():
                console.print(f"  [cyan]{name}[/cyan]: {preset.description}")

        raise typer.Exit()


def _save_output(content: str, filepath: Path) -> None:
    """Save output to file."""
    filepath.write_text(content)
    if not _no_color:
        console.print(f"[green]Saved to {filepath}[/green]")
    else:
        print(f"Saved to {filepath}")


def _get_console() -> Console:
    """Get console with color settings."""
    return Console(no_color=_no_color, force_terminal=not _no_color)


def _get_default(section: str, key: str, fallback: Any = None) -> Any:
    """Get default value from config.

    Args:
        section: Config section (mtu, vni, fabric, evpn, ebgp, multicast)
        key: Key within the section
        fallback: Fallback value if not found

    Returns:
        Value from config or fallback
    """
    section_obj = getattr(_config, section, None)
    if section_obj is None:
        return fallback
    return getattr(section_obj, key, fallback)


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-V", callback=version_callback, is_eager=True, help="Show version")
    ] = None,
    config_file: Annotated[
        Optional[Path],
        typer.Option("--config", "-c", help="Path to config file (default: ~/.vxlan.yaml)")
    ] = None,
    preset: Annotated[
        Optional[str],
        typer.Option("--preset", "-P", help="Use preset configuration (small-dc, medium-dc, large-dc, etc.)")
    ] = None,
    list_presets_flag: Annotated[
        Optional[bool],
        typer.Option("--list-presets", callback=_list_presets_callback, is_eager=True, help="List available presets")
    ] = None,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable colored output (for piping)")
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Verbose output with extra details")
    ] = False,
) -> None:
    """VXLAN/EVPN Calculator CLI.

    Configuration can be loaded from:
    - ~/.vxlan.yaml (default)
    - Custom file via --config
    - Built-in presets via --preset (small-dc, medium-dc, large-dc, multi-tenant, campus)
    """
    global _no_color, _verbose, _config, _active_preset
    _no_color = no_color
    _verbose = verbose
    if no_color:
        configure_console(no_color=True)

    # Load config file
    _config = load_config(config_file)

    # Apply preset if specified
    if preset:
        _active_preset = preset
        # Check built-in presets first
        if preset in BUILTIN_PRESETS:
            preset_obj = BUILTIN_PRESETS[preset]
        else:
            preset_obj = get_preset(_config, preset)

        if not preset_obj:
            console.print(f"[red]Unknown preset: {preset}[/red]")
            console.print("Use --list-presets to see available presets")
            raise typer.Exit(1)

        # Merge preset into config defaults
        if preset_obj.fabric:
            for key, val in preset_obj.fabric.items():
                if hasattr(_config.fabric, key):
                    setattr(_config.fabric, key, val)
        if preset_obj.ebgp:
            for key, val in preset_obj.ebgp.items():
                if hasattr(_config.ebgp, key):
                    setattr(_config.ebgp, key, val)
        if preset_obj.evpn:
            for key, val in preset_obj.evpn.items():
                if hasattr(_config.evpn, key):
                    setattr(_config.evpn, key, val)
        if preset_obj.vni:
            for key, val in preset_obj.vni.items():
                if hasattr(_config.vni, key):
                    setattr(_config.vni, key, val)
        if preset_obj.multicast:
            for key, val in preset_obj.multicast.items():
                if hasattr(_config.multicast, key):
                    setattr(_config.multicast, key, val)

        if _verbose:
            console.print(f"[dim]Using preset: {preset}[/dim]")


# =============================================================================
# MTU Command
# =============================================================================

@app.command()
def mtu(
    payload: Annotated[int, typer.Option("--payload", "-p", help="Inner payload size in bytes")] = 1500,
    underlay: Annotated[
        UnderlayType,
        typer.Option("--underlay", "-u", help="Underlay network type")
    ] = UnderlayType.IPV4,
    outer_vlan_tags: Annotated[
        int,
        typer.Option("--outer-vlans", help="Number of VLAN tags on outer frame (0-2)")
    ] = 0,
    inner_vlan_tags: Annotated[
        int,
        typer.Option("--inner-vlans", help="Number of VLAN tags on inner frame (0-2)")
    ] = 0,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format")
    ] = OutputFormat.TABLE,
    save: Annotated[
        Optional[Path],
        typer.Option("--save", "-s", help="Save output to file")
    ] = None,
) -> None:
    """Calculate required MTU for VXLAN encapsulation."""
    result = calculate_mtu(
        payload_size=payload,
        underlay_type=underlay,
        outer_vlan_tags=outer_vlan_tags,
        inner_vlan_tags=inner_vlan_tags,
    )

    if output == OutputFormat.JSON:
        content = json.dumps(result.__dict__, default=lambda o: o.__dict__, indent=2)
        if save:
            _save_output(content, save)
        else:
            output_json(result)
    elif output == OutputFormat.YAML:
        if save:
            content = yaml.dump(result.__dict__, default_flow_style=False)
            _save_output(content, save)
        else:
            output_yaml(result)
    else:
        output_table(
            title="VXLAN MTU Breakdown",
            columns=["Layer", "Size (bytes)", "Description"],
            rows=[[layer.name, str(layer.size), layer.description] for layer in result.layers],
        )
        console.print()
        output_key_value("Summary", {
            "Total Overhead": f"{result.total_overhead} bytes",
            "Total Frame Size": f"{result.total_frame_size} bytes",
            "Required MTU": f"{result.required_mtu} bytes",
            "Recommended MTU": f"{result.recommended_mtu} bytes",
        })


# =============================================================================
# VNI Command
# =============================================================================

@app.command()
def vni(
    scheme: Annotated[
        Optional[VNIScheme],
        typer.Option("--scheme", "-s", help="VNI allocation scheme")
    ] = None,
    base_vni: Annotated[Optional[int], typer.Option("--base-vni", "-b", help="Base VNI number")] = None,
    tenant_id: Annotated[int, typer.Option("--tenant-id", "-t", help="Tenant ID (for tenant-based scheme)")] = 1,
    start_vlan: Annotated[Optional[int], typer.Option("--start-vlan", help="Starting VLAN ID")] = None,
    count: Annotated[Optional[int], typer.Option("--count", "-c", help="Number of VNIs to allocate")] = None,
    multicast_base: Annotated[
        Optional[str],
        typer.Option("--mcast-base", help="Base multicast address", callback=multicast_callback)
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format")
    ] = OutputFormat.TABLE,
    save: Annotated[
        Optional[Path],
        typer.Option("--save", help="Save output to file")
    ] = None,
) -> None:
    """Calculate VNI allocation based on selected scheme.

    Uses values from config file or preset if not specified.
    """
    # Apply defaults from config
    scheme = scheme if scheme is not None else VNIScheme(_config.vni.scheme)
    base_vni = base_vni if base_vni is not None else _config.vni.base_vni
    start_vlan = start_vlan if start_vlan is not None else _config.vni.start_vlan
    count = count if count is not None else _config.vni.count
    multicast_base = multicast_base if multicast_base is not None else _config.vni.multicast_base

    result = calculate_vni_allocation(
        scheme=scheme,
        base_vni=base_vni,
        tenant_id=tenant_id,
        start_vlan=start_vlan,
        count=count,
        multicast_base=multicast_base,
    )

    if output == OutputFormat.JSON:
        output_json(result)
    elif output == OutputFormat.YAML:
        output_yaml(result)
    else:
        output_key_value("VNI Allocation Parameters", {
            "Scheme": result.scheme,
            "Base VNI": result.base_vni,
            "Tenant ID": result.tenant_id or "N/A",
            "Start VLAN": result.start_vlan,
            "Count": result.count,
        })
        console.print()
        output_table(
            title="VNI Allocation Table",
            columns=["VLAN ID", "VNI (Decimal)", "VNI (Hex)", "Multicast Group"],
            rows=[
                [str(e.vlan_id), str(e.vni_decimal), e.vni_hex, e.multicast_group]
                for e in result.entries
            ],
        )


# =============================================================================
# Fabric Command
# =============================================================================

@app.command()
def fabric(
    vteps: Annotated[Optional[int], typer.Option("--vteps", help="Number of VTEP (leaf) switches")] = None,
    spines: Annotated[Optional[int], typer.Option("--spines", help="Number of spine switches")] = None,
    vnis: Annotated[Optional[int], typer.Option("--vnis", help="Total number of VNIs")] = None,
    hosts: Annotated[Optional[int], typer.Option("--hosts", "-h", help="Average hosts per VTEP")] = None,
    replication: Annotated[
        Optional[ReplicationMode],
        typer.Option("--replication", "-r", help="BUM replication mode")
    ] = None,
    loopback_net: Annotated[
        Optional[str],
        typer.Option("--loopback-net", help="Loopback network", callback=network_callback)
    ] = None,
    vtep_net: Annotated[
        Optional[str],
        typer.Option("--vtep-net", help="VTEP loopback network", callback=network_callback)
    ] = None,
    p2p_net: Annotated[
        Optional[str],
        typer.Option("--p2p-net", help="P2P links network", callback=network_callback)
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format")
    ] = OutputFormat.TABLE,
    save: Annotated[
        Optional[Path],
        typer.Option("--save", help="Save output to file")
    ] = None,
) -> None:
    """Calculate fabric parameters for VXLAN/EVPN deployment.

    Uses values from config file or preset if not specified.
    """
    # Apply defaults from config
    vteps = vteps if vteps is not None else _config.fabric.vtep_count
    spines = spines if spines is not None else _config.fabric.spine_count
    vnis = vnis if vnis is not None else _config.fabric.vni_count
    hosts = hosts if hosts is not None else _config.fabric.hosts_per_vtep
    replication = replication if replication is not None else ReplicationMode(_config.fabric.replication_mode)
    loopback_net = loopback_net if loopback_net is not None else _config.fabric.loopback_network
    vtep_net = vtep_net if vtep_net is not None else _config.fabric.vtep_loopback_network
    p2p_net = p2p_net if p2p_net is not None else _config.fabric.p2p_network

    result = calculate_fabric_params(
        vtep_count=vteps,
        spine_count=spines,
        vni_count=vnis,
        hosts_per_vtep=hosts,
        replication_mode=replication,
        loopback_network=loopback_net,
        vtep_loopback_network=vtep_net,
        p2p_network=p2p_net,
    )

    if output == OutputFormat.JSON:
        output_json(result)
    elif output == OutputFormat.YAML:
        output_yaml(result)
    else:
        output_key_value("Fabric Topology", {
            "VTEP (Leaf) Count": result.vtep_count,
            "Spine Count": result.spine_count,
            "VNI Count": result.vni_count,
            "Hosts per VTEP": result.hosts_per_vtep,
            "Replication Mode": result.replication_mode,
            "Total P2P Links": result.p2p_links_total,
        })
        console.print()

        output_table(
            title=result.loopback_allocation.name,
            columns=["Assignment"],
            rows=[[addr] for addr in result.loopback_allocation.addresses],
            caption=f"Network: {result.loopback_allocation.network}",
        )
        console.print()

        output_table(
            title=result.vtep_loopback_allocation.name,
            columns=["Assignment"],
            rows=[[addr] for addr in result.vtep_loopback_allocation.addresses],
            caption=f"Network: {result.vtep_loopback_allocation.network}",
        )
        console.print()

        output_table(
            title=result.p2p_allocation.name,
            columns=["Link"],
            rows=[[addr] for addr in result.p2p_allocation.addresses],
            caption=f"Network: {result.p2p_allocation.network}",
        )
        console.print()

        output_key_value("Resource Estimates", {
            "Total MAC Entries": result.estimates.total_mac_entries,
            "MAC Entries per VTEP": result.estimates.mac_entries_per_vtep,
            "EVPN Type-2 Routes": result.estimates.evpn_type2_routes,
            "EVPN Type-3 Routes": result.estimates.evpn_type3_routes,
            "BGP Sessions per Leaf": result.estimates.bgp_sessions_per_leaf,
            "BGP Sessions Total": result.estimates.bgp_sessions_total,
            "BUM Replication Factor": result.estimates.bum_replication_factor,
        })

        # Display warnings if any
        if result.warnings:
            console.print()
            console.print("[bold yellow]Warnings:[/bold yellow]")
            for warning in result.warnings:
                console.print(f"  [yellow]! {warning.message}[/yellow]")


# =============================================================================
# EVPN Command
# =============================================================================

@app.command()
def evpn(
    bgp_as: Annotated[Optional[int], typer.Option("--as", help="BGP AS number")] = None,
    loopback: Annotated[
        Optional[str],
        typer.Option("--loopback", "-l", help="VTEP loopback IP", callback=ipv4_address_callback)
    ] = None,
    l2_vni: Annotated[int, typer.Option("--l2-vni", help="Layer 2 VNI")] = 10010,
    vlan_id: Annotated[int, typer.Option("--vlan", help="VLAN ID")] = 10,
    l3_vni: Annotated[Optional[int], typer.Option("--l3-vni", help="Layer 3 VNI (optional)")] = None,
    vrf_name: Annotated[Optional[str], typer.Option("--vrf", help="VRF name (optional)")] = None,
    vendor: Annotated[
        Optional[list[Vendor]],
        typer.Option("--vendor", help="Vendor(s) to generate config for")
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format")
    ] = OutputFormat.TABLE,
    save: Annotated[
        Optional[Path],
        typer.Option("--save", help="Save output to file")
    ] = None,
) -> None:
    """Calculate EVPN parameters and generate vendor configurations.

    Uses values from config file or preset if not specified.
    """
    # Apply defaults from config
    bgp_as = bgp_as if bgp_as is not None else _config.evpn.bgp_as
    loopback = loopback if loopback is not None else _config.evpn.loopback_ip

    # Use configured vendors if none specified and config has vendors
    if vendor is None and _config.evpn.vendors:
        vendor = [Vendor(v) for v in _config.evpn.vendors]

    result = calculate_evpn_params(
        bgp_as=bgp_as,
        loopback_ip=loopback,
        l2_vni=l2_vni,
        vlan_id=vlan_id,
        l3_vni=l3_vni,
        vrf_name=vrf_name,
        vendors=vendor,
    )

    if output == OutputFormat.JSON:
        output_json(result)
    elif output == OutputFormat.YAML:
        output_yaml(result)
    else:
        output_key_value("Input Parameters", {
            "BGP AS": result.bgp_as,
            "Loopback IP": result.loopback_ip,
            "L2 VNI": result.l2_vni,
            "VLAN ID": result.vlan_id,
            "L3 VNI": result.l3_vni or "N/A",
            "VRF Name": result.vrf_name or "N/A",
        })
        console.print()

        output_key_value("L2 EVPN Parameters", {
            "Route Distinguisher (RD)": result.l2_params.route_distinguisher,
            "Route Target Import": result.l2_params.route_target_import,
            "Route Target Export": result.l2_params.route_target_export,
            "EVI": result.l2_params.evi,
        })

        if result.l3_params:
            console.print()
            output_key_value("L3 EVPN Parameters", {
                "Route Distinguisher (RD)": result.l3_params.route_distinguisher,
                "Route Target Import": result.l3_params.route_target_import,
                "Route Target Export": result.l3_params.route_target_export,
                "EVI": result.l3_params.evi,
            })

        console.print()
        for cfg in result.configs:
            output_config(f"{cfg.vendor.upper()} Configuration", cfg.config)
            console.print()

    if save:
        # Save all configs to file
        content = "\n\n".join([f"# {cfg.vendor.upper()}\n{cfg.config}" for cfg in result.configs])
        _save_output(content, save)


# =============================================================================
# eBGP Underlay Command
# =============================================================================

@app.command()
def ebgp(
    spines: Annotated[Optional[int], typer.Option("--spines", "-s", help="Number of spine switches")] = None,
    leaves: Annotated[Optional[int], typer.Option("--leaves", "-l", help="Number of leaf switches")] = None,
    scheme: Annotated[
        Optional[ASNScheme],
        typer.Option("--scheme", help="ASN allocation scheme")
    ] = None,
    base_asn: Annotated[
        Optional[int],
        typer.Option("--base-asn", help="Base ASN (for custom scheme)")
    ] = None,
    p2p_net: Annotated[
        Optional[str],
        typer.Option("--p2p-net", help="P2P links network", callback=network_callback)
    ] = None,
    spine_same_asn: Annotated[
        Optional[bool],
        typer.Option("--spine-same-asn/--spine-unique-asn", help="Spines share same ASN")
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format")
    ] = OutputFormat.TABLE,
    save: Annotated[
        Optional[Path],
        typer.Option("--save", help="Save output to file")
    ] = None,
) -> None:
    """Calculate eBGP underlay parameters (RFC 7938).

    Uses values from config file or preset if not specified.
    """
    # Apply defaults from config
    spines = spines if spines is not None else _config.ebgp.spine_count
    leaves = leaves if leaves is not None else _config.ebgp.leaf_count
    scheme = scheme if scheme is not None else ASNScheme(_config.ebgp.scheme)
    p2p_net = p2p_net if p2p_net is not None else _config.ebgp.p2p_network
    spine_same_asn = spine_same_asn if spine_same_asn is not None else _config.ebgp.spine_asn_same

    result = calculate_ebgp_underlay(
        spine_count=spines,
        leaf_count=leaves,
        scheme=scheme,
        base_asn=base_asn,
        p2p_network=p2p_net,
        spine_asn_same=spine_same_asn,
    )

    if output == OutputFormat.JSON:
        output_json(result)
    elif output == OutputFormat.YAML:
        output_yaml(result)
    else:
        output_key_value("eBGP Underlay Configuration", {
            "ASN Scheme": result.scheme,
            "Spine Count": result.spine_count,
            "Leaf Count": result.leaf_count,
            "Base ASN": result.base_asn,
            "Spine ASN Range": result.spine_asn_range,
            "Leaf ASN Range": result.leaf_asn_range,
            "Total BGP Sessions": result.total_sessions,
        })
        console.print()

        output_table(
            title="ASN Assignments",
            columns=["Device", "Role", "ASN"],
            rows=[
                [asn.device_name, asn.device_role, str(asn.asn)]
                for asn in result.asn_assignments
            ],
        )
        console.print()

        output_table(
            title="BGP Sessions",
            columns=["Device A", "IP A", "ASN A", "Device B", "IP B", "ASN B"],
            rows=[
                [s.device_a, s.device_a_ip, str(s.device_a_asn),
                 s.device_b, s.device_b_ip, str(s.device_b_asn)]
                for s in result.bgp_sessions[:20]  # Limit to 20 for display
            ] + ([["...", "...", "...", "...", "...", "..."]] if len(result.bgp_sessions) > 20 else []),
            caption=f"P2P Network: {result.p2p_network}",
        )


# =============================================================================
# Multicast Command
# =============================================================================

@app.command()
def multicast(
    vni_start: Annotated[Optional[int], typer.Option("--vni-start", help="Starting VNI")] = None,
    vni_count: Annotated[Optional[int], typer.Option("--vni-count", "-c", help="Number of VNIs")] = None,
    scheme: Annotated[
        Optional[MulticastScheme],
        typer.Option("--scheme", "-s", help="Multicast allocation scheme")
    ] = None,
    base_group: Annotated[
        Optional[str],
        typer.Option("--base-group", "-g", help="Base multicast group address", callback=multicast_callback)
    ] = None,
    vnis_per_group: Annotated[
        Optional[int],
        typer.Option("--vnis-per-group", help="VNIs per group (for shared/range schemes)")
    ] = None,
    rp_address: Annotated[
        Optional[str],
        typer.Option("--rp", help="PIM Rendezvous Point address", callback=ipv4_address_callback)
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format")
    ] = OutputFormat.TABLE,
    save: Annotated[
        Optional[Path],
        typer.Option("--save", help="Save output to file")
    ] = None,
) -> None:
    """Calculate multicast groups for VXLAN BUM replication.

    Uses values from config file or preset if not specified.
    """
    # Apply defaults from config
    vni_start = vni_start if vni_start is not None else _config.multicast.vni_start
    vni_count = vni_count if vni_count is not None else _config.multicast.vni_count
    scheme = scheme if scheme is not None else MulticastScheme(_config.multicast.scheme)
    base_group = base_group if base_group is not None else _config.multicast.base_group
    vnis_per_group = vnis_per_group if vnis_per_group is not None else _config.multicast.vnis_per_group

    result = calculate_multicast_groups(
        vni_start=vni_start,
        vni_count=vni_count,
        scheme=scheme,
        base_group=base_group,
        vnis_per_group=vnis_per_group,
        rp_address=rp_address,
    )

    if output == OutputFormat.JSON:
        output_json(result)
    elif output == OutputFormat.YAML:
        output_yaml(result)
    else:
        output_key_value("Multicast Configuration", {
            "Scheme": result.scheme,
            "Base Group": result.base_group,
            "VNI Start": result.vni_start,
            "VNI Count": result.vni_count,
            "Groups Used": result.groups_used,
        })
        console.print()

        # Show first 20 mappings
        output_table(
            title="VNI to Multicast Mappings",
            columns=["VNI", "Multicast Group"],
            rows=[
                [str(m.vni), m.multicast_group]
                for m in result.mappings[:20]
            ] + ([["...", "..."]] if len(result.mappings) > 20 else []),
        )
        console.print()

        output_key_value("Underlay Requirements", result.underlay_requirements)

        if result.pim_config:
            console.print()
            output_key_value("PIM Configuration", {
                "RP Address": result.pim_config.rp_address,
                "Group Range": result.pim_config.rp_group_range,
                "Anycast RP": "Yes" if result.pim_config.anycast_rp else "No",
            })


# =============================================================================
# Route Reflector Command
# =============================================================================

@app.command()
def rr(
    clients: Annotated[int, typer.Option("--clients", "-c", help="Number of BGP clients (VTEPs)")] = 10,
    bgp_as: Annotated[int, typer.Option("--as", help="BGP AS number")] = 65000,
    placement: Annotated[
        RRPlacement,
        typer.Option("--placement", "-p", help="RR placement strategy")
    ] = RRPlacement.SPINE,
    redundancy: Annotated[
        RRRedundancy,
        typer.Option("--redundancy", "-r", help="RR redundancy model")
    ] = RRRedundancy.PAIR,
    rr_network: Annotated[
        str,
        typer.Option("--rr-network", help="RR loopback network", callback=network_callback)
    ] = "10.255.0.0/24",
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format")
    ] = OutputFormat.TABLE,
    save: Annotated[
        Optional[Path],
        typer.Option("--save", help="Save output to file")
    ] = None,
) -> None:
    """Calculate BGP Route Reflector configuration for EVPN overlay."""
    result = calculate_route_reflector(
        client_count=clients,
        bgp_as=bgp_as,
        placement=placement,
        redundancy=redundancy,
        rr_loopback_network=rr_network,
    )

    if output == OutputFormat.JSON:
        output_json(result)
    elif output == OutputFormat.YAML:
        output_yaml(result)
    else:
        output_key_value("Route Reflector Design", {
            "Placement": result.placement,
            "Redundancy": result.redundancy,
            "BGP AS": result.bgp_as,
            "Total RR Nodes": result.total_rr_nodes,
            "Total Clients": result.total_clients,
        })
        console.print()

        for cluster in result.clusters:
            output_table(
                title=f"Cluster {cluster.cluster_id}",
                columns=["Name", "Loopback IP", "Role"],
                rows=[
                    [m.name, m.loopback_ip, m.role]
                    for m in cluster.members
                ],
                caption=f"Clients: ~{cluster.client_count}",
            )
            console.print()

        output_table(
            title="BGP Peer Groups",
            columns=["Name", "Description", "RR Client"],
            rows=[
                [pg.name, pg.description, "Yes" if pg.route_reflector_client else "No"]
                for pg in result.peer_groups
            ],
        )
        console.print()

        console.print("[bold]Design Notes:[/bold]")
        for note in result.design_notes:
            console.print(f"  - {note}")
        console.print()

        output_config("Sample RR Configuration", result.config_template)

    if save:
        _save_output(result.config_template, save)


# =============================================================================
# Bandwidth Command
# =============================================================================

@app.command()
def bandwidth(
    spines: Annotated[int, typer.Option("--spines", "-s", help="Number of spine switches")] = 2,
    leaves: Annotated[int, typer.Option("--leaves", "-l", help="Number of leaf switches")] = 4,
    uplink_speed: Annotated[
        LinkSpeed,
        typer.Option("--uplink-speed", help="Leaf-to-spine link speed")
    ] = LinkSpeed.GE_100,
    uplinks: Annotated[
        int,
        typer.Option("--uplinks", "-u", help="Uplinks per leaf")
    ] = 2,
    downlink_speed: Annotated[
        LinkSpeed,
        typer.Option("--downlink-speed", help="Host-facing link speed")
    ] = LinkSpeed.GE_25,
    downlinks: Annotated[
        int,
        typer.Option("--downlinks", "-d", help="Downlink ports per leaf")
    ] = 48,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format")
    ] = OutputFormat.TABLE,
    save: Annotated[
        Optional[Path],
        typer.Option("--save", help="Save output to file")
    ] = None,
) -> None:
    """Calculate fabric bandwidth and oversubscription ratios."""
    result = calculate_bandwidth(
        spine_count=spines,
        leaf_count=leaves,
        uplink_speed=uplink_speed,
        uplink_count_per_leaf=uplinks,
        downlink_speed=downlink_speed,
        downlink_count_per_leaf=downlinks,
    )

    if output == OutputFormat.JSON:
        output_json(result)
    elif output == OutputFormat.YAML:
        output_yaml(result)
    else:
        output_key_value("Fabric Topology", {
            "Spine Count": result.spine_count,
            "Leaf Count": result.leaf_count,
            "Uplink Speed": result.uplink_speed,
            "Uplinks per Leaf": result.uplink_count_per_leaf,
            "Downlink Speed": result.downlink_speed,
            "Downlinks per Leaf": result.downlink_count_per_leaf,
        })
        console.print()

        output_key_value("Bandwidth Summary", {
            "Leaf Uplink Bandwidth": f"{result.leaf_uplink_bandwidth_gbps} Gbps",
            "Leaf Downlink Bandwidth": f"{result.leaf_downlink_bandwidth_gbps} Gbps",
            "Spine Total Bandwidth": f"{result.spine_total_bandwidth_gbps} Gbps",
            "Fabric Bisection Bandwidth": f"{result.fabric_bisection_bandwidth_gbps} Gbps",
        })
        console.print()

        oversub = result.leaf_oversubscription
        status = "[green]Non-blocking[/green]" if oversub.is_non_blocking else f"[yellow]{oversub.oversubscription_ratio:.1f}:1[/yellow]"
        output_key_value("Oversubscription Analysis", {
            "Tier": oversub.tier_name,
            "Downlink BW": f"{oversub.downlink_bandwidth_gbps} Gbps",
            "Uplink BW": f"{oversub.uplink_bandwidth_gbps} Gbps",
            "Ratio": status,
        })
        console.print()

        output_key_value("ECMP Analysis", {
            "ECMP Paths": result.ecmp_paths,
            "Hash Efficiency": f"{result.hash_efficiency * 100:.0f}%",
        })
        console.print()

        output_table(
            title="Failure Scenarios",
            columns=["Scenario", "Remaining BW", "Reduction", "Status"],
            rows=[
                [
                    fs.scenario,
                    f"{fs.remaining_bandwidth_gbps:.0f} Gbps",
                    f"{fs.bandwidth_reduction_percent:.0f}%",
                    "[green]OK[/green]" if fs.still_operational else "[red]FAIL[/red]",
                ]
                for fs in result.failure_scenarios
            ],
        )
        console.print()

        console.print("[bold]Recommendations:[/bold]")
        for rec in result.recommendations:
            console.print(f"  - {rec}")


# =============================================================================
# Topology Command
# =============================================================================

@app.command()
def topology(
    spines: Annotated[int, typer.Option("--spines", "-s", help="Number of spine switches")] = 2,
    leaves: Annotated[int, typer.Option("--leaves", "-l", help="Number of leaf switches")] = 4,
    uplink_speed: Annotated[str, typer.Option("--uplink-speed", help="Leaf-to-spine link speed")] = "100G",
    downlink_speed: Annotated[str, typer.Option("--downlink-speed", help="Host-facing link speed")] = "25G",
    format_type: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: ascii, dot, or both")
    ] = "both",
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Data output format (json/yaml)")
    ] = OutputFormat.TABLE,
    save: Annotated[
        Optional[Path],
        typer.Option("--save", help="Save Graphviz DOT to file")
    ] = None,
) -> None:
    """Generate leaf-spine topology visualization (ASCII or Graphviz DOT)."""
    result = generate_topology(
        spine_count=spines,
        leaf_count=leaves,
        uplink_speed=uplink_speed,
        downlink_speed=downlink_speed,
    )

    if output == OutputFormat.JSON:
        output_json(result)
    elif output == OutputFormat.YAML:
        output_yaml(result)
    else:
        if format_type in ("ascii", "both"):
            console.print(result.ascii_art)
            console.print()

        if format_type in ("dot", "both"):
            console.print("[bold]Graphviz DOT Output:[/bold]")
            console.print("(Save with --save topology.dot, then: dot -Tpng topology.dot -o topology.png)")
            console.print()
            output_config("Graphviz DOT", result.graphviz_dot)

    if save:
        _save_output(result.graphviz_dot, save)
        console.print(f"\n[dim]Render with: dot -Tpng {save} -o {save.stem}.png[/dim]")


# =============================================================================
# Interactive Command
# =============================================================================

@app.command()
def interactive() -> None:
    """Launch interactive mode with guided input."""
    from evpn_ninja.interactive import run_interactive
    run_interactive()


# =============================================================================
# Export Command
# =============================================================================

@app.command()
def export(
    format_type: Annotated[
        str,
        typer.Argument(help="Export format: ansible, nornir, containerlab, eve-ng, gns3, or all")
    ] = "ansible",
    spines: Annotated[int, typer.Option("--spines", "-s", help="Number of spine switches")] = 2,
    leaves: Annotated[int, typer.Option("--leaves", "-l", help="Number of leaf switches")] = 4,
    bgp_as: Annotated[int, typer.Option("--as", help="BGP AS number")] = 65000,
    loopback_net: Annotated[
        str,
        typer.Option("--loopback-net", help="Loopback network", callback=network_callback)
    ] = "10.0.0.0/24",
    vtep_net: Annotated[
        str,
        typer.Option("--vtep-net", help="VTEP loopback network", callback=network_callback)
    ] = "10.0.1.0/24",
    platform: Annotated[
        str,
        typer.Option("--platform", "-p", help="Device platform (eos, nxos, srlinux, sonic, etc.)")
    ] = "eos",
    lab_name: Annotated[
        str,
        typer.Option("--lab-name", help="Containerlab lab name")
    ] = "vxlan-fabric",
    include_hosts: Annotated[
        bool,
        typer.Option("--include-hosts/--no-hosts", help="Include test hosts in containerlab")
    ] = False,
    output_dir: Annotated[
        Optional[Path],
        typer.Option("--output-dir", "-o", help="Output directory for files")
    ] = None,
) -> None:
    """Export fabric configuration for automation tools and lab simulators.

    Supported formats:
    - ansible: Ansible inventory and playbooks
    - nornir: Nornir inventory and scripts
    - containerlab: Containerlab topology file (.clab.yml)
    - eve-ng: EVE-NG lab topology file (.unl)
    - gns3: GNS3 project file (.gns3)
    - all: Export all formats

    Examples:
        vxlan export ansible --spines 2 --leaves 4 --output-dir ./ansible
        vxlan export nornir --platform nxos --output-dir ./nornir
        vxlan export containerlab --platform eos --lab-name my-fabric
        vxlan export eve-ng --platform eos --include-hosts
        vxlan export gns3 --platform nxos --lab-name my-lab
        vxlan export all --output-dir ./automation
    """
    from ipaddress import IPv4Network
    from evpn_ninja.exporters.ansible import (
        export_ansible_inventory,
        export_ansible_vars,
        generate_ansible_playbook_template,
    )
    from evpn_ninja.exporters.nornir import (
        export_nornir_inventory,
        export_nornir_groups,
        export_nornir_defaults,
        generate_nornir_config,
        generate_nornir_script_template,
    )
    from evpn_ninja.exporters.containerlab import (
        export_containerlab_topology,
        generate_containerlab_configs,
        generate_makefile,
    )
    from evpn_ninja.exporters.eve_gns3 import (
        export_eve_ng_topology,
        export_gns3_topology,
        generate_eve_ng_startup_scripts,
    )

    format_type = format_type.lower()
    # Support "both" as alias for "all" for backward compatibility
    if format_type == "both":
        format_type = "all"

    valid_formats = ("ansible", "nornir", "containerlab", "eve-ng", "gns3", "all")
    if format_type not in valid_formats:
        console.print(f"[red]Invalid format: {format_type}[/red]")
        console.print(f"Valid options: {', '.join(valid_formats)}")
        raise typer.Exit(1)

    # Generate device lists
    loopback_network = IPv4Network(loopback_net)
    vtep_network = IPv4Network(vtep_net)
    loopback_hosts = list(loopback_network.hosts())
    vtep_hosts = list(vtep_network.hosts())

    spine_list = []
    for i in range(spines):
        spine_list.append({
            "name": f"spine-{i + 1}",
            "ip": str(loopback_hosts[i]) if i < len(loopback_hosts) else f"10.0.0.{i + 1}",
            "loopback": str(loopback_hosts[i]) if i < len(loopback_hosts) else f"10.0.0.{i + 1}",
            "asn": bgp_as,
        })

    leaf_list = []
    for i in range(leaves):
        idx = spines + i
        leaf_list.append({
            "name": f"leaf-{i + 1}",
            "ip": str(loopback_hosts[idx]) if idx < len(loopback_hosts) else f"10.0.0.{idx + 1}",
            "loopback": str(loopback_hosts[idx]) if idx < len(loopback_hosts) else f"10.0.0.{idx + 1}",
            "vtep_ip": str(vtep_hosts[i]) if i < len(vtep_hosts) else f"10.0.1.{i + 1}",
            "asn": bgp_as,
        })

    # Generate output
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    if format_type in ("ansible", "all"):
        inventory = export_ansible_inventory(spine_list, leaf_list, bgp_as)
        group_vars = export_ansible_vars(
            fabric_params={
                "spine_count": spines,
                "leaf_count": leaves,
                "loopback_network": loopback_net,
                "vtep_loopback_network": vtep_net,
            }
        )
        playbook = generate_ansible_playbook_template()

        if output_dir:
            ansible_dir = output_dir / "ansible"
            ansible_dir.mkdir(parents=True, exist_ok=True)
            (ansible_dir / "inventory.yaml").write_text(inventory)
            (ansible_dir / "group_vars" / "all.yaml").parent.mkdir(exist_ok=True)
            (ansible_dir / "group_vars" / "all.yaml").write_text(group_vars)
            (ansible_dir / "deploy.yaml").write_text(playbook)
            console.print(f"[green]Ansible files written to {ansible_dir}[/green]")
        else:
            console.print("[bold]Ansible Inventory:[/bold]")
            output_config("inventory.yaml", inventory)
            console.print()
            console.print("[bold]Ansible Group Vars:[/bold]")
            output_config("group_vars/all.yaml", group_vars)

    if format_type in ("nornir", "all"):
        hosts = export_nornir_inventory(spine_list, leaf_list)
        groups = export_nornir_groups(
            fabric_vars={"bgp_as": bgp_as},
            spine_vars={"role": "spine"},
            leaf_vars={"role": "leaf"},
        )
        defaults = export_nornir_defaults(platform=platform)
        config = generate_nornir_config()
        script = generate_nornir_script_template()

        if output_dir:
            nornir_dir = output_dir / "nornir"
            nornir_dir.mkdir(parents=True, exist_ok=True)
            inv_dir = nornir_dir / "inventory"
            inv_dir.mkdir(exist_ok=True)
            (inv_dir / "hosts.yaml").write_text(hosts)
            (inv_dir / "groups.yaml").write_text(groups)
            (inv_dir / "defaults.yaml").write_text(defaults)
            (nornir_dir / "config.yaml").write_text(config)
            (nornir_dir / "deploy.py").write_text(script)
            console.print(f"[green]Nornir files written to {nornir_dir}[/green]")
        else:
            if format_type == "all":
                console.print()
            console.print("[bold]Nornir Hosts:[/bold]")
            output_config("inventory/hosts.yaml", hosts)
            console.print()
            console.print("[bold]Nornir Groups:[/bold]")
            output_config("inventory/groups.yaml", groups)
            console.print()
            console.print("[bold]Nornir Defaults:[/bold]")
            output_config("inventory/defaults.yaml", defaults)

    if format_type in ("containerlab", "all"):
        topology = export_containerlab_topology(
            spines=spine_list,
            leaves=leaf_list,
            lab_name=lab_name,
            platform=platform,
            include_hosts=include_hosts,
        )
        configs = generate_containerlab_configs(
            spines=spine_list,
            leaves=leaf_list,
            platform=platform,
            bgp_as=bgp_as,
        )
        makefile = generate_makefile()

        if output_dir:
            clab_dir = output_dir / "containerlab"
            clab_dir.mkdir(parents=True, exist_ok=True)
            (clab_dir / f"{lab_name}.clab.yml").write_text(topology)
            (clab_dir / "Makefile").write_text(makefile)

            # Write node configs
            configs_dir = clab_dir / "configs"
            configs_dir.mkdir(exist_ok=True)
            for node_name, config_content in configs.items():
                (configs_dir / f"{node_name}.cfg").write_text(config_content)

            console.print(f"[green]Containerlab files written to {clab_dir}[/green]")
            console.print(f"[dim]Deploy with: cd {clab_dir} && make deploy[/dim]")
        else:
            if format_type == "all":
                console.print()
            console.print("[bold]Containerlab Topology:[/bold]")
            output_config(f"{lab_name}.clab.yml", topology)
            console.print()
            console.print(f"[dim]Deploy with: containerlab deploy -t {lab_name}.clab.yml[/dim]")

    if format_type in ("eve-ng", "all"):
        eve_topology = export_eve_ng_topology(
            spines=spine_list,
            leaves=leaf_list,
            lab_name=lab_name,
            platform=platform,
            include_hosts=include_hosts,
        )
        eve_configs = generate_eve_ng_startup_scripts(
            spines=spine_list,
            leaves=leaf_list,
            platform=platform,
            bgp_as=bgp_as,
        )

        if output_dir:
            eve_dir = output_dir / "eve-ng"
            eve_dir.mkdir(parents=True, exist_ok=True)
            (eve_dir / f"{lab_name}.unl").write_text(eve_topology)

            # Write startup configs
            configs_dir = eve_dir / "configs"
            configs_dir.mkdir(exist_ok=True)
            for node_name, config_content in eve_configs.items():
                (configs_dir / f"{node_name}.cfg").write_text(config_content)

            console.print(f"[green]EVE-NG files written to {eve_dir}[/green]")
            console.print("[dim]Import the .unl file into EVE-NG[/dim]")
        else:
            if format_type == "all":
                console.print()
            console.print("[bold]EVE-NG Topology:[/bold]")
            output_config(f"{lab_name}.unl", eve_topology)

    if format_type in ("gns3", "all"):
        gns3_topology = export_gns3_topology(
            spines=spine_list,
            leaves=leaf_list,
            lab_name=lab_name,
            platform=platform,
            include_hosts=include_hosts,
        )

        if output_dir:
            gns3_dir = output_dir / "gns3"
            gns3_dir.mkdir(parents=True, exist_ok=True)
            (gns3_dir / f"{lab_name}.gns3").write_text(gns3_topology)

            console.print(f"[green]GNS3 files written to {gns3_dir}[/green]")
            console.print("[dim]Open the .gns3 file in GNS3[/dim]")
        else:
            if format_type == "all":
                console.print()
            console.print("[bold]GNS3 Project:[/bold]")
            output_config(f"{lab_name}.gns3", gns3_topology)


# =============================================================================
# Shell Completion Command
# =============================================================================

@app.command()
def completion(
    shell: Annotated[
        str,
        typer.Argument(help="Shell type: bash, zsh, fish, or powershell")
    ],
    install: Annotated[
        bool,
        typer.Option("--install", "-i", help="Install completion to shell config")
    ] = False,
) -> None:
    """Generate shell completion script.

    Examples:
        vxlan completion bash > ~/.vxlan-complete.bash
        echo 'source ~/.vxlan-complete.bash' >> ~/.bashrc

        vxlan completion zsh > ~/.vxlan-complete.zsh
        echo 'source ~/.vxlan-complete.zsh' >> ~/.zshrc

        vxlan completion fish > ~/.config/fish/completions/vxlan.fish
    """
    shell = shell.lower()
    valid_shells = ["bash", "zsh", "fish", "powershell"]

    if shell not in valid_shells:
        console.print(f"[red]Invalid shell: {shell}[/red]")
        console.print(f"Valid options: {', '.join(valid_shells)}")
        raise typer.Exit(1)

    # Generate completion script using typer's built-in support
    env_var = "_VXLAN_COMPLETE"
    script_name = "vxlan"

    if shell == "bash":
        script = f'''# Bash completion for vxlan
_{script_name}_completions() {{
    local IFS=$'\\n'
    COMPREPLY=( $(env COMP_WORDS="${{COMP_WORDS[*]}}" \\
                 COMP_CWORD=$COMP_CWORD \\
                 {env_var}=complete_bash \\
                 {script_name}) )
    return 0
}}
complete -o default -F _{script_name}_completions {script_name}
'''
    elif shell == "zsh":
        script = f'''#compdef vxlan
_{script_name}_completions() {{
    eval $(env _TYPER_COMPLETE_ARGS="${{words[1,$CURRENT]}}" \\
           {env_var}=complete_zsh \\
           {script_name})
}}
compdef _{script_name}_completions {script_name}
'''
    elif shell == "fish":
        script = f'''# Fish completion for vxlan
complete -c {script_name} -f -a "(env {env_var}=complete_fish COMP_WORDS=(commandline -cp) COMP_CWORD=(commandline -t) {script_name})"
'''
    else:  # powershell
        script = f'''# PowerShell completion for vxlan
Register-ArgumentCompleter -Native -CommandName {script_name} -ScriptBlock {{
    param($wordToComplete, $commandAst, $cursorPosition)
    $env:{env_var} = 'complete_powershell'
    $env:_TYPER_COMPLETE_ARGS = $commandAst.ToString()
    {script_name} | ForEach-Object {{
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }}
    Remove-Item Env:{env_var}
    Remove-Item Env:_TYPER_COMPLETE_ARGS
}}
'''

    if install:
        # Determine config file
        home = Path.home()
        if shell == "bash":
            config_file = home / ".bashrc"
            source_line = f"\nsource ~/.vxlan-complete.bash"
            completion_file = home / ".vxlan-complete.bash"
        elif shell == "zsh":
            config_file = home / ".zshrc"
            source_line = f"\nsource ~/.vxlan-complete.zsh"
            completion_file = home / ".vxlan-complete.zsh"
        elif shell == "fish":
            config_dir = home / ".config" / "fish" / "completions"
            config_dir.mkdir(parents=True, exist_ok=True)
            completion_file = config_dir / "vxlan.fish"
            config_file = None
            source_line = None
        else:
            config_file = home / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
            source_line = f"\n. ~\\vxlan-complete.ps1"
            completion_file = home / "vxlan-complete.ps1"

        # Write completion script
        completion_file.write_text(script)
        console.print(f"[green]Wrote completion script to {completion_file}[/green]")

        # Add source line to config if needed
        if config_file and source_line:
            if config_file.exists():
                content = config_file.read_text()
                if source_line.strip() not in content:
                    with config_file.open("a") as f:
                        f.write(source_line)
                    console.print(f"[green]Added source line to {config_file}[/green]")
                else:
                    console.print(f"[yellow]Source line already in {config_file}[/yellow]")
            else:
                config_file.write_text(source_line)
                console.print(f"[green]Created {config_file} with source line[/green]")

        console.print("\n[bold]Restart your shell or run:[/bold]")
        if shell in ("bash", "zsh"):
            console.print(f"  source {completion_file}")
        elif shell == "fish":
            console.print("  (Fish loads completions automatically)")
        else:
            console.print(f"  . {completion_file}")
    else:
        # Just print the script
        print(script)


# =============================================================================
# Config Command
# =============================================================================

config_app = typer.Typer(help="Manage VXLAN Calculator configuration")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show() -> None:
    """Show current configuration."""
    config_data = {
        "config_file": str(DEFAULT_CONFIG_PATH),
        "config_exists": DEFAULT_CONFIG_PATH.exists(),
        "active_preset": _active_preset,
        "defaults": {
            "mtu": {
                "payload_size": _config.mtu.payload_size,
                "underlay_type": _config.mtu.underlay_type,
            },
            "vni": {
                "base_vni": _config.vni.base_vni,
                "scheme": _config.vni.scheme,
                "count": _config.vni.count,
            },
            "fabric": {
                "vtep_count": _config.fabric.vtep_count,
                "spine_count": _config.fabric.spine_count,
                "vni_count": _config.fabric.vni_count,
                "replication_mode": _config.fabric.replication_mode,
            },
            "evpn": {
                "bgp_as": _config.evpn.bgp_as,
                "loopback_ip": _config.evpn.loopback_ip,
            },
            "ebgp": {
                "scheme": _config.ebgp.scheme,
                "spine_asn_same": _config.ebgp.spine_asn_same,
            },
        },
    }

    output_yaml(config_data)


@config_app.command("init")
def config_init(
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing config file")
    ] = False,
) -> None:
    """Initialize default configuration file at ~/.vxlan.yaml."""
    if DEFAULT_CONFIG_PATH.exists() and not force:
        console.print(f"[yellow]Config file already exists: {DEFAULT_CONFIG_PATH}[/yellow]")
        console.print("Use --force to overwrite")
        raise typer.Exit(1)

    # Create default config
    default_config = Config()
    save_config(default_config, DEFAULT_CONFIG_PATH)
    console.print(f"[green]Created config file: {DEFAULT_CONFIG_PATH}[/green]")
    console.print("\nEdit this file to customize your defaults.")
    console.print("See 'vxlan config show' for current settings.")


@config_app.command("path")
def config_path() -> None:
    """Show config file path."""
    print(str(DEFAULT_CONFIG_PATH))


# =============================================================================
# Multi-homing Command
# =============================================================================

@app.command()
def multihoming(
    es_count: Annotated[int, typer.Option("--es-count", "-e", help="Number of Ethernet Segments")] = 1,
    peers: Annotated[int, typer.Option("--peers", "-p", help="PE peers per ES")] = 2,
    mode: Annotated[
        MultiHomingMode,
        typer.Option("--mode", "-m", help="Multi-homing mode")
    ] = MultiHomingMode.ACTIVE_ACTIVE,
    esi_type: Annotated[
        ESIType,
        typer.Option("--esi-type", help="ESI type (type-0, type-1, type-3)")
    ] = ESIType.TYPE_0,
    system_mac: Annotated[
        str,
        typer.Option("--system-mac", help="LACP system MAC address")
    ] = "00:00:00:00:00:01",
    vendor: Annotated[
        Optional[list[str]],
        typer.Option("--vendor", "-v", help="Vendor(s) to generate config for")
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format")
    ] = OutputFormat.TABLE,
    save: Annotated[
        Optional[Path],
        typer.Option("--save", help="Save output to file")
    ] = None,
) -> None:
    """Calculate EVPN multi-homing parameters (ESI, LACP, ES-RT).

    Generates Ethernet Segment Identifiers, LACP configurations,
    and vendor-specific multi-homing configs.

    Examples:

        evpn-ninja multihoming --es-count 4 --mode active-active

        evpn-ninja multihoming --esi-type type-1 --vendor arista
    """
    result = calculate_multihoming(
        es_count=es_count,
        peers_per_es=peers,
        mode=mode,
        esi_type=esi_type,
        system_mac=system_mac,
        vendors=vendor,
    )

    if output == OutputFormat.JSON:
        output_json(result)
    elif output == OutputFormat.YAML:
        output_yaml(result)
    else:
        # Summary
        output_key_value("Multi-homing Summary", {
            "Ethernet Segments": result.total_es_count,
            "PE Switches": result.total_pe_count,
            "Redundancy Mode": result.redundancy_mode,
            "LACP System MAC": result.lacp_system_mac,
        })
        console.print()

        # ES Details table
        es_rows = []
        for es in result.ethernet_segments:
            es_rows.append([
                es.name,
                es.esi_config.esi,
                es.esi_config.esi_type,
                es.mode,
                es.df_election,
            ])

        output_table(
            title="Ethernet Segments",
            columns=["Name", "ESI", "Type", "Mode", "DF Algorithm"],
            rows=es_rows,
        )
        console.print()

        # Peer details
        if result.ethernet_segments:
            peer_rows = []
            for es in result.ethernet_segments:
                for peer in es.peers:
                    peer_rows.append([
                        es.name,
                        peer.name,
                        peer.loopback_ip,
                        peer.interface,
                        peer.lacp_config.system_id,
                    ])

            output_table(
                title="PE Peer Configurations",
                columns=["ES", "PE Name", "Loopback", "Interface", "LACP System ID"],
                rows=peer_rows,
            )

        # Vendor configs
        if result.vendor_configs:
            for vendor_name, config in result.vendor_configs.items():
                console.print()
                output_config(vendor_name.upper(), config)

    if save:
        if output == OutputFormat.JSON:
            import json
            content = json.dumps(result.__dict__, indent=2, default=str)
        elif output == OutputFormat.YAML:
            content = yaml.dump(result.__dict__, default_flow_style=False)
        else:
            content = f"Multi-homing: {result.total_es_count} ES, {result.total_pe_count} PEs"
        _save_output(content, save)


# =============================================================================
# Presets Command
# =============================================================================

@app.command()
def presets() -> None:
    """List available presets with their configurations."""
    console.print("[bold]Built-in Presets:[/bold]\n")

    for name, preset in BUILTIN_PRESETS.items():
        console.print(f"[bold cyan]{name}[/bold cyan]")
        console.print(f"  {preset.description}")
        if preset.fabric:
            console.print(f"  [dim]Fabric:[/dim] {preset.fabric}")
        if preset.ebgp:
            console.print(f"  [dim]eBGP:[/dim] {preset.ebgp}")
        if preset.vni:
            console.print(f"  [dim]VNI:[/dim] {preset.vni}")
        if preset.evpn:
            console.print(f"  [dim]EVPN:[/dim] {preset.evpn}")
        console.print()

    if _config.presets:
        console.print("[bold]User Presets (from config file):[/bold]\n")
        for name, preset in _config.presets.items():
            console.print(f"[bold cyan]{name}[/bold cyan]")
            console.print(f"  {preset.description}")
            console.print()

    console.print("[dim]Use --preset <name> with any command to apply preset defaults[/dim]")


if __name__ == "__main__":
    app()
