"""Tri-vector cross-braid embedding layer for poly-embedded JEPA receipts.

Re-projects a ``PolyEmbedding`` into the canonical fast/memory/governance
triad used by ``src/harmonic/sheaf_consensus_gate.py`` and stamps it with
the order-dependent ordered hash discipline of ``src/crypto/tri_bundle.py``.

The output is a topological fingerprint:

- three vectors covering immediate, smoothed, and provenance signal lanes
- a per-dimension dominant-axis walk (fast / memory / governance)
- a crossing count (where the dominant axis switches)
- an order-dependent SHA3-256 hash that detects vector reordering
- a decision in {ALLOW, QUARANTINE, DENY} matched to the sheaf gate bands

The ``ordered_hash`` is non-commutative under permutation of the three
vectors, which catches replay/permutation-style attacks where the SHA-256
packet hash on the underlying ``PolyEmbedding`` could in principle be
preserved by a colluding adversary that shuffles surfaces.
"""

from __future__ import annotations

import hashlib
import itertools
import math
import struct
from dataclasses import dataclass
from typing import Sequence

from .atomic_tokenization import TONGUES
from .poly_embedded_jepa import (
    PHI,
    CodingSystem,
    PolyEmbedding,
    build_poly_embedding,
    normalized_tongue_weights,
)

SCHEMA_VERSION = "scbe_tri_braid_embedding_v1"

ALLOW = "ALLOW"
QUARANTINE = "QUARANTINE"
DENY = "DENY"

_ALLOW_TRIADIC = 0.70
_QUARANTINE_TRIADIC = 0.30
_ALLOW_MIN_MAG = 0.30
_DENY_MIN_MAG = 0.10

_AXIS_LABELS = ("fast", "memory", "governance")

# Strand ordering for the B_3 braid group: fast=1, memory=2, governance=3.
# sigma_1 swaps strands 1 and 2 (fast <-> memory); sigma_2 swaps strands 2
# and 3 (memory <-> governance). Generators are integer-encoded as
# +1 = sigma_1, -1 = sigma_1^-1, +2 = sigma_2, -2 = sigma_2^-1.
_LANE_STRAND: dict[str, int] = {"fast": 0, "memory": 1, "governance": 2}

_TERNARY_DEAD_BAND = 0.30
_AXIS_TRIPLETS: tuple[tuple[int, int, int], ...] = tuple(itertools.combinations(range(6), 3))


@dataclass(frozen=True)
class TriadicAxisAnchor:
    """Cross-lane sign-pattern agreement at a triple of tile dimensions.

    Adapts the NeuroGolf triadic-anchor pattern (`src/neurogolf/triadic_anchor.py`)
    to a per-embedding signal: a triple of axes is an "anchor" when at least a
    majority of the fast/memory/governance lanes share the same ternary sign
    pattern at those axes. Quality = cross_lane_stability * mean_strength.
    """

    axes: tuple[int, int, int]
    sign_pattern: tuple[int, int, int]
    cross_lane_stability: float
    mean_strength: float

    @property
    def quality(self) -> float:
        return round(self.cross_lane_stability * self.mean_strength, 8)


@dataclass(frozen=True)
class TriBraidSignature:
    """Topological fingerprint of a poly-embedded JEPA concept."""

    schema_version: str
    fast: tuple[float, ...]
    memory: tuple[float, ...]
    governance: tuple[float, ...]
    dominant_axes: tuple[str, ...]
    crossing_count: int
    triadic_stable: float
    ordered_hash: str
    decision: str
    invariants: tuple[str, ...]


def _system_to_tongue_index(system_id: str) -> int:
    digest = hashlib.sha256(system_id.encode("utf-8")).digest()
    return digest[0] % len(TONGUES)


def _governance_vector(coding_systems: Sequence[CodingSystem]) -> tuple[float, ...]:
    """Build a 6-dim provenance vector from coding-system contributions.

    Each system maps deterministically to one of the six tongues and
    contributes that tongue's normalized phi weight. The resulting vector
    is centered into roughly the (-1, 1) range so its magnitude is
    comparable to the JEPA latent and prediction surfaces.
    """
    weights = normalized_tongue_weights()
    accumulator = [0.0] * len(TONGUES)
    if not coding_systems:
        return tuple(accumulator)
    for system in coding_systems:
        tongue_idx = _system_to_tongue_index(system.system_id)
        tongue = TONGUES[tongue_idx]
        accumulator[tongue_idx] += weights[tongue]
    total = sum(accumulator)
    if total == 0.0:
        return tuple(accumulator)
    centered = [(value / total) * 2.0 - (1.0 / len(TONGUES)) for value in accumulator]
    return tuple(round(v, 8) for v in centered)


def _ternary_sign(value: float) -> int:
    if value > _TERNARY_DEAD_BAND:
        return 1
    if value < -_TERNARY_DEAD_BAND:
        return -1
    return 0


def _dominant_axis(values: tuple[float, float, float]) -> str:
    fast, memory, governance = values
    return max(
        zip(_AXIS_LABELS, (abs(fast), abs(memory), abs(governance))),
        key=lambda pair: pair[1],
    )[0]


def _walk_dominant_axes(
    fast: tuple[float, ...],
    memory: tuple[float, ...],
    governance: tuple[float, ...],
) -> tuple[str, ...]:
    return tuple(_dominant_axis((fast[i], memory[i], governance[i])) for i in range(len(fast)))


def _count_crossings(axes: tuple[str, ...]) -> int:
    return sum(1 for a, b in zip(axes, axes[1:]) if a != b)


def _vector_norm(vec: tuple[float, ...]) -> float:
    return math.sqrt(sum(v * v for v in vec))


def _triadic_stability(
    fast: tuple[float, ...],
    memory: tuple[float, ...],
    governance: tuple[float, ...],
) -> float:
    norms = [_vector_norm(fast), _vector_norm(memory), _vector_norm(governance)]
    max_norm = max(norms)
    min_norm = min(norms)
    if max_norm == 0.0:
        return 0.0
    imbalance = (max_norm - min_norm) / max_norm
    return max(0.0, min(1.0, 1.0 - imbalance))


def _decide(triadic_stable: float, min_norm: float) -> str:
    if triadic_stable < _QUARANTINE_TRIADIC or min_norm < _DENY_MIN_MAG:
        return DENY
    if triadic_stable >= _ALLOW_TRIADIC and min_norm >= _ALLOW_MIN_MAG:
        return ALLOW
    return QUARANTINE


def _ordered_hash(
    fast: tuple[float, ...],
    memory: tuple[float, ...],
    governance: tuple[float, ...],
) -> str:
    """Order-dependent hash. Labels are emitted before each vector so a
    permutation of the (fast, memory, governance) inputs produces a
    different digest even when the vectors themselves are identical.
    """
    digest = hashlib.sha3_256()
    digest.update(SCHEMA_VERSION.encode("utf-8"))
    for label, vector in zip(_AXIS_LABELS, (fast, memory, governance)):
        digest.update(label.encode("utf-8"))
        digest.update(b"|")
        for value in vector:
            digest.update(struct.pack(">d", float(value)))
    return digest.hexdigest()


def tri_braid_signature(embedding: PolyEmbedding) -> TriBraidSignature:
    """Compute the tri-vector cross-braid signature for a poly-embedded JEPA receipt."""
    fast = tuple(embedding.jepa_latent)
    memory = tuple(embedding.jepa_prediction)
    governance = _governance_vector(embedding.coding_systems)

    if not (len(fast) == len(memory) == len(governance)):
        raise ValueError("fast, memory, and governance vectors must share length")

    axes = _walk_dominant_axes(fast, memory, governance)
    crossings = _count_crossings(axes)
    triadic_stable = _triadic_stability(fast, memory, governance)
    min_norm = min(_vector_norm(fast), _vector_norm(memory), _vector_norm(governance))
    decision = _decide(triadic_stable, min_norm)
    ordered = _ordered_hash(fast, memory, governance)

    return TriBraidSignature(
        schema_version=SCHEMA_VERSION,
        fast=fast,
        memory=memory,
        governance=governance,
        dominant_axes=axes,
        crossing_count=crossings,
        triadic_stable=round(triadic_stable, 8),
        ordered_hash=ordered,
        decision=decision,
        invariants=(
            "vectors_share_length",
            "axes_in_three_label_set",
            "crossing_count_in_zero_to_n_minus_one",
            "ordered_hash_is_non_commutative",
            "decision_in_allow_quarantine_deny",
        ),
    )


def _adjacent_swap_generator(from_axis: str, to_axis: str) -> tuple[int, ...]:
    """Map an axis transition to a B_3 generator sequence.

    Adjacent transitions emit a single generator (sigma_1, sigma_2 or
    their inverses). Non-adjacent transitions (fast <-> governance)
    decompose through the middle strand.
    """
    if from_axis == to_axis:
        return ()
    a = _LANE_STRAND[from_axis]
    b = _LANE_STRAND[to_axis]
    if (a, b) == (0, 1):
        return (1,)
    if (a, b) == (1, 0):
        return (-1,)
    if (a, b) == (1, 2):
        return (2,)
    if (a, b) == (2, 1):
        return (-2,)
    if (a, b) == (0, 2):
        return (1, 2)
    if (a, b) == (2, 0):
        return (-2, -1)
    raise ValueError(f"unknown lane transition {from_axis} -> {to_axis}")


def braid_word(signature: TriBraidSignature) -> tuple[int, ...]:
    """Encode the dominant-axis walk as a B_3 braid word.

    Each adjacent-axis transition produces one or two generators:
    sigma_1 (=+1), sigma_2 (=+2), and their inverses. Concatenating
    these across the walk gives a word in the free group on
    {sigma_1, sigma_2} that represents the cross-braid topology.
    """
    word: list[int] = []
    axes = signature.dominant_axes
    for prev_axis, next_axis in zip(axes, axes[1:]):
        word.extend(_adjacent_swap_generator(prev_axis, next_axis))
    return tuple(word)


def braid_word_length(signature: TriBraidSignature) -> int:
    return len(braid_word(signature))


def extract_axis_anchors(
    signature: TriBraidSignature,
    *,
    min_stability: float = 2.0 / 3.0,
    min_strength: float = 0.0,
) -> tuple[TriadicAxisAnchor, ...]:
    """Find stable cross-lane sign-pattern agreements across triples of axes.

    For each triplet ``(i, j, k)`` chosen from the six tile dimensions, compute
    the ternary sign pattern in each of the three lanes (fast/memory/governance)
    and keep the triplet when a majority share the same pattern. Anchors are
    returned ordered by ``quality`` descending so callers can take the top-k.
    """
    lanes = (signature.fast, signature.memory, signature.governance)
    if not all(len(lane) == 6 for lane in lanes):
        raise ValueError("axis anchors require six-dimensional fast/memory/governance vectors")

    anchors: list[TriadicAxisAnchor] = []
    for axes in _AXIS_TRIPLETS:
        patterns: list[tuple[int, int, int]] = []
        magnitudes: list[float] = []
        for lane in lanes:
            patterns.append(tuple(_ternary_sign(lane[i]) for i in axes))
            magnitudes.append(sum(abs(lane[i]) for i in axes) / len(axes))

        counts: dict[tuple[int, int, int], int] = {}
        for pattern in patterns:
            counts[pattern] = counts.get(pattern, 0) + 1
        majority_pattern = max(counts, key=lambda p: counts[p])
        stability = counts[majority_pattern] / len(lanes)
        if stability < min_stability:
            continue

        mean_strength = sum(magnitudes) / len(magnitudes)
        if mean_strength < min_strength:
            continue

        anchors.append(
            TriadicAxisAnchor(
                axes=axes,
                sign_pattern=majority_pattern,
                cross_lane_stability=round(stability, 8),
                mean_strength=round(mean_strength, 8),
            )
        )

    anchors.sort(key=lambda a: a.quality, reverse=True)
    return tuple(anchors)


def verify_tri_braid_signature(
    signature: TriBraidSignature,
    embedding: PolyEmbedding,
) -> dict[str, object]:
    """Recompute the signature from the embedding and compare every surface.

    Also exercises the non-commutativity invariant by hashing a permuted
    ordering and asserting it differs from the canonical hash.
    """
    reconstructed = tri_braid_signature(embedding)
    permuted_hash = _ordered_hash(signature.memory, signature.fast, signature.governance)

    checks = {
        "fast_matches": signature.fast == reconstructed.fast,
        "memory_matches": signature.memory == reconstructed.memory,
        "governance_matches": signature.governance == reconstructed.governance,
        "axes_match": signature.dominant_axes == reconstructed.dominant_axes,
        "crossing_count_matches": signature.crossing_count == reconstructed.crossing_count,
        "ordered_hash_matches": signature.ordered_hash == reconstructed.ordered_hash,
        "decision_matches": signature.decision == reconstructed.decision,
        "ordered_hash_non_commutative": signature.ordered_hash != permuted_hash,
        "axes_in_label_set": all(axis in _AXIS_LABELS for axis in signature.dominant_axes),
        "crossings_within_bound": 0 <= signature.crossing_count < max(1, len(signature.fast)),
        "decision_in_allowed_set": signature.decision in {ALLOW, QUARANTINE, DENY},
        "triadic_stable_in_unit_interval": 0.0 <= signature.triadic_stable <= 1.0,
    }
    return {
        "ok": all(checks.values()),
        "schema_version": SCHEMA_VERSION,
        "checks": checks,
        "failed": [name for name, ok in checks.items() if not ok],
    }


# ---------------------------------------------------------------------------
# Knot/braid invariants from algebraic topology
# ---------------------------------------------------------------------------


def braid_exponent_sum(signature: TriBraidSignature) -> int:
    """Abelianization B_3 -> Z. Invariant under conjugacy and Yang-Baxter.

    Maps each generator to its sign and sums. Equivalent braid words
    (under cyclic permutation, sigma_i sigma_j = sigma_j sigma_i for
    |i - j| > 1, and Yang-Baxter sigma_1 sigma_2 sigma_1 =
    sigma_2 sigma_1 sigma_2) all share the same exponent sum.
    """
    return sum(1 if g > 0 else -1 for g in braid_word(signature))


def braid_writhe(signature: TriBraidSignature) -> int:
    """Writhe = signed crossing count.

    For braid closures this equals the exponent sum; the function name
    surfaces the knot-theoretic interpretation (positive minus negative
    crossings) for callers reasoning about topological charge.
    """
    return braid_exponent_sum(signature)


# ---------------------------------------------------------------------------
# Hamiltonian-Braid 9-state governance classifier
# ---------------------------------------------------------------------------

# 9 dual-ternary states from src/ai_brain/hamiltonian-braid.ts
RESONANT_LOCK = "RESONANT_LOCK"
FORWARD_THRUST = "FORWARD_THRUST"
CREATIVE_TENSION_A = "CREATIVE_TENSION_A"
PERPENDICULAR_POS = "PERPENDICULAR_POS"
ZERO_GRAVITY_STATE = "ZERO_GRAVITY"
PERPENDICULAR_NEG = "PERPENDICULAR_NEG"
CREATIVE_TENSION_B = "CREATIVE_TENSION_B"
BACKWARD_CHECK = "BACKWARD_CHECK"
COLLAPSE_ATTRACTOR = "COLLAPSE_ATTRACTOR"

_BRAID_STATE_TABLE: dict[tuple[int, int], str] = {
    (1, 1): RESONANT_LOCK,
    (1, 0): FORWARD_THRUST,
    (1, -1): CREATIVE_TENSION_A,
    (0, 1): PERPENDICULAR_POS,
    (0, 0): ZERO_GRAVITY_STATE,
    (0, -1): PERPENDICULAR_NEG,
    (-1, 1): CREATIVE_TENSION_B,
    (-1, 0): BACKWARD_CHECK,
    (-1, -1): COLLAPSE_ATTRACTOR,
}

_BRAID_TRUST_LEVEL: dict[str, str] = {
    RESONANT_LOCK: "maximum",
    FORWARD_THRUST: "high",
    CREATIVE_TENSION_A: "medium",
    CREATIVE_TENSION_B: "medium",
    PERPENDICULAR_POS: "low",
    PERPENDICULAR_NEG: "low",
    ZERO_GRAVITY_STATE: "consensus",
    BACKWARD_CHECK: "audit",
    COLLAPSE_ATTRACTOR: "block",
}

_BRAID_SECURITY_ACTION: dict[str, str] = {
    RESONANT_LOCK: "INSTANT_APPROVE",
    FORWARD_THRUST: "STANDARD_PATH",
    CREATIVE_TENSION_A: "FRACTAL_INSPECT",
    CREATIVE_TENSION_B: "FRACTAL_INSPECT",
    PERPENDICULAR_POS: "REANCHOR",
    PERPENDICULAR_NEG: "REANCHOR",
    ZERO_GRAVITY_STATE: "HOLD_QUORUM",
    BACKWARD_CHECK: "ROLLBACK",
    COLLAPSE_ATTRACTOR: "HARD_DENY",
}


@dataclass(frozen=True)
class BraidGovernance:
    """9-state governance descriptor matching ``src/ai_brain/hamiltonian-braid.ts``."""

    state: str
    primary_trit: int
    mirror_trit: int
    trust_level: str
    security_action: str


def _aggregate_ternary(signature: TriBraidSignature) -> tuple[int, int]:
    """Reduce the three signal vectors into a (primary, mirror) ternary pair.

    primary = ternary sign of (mean(fast) - mean(memory))
    mirror  = ternary sign of (mean(memory) - mean(governance))

    These two trits index into the 9-state phase diagram.
    """
    fast_mean = sum(signature.fast) / len(signature.fast)
    mem_mean = sum(signature.memory) / len(signature.memory)
    gov_mean = sum(signature.governance) / len(signature.governance)
    return _ternary_sign(fast_mean - mem_mean), _ternary_sign(mem_mean - gov_mean)


def classify_braid_governance(signature: TriBraidSignature) -> BraidGovernance:
    """Map a tri-braid signature to one of nine Hamiltonian-Braid trust states."""
    primary, mirror = _aggregate_ternary(signature)
    state = _BRAID_STATE_TABLE[(primary, mirror)]
    return BraidGovernance(
        state=state,
        primary_trit=primary,
        mirror_trit=mirror,
        trust_level=_BRAID_TRUST_LEVEL[state],
        security_action=_BRAID_SECURITY_ACTION[state],
    )


# ---------------------------------------------------------------------------
# L11 Temporal Braid: previous/current/next admissibility
# ---------------------------------------------------------------------------

# Limits taken from src/crypto/dual_lattice_integration.py.
_TEMPORAL_VELOCITY_LIMIT = 2.5
_TEMPORAL_ACCELERATION_LIMIT = 1.5

_DECISION_LEVEL = {ALLOW: 2, QUARANTINE: 1, DENY: 0}


@dataclass(frozen=True)
class TemporalAdmissibility:
    """Result of an L11 (prev, curr, next) admissibility check on signatures."""

    admit: bool
    velocity: float
    acceleration: float
    causality_monotone: bool
    velocity_within_bound: bool
    acceleration_within_bound: bool
    reason: str


def _signature_norm(signature: TriBraidSignature) -> float:
    return math.sqrt(
        sum(v * v for v in signature.fast)
        + sum(v * v for v in signature.memory)
        + sum(v * v for v in signature.governance)
    )


def temporal_braid_admit(
    prev_sig: TriBraidSignature,
    curr_sig: TriBraidSignature,
    next_sig: TriBraidSignature,
    *,
    velocity_limit: float = _TEMPORAL_VELOCITY_LIMIT,
    acceleration_limit: float = _TEMPORAL_ACCELERATION_LIMIT,
) -> TemporalAdmissibility:
    """L11 check on three temporally adjacent tri-braid signatures.

    Velocity         = mean(|d_norm|) across the two adjacent steps.
    Acceleration     = |delta velocity| between the two steps.
    Causality monotone = governance decision may relax by at most one
                         level per step (matches the sheaf gate's
                         twisted-edge restriction map).
    """
    n_prev = _signature_norm(prev_sig)
    n_curr = _signature_norm(curr_sig)
    n_next = _signature_norm(next_sig)

    v1 = abs(n_curr - n_prev)
    v2 = abs(n_next - n_curr)
    velocity = (v1 + v2) / 2.0
    acceleration = abs(v2 - v1)

    levels = (
        _DECISION_LEVEL[prev_sig.decision],
        _DECISION_LEVEL[curr_sig.decision],
        _DECISION_LEVEL[next_sig.decision],
    )
    causality_monotone = (levels[0] - levels[1] <= 1) and (levels[1] - levels[2] <= 1)
    velocity_ok = velocity <= velocity_limit
    accel_ok = acceleration <= acceleration_limit
    admit = causality_monotone and velocity_ok and accel_ok

    if admit:
        reason = "all temporal admissibility constraints satisfied"
    else:
        problems = []
        if not causality_monotone:
            problems.append("decision drops more than one level between adjacent steps")
        if not velocity_ok:
            problems.append(f"velocity {velocity:.4f} exceeds limit {velocity_limit}")
        if not accel_ok:
            problems.append(f"acceleration {acceleration:.4f} exceeds limit {acceleration_limit}")
        reason = "; ".join(problems)

    return TemporalAdmissibility(
        admit=admit,
        velocity=round(velocity, 8),
        acceleration=round(acceleration, 8),
        causality_monotone=causality_monotone,
        velocity_within_bound=velocity_ok,
        acceleration_within_bound=accel_ok,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Sacred Egg envelope (geometric ritual seal over the tri-braid signature)
# ---------------------------------------------------------------------------

SACRED_EGG_SCHEMA = "scbe_sacred_egg_seal_v1"
_RING_RADIUS: tuple[float, ...] = tuple(round((PHI**i) / (PHI**5), 8) for i in range(6))


@dataclass(frozen=True)
class SacredEggSeal:
    """Ritual-style envelope binding a tri-braid signature to a phi ring.

    Inspired by the Notion 'Sacred Eggs: Ritual-Based Genesis Protocol'
    and 'Sacred Egg Data Packets' pages. Each seal pins the signature
    to one of six phi-scaled GeoSeal rings; the SHA3 seal hash binds
    the (ordered_hash, ring_index, ring_radius, schema) tuple so any
    drift from the source signature breaks the seal.
    """

    schema_version: str
    ordered_hash: str
    ring_index: int
    ring_radius: float
    egg_seal_sha3: str


def _egg_ring_index(signature: TriBraidSignature) -> int:
    fast = signature.fast
    return max(range(len(fast)), key=lambda i: abs(fast[i]))


def seal_sacred_egg(signature: TriBraidSignature) -> SacredEggSeal:
    ring = _egg_ring_index(signature)
    radius = _RING_RADIUS[ring]
    seal_input = f"{SCHEMA_VERSION}|{signature.ordered_hash}|{ring}|{radius:.8f}"
    seal_hash = hashlib.sha3_256(seal_input.encode("utf-8")).hexdigest()
    return SacredEggSeal(
        schema_version=SACRED_EGG_SCHEMA,
        ordered_hash=signature.ordered_hash,
        ring_index=ring,
        ring_radius=radius,
        egg_seal_sha3=seal_hash,
    )


def verify_sacred_egg(seal: SacredEggSeal, signature: TriBraidSignature) -> dict[str, object]:
    expected = seal_sacred_egg(signature)
    checks = {
        "ordered_hash_matches": seal.ordered_hash == signature.ordered_hash,
        "ring_index_in_range": 0 <= seal.ring_index < len(TONGUES),
        "ring_radius_in_unit_interval": 0.0 < seal.ring_radius <= 1.0,
        "seal_recomputes": seal.egg_seal_sha3 == expected.egg_seal_sha3,
    }
    return {
        "ok": all(checks.values()),
        "schema_version": seal.schema_version,
        "checks": checks,
        "failed": [name for name, ok in checks.items() if not ok],
    }


# ---------------------------------------------------------------------------
# Production governance receipt — tested surface used by the n8n bridge
# ---------------------------------------------------------------------------

GOVERNANCE_RECEIPT_SCHEMA = "scbe_governance_receipt_v1"


def governance_receipt(
    content: str,
    *,
    masked_row: int = 0,
    masked_col: int = 0,
) -> dict[str, object]:
    """Build a serializable topological governance receipt for arbitrary text.

    Composes the full stack into one dict:
    - poly-embedded JEPA ``binary_packet_sha256`` (provenance)
    - tri-vector cross-braid ``ordered_hash`` (non-commutative)
    - ``crossing_count``, ``braid_word_length``, ``braid_exponent_sum`` (topology)
    - 9-state Hamiltonian-Braid governance state with trust + action
    - Sacred Egg ring seal

    Used by the ``/v1/governance/scan`` route and any other publisher that
    needs a tamper-evident receipt for an ingested record.
    """
    if not content.strip():
        raise ValueError("governance_receipt requires non-empty content")

    embedding = build_poly_embedding(content, masked_row=masked_row, masked_col=masked_col)
    signature = tri_braid_signature(embedding)
    governance = classify_braid_governance(signature)
    seal = seal_sacred_egg(signature)

    # Local import keeps tri_cone_embedding optional and avoids the
    # circular dependency it would create at module load time.
    from .tri_cone_embedding import tri_cone_signature

    cone = tri_cone_signature(signature)

    # Local import: hjepa_embedding pulls in tri_braid_embedding itself,
    # so it must be imported at runtime rather than at module load.
    from .hjepa_embedding import hjepa_signature

    hjepa = hjepa_signature(content, masked_row=masked_row, masked_col=masked_col)

    return {
        "schema_version": GOVERNANCE_RECEIPT_SCHEMA,
        "binary_packet_sha256": embedding.binary_packet_sha256,
        "ordered_hash": signature.ordered_hash,
        "crossing_count": signature.crossing_count,
        "triadic_stable": signature.triadic_stable,
        "decision": signature.decision,
        "braid_word_length": braid_word_length(signature),
        "braid_exponent_sum": braid_exponent_sum(signature),
        "governance_state": governance.state,
        "primary_trit": governance.primary_trit,
        "mirror_trit": governance.mirror_trit,
        "trust_level": governance.trust_level,
        "security_action": governance.security_action,
        "egg_seal_sha3": seal.egg_seal_sha3,
        "ring_index": seal.ring_index,
        "ring_radius": seal.ring_radius,
        "tile": embedding.masked_tile,
        "tongue": embedding.tile_node.tongue,
        "cone_governance": cone.cone_governance,
        "cone_hash": cone.cone_hash,
        "cone_positive_count": cone.positive_membership_count,
        "cone_shadow_count": cone.shadow_membership_count,
        "cone_triple_intersection_score": cone.triple_intersection_score,
        "cone_triple_shadow_score": cone.triple_shadow_score,
        "cone_interference_score": cone.interference_score,
        "cone_plateau_imbalance": cone.plateau_imbalance,
        "cone_joint_embedding": cone.joint_embedding,
        "cone_joint_shadow": cone.joint_shadow,
        "hjepa_hash": hjepa.hjepa_hash,
        "hjepa_l1_loss": hjepa.levels[0].loss,
        "hjepa_l2_loss": hjepa.levels[1].loss,
        "hjepa_l3_loss": hjepa.levels[2].loss,
        "hjepa_triangle_residual": hjepa.triangle_residual,
        "hjepa_total_loss": hjepa.total_loss,
    }
