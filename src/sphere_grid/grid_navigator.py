"""
Sphere Grid Navigator — A* pathfinding on the hyperbolic manifold.

Finds optimal routes through the skill tree considering:
  - ds^2 distance between nodes (hyperbolic product manifold metric)
  - Governance locks (Sacred Tongue sphere requirements)
  - Tested vs untested paths (tested paths have lower cost)
  - Phase ordering (SENSE -> PLAN -> EXECUTE -> PUBLISH preferred)
"""

import heapq
import math
from typing import Dict, List, Optional, Set, Tuple

from .canonical_state import (
    TONGUE_NAMES,
    CanonicalState,
    compute_ds_squared,
    governance_gate,
)
from .grid_generator import PHASE_ORDER, SphereGrid


def heuristic(grid: SphereGrid, current: str, goal: str) -> float:
    """
    Admissible heuristic for A*: uses ds^2 tongue distance (lower bound).
    """
    n1 = grid.nodes.get(current)
    n2 = grid.nodes.get(goal)
    if not n1 or not n2 or not n1.state or not n2.state:
        return 0.0
    ds2 = compute_ds_squared(n1.state, n2.state)
    return math.sqrt(ds2["tongue"])  # tongue distance as heuristic


def find_path(
    grid: SphereGrid,
    start: str,
    goal: str,
    respect_locks: bool = True,
    prefer_tested: bool = True,
    untested_penalty: float = 2.0,
) -> Optional[List[str]]:
    """
    A* pathfinding through the sphere grid.

    Args:
        grid: The sphere grid
        start: Starting skill node name
        goal: Target skill node name
        respect_locks: If True, locked nodes are impassable
        prefer_tested: If True, tested edges cost less
        untested_penalty: Multiplier for untested edge cost

    Returns:
        List of skill names forming the path, or None if unreachable
    """
    if start not in grid.nodes or goal not in grid.nodes:
        return None

    # Build adjacency with costs
    adj: Dict[str, List[Tuple[str, float]]] = {}
    for name in grid.nodes:
        adj[name] = []

    for edge in grid.edges:
        cost = edge.weight
        if prefer_tested and not edge.tested:
            cost *= untested_penalty

        if edge.source in adj:
            adj[edge.source].append((edge.target, cost))
        if edge.target in adj:
            adj[edge.target].append((edge.source, cost))

    # A* search
    open_set: List[Tuple[float, str]] = [(0.0, start)]
    came_from: Dict[str, str] = {}
    g_score: Dict[str, float] = {start: 0.0}
    closed: Set[str] = set()

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            # Reconstruct path
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            return list(reversed(path))

        if current in closed:
            continue
        closed.add(current)

        for neighbor, edge_cost in adj.get(current, []):
            if neighbor in closed:
                continue

            # Lock check
            if respect_locks and not grid.nodes[neighbor].unlocked:
                continue

            tentative_g = g_score[current] + edge_cost
            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + heuristic(grid, neighbor, goal)
                heapq.heappush(open_set, (f_score, neighbor))

    return None  # No path found


def find_optimal_phase_route(
    grid: SphereGrid,
    target_phase: str = "PUBLISH",
) -> Optional[List[str]]:
    """
    Find the optimal route from any SENSE node to a PUBLISH node,
    passing through PLAN and EXECUTE phases in order.
    """
    groups = grid.phase_groups
    target_idx = PHASE_ORDER.index(target_phase) if target_phase in PHASE_ORDER else 3

    # Find the best chain: pick one node per phase
    best_path = None
    best_cost = float("inf")

    sense_nodes = [n for n in groups.get("SENSE", []) if grid.nodes[n].unlocked]
    if not sense_nodes:
        return None

    for start in sense_nodes:
        # Greedy: from SENSE, find nearest PLAN node, then EXECUTE, then PUBLISH
        current = start
        chain = [current]
        total_cost = 0.0

        for phase_idx in range(1, target_idx + 1):
            phase = PHASE_ORDER[phase_idx]
            phase_nodes = [n for n in groups.get(phase, []) if grid.nodes[n].unlocked]
            if not phase_nodes:
                break

            # Find nearest phase node
            best_next = None
            best_next_cost = float("inf")
            for candidate in phase_nodes:
                path = find_path(grid, current, candidate, prefer_tested=True)
                if path:
                    cost = sum(
                        _edge_cost(grid, path[i], path[i + 1])
                        for i in range(len(path) - 1)
                    )
                    if cost < best_next_cost:
                        best_next = candidate
                        best_next_cost = cost

            if best_next is None:
                break
            chain.append(best_next)
            total_cost += best_next_cost
            current = best_next

        if len(chain) == target_idx + 1 and total_cost < best_cost:
            best_path = chain
            best_cost = total_cost

    return best_path


def _edge_cost(grid: SphereGrid, a: str, b: str) -> float:
    """Get the edge cost between two adjacent nodes."""
    for edge in grid.edges:
        if (edge.source == a and edge.target == b) or \
           (edge.source == b and edge.target == a):
            return edge.weight
    return float("inf")


def suggest_next_skills(
    grid: SphereGrid,
    current_skill: str,
    count: int = 3,
) -> List[Tuple[str, float, str]]:
    """
    Suggest the next best skills to use from current position.
    Returns list of (skill_name, cost, reason) tuples.
    """
    suggestions = []
    neighbors = grid.adjacency(current_skill)

    for name, weight in sorted(neighbors, key=lambda x: x[1]):
        if len(suggestions) >= count:
            break
        node = grid.nodes.get(name)
        if not node:
            continue

        if not node.unlocked:
            lock = grid.locks.get(name)
            if lock:
                req = ",".join(TONGUE_NAMES[t] for t in lock.required_tongues)
                suggestions.append((name, weight, f"LOCKED (needs {req})"))
            continue

        # Prefer untested paths (exploration value)
        tested = any(
            (e.source == current_skill and e.target == name) or
            (e.source == name and e.target == current_skill)
            for e in grid.edges if e.tested
        )
        reason = "tested path" if tested else "unexplored route"
        suggestions.append((name, weight, reason))

    return suggestions


def evaluate_route_governance(
    grid: SphereGrid,
    route: List[str],
) -> List[Dict]:
    """
    Evaluate governance gates along a route.
    Returns per-step governance decisions.
    """
    if not grid.player_state:
        return []

    results = []
    for skill_name in route:
        node = grid.nodes.get(skill_name)
        if not node or not node.state:
            results.append({"skill": skill_name, "decision": "UNKNOWN"})
            continue

        decision = governance_gate(
            grid.player_state,
            node.primary_tongue,
        )
        results.append({
            "skill": skill_name,
            "phase": node.phase,
            "tongue": TONGUE_NAMES[node.primary_tongue],
            "decision": decision,
            "difficulty": node.difficulty,
        })

    return results
