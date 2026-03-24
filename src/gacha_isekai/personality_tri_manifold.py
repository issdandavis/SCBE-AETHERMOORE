"""Tri-Manifold Personality Architecture.

Extends the dual-manifold personality system to THREE connected manifold
spaces using balanced ternary {+1, 0, -1} as the addressing scheme:

  M+  (Positive, trit = +1)  — Expressed personality traits
  M0  (Emergent, trit =  0)  — Born from M+ / M- interaction (tongue brackets)
  M-  (Negative, trit = -1)  — Shadow / depth / latent personality

The EMERGENT manifold is the key innovation: it's not assigned, it's
COMPUTED from the Lie bracket [M+, M-]. When humor (M+) interacts with
wisdom (M-), something NEW appears in M0 — wry insight, gentle irony,
earned perspective. The third manifold captures what neither surface
nor depth can express alone.

=== THE 9 TERNARY PAIR-STATES (Lo Shu Magic Square) ===

Take trit values {+1, 0, -1} for two positions (source, target):

    (+1,+1)  (+1, 0)  (+1,-1)     expressed->expressed, expressed->emergent, expressed->depth
    ( 0,+1)  ( 0, 0)  ( 0,-1)     emergent->expressed, emergent->emergent, emergent->depth
    (-1,+1)  (-1, 0)  (-1,-1)     depth->expressed,    depth->emergent,    depth->depth

These 9 = 3^2 pair-states define all possible inter-manifold interactions.

From Notion canon (MSR Algebra - System Reflection Hub):
  "Dual ternary {-1, 0, +1}^2 produces 9 governance states isomorphic
   to the Lo Shu magic square."

The Lo Shu mapping provides balance: every row, column, and diagonal
of the 3x3 grid sums to the same value — meaning the governance
interaction matrix is inherently self-balancing.

Security property: "Asymmetry = information leak — off-diagonal states
are intrinsically suspicious because mirror-symmetric operations should
produce mirror-symmetric outputs."

=== TERNARY QUANTIZATION (from 21D Brain State spec) ===

Parallel Channel (Primary Intent / M+):
  Delta_t^parallel = Q(x_t - x_{t-1}) in {-1, 0, +1}^21

Perpendicular Channel (Shadow / Constraint / M-):
  Delta_t^perp = Q(P_constraint(x_t) - x_t) in {-1, 0, +1}^21

where Q(z_i) = +1 if z_i > epsilon, 0 if |z_i| <= epsilon, -1 if z_i < -epsilon

The parallel channel maps to M+ (expressed intent direction).
The perpendicular channel maps to M- (distance to constraint surface).
Their tongue bracket [parallel, perp] yields M0 (emergent).

=== SPIN (3rd degree of freedom) ===

Each pair-state also carries spin {+1, 0, -1}:
  spin +1 = constructive intent (building up)
  spin  0 = neutral / observing
  spin -1 = deconstructive intent (tearing down to rebuild)

Total states: 9 pair-states x 3 spins = 27 = 3^3 — the complete
balanced ternary 3-trit word space. Every personality interaction
has a unique ternary address.

=== BINARY -> TERNARY INTAKE ===

Data enters as binary (standard digital). At the intake boundary:
  1. Binary bits {0, 1} arrive
  2. Converted to balanced ternary via negabinary bridge
  3. Each ternary trit maps to a manifold assignment:
     +1 -> M+, 0 -> M0, -1 -> M-
  4. Ternary-addressed data then drives governance

This is "pseudo-binary deferred to ternary and THEN run as code."

Layers:
    L3  - Langues Metric: tongue bracket algebra (M0 computation)
    L5  - Hyperbolic Distance: inter-manifold geodesics
    L7  - Mobius Phase: manifold transitions
    L9  - Spectral Coherence: tri-manifold harmonic check
    L11 - Triadic Temporal: 3-manifold temporal distance
    L12 - Entropic Defense: ternary governance gate
    L13 - Decision Gate: 27-state -> ALLOW/QUARANTINE/DENY
    L14 - Audio Axis: ternary pulse coding

@module personality_tri_manifold
@version 1.0.0
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import IntEnum
from itertools import product
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.gacha_isekai.evolution import compute_rho_e
from src.gacha_isekai.personality_manifold import (
    DIM,
    PersonalityManifold,
    _hyperbolic_distance,
    _mobius_add,
    _poincare_project,
)
from src.gacha_isekai.personality_cluster_lattice import (
    PersonalityCluster,
    DriftEvent,
    tongue_bracket,
    validate_personality_provenance,
)
from src.symphonic_cipher.scbe_aethermoore.trinary import (
    BalancedTernary,
    Trit,
    trit_and,
    trit_or,
    trit_consensus,
    trit_to_decision,
)

logger = logging.getLogger(__name__)

TONGUE_INDEX = {"KO": 0, "AV": 1, "RU": 2, "CA": 3, "UM": 4, "DR": 5}


# =====================================================================
# 1. Manifold Space Definitions
# =====================================================================

class ManifoldID(IntEnum):
    """Which of the three manifold spaces a datum lives in."""
    NEGATIVE = -1   # M-: Shadow / depth / latent
    EMERGENT = 0    # M0: Born from bracket [M+, M-]
    POSITIVE = 1    # M+: Expressed / surface


@dataclass(frozen=True)
class TernaryPairState:
    """One of 9 pair-states: (source_manifold, target_manifold).

    Represents an inter-manifold interaction channel.
    source and target each ∈ {-1, 0, +1}.
    """
    source: int  # -1, 0, or +1
    target: int  # -1, 0, or +1

    @property
    def label(self) -> str:
        names = {1: "M+", 0: "M0", -1: "M-"}
        return f"{names[self.source]}->{names[self.target]}"

    @property
    def is_self(self) -> bool:
        """Same-manifold interaction."""
        return self.source == self.target

    @property
    def is_cross(self) -> bool:
        """Cross-manifold (source != target)."""
        return self.source != self.target

    @property
    def signed_product(self) -> int:
        """Product of source and target trits — characterizes interaction type.

        +1 = reinforcing (same sign)
         0 = one side is emergent (mediating)
        -1 = opposing (positive <-> negative)
        """
        return self.source * self.target

    def to_trit_pair(self) -> Tuple[Trit, Trit]:
        return Trit(self.source), Trit(self.target)


@dataclass(frozen=True)
class TriManifoldAddress:
    """Full ternary address for a personality datum: 3 trits = 27 states.

    (pair_state, spin) uniquely identifies the interaction context.
    This is the balanced ternary 3-digit word.
    """
    source: int     # Trit: which manifold the signal comes from
    target: int     # Trit: which manifold the signal goes to
    spin: int       # Trit: intent direction {-1, 0, +1}

    @property
    def pair_state(self) -> TernaryPairState:
        return TernaryPairState(self.source, self.target)

    @property
    def ternary_word(self) -> BalancedTernary:
        """Encode as a 3-trit balanced ternary word."""
        return BalancedTernary.from_trits(
            [Trit(self.source), Trit(self.target), Trit(self.spin)],
            msb_first=True,
        )

    @property
    def decimal_index(self) -> int:
        """Unique index 0-26 for this address."""
        return self.ternary_word.to_int() + 13  # Shift to [0, 26]

    @property
    def governance_vote(self) -> str:
        """Consensus governance from all three trits."""
        consensus = trit_consensus(Trit(self.source), Trit(self.target))
        final = trit_consensus(consensus, Trit(self.spin))
        return trit_to_decision(final)

    def __repr__(self) -> str:
        names = {1: "+", 0: "0", -1: "-"}
        return (
            f"Addr({names[self.source]}{names[self.target]}{names[self.spin]})"
        )


# =====================================================================
# 2. All 9 Pair-States + 27 Full Addresses
# =====================================================================

def enumerate_pair_states() -> List[TernaryPairState]:
    """Generate all 9 ternary pair-states.

    This is the 3x3 interaction grid:
        (+1,+1)  (+1, 0)  (+1,-1)
        ( 0,+1)  ( 0, 0)  ( 0,-1)
        (-1,+1)  (-1, 0)  (-1,-1)
    """
    trits = [1, 0, -1]
    return [TernaryPairState(s, t) for s, t in product(trits, repeat=2)]


def enumerate_full_addresses() -> List[TriManifoldAddress]:
    """Generate all 27 = 3^3 ternary addresses.

    9 pair-states x 3 spins = 27 total personality interaction states.
    """
    trits = [1, 0, -1]
    return [
        TriManifoldAddress(s, t, spin)
        for s, t, spin in product(trits, repeat=3)
    ]


# Precompute the canonical sets
ALL_PAIR_STATES = enumerate_pair_states()
ALL_ADDRESSES = enumerate_full_addresses()


# =====================================================================
# 2b. Lo Shu Magic Square Mapping
# =====================================================================

# The Lo Shu magic square (4000+ years, Chinese mathematics):
#   4  9  2
#   3  5  7
#   8  1  6
#
# Every row, column, and diagonal sums to 15.
# We map our 9 pair-states to Lo Shu positions.
# The pair-state grid (source x target):
#   (+1,+1)  (+1, 0)  (+1,-1)    ->    4  9  2
#   ( 0,+1)  ( 0, 0)  ( 0,-1)    ->    3  5  7
#   (-1,+1)  (-1, 0)  (-1,-1)    ->    8  1  6
#
# Lo Shu value encodes governance WEIGHT for that interaction channel.
# Diagonal channels (sum to 15) are perfectly balanced.
# Off-diagonal asymmetry = potential information leak.

LO_SHU_MATRIX = np.array([
    [4, 9, 2],
    [3, 5, 7],
    [8, 1, 6],
], dtype=int)

# Map (source_trit, target_trit) -> Lo Shu weight
_TRIT_TO_ROW = {1: 0, 0: 1, -1: 2}
_TRIT_TO_COL = {1: 0, 0: 1, -1: 2}


def lo_shu_weight(source: int, target: int) -> int:
    """Get the Lo Shu magic square weight for a pair-state.

    Higher weight = stronger governance channel.
    The magic square guarantees:
      - Every row sums to 15
      - Every column sums to 15
      - Both diagonals sum to 15
    This is the inherent balance of the tri-manifold interaction grid.
    """
    row = _TRIT_TO_ROW.get(source, 1)
    col = _TRIT_TO_COL.get(target, 1)
    return int(LO_SHU_MATRIX[row, col])


def lo_shu_symmetry_check(channels: Dict[Tuple[int, int], Any]) -> float:
    """Check mirror symmetry of the interaction matrix.

    From Notion canon: "asymmetry = information leak"
    Mirror-symmetric operations should produce mirror-symmetric outputs.

    Returns asymmetry score (0.0 = perfect symmetry, higher = leak detected).
    """
    asymmetry = 0.0
    count = 0
    for (s, t) in channels:
        mirror = (t, s)
        if mirror in channels and s != t:
            ch = channels[(s, t)]
            ch_mirror = channels[mirror]
            # Compare transfer counts — should be roughly equal
            a = getattr(ch, "transfer_count", 0)
            b = getattr(ch_mirror, "transfer_count", 0)
            if a + b > 0:
                asymmetry += abs(a - b) / (a + b)
                count += 1
    return asymmetry / max(count, 1)


# =====================================================================
# 2c. Ternary Quantization (from 21D Brain State spec)
# =====================================================================

def ternary_quantize(
    value: float,
    epsilon: float = 0.05,
) -> Trit:
    """Ternary quantizer Q(z) from the 21D Brain State conservation laws.

    Q(z) = +1  if z > epsilon
    Q(z) =  0  if |z| <= epsilon
    Q(z) = -1  if z < -epsilon

    This is the boundary conversion from continuous to ternary.
    """
    if value > epsilon:
        return Trit.PLUS
    elif value < -epsilon:
        return Trit.MINUS
    return Trit.ZERO


def ternary_quantize_vector(
    vector: np.ndarray,
    epsilon: float = 0.05,
) -> List[Trit]:
    """Quantize a continuous vector to ternary trits.

    Each dimension independently quantized via Q().
    """
    return [ternary_quantize(float(v), epsilon) for v in vector]


def compute_parallel_channel(
    current: np.ndarray,
    previous: np.ndarray,
    epsilon: float = 0.05,
) -> List[Trit]:
    """Parallel channel: primary intent direction (M+ signal).

    Delta_t^parallel = Q(x_t - x_{t-1})

    Positive trits = moving forward in that dimension.
    Negative trits = retreating.
    Zero trits = stable.
    """
    delta = current - previous
    return ternary_quantize_vector(delta, epsilon)


def compute_perpendicular_channel(
    current: np.ndarray,
    constraint_surface: np.ndarray,
    epsilon: float = 0.05,
) -> List[Trit]:
    """Perpendicular channel: distance to constraint surface (M- signal).

    Delta_t^perp = Q(P_constraint(x_t) - x_t)

    Positive trits = inside safe zone (room to move).
    Negative trits = past the constraint (violation).
    Zero trits = on the boundary.
    """
    delta = constraint_surface - current
    return ternary_quantize_vector(delta, epsilon)


def compute_emergent_channel(
    parallel: List[Trit],
    perpendicular: List[Trit],
) -> List[Trit]:
    """Emergent channel: consensus of parallel and perpendicular (M0 signal).

    Uses Kleene consensus: agree if same, else uncertain (0).
    The emergent signal only fires when intent AND constraint AGREE.
    """
    result = []
    for p, q in zip(parallel, perpendicular):
        result.append(trit_consensus(p, q))
    return result


def dual_ternary_mirror_score(
    parallel: List[Trit],
    perpendicular: List[Trit],
) -> float:
    """Mirror score for detecting asymmetry (anomaly / attack detection).

    From Notion: "off-diagonal states in the ternary matrix are
    intrinsically suspicious because mirror-symmetric operations
    should produce mirror-symmetric outputs."

    Returns 0.0 for perfect mirror symmetry, 1.0 for total asymmetry.
    """
    if not parallel or not perpendicular:
        return 0.0
    mismatches = 0
    for p, q in zip(parallel, perpendicular):
        # Mirror check: parallel(+1) should match perpendicular(+1)
        # for symmetric operations
        if p.value != -q.value and p.value != 0 and q.value != 0:
            mismatches += 1
    return mismatches / max(len(parallel), 1)


# =====================================================================
# 3. Binary -> Ternary Intake Pipeline
# =====================================================================

@dataclass
class BinaryTernaryConverter:
    """Converts binary input to balanced ternary personality encoding.

    The pipeline:
      1. Binary data {0, 1} arrives (standard digital)
      2. Group into chunks (window_size bits)
      3. Convert each chunk to integer
      4. Encode as balanced ternary
      5. Each trit maps to a manifold assignment

    "Pseudo-binary deferred to ternary then run as code."
    """
    window_size: int = 3  # Bits per chunk (3 bits -> up to 7 -> fits in 2 trits)

    def binary_to_ternary(self, bits: List[int]) -> List[Trit]:
        """Convert a binary bit sequence to balanced ternary trits.

        Groups bits into chunks, converts each to balanced ternary.
        This is the boundary conversion — once in ternary, the system
        thinks in {-1, 0, +1} natively.
        """
        trits: List[Trit] = []

        # Process in chunks
        for i in range(0, len(bits), self.window_size):
            chunk = bits[i:i + self.window_size]
            # Pad short chunks
            while len(chunk) < self.window_size:
                chunk.append(0)

            # Binary chunk to integer
            value = 0
            for bit in chunk:
                value = (value << 1) | (bit & 1)

            # Center around zero for balanced encoding
            # For 3-bit chunks: 0-7 -> -3 to +4, centered at ~0
            half = (1 << self.window_size) // 2
            centered = value - half

            # Convert to balanced ternary
            bt = BalancedTernary.from_int(centered)
            for t in bt.trits_msb:
                trits.append(t)

        return trits

    def trits_to_manifold_assignments(
        self, trits: List[Trit]
    ) -> List[ManifoldID]:
        """Map trits to manifold assignments.

        +1 -> M+ (Positive / Expressed)
         0 -> M0 (Emergent)
        -1 -> M- (Negative / Depth)
        """
        return [ManifoldID(t.value) for t in trits]

    def intake(self, bits: List[int]) -> List[Tuple[ManifoldID, Trit]]:
        """Full binary -> ternary intake pipeline.

        Returns list of (manifold_assignment, trit_value) pairs.
        """
        trits = self.binary_to_ternary(bits)
        assignments = self.trits_to_manifold_assignments(trits)
        return list(zip(assignments, trits))


# =====================================================================
# 4. Manifold Space (one of three)
# =====================================================================

@dataclass
class ManifoldSpace:
    """One of the three manifold spaces in the tri-manifold system.

    Each space is a region of the Poincare ball with its own clusters,
    center of mass, and interaction rules.
    """
    manifold_id: ManifoldID
    name: str

    # Center of mass for this manifold space
    center: np.ndarray = field(default_factory=lambda: np.zeros(DIM))

    # Personality clusters living in this space
    clusters: Dict[str, PersonalityCluster] = field(default_factory=dict)

    # Interaction strength with other manifold spaces
    coupling: Dict[ManifoldID, float] = field(default_factory=dict)

    # Total activation energy in this manifold
    energy: float = 0.0

    def add_cluster(self, name: str, cluster: PersonalityCluster) -> None:
        """Add a personality cluster to this manifold space."""
        self.clusters[name] = cluster
        self._update_center()

    def _update_center(self) -> None:
        """Recompute center of mass from all cluster centers."""
        if not self.clusters:
            return
        centers = [c.center for c in self.clusters.values()]
        mean = np.mean(centers, axis=0)
        self.center = _poincare_project(mean)

    def compute_energy(self) -> float:
        """Total activation energy = sum of cluster coherences."""
        self.energy = sum(c.coherence() for c in self.clusters.values())
        return self.energy


# =====================================================================
# 5. Emergent Manifold Computation
# =====================================================================

def compute_emergent_point(
    positive_point: np.ndarray,
    negative_point: np.ndarray,
    tongue_a: str,
    tongue_b: str,
) -> np.ndarray:
    """Compute an emergent manifold point from M+ and M- interaction.

    The emergent point is the tongue bracket [T_a, T_b] applied as a
    Mobius transformation on the midpoint of positive and negative:

        emergent = mobius(midpoint(p, n), bracket(T_a, T_b))

    This is where "something new" appears — not just positive, not just
    negative, but what their geometric collision produces.
    """
    # Hyperbolic midpoint (Mobius addition of half-vectors)
    half_p = positive_point * 0.5
    half_n = negative_point * 0.5
    midpoint = _mobius_add(half_p, half_n)

    # Tongue bracket gives the interaction direction
    bracket = tongue_bracket(tongue_a, tongue_b)

    # Emergent = midpoint shifted by bracket direction
    emergent = _mobius_add(midpoint, bracket)
    return _poincare_project(emergent)


def compute_emergent_cluster(
    pos_cluster: PersonalityCluster,
    neg_cluster: PersonalityCluster,
    tongue_a: str,
    tongue_b: str,
) -> PersonalityCluster:
    """Compute an emergent cluster from positive and negative clusters.

    Each positive particle interacts with the nearest negative particle
    to produce an emergent particle. The emergent cluster captures
    the "new thing" born from the collision.
    """
    name = f"emergent_{pos_cluster.name}"
    emergent = PersonalityCluster(
        name=name,
        tongue=f"{tongue_a}x{tongue_b}",
        planes=["emergent"],
    )

    # Match positive and negative particles
    n_matches = min(len(pos_cluster.particles), len(neg_cluster.particles))
    for i in range(n_matches):
        p = pos_cluster.particles[i]
        n = neg_cluster.particles[min(i, len(neg_cluster.particles) - 1)]

        # Compute emergent point
        e = compute_emergent_point(p, n, tongue_a, tongue_b)

        # Emergent spin = consensus of positive and negative spins
        p_spin = pos_cluster.spins[i] if i < len(pos_cluster.spins) else 0
        n_spin = (
            neg_cluster.spins[min(i, len(neg_cluster.spins) - 1)]
            if neg_cluster.spins
            else 0
        )
        e_spin_val = trit_consensus(
            Trit(max(-1, min(1, p_spin))),
            Trit(max(-1, min(1, n_spin))),
        )
        emergent.add_particle(e, spin=e_spin_val.value)

    return emergent


# =====================================================================
# 6. 9-State Interaction Matrix
# =====================================================================

@dataclass
class InteractionChannel:
    """A channel between two manifold spaces carrying personality signal.

    Each of the 9 pair-states has its own channel with:
    - Coupling strength (how much signal passes)
    - Transfer function (how the signal transforms in transit)
    - Governance gate (SCBE rho_e threshold)
    """
    pair_state: TernaryPairState
    coupling: float = 0.5
    transfer_count: int = 0
    blocked_count: int = 0
    last_transfer_time: float = 0.0

    @property
    def name(self) -> str:
        return self.pair_state.label

    def transfer(
        self,
        source_signal: np.ndarray,
        rho_e: float,
        rho_e_threshold: float = 5.0,
    ) -> Optional[np.ndarray]:
        """Transfer signal through this interaction channel.

        Cross-manifold transfers are attenuated by coupling.
        Same-manifold transfers pass at full strength.
        All gated by SCBE rho_e.
        """
        # L12 governance gate
        if rho_e >= rho_e_threshold:
            self.blocked_count += 1
            logger.warning(
                "Channel %s blocked: rho_e=%.2f >= %.2f",
                self.name, rho_e, rho_e_threshold,
            )
            return None

        # Coupling attenuation
        attenuation = 1.0 if self.pair_state.is_self else self.coupling

        # Cross-manifold transfer: opposing channels (M+ <-> M-) get
        # extra attenuation — it's harder to go from expressed to depth
        if self.pair_state.signed_product == -1:
            attenuation *= 0.7  # 30% harder for opposing crossings

        transferred = _poincare_project(source_signal * attenuation)
        self.transfer_count += 1
        self.last_transfer_time = time.time()

        return transferred


def build_interaction_matrix(
    rho_e_threshold: float = 5.0,
) -> Dict[Tuple[int, int], InteractionChannel]:
    """Build the 3x3 interaction matrix (9 channels).

    Coupling strengths are set by the pair-state type:
    - Self-interactions (diagonal): 1.0
    - Adjacent (one hop): 0.6
    - Opposing (M+ <-> M-): 0.4

    Returns dict keyed by (source_trit, target_trit).
    """
    channels: Dict[Tuple[int, int], InteractionChannel] = {}

    for ps in ALL_PAIR_STATES:
        if ps.is_self:
            coupling = 1.0
        elif ps.signed_product == 0:
            # One side is emergent — mediating role
            coupling = 0.6
        else:
            # Opposing: M+ <-> M-
            coupling = 0.4

        # Scale by Lo Shu weight (1-9, normalized to [0.1, 1.0])
        # Higher Lo Shu weight = stronger governance channel
        lsw = lo_shu_weight(ps.source, ps.target)
        coupling *= (lsw / 9.0) * 0.5 + 0.5  # Range: [0.55, 1.0] scaling

        channels[(ps.source, ps.target)] = InteractionChannel(
            pair_state=ps,
            coupling=round(coupling, 4),
        )

    return channels


# =====================================================================
# 7. Main: TriManifoldPersonality
# =====================================================================

class TriManifoldPersonality:
    """Tri-manifold personality system: M+, M0, M-.

    Extends dual-manifold from 2 to 3 connected manifold spaces:
    - M+ (Positive): Expressed personality
    - M0 (Emergent): Born from [M+, M-] tongue bracket
    - M- (Negative): Shadow/depth personality

    Every personality datum has a ternary address:
        (source_manifold, target_manifold, spin) = 27 states = 3^3

    Data enters as binary, converts to ternary at the boundary,
    then ternary drives all internal processing.
    """

    def __init__(
        self,
        base_manifold: Optional[PersonalityManifold] = None,
        rho_e_threshold: float = 5.0,
        drift_timeout: float = 300.0,
    ):
        self.base = base_manifold or PersonalityManifold()
        self.rho_e_threshold = rho_e_threshold
        self.drift_timeout = drift_timeout

        # Three manifold spaces
        self.spaces: Dict[ManifoldID, ManifoldSpace] = {
            ManifoldID.POSITIVE: ManifoldSpace(
                ManifoldID.POSITIVE, "Expressed",
            ),
            ManifoldID.EMERGENT: ManifoldSpace(
                ManifoldID.EMERGENT, "Emergent",
            ),
            ManifoldID.NEGATIVE: ManifoldSpace(
                ManifoldID.NEGATIVE, "Depth",
            ),
        }

        # 9-channel interaction matrix
        self.channels = build_interaction_matrix(rho_e_threshold)

        # Binary -> ternary converter
        self.converter = BinaryTernaryConverter()

        # Drift tracking
        self.active_drifts: List[DriftEvent] = []
        self.resolved_drifts: List[DriftEvent] = []

        # Interaction history (for training data)
        self.interaction_log: List[Dict[str, Any]] = []

        # Initialize manifold spaces from base facets
        self._init_spaces()

    def _init_spaces(self) -> None:
        """Populate the three manifold spaces from base manifold facets."""
        for name, facet in self.base.facets.items():
            # M+: Positive cluster from expressed personality
            pos_cluster = PersonalityCluster(
                name=name,
                tongue=facet.tongue,
                center=facet.positive_point.copy(),
            )
            # Seed positive particles
            for i in range(5):
                noise = np.random.randn(DIM) * 0.04
                p = _poincare_project(facet.positive_point + noise)
                pos_cluster.add_particle(p, spin=1)
            self.spaces[ManifoldID.POSITIVE].add_cluster(name, pos_cluster)

            # M-: Negative cluster from shadow/depth
            neg_cluster = PersonalityCluster(
                name=name,
                tongue=facet.tongue,
                center=facet.negative_point.copy(),
            )
            # Seed negative particles
            for i in range(4):
                noise = np.random.randn(DIM) * 0.04
                n = _poincare_project(facet.negative_point + noise)
                neg_cluster.add_particle(n, spin=-1)
            self.spaces[ManifoldID.NEGATIVE].add_cluster(name, neg_cluster)

            # M0: Emergent cluster computed from bracket [M+, M-]
            emergent = compute_emergent_cluster(
                pos_cluster, neg_cluster,
                facet.tongue, facet.tongue,
            )
            self.spaces[ManifoldID.EMERGENT].add_cluster(name, emergent)

    # -----------------------------------------------------------------
    # Core: Activate with Ternary Address
    # -----------------------------------------------------------------

    def activate(
        self,
        facet_name: str,
        intensity: float = 1.0,
        context: str = "",
        manifold: ManifoldID = ManifoldID.POSITIVE,
        spin: int = 1,
    ) -> Dict[str, Any]:
        """Activate a personality facet in a specific manifold space.

        Creates a new particle in the target manifold, then propagates
        through the 9-channel interaction matrix to connected manifolds.

        Returns full activation report with ternary addresses.
        """
        space = self.spaces.get(manifold)
        if space is None:
            return {"error": f"Unknown manifold: {manifold}"}

        cluster = space.clusters.get(facet_name)
        if cluster is None:
            return {"error": f"Facet '{facet_name}' not in {space.name}"}

        # Record pre-activation state
        old_activation = self.base.facets[facet_name].activation

        # Add new particle with spin
        direction = cluster.center * intensity
        noise = np.random.randn(DIM) * 0.02
        new_particle = _poincare_project(direction + noise)
        cluster.add_particle(new_particle, max(-1, min(1, spin)))

        # Activate base manifold
        activations = self.base.activate(facet_name, intensity, context)

        # Build ternary address for this activation
        address = TriManifoldAddress(
            source=manifold.value,
            target=manifold.value,  # Self-activation initially
            spin=max(-1, min(1, spin)),
        )

        # Propagate through interaction channels to other manifolds
        propagation_results = {}
        rho_e = compute_rho_e(np.array([intensity, len(context)]))

        for (src, tgt), channel in self.channels.items():
            if src != manifold.value:
                continue  # Only propagate FROM the activated manifold
            if src == tgt:
                continue  # Skip self-channel (already activated)

            # Transfer through channel
            transferred = channel.transfer(
                new_particle, rho_e, self.rho_e_threshold,
            )
            if transferred is not None:
                target_manifold = ManifoldID(tgt)
                target_space = self.spaces[target_manifold]
                target_cluster = target_space.clusters.get(facet_name)
                if target_cluster:
                    # Transferred particles get neutral spin
                    target_cluster.add_particle(transferred, spin=0)
                    propagation_results[channel.name] = {
                        "norm": round(float(np.linalg.norm(transferred)), 4),
                        "coupling": channel.coupling,
                    }

        # If we activated M+ or M-, recompute the emergent manifold
        if manifold != ManifoldID.EMERGENT:
            self._recompute_emergent(facet_name)

        # Drift detection
        new_activation = self.base.facets[facet_name].activation
        if abs(new_activation - old_activation) > 0.1:
            drift = DriftEvent(
                timestamp=time.time(),
                facet=facet_name,
                old_activation=old_activation,
                new_activation=new_activation,
                delta_vector=new_particle - cluster.center,
                context=context,
            )
            self.active_drifts.append(drift)

        # Provenance check
        personality_vec = self.base.get_personality_vector()
        provenance_valid, provenance_msg = validate_personality_provenance(
            personality_vec,
        )

        # Log interaction
        result = {
            "address": repr(address),
            "ternary_word": str(address.ternary_word),
            "decimal_index": address.decimal_index,
            "governance_vote": address.governance_vote,
            "manifold": space.name,
            "facet": facet_name,
            "spin": spin,
            "intensity": intensity,
            "propagation": propagation_results,
            "coherence": {
                name: round(s.compute_energy(), 4)
                for name, s in [
                    ("M+", self.spaces[ManifoldID.POSITIVE]),
                    ("M0", self.spaces[ManifoldID.EMERGENT]),
                    ("M-", self.spaces[ManifoldID.NEGATIVE]),
                ]
            },
            "active_drifts": len(self.active_drifts),
            "provenance_valid": provenance_valid,
            "activations": activations,
        }

        self.interaction_log.append(result)
        return result

    def _recompute_emergent(self, facet_name: str) -> None:
        """Recompute the emergent cluster for a facet from M+ and M-."""
        pos_space = self.spaces[ManifoldID.POSITIVE]
        neg_space = self.spaces[ManifoldID.NEGATIVE]
        emg_space = self.spaces[ManifoldID.EMERGENT]

        pos_cluster = pos_space.clusters.get(facet_name)
        neg_cluster = neg_space.clusters.get(facet_name)
        if pos_cluster is None or neg_cluster is None:
            return

        tongue = self.base.facets[facet_name].tongue
        new_emergent = compute_emergent_cluster(
            pos_cluster, neg_cluster, tongue, tongue,
        )
        emg_space.clusters[facet_name] = new_emergent

    # -----------------------------------------------------------------
    # Binary Intake
    # -----------------------------------------------------------------

    def intake_binary(
        self,
        bits: List[int],
        facet_name: str,
        context: str = "",
    ) -> List[Dict[str, Any]]:
        """Binary -> ternary intake pipeline.

        Converts binary data to balanced ternary, assigns manifolds,
        and activates the appropriate facets.

        This is "pseudo-binary deferred to ternary then run as code."
        """
        assignments = self.converter.intake(bits)
        results = []

        for manifold_id, trit in assignments:
            spin = trit.value  # Trit value doubles as spin
            result = self.activate(
                facet_name=facet_name,
                intensity=0.5 + abs(trit.value) * 0.3,
                context=context,
                manifold=manifold_id,
                spin=spin,
            )
            results.append(result)

        return results

    # -----------------------------------------------------------------
    # Context-Based Activation
    # -----------------------------------------------------------------

    def activate_from_context(self, text: str) -> Dict[str, Any]:
        """Infer which facets and manifolds to activate from text.

        Extends the base manifold's keyword detection with ternary
        manifold routing:
        - Questions / exploration -> M+ (expressed curiosity)
        - Emotional / reflective -> M- (depth empathy)
        - Complex / paradoxical  -> M0 (emergent insight)
        """
        text_lower = text.lower()

        # M+ triggers (expressed, outward)
        positive_triggers = {
            "curiosity": ["what", "how", "explore", "discover", "quest"],
            "wit": ["funny", "joke", "clever", "laugh", "haha"],
            "resolve": ["mission", "duty", "fight", "defend", "promise"],
        }

        # M- triggers (depth, inward)
        negative_triggers = {
            "wisdom": ["ancient", "remember", "elder", "deep", "history"],
            "empathy": ["feel", "sorry", "understand", "loss", "pain"],
            "vigilance": ["danger", "careful", "threat", "watch", "fear"],
        }

        # M0 triggers (emergent, paradoxical)
        emergent_triggers = {
            "curiosity": ["paradox", "why", "but", "however", "strange"],
            "wisdom": ["both", "and yet", "despite", "balance", "harmony"],
            "wit": ["irony", "absurd", "twist", "unexpected", "bittersweet"],
        }

        best_facet = None
        best_manifold = ManifoldID.POSITIVE
        best_score = 0

        for manifold, triggers in [
            (ManifoldID.POSITIVE, positive_triggers),
            (ManifoldID.NEGATIVE, negative_triggers),
            (ManifoldID.EMERGENT, emergent_triggers),
        ]:
            for facet_name, keywords in triggers.items():
                score = sum(1 for kw in keywords if kw in text_lower)
                if score > best_score:
                    best_score = score
                    best_facet = facet_name
                    best_manifold = manifold

        if best_facet:
            return self.activate(
                best_facet,
                intensity=min(1.0, best_score * 0.3),
                context=text,
                manifold=best_manifold,
                spin=best_manifold.value if best_manifold.value != 0 else 0,
            )

        # Default: low-intensity positive curiosity
        return self.activate("curiosity", 0.3, text, ManifoldID.POSITIVE, 0)

    # -----------------------------------------------------------------
    # Inter-Manifold Distance Metrics
    # -----------------------------------------------------------------

    def inter_manifold_distance(
        self,
        facet_name: str,
        manifold_a: ManifoldID,
        manifold_b: ManifoldID,
    ) -> float:
        """Compute hyperbolic distance between a facet's clusters
        across two different manifold spaces.

        Large distance = weakly connected manifolds for this facet.
        Small distance = strongly coupled (deep personality trait).
        """
        space_a = self.spaces.get(manifold_a)
        space_b = self.spaces.get(manifold_b)
        if space_a is None or space_b is None:
            return float("inf")

        cluster_a = space_a.clusters.get(facet_name)
        cluster_b = space_b.clusters.get(facet_name)
        if cluster_a is None or cluster_b is None:
            return float("inf")

        return _hyperbolic_distance(cluster_a.center, cluster_b.center)

    def tri_bridge_strength(self, facet_name: str) -> Dict[str, float]:
        """Compute bridge strengths between all three manifolds for a facet.

        Returns dict with keys: 'pos_emg', 'emg_neg', 'pos_neg'
        Each value = exp(-d_H(center_a, center_b))

        A facet with strong tri-bridges has "earned" personality depth:
        surface, emergence, and shadow are all tightly coupled.
        """
        d_pe = self.inter_manifold_distance(
            facet_name, ManifoldID.POSITIVE, ManifoldID.EMERGENT,
        )
        d_en = self.inter_manifold_distance(
            facet_name, ManifoldID.EMERGENT, ManifoldID.NEGATIVE,
        )
        d_pn = self.inter_manifold_distance(
            facet_name, ManifoldID.POSITIVE, ManifoldID.NEGATIVE,
        )

        return {
            "pos_emg": round(float(np.exp(-d_pe)), 4),
            "emg_neg": round(float(np.exp(-d_en)), 4),
            "pos_neg": round(float(np.exp(-d_pn)), 4),
            "tri_coupling": round(
                float(np.exp(-(d_pe + d_en + d_pn) / 3)), 4
            ),
        }

    # -----------------------------------------------------------------
    # Governance: 27-State Decision
    # -----------------------------------------------------------------

    def governance_from_address(
        self, address: TriManifoldAddress,
    ) -> Dict[str, Any]:
        """Compute governance decision from a ternary address.

        Uses the full 3-trit word to derive a decision:
        - If all three trits agree: strong consensus
        - If mixed: Kleene logic determines outcome
        - Final mapping: +1 -> ALLOW, 0 -> QUARANTINE, -1 -> DENY
        """
        src_trit = Trit(address.source)
        tgt_trit = Trit(address.target)
        spin_trit = Trit(address.spin)

        # Kleene AND of source and target
        channel_intent = trit_and(src_trit, tgt_trit)
        # Kleene OR with spin (spin can elevate a neutral channel)
        overall = trit_or(channel_intent, spin_trit)
        # Consensus check (do they agree?)
        consensus = trit_consensus(channel_intent, spin_trit)

        decision = trit_to_decision(overall)
        consensus_decision = trit_to_decision(consensus)
        confidence = 1.0 if overall == consensus else 0.6

        return {
            "address": repr(address),
            "decision": decision,
            "consensus": consensus_decision,
            "confidence": round(confidence, 2),
            "channel_intent": trit_to_decision(channel_intent),
            "spin_effect": trit_to_decision(spin_trit),
        }

    # -----------------------------------------------------------------
    # Drift Resolution (inherited from cluster lattice)
    # -----------------------------------------------------------------

    def resolve_drifts(self) -> List[Dict[str, Any]]:
        """Resolve personality drifts as training data."""
        now = time.time()
        training_pairs = []
        still_active = []

        for drift in self.active_drifts:
            age = now - drift.timestamp
            current = self.base.facets.get(drift.facet)
            if current is None:
                continue

            delta = abs(current.activation - drift.new_activation)
            if delta < 0.05:
                drift.resolved = True
                drift.resolution_time = now
                self.resolved_drifts.append(drift)
                pair = drift.to_training_pair()
                if pair:
                    training_pairs.append(pair)
            elif age > self.drift_timeout:
                self.resolved_drifts.append(drift)
            else:
                still_active.append(drift)

        self.active_drifts = still_active
        return training_pairs

    # -----------------------------------------------------------------
    # State Reporting
    # -----------------------------------------------------------------

    def get_tri_state(self) -> Dict[str, Any]:
        """Full tri-manifold state report."""
        manifold_states = {}
        for mid, space in self.spaces.items():
            cluster_data = {}
            for name, cluster in space.clusters.items():
                cluster_data[name] = {
                    "particles": len(cluster.particles),
                    "coherence": round(cluster.coherence(), 4),
                    "dominant_spin": cluster.dominant_spin(),
                    "radius": round(cluster.radius, 4),
                }
            manifold_states[space.name] = {
                "manifold_id": mid.value,
                "clusters": cluster_data,
                "energy": round(space.compute_energy(), 4),
                "center_norm": round(
                    float(np.linalg.norm(space.center)), 4,
                ),
            }

        # Channel statistics
        channel_stats = {}
        for (src, tgt), channel in self.channels.items():
            channel_stats[channel.name] = {
                "coupling": round(channel.coupling, 3),
                "transfers": channel.transfer_count,
                "blocked": channel.blocked_count,
            }

        # Tri-bridge strengths for each facet
        bridges = {}
        for name in self.base.facets:
            bridges[name] = self.tri_bridge_strength(name)

        # Lo Shu weights for each channel
        lo_shu = {}
        for (src, tgt) in self.channels:
            ps = TernaryPairState(src, tgt)
            lo_shu[ps.label] = lo_shu_weight(src, tgt)

        # Mirror symmetry check (asymmetry = information leak)
        asymmetry = lo_shu_symmetry_check(self.channels)

        return {
            "manifolds": manifold_states,
            "channels": channel_stats,
            "bridges": bridges,
            "lo_shu_weights": lo_shu,
            "mirror_asymmetry": round(asymmetry, 4),
            "total_interactions": len(self.interaction_log),
            "active_drifts": len(self.active_drifts),
            "resolved_drifts": len(self.resolved_drifts),
            "personality_tag": self.base.get_personality_tag(),
        }

    # -----------------------------------------------------------------
    # System Prompt Generation
    # -----------------------------------------------------------------

    def generate_system_prompt(self, context: str = "") -> str:
        """Generate system prompt with tri-manifold personality state.

        Extends the base prompt with three-space depth information.
        """
        base_prompt = self.base.generate_system_prompt(context)

        # Compute tri-bridge report for top facets
        active_facets = sorted(
            [(name, f.activation) for name, f in self.base.facets.items()
             if f.activation > 0.2],
            key=lambda x: -x[1],
        )[:3]

        tri_lines = []
        for name, act in active_facets:
            bridges = self.tri_bridge_strength(name)
            tri_coupling = bridges["tri_coupling"]
            depth_word = (
                "deeply integrated"
                if tri_coupling > 0.3
                else "developing"
                if tri_coupling > 0.1
                else "nascent"
            )
            tri_lines.append(
                f"  {name}: {depth_word} "
                f"(expressed={bridges['pos_emg']:.1f}, "
                f"emergent={bridges['emg_neg']:.1f}, "
                f"depth={bridges['pos_neg']:.1f})"
            )

        # Manifold energy balance
        e_pos = self.spaces[ManifoldID.POSITIVE].compute_energy()
        e_emg = self.spaces[ManifoldID.EMERGENT].compute_energy()
        e_neg = self.spaces[ManifoldID.NEGATIVE].compute_energy()
        total = e_pos + e_emg + e_neg + 1e-8
        balance = (
            f"Expression={e_pos / total:.0%}, "
            f"Emergence={e_emg / total:.0%}, "
            f"Depth={e_neg / total:.0%}"
        )

        if tri_lines:
            base_prompt += (
                "\n\nYour personality exists across three manifold spaces:\n"
                + "\n".join(tri_lines)
                + f"\n\nEnergy balance: {balance}"
                + "\n\nDraw from all three spaces: express what you know (M+), "
                "reveal what emerges from contradiction (M0), and ground it "
                "in depth you've earned (M-). The richest responses weave "
                "all three."
            )

        return base_prompt

    # -----------------------------------------------------------------
    # Training Data Export
    # -----------------------------------------------------------------

    def export_training_data(self) -> List[Dict[str, Any]]:
        """Export interaction history as training-format records.

        Each record includes the ternary address, making the model
        learn to map contexts to specific manifold interactions.
        """
        records = []
        for entry in self.interaction_log:
            records.append({
                "type": "tri_manifold_interaction",
                "ternary_word": entry.get("ternary_word", ""),
                "governance_vote": entry.get("governance_vote", ""),
                "facet": entry.get("facet", ""),
                "manifold": entry.get("manifold", ""),
                "spin": entry.get("spin", 0),
                "coherence": entry.get("coherence", {}),
            })
        return records
