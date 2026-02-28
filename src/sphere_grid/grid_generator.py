"""
Sphere Grid Generator — auto-generates the FFX-style skill tree topology from:
  1. Discovered skills (positioned by phase + tongue)
  2. Operational telemetry (tested paths become edges)
  3. Governance gates (Sacred Tongue sphere locks)

The grid is a graph where:
  - Nodes = skills (positioned by 21D CanonicalState)
  - Edges = operational connections (weighted by ds^2 distance)
  - Locks = governance gates (require Sacred Tongue spheres)
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .canonical_state import (
    TONGUE_NAMES,
    TONGUE_WEIGHTS,
    CanonicalState,
    compute_ds_squared,
    governance_gate,
    make_player_state,
)
from .skill_registry import SkillNode, build_registry

# Phase ordering for the layered tree
PHASE_ORDER = ["SENSE", "PLAN", "EXECUTE", "PUBLISH"]


@dataclass
class GridEdge:
    """An edge between two skill nodes on the sphere grid."""
    source: str  # skill name
    target: str  # skill name
    weight: float  # ds^2 distance
    tested: bool = False  # has this path been operationally tested?
    test_count: int = 0
    last_tested: Optional[float] = None  # unix timestamp

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "weight": self.weight,
            "tested": self.tested,
            "test_count": self.test_count,
            "last_tested": self.last_tested,
        }


@dataclass
class SphereGridLock:
    """A governance lock on a grid node requiring Sacred Tongue spheres."""
    node_name: str
    required_tongues: List[int]  # tongue indices needed to unlock
    required_level: float  # minimum tongue strength to pass
    lock_type: str = "STANDARD"  # STANDARD, ADVANCED, SACRED_EGG

    def to_dict(self) -> dict:
        return {
            "node_name": self.node_name,
            "required_tongues": self.required_tongues,
            "required_level": self.required_level,
            "lock_type": self.lock_type,
        }

    def check(self, player_state: CanonicalState) -> bool:
        """Check if player state can pass this lock."""
        for tongue_idx in self.required_tongues:
            if player_state.data[tongue_idx] < self.required_level:
                return False
        return True


@dataclass
class SphereGrid:
    """The complete sphere grid — nodes, edges, locks, and player state."""
    nodes: Dict[str, SkillNode] = field(default_factory=dict)
    edges: List[GridEdge] = field(default_factory=list)
    locks: Dict[str, SphereGridLock] = field(default_factory=dict)
    player_state: Optional[CanonicalState] = None
    collected_spheres: Dict[str, int] = field(default_factory=lambda: {
        "KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0,
    })
    telemetry_log: List[dict] = field(default_factory=list)

    @property
    def phase_groups(self) -> Dict[str, List[str]]:
        """Group nodes by phase."""
        groups: Dict[str, List[str]] = {p: [] for p in PHASE_ORDER}
        for name, node in self.nodes.items():
            if node.phase in groups:
                groups[node.phase].append(name)
        return groups

    @property
    def unlocked_nodes(self) -> List[str]:
        return [n for n, node in self.nodes.items() if node.unlocked]

    @property
    def locked_nodes(self) -> List[str]:
        return [n for n, node in self.nodes.items() if not node.unlocked]

    def adjacency(self, node_name: str) -> List[Tuple[str, float]]:
        """Get adjacent nodes with edge weights."""
        result = []
        for e in self.edges:
            if e.source == node_name:
                result.append((e.target, e.weight))
            elif e.target == node_name:
                result.append((e.source, e.weight))
        return result

    def to_dict(self) -> dict:
        return {
            "nodes": {n: node.to_dict() for n, node in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
            "locks": {n: lock.to_dict() for n, lock in self.locks.items()},
            "player_state": self.player_state.to_dict() if self.player_state else None,
            "collected_spheres": self.collected_spheres,
            "telemetry_log_count": len(self.telemetry_log),
        }


def generate_grid(
    extra_skill_dirs: List[Path] = None,
    player_tongue_xp: List[float] = None,
    max_edge_distance: float = 2.0,
) -> SphereGrid:
    """
    Auto-generate the sphere grid from discovered skills.

    1. Discover all skills and create nodes
    2. Compute ds^2 between all pairs to create edges
    3. Generate governance locks based on phase + difficulty
    4. Initialize player state
    """
    registry = build_registry(extra_skill_dirs)
    grid = SphereGrid(
        nodes=registry,
        player_state=make_player_state(player_tongue_xp),
    )

    # Generate edges: connect nodes within same phase and adjacent phases
    node_names = list(registry.keys())
    for i, name_a in enumerate(node_names):
        node_a = registry[name_a]
        if node_a.state is None:
            continue
        for name_b in node_names[i + 1:]:
            node_b = registry[name_b]
            if node_b.state is None:
                continue

            # Only connect within same phase or adjacent phases
            phase_a = PHASE_ORDER.index(node_a.phase) if node_a.phase in PHASE_ORDER else -1
            phase_b = PHASE_ORDER.index(node_b.phase) if node_b.phase in PHASE_ORDER else -1
            if phase_a < 0 or phase_b < 0:
                continue
            if abs(phase_a - phase_b) > 1:
                continue

            # Compute distance
            ds2 = compute_ds_squared(node_a.state, node_b.state)
            if ds2["total"] <= max_edge_distance:
                grid.edges.append(GridEdge(
                    source=name_a,
                    target=name_b,
                    weight=ds2["total"],
                ))

    # Generate locks for higher-difficulty nodes
    for name, node in registry.items():
        if node.difficulty > 0.4:
            required_tongues = [node.primary_tongue]
            # Higher phases need more tongues
            phase_idx = PHASE_ORDER.index(node.phase) if node.phase in PHASE_ORDER else 0
            if phase_idx >= 2:  # EXECUTE or PUBLISH
                # Add Hodge dual tongue
                dual_map = {0: 5, 5: 0, 1: 4, 4: 1, 2: 3, 3: 2}
                required_tongues.append(dual_map[node.primary_tongue])

            lock_type = "STANDARD"
            if node.difficulty > 0.7:
                lock_type = "ADVANCED"
            if node.difficulty > 0.9:
                lock_type = "SACRED_EGG"

            grid.locks[name] = SphereGridLock(
                node_name=name,
                required_tongues=required_tongues,
                required_level=node.difficulty * 0.3,
                lock_type=lock_type,
            )
            node.unlocked = False

    # Evaluate which nodes the player can already unlock
    if grid.player_state:
        for name, lock in grid.locks.items():
            if lock.check(grid.player_state):
                grid.nodes[name].unlocked = True

    return grid


def record_skill_invocation(grid: SphereGrid, skill_name: str, success: bool = True):
    """Record that a skill was invoked — updates telemetry and edges."""
    if skill_name not in grid.nodes:
        return

    node = grid.nodes[skill_name]
    node.telemetry_count += 1

    # Grant sphere for the skill's primary tongue
    tongue_name = TONGUE_NAMES[node.primary_tongue]
    if success:
        grid.collected_spheres[tongue_name] = grid.collected_spheres.get(tongue_name, 0) + 1

    # Log telemetry
    grid.telemetry_log.append({
        "skill": skill_name,
        "timestamp": time.time(),
        "success": success,
        "tongue": tongue_name,
        "phase": node.phase,
    })


def record_path(grid: SphereGrid, skill_sequence: List[str]):
    """Record a sequence of skill invocations — marks edges as tested."""
    now = time.time()
    for i in range(len(skill_sequence) - 1):
        src, tgt = skill_sequence[i], skill_sequence[i + 1]
        # Find or create edge
        found = False
        for edge in grid.edges:
            if (edge.source == src and edge.target == tgt) or \
               (edge.source == tgt and edge.target == src):
                edge.tested = True
                edge.test_count += 1
                edge.last_tested = now
                found = True
                break
        if not found and src in grid.nodes and tgt in grid.nodes:
            # Auto-create edge from tested path
            s1 = grid.nodes[src].state
            s2 = grid.nodes[tgt].state
            if s1 and s2:
                ds2 = compute_ds_squared(s1, s2)
                grid.edges.append(GridEdge(
                    source=src,
                    target=tgt,
                    weight=ds2["total"],
                    tested=True,
                    test_count=1,
                    last_tested=now,
                ))


def save_grid(grid: SphereGrid, path: Path):
    """Persist grid state to JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(grid.to_dict(), indent=2, default=str), encoding="utf-8")


def render_ascii_grid(grid: SphereGrid) -> str:
    """Render the sphere grid as ASCII art for terminal display."""
    lines = []
    lines.append("=" * 70)
    lines.append("  SCBE SPHERE GRID — FFX-Style Federated Skill Tree")
    lines.append("=" * 70)

    # Sphere collection summary
    spheres = grid.collected_spheres
    sphere_bar = "  Spheres: " + " | ".join(
        f"{name}:{count}" for name, count in spheres.items()
    )
    lines.append(sphere_bar)
    lines.append("-" * 70)

    # Render by phase
    groups = grid.phase_groups
    layer_ranges = {"SENSE": "L1-L4", "PLAN": "L5-L8", "EXECUTE": "L9-L12", "PUBLISH": "L13-L14"}

    for phase in PHASE_ORDER:
        nodes = groups.get(phase, [])
        layers = layer_ranges.get(phase, "")
        lines.append(f"\n  [{phase}] ({layers}) — {len(nodes)} nodes")
        lines.append("  " + "-" * 40)

        for name in sorted(nodes):
            node = grid.nodes[name]
            lock_icon = "O" if node.unlocked else "X"
            tongue = TONGUE_NAMES[node.primary_tongue]
            tested = node.telemetry_count
            lock_info = ""
            if name in grid.locks and not node.unlocked:
                lock = grid.locks[name]
                req = ",".join(TONGUE_NAMES[t] for t in lock.required_tongues)
                lock_info = f" [LOCKED: needs {req} >= {lock.required_level:.1f}]"

            lines.append(f"    [{lock_icon}] {name} ({tongue}) x{tested}{lock_info}")

    # Edge summary
    tested_edges = sum(1 for e in grid.edges if e.tested)
    total_edges = len(grid.edges)
    lines.append(f"\n  Paths: {tested_edges}/{total_edges} tested")
    lines.append("=" * 70)

    return "\n".join(lines)
