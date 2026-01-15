"""VXLAN/EVPN calculators."""

from .bandwidth import BandwidthResult, LinkSpeed, calculate_bandwidth
from .ebgp import ASNScheme, EBGPUnderlayResult, calculate_ebgp_underlay
from .evpn import EVPNResult, Vendor, calculate_evpn_params
from .fabric import (
    CapacityWarning,
    FabricResult,
    IPOverlapWarning,
    ReplicationMode,
    calculate_fabric_params,
    validate_fabric_networks,
)
from .mtu import MTUResult, UnderlayType, calculate_mtu
from .multicast import MulticastResult, MulticastScheme, calculate_multicast_groups
from .multihoming import (
    ESIConfig,
    ESIType,
    EthernetSegment,
    MultiHomingMode,
    MultiHomingResult,
    calculate_multihoming,
    generate_esi_type0,
    generate_esi_type1,
    generate_esi_type3,
)
from .route_reflector import (
    RouteReflectorResult,
    RRPlacement,
    RRRedundancy,
    calculate_route_reflector,
)
from .topology import TopologyResult, generate_topology
from .vni import VNIAllocationResult, VNIScheme, calculate_vni_allocation

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
