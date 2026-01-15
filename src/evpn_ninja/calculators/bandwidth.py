"""ECMP/LAG Bandwidth Calculator for datacenter fabrics.

Calculates effective bandwidth, oversubscription ratios,
and failure scenarios for leaf-spine topologies.
"""

from dataclasses import dataclass
from enum import Enum


class LinkSpeed(str, Enum):
    """Common link speeds."""

    GE_1 = "1g"
    GE_10 = "10g"
    GE_25 = "25g"
    GE_40 = "40g"
    GE_50 = "50g"
    GE_100 = "100g"
    GE_200 = "200g"
    GE_400 = "400g"

    @property
    def gbps(self) -> int:
        """Get speed in Gbps."""
        speed_map = {
            "1g": 1,
            "10g": 10,
            "25g": 25,
            "40g": 40,
            "50g": 50,
            "100g": 100,
            "200g": 200,
            "400g": 400,
        }
        return speed_map[self.value]


@dataclass
class LinkGroup:
    """A group of parallel links (LAG or ECMP)."""

    name: str
    link_count: int
    link_speed_gbps: int
    total_bandwidth_gbps: int
    effective_bandwidth_gbps: float  # After considering hashing efficiency


@dataclass
class OversubscriptionAnalysis:
    """Oversubscription analysis for a tier."""

    tier_name: str
    downlink_bandwidth_gbps: float
    uplink_bandwidth_gbps: float
    oversubscription_ratio: float
    is_non_blocking: bool


@dataclass
class FailureScenario:
    """Bandwidth analysis for a failure scenario."""

    scenario: str
    remaining_bandwidth_gbps: float
    bandwidth_reduction_percent: float
    still_operational: bool
    notes: str


@dataclass
class BandwidthResult:
    """Bandwidth calculation result."""

    # Topology
    spine_count: int
    leaf_count: int
    uplink_speed: str
    uplink_count_per_leaf: int
    downlink_speed: str
    downlink_count_per_leaf: int

    # Bandwidth summary
    leaf_uplink_bandwidth_gbps: float
    leaf_downlink_bandwidth_gbps: float
    spine_total_bandwidth_gbps: float
    fabric_bisection_bandwidth_gbps: float

    # Analysis
    leaf_oversubscription: OversubscriptionAnalysis
    ecmp_paths: int
    hash_efficiency: float

    # Failure scenarios
    failure_scenarios: list[FailureScenario]

    # Recommendations
    recommendations: list[str]


def _calculate_hash_efficiency(ecmp_paths: int) -> float:
    """
    Estimate ECMP hash efficiency based on number of paths.

    Real-world ECMP hashing is not perfectly balanced.
    Efficiency typically ranges from 70-95% depending on
    traffic patterns and hash algorithm.
    """
    if ecmp_paths == 1:
        return 1.0
    elif ecmp_paths == 2:
        return 0.95  # 2-way ECMP is usually well balanced
    elif ecmp_paths <= 4:
        return 0.90
    elif ecmp_paths <= 8:
        return 0.85
    else:
        return 0.80  # Large ECMP groups have more variance


def calculate_bandwidth(
    spine_count: int = 2,
    leaf_count: int = 4,
    uplink_speed: LinkSpeed = LinkSpeed.GE_100,
    uplink_count_per_leaf: int = 2,
    downlink_speed: LinkSpeed = LinkSpeed.GE_25,
    downlink_count_per_leaf: int = 48,
    host_utilization_percent: float = 50.0,
) -> BandwidthResult:
    """
    Calculate fabric bandwidth and oversubscription.

    This calculator helps design datacenter fabrics by analyzing:
    - Total bandwidth at each tier
    - Oversubscription ratios
    - ECMP path count and efficiency
    - Impact of link/switch failures

    Args:
        spine_count: Number of spine switches
        leaf_count: Number of leaf switches
        uplink_speed: Speed of leaf-to-spine uplinks
        uplink_count_per_leaf: Number of uplinks per leaf (usually = spine_count)
        downlink_speed: Speed of host-facing downlinks
        downlink_count_per_leaf: Number of downlink ports per leaf
        host_utilization_percent: Expected average host port utilization

    Returns:
        BandwidthResult with bandwidth analysis
    """
    recommendations: list[str] = []

    # Calculate leaf bandwidth
    leaf_uplink_bw = uplink_count_per_leaf * uplink_speed.gbps
    leaf_downlink_bw = downlink_count_per_leaf * downlink_speed.gbps

    # Calculate spine bandwidth
    # Each spine connects to all leaves
    spine_total_bw = leaf_count * uplink_speed.gbps

    # Bisection bandwidth (total bandwidth available for east-west traffic)
    # This is the total uplink capacity from all leaves
    bisection_bw = leaf_count * leaf_uplink_bw

    # Oversubscription analysis
    if leaf_uplink_bw >= leaf_downlink_bw:
        oversub_ratio = 1.0
        is_non_blocking = True
    else:
        oversub_ratio = leaf_downlink_bw / leaf_uplink_bw
        is_non_blocking = False

    leaf_oversub = OversubscriptionAnalysis(
        tier_name="Leaf",
        downlink_bandwidth_gbps=leaf_downlink_bw,
        uplink_bandwidth_gbps=leaf_uplink_bw,
        oversubscription_ratio=oversub_ratio,
        is_non_blocking=is_non_blocking,
    )

    # ECMP analysis
    ecmp_paths = min(uplink_count_per_leaf, spine_count)
    hash_efficiency = _calculate_hash_efficiency(ecmp_paths)

    # Effective bandwidth considering hash efficiency
    effective_uplink_bw = leaf_uplink_bw * hash_efficiency

    # Failure scenarios
    failure_scenarios: list[FailureScenario] = []

    # Scenario 1: Single spine failure
    if spine_count > 1:
        remaining_bw = leaf_uplink_bw * (spine_count - 1) / spine_count
        reduction = (1 - (spine_count - 1) / spine_count) * 100
        failure_scenarios.append(FailureScenario(
            scenario="Single spine failure",
            remaining_bandwidth_gbps=remaining_bw,
            bandwidth_reduction_percent=reduction,
            still_operational=True,
            notes=f"Traffic redistributes to {spine_count - 1} remaining spines",
        ))

    # Scenario 2: Single uplink failure (per leaf)
    if uplink_count_per_leaf > 1:
        remaining_bw = leaf_uplink_bw * (uplink_count_per_leaf - 1) / uplink_count_per_leaf
        reduction = (1 / uplink_count_per_leaf) * 100
        failure_scenarios.append(FailureScenario(
            scenario="Single uplink failure (per leaf)",
            remaining_bandwidth_gbps=remaining_bw,
            bandwidth_reduction_percent=reduction,
            still_operational=True,
            notes="ECMP redistributes to remaining uplinks",
        ))

    # Scenario 3: Single leaf failure
    remaining_bw = bisection_bw * (leaf_count - 1) / leaf_count
    failure_scenarios.append(FailureScenario(
        scenario="Single leaf failure",
        remaining_bandwidth_gbps=remaining_bw,
        bandwidth_reduction_percent=(1 / leaf_count) * 100,
        still_operational=True,
        notes=f"Hosts on failed leaf lose connectivity; {leaf_count - 1} leaves remain",
    ))

    # Scenario 4: Worst case - spine + uplink failure
    if spine_count > 1 and uplink_count_per_leaf > 1:
        # Assuming 1 spine down + 1 uplink down (different spine)
        remaining_uplinks = uplink_count_per_leaf - 2 if uplink_count_per_leaf > 2 else uplink_count_per_leaf - 1
        if remaining_uplinks > 0:
            remaining_bw = uplink_speed.gbps * remaining_uplinks
            reduction = (1 - remaining_uplinks / uplink_count_per_leaf) * 100
            failure_scenarios.append(FailureScenario(
                scenario="Spine + uplink failure (worst case per leaf)",
                remaining_bandwidth_gbps=remaining_bw,
                bandwidth_reduction_percent=reduction,
                still_operational=True,
                notes="Multiple simultaneous failures",
            ))

    # Recommendations
    if oversub_ratio > 3:
        recommendations.append(
            f"High oversubscription ({oversub_ratio:.1f}:1) - consider adding uplinks or faster speeds"
        )
    elif oversub_ratio > 1:
        recommendations.append(
            f"Oversubscription ratio {oversub_ratio:.1f}:1 is acceptable for most workloads"
        )
    else:
        recommendations.append("Non-blocking fabric - suitable for high-performance workloads")

    if uplink_count_per_leaf < spine_count:
        recommendations.append(
            f"Not all spines utilized - consider adding {spine_count - uplink_count_per_leaf} more uplinks per leaf"
        )

    if ecmp_paths < 2:
        recommendations.append("Single path - no redundancy! Add more uplinks for ECMP")
    else:
        recommendations.append(f"{ecmp_paths}-way ECMP provides good load balancing")

    if hash_efficiency < 0.85:
        recommendations.append(
            "Consider traffic engineering for better ECMP distribution with many paths"
        )

    # Check for common design patterns
    if spine_count == 2 and uplink_count_per_leaf == 2:
        recommendations.append("Standard 2-spine design - good for small/medium deployments")
    elif spine_count == 4 and uplink_count_per_leaf == 4:
        recommendations.append("4-spine design - good for large deployments with high redundancy")

    return BandwidthResult(
        spine_count=spine_count,
        leaf_count=leaf_count,
        uplink_speed=uplink_speed.value,
        uplink_count_per_leaf=uplink_count_per_leaf,
        downlink_speed=downlink_speed.value,
        downlink_count_per_leaf=downlink_count_per_leaf,
        leaf_uplink_bandwidth_gbps=leaf_uplink_bw,
        leaf_downlink_bandwidth_gbps=leaf_downlink_bw,
        spine_total_bandwidth_gbps=spine_total_bw,
        fabric_bisection_bandwidth_gbps=bisection_bw,
        leaf_oversubscription=leaf_oversub,
        ecmp_paths=ecmp_paths,
        hash_efficiency=hash_efficiency,
        failure_scenarios=failure_scenarios,
        recommendations=recommendations,
    )
