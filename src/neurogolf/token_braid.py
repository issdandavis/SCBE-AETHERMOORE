from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER

from .arc_io import ARCTask
from .family_lattice import AXES, FAMILY_TOPOLOGIES, FLAT_FAMILY_ORDER, task_topology
from .pqc_braid_thread import ThreatVerdict, detect_threat, pqc_thread_score


BRAID_TONGUES = ("CA", "UM", "DR")

# Phi weights per tongue (KO=1.0 baseline, DR=11.09 most sensitive).
# Defined here so _VALID_TOKENIZER_CODES can be derived from the single source.
_TONGUE_PHI_WEIGHTS: dict[str, float] = {
    "ko": 1.00,
    "av": 1.62,
    "ru": 2.62,
    "ca": 4.24,
    "um": 6.85,
    "dr": 11.09,
}

_VALID_TOKENIZER_CODES: frozenset[str] = frozenset(_TONGUE_PHI_WEIGHTS)


def _tokenizer_code(tongue: str) -> str:
    code = tongue.lower()
    if code not in _VALID_TOKENIZER_CODES:
        raise ValueError(f"Unknown tongue '{tongue}' — expected one of {_VALID_TOKENIZER_CODES}")
    return code


@dataclass(frozen=True)
class TokenBraidSignature:
    family: str
    packet: bytes
    tokens: tuple[str, ...]
    triad: tuple[int, ...]


@dataclass(frozen=True)
class TritVoxel:
    neg_band: frozenset[int]
    zero_band: frozenset[int]
    pos_band: frozenset[int]

    @classmethod
    def from_triad(cls, triad: tuple[int, ...]) -> "TritVoxel":
        return cls(
            neg_band=frozenset(i for i, state in enumerate(triad) if state < 0),
            zero_band=frozenset(i for i, state in enumerate(triad) if state == 0),
            pos_band=frozenset(i for i, state in enumerate(triad) if state > 0),
        )


def _quantize_unit_interval(values: np.ndarray) -> bytes:
    clipped = np.clip(values, 0.0, 1.0)
    quantized = np.rint(clipped * 255.0).astype(np.uint8)
    return bytes(int(v) for v in quantized.tolist())


def _triadic_projection(data: bytes) -> tuple[int, ...]:
    triads: list[int] = []
    for value in data:
        if value < 85:
            triads.append(-1)
        elif value < 170:
            triads.append(0)
        else:
            triads.append(1)
    return tuple(triads)


def _packet_from_topology(vector: np.ndarray) -> bytes:
    return _quantize_unit_interval(vector)


def task_packet(task: ARCTask) -> bytes:
    return _packet_from_topology(task_topology(task))


def task_tokens(task: ARCTask, tongue: str = "CA") -> tuple[str, ...]:
    packet = task_packet(task)
    return tuple(SACRED_TONGUE_TOKENIZER.encode_bytes(_tokenizer_code(tongue), packet))


def task_triad(task: ARCTask) -> tuple[int, ...]:
    return _triadic_projection(task_packet(task))


def task_trit_voxel(task: ARCTask) -> TritVoxel:
    return TritVoxel.from_triad(task_triad(task))


def _family_packet(family: str) -> bytes:
    topology = FAMILY_TOPOLOGIES[family]
    return _packet_from_topology(topology.as_array())


def family_trit_voxel(family: str) -> TritVoxel:
    family_sig = next(iter(FAMILY_BRAID_SIGNATURES[family].values()))
    return TritVoxel.from_triad(family_sig.triad)


def family_token_braid_signatures(tongues: tuple[str, ...] = BRAID_TONGUES) -> dict[str, dict[str, TokenBraidSignature]]:
    out: dict[str, dict[str, TokenBraidSignature]] = {}
    for family in FAMILY_TOPOLOGIES:
        packet = _family_packet(family)
        triad = _triadic_projection(packet)
        out[family] = {}
        for tongue in tongues:
            tokens = tuple(SACRED_TONGUE_TOKENIZER.encode_bytes(_tokenizer_code(tongue), packet))
            out[family][tongue] = TokenBraidSignature(
                family=family,
                packet=packet,
                tokens=tokens,
                triad=triad,
            )
    return out


FAMILY_BRAID_SIGNATURES = family_token_braid_signatures()

# Thread 3: pre-built PQC fingerprints for each family (built once at import)
FAMILY_PQC_PACKETS: dict[str, bytes] = {
    family: next(iter(FAMILY_BRAID_SIGNATURES[family].values())).packet
    for family in FAMILY_TOPOLOGIES
}


def _token_alignment(
    task_tokens_by_tongue: dict[str, tuple[str, ...]],
    task_token_sets: dict[str, set[str]],
    family: str,
    tongues: tuple[str, ...],
) -> float:
    score = 0.0
    for tongue in tongues:
        family_tokens = FAMILY_BRAID_SIGNATURES[family][tongue].tokens
        overlap = sum(1 for token in family_tokens if token in task_token_sets[tongue])
        overlap_score = overlap / max(len(family_tokens), 1)
        task_tokens = task_tokens_by_tongue[tongue]
        # Positional agreement is more diagnostic than set membership once compound
        # families introduce repeated tokens that can inflate overlap.
        positional_matches = sum(
            1 for idx, token in enumerate(family_tokens) if idx < len(task_tokens) and token == task_tokens[idx]
        )
        positional_score = positional_matches / max(len(family_tokens), 1)
        score += 0.45 * overlap_score + 0.55 * positional_score
    return score / max(len(tongues), 1)


def _packet_alignment(task_packet_bytes: bytes, family: str) -> float:
    family_packet = next(iter(FAMILY_BRAID_SIGNATURES[family].values())).packet
    if len(task_packet_bytes) != len(family_packet):
        return 0.0
    task_arr = np.frombuffer(task_packet_bytes, dtype=np.uint8).astype(np.float64)
    family_arr = np.frombuffer(family_packet, dtype=np.uint8).astype(np.float64)
    return 1.0 - float(np.mean(np.abs(task_arr - family_arr)) / 255.0)


def _jaccard(left: frozenset[int], right: frozenset[int]) -> float:
    union = left | right
    if not union:
        return 1.0
    return len(left & right) / len(union)


def _trit_voxel_alignment(task_voxel: TritVoxel, family_voxel: TritVoxel) -> float:
    neg_score = _jaccard(task_voxel.neg_band, family_voxel.neg_band)
    zero_score = _jaccard(task_voxel.zero_band, family_voxel.zero_band)
    pos_score = _jaccard(task_voxel.pos_band, family_voxel.pos_band)
    return 0.4 * neg_score + 0.2 * zero_score + 0.4 * pos_score


def _triad_alignment(task_triad_vec: tuple[int, ...], family: str) -> float:
    task_voxel = TritVoxel.from_triad(task_triad_vec)
    return _trit_voxel_alignment(task_voxel, family_trit_voxel(family))


def _harmonic_alignment(task_tokens_by_tongue: dict[str, tuple[str, ...]], family: str, tongues: tuple[str, ...]) -> float:
    score = 0.0
    for tongue in tongues:
        tokenizer_tongue = _tokenizer_code(tongue)
        task_fp = SACRED_TONGUE_TOKENIZER.compute_harmonic_fingerprint(
            tokenizer_tongue, list(task_tokens_by_tongue[tongue])
        )
        family_fp = SACRED_TONGUE_TOKENIZER.compute_harmonic_fingerprint(
            tokenizer_tongue, list(FAMILY_BRAID_SIGNATURES[family][tongue].tokens)
        )
        score += 1.0 - min(abs(task_fp - family_fp), 1.0)
    return score / max(len(tongues), 1)


def _token_braid_scores(task: ARCTask, tongues: tuple[str, ...] = BRAID_TONGUES) -> list[tuple[str, float]]:
    task_packet_bytes = task_packet(task)
    task_tokens_by_tongue = {
        tongue: tuple(SACRED_TONGUE_TOKENIZER.encode_bytes(_tokenizer_code(tongue), task_packet_bytes))
        for tongue in tongues
    }
    task_token_sets = {tongue: set(tokens) for tongue, tokens in task_tokens_by_tongue.items()}
    task_triad_vec = _triadic_projection(task_packet_bytes)

    scored: list[tuple[str, float]] = []
    for family, topology in FAMILY_TOPOLOGIES.items():
        # Thread 1: Sacred Tongue bijective token braid (CA/UM/DR)
        token_score = _token_alignment(task_tokens_by_tongue, task_token_sets, family, tongues)
        harmonic_score = _harmonic_alignment(task_tokens_by_tongue, family, tongues)
        # Thread 2: Geometric (packet byte distance + TritVoxel band alignment)
        packet_score = _packet_alignment(task_packet_bytes, family)
        triad_score = _triad_alignment(task_triad_vec, family)
        # Thread 3: PQC hash-tree fingerprint (FIPS 205 FORS-style Merkle tree)
        pqc_score = pqc_thread_score(task_packet_bytes, FAMILY_PQC_PACKETS[family])
        score = (
            0.25 * token_score       # Thread 1 — tongue braid
            + 0.10 * harmonic_score  # Thread 1 — harmonic fingerprint
            + 0.25 * packet_score    # Thread 2 — geometry
            + 0.20 * triad_score     # Thread 2 — TritVoxel
            + 0.15 * pqc_score       # Thread 3 — PQC proof
            + 0.05 * topology.charge
        )
        scored.append((family, score))
    return scored


def _sorted_families(scored: list[tuple[str, float]]) -> list[str]:
    scored.sort(
        key=lambda item: (
            -item[1],
            FLAT_FAMILY_ORDER.index(item[0]) if item[0] in FLAT_FAMILY_ORDER else 999,
        )
    )
    return [family for family, _ in scored]


def rank_families_by_token_braid(task: ARCTask, tongues: tuple[str, ...] = BRAID_TONGUES) -> list[str]:
    return _sorted_families(_token_braid_scores(task, tongues))


# ---------------------------------------------------------------------------
# Cross-tongue null space analysis
# ---------------------------------------------------------------------------

_ALL_TONGUES: tuple[str, ...] = tuple(_TONGUE_PHI_WEIGHTS)


def tongue_null_axes(task: ARCTask, base_threshold: float = 0.10) -> dict[str, frozenset[int]]:
    """Return per-tongue null axis sets.

    An axis is "null" in a tongue when its phi-amplified topology value
    falls below *base_threshold*.  Coarse tongues (KO weight=1.0) have
    higher thresholds; sensitive tongues (DR weight=11.09) can detect
    very faint signals.

    Returns a dict mapping tongue code → frozenset of null axis indices.
    """
    topo = task_topology(task)
    result: dict[str, frozenset[int]] = {}
    for tongue, phi in _TONGUE_PHI_WEIGHTS.items():
        null = frozenset(
            i for i, v in enumerate(topo) if float(v) * phi < base_threshold
        )
        result[tongue] = null
    return result


def invariant_null_axes(task: ARCTask, base_threshold: float = 0.10) -> frozenset[int]:
    """Axes null in ALL six tongues — no tongue can see a signal there.

    These are the axes the solver should not search; the transformation
    is provably not operating in this subspace.
    """
    per_tongue = tongue_null_axes(task, base_threshold)
    return frozenset.intersection(*per_tongue.values())


def wormhole_axes(task: ARCTask, base_threshold: float = 0.10) -> frozenset[int]:
    """Axes null in the three coarse tongues (KO/AV/RU) but active in
    at least one fine tongue (CA/UM/DR).

    These are the "wormhole" dimensions: too faint for direct-path solvers,
    but real enough that high-sensitivity tongues detect them.  A move
    sequence that routes through a wormhole axis can reach the solution
    from an angle the primary solver misses.
    """
    per_tongue = tongue_null_axes(task, base_threshold)
    coarse_null = per_tongue["ko"] & per_tongue["av"] & per_tongue["ru"]
    fine_active = set(range(len(AXES))) - (per_tongue["ca"] & per_tongue["um"] & per_tongue["dr"])
    return coarse_null & fine_active


def free_axes(task: ARCTask, base_threshold: float = 0.10) -> tuple[int, ...]:
    """Axis indices active in at least one tongue — the live search space.

    Complement of *invariant_null_axes*.  The solver should restrict
    its topology-guided search to these axes.
    """
    null = invariant_null_axes(task, base_threshold)
    return tuple(i for i in range(len(AXES)) if i not in null)


def null_space_report(task: ARCTask, base_threshold: float = 0.10) -> dict[str, object]:
    """Human-readable cross-tongue null space breakdown for a task."""
    per_tongue = tongue_null_axes(task, base_threshold)
    inv_null = invariant_null_axes(task, base_threshold)
    worm = wormhole_axes(task, base_threshold)
    topo = task_topology(task)
    return {
        "topology": {AXES[i]: round(float(topo[i]), 3) for i in range(len(AXES))},
        "per_tongue_null": {t: sorted(v) for t, v in per_tongue.items()},
        "invariant_null_axes": [AXES[i] for i in sorted(inv_null)],
        "wormhole_axes": [AXES[i] for i in sorted(worm)],
        "free_axes": [AXES[i] for i in free_axes(task, base_threshold)],
    }


def _mean(values) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 0.0


def rank_families_by_token_braid_null_space(
    task: ARCTask,
    tongues: tuple[str, ...] = BRAID_TONGUES,
    *,
    base_threshold: float = 0.10,
    null_penalty_weight: float = 0.20,
    wormhole_bonus_weight: float = 0.10,
) -> list[str]:
    """Re-rank token-braid matches using the task's cross-tongue null structure."""
    scored = _token_braid_scores(task, tongues)
    inv_null = invariant_null_axes(task, base_threshold)
    wormhole = wormhole_axes(task, base_threshold)

    adjusted: list[tuple[str, float]] = []
    for family, score in scored:
        topology = FAMILY_TOPOLOGIES[family].as_array()
        null_mass = _mean(float(topology[idx]) for idx in inv_null)
        wormhole_mass = _mean(float(topology[idx]) for idx in wormhole)
        adjusted_score = score - null_penalty_weight * null_mass + wormhole_bonus_weight * wormhole_mass
        adjusted.append((family, adjusted_score))
    return _sorted_families(adjusted)


def box_threat_topology(
    task: ARCTask,
    tongues: tuple[str, ...] = BRAID_TONGUES,
    *,
    quarantine_threshold: float = 0.62,
    deny_threshold: float = 0.55,
) -> ThreatVerdict:
    """Thread 3 security gate: detect topology impostors and route to GeoSeal.

    Runs Threads 1+2 scoring first to find the best-matching family, then
    cross-checks with Thread 3 (PQC hash-tree fingerprint).  A task that
    looks like a safe family on Threads 1+2 but diverges on Thread 3 is
    flagged as an impostor.

    Actions map to GeoSeal routing::

        ALLOW      → pass through to solver
        QUARANTINE → hold for governance review
        DENY       → block; log as adversarial training pair

    Returns:
        ThreatVerdict with impostor_confidence, pqc_score, and action.
    """
    task_packet_bytes = task_packet(task)
    scores = _token_braid_scores(task, tongues)
    # Pass Thread 1+2 scores alongside pre-built family packets to detector
    tg_scores = sorted(scores, key=lambda x: -x[1])
    return detect_threat(
        task_packet_bytes,
        tg_scores,
        FAMILY_PQC_PACKETS,
        quarantine_threshold=quarantine_threshold,
        deny_threshold=deny_threshold,
    )


def explain_task_braid(task: ARCTask, tongue: str = "CA") -> dict[str, object]:
    packet = task_packet(task)
    topology = task_topology(task)
    return {
        "axes": {axis: round(float(topology[i]), 3) for i, axis in enumerate(AXES)},
        "packet": list(packet),
        "triad": list(_triadic_projection(packet)),
        "tokens": list(SACRED_TONGUE_TOKENIZER.encode_bytes(_tokenizer_code(tongue), packet)),
        "tokenizer_tongue": _tokenizer_code(tongue),
    }
