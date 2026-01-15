"""Fabric Parameters Calculator for VXLAN/EVPN networks."""

from dataclasses import dataclass, field
from enum import Enum
from ipaddress import IPv4Network

# Maximum allowed values to prevent resource exhaustion
MAX_VTEP_COUNT = 10000
MAX_SPINE_COUNT = 1000
MAX_VNI_COUNT = 16777215  # Maximum VNI value (2^24 - 1)
MAX_HOSTS_PER_VTEP = 100000


class ReplicationMode(str, Enum):
    """BUM traffic replication mode."""
    INGRESS = "ingress"      # Head-end replication (unicast)
    MULTICAST = "multicast"  # Multicast-based replication


@dataclass
class IPAllocation:
    """IP allocation for a component."""
    name: str
    network: str
    addresses: list[str]


@dataclass
class IPOverlapWarning:
    """Warning about IP network overlap."""
    network1_name: str
    network1: str
    network2_name: str
    network2: str
    message: str


@dataclass
class CapacityWarning:
    """Warning about insufficient capacity."""
    resource: str
    required: int
    available: int
    message: str


@dataclass
class FabricEstimates:
    """Estimated resource requirements."""
    total_mac_entries: int
    mac_entries_per_vtep: int
    evpn_type2_routes: int
    evpn_type3_routes: int
    evpn_type5_routes: int | None
    bgp_sessions_per_leaf: int
    bgp_sessions_total: int
    bum_replication_factor: int


@dataclass
class FabricResult:
    """Fabric parameters calculation result."""
    vtep_count: int
    spine_count: int
    vni_count: int
    hosts_per_vtep: int
    replication_mode: str
    p2p_links_total: int
    loopback_allocation: IPAllocation
    vtep_loopback_allocation: IPAllocation
    p2p_allocation: IPAllocation
    estimates: FabricEstimates
    warnings: list[IPOverlapWarning | CapacityWarning] = field(default_factory=list)


def _generate_addresses(network: IPv4Network, count: int, skip_network: bool = True) -> list[str]:
    """Generate a list of host addresses from a network."""
    hosts = list(network.hosts())
    if skip_network:
        return [str(hosts[i]) for i in range(min(count, len(hosts)))]
    return [str(network.network_address + i) for i in range(min(count, network.num_addresses))]


def _check_network_overlap(
    net1: IPv4Network,
    net1_name: str,
    net2: IPv4Network,
    net2_name: str,
) -> IPOverlapWarning | None:
    """Check if two networks overlap and return a warning if they do."""
    if net1.overlaps(net2):
        return IPOverlapWarning(
            network1_name=net1_name,
            network1=str(net1),
            network2_name=net2_name,
            network2=str(net2),
            message=f"{net1_name} ({net1}) overlaps with {net2_name} ({net2})",
        )
    return None


def _check_network_capacity(
    network: IPv4Network,
    network_name: str,
    required: int,
    resource_type: str = "addresses",
) -> CapacityWarning | None:
    """Check if a network has enough capacity and return a warning if not."""
    available = network.num_addresses - 2  # Subtract network and broadcast
    if available < required:
        return CapacityWarning(
            resource=f"{network_name} {resource_type}",
            required=required,
            available=available,
            message=f"{network_name} ({network}) has {available} usable addresses, but {required} required",
        )
    return None


def validate_fabric_networks(
    loopback_network: str,
    vtep_loopback_network: str,
    p2p_network: str,
    vtep_count: int,
    spine_count: int,
) -> list[IPOverlapWarning | CapacityWarning]:
    """
    Validate fabric networks for overlaps and capacity.

    Args:
        loopback_network: Network for router loopbacks
        vtep_loopback_network: Network for VTEP loopbacks
        p2p_network: Network for P2P links
        vtep_count: Number of VTEP switches
        spine_count: Number of spine switches

    Returns:
        List of warnings (empty if no issues found)
    """
    warnings: list[IPOverlapWarning | CapacityWarning] = []

    loopback_net = IPv4Network(loopback_network)
    vtep_loopback_net = IPv4Network(vtep_loopback_network)
    p2p_net = IPv4Network(p2p_network)

    # Check for overlaps
    networks = [
        (loopback_net, "Loopback network"),
        (vtep_loopback_net, "VTEP loopback network"),
        (p2p_net, "P2P network"),
    ]

    for i, (net1, name1) in enumerate(networks):
        for net2, name2 in networks[i + 1:]:
            warning = _check_network_overlap(net1, name1, net2, name2)
            if warning:
                warnings.append(warning)

    # Check capacity
    total_switches = vtep_count + spine_count
    p2p_links = vtep_count * spine_count

    capacity_checks = [
        (loopback_net, "Loopback network", total_switches),
        (vtep_loopback_net, "VTEP loopback network", vtep_count),
    ]

    for net, name, required in capacity_checks:
        capacity_warning = _check_network_capacity(net, name, required)
        if capacity_warning:
            warnings.append(capacity_warning)

    # P2P network capacity (needs subnets, not just addresses)
    # Handle edge case where prefixlen >= 31 (no room for /31 subnets)
    if p2p_net.prefixlen >= 31:
        p2p_subnets_available = 0
        warnings.append(CapacityWarning(
            resource="P2P /31 subnets",
            required=p2p_links,
            available=0,
            message=f"P2P network ({p2p_net}) prefix length is too large (/{p2p_net.prefixlen}) to create /31 subnets",
        ))
    else:
        p2p_subnets_available = 2 ** (31 - p2p_net.prefixlen)
        if p2p_subnets_available < p2p_links:
            warnings.append(CapacityWarning(
                resource="P2P /31 subnets",
                required=p2p_links,
                available=p2p_subnets_available,
                message=f"P2P network ({p2p_net}) can provide {p2p_subnets_available} /31 subnets, but {p2p_links} required",
            ))

    return warnings


def calculate_fabric_params(
    vtep_count: int = 4,
    spine_count: int = 2,
    vni_count: int = 100,
    hosts_per_vtep: int = 50,
    replication_mode: ReplicationMode = ReplicationMode.INGRESS,
    loopback_network: str = "10.0.0.0/24",
    vtep_loopback_network: str = "10.0.1.0/24",
    p2p_network: str = "10.0.100.0/22",
) -> FabricResult:
    """
    Calculate fabric parameters for a VXLAN/EVPN deployment.

    This calculates:
    - Number of P2P links (leaf-spine interconnects)
    - IP addressing plan (loopbacks, VTEP loopbacks, P2P links)
    - Resource estimates (MAC entries, EVPN routes, BGP sessions)

    Topology assumed:
    - Full mesh between leaf (VTEP) and spine switches
    - Each leaf has connections to all spines
    - eBGP underlay with iBGP EVPN overlay (or eBGP for both)

    Args:
        vtep_count: Number of VTEP (leaf) switches (must be > 0)
        spine_count: Number of spine switches (must be > 0)
        vni_count: Total number of VNIs in the fabric (must be > 0)
        hosts_per_vtep: Average number of hosts per VTEP (must be >= 0)
        replication_mode: BUM traffic replication mode
        loopback_network: Network for router loopbacks
        vtep_loopback_network: Network for VTEP (NVE) loopbacks
        p2p_network: Network for P2P links

    Returns:
        FabricResult with all calculations

    Raises:
        ValueError: If input parameters are invalid
    """
    # Validate input parameters with both lower and upper bounds
    if vtep_count <= 0:
        raise ValueError(f"vtep_count must be positive, got {vtep_count}")
    if vtep_count > MAX_VTEP_COUNT:
        raise ValueError(f"vtep_count must be <= {MAX_VTEP_COUNT}, got {vtep_count}")
    if spine_count <= 0:
        raise ValueError(f"spine_count must be positive, got {spine_count}")
    if spine_count > MAX_SPINE_COUNT:
        raise ValueError(f"spine_count must be <= {MAX_SPINE_COUNT}, got {spine_count}")
    if vni_count <= 0:
        raise ValueError(f"vni_count must be positive, got {vni_count}")
    if vni_count > MAX_VNI_COUNT:
        raise ValueError(f"vni_count must be <= {MAX_VNI_COUNT}, got {vni_count}")
    if hosts_per_vtep < 0:
        raise ValueError(f"hosts_per_vtep must be non-negative, got {hosts_per_vtep}")
    if hosts_per_vtep > MAX_HOSTS_PER_VTEP:
        raise ValueError(f"hosts_per_vtep must be <= {MAX_HOSTS_PER_VTEP}, got {hosts_per_vtep}")

    # Validate networks for overlaps and capacity
    warnings = validate_fabric_networks(
        loopback_network=loopback_network,
        vtep_loopback_network=vtep_loopback_network,
        p2p_network=p2p_network,
        vtep_count=vtep_count,
        spine_count=spine_count,
    )

    # Calculate P2P links
    # In a leaf-spine topology, each leaf connects to each spine
    p2p_links_total = vtep_count * spine_count

    # Parse networks
    loopback_net = IPv4Network(loopback_network)
    vtep_loopback_net = IPv4Network(vtep_loopback_network)
    p2p_net = IPv4Network(p2p_network)

    # Generate loopback addresses for all switches (leafs + spines)
    total_switches = vtep_count + spine_count
    loopback_addrs = _generate_addresses(loopback_net, total_switches)

    # Separate into leaf and spine loopbacks
    leaf_loopbacks = loopback_addrs[:vtep_count]
    spine_loopbacks = loopback_addrs[vtep_count:vtep_count + spine_count]

    loopback_allocation = IPAllocation(
        name="Router Loopbacks",
        network=loopback_network,
        addresses=[f"Leaf-{i+1}: {addr}" for i, addr in enumerate(leaf_loopbacks)] +
                  [f"Spine-{i+1}: {addr}" for i, addr in enumerate(spine_loopbacks)],
    )

    # Generate VTEP loopback addresses (for NVE interface)
    vtep_addrs = _generate_addresses(vtep_loopback_net, vtep_count)
    vtep_loopback_allocation = IPAllocation(
        name="VTEP (NVE) Loopbacks",
        network=vtep_loopback_network,
        addresses=[f"VTEP-{i+1}: {addr}" for i, addr in enumerate(vtep_addrs)],
    )

    # Generate P2P link addresses
    # Each P2P link needs a /31 or /30
    p2p_addresses = []
    p2p_subnets = list(p2p_net.subnets(new_prefix=31))

    link_idx = 0
    for leaf_idx in range(vtep_count):
        for spine_idx in range(spine_count):
            if link_idx < len(p2p_subnets):
                subnet = p2p_subnets[link_idx]
                hosts = list(subnet.hosts())
                if len(hosts) >= 2:
                    p2p_addresses.append(
                        f"Leaf-{leaf_idx+1} <-> Spine-{spine_idx+1}: {hosts[0]}/31 - {hosts[1]}/31"
                    )
            link_idx += 1

    p2p_allocation = IPAllocation(
        name="P2P Links",
        network=p2p_network,
        addresses=p2p_addresses[:20] + (["..."] if len(p2p_addresses) > 20 else []),
    )

    # Calculate estimates
    total_hosts = vtep_count * hosts_per_vtep
    total_mac_entries = total_hosts  # Assuming 1 MAC per host

    # EVPN Type-2 routes: MAC/IP advertisements
    # Each MAC learned on one VTEP is advertised to all other VTEPs
    evpn_type2_routes = total_mac_entries * (vtep_count - 1)

    # EVPN Type-3 routes: Inclusive Multicast Ethernet Tag routes
    # One per VNI per VTEP
    evpn_type3_routes = vni_count * vtep_count

    # BGP sessions per leaf: 1 to each spine (underlay) + 1 to each spine or RR (overlay)
    # Simplified: assuming each leaf peers with all spines for both
    bgp_sessions_per_leaf = spine_count * 2  # underlay + overlay

    # Total BGP sessions in the fabric
    bgp_sessions_total = vtep_count * bgp_sessions_per_leaf

    # BUM replication factor
    if replication_mode == ReplicationMode.INGRESS:
        # Head-end replication: each BUM frame is replicated to all remote VTEPs
        bum_replication_factor = vtep_count - 1
    else:
        # Multicast: one copy per VNI, network handles replication
        bum_replication_factor = 1

    estimates = FabricEstimates(
        total_mac_entries=total_mac_entries,
        mac_entries_per_vtep=total_mac_entries,  # Each VTEP learns all MACs (local + remote)
        evpn_type2_routes=evpn_type2_routes,
        evpn_type3_routes=evpn_type3_routes,
        evpn_type5_routes=None,  # Type-5 depends on L3VNI config
        bgp_sessions_per_leaf=bgp_sessions_per_leaf,
        bgp_sessions_total=bgp_sessions_total,
        bum_replication_factor=bum_replication_factor,
    )

    return FabricResult(
        vtep_count=vtep_count,
        spine_count=spine_count,
        vni_count=vni_count,
        hosts_per_vtep=hosts_per_vtep,
        replication_mode=replication_mode.value,
        p2p_links_total=p2p_links_total,
        loopback_allocation=loopback_allocation,
        vtep_loopback_allocation=vtep_loopback_allocation,
        p2p_allocation=p2p_allocation,
        estimates=estimates,
        warnings=warnings,
    )
