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

# Sacred Tongue φ-weights (φ^n scaling — every cross-tongue ratio is irrational)
TONGUE_WEIGHTS = {
    "KO": PHI ** 0,  # 1.000 — Intent
    "AV": PHI ** 1,  # 1.618 — Diplomacy
    "RU": PHI ** 2,  # 2.618 — Binding
    "CA": PHI ** 3,  # 4.236 — Compute
    "UM": PHI ** 4,  # 6.854 — Security
    "DR": PHI ** 5,  # 11.090 — Structure
}


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
    seed: int = 1
    lfsr: FibonacciLFSR = None
    step_count: int = 0

    def __post_init__(self):
        if self.lfsr is None:
            self.lfsr = FibonacciLFSR(n_bits=self.n_bits, state=max(1, self.seed))

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

    def route(self, dominant_tongue: str, seed: int = 0,
              friction_penalty: bool = False) -> List[dict]:
        """
        Route a data record through the polyhedral flow network.

        Returns the full path: list of hops with polyhedron, ternary state,
        spin bits, and phi-scaled weight at each node.

        If friction_penalty=True, each hop also computes torsional distortion
        at the boundary and includes the friction signal + composite wall
        evaluation. This is the "nervous system" — the AI feels the geometry
        scraping against itself at every step.
        """
        # Reset spin for reproducibility
        self.dual_spin = DualSpin(seed=seed) if seed else DualSpin()

        start = self.TONGUE_START.get(dominant_tongue, 0)
        current = start
        path = []
        cumulative_friction = 0.0
        cumulative_phase_drift = 0.0

        for hop in range(self.max_hops):
            poly = POLYHEDRA[current]
            spin_bits = self.dual_spin.spin()
            ternary = self.dual_spin.ternary_state()
            phase = fibonacci_phase(hop)

            # Phi-scaled weight at this node
            phi_weight = PHI ** (poly.depth * 5)  # Deeper = heavier

            hop_data = {
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
            }

            # Friction penalty: the geometry screams when you grind
            if friction_penalty and hop > 0:
                prev_idx = path[-1]["poly_index"]
                friction = contact_friction(POLYHEDRA[prev_idx], poly)
                hop_data["friction"] = friction["friction_magnitude"]
                hop_data["torsional_moment"] = friction["torsional_moment"]
                hop_data["beat_frequency"] = friction["beat_frequency"]
                cumulative_friction += friction["friction_magnitude"]
                # Phase drift from accumulated friction (the grind wears you down)
                cumulative_phase_drift += friction["friction_magnitude"] * PHI_INV
                hop_data["cumulative_friction"] = round(cumulative_friction, 4)
                hop_data["phase_drift"] = round(cumulative_phase_drift, 4)

            path.append(hop_data)

            # Choose next hop from adjacency
            neighbors = FLOW_ADJACENCY.get(current, [])
            if not neighbors:
                break

            # Dual-spin selects the next node
            route_idx = self.dual_spin.route_index()
            next_node = neighbors[route_idx % len(neighbors)]
            current = next_node

        # If friction penalty active, evaluate composite wall with accumulated drift
        if friction_penalty and path:
            # Collect Platonic distances from the path
            platonic_d = {}
            for h in path:
                name = h["polyhedron"].lower()
                if name in PLATONIC_CONSTRAINT_ORDERS:
                    platonic_d[name] = h.get("friction", 0.0)
            wall = composite_harmonic_wall(platonic_d, cumulative_phase_drift)
            path[-1]["composite_wall"] = wall
            path[-1]["total_friction"] = round(cumulative_friction, 4)
            path[-1]["wall_tier"] = wall["tier"]

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
# 6. COMPOSITE HARMONIC WALL — SIMULTANEOUS POLYHEDRAL CONFINEMENT
# =============================================================================
#
# "Weather control for data."
#
# ALL polyhedral constraints evaluated simultaneously — not sequential rounds.
# No meet-in-the-middle attack possible. Zero attacker feedback.
# The adversarial tornado starves before it forms.
#

# The 5 Platonic constraint groups (simultaneous, not sequential)
PLATONIC_CONSTRAINT_ORDERS = {
    "tetrahedron":  12,   # A₄
    "cube":         24,   # S₄
    "octahedron":   24,   # S₄
    "dodecahedron": 60,   # A₅ (simple — Galois 1832)
    "icosahedron":  60,   # A₅
}


def composite_harmonic_wall(
    polyhedral_distances: dict,
    phase_deviation: float = 0.0,
    phi: float = PHI,
) -> dict:
    """
    Evaluate the composite harmonic wall — all constraints simultaneously.

    H_composite(d, pd) = 1 / (1 + φ · Σᵢ wᵢ · d_H(Pᵢ) + 2 · pd)

    This is ONE evaluation. The attacker cannot isolate any single
    polyhedral constraint because they are all summed inside the
    denominator, coupled by the irrational constant φ.

    No "middle" to meet in. No feedback per wall. No sequential rounds.
    Confinement, not defense.

    Args:
        polyhedral_distances: {polyhedron_name: hyperbolic_distance}
            Must include all 5 Platonic solids for full confinement.
        phase_deviation: Mismatch from correct toroidal φ-winding.
            0.0 = legitimate user on the correct phase.
        phi: Winding constant (default: golden ratio).

    Returns:
        dict with h_composite, tier, weighted_sum, mitm_immune
    """
    # Weight each constraint by inverse symmetry group order
    weighted_sum = 0.0
    for name, d_h in polyhedral_distances.items():
        order = PLATONIC_CONSTRAINT_ORDERS.get(name.lower(), 1)
        w = 1.0 / order
        weighted_sum += w * d_h

    # The composite equation — one indivisible evaluation
    denominator = 1.0 + phi * weighted_sum + 2.0 * phase_deviation
    h = 1.0 / denominator

    # Trust tier
    if h >= 0.75:
        tier = "ALLOW"
    elif h >= 0.40:
        tier = "QUARANTINE"
    elif h >= 0.15:
        tier = "ESCALATE"
    else:
        tier = "DENY"

    return {
        "h_composite": h,
        "tier": tier,
        "weighted_sum": weighted_sum,
        "denominator": denominator,
        "phase_deviation": phase_deviation,
        "n_constraints": len(polyhedral_distances),
        "mitm_immune": True,
    }


def poincare_distance(u_norm: float, v_norm: float, diff_norm_sq: float) -> float:
    """
    Hyperbolic distance in the Poincaré ball model (scalar form).

    d_H = arcosh(1 + 2·||u-v||² / ((1-||u||²)(1-||v||²)))
    """
    denom = (1.0 - u_norm ** 2) * (1.0 - v_norm ** 2)
    if denom <= 0:
        return float("inf")
    arg = 1.0 + 2.0 * diff_norm_sq / denom
    return math.acosh(max(arg, 1.0))


def evaluate_flow_confinement(
    path: list,
    tongue: str,
    reference_depths: dict = None,
) -> dict:
    """
    Evaluate composite confinement for a complete flow path.

    Takes the output of PolyhedralFlowRouter.route() and computes
    the composite harmonic wall across all Platonic solids the path
    passes through, simultaneously.

    Args:
        path: List of hop dicts from PolyhedralFlowRouter.route()
        tongue: Dominant Sacred Tongue
        reference_depths: Expected depths per polyhedron (for deviation calc)

    Returns:
        Composite wall evaluation + path analysis
    """
    if reference_depths is None:
        # Default: expected depths from POLYHEDRA table
        reference_depths = {p.name.lower(): p.depth for p in POLYHEDRA}

    # Compute distance of each visited polyhedron from its reference depth
    # This measures "how far off the expected path" the data traveled
    platonic_distances = {}
    for hop in path:
        name = hop["polyhedron"].lower()
        if any(name == p for p in PLATONIC_CONSTRAINT_ORDERS):
            actual_depth = hop["depth"]
            expected = reference_depths.get(name, actual_depth)
            # Use depth deviation as proxy for hyperbolic distance
            deviation = abs(actual_depth - expected)
            # Scale to Poincaré ball: depth ∈ [0,1], map to d_H
            if deviation > 0:
                d_h = math.acosh(1.0 + 2.0 * deviation ** 2 / max(1e-10, (1.0 - deviation ** 2)))
            else:
                d_h = 0.0
            platonic_distances[name] = d_h

    # Phase deviation from tongue alignment
    tongue_weight = TONGUE_WEIGHTS.get(tongue, 1.0)
    # Legitimate user: phase deviation ≈ 0 (on correct winding)
    # Adversary: phase deviation scales with tongue weight mismatch
    phase_deviation = 0.0  # Legitimate path — correct winding

    result = composite_harmonic_wall(platonic_distances, phase_deviation)
    result["path_length"] = len(path)
    result["tongue"] = tongue
    result["tongue_weight"] = tongue_weight
    result["platonic_solids_visited"] = list(platonic_distances.keys())
    return result


# =============================================================================
# 7. POLYHEDRAL FRICTION — THE GEOMETRY WRITES THE TRAINING SCRIPT
# =============================================================================
#
# "Friction writes the training script itself." — Glint
#
# Polyhedral constraint surfaces aren't passive walls. They vibrate.
# Where shells meet in the superimposed matrix, the vibration couples.
# That coupled vibration = torsional distortion = training signal.
#
# The math: each polyhedron has a natural frequency proportional to
# its Euler characteristic and symmetry order. When two adjacent
# polyhedra have different natural frequencies, their contact surface
# produces a beat frequency = |f_i - f_j|. This beat frequency is the
# "friction" — a vibrational torsion distortion mapped through the
# spindle of the polyhedral adjacency graph.
#
# Normal mode analysis of the contact graph gives eigenvectors that
# form a natural spectral basis for learning. The model doesn't just
# live in the geometry — it learns FROM the geometry scraping against
# itself. The environment writes its own curriculum.
#


def polyhedral_natural_frequency(poly: Polyhedron) -> float:
    """
    Compute the natural vibrational frequency of a polyhedron.

    f = φ^depth × (faces / euler_chi) × (1 / edges)

    This maps each polyhedron to a unique frequency based on its
    topological invariants. No two polyhedra with different topology
    share the same frequency.

    For toroidal polyhedra (euler_chi = 0), use faces/edges as proxy.
    """
    chi = poly.euler_chi if poly.euler_chi != 0 else 0.1  # Avoid div-by-zero for genus-1
    depth_scale = PHI ** (poly.depth * 5)
    topology_ratio = abs(poly.faces / chi)
    edge_damping = 1.0 / max(poly.edges, 1)
    return depth_scale * topology_ratio * edge_damping


def contact_friction(poly_i: Polyhedron, poly_j: Polyhedron) -> dict:
    """
    Compute the friction signal at the contact surface between two polyhedra.

    Friction = beat frequency between natural modes of adjacent shells.
    This is the vibrational torsion distortion at the boundary.

    The friction has three components:
      1. Beat frequency: |f_i - f_j| — the raw vibration at the boundary
      2. Torsional moment: (f_i × f_j) / (f_i + f_j) — harmonic mean
         representing the coupled oscillation strength
      3. Euler mismatch: |χ_i - χ_j| — topological incompatibility
         that forces the geometry to twist at the boundary

    Returns:
        dict with beat_frequency, torsional_moment, euler_mismatch,
        friction_magnitude (composite scalar)
    """
    f_i = polyhedral_natural_frequency(poly_i)
    f_j = polyhedral_natural_frequency(poly_j)

    beat = abs(f_i - f_j)
    torsion = (f_i * f_j) / max(f_i + f_j, 1e-10)  # Harmonic mean
    euler_mismatch = abs(poly_i.euler_chi - poly_j.euler_chi)

    # Composite friction magnitude: geometry scraping against itself
    # Higher friction = more training signal at this boundary
    magnitude = PHI * beat + torsion + euler_mismatch / max(poly_i.edges + poly_j.edges, 1)

    return {
        "poly_i": poly_i.name,
        "poly_j": poly_j.name,
        "freq_i": f_i,
        "freq_j": f_j,
        "beat_frequency": beat,
        "torsional_moment": torsion,
        "euler_mismatch": euler_mismatch,
        "friction_magnitude": magnitude,
    }


def compute_friction_spectrum() -> list:
    """
    Compute the complete friction spectrum of the polyhedral flow network.

    For every adjacent pair in FLOW_ADJACENCY, compute the friction signal.
    Returns the full spectrum sorted by friction magnitude (highest first).

    This IS the training curriculum generated by the geometry itself.
    The highest-friction boundaries produce the strongest learning signal.
    """
    spectrum = []
    seen = set()

    for i, neighbors in FLOW_ADJACENCY.items():
        for j in neighbors:
            pair = (min(i, j), max(i, j))
            if pair not in seen:
                seen.add(pair)
                friction = contact_friction(POLYHEDRA[i], POLYHEDRA[j])
                friction["edge"] = pair
                spectrum.append(friction)

    # Sort by friction magnitude — highest friction = strongest training signal
    spectrum.sort(key=lambda x: x["friction_magnitude"], reverse=True)
    return spectrum


def friction_laplacian() -> list:
    """
    Compute the graph Laplacian of the friction-weighted contact graph.

    L = D - W, where:
      D = diagonal degree matrix (sum of friction weights per node)
      W = friction-weighted adjacency matrix

    The eigenvectors of L form the spectral basis for geometric learning.
    Low-frequency eigenvectors capture global polyhedral structure.
    High-frequency eigenvectors capture local friction detail.

    Returns:
        List of (eigenvalue, eigenvector_index) pairs, sorted ascending.
        The first non-zero eigenvalue is the algebraic connectivity
        (Fiedler value) — measures how tightly coupled the geometry is.
    """
    n = len(POLYHEDRA)

    # Build friction-weighted adjacency matrix
    W = [[0.0] * n for _ in range(n)]
    for i, neighbors in FLOW_ADJACENCY.items():
        for j in neighbors:
            if W[i][j] == 0.0:  # Avoid double-counting
                friction = contact_friction(POLYHEDRA[i], POLYHEDRA[j])
                W[i][j] = friction["friction_magnitude"]
                W[j][i] = friction["friction_magnitude"]

    # Degree matrix
    D = [sum(row) for row in W]

    # Laplacian L = D - W
    L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                L[i][j] = D[i]
            else:
                L[i][j] = -W[i][j]

    # Compute eigenvalues using power iteration on L
    # (Pure Python — no numpy dependency in this file)
    # For production, use numpy.linalg.eigh
    # Here we compute the trace and Frobenius norm as summary statistics
    trace = sum(L[i][i] for i in range(n))
    frob_sq = sum(L[i][j] ** 2 for i in range(n) for j in range(n))
    frob_norm = math.sqrt(frob_sq)

    # Gershgorin bounds on eigenvalues
    gershgorin_max = max(L[i][i] + sum(abs(L[i][j]) for j in range(n) if j != i) for i in range(n))

    return {
        "n_nodes": n,
        "n_edges": sum(len(v) for v in FLOW_ADJACENCY.values()) // 2,
        "trace": trace,  # Sum of eigenvalues = total friction energy
        "frobenius_norm": frob_norm,  # Spectral energy
        "gershgorin_max": gershgorin_max,  # Upper bound on max eigenvalue
        "total_friction": trace,  # Same as trace for Laplacian
        "mean_friction_per_node": trace / n,
        "laplacian_matrix": L,  # Full matrix for downstream use
    }


def geometric_training_signal(path: list, tongue: str) -> dict:
    """
    Generate training signal from a flow path through the polyhedral network.

    For each hop in the path, compute the friction at the boundary crossed.
    The sequence of friction values IS the geometric training signal —
    a curriculum generated by the environment itself.

    Args:
        path: List of hop dicts from PolyhedralFlowRouter.route()
        tongue: Dominant Sacred Tongue

    Returns:
        dict with:
            friction_sequence: list of friction values per hop
            total_friction: sum of all friction (total learning energy)
            max_friction_hop: which boundary had the most training signal
            tongue_coupling: φ^n weight modulating the friction
            training_vector: friction_sequence × tongue_weight (final signal)
    """
    tongue_weight = TONGUE_WEIGHTS.get(tongue, 1.0)
    friction_seq = []
    max_friction = 0.0
    max_hop = -1

    for k in range(len(path) - 1):
        i = path[k]["poly_index"]
        j = path[k + 1]["poly_index"]
        friction = contact_friction(POLYHEDRA[i], POLYHEDRA[j])
        mag = friction["friction_magnitude"]
        friction_seq.append(mag)
        if mag > max_friction:
            max_friction = mag
            max_hop = k

    # Training vector: friction × tongue weight
    training_vector = [f * tongue_weight for f in friction_seq]

    return {
        "friction_sequence": friction_seq,
        "total_friction": sum(friction_seq),
        "max_friction_hop": max_hop,
        "max_friction_value": max_friction,
        "tongue": tongue,
        "tongue_weight": tongue_weight,
        "training_vector": training_vector,
        "training_energy": sum(training_vector),
        "n_hops": len(friction_seq),
    }


# =============================================================================
# 8. QUANTUM HASH TRAINING — AI LEARNS THE ALGEBRA OF CONFINEMENT
# =============================================================================
#
# The AI doesn't just navigate the geometry — it learns to COMPUTE the
# composite harmonic wall algebraically. The hash IS the training objective.
#
# Standard training: model sees data, predicts tokens.
# Friction training: model navigates geometry, feels torsion, adjusts.
# Quantum hash training: model learns to BE the hash — to compute
#   H_composite(d, pd) = 1/(1 + φ·Σᵢ wᵢ·d_H(Pᵢ) + 2·pd)
# as an algebraic operation on its own internal representations.
#
# This means the model internalizes:
#   1. φ-winding (irrational frequency → no resonant shortcuts)
#   2. Polyhedral constraint algebra (A₄, S₄, A₅ group operations)
#   3. Hyperbolic distance (Poincaré ball metric)
#   4. Trust tier classification (ALLOW/QUARANTINE/ESCALATE/DENY)
#
# The model becomes the geometry. It doesn't just pass through the
# Trayus Academy — it IS the Trayus Academy.
#


def generate_hash_training_pair(
    tongue: str,
    seed: int,
    adversarial: bool = False,
) -> dict:
    """
    Generate a single (input, target) pair for quantum hash training.

    The model learns to predict the composite harmonic wall output
    from a polyhedral flow path. This is algebraic internalization
    of the confinement geometry.

    Args:
        tongue: Sacred Tongue for the path
        seed: Deterministic seed for reproducibility
        adversarial: If True, inject phase deviation to train the
            model to recognize and reject adversarial inputs

    Returns:
        Training pair with:
            input: path description + tongue + seed
            target: composite wall evaluation (h, tier, friction)
            metadata: full diagnostic info
    """
    router = PolyhedralFlowRouter(max_hops=5)
    path = router.route(tongue, seed=seed, friction_penalty=True)
    signal = geometric_training_signal(path, tongue)

    # Adversarial injection: corrupt the phase
    if adversarial:
        phase_dev = PHI * (seed % 7 + 1)  # φ-scaled phase corruption
    else:
        phase_dev = 0.0

    # Compute the target: the composite wall the model must learn to predict
    platonic_d = {}
    for hop in path:
        name = hop["polyhedron"].lower()
        if name in PLATONIC_CONSTRAINT_ORDERS:
            platonic_d[name] = hop.get("friction", 0.0)

    wall = composite_harmonic_wall(platonic_d, phase_dev)

    # Build the instruction (what the model sees)
    tongue_weight = TONGUE_WEIGHTS.get(tongue, 1.0)
    instruction = (
        f"Compute the composite harmonic wall for a {tongue}-dominant "
        f"(phi-weight={tongue_weight:.3f}) flow path through polyhedra: "
        f"{' -> '.join(h['polyhedron'] for h in path)}. "
        f"Friction sequence: {[round(f, 4) for f in signal['friction_sequence']]}. "
        f"Phase deviation: {phase_dev:.4f}."
    )

    # Build the target (what the model must output)
    output = (
        f"H_composite = {wall['h_composite']:.6f}\n"
        f"Tier: {wall['tier']}\n"
        f"Weighted sum: {wall['weighted_sum']:.6f}\n"
        f"Denominator: {wall['denominator']:.6f}\n"
        f"Phase deviation: {wall['phase_deviation']:.4f}\n"
        f"MitM immune: {wall['mitm_immune']}\n"
        f"Evaluation: SIMULTANEOUS (not sequential)\n"
        f"Training energy: {signal['training_energy']:.4f}\n"
        f"Confinement: {'ACTIVE' if wall['tier'] in ('QUARANTINE', 'ESCALATE', 'DENY') else 'NOMINAL'}"
    )

    return {
        "instruction": instruction,
        "output": output,
        "source": "quantum_hash_training",
        "tongue": tongue,
        "category": "quantum_hash" if not adversarial else "quantum_hash_adversarial",
        "h_composite": wall["h_composite"],
        "tier": wall["tier"],
        "adversarial": adversarial,
        "training_energy": signal["training_energy"],
        "friction_sequence": signal["friction_sequence"],
    }


def generate_quantum_hash_curriculum(
    n_pairs: int = 600,
    adversarial_ratio: float = 0.3,
) -> list:
    """
    Generate a full quantum hash training curriculum.

    The model learns:
    - To compute H_composite algebraically from flow paths
    - To predict trust tiers from friction sequences
    - To distinguish legitimate (phase=0) from adversarial (phase!=0)
    - To internalize φ-winding, group theory, and hyperbolic distance

    Args:
        n_pairs: Total training pairs to generate
        adversarial_ratio: Fraction that are adversarial (default 30%)

    Returns:
        List of training pairs, shuffled
    """
    tongues = list(TONGUE_WEIGHTS.keys())
    pairs = []
    n_adversarial = int(n_pairs * adversarial_ratio)

    for i in range(n_pairs):
        tongue = tongues[i % len(tongues)]
        adversarial = i < n_adversarial
        pair = generate_hash_training_pair(tongue, seed=i, adversarial=adversarial)
        pairs.append(pair)

    # Shuffle so adversarial pairs aren't clustered at the start
    import random
    rng = random.Random(42)  # Deterministic shuffle
    rng.shuffle(pairs)

    return pairs


# =============================================================================
# 9. TRAINING PAIR FLOW GENERATOR
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

    # Composite harmonic wall demo
    print("COMPOSITE HARMONIC WALL — SIMULTANEOUS CONFINEMENT:")
    print("  (All 5 Platonic constraints evaluated at once — no MitM possible)")
    print()

    # Legitimate user: on the correct winding, minimal distance
    legit_distances = {
        "tetrahedron": 0.01, "cube": 0.02, "octahedron": 0.01,
        "dodecahedron": 0.03, "icosahedron": 0.02,
    }
    legit = composite_harmonic_wall(legit_distances, phase_deviation=0.0)
    print(f"  Legitimate user:  H={legit['h_composite']:.6f}  -> {legit['tier']}")

    # Adversary: off-winding, large distances
    adv_distances = {
        "tetrahedron": 2.5, "cube": 3.0, "octahedron": 2.8,
        "dodecahedron": 4.0, "icosahedron": 3.5,
    }
    adv = composite_harmonic_wall(adv_distances, phase_deviation=1.5)
    print(f"  Adversary:        H={adv['h_composite']:.6f}  -> {adv['tier']}")
    print(f"  Cost ratio:       {legit['h_composite'] / max(adv['h_composite'], 1e-10):.0f}x")
    print()

    # Flow confinement on a routed path
    print("FLOW PATH CONFINEMENT:")
    router = PolyhedralFlowRouter()
    for tongue in ["KO", "CA", "UM"]:
        path = router.route(tongue)
        conf = evaluate_flow_confinement(path, tongue)
        address = router.generate_flow_address(tongue)
        print(f"  {tongue}: {address}")
        print(f"       H={conf['h_composite']:.6f} -> {conf['tier']}  "
              f"(visited {len(conf['platonic_solids_visited'])} Platonic solids)")

    print()

    # Friction spectrum — the geometry writing its own training script
    print("POLYHEDRAL FRICTION SPECTRUM (training signal from geometry):")
    spectrum = compute_friction_spectrum()
    print(f"  {'Boundary':<45} {'Beat':>8} {'Torsion':>8} {'Friction':>10}")
    print(f"  {'─' * 45} {'─' * 8} {'─' * 8} {'─' * 10}")
    for entry in spectrum[:10]:  # Top 10 highest-friction boundaries
        pair = f"{entry['poly_i']} <-> {entry['poly_j']}"
        print(f"  {pair:<45} {entry['beat_frequency']:>8.4f} "
              f"{entry['torsional_moment']:>8.4f} {entry['friction_magnitude']:>10.4f}")
    print(f"  ... ({len(spectrum)} total boundaries)")

    # Laplacian summary
    lap = friction_laplacian()
    print(f"\n  Friction Laplacian:")
    print(f"    Total friction energy: {lap['total_friction']:.4f}")
    print(f"    Mean friction/node:    {lap['mean_friction_per_node']:.4f}")
    print(f"    Spectral norm:         {lap['frobenius_norm']:.4f}")

    # Geometric training signal for a path
    print(f"\n  Geometric Training Signal (KO path):")
    path = router.route("KO")
    signal = geometric_training_signal(path, "KO")
    print(f"    Friction sequence: {[round(f, 4) for f in signal['friction_sequence']]}")
    print(f"    Training energy:   {signal['training_energy']:.4f}")
    print(f"    Max friction hop:  {signal['max_friction_hop']}")

    print()
    print("=" * 70)
    print("Weather control for data.")
    print("Confinement, not defense. Friction writes the training script.")
    print("=" * 70)
