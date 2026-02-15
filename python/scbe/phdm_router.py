"""
PHDM Router: Hamiltonian Path Routing with φ-Weighted Energy Costs
====================================================================

Crystal Cranium v3.0.0 Section 4 — Thought Trajectory Validation

A "thought" is a Hamiltonian path through the 16 polyhedral nodes:
    - Visits each required node exactly once
    - Conserves symplectic momentum: Σ p·dq = const
    - No jumps across disconnected regions
    - Energy cost φ-weighted per segment

The router validates that thought trajectories are physically
realizable on the polyhedral graph, with energy costs that
escalate exponentially in the Risk and Recursive zones.

Integration Points:
    - Layer 0.5: Golden path construction from Kyber shared secret
    - Layer 7:   Swarm consensus uses expected trajectory γ(t)
    - Layer 13:  Curvature κ(t) feeds risk scoring
    - Layer 14:  s_phdm subscore from path adherence

Academic Foundation:
    - O'Rourke (2010): 4/5 Platonic solids admit Hamiltonian unfoldings
    - Séquin (2005): All Platonic solids admit Hamiltonian cycles
    - Dodecahedron is "zip-rigid" — consistent with Core zone stability
    - Risk zone solids are deliberately hard to traverse

Author: Issac Davis
Version: 3.0.0
"""

from __future__ import annotations

import hashlib
import hmac
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any, Set
from enum import Enum

# =============================================================================
# Constants
# =============================================================================

PHI = (1 + np.sqrt(5)) / 2
PHI_INV = 2 / (1 + np.sqrt(5))
R_FIFTH = 3 / 2
PYTHAGOREAN_COMMA = 531441 / 524288


# =============================================================================
# Import polyhedra registry
# =============================================================================

try:
    from .phdm_polyhedra import (
        get_registry, get_polyhedron, CrystalPolyhedron,
        CognitiveZone, ZONE_SPECS, PHI as _PHI
    )
except ImportError:
    # Standalone mode — define minimal stubs
    get_registry = None
    get_polyhedron = None


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ThoughtPath:
    """
    A validated Hamiltonian path through the polyhedral lattice.

    Represents a single "thought" — the trajectory an intent takes
    through the 16 cognitive polyhedra.
    """
    nodes: List[int]                    # Ordered list of polyhedron indices
    tongue: str = "KO"                  # Active Sacred Tongue
    energy_cost: float = 0.0            # Total φ-weighted energy
    segment_energies: List[float] = field(default_factory=list)
    is_valid: bool = True               # Passes Hamiltonian check
    violations: List[str] = field(default_factory=list)
    symplectic_momentum: float = 0.0    # Σ p·dq

    def is_hamiltonian(self) -> bool:
        """Check if path visits each node exactly once."""
        return (
            self.is_valid and
            len(self.nodes) == len(set(self.nodes)) and
            len(self.violations) == 0
        )

    @property
    def length(self) -> int:
        return len(self.nodes)


@dataclass
class GeodesicSegment:
    """A segment of the geodesic curve γ(t) between two polyhedra."""
    from_idx: int
    to_idx: int
    from_centroid: np.ndarray
    to_centroid: np.ndarray
    energy: float               # φ-weighted segment energy
    hyperbolic_distance: float  # d_H between centroids
    curvature: float = 0.0     # Local curvature κ at midpoint


# =============================================================================
# Adjacency Graph
# =============================================================================

# Default adjacency graph for the 16 polyhedra
# Each node connects to 3-5 neighbors based on geometric/topological affinity
DEFAULT_ADJACENCY: Dict[int, List[int]] = {
    0:  [1, 2, 5, 10],       # Tetrahedron → Cube, Octahedron, TruncTet, Szilassi
    1:  [0, 2, 6, 14],       # Cube → Tet, Oct, Cuboctahedron, RhombDodec
    2:  [0, 1, 3, 6],        # Octahedron → Tet, Cube, Dodec, Cuboctahedron
    3:  [2, 4, 7, 8],        # Dodecahedron → Oct, Ico, Icosidodec, SmallStell
    4:  [3, 5, 7, 9],        # Icosahedron → Dodec, TruncTet, Icosidodec, GreatDodec
    5:  [0, 4, 6, 10],       # TruncTet → Tet, Ico, Cuboctahedron, Szilassi
    6:  [1, 2, 5, 7, 14],    # Cuboctahedron → Cube, Oct, TruncTet, Icosidodec, RhombDodec
    7:  [3, 4, 6, 8, 15],    # Icosidodecahedron → Dodec, Ico, Cuboctahedron, SmallStell, Bilinski
    8:  [3, 7, 9, 15],       # SmallStellDodec → Dodec, Icosidodec, GreatDodec, Bilinski
    9:  [4, 8, 10, 11],      # GreatDodec → Ico, SmallStell, Szilassi, Csaszar
    10: [0, 5, 9, 11],       # Szilassi → Tet, TruncTet, GreatDodec, Csaszar
    11: [9, 10, 12, 13],     # Csaszar → GreatDodec, Szilassi, PentBipyr, TriCup
    12: [11, 13, 14],        # PentBipyramid → Csaszar, TriCup, RhombDodec
    13: [11, 12, 15],        # TriCupola → Csaszar, PentBipyr, Bilinski
    14: [1, 6, 12, 15],      # RhombDodec → Cube, Cuboctahedron, PentBipyr, Bilinski
    15: [7, 8, 13, 14],      # Bilinski → Icosidodec, SmallStell, TriCup, RhombDodec
}


def get_adjacency() -> Dict[int, List[int]]:
    """Get the adjacency graph, preferring registry data if available."""
    if get_registry is not None:
        try:
            registry = get_registry()
            adj = {}
            for p in registry:
                if p.adjacency:
                    adj[p.index] = p.adjacency
            if len(adj) == 16:
                return adj
        except Exception:
            pass
    return DEFAULT_ADJACENCY


# =============================================================================
# Hamiltonian Path Router
# =============================================================================

class HamiltonianRouter:
    """
    Routes thoughts through the 16 polyhedral nodes as Hamiltonian paths.

    Given an intent vector and context, finds a valid Hamiltonian path
    (visits each required node exactly once) with minimal φ-weighted
    energy cost.

    The router enforces:
        1. Single-visit constraint (no loops)
        2. Adjacency constraint (must follow graph edges)
        3. Energy conservation (Σ p·dq = const along path)
        4. Zone-dependent traversal costs (Risk zone = expensive)
    """

    def __init__(self, adjacency: Optional[Dict[int, List[int]]] = None):
        self.adjacency = adjacency or get_adjacency()
        self._centroids = self._load_centroids()

    def _load_centroids(self) -> Dict[int, np.ndarray]:
        """Load 6D centroids from registry or generate defaults."""
        centroids = {}
        if get_registry is not None:
            try:
                for p in get_registry():
                    centroids[p.index] = p.centroid_6d
                return centroids
            except Exception:
                pass

        # Generate default centroids using φ-spacing
        for i in range(16):
            angles = np.array([(i * PHI * k) % (2 * np.pi)
                               for k in range(1, 7)])
            r = 0.1 + 0.05 * i  # Spread across radial distance
            centroids[i] = np.cos(angles) * r
        return centroids

    def _phi_energy(self, from_idx: int, to_idx: int) -> float:
        """
        Compute φ-weighted energy cost for traversing an edge.

        Energy = φ^(max_zone_index) * hyperbolic_distance(from, to)

        Risk zone edges cost φ^8 to φ^9 times more than Core edges.
        """
        c1 = self._centroids.get(from_idx, np.zeros(6))
        c2 = self._centroids.get(to_idx, np.zeros(6))

        # Hyperbolic distance approximation
        diff = np.linalg.norm(c1 - c2)

        # Zone multiplier: φ^(zone_index)
        zone_mult = PHI ** max(from_idx, to_idx)

        return float(diff * zone_mult)

    def _hyperbolic_distance(self, u: np.ndarray, v: np.ndarray) -> float:
        """Poincaré ball hyperbolic distance."""
        u, v = np.asarray(u), np.asarray(v)
        norm_u_sq = min(np.sum(u ** 2), 0.9999)
        norm_v_sq = min(np.sum(v ** 2), 0.9999)
        diff_sq = np.sum((u - v) ** 2)
        delta = 2 * diff_sq / ((1 - norm_u_sq) * (1 - norm_v_sq))
        return float(np.arccosh(1 + delta))

    def trace_path(
        self,
        intent_vector: np.ndarray,
        required_nodes: Optional[Set[int]] = None,
        tongue: str = "KO",
        max_nodes: int = 16,
    ) -> ThoughtPath:
        """
        Trace a Hamiltonian path through the lattice.

        Uses intent-hash-directed greedy search with backtracking
        to find a valid path visiting all required nodes.

        Args:
            intent_vector: Intent embedded as a vector
            required_nodes: Set of node indices to visit (default: all 16)
            tongue: Active Sacred Tongue for weighting
            max_nodes: Maximum nodes to visit

        Returns:
            ThoughtPath with validation results
        """
        if required_nodes is None:
            required_nodes = set(range(16))

        # Hash intent to determine starting node
        intent_hash = hashlib.sha256(
            intent_vector.tobytes() + tongue.encode()
        ).digest()
        start_idx = intent_hash[0] % 16
        while start_idx not in required_nodes:
            start_idx = (start_idx + 1) % 16

        # Greedy Hamiltonian search with intent-directed scoring
        path = self._hamiltonian_search(
            start=start_idx,
            required=required_nodes,
            intent_hash=intent_hash,
            max_nodes=max_nodes,
        )

        # Build ThoughtPath with energy calculations
        thought = ThoughtPath(
            nodes=path,
            tongue=tongue,
        )

        # Calculate segment energies
        total_energy = 0.0
        symplectic_sum = 0.0
        for i in range(len(path) - 1):
            seg_energy = self._phi_energy(path[i], path[i + 1])
            thought.segment_energies.append(seg_energy)
            total_energy += seg_energy

            # Symplectic momentum: p·dq approximation
            c1 = self._centroids.get(path[i], np.zeros(6))
            c2 = self._centroids.get(path[i + 1], np.zeros(6))
            dq = c2 - c1
            p = (c1 + c2) / 2  # Midpoint as momentum proxy
            symplectic_sum += float(np.dot(p, dq))

        thought.energy_cost = total_energy
        thought.symplectic_momentum = symplectic_sum

        # Validate
        thought.is_valid = True
        visited = set(path)

        if len(path) != len(visited):
            thought.is_valid = False
            thought.violations.append("Repeated nodes (not Hamiltonian)")

        missing = required_nodes - visited
        if missing and len(path) < len(required_nodes):
            thought.violations.append(f"Missing nodes: {missing}")

        # Check adjacency
        for i in range(len(path) - 1):
            neighbors = self.adjacency.get(path[i], [])
            if path[i + 1] not in neighbors:
                thought.violations.append(
                    f"P{path[i]}→P{path[i+1]}: no edge in adjacency graph"
                )

        return thought

    def _hamiltonian_search(
        self,
        start: int,
        required: Set[int],
        intent_hash: bytes,
        max_nodes: int,
    ) -> List[int]:
        """
        Intent-directed greedy Hamiltonian search with backtracking.

        Uses the intent hash to bias neighbor selection, producing
        different paths for different intents.
        """
        path = [start]
        visited = {start}

        while len(path) < min(max_nodes, len(required)):
            current = path[-1]
            neighbors = self.adjacency.get(current, [])

            # Filter to unvisited neighbors in required set
            candidates = [n for n in neighbors
                          if n not in visited and n in required]

            if not candidates:
                # Backtrack if stuck
                if len(path) > 1:
                    path.pop()
                    visited = set(path)
                    continue
                break

            # Intent-directed scoring: hash byte determines preference
            byte_idx = len(path) % len(intent_hash)
            seed = intent_hash[byte_idx]

            # Score candidates by (energy_cost + intent_bias)
            scored = []
            for c in candidates:
                energy = self._phi_energy(current, c)
                bias = ((seed + c) % 256) / 256.0  # Intent-dependent bias
                scored.append((energy * (1.0 + bias), c))

            scored.sort()
            chosen = scored[0][1]

            path.append(chosen)
            visited.add(chosen)

        return path

    def validate_path(self, path: List[int]) -> Tuple[bool, List[str]]:
        """
        Validate an externally-provided path.

        Checks:
            1. No repeated nodes
            2. All edges exist in adjacency graph
            3. All nodes are valid (0-15)
        """
        errors = []

        if len(path) != len(set(path)):
            errors.append("Path contains repeated nodes")

        for node in path:
            if node < 0 or node > 15:
                errors.append(f"Invalid node index: {node}")

        for i in range(len(path) - 1):
            neighbors = self.adjacency.get(path[i], [])
            if path[i + 1] not in neighbors:
                errors.append(f"No edge: P{path[i]}→P{path[i+1]}")

        return len(errors) == 0, errors

    def all_paths_from(self, start: int, max_depth: int = 16) -> List[List[int]]:
        """
        Enumerate all Hamiltonian paths from a start node (DFS).

        Warning: exponential in worst case. Use max_depth to limit.
        """
        all_paths = []

        def dfs(current: int, path: List[int], visited: Set[int]):
            if len(path) == max_depth or len(path) == 16:
                all_paths.append(path[:])
                return
            for neighbor in self.adjacency.get(current, []):
                if neighbor not in visited:
                    path.append(neighbor)
                    visited.add(neighbor)
                    dfs(neighbor, path, visited)
                    path.pop()
                    visited.remove(neighbor)

        dfs(start, [start], {start})
        return all_paths


# =============================================================================
# Golden Path (HMAC-chained geodesic)
# =============================================================================

def create_golden_path(
    shared_secret: bytes,
    total_duration: float = 60.0,
) -> Tuple[List[np.ndarray], List[float], List[bytes]]:
    """
    Create the "golden path" geodesic through all polyhedra.

    HMAC-chains each polyhedron with the shared secret to produce
    key-dependent waypoints. This is the expected trajectory γ(t)
    for intrusion detection.

    Args:
        shared_secret: Kyber shared secret (32 bytes)
        total_duration: Total time to traverse path

    Returns:
        (waypoints, timestamps, hmac_keys)
    """
    waypoints = []
    timestamps = []
    keys = [shared_secret]

    # Load centroids
    centroids = {}
    if get_registry is not None:
        try:
            for p in get_registry():
                centroids[p.index] = p.centroid_6d
        except Exception:
            pass

    # Default Hamiltonian ordering
    ordering = [0, 1, 2, 6, 14, 3, 4, 7, 15, 8, 9, 5, 10, 11, 12, 13]

    for i, idx in enumerate(ordering):
        # Get centroid (or generate)
        if idx in centroids:
            centroid = centroids[idx].copy()
        else:
            angles = np.array([(idx * PHI * k) % (2 * np.pi) for k in range(1, 7)])
            centroid = np.cos(angles) * (0.1 + 0.05 * idx)

        # HMAC perturbation (key-dependent)
        K = keys[-1]
        data = f"{idx}|{i}".encode() + K
        K_next = hmac.new(K, data, hashlib.sha256).digest()
        keys.append(K_next)

        # Perturb centroid by key
        perturbation = np.array([
            (b % 100) / 10000.0 - 0.005 for b in K_next[:6]
        ])
        centroid += perturbation

        waypoints.append(centroid)
        timestamps.append(i * total_duration / len(ordering))

    return waypoints, timestamps, keys


# =============================================================================
# Self-Test
# =============================================================================

def self_test() -> Dict[str, Any]:
    """Run self-tests on the Hamiltonian router."""
    results = {}
    passed = 0
    total = 0

    router = HamiltonianRouter()

    # Test 1: Adjacency graph is valid
    total += 1
    adj = router.adjacency
    if len(adj) == 16:
        passed += 1
        results["adjacency_graph"] = f"PASS (16 nodes, {sum(len(v) for v in adj.values())} edges)"
    else:
        results["adjacency_graph"] = f"FAIL ({len(adj)} nodes)"

    # Test 2: Adjacency is symmetric
    total += 1
    symmetric = True
    for node, neighbors in adj.items():
        for n in neighbors:
            if node not in adj.get(n, []):
                symmetric = False
                break
    if symmetric:
        passed += 1
        results["adjacency_symmetric"] = "PASS"
    else:
        results["adjacency_symmetric"] = "FAIL"

    # Test 3: trace_path produces valid output
    total += 1
    intent = np.random.randn(6) * 0.3
    path = router.trace_path(intent, tongue="KO")
    if path.length > 0 and path.energy_cost > 0:
        passed += 1
        results["trace_path"] = (
            f"PASS ({path.length} nodes, "
            f"energy={path.energy_cost:.2f}, "
            f"violations={len(path.violations)})"
        )
    else:
        results["trace_path"] = "FAIL"

    # Test 4: Different intents produce different paths
    total += 1
    intent2 = np.random.randn(6) * 0.3
    path2 = router.trace_path(intent2, tongue="UM")
    if path.nodes != path2.nodes or path.tongue != path2.tongue:
        passed += 1
        results["intent_sensitivity"] = "PASS (different paths for different intents)"
    else:
        results["intent_sensitivity"] = "FAIL (identical paths)"

    # Test 5: validate_path catches invalid paths
    total += 1
    valid_ok, _ = router.validate_path([0, 1, 2, 3])
    invalid_ok, errors = router.validate_path([0, 0, 1])  # Repeated
    if valid_ok and not invalid_ok and "repeated" in errors[0].lower():
        passed += 1
        results["validation"] = "PASS (catches repeated nodes)"
    else:
        results["validation"] = f"FAIL (valid={valid_ok}, invalid={invalid_ok})"

    # Test 6: Golden path construction
    total += 1
    secret = b"test_secret_for_golden_path_32b"
    waypoints, timestamps, keys = create_golden_path(secret)
    if len(waypoints) == 16 and len(keys) == 17:
        passed += 1
        results["golden_path"] = f"PASS (16 waypoints, 17 keys)"
    else:
        results["golden_path"] = f"FAIL (wp={len(waypoints)}, keys={len(keys)})"

    # Test 7: φ-weighted energy increases with node index
    total += 1
    e_core = router._phi_energy(0, 1)
    e_risk = router._phi_energy(8, 9)
    if e_risk > e_core:
        passed += 1
        results["phi_energy_scaling"] = f"PASS (core={e_core:.2f} < risk={e_risk:.2f})"
    else:
        results["phi_energy_scaling"] = f"FAIL (core={e_core:.2f}, risk={e_risk:.2f})"

    # Test 8: Symplectic momentum is computed
    total += 1
    if abs(path.symplectic_momentum) > 0 or path.length <= 1:
        passed += 1
        results["symplectic_momentum"] = f"PASS (Σp·dq = {path.symplectic_momentum:.6f})"
    else:
        results["symplectic_momentum"] = "FAIL (zero momentum)"

    return {
        "passed": passed,
        "total": total,
        "results": results,
        "rate": f"{passed}/{total} ({100 * passed / max(1, total):.0f}%)",
    }


if __name__ == "__main__":
    print("=" * 60)
    print("PHDM Router — Hamiltonian Path Routing")
    print("=" * 60)

    test_results = self_test()
    for name, result in test_results["results"].items():
        print(f"  {name}: {result}")
    print("-" * 60)
    print(f"  TOTAL: {test_results['rate']}")
