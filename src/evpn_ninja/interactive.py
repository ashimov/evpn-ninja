"""Interactive mode for VXLAN/EVPN Calculator."""

from ipaddress import IPv4Address, IPv4Network

import questionary

from evpn_ninja.calculators.evpn import Vendor, calculate_evpn_params
from evpn_ninja.calculators.fabric import ReplicationMode, calculate_fabric_params
from evpn_ninja.calculators.mtu import UnderlayType, calculate_mtu
from evpn_ninja.calculators.vni import VNIScheme, calculate_vni_allocation
from evpn_ninja.output import (
    OutputFormat,
    console,
    output_config,
    output_json,
    output_key_value,
    output_table,
    output_yaml,
)


def _is_valid_ipv4(value: str) -> bool:
    """Check if value is a valid IPv4 address."""
    try:
        IPv4Address(value)
        return True
    except (ValueError, TypeError):
        return False


def _is_valid_multicast(value: str) -> bool:
    """Check if value is a valid IPv4 multicast address."""
    try:
        addr = IPv4Address(value)
        return addr.is_multicast
    except (ValueError, TypeError):
        return False


def _is_valid_cidr(value: str) -> bool:
    """Check if value is a valid IPv4 CIDR network."""
    try:
        IPv4Network(value, strict=False)
        return True
    except (ValueError, TypeError):
        return False


def _ask_output_format() -> OutputFormat | None:
    """Ask user for output format. Returns None if cancelled."""
    choice = questionary.select(
        "Output format:",
        choices=["Table (formatted)", "JSON", "YAML"],
        default="Table (formatted)",
    ).ask()

    if choice is None:
        return None
    if choice == "JSON":
        return OutputFormat.JSON
    elif choice == "YAML":
        return OutputFormat.YAML
    return OutputFormat.TABLE


def _interactive_mtu() -> None:
    """Interactive MTU calculator."""
    console.print("\n[bold cyan]MTU Calculator[/bold cyan]\n")

    payload = questionary.text(
        "Inner payload size (bytes):",
        default="1500",
        validate=lambda x: x.isdigit() and int(x) > 0,
    ).ask()
    if payload is None:
        return

    underlay = questionary.select(
        "Underlay network type:",
        choices=["IPv4", "IPv6"],
        default="IPv4",
    ).ask()
    if underlay is None:
        return

    outer_vlans = questionary.text(
        "Outer VLAN tags (0-2):",
        default="0",
        validate=lambda x: x.isdigit() and 0 <= int(x) <= 2,
    ).ask()
    if outer_vlans is None:
        return

    inner_vlans = questionary.text(
        "Inner VLAN tags (0-2):",
        default="0",
        validate=lambda x: x.isdigit() and 0 <= int(x) <= 2,
    ).ask()
    if inner_vlans is None:
        return

    output_format = _ask_output_format()
    if output_format is None:
        return

    result = calculate_mtu(
        payload_size=int(payload),
        underlay_type=UnderlayType.IPV4 if underlay == "IPv4" else UnderlayType.IPV6,
        outer_vlan_tags=int(outer_vlans),
        inner_vlan_tags=int(inner_vlans),
    )

    console.print()
    if output_format == OutputFormat.JSON:
        output_json(result)
    elif output_format == OutputFormat.YAML:
        output_yaml(result)
    else:
        output_table(
            title="VXLAN MTU Breakdown",
            columns=["Layer", "Size (bytes)", "Description"],
            rows=[[layer.name, str(layer.size), layer.description] for layer in result.layers],
        )
        console.print()
        output_key_value(
            "Summary",
            {
                "Total Overhead": f"{result.total_overhead} bytes",
                "Total Frame Size": f"{result.total_frame_size} bytes",
                "Required MTU": f"{result.required_mtu} bytes",
                "Recommended MTU": f"{result.recommended_mtu} bytes",
            },
        )


def _interactive_vni() -> None:
    """Interactive VNI allocation calculator."""
    console.print("\n[bold cyan]VNI Allocation Calculator[/bold cyan]\n")

    scheme = questionary.select(
        "Allocation scheme:",
        choices=[
            "VLAN-based (VNI = base + vlan_id)",
            "Tenant-based (VNI = tenant_id * 10000 + vlan_id)",
            "Sequential (VNI = base + index)",
            "Custom (VNI = base + vlan_id * multiplier)",
        ],
        default="VLAN-based (VNI = base + vlan_id)",
    ).ask()
    if scheme is None:
        return

    scheme_map = {
        "VLAN-based (VNI = base + vlan_id)": VNIScheme.VLAN_BASED,
        "Tenant-based (VNI = tenant_id * 10000 + vlan_id)": VNIScheme.TENANT_BASED,
        "Sequential (VNI = base + index)": VNIScheme.SEQUENTIAL,
        "Custom (VNI = base + vlan_id * multiplier)": VNIScheme.CUSTOM,
    }

    base_vni = questionary.text(
        "Base VNI:",
        default="10000",
        validate=lambda x: x.isdigit() and 1 <= int(x) <= 16777215,
    ).ask()
    if base_vni is None:
        return

    tenant_id = "1"
    if scheme_map[scheme] == VNIScheme.TENANT_BASED:
        tenant_id = questionary.text(
            "Tenant ID:",
            default="1",
            validate=lambda x: x.isdigit() and int(x) > 0,
        ).ask()
        if tenant_id is None:
            return

    start_vlan = questionary.text(
        "Starting VLAN ID:",
        default="10",
        validate=lambda x: x.isdigit() and 1 <= int(x) <= 4094,
    ).ask()
    if start_vlan is None:
        return

    count = questionary.text(
        "Number of VNIs:",
        default="10",
        validate=lambda x: x.isdigit() and int(x) > 0,
    ).ask()
    if count is None:
        return

    mcast_base = questionary.text(
        "Multicast base address:",
        default="239.1.1.0",
        validate=lambda x: (
            _is_valid_multicast(x)
            or "Must be a valid multicast address (224.0.0.0-239.255.255.255)"
        ),
    ).ask()
    if mcast_base is None:
        return

    output_format = _ask_output_format()
    if output_format is None:
        return

    result = calculate_vni_allocation(
        scheme=scheme_map[scheme],
        base_vni=int(base_vni),
        tenant_id=int(tenant_id),
        start_vlan=int(start_vlan),
        count=int(count),
        multicast_base=mcast_base,
    )

    console.print()
    if output_format == OutputFormat.JSON:
        output_json(result)
    elif output_format == OutputFormat.YAML:
        output_yaml(result)
    else:
        output_key_value(
            "VNI Allocation Parameters",
            {
                "Scheme": result.scheme,
                "Base VNI": result.base_vni,
                "Tenant ID": result.tenant_id or "N/A",
                "Start VLAN": result.start_vlan,
                "Count": result.count,
            },
        )
        console.print()
        output_table(
            title="VNI Allocation Table",
            columns=["VLAN ID", "VNI (Decimal)", "VNI (Hex)", "Multicast Group"],
            rows=[
                [str(e.vlan_id), str(e.vni_decimal), e.vni_hex, e.multicast_group]
                for e in result.entries
            ],
        )


def _interactive_fabric() -> None:
    """Interactive fabric parameters calculator."""
    console.print("\n[bold cyan]Fabric Parameters Calculator[/bold cyan]\n")

    vteps = questionary.text(
        "Number of VTEP (leaf) switches:",
        default="4",
        validate=lambda x: x.isdigit() and int(x) > 0,
    ).ask()
    if vteps is None:
        return

    spines = questionary.text(
        "Number of spine switches:",
        default="2",
        validate=lambda x: x.isdigit() and int(x) > 0,
    ).ask()
    if spines is None:
        return

    vnis = questionary.text(
        "Total number of VNIs:",
        default="100",
        validate=lambda x: x.isdigit() and int(x) > 0,
    ).ask()
    if vnis is None:
        return

    hosts = questionary.text(
        "Average hosts per VTEP:",
        default="50",
        validate=lambda x: x.isdigit() and int(x) > 0,
    ).ask()
    if hosts is None:
        return

    replication = questionary.select(
        "BUM replication mode:",
        choices=["Ingress (Head-end)", "Multicast"],
        default="Ingress (Head-end)",
    ).ask()
    if replication is None:
        return

    loopback_net = questionary.text(
        "Loopback network:",
        default="10.0.0.0/24",
        validate=lambda x: _is_valid_cidr(x) or "Invalid CIDR notation (e.g. 10.0.0.0/24)",
    ).ask()
    if loopback_net is None:
        return

    vtep_net = questionary.text(
        "VTEP loopback network:",
        default="10.0.1.0/24",
        validate=lambda x: _is_valid_cidr(x) or "Invalid CIDR notation (e.g. 10.0.1.0/24)",
    ).ask()
    if vtep_net is None:
        return

    p2p_net = questionary.text(
        "P2P links network:",
        default="10.0.100.0/22",
        validate=lambda x: _is_valid_cidr(x) or "Invalid CIDR notation (e.g. 10.0.100.0/22)",
    ).ask()
    if p2p_net is None:
        return

    output_format = _ask_output_format()
    if output_format is None:
        return

    result = calculate_fabric_params(
        vtep_count=int(vteps),
        spine_count=int(spines),
        vni_count=int(vnis),
        hosts_per_vtep=int(hosts),
        replication_mode=ReplicationMode.INGRESS
        if "Ingress" in replication
        else ReplicationMode.MULTICAST,
        loopback_network=loopback_net,
        vtep_loopback_network=vtep_net,
        p2p_network=p2p_net,
    )

    console.print()
    if output_format == OutputFormat.JSON:
        output_json(result)
    elif output_format == OutputFormat.YAML:
        output_yaml(result)
    else:
        output_key_value(
            "Fabric Topology",
            {
                "VTEP (Leaf) Count": result.vtep_count,
                "Spine Count": result.spine_count,
                "VNI Count": result.vni_count,
                "Hosts per VTEP": result.hosts_per_vtep,
                "Replication Mode": result.replication_mode,
                "Total P2P Links": result.p2p_links_total,
            },
        )
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

        output_key_value(
            "Resource Estimates",
            {
                "Total MAC Entries": result.estimates.total_mac_entries,
                "EVPN Type-2 Routes": result.estimates.evpn_type2_routes,
                "EVPN Type-3 Routes": result.estimates.evpn_type3_routes,
                "BGP Sessions Total": result.estimates.bgp_sessions_total,
            },
        )


def _interactive_evpn() -> None:
    """Interactive EVPN parameters calculator."""
    console.print("\n[bold cyan]EVPN Parameters Calculator[/bold cyan]\n")

    bgp_as = questionary.text(
        "BGP AS number:",
        default="65000",
        validate=lambda x: x.isdigit() and int(x) > 0,
    ).ask()
    if bgp_as is None:
        return

    loopback = questionary.text(
        "VTEP loopback IP:",
        default="10.0.0.1",
        validate=lambda x: _is_valid_ipv4(x) or "Invalid IPv4 address",
    ).ask()
    if loopback is None:
        return

    l2_vni = questionary.text(
        "Layer 2 VNI:",
        default="10010",
        validate=lambda x: x.isdigit() and 1 <= int(x) <= 16777215,
    ).ask()
    if l2_vni is None:
        return

    vlan_id = questionary.text(
        "VLAN ID:",
        default="10",
        validate=lambda x: x.isdigit() and 1 <= int(x) <= 4094,
    ).ask()
    if vlan_id is None:
        return

    has_l3 = questionary.confirm(
        "Configure L3 VNI (VRF)?",
        default=False,
    ).ask()
    if has_l3 is None:
        return

    l3_vni = None
    vrf_name = None
    if has_l3:
        l3_vni_str = questionary.text(
            "Layer 3 VNI:",
            default="50000",
            validate=lambda x: x.isdigit() and 1 <= int(x) <= 16777215,
        ).ask()
        if l3_vni_str is None:
            return
        l3_vni = int(l3_vni_str)

        vrf_name = questionary.text(
            "VRF name:",
            default="TENANT-1",
        ).ask()
        if vrf_name is None:
            return

    vendors_choice = questionary.checkbox(
        "Generate configs for:",
        choices=[
            questionary.Choice("Arista EOS", checked=True),
            questionary.Choice("Cisco NX-OS", checked=True),
            questionary.Choice("Juniper Junos", checked=True),
        ],
    ).ask()
    if vendors_choice is None:
        return

    vendor_map = {
        "Arista EOS": Vendor.ARISTA,
        "Cisco NX-OS": Vendor.CISCO_NXOS,
        "Juniper Junos": Vendor.JUNIPER,
    }
    vendors = [vendor_map[v] for v in vendors_choice] if vendors_choice else None

    output_format = _ask_output_format()
    if output_format is None:
        return

    result = calculate_evpn_params(
        bgp_as=int(bgp_as),
        loopback_ip=loopback,
        l2_vni=int(l2_vni),
        vlan_id=int(vlan_id),
        l3_vni=l3_vni,
        vrf_name=vrf_name,
        vendors=vendors,
    )

    console.print()
    if output_format == OutputFormat.JSON:
        output_json(result)
    elif output_format == OutputFormat.YAML:
        output_yaml(result)
    else:
        output_key_value(
            "Input Parameters",
            {
                "BGP AS": result.bgp_as,
                "Loopback IP": result.loopback_ip,
                "L2 VNI": result.l2_vni,
                "VLAN ID": result.vlan_id,
                "L3 VNI": result.l3_vni or "N/A",
                "VRF Name": result.vrf_name or "N/A",
            },
        )
        console.print()

        output_key_value(
            "L2 EVPN Parameters",
            {
                "Route Distinguisher (RD)": result.l2_params.route_distinguisher,
                "Route Target Import": result.l2_params.route_target_import,
                "Route Target Export": result.l2_params.route_target_export,
                "EVI": result.l2_params.evi,
            },
        )

        if result.l3_params:
            console.print()
            output_key_value(
                "L3 EVPN Parameters",
                {
                    "Route Distinguisher (RD)": result.l3_params.route_distinguisher,
                    "Route Target Import": result.l3_params.route_target_import,
                    "Route Target Export": result.l3_params.route_target_export,
                    "EVI": result.l3_params.evi,
                },
            )

        console.print()
        for cfg in result.configs:
            output_config(f"{cfg.vendor.upper()} Configuration", cfg.config)
            console.print()


def run_interactive() -> None:
    """Run interactive mode."""
    console.print("\n[bold green]VXLAN/EVPN Calculator - Interactive Mode[/bold green]")
    console.print("Press Ctrl+C at any time to exit.\n")

    while True:
        try:
            choice = questionary.select(
                "Select calculator:",
                choices=[
                    "MTU Calculator",
                    "VNI Allocation",
                    "Fabric Parameters",
                    "EVPN Parameters",
                    "Exit",
                ],
            ).ask()

            if choice == "Exit" or choice is None:
                console.print("\n[bold yellow]Goodbye![/bold yellow]")
                break
            elif choice == "MTU Calculator":
                _interactive_mtu()
            elif choice == "VNI Allocation":
                _interactive_vni()
            elif choice == "Fabric Parameters":
                _interactive_fabric()
            elif choice == "EVPN Parameters":
                _interactive_evpn()

            console.print()
            again = questionary.confirm("Run another calculation?", default=True).ask()
            if again is None or not again:
                console.print("\n[bold yellow]Goodbye![/bold yellow]")
                break

        except KeyboardInterrupt:
            console.print("\n\n[bold yellow]Interrupted. Goodbye![/bold yellow]")
            break
