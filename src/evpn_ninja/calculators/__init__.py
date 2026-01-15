"""VXLAN/EVPN calculators."""

from .mtu import calculate_mtu, MTUResult, UnderlayType
from .vni import calculate_vni_allocation, VNIAllocationResult, VNIScheme
from .fabric import (
    calculate_fabric_params,
    validate_fabric_networks,
    FabricResult,
    ReplicationMode,
    IPOverlapWarning,
    CapacityWarning,
)
from .evpn import calculate_evpn_params, EVPNResult, Vendor
from .ebgp import calculate_ebgp_underlay, EBGPUnderlayResult, ASNScheme
from .multicast import calculate_multicast_groups, MulticastResult, MulticastScheme
from .route_reflector import (
    calculate_route_reflector,
    RouteReflectorResult,
    RRPlacement,
    RRRedundancy,
)
from .bandwidth import calculate_bandwidth, BandwidthResult, LinkSpeed
from .topology import generate_topology, TopologyResult
from .multihoming import (
    calculate_multihoming,
    generate_esi_type0,
    generate_esi_type1,
    generate_esi_type3,
    MultiHomingResult,
    MultiHomingMode,
    ESIType,
    EthernetSegment,
    ESIConfig,
)

__all__ = [
    # MTU
    "calculate_mtu",
    "MTUResult",
    "UnderlayType",
    # VNI
    "calculate_vni_allocation",
    "VNIAllocationResult",
    "VNIScheme",
    # Fabric
    "calculate_fabric_params",
    "validate_fabric_networks",
    "FabricResult",
    "ReplicationMode",
    "IPOverlapWarning",
    "CapacityWarning",
    # EVPN
    "calculate_evpn_params",
    "EVPNResult",
    "Vendor",
    # eBGP
    "calculate_ebgp_underlay",
    "EBGPUnderlayResult",
    "ASNScheme",
    # Multicast
    "calculate_multicast_groups",
    "MulticastResult",
    "MulticastScheme",
    # Route Reflector
    "calculate_route_reflector",
    "RouteReflectorResult",
    "RRPlacement",
    "RRRedundancy",
    # Bandwidth
    "calculate_bandwidth",
    "BandwidthResult",
    "LinkSpeed",
    # Topology
    "generate_topology",
    "TopologyResult",
    # Multi-homing
    "calculate_multihoming",
    "generate_esi_type0",
    "generate_esi_type1",
    "generate_esi_type3",
    "MultiHomingResult",
    "MultiHomingMode",
    "ESIType",
    "EthernetSegment",
    "ESIConfig",
]
