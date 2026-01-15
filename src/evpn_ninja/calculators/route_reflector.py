"""BGP Route Reflector Calculator for EVPN overlay.

Calculates optimal Route Reflector placement, cluster IDs,
and BGP session configuration for EVPN fabrics.
"""

from dataclasses import dataclass
from enum import Enum
from ipaddress import IPv4Network


class RRPlacement(str, Enum):
    """Route Reflector placement strategy."""

    SPINE = "spine"  # RR on spine switches (recommended for small fabrics)
    DEDICATED = "dedicated"  # Dedicated RR nodes (recommended for large fabrics)
    BORDER = "border"  # RR on border/exit switches


class RRRedundancy(str, Enum):
    """Route Reflector redundancy model."""

    SINGLE = "single"  # Single RR (no redundancy)
    PAIR = "pair"  # RR pair (active-active)
    CLUSTER = "cluster"  # Multiple RR clusters


@dataclass
class RRNode:
    """Route Reflector node."""

    name: str
    loopback_ip: str
    cluster_id: str
    role: str  # primary, secondary, or cluster member


@dataclass
class RRCluster:
    """Route Reflector cluster."""

    cluster_id: str
    members: list[RRNode]
    client_count: int


@dataclass
class BGPPeerGroup:
    """BGP peer group configuration."""

    name: str
    description: str
    remote_as: int | str  # Can be 'internal' for iBGP
    update_source: str
    address_family: str
    route_reflector_client: bool
    next_hop_self: bool


@dataclass
class RouteReflectorResult:
    """Route Reflector calculation result."""

    placement: str
    redundancy: str
    bgp_as: int
    total_rr_nodes: int
    total_clients: int
    clusters: list[RRCluster]
    peer_groups: list[BGPPeerGroup]
    design_notes: list[str]
    config_template: str


def _calculate_optimal_cluster_count(client_count: int) -> int:
    """
    Calculate optimal number of RR clusters based on client count.

    Guidelines:
    - Up to 50 clients: 1 cluster (2 RRs)
    - 50-200 clients: 2 clusters (4 RRs)
    - 200+ clients: 1 cluster per 100 clients
    """
    if client_count <= 50:
        return 1
    elif client_count <= 200:
        return 2
    else:
        return (client_count + 99) // 100


def _generate_cluster_id(index: int, base_ip: str = "10.255.255.") -> str:
    """Generate cluster ID from index."""
    return f"{base_ip}{index + 1}"


def _generate_rr_config(
    bgp_as: int,
    rr_nodes: list[RRNode],
    clients_per_rr: int,
) -> str:
    """Generate sample RR configuration."""
    config = f"""! BGP Route Reflector Configuration
! AS: {bgp_as}
! Route Reflectors: {len(rr_nodes)}
! Clients per RR: ~{clients_per_rr}

router bgp {bgp_as}
 bgp router-id <loopback-ip>
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 !
 ! Peer group for EVPN clients
 neighbor EVPN-CLIENTS peer-group
 neighbor EVPN-CLIENTS remote-as {bgp_as}
 neighbor EVPN-CLIENTS update-source Loopback0
 neighbor EVPN-CLIENTS route-reflector-client
 neighbor EVPN-CLIENTS send-community extended
 !
 ! Peer group for RR-to-RR peering
 neighbor RR-PEERS peer-group
 neighbor RR-PEERS remote-as {bgp_as}
 neighbor RR-PEERS update-source Loopback0
 neighbor RR-PEERS send-community extended
 !"""

    for rr in rr_nodes:
        config += f"""
 ! RR peer: {rr.name}
 neighbor {rr.loopback_ip} peer-group RR-PEERS
 neighbor {rr.loopback_ip} description {rr.name}"""

    config += """
 !
 address-family l2vpn evpn
  neighbor EVPN-CLIENTS activate
  neighbor EVPN-CLIENTS route-reflector-client
  neighbor RR-PEERS activate
 exit-address-family
!"""

    return config


def calculate_route_reflector(
    client_count: int = 10,
    bgp_as: int = 65000,
    placement: RRPlacement = RRPlacement.SPINE,
    redundancy: RRRedundancy = RRRedundancy.PAIR,
    rr_loopback_network: str = "10.255.0.0/24",
    custom_cluster_count: int | None = None,
) -> RouteReflectorResult:
    """
    Calculate BGP Route Reflector configuration for EVPN overlay.

    In EVPN fabrics, iBGP is typically used for the overlay with
    Route Reflectors to avoid full mesh between all VTEPs.

    Design considerations:
    - Small fabrics (<20 leaves): RR on spines is acceptable
    - Large fabrics: Dedicated RR nodes recommended
    - Always use at least 2 RRs for redundancy
    - Use cluster-id to prevent loops when multiple RRs
    - Consider RR placement for optimal path selection

    Args:
        client_count: Number of BGP clients (VTEPs/leaves)
        bgp_as: BGP AS number for iBGP
        placement: Where to place Route Reflectors
        redundancy: Redundancy model
        rr_loopback_network: Network for RR loopback addresses
        custom_cluster_count: Override automatic cluster calculation

    Returns:
        RouteReflectorResult with RR configuration
    """
    design_notes: list[str] = []

    # Calculate number of clusters
    if custom_cluster_count:
        cluster_count = custom_cluster_count
    else:
        cluster_count = _calculate_optimal_cluster_count(client_count)

    # Calculate RRs per cluster based on redundancy
    if redundancy == RRRedundancy.SINGLE:
        rrs_per_cluster = 1
        design_notes.append("WARNING: Single RR has no redundancy - not recommended for production")
    elif redundancy == RRRedundancy.PAIR:
        rrs_per_cluster = 2
        design_notes.append("RR pair provides active-active redundancy")
    else:  # CLUSTER
        rrs_per_cluster = 3
        design_notes.append("3-node cluster provides N+2 redundancy")

    total_rr_nodes = cluster_count * rrs_per_cluster

    # Generate RR loopback addresses
    rr_network = IPv4Network(rr_loopback_network)
    rr_hosts = list(rr_network.hosts())

    # Create clusters
    clusters: list[RRCluster] = []
    all_rr_nodes: list[RRNode] = []
    clients_per_cluster = (client_count + cluster_count - 1) // cluster_count

    rr_index = 0
    for cluster_idx in range(cluster_count):
        cluster_id = _generate_cluster_id(cluster_idx)
        members: list[RRNode] = []

        for member_idx in range(rrs_per_cluster):
            if rr_index < len(rr_hosts):
                rr_ip = str(rr_hosts[rr_index])
            else:
                rr_ip = f"10.255.{rr_index // 256}.{rr_index % 256}"

            role = "primary" if member_idx == 0 else "secondary" if member_idx == 1 else "member"

            if placement == RRPlacement.SPINE:
                name = f"spine-rr-{rr_index + 1}"
            elif placement == RRPlacement.DEDICATED:
                name = f"rr-{rr_index + 1}"
            else:
                name = f"border-rr-{rr_index + 1}"

            rr_node = RRNode(
                name=name,
                loopback_ip=rr_ip,
                cluster_id=cluster_id,
                role=role,
            )
            members.append(rr_node)
            all_rr_nodes.append(rr_node)
            rr_index += 1

        clusters.append(RRCluster(
            cluster_id=cluster_id,
            members=members,
            client_count=clients_per_cluster,
        ))

    # Create peer groups
    peer_groups = [
        BGPPeerGroup(
            name="EVPN-CLIENTS",
            description="EVPN Route Reflector clients (VTEPs)",
            remote_as=bgp_as,
            update_source="Loopback0",
            address_family="l2vpn evpn",
            route_reflector_client=True,
            next_hop_self=False,  # Keep original next-hop for EVPN
        ),
        BGPPeerGroup(
            name="RR-PEERS",
            description="Route Reflector to Route Reflector peering",
            remote_as=bgp_as,
            update_source="Loopback0",
            address_family="l2vpn evpn",
            route_reflector_client=False,
            next_hop_self=False,
        ),
    ]

    # Add design notes
    design_notes.extend([
        f"Placement: {placement.value} - {'Recommended for small fabrics' if placement == RRPlacement.SPINE else 'Recommended for large fabrics'}",
        f"Total BGP sessions: {client_count * rrs_per_cluster} (clients) + {total_rr_nodes * (total_rr_nodes - 1) // 2} (RR mesh)",
        "All RRs in a cluster share the same cluster-id to prevent routing loops",
        "EVPN next-hop should NOT be modified by RR (no next-hop-self)",
        "Extended communities must be preserved for RT/RD",
    ])

    if client_count > 100 and placement == RRPlacement.SPINE:
        design_notes.append("RECOMMENDATION: Consider dedicated RR nodes for better scalability")

    # Generate config template
    config_template = _generate_rr_config(
        bgp_as=bgp_as,
        rr_nodes=all_rr_nodes,
        clients_per_rr=clients_per_cluster,
    )

    return RouteReflectorResult(
        placement=placement.value,
        redundancy=redundancy.value,
        bgp_as=bgp_as,
        total_rr_nodes=total_rr_nodes,
        total_clients=client_count,
        clusters=clusters,
        peer_groups=peer_groups,
        design_notes=design_notes,
        config_template=config_template,
    )
