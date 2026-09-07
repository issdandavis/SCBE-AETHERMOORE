"""Bounded dual-trit phase and torus search on deliberately tiny LWE.

This module is a measurement scaffold, not an attack on ML-KEM or ML-DSA.
It reuses three existing exact/discrete surfaces:

* the nine dual-ternary states from ``ai_brain.dual_ternary``;
* the exact 30-degree cyclotomic action from ``integer_phase_shards``;
* the support-cube edges from ``python.scbe.torus.hypercube_neighbors``.

The phase wheel proposes at most a caller-declared number of complete toy
secrets.  The fallback performs best-first search on the finite trit torus
``C3^d``.  Every objective call is counted and no heuristic can prune a
candidate.  Exact ground truth remains the exhaustive or interval-bound search
in :mod:`toy_lwe_box_field`.
"""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
import random
from typing import Sequence

from python.scbe.torus import hypercube_neighbors
from src.crypto.integer_phase_shards import PHASE_ORDER, rotate_phase30
from src.crypto.toy_lwe_box_field import ToyLWEInstance, exact_score, validate_instance
from src.symphonic_cipher.scbe_aethermoore.ai_brain.dual_ternary import FULL_STATE_SPACE

Candidate = tuple[int, ...]
TRITS = (-1, 0, 1)
DUAL_TRIT_STATES = tuple((state.primary, state.mirror) for state in FULL_STATE_SPACE)


@dataclass(frozen=True)
class CandidateBatch:
    candidates: tuple[Candidate, ...]
    proposals: int
    duplicate_proposals: int
    strategy: str


@dataclass(frozen=True)
class ProbeResult:
    candidate: Candidate
    score: int
    evaluated_candidates: int
    candidate_proposals: int
    duplicate_proposals: int
    frontier_expansions: int
    evaluated: tuple[tuple[Candidate, int], ...]
    strategy: str


def _plain_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_dimension_count(dimension: int, count: int) -> int:
    if not _plain_int(dimension) or dimension < 1:
        raise ValueError("dimension must be a positive integer")
    if not _plain_int(count) or count < 1:
        raise ValueError("count must be a positive integer")
    total = 3**dimension
    if count > total:
        raise ValueError("count exceeds the finite trit space")
    return total


def _validate_candidate(candidate: Sequence[int], dimension: int) -> Candidate:
    value = tuple(candidate)
    if len(value) != dimension or any(not _plain_int(item) or item not in TRITS for item in value):
        raise ValueError("candidate must lie in {-1,0,+1}^dimension")
    return value


def balanced_trit_wrap(value: int) -> int:
    """Return the balanced representative of an integer modulo three."""

    if not _plain_int(value):
        raise TypeError("trit wrapping requires an integer")
    return ((value + 1) % 3) - 1


def move_on_trit_torus(anchor: Sequence[int], direction: Sequence[int]) -> Candidate:
    """Translate a signed direction around any exact trit-space intercept."""

    anchor_value = tuple(anchor)
    direction_value = tuple(direction)
    if len(anchor_value) != len(direction_value):
        raise ValueError("anchor and direction dimensions differ")
    _validate_candidate(anchor_value, len(anchor_value))
    _validate_candidate(direction_value, len(direction_value))
    return tuple(balanced_trit_wrap(left + right) for left, right in zip(anchor_value, direction_value, strict=True))


def hamming_distance(left: Sequence[int], right: Sequence[int]) -> int:
    if len(left) != len(right):
        raise ValueError("Hamming operands have different dimensions")
    return sum(a != b for a, b in zip(left, right, strict=True))


def _decode_balanced(index: int, dimension: int) -> Candidate:
    values = []
    for _ in range(dimension):
        index, residue = divmod(index, 3)
        values.append(residue - 1)
    return tuple(values)


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


def _mirrored_phase_rotation(candidate: Candidate, phase_step: int) -> Candidate:
    """Rotate four-coordinate blocks in opposite exact phase directions."""

    rotated: list[int] = []
    for start in range(0, len(candidate), 4):
        raw_block = candidate[start : start + 4]
        padded = raw_block + (0,) * (4 - len(raw_block))
        signed_step = phase_step if (start // 4) % 2 == 0 else -phase_step
        exact = rotate_phase30(padded, signed_step)
        rotated.extend(_sign(value) for value in exact[: len(raw_block)])
    result = tuple(rotated)
    if any(result[index : index + 2] not in DUAL_TRIT_STATES for index in range(0, len(result) - 1, 2)):
        raise RuntimeError("phase projection escaped the existing dual-trit state space")
    return result


def phase_wheel_candidates(
    dimension: int,
    *,
    count: int = 360,
    anchor: Sequence[int] | None = None,
) -> CandidateBatch:
    """Build unique exact candidates from mirrored 30-degree phase orbits.

    The 360 entries are labelled phase probes, not 360 equally spaced
    Euclidean directions.  A high-dimensional ternary cube has no canonical
    one-degree angular discretization.  Collisions after sign projection are
    counted.  If a small dimension cannot supply ``count`` unique phase-orbit
    images, a deterministic balanced-ternary traversal fills the remainder and
    that work remains visible in ``proposals``.
    """

    total = _validate_dimension_count(dimension, count)
    origin = (0,) * dimension if anchor is None else _validate_candidate(anchor, dimension)
    stride = 2 * (total // 3) + 1
    seen: set[Candidate] = set()
    candidates: list[Candidate] = []
    proposals = 0
    duplicates = 0

    def propose(direction: Candidate) -> None:
        nonlocal proposals, duplicates
        proposals += 1
        candidate = move_on_trit_torus(origin, direction)
        if candidate in seen:
            duplicates += 1
            return
        seen.add(candidate)
        candidates.append(candidate)

    for cursor in range(total * PHASE_ORDER):
        base = _decode_balanced((1 + cursor * stride) % total, dimension)
        turned = _mirrored_phase_rotation(base, cursor % PHASE_ORDER)
        propose(turned)
        if len(candidates) == count:
            break
        propose(tuple(-value for value in turned))
        if len(candidates) == count:
            break

    if len(candidates) < count:
        center_index = (total - 1) // 2
        for cursor in range(total):
            propose(_decode_balanced((center_index + cursor * stride) % total, dimension))
            if len(candidates) == count:
                break

    if len(candidates) != count:
        raise RuntimeError("failed to fill the declared finite phase wheel")
    return CandidateBatch(
        candidates=tuple(candidates),
        proposals=proposals,
        duplicate_proposals=duplicates,
        strategy="dual-trit-mirrored-30deg-wheel",
    )


def random_candidates(dimension: int, *, count: int, seed: int) -> CandidateBatch:
    """Uniform unique control candidates without enumerating the full space."""

    total = _validate_dimension_count(dimension, count)
    if not _plain_int(seed):
        raise ValueError("random control seed must be an integer")
    rng = random.Random(seed)
    seen: set[Candidate] = set()
    values: list[Candidate] = []
    proposals = 0
    while len(values) < count:
        candidate = _decode_balanced(rng.randrange(total), dimension)
        proposals += 1
        if candidate not in seen:
            seen.add(candidate)
            values.append(candidate)
    return CandidateBatch(
        candidates=tuple(values),
        proposals=proposals,
        duplicate_proposals=proposals - count,
        strategy="uniform-random-control",
    )


def trit_torus_hypercube_neighbors(candidate: Sequence[int]) -> tuple[Candidate, ...]:
    """Return the two one-coordinate C3 neighbors along every support-cube axis.

    The existing binary hypercube supplies support on/off edges.  A direct sign
    seam completes each three-state coordinate cycle ``-1 -> 0 -> +1 -> -1``.
    Their Cartesian product is the finite trit torus ``C3^d``.
    """

    value = _validate_candidate(candidate, len(candidate))
    support = sum((item != 0) << index for index, item in enumerate(value))
    neighbors: list[Candidate] = []
    for adjacent_support in hypercube_neighbors(support, bits=len(value)):
        changed = support ^ adjacent_support
        index = changed.bit_length() - 1
        if value[index] == 0:
            for sign in (-1, 1):
                neighbor = list(value)
                neighbor[index] = sign
                neighbors.append(tuple(neighbor))
        else:
            neighbor = list(value)
            neighbor[index] = 0
            neighbors.append(tuple(neighbor))
    for index, item in enumerate(value):
        if item != 0:
            neighbor = list(value)
            neighbor[index] = -item
            neighbors.append(tuple(neighbor))
    unique = tuple(dict.fromkeys(neighbors))
    if len(unique) != 2 * len(value):
        raise RuntimeError("trit torus did not produce two neighbors per axis")
    return unique


def evaluate_candidates(instance: ToyLWEInstance, batch: CandidateBatch) -> ProbeResult:
    """Evaluate one complete bounded batch and retain its auditable trace."""

    validate_instance(instance)
    if instance.secret_low != -1 or instance.secret_high != 1:
        raise ValueError("phase probe currently requires the exact balanced-trit secret domain")
    evaluated = tuple((candidate, exact_score(instance, candidate)) for candidate in batch.candidates)
    score, candidate = min((score, candidate) for candidate, score in evaluated)
    return ProbeResult(
        candidate=candidate,
        score=score,
        evaluated_candidates=len(evaluated),
        candidate_proposals=batch.proposals,
        duplicate_proposals=batch.duplicate_proposals,
        frontier_expansions=0,
        evaluated=evaluated,
        strategy=batch.strategy,
    )


def foothold_search(
    instance: ToyLWEInstance,
    initial: CandidateBatch,
    *,
    max_evaluations: int = 360,
) -> ProbeResult:
    """Best-first finite-torus expansion with a hard objective-call limit."""

    validate_instance(instance)
    if instance.secret_low != -1 or instance.secret_high != 1:
        raise ValueError("foothold search currently requires the balanced-trit domain")
    _validate_dimension_count(instance.dimension, max_evaluations)
    if not initial.candidates:
        raise ValueError("foothold search requires at least one initial candidate")

    scores: dict[Candidate, int] = {}
    order: list[tuple[Candidate, int]] = []
    frontier: list[tuple[int, Candidate]] = []
    expanded: set[Candidate] = set()
    proposals = initial.proposals
    duplicates = initial.duplicate_proposals

    def measure(candidate: Candidate) -> None:
        nonlocal duplicates
        candidate = _validate_candidate(candidate, instance.dimension)
        if candidate in scores:
            duplicates += 1
            return
        if len(scores) >= max_evaluations:
            return
        score = exact_score(instance, candidate)
        scores[candidate] = score
        order.append((candidate, score))
        heappush(frontier, (score, candidate))

    for candidate in initial.candidates:
        measure(candidate)
        if len(scores) == max_evaluations:
            break

    frontier_expansions = 0
    while frontier and len(scores) < max_evaluations:
        _, candidate = heappop(frontier)
        if candidate in expanded:
            continue
        expanded.add(candidate)
        frontier_expansions += 1
        neighbors = trit_torus_hypercube_neighbors(candidate)
        for neighbor in neighbors:
            proposals += 1
            measure(neighbor)
            if len(scores) == max_evaluations:
                break

    if len(scores) != max_evaluations:
        raise RuntimeError("connected trit torus exhausted before the declared budget")
    score, candidate = min((score, candidate) for candidate, score in scores.items())
    return ProbeResult(
        candidate=candidate,
        score=score,
        evaluated_candidates=len(scores),
        candidate_proposals=proposals,
        duplicate_proposals=duplicates,
        frontier_expansions=frontier_expansions,
        evaluated=tuple(order),
        strategy=f"{initial.strategy}+best-first-C3-hypercube",
    )
