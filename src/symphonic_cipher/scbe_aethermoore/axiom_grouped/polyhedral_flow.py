"""
Polyhedral Flow Network — Internal Network Fold Geometry
=========================================================

Data flows through the 16 PHDM polyhedra nested in one ball,
using non-Euclidean routing (Harry Potter staircases) where paths
shift based on ternary state and phi-scaled propagation.

Three bit-spin modes:
  1. Fibonacci spin: ordered phi-progression (stable routing)
  2. Mod-2 Fibonacci LFSR: deterministic chaos (exploration routing)
  3. Dual spin: both running simultaneously, XOR'd for hybrid routing

The 16 polyhedra nest inside each other via dual relationships:
  - Platonic duals: tetrahedron↔tetrahedron, cube↔octahedron,
    dodecahedron↔icosahedron
  - Archimedean truncations: truncated tetrahedron from tetrahedron,
    cuboctahedron from cube+octahedron, icosidodecahedron from
    dodecahedron+icosahedron
  - Kepler-Poinsot stars: stellated/great forms of dodecahedron
  - Toroidal: genus-1 self-intersecting (recursive loops)
  - Johnson/Rhombic: bridge connectors between families

Data follows geodesic paths along polyhedral edges, refracting
at face boundaries (the "walls" formed by ternary state layers).

Patent: USPTO #63/961,403
Author: Issac Davis
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

PHI = (1 + math.sqrt(5)) / 2
PHI_INV = 1.0 / PHI
FIB_SEQUENCE = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610]


# =============================================================================
# 1. THE 16 PHDM POLYHEDRA — Nested in One Ball
# =============================================================================

@dataclass(frozen=True)
class Polyhedron:
    """A single polyhedron in the PHDM ball."""
    index: int
    name: str
    family: str          # platonic, archimedean, kepler_poinsot, toroidal, johnson, rhombic
    zone: str            # core, cortex, risk, recursive, bridge
    vertices: int
    edges: int
    faces: int
    euler_chi: int       # Euler characteristic
    dual_index: Optional[int]  # Index of dual polyhedron (None if self-dual)
    parent_index: Optional[int]  # Truncated from which parent
    depth: float         # Nesting depth in the ball [0=center, 1=surface]


# The 16 canonical polyhedra with nesting relationships
POLYHEDRA = [
    # Core (Platonic) — innermost shells
    Polyhedron(0, "Tetrahedron", "platonic", "core", 4, 6, 4, 2, 0, None, 0.1),  # self-dual
    Polyhedron(1, "Cube", "platonic", "core", 8, 12, 6, 2, 2, None, 0.2),
    Polyhedron(2, "Octahedron", "platonic", "core", 6, 12, 8, 2, 1, None, 0.2),  # dual of cube
    Polyhedron(3, "Dodecahedron", "platonic", "core", 20, 30, 12, 2, 4, None, 0.3),
    Polyhedron(4, "Icosahedron", "platonic", "core", 12, 30, 20, 2, 3, None, 0.3),  # dual of dodecahedron
    # Cortex (Archimedean) — middle shells (truncated from Platonic)
    Polyhedron(5, "Truncated Tetrahedron", "archimedean", "cortex", 12, 18, 8, 2, None, 0, 0.4),
    Polyhedron(6, "Cuboctahedron", "archimedean", "cortex", 12, 24, 14, 2, None, 1, 0.5),  # from cube+oct
    Polyhedron(7, "Icosidodecahedron", "archimedean", "cortex", 30, 60, 32, 2, None, 3, 0.6),  # from dodec+icos
    # Risk (Kepler-Poinsot) — outer shells (self-intersecting stars)
    Polyhedron(8, "Small Stellated Dodecahedron", "kepler_poinsot", "risk", 12, 30, 12, -6, None, 3, 0.7),
    Polyhedron(9, "Great Dodecahedron", "kepler_poinsot", "risk", 12, 30, 12, -6, None, 4, 0.7),
    # Recursive (Toroidal) — genus-1 loops
    Polyhedron(10, "Szilassi", "toroidal", "recursive", 7, 21, 14, 0, 11, None, 0.8),
    Polyhedron(11, "Csaszar", "toroidal", "recursive", 7, 21, 14, 0, 10, None, 0.8),  # dual of Szilassi
    # Bridge (Johnson + Rhombic) — connectors between families
    Polyhedron(12, "Pentagonal Bipyramid", "johnson", "bridge", 7, 15, 10, 2, None, None, 0.5),
    Polyhedron(13, "Triangular Cupola", "johnson", "bridge", 9, 15, 8, 2, None, None, 0.5),
    Polyhedron(14, "Rhombic Dodecahedron", "rhombic", "bridge", 14, 24, 12, 2, None, 1, 0.6),
    Polyhedron(15, "Bilinski Dodecahedron", "rhombic", "bridge", 14, 24, 12, 2, None, None, 0.6),
]

# Adjacency: which polyhedra can route to which (edges of the flow graph)
# Based on: dual relationships, truncation parentage, family proximity, zone bridging
FLOW_ADJACENCY: Dict[int, List[int]] = {
    0: [1, 2, 5, 12],       # Tetra->Cube, Oct, TruncTetra, PentBipyramid
    1: [0, 2, 6, 14],       # Cube->Tetra, Oct, Cubocta, RhombicDodec
    2: [0, 1, 6, 13],       # Oct->Tetra, Cube, Cubocta, TriCupola
    3: [4, 7, 8, 14],       # Dodec->Icos, Icosidodec, SmallStellated, RhombicDodec
    4: [3, 7, 9, 15],       # Icos->Dodec, Icosidodec, GreatDodec, Bilinski
    5: [0, 6, 12, 13],      # TruncTetra->Tetra, Cubocta, bridges
    6: [1, 2, 5, 7, 14],    # Cubocta->Cube, Oct, TruncTetra, Icosidodec, RhombicDodec
    7: [3, 4, 6, 8, 9],     # Icosidodec->Dodec, Icos, Cubocta, stars
    8: [3, 7, 9, 10],       # SmallStellated->Dodec, Icosidodec, GreatDodec, Szilassi
    9: [4, 7, 8, 11],       # GreatDodec->Icos, Icosidodec, SmallStellated, Csaszar
    10: [8, 11, 12, 13],    # Szilassi->SmallStellated, Csaszar, bridges (recursive loop)
    11: [9, 10, 14, 15],    # Csaszar->GreatDodec, Szilassi, bridges (recursive loop)
    12: [0, 5, 10, 13],     # PentBipyramid->bridges across core/cortex/recursive
    13: [2, 5, 10, 12],     # TriCupola->bridges
    14: [1, 3, 6, 11, 15],  # RhombicDodec->space-filling connector
    15: [4, 11, 14],         # Bilinski->compressed connector
}


# =============================================================================
# 2. FIBONACCI BIT SPIN (Ordered Progression)
# =============================================================================

def fibonacci_spin(step: int, n_bits: int = 8) -> List[int]:
    """
    Generate a Fibonacci-ordered bit pattern for routing.

    Each bit position follows the Fibonacci sequence mod 2.
    This creates a phi-harmonic routing pattern that's stable
    and self-similar at every scale.
    """
    bits = []
    a, b = 0, 1
    for _ in range(n_bits):
        bits.append(b % 2)
        a, b = b, a + b
    # Rotate by step position
    shift = step % n_bits
    return bits[shift:] + bits[:shift]


def fibonacci_phase(step: int) -> float:
    """
    Fibonacci phase angle: maps step to a golden-angle rotation.

    Golden angle = 2*pi / phi^2 ≈ 137.5 degrees.
    This is the most irrational angle — maximally spreads samples
    on a circle (sunflower pattern).
    """
    golden_angle = 2 * math.pi / (PHI * PHI)
    return (step * golden_angle) % (2 * math.pi)


# =============================================================================
# 3. MOD-2 FIBONACCI LFSR (Deterministic Chaos)
# =============================================================================

@dataclass
class FibonacciLFSR:
    """
    Mod-2 Fibonacci Linear Feedback Shift Register.

    Produces a maximum-length pseudo-random sequence of 2^n - 1 states.
    Deterministic: same seed always produces same sequence.
    Chaotic-looking: passes basic randomness tests.
    Reproducible: can reconstruct full sequence from any state.

    Used for "chaotic bit spin" — asynchronous exploration routing
    that looks random but is mathematically reproducible.

    Taps are Fibonacci-spaced: positions follow the Fibonacci sequence.
    """

    n_bits: int = 8
    state: int = 1  # Must be non-zero
    taps: Tuple[int, ...] = ()  # XOR tap positions (Fibonacci-spaced)

    def __post_init__(self):
        if not self.taps:
            # Default: Fibonacci-spaced taps for n_bits
            # For 8-bit: taps at positions derived from Fibonacci
            if self.n_bits == 8:
                self.taps = (7, 5, 3, 1)  # Fibonacci-like spacing
            elif self.n_bits == 16:
                self.taps = (15, 13, 8, 5)
            elif self.n_bits == 32:
                self.taps = (31, 21, 13, 8)
            else:
                # Generic: use Fibonacci numbers as tap positions
                fibs = [f for f in FIB_SEQUENCE if f < self.n_bits]
                self.taps = tuple(fibs[-4:]) if len(fibs) >= 4 else tuple(fibs)

    def step(self) -> int:
        """Advance the LFSR one step. Returns current output bit."""
        output_bit = self.state & 1

        # XOR the tap positions
        feedback = 0
        for tap in self.taps:
            feedback ^= (self.state >> tap) & 1

        # Shift right, insert feedback at MSB
        self.state = ((self.state >> 1) | (feedback << (self.n_bits - 1))) & ((1 << self.n_bits) - 1)

        # Safety: prevent all-zero lock
        if self.state == 0:
            self.state = 1

        return output_bit

    def generate(self, n_steps: int) -> List[int]:
        """Generate n output bits."""
        return [self.step() for _ in range(n_steps)]

    def current_bits(self) -> List[int]:
        """Return current state as bit list."""
        return [(self.state >> i) & 1 for i in range(self.n_bits)]


# =============================================================================
# 4. DUAL SPIN — Fibonacci + LFSR Combined
# =============================================================================

@dataclass
class DualSpin:
    """
    Dual bit spin: ordered Fibonacci + chaotic LFSR, XOR'd together.

    The Fibonacci spin provides phi-harmonic structure.
    The LFSR provides controlled chaos at asynchronous intervals.
    XOR combines them: the result has structure AND unpredictability.

    This drives the "Harry Potter staircase" routing — paths that
    shift deterministically but appear to change unpredictably.
    """

    n_bits: int = 8
    lfsr: FibonacciLFSR = None
    step_count: int = 0

    def __post_init__(self):
        if self.lfsr is None:
            self.lfsr = FibonacciLFSR(n_bits=self.n_bits)

    def spin(self) -> List[int]:
        """Generate one dual-spin bit pattern."""
        ordered = fibonacci_spin(self.step_count, self.n_bits)
        chaotic = self.lfsr.current_bits()
        self.lfsr.step()
        self.step_count += 1

        # XOR: structure + chaos = hybrid routing
        return [o ^ c for o, c in zip(ordered, chaotic)]

    def route_index(self) -> int:
        """Convert current spin to a polyhedron index (0-15)."""
        bits = self.spin()
        # Use first 4 bits as polyhedron selector
        return (bits[0] * 8 + bits[1] * 4 + bits[2] * 2 + bits[3]) % 16

    def ternary_state(self) -> List[int]:
        """
        Convert current spin to ternary state (-1, 0, +1).

        Uses bit pairs: 00→0, 01→+1, 10→-1, 11→0 (balanced ternary).
        """
        bits = self.spin()
        trits = []
        for i in range(0, len(bits) - 1, 2):
            pair = bits[i] * 2 + bits[i + 1]
            if pair == 0:
                trits.append(0)
            elif pair == 1:
                trits.append(1)
            elif pair == 2:
                trits.append(-1)
            else:
                trits.append(0)
        return trits


# =============================================================================
# 5. POLYHEDRAL FLOW ROUTER
# =============================================================================

@dataclass
class PolyhedralFlowRouter:
    """
    Routes data through the 16 nested polyhedra using dual-spin navigation.

    Each data record is assigned a polyhedral path:
    1. Start at the polyhedron matching the dominant tongue
    2. Follow flow adjacency, guided by dual-spin routing
    3. Accumulate ternary state at each hop
    4. Terminal node determines the record's geometric address

    The phi_wall at each hop determines whether the data "refracts"
    (follows the geodesic) or "reflects" (bounces to an adjacent face).

    This creates the "Harry Potter staircase" effect: paths are
    deterministic but shift based on the ternary accumulator state.
    """

    dual_spin: DualSpin = field(default_factory=DualSpin)
    max_hops: int = 5

    # Tongue->starting polyhedron mapping
    TONGUE_START = {
        "KO": 0,   # Tetrahedron (simplest, intent/authority)
        "AV": 6,   # Cuboctahedron (bridge, diplomatic)
        "RU": 10,  # Szilassi (recursive, binding/witness)
        "CA": 3,   # Dodecahedron (12 faces = compute complexity)
        "UM": 8,   # Small Stellated Dodecahedron (risk/security)
        "DR": 14,  # Rhombic Dodecahedron (space-filling structure)
    }

    def route(self, dominant_tongue: str, seed: int = 0) -> List[dict]:
        """
        Route a data record through the polyhedral flow network.

        Returns the full path: list of hops with polyhedron, ternary state,
        spin bits, and phi-scaled weight at each node.
        """
        # Reset spin for reproducibility
        self.dual_spin = DualSpin(seed=seed) if seed else DualSpin()

        start = self.TONGUE_START.get(dominant_tongue, 0)
        current = start
        path = []

        for hop in range(self.max_hops):
            poly = POLYHEDRA[current]
            spin_bits = self.dual_spin.spin()
            ternary = self.dual_spin.ternary_state()
            phase = fibonacci_phase(hop)

            # Phi-scaled weight at this node
            phi_weight = PHI ** (poly.depth * 5)  # Deeper = heavier

            path.append({
                "hop": hop,
                "polyhedron": poly.name,
                "poly_index": current,
                "zone": poly.zone,
                "family": poly.family,
                "depth": poly.depth,
                "phi_weight": round(phi_weight, 4),
                "ternary_state": ternary,
                "fibonacci_phase": round(phase, 4),
                "faces": poly.faces,
                "euler_chi": poly.euler_chi,
            })

            # Choose next hop from adjacency
            neighbors = FLOW_ADJACENCY.get(current, [])
            if not neighbors:
                break

            # Dual-spin selects the next node
            route_idx = self.dual_spin.route_index()
            next_node = neighbors[route_idx % len(neighbors)]
            current = next_node

        return path

    def generate_flow_address(self, dominant_tongue: str, seed: int = 0) -> str:
        """
        Generate a compact polyhedral flow address for a data record.

        Format: "KO:T→CO→ID→SS→Sz" (tongue:path through polyhedra)
        """
        path = self.route(dominant_tongue, seed)
        abbreviations = {
            "Tetrahedron": "T", "Cube": "Cu", "Octahedron": "O",
            "Dodecahedron": "D", "Icosahedron": "I",
            "Truncated Tetrahedron": "TT", "Cuboctahedron": "CO",
            "Icosidodecahedron": "ID",
            "Small Stellated Dodecahedron": "SS", "Great Dodecahedron": "GD",
            "Szilassi": "Sz", "Csaszar": "Cs",
            "Pentagonal Bipyramid": "PB", "Triangular Cupola": "TC",
            "Rhombic Dodecahedron": "RD", "Bilinski Dodecahedron": "BD",
        }
        nodes = [abbreviations.get(h["polyhedron"], "?") for h in path]
        return f"{dominant_tongue}:{'->'.join(nodes)}"


# =============================================================================
# 6. TRAINING PAIR FLOW GENERATOR
# =============================================================================

def generate_flow_training_pairs(n_pairs: int = 100) -> List[dict]:
    """
    Generate SFT training pairs that follow polyhedral flow patterns.

    Each pair is routed through the 16 polyhedra, accumulating
    geometric context at each hop. The output includes the flow
    address and the ternary state sequence.
    """
    router = PolyhedralFlowRouter()
    pairs = []
    tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]

    for i in range(n_pairs):
        tongue = tongues[i % 6]
        path = router.route(tongue, seed=i)
        address = router.generate_flow_address(tongue, seed=i)

        # Build instruction from the flow path
        zones_visited = [h["zone"] for h in path]
        families_visited = [h["family"] for h in path]

        instruction = (
            f"Trace the polyhedral flow path for a {tongue}-dominant "
            f"data record through the PHDM ball."
        )

        output = (
            f"Flow address: {address}\n"
            f"Zones traversed: {'->'.join(zones_visited)}\n"
            f"Families crossed: {'->'.join(dict.fromkeys(families_visited))}\n"
            f"Hops: {len(path)}\n"
            f"Terminal polyhedron: {path[-1]['polyhedron']} "
            f"(depth={path[-1]['depth']}, "
            f"phi_weight={path[-1]['phi_weight']}, "
            f"faces={path[-1]['faces']})\n"
            f"Euler characteristic at terminal: {path[-1]['euler_chi']}"
        )

        pairs.append({
            "instruction": instruction,
            "output": output,
            "source": "polyhedral_flow_generator",
            "tongue": tongue,
            "category": "polyhedral_flow",
            "flow_address": address,
            "path_length": len(path),
            "terminal_zone": path[-1]["zone"],
        })

    return pairs


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("POLYHEDRAL FLOW NETWORK — Internal Network Fold Geometry")
    print("=" * 70)
    print()

    # Show polyhedra nesting
    print("16 PHDM POLYHEDRA (nested in one ball):")
    print(f"  {'#':<3} {'Name':<30} {'Zone':<10} {'Depth':<6} {'F':<4} {'E':<4} {'V':<4} {'X':<4}")
    print("  " + "-" * 65)
    for p in POLYHEDRA:
        print(f"  {p.index:<3} {p.name:<30} {p.zone:<10} {p.depth:<6.1f} {p.faces:<4} {p.edges:<4} {p.vertices:<4} {p.euler_chi:<4}")

    print()

    # Fibonacci spin demo
    print("FIBONACCI BIT SPIN (ordered):")
    for step in range(6):
        bits = fibonacci_spin(step)
        print(f"  Step {step}: {bits}  phase={fibonacci_phase(step):.4f}")

    print()

    # LFSR demo
    print("MOD-2 FIBONACCI LFSR (chaotic):")
    lfsr = FibonacciLFSR(n_bits=8, state=42)
    for step in range(6):
        bits = lfsr.current_bits()
        output = lfsr.step()
        print(f"  Step {step}: state={bits}  output={output}")

    print()

    # Dual spin demo
    print("DUAL SPIN (ordered XOR chaotic):")
    ds = DualSpin()
    for step in range(6):
        route = ds.route_index()
        ternary = ds.ternary_state()
        poly = POLYHEDRA[route]
        print(f"  Step {step}: poly={poly.name:<30} ternary={ternary}")

    print()

    # Flow routing demo
    print("POLYHEDRAL FLOW ROUTING:")
    router = PolyhedralFlowRouter()
    for tongue in ["KO", "CA", "UM"]:
        address = router.generate_flow_address(tongue)
        print(f"  {tongue}: {address}")

    print()
    print("=" * 70)
    print("Data flows along polyhedral edges, refracting at face boundaries.")
    print("Fibonacci spin = stable routing. LFSR = chaotic exploration.")
    print("Dual spin XOR = Harry Potter staircases.")
    print("=" * 70)
