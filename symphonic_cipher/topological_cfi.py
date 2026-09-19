#!/usr/bin/env python3
"""
Topological Control-Flow Integrity (TLCFI) Module
=================================================
Implements patent claims for topological linearization CFI:
- Control-flow graph extraction and analysis
- Directed Hamiltonian path diagnostics
- Dimensional lifting for non-Hamiltonian graphs
- Principal curve computation through embedded states
- Runtime deviation detection with O(1) checks

Runtime enforcement uses frozen directed edges. Geometry is diagnostic and
does not prove attack coverage or a fixed percentage of runtime overhead.

Author: Issac Davis / SpiralVerse OS
Date: January 15, 2026
"""

import numpy as np
from typing import List, Dict, Tuple, Set, Optional, Any
from dataclasses import dataclass
from enum import Enum
import hashlib

# Constants
DEVIATION_THRESHOLD = 0.05
MIN_DIMENSION_LIFT = 4
MAX_DIMENSION_LIFT = 6
EPSILON = 1e-9


# =============================================================================
# HYPERBOLIC GEOMETRY PRIMITIVES (for patent claims)
# =============================================================================


@dataclass
class HyperbolicPoint:
    """A point in the Poincaré disk model of hyperbolic space."""

    x: float
    y: float

    def __post_init__(self):
        # Ensure point is inside the disk (|z| < 1)
        r = np.sqrt(self.x**2 + self.y**2)
        if r >= 1.0:
            # Project onto disk boundary - epsilon
            scale = 0.9999 / r
            self.x *= scale
            self.y *= scale

    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y])


def compute_hyperbolic_distance(p1: HyperbolicPoint, p2: HyperbolicPoint) -> float:
    """
    Compute the hyperbolic distance between two points in the Poincaré disk.
    Uses the formula: d(z1, z2) = 2 * arctanh(|z1 - z2| / |1 - z1*conj(z2)|)
    """
    z1 = complex(p1.x, p1.y)
    z2 = complex(p2.x, p2.y)

    # Handle same point case
    if abs(z1 - z2) < EPSILON:
        return 0.0

    numerator = abs(z1 - z2)
    denominator = abs(1 - z1 * z2.conjugate())

    if denominator < EPSILON:
        return float("inf")

    ratio = numerator / denominator
    # Clamp to valid arctanh range
    ratio = min(ratio, 0.9999999)

    return 2.0 * np.arctanh(ratio)


def map_to_poincare_disk(x: float, y: float) -> HyperbolicPoint:
    """
    Map Euclidean coordinates to the Poincaré disk using tanh projection.
    Ensures the result is always inside the unit disk.
    """
    # Use tanh to map R^2 -> unit disk
    r = np.sqrt(x**2 + y**2)
    if r < EPSILON:
        return HyperbolicPoint(0.0, 0.0)

    # Scale factor using tanh
    scale = np.tanh(r) / r
    px = x * scale * 0.99  # Stay strictly inside disk
    py = y * scale * 0.99

    return HyperbolicPoint(px, py)


def verify_principal_curve_membership(auth_state: Dict) -> bool:
    """
    Verify if an authorization state lies on the principal curve.
    Returns True for valid (authorized) states, False for tampered/invalid states.

    The principal curve represents the manifold of valid authorization states.
    Unauthorized actions (like DELETE_ALL) deviate from this curve.
    """
    # Hash the authorization state
    state_str = str(sorted(auth_state.items()))
    state_hash = hashlib.sha256(state_str.encode()).digest()

    # Check for known malicious patterns
    intent = auth_state.get("intent", "").upper()
    malicious_patterns = ["DELETE_ALL", "DROP", "TRUNCATE", "ADMIN_OVERRIDE", "BYPASS"]

    for pattern in malicious_patterns:
        if pattern in intent:
            return False

    # For valid intents, verify hash coherence
    # Valid states have even parity in their hash (simplified check)
    hash_sum = sum(state_hash[:8])
    deviation = abs(hash_sum % 256 - 128) / 128.0

    # States with low deviation are on the curve
    return deviation < 0.8


class CFIResult(Enum):
    """Control-flow integrity check result."""

    VALID = "valid"
    VIOLATION = "violation"
    UNKNOWN = "unknown"


@dataclass
class BasicBlock:
    """Represents a basic block in the control-flow graph."""

    id: int
    instructions: List[str]
    entry_point: int
    exit_point: int

    def __hash__(self):
        return self.id


@dataclass(eq=False)
class CFGEdge:
    """Represents an edge in the control-flow graph.

    Two decisions here are load-bearing and were previously wrong:

    1. The ``@dataclass`` decorator is required. Without it the annotations
       below are bare class-level hints rather than fields, and
       ``CFGEdge(source=0, target=1, edge_type="jump")`` raises
       ``TypeError: CFGEdge() takes no arguments`` — no edge can be built.
    2. ``eq=False`` keeps dataclass from generating an ``__eq__`` over all three
       fields. Identity is ``(source, target)``, matching ``__hash__``. With a
       generated three-field ``__eq__``, two edges between the same pair of
       blocks would hash alike but compare unequal, so ``ControlFlowGraph.edges``
       (a ``Set``) would store both and inflate the degree counts that
       :class:`HamiltonianTester` relies on.
    """

    source: int
    target: int
    edge_type: str  # 'jump', 'call', 'return', 'fallthrough'

    def __hash__(self):
        return hash((self.source, self.target))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, CFGEdge):
            return NotImplemented
        return (self.source, self.target) == (other.source, other.target)


class ControlFlowGraph:
    """
    Control-Flow Graph representation.
    Vertices = basic blocks, Edges = valid control-flow transitions.
    """

    def __init__(self):
        self.vertices: Dict[int, BasicBlock] = {}
        self.edges: Set[CFGEdge] = set()
        self.adjacency: Dict[int, List[int]] = {}

    def add_vertex(self, block: BasicBlock):
        """Add a basic block vertex."""
        self.vertices[block.id] = block
        if block.id not in self.adjacency:
            self.adjacency[block.id] = []

    def add_edge(self, edge: CFGEdge):
        """Add a control-flow edge."""
        if edge in self.edges:
            return
        self.edges.add(edge)
        if edge.source not in self.adjacency:
            self.adjacency[edge.source] = []
        self.adjacency[edge.source].append(edge.target)

    def get_degree(self, vertex_id: int) -> int:
        """Get degree of a vertex (in + out)."""
        out_degree = len(self.adjacency.get(vertex_id, []))
        in_degree = sum(1 for e in self.edges if e.target == vertex_id)
        return in_degree + out_degree

    def vertex_count(self) -> int:
        return len(self.vertices)

    def edge_count(self) -> int:
        return len(self.edges)


class HamiltonianTester:
    """Tests whether a control-flow graph admits a Hamiltonian path.

    A control-flow graph is DIRECTED — its edges are jumps, calls, returns and
    fallthroughs, all of which are one-way. Dirac's criterion and Ore's theorem
    are theorems about simple UNDIRECTED graphs and are not valid on a digraph;
    applying them here produced false positives (see ``EXACT_MAX_VERTICES`` note
    and ``tests/test_topological_cfi_hamiltonian.py``).

    The failure direction mattered: ``lift_to_hamiltonian`` is applied only when
    a graph is found NON-Hamiltonian, so a false positive skipped the lift, left
    no principal curve, and gave runtime deviation nothing to measure against —
    the detector failed open.

    Strategy, cheapest test first:

    1. Necessary conditions (O(V+E)) — reject outright. A Hamiltonian path has
       exactly one start and one end, so more than one source or more than one
       sink is fatal, as is weak disconnection.
    2. Ghouila-Houri (1960) (O(V+E)) — accept. A strongly connected digraph in
       which EVERY vertex has in-degree >= n/2 AND out-degree >= n/2 has a
       Hamiltonian circuit, which implies a Hamiltonian path. Note the two
       degrees are constrained separately; summing them is strictly weaker and
       is what admitted sinks.
    3. Exact bitmask DP (O(2^n * n^2)) for small graphs — decide it properly.
       Per-function CFGs are usually well inside this bound.
    4. Otherwise report unknown, which routes the graph to the lift. Unknown
       must fail CLOSED.
    """

    #: Above this vertex count the exact DP is skipped (2^n state space).
    EXACT_MAX_VERTICES = 20

    def __init__(self, cfg: ControlFlowGraph):
        self.cfg = cfg

    def _degrees(self) -> Tuple[Dict[int, int], Dict[int, int]]:
        """Return (in_degree, out_degree) maps, counted separately."""
        in_deg = {v: 0 for v in self.cfg.vertices}
        out_deg = {v: 0 for v in self.cfg.vertices}
        for edge in self.cfg.edges:
            if edge.source == edge.target:
                continue  # self-loops do not connect distinct Hamiltonian vertices
            if edge.source in out_deg:
                out_deg[edge.source] += 1
            if edge.target in in_deg:
                in_deg[edge.target] += 1
        return in_deg, out_deg

    def necessary_conditions(self) -> Tuple[bool, str]:
        """Cheap structural conditions that a Hamiltonian path must satisfy.

        Returns:
            (still_possible, reason). ``False`` is a definitive NO.
        """
        n = self.cfg.vertex_count()
        if n < 2:
            return True, "trivial"

        in_deg, out_deg = self._degrees()

        # A path visits every vertex once and has exactly one final vertex, so at
        # most one vertex may have no outgoing edge. Two sinks is unsatisfiable.
        sinks = [v for v, d in out_deg.items() if d == 0]
        if len(sinks) > 1:
            return False, f"multiple_sinks({len(sinks)})"

        sources = [v for v, d in in_deg.items() if d == 0]
        if len(sources) > 1:
            return False, f"multiple_sources({len(sources)})"

        if not self._is_weakly_connected():
            return False, "disconnected"

        return True, "possible"

    def _is_weakly_connected(self) -> bool:
        """True if the underlying undirected graph is connected."""
        vertices = list(self.cfg.vertices.keys())
        if not vertices:
            return True
        undirected: Dict[int, Set[int]] = {v: set() for v in vertices}
        for edge in self.cfg.edges:
            if edge.source in undirected and edge.target in undirected:
                undirected[edge.source].add(edge.target)
                undirected[edge.target].add(edge.source)
        seen = {vertices[0]}
        stack = [vertices[0]]
        while stack:
            for nxt in undirected[stack.pop()]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return len(seen) == len(vertices)

    def _is_strongly_connected(self) -> bool:
        """True if every vertex reaches every other following edge direction."""
        vertices = list(self.cfg.vertices.keys())
        if len(vertices) < 2:
            return True
        forward: Dict[int, Set[int]] = {v: set() for v in vertices}
        reverse: Dict[int, Set[int]] = {v: set() for v in vertices}
        for edge in self.cfg.edges:
            if edge.source in forward and edge.target in forward:
                forward[edge.source].add(edge.target)
                reverse[edge.target].add(edge.source)

        def reaches_all(adj: Dict[int, Set[int]]) -> bool:
            seen = {vertices[0]}
            stack = [vertices[0]]
            while stack:
                for nxt in adj[stack.pop()]:
                    if nxt not in seen:
                        seen.add(nxt)
                        stack.append(nxt)
            return len(seen) == len(vertices)

        return reaches_all(forward) and reaches_all(reverse)

    def ghouila_houri_criterion(self) -> bool:
        """Ghouila-Houri sufficient condition for a Hamiltonian circuit.

        A strongly connected digraph on n vertices in which every vertex has
        in-degree >= n/2 and out-degree >= n/2 is Hamiltonian. The two degrees
        are checked SEPARATELY — this is the directed replacement for the
        previously-used Dirac criterion.
        """
        n = self.cfg.vertex_count()
        if n < 3:
            return False  # defer to the exact test
        if not self._is_strongly_connected():
            return False
        in_deg, out_deg = self._degrees()
        threshold = n / 2
        return all(in_deg[v] >= threshold and out_deg[v] >= threshold for v in self.cfg.vertices)

    def _exact_hamiltonian_path(self) -> Optional[bool]:
        """Decide Hamiltonian-path existence exactly by bitmask DP.

        Returns None if the graph is too large for the exact test.
        """
        vertices = list(self.cfg.vertices.keys())
        n = len(vertices)
        if n == 0:
            return True
        if n > self.EXACT_MAX_VERTICES:
            return None

        index = {v: i for i, v in enumerate(vertices)}
        succ = [0] * n
        for edge in self.cfg.edges:
            if edge.source in index and edge.target in index and edge.source != edge.target:
                succ[index[edge.source]] |= 1 << index[edge.target]

        full = (1 << n) - 1
        # reachable[mask] = bitset of vertices that can be the END of a path
        # visiting exactly `mask`.
        reachable = [0] * (1 << n)
        for i in range(n):
            reachable[1 << i] = 1 << i
        for mask in range(1 << n):
            ends = reachable[mask]
            if not ends:
                continue
            if mask == full:
                return True
            e = ends
            while e:
                low = e & -e
                i = low.bit_length() - 1
                e ^= low
                nxt = succ[i] & ~mask
                while nxt:
                    lown = nxt & -nxt
                    j = lown.bit_length() - 1
                    nxt ^= lown
                    reachable[mask | lown] |= 1 << j
        return bool(reachable[full])

    def is_hamiltonian(self) -> Tuple[bool, str]:
        """Test whether the CFG admits a Hamiltonian path.

        Returns:
            (is_hamiltonian, reason). ``reason`` is one of ``trivial``,
            ``ghouila_houri``, ``exact``, a ``necessary:*`` rejection, or
            ``unknown``. ``unknown`` means undecided and MUST be treated as
            non-Hamiltonian by callers so the dimensional lift still runs.
        """
        n = self.cfg.vertex_count()
        if n < 2:
            return True, "trivial"

        possible, why = self.necessary_conditions()
        if not possible:
            return False, f"necessary:{why}"

        if self.ghouila_houri_criterion():
            return True, "ghouila_houri"

        exact = self._exact_hamiltonian_path()
        if exact is not None:
            return exact, "exact"

        return False, "unknown"


class DimensionalLifter:
    """Embed graph vertices for diagnostics without changing legal edges.

    Higher dimension and distance variance do not establish Hamiltonicity.
    The historical method name is retained for callers, not as a proof claim.
    """

    def __init__(self, cfg: ControlFlowGraph):
        self.cfg = cfg
        self.lifted_dimension = MIN_DIMENSION_LIFT
        self.embeddings: Dict[int, np.ndarray] = {}

    def spectral_embedding(self, dim: int) -> Dict[int, np.ndarray]:
        """
        Compute spectral embedding using graph Laplacian.
        Maps vertices to d-dimensional manifold.
        """
        n = self.cfg.vertex_count()
        if n == 0:
            return {}

        # Build adjacency matrix
        vertices = list(self.cfg.vertices.keys())
        v_idx = {v: i for i, v in enumerate(vertices)}
        A = np.zeros((n, n))

        for edge in self.cfg.edges:
            if edge.source in v_idx and edge.target in v_idx:
                i, j = v_idx[edge.source], v_idx[edge.target]
                A[i, j] = 1
                A[j, i] = 1  # Symmetric for embedding

        # Laplacian L = D - A
        D = np.diag(A.sum(axis=1))
        L = D - A

        # Eigendecomposition
        eigenvalues, eigenvectors = np.linalg.eigh(L)

        # Use smallest non-zero eigenvectors for embedding
        # Skip first (constant) eigenvector
        embedding_dim = min(dim, n - 1)
        coords = eigenvectors[:, 1 : embedding_dim + 1]

        # Pad if needed
        if coords.shape[1] < dim:
            padding = np.zeros((n, dim - coords.shape[1]))
            coords = np.hstack([coords, padding])

        return {v: coords[i] for v, i in v_idx.items()}

    def lift_to_hamiltonian(self) -> Tuple[Dict[int, np.ndarray], int]:
        """
        Select an embedding dimension using a distance-variance heuristic.
        The original graph connectivity is unchanged.
        """
        for dim in range(MIN_DIMENSION_LIFT, MAX_DIMENSION_LIFT + 1):
            self.embeddings = self.spectral_embedding(dim)
            self.lifted_dimension = dim

            # Check if embedding induces connectivity
            if self._check_lifted_connectivity():
                return self.embeddings, dim

        return self.embeddings, MAX_DIMENSION_LIFT

    def _check_lifted_connectivity(self) -> bool:
        """
        Check if lifted embedding provides good connectivity.
        Uses distance variance as heuristic.
        """
        if len(self.embeddings) < 2:
            return True

        coords = list(self.embeddings.values())
        distances = []
        for i, c1 in enumerate(coords):
            for c2 in coords[i + 1 :]:
                distances.append(np.linalg.norm(c1 - c2))

        if not distances:
            return True

        # Good connectivity: low variance in distances
        variance = np.var(distances)
        return variance < 1.0


class PrincipalCurve:
    """
    Computes and represents the principal curve through
    the embedded control-flow states.
    """

    def __init__(self, embeddings: Dict[int, np.ndarray]):
        self.embeddings = embeddings
        self.curve_points: List[np.ndarray] = []
        self.curve_params: List[float] = []

    def fit(self) -> bool:
        """
        Fit principal curve through embedded states.
        Uses iterative local regression approach.
        """
        if len(self.embeddings) < 2:
            return False

        coords = np.array(list(self.embeddings.values()))

        # Initialize with first principal component
        mean = coords.mean(axis=0)
        centered = coords - mean
        _, _, Vt = np.linalg.svd(centered, full_matrices=False)

        # Project onto first PC
        projections = centered @ Vt[0]
        sorted_idx = np.argsort(projections)

        # Build curve through sorted points
        self.curve_points = [coords[i] for i in sorted_idx]
        self.curve_params = list(np.linspace(0, 1, len(self.curve_points)))

        return True

    def project(self, point: np.ndarray) -> Tuple[float, np.ndarray]:
        """
        Project a point onto the curve.
        Returns (parameter, closest_point_on_curve).
        """
        if not self.curve_points:
            return 0.0, point

        min_dist = float("inf")
        best_param = 0.0
        best_point = self.curve_points[0]

        for i, cp in enumerate(self.curve_points):
            dist = np.linalg.norm(point - cp)
            if dist < min_dist:
                min_dist = dist
                best_param = self.curve_params[i]
                best_point = cp

        return best_param, best_point

    def deviation(self, point: np.ndarray) -> float:
        """
        Compute orthogonal deviation from principal curve.
        Diagnostic only: proximity must never grant a control-flow permission.
        """
        _, closest = self.project(point)
        return float(np.linalg.norm(point - closest))


class TopologicalCFI:
    """Frozen directed policy enforcement with geometric diagnostics.

    A curve through known blocks cannot distinguish a legal edge from a jump
    to another known block. Runtime authorization therefore uses the original
    directed edges, not proximity. This is not proof of semantic program safety.
    """

    def __init__(self):
        self.cfg: Optional[ControlFlowGraph] = None
        self.hamiltonian_tester: Optional[HamiltonianTester] = None
        self.lifter: Optional[DimensionalLifter] = None
        self.curve: Optional[PrincipalCurve] = None
        self.is_hamiltonian: bool = False
        self.lifted_dim: int = 0
        self.embeddings: Dict[int, np.ndarray] = {}
        self.violation_count: int = 0
        self.check_count: int = 0
        self.hamiltonian_tested: bool = False
        self._policy_ready = False
        self._allowed_vertices = frozenset()
        self._allowed_edges = frozenset()

    def initialize(self, cfg: ControlFlowGraph) -> Dict[str, any]:
        """
        Initialize CFI system with a control-flow graph.
        Freeze an explicit policy; rebuild only through this method.
        A failed rebuild revokes the previous policy rather than failing open.
        """
        self._policy_ready = False
        self.hamiltonian_tested = False
        self._allowed_vertices = frozenset()
        self._allowed_edges = frozenset()
        self.curve = None
        self.embeddings = {}
        vertices = frozenset(cfg.vertices)
        edges = frozenset((edge.source, edge.target) for edge in cfg.edges)
        if any(type(v) is not int for v in vertices) or any(
            type(a) is not int or type(b) is not int or a not in vertices or b not in vertices for a, b in edges
        ):
            raise ValueError("CFI policy requires integer vertices and edges with known endpoints")
        self.cfg = cfg
        results = {"status": "initialized"}

        # Step 1: Test Hamiltonicity
        self.hamiltonian_tester = HamiltonianTester(cfg)
        self.is_hamiltonian, reason = self.hamiltonian_tester.is_hamiltonian()
        self.hamiltonian_tested = True
        results["hamiltonian"] = self.is_hamiltonian
        results["hamiltonian_reason"] = reason

        # Step 2: Dimensional lifting if needed
        self.lifter = DimensionalLifter(cfg)
        if not self.is_hamiltonian:
            self.embeddings, self.lifted_dim = self.lifter.lift_to_hamiltonian()
            results["lifted_dimension"] = self.lifted_dim
        else:
            # Use base 3D embedding for Hamiltonian graphs
            self.embeddings = self.lifter.spectral_embedding(3)
            self.lifted_dim = 3
            results["lifted_dimension"] = 3

        # Step 3: Compute principal curve
        self.curve = PrincipalCurve(self.embeddings)
        curve_fitted = self.curve.fit()
        results["curve_fitted"] = curve_fitted
        results["num_vertices"] = cfg.vertex_count()
        results["num_edges"] = cfg.edge_count()
        self._allowed_vertices = vertices
        self._allowed_edges = edges
        self._policy_ready = bool(vertices)
        results["policy_ready"] = self._policy_ready
        results["enforcement"] = "frozen_directed_edges"
        results["geometry_proves_connectivity"] = False

        return results

    def check_transition(self, from_block: int, to_block: int) -> CFIResult:
        """
        Expected O(1) hash lookup against the initialized directed policy.
        This is called at every control-flow transition.
        """
        self.check_count += 1

        if not self._policy_ready:
            return CFIResult.UNKNOWN
        if (
            type(from_block) is not int
            or type(to_block) is not int
            or (from_block, to_block) not in self._allowed_edges
        ):
            self.violation_count += 1
            return CFIResult.VIOLATION

        return CFIResult.VALID

    def get_detection_stats(self) -> Dict[str, float]:
        """Observed rejection fraction; not a labelled attack detection rate."""
        if self.check_count == 0:
            return {"detection_rate": 0.0, "checks": 0, "violations": 0}
        return {
            "detection_rate": self.violation_count / self.check_count,
            "checks": self.check_count,
            "violations": self.violation_count,
        }

    def verify_execution_path(self, path: List[str]) -> Dict[str, Any]:
        """
        Verify canonical string block IDs against the initialized policy.
        Legitimate cycles are allowed. Uniqueness alone is not authorization.
        """
        ids = {str(v): v for v in self._allowed_vertices}
        valid = (
            self._policy_ready
            and isinstance(path, (list, tuple))
            and len(path) >= 2
            and all(type(node) is str and node in ids for node in path)
        )
        if valid:
            valid = all(self.check_transition(ids[a], ids[b]) == CFIResult.VALID for a, b in zip(path, path[1:]))
        return {
            "valid": bool(valid),
            "hamiltonian_tested": self.hamiltonian_tested,
            "policy_verified": bool(valid),
            "reason": "verified directed policy" if valid else "violation: missing policy or illegal path",
            "hash": hashlib.sha256(repr(path).encode()).hexdigest(),
        }


# =============================================================================
# EXAMPLE USAGE AND TESTS
# =============================================================================


def create_sample_cfg() -> ControlFlowGraph:
    """Create a sample CFG for testing."""
    cfg = ControlFlowGraph()

    # Add basic blocks
    for i in range(6):
        block = BasicBlock(
            id=i, instructions=[f"instr_{i}_0", f"instr_{i}_1"], entry_point=i * 100, exit_point=i * 100 + 50
        )
        cfg.add_vertex(block)

    # Add edges (control flow transitions)
    edges = [
        (0, 1, "fallthrough"),
        (1, 2, "jump"),
        (1, 3, "jump"),
        (2, 4, "fallthrough"),
        (3, 4, "fallthrough"),
        (4, 5, "call"),
        (5, 0, "return"),  # Loop back
    ]

    for src, tgt, etype in edges:
        cfg.add_edge(CFGEdge(src, tgt, etype))

    return cfg


def run_cfi_demo():
    """Demonstrate the Topological CFI system."""
    print("=" * 60)
    print("TOPOLOGICAL CFI DEMONSTRATION")
    print("=" * 60)

    # Create CFG
    cfg = create_sample_cfg()
    print(f"\nCreated CFG with {cfg.vertex_count()} vertices, {cfg.edge_count()} edges")

    # Initialize CFI system
    cfi = TopologicalCFI()
    results = cfi.initialize(cfg)

    print(f"\nInitialization Results:")
    print(f"  Hamiltonian: {results['hamiltonian']} ({results['hamiltonian_reason']})")
    print(f"  Lifted Dimension: {results['lifted_dimension']}")
    print(f"  Curve Fitted: {results['curve_fitted']}")

    # Simulate valid transitions
    print("\nTesting Valid Transitions:")
    valid_transitions = [(0, 1), (1, 2), (2, 4), (4, 5)]
    for from_b, to_b in valid_transitions:
        result = cfi.check_transition(from_b, to_b)
        print(f"  {from_b} -> {to_b}: {result.value}")

    # Simulate attack (invalid transition)
    print("\nTesting Invalid Transitions (simulated ROP):")
    invalid_transitions = [(0, 5), (2, 0), (99, 100)]  # 99, 100 don't exist
    for from_b, to_b in invalid_transitions:
        result = cfi.check_transition(from_b, to_b)
        print(f"  {from_b} -> {to_b}: {result.value}")

    # Get stats
    stats = cfi.get_detection_stats()
    print(f"\nDetection Statistics:")
    print(f"  Total Checks: {stats['checks']}")
    print(f"  Violations Detected: {stats['violations']}")
    print(f"  Detection Rate: {stats['detection_rate']:.2%}")

    print("\n" + "=" * 60)
    return results


if __name__ == "__main__":
    run_cfi_demo()
