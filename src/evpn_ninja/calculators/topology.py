"""Topology visualization for datacenter fabrics.

Generates ASCII art and Graphviz DOT representations
of leaf-spine topologies.
"""

from dataclasses import dataclass


@dataclass
class TopologyResult:
    """Topology visualization result."""

    spine_count: int
    leaf_count: int
    ascii_art: str
    graphviz_dot: str


def _generate_ascii_topology(
    spine_count: int,
    leaf_count: int,
    show_connections: bool = True,
) -> str:
    """
    Generate ASCII art representation of leaf-spine topology.

    Example output for 2 spines, 4 leaves:

    ┌─────────┐     ┌─────────┐
    │ Spine 1 │     │ Spine 2 │
    └────┬────┘     └────┬────┘
         │    ╲   ╱    │
         │     ╲ ╱     │
         │      ╳      │
         │     ╱ ╲     │
         │    ╱   ╲    │
    ┌────┴────┐ ┌────┴────┐ ┌─────────┐ ┌─────────┐
    │ Leaf 1  │ │ Leaf 2  │ │ Leaf 3  │ │ Leaf 4  │
    └─────────┘ └─────────┘ └─────────┘ └─────────┘
    """
    lines: list[str] = []

    # Calculate widths
    box_width = 11
    spine_spacing = 5
    leaf_spacing = 1

    # Header
    lines.append("")
    lines.append("  Leaf-Spine Topology")
    lines.append("  " + "=" * 40)
    lines.append("")

    # Spine layer
    spine_line_top = ""
    spine_line_mid = ""
    spine_line_bot = ""

    for i in range(spine_count):
        prefix = " " * spine_spacing if i > 0 else ""
        spine_line_top += prefix + "┌" + "─" * (box_width - 2) + "┐"
        spine_line_mid += prefix + "│" + f" Spine {i+1} ".center(box_width - 2) + "│"
        spine_line_bot += prefix + "└" + "─" * (box_width - 2) + "┘"

    lines.append("  " + spine_line_top)
    lines.append("  " + spine_line_mid)
    lines.append("  " + spine_line_bot)

    # Connection lines (simplified)
    if show_connections and spine_count <= 4 and leaf_count <= 8:
        lines.append("")
        total_spine_width = spine_count * box_width + (spine_count - 1) * spine_spacing
        total_leaf_width = leaf_count * box_width + (leaf_count - 1) * leaf_spacing

        # Simple connection indicator
        conn_line = " " * 2 + "│" * (total_spine_width // 2)
        lines.append(conn_line)
        lines.append("  " + "─" * max(total_spine_width, total_leaf_width))
        conn_line = " " * 2 + "│" * (total_leaf_width // 2)
        lines.append(conn_line)
        lines.append("")
    else:
        lines.append("")
        lines.append("       ║ Full mesh connectivity ║")
        lines.append("")

    # Leaf layer
    leaf_line_top = ""
    leaf_line_mid = ""
    leaf_line_bot = ""

    for i in range(leaf_count):
        prefix = " " * leaf_spacing if i > 0 else ""
        leaf_line_top += prefix + "┌" + "─" * (box_width - 2) + "┐"
        leaf_line_mid += prefix + "│" + f" Leaf {i+1}  ".center(box_width - 2)[:box_width-2] + "│"
        leaf_line_bot += prefix + "└" + "─" * (box_width - 2) + "┘"

    lines.append("  " + leaf_line_top)
    lines.append("  " + leaf_line_mid)
    lines.append("  " + leaf_line_bot)

    # Summary
    lines.append("")
    lines.append(f"  Spines: {spine_count}  |  Leaves: {leaf_count}  |  Links: {spine_count * leaf_count}")
    lines.append("")

    return "\n".join(lines)


def _generate_graphviz_dot(
    spine_count: int,
    leaf_count: int,
    uplink_speed: str = "100G",
    downlink_speed: str = "25G",
) -> str:
    """
    Generate Graphviz DOT representation.

    Can be rendered with: dot -Tpng topology.dot -o topology.png
    """
    lines: list[str] = []

    lines.append("// VXLAN Leaf-Spine Topology")
    lines.append("// Render with: dot -Tpng topology.dot -o topology.png")
    lines.append("")
    lines.append("digraph LeafSpine {")
    lines.append("    rankdir=TB;")
    lines.append("    splines=polyline;")
    lines.append("    nodesep=0.8;")
    lines.append("    ranksep=1.5;")
    lines.append("")
    lines.append("    // Graph styling")
    lines.append('    graph [fontname="Helvetica", bgcolor="white"];')
    lines.append('    node [fontname="Helvetica", fontsize=12];')
    lines.append('    edge [fontname="Helvetica", fontsize=10];')
    lines.append("")

    # Spine nodes
    lines.append("    // Spine layer")
    lines.append("    subgraph cluster_spines {")
    lines.append('        label="Spine Layer";')
    lines.append('        style=dashed;')
    lines.append('        color=blue;')
    lines.append("")

    for i in range(spine_count):
        lines.append(
            f'        spine{i+1} [label="Spine {i+1}\\n(BGP RR)", '
            f'shape=box, style=filled, fillcolor="lightblue"];'
        )
    lines.append("    }")
    lines.append("")

    # Leaf nodes
    lines.append("    // Leaf layer")
    lines.append("    subgraph cluster_leaves {")
    lines.append('        label="Leaf Layer (VTEPs)";')
    lines.append('        style=dashed;')
    lines.append('        color=green;')
    lines.append("")

    for i in range(leaf_count):
        lines.append(
            f'        leaf{i+1} [label="Leaf {i+1}\\n(VTEP)", '
            f'shape=box, style=filled, fillcolor="lightgreen"];'
        )
    lines.append("    }")
    lines.append("")

    # Connections
    lines.append("    // Spine-Leaf connections")
    for spine_idx in range(spine_count):
        for leaf_idx in range(leaf_count):
            lines.append(
                f'    spine{spine_idx+1} -> leaf{leaf_idx+1} '
                f'[dir=none, label="{uplink_speed}", color="darkgray"];'
            )
    lines.append("")

    # Rank constraints
    lines.append("    // Rank constraints")
    spine_list = " ".join([f"spine{i+1}" for i in range(spine_count)])
    leaf_list = " ".join([f"leaf{i+1}" for i in range(leaf_count)])
    lines.append(f"    {{ rank=same; {spine_list} }}")
    lines.append(f"    {{ rank=same; {leaf_list} }}")
    lines.append("")

    # Legend
    lines.append("    // Legend")
    lines.append("    subgraph cluster_legend {")
    lines.append('        label="Legend";')
    lines.append('        style=solid;')
    lines.append('        color=gray;')
    lines.append(f'        info [label="Spines: {spine_count}\\n'
                 f'Leaves: {leaf_count}\\n'
                 f'Links: {spine_count * leaf_count}\\n'
                 f'Uplink: {uplink_speed}\\n'
                 f'Downlink: {downlink_speed}", '
                 f'shape=note, style=filled, fillcolor="lightyellow"];')
    lines.append("    }")

    lines.append("}")

    return "\n".join(lines)


def generate_topology(
    spine_count: int = 2,
    leaf_count: int = 4,
    uplink_speed: str = "100G",
    downlink_speed: str = "25G",
) -> TopologyResult:
    """
    Generate topology visualizations.

    Args:
        spine_count: Number of spine switches
        leaf_count: Number of leaf switches
        uplink_speed: Speed of leaf-to-spine links
        downlink_speed: Speed of host-facing links

    Returns:
        TopologyResult with ASCII and Graphviz representations
    """
    ascii_art = _generate_ascii_topology(spine_count, leaf_count)
    graphviz_dot = _generate_graphviz_dot(
        spine_count, leaf_count, uplink_speed, downlink_speed
    )

    return TopologyResult(
        spine_count=spine_count,
        leaf_count=leaf_count,
        ascii_art=ascii_art,
        graphviz_dot=graphviz_dot,
    )
