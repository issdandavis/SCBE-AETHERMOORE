"""Remove projection and prefix bias from the toy dual-trit phase probe.

The first phase-wheel experiment used ``sign(rotate_phase30(...))``.  Sign is
many-to-one, so that projection collapsed exact phase states and produced a
poorly balanced 360-point subset.  This module keeps the existing exact
cyclotomic action, but reduces its integer coefficients modulo three.  The
result is a permutation of the finite trit field rather than a lossy sign
projection.

Complete twelve-phase orbits are selected by their still-uncovered radius-one
neighborhoods.  Selection sees only the finite trit geometry; it never reads
an LWE matrix, public vector, secret, residual, or objective.  This is a toy
coverage instrument, not a cryptographic primitive or key-recovery claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Sequence

from src.crypto import toy_lwe_phase_search as LEGACY
from src.crypto.integer_phase_shards import PHASE_ORDER, rotate_phase30

Candidate = tuple[int, ...]
MAX_TOY_SPACE = 3**8


@dataclass(frozen=True)
class OrbitCoverStats:
    candidates: int
    total_space: int
    radius_one_covered: int
    nearest_distance_sum: int
    covering_radius: int
    coordinate_counts: tuple[tuple[int, int, int], ...]
    max_coordinate_discrepancy_scaled_by_three: int
    max_pair_cell_discrepancy_scaled_by_nine: int
    complete_phase_orbit_members: int


def _plain_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_shape(dimension: int, count: int) -> int:
    if not _plain_int(dimension) or dimension < 4 or dimension % 4:
        raise ValueError("phase-orbit cover requires a positive multiple of four dimensions")
    if not _plain_int(count) or count < 1:
        raise ValueError("count must be a positive integer")
    total = 3**dimension
    if total > MAX_TOY_SPACE:
        raise ValueError("phase-orbit cover is intentionally bounded to at most 3**8 toy states")
    if count > total:
        raise ValueError("count exceeds the finite trit space")
    return total


def _validate_candidate(candidate: Sequence[int], dimension: int) -> Candidate:
    result = tuple(candidate)
    if len(result) != dimension or any(not _plain_int(value) or value not in LEGACY.TRITS for value in result):
        raise ValueError("candidate must lie in {-1,0,+1}^dimension")
    return result


def _decode_balanced(index: int, dimension: int) -> Candidate:
    values = []
    for _ in range(dimension):
        index, residue = divmod(index, 3)
        values.append(residue - 1)
    return tuple(values)


def rotate_phase_mod3(candidate: Sequence[int], phase_step: int) -> Candidate:
    """Apply the existing exact phase action and retain its balanced mod-3 state."""

    value = tuple(candidate)
    _validate_shape(len(value), 1)
    value = _validate_candidate(value, len(value))
    if not _plain_int(phase_step):
        raise ValueError("phase step must be an integer")
    rotated: list[int] = []
    for start in range(0, len(value), 4):
        block = value[start : start + 4]
        signed_step = phase_step if (start // 4) % 2 == 0 else -phase_step
        exact = rotate_phase30(block, signed_step)
        rotated.extend(LEGACY.balanced_trit_wrap(coefficient) for coefficient in exact)
    return tuple(rotated)


@lru_cache(maxsize=None)
def phase_orbits(dimension: int) -> tuple[tuple[Candidate, ...], ...]:
    """Partition the bounded trit field into exact modulo-three phase orbits."""

    total = _validate_shape(dimension, 1)
    seen: set[Candidate] = set()
    orbits: list[tuple[Candidate, ...]] = []
    for index in range(total):
        candidate = _decode_balanced(index, dimension)
        if candidate in seen:
            continue
        orbit = tuple(dict.fromkeys(rotate_phase_mod3(candidate, step) for step in range(PHASE_ORDER)))
        if any(member in seen for member in orbit):
            raise RuntimeError("phase action produced overlapping finite orbits")
        seen.update(orbit)
        orbits.append(orbit)
    if len(seen) != total:
        raise RuntimeError("phase orbits did not cover the finite trit field")
    return tuple(orbits)


@lru_cache(maxsize=None)
def _radius_one(candidate: Candidate) -> frozenset[Candidate]:
    values = {candidate}
    for index, current in enumerate(candidate):
        for replacement in LEGACY.TRITS:
            if replacement == current:
                continue
            neighbor = list(candidate)
            neighbor[index] = replacement
            values.add(tuple(neighbor))
    return frozenset(values)


@lru_cache(maxsize=None)
def _orbit_neighborhood(orbit: tuple[Candidate, ...]) -> frozenset[Candidate]:
    values: set[Candidate] = set()
    for candidate in orbit:
        values.update(_radius_one(candidate))
    return frozenset(values)


@lru_cache(maxsize=None)
def _origin_cover(dimension: int, count: int) -> tuple[Candidate, ...]:
    _validate_shape(dimension, count)
    available = list(phase_orbits(dimension))
    covered: set[Candidate] = set()
    selected: list[Candidate] = []

    while len(selected) < count:
        remaining = count - len(selected)
        fitting = [orbit for orbit in available if len(orbit) <= remaining]
        if not fitting:
            break
        chosen = min(
            fitting,
            key=lambda orbit: (-len(_orbit_neighborhood(orbit) - covered), -len(orbit), orbit[0]),
        )
        selected.extend(chosen)
        covered.update(_orbit_neighborhood(chosen))
        available.remove(chosen)

    while len(selected) < count:
        used = set(selected)
        remaining_candidates = (candidate for orbit in available for candidate in orbit if candidate not in used)
        chosen = min(remaining_candidates, key=lambda candidate: (-len(_radius_one(candidate) - covered), candidate))
        selected.append(chosen)
        covered.update(_radius_one(chosen))

    if len(selected) != len(set(selected)) or len(selected) != count:
        raise RuntimeError("phase-orbit cover did not produce the declared unique count")
    return tuple(selected)


def phase_orbit_cover_candidates(
    dimension: int,
    *,
    count: int = 360,
    anchor: Sequence[int] | None = None,
) -> LEGACY.CandidateBatch:
    """Return a radius-one cover made from complete exact phase orbits."""

    total = _validate_shape(dimension, count)
    origin = (0,) * dimension if anchor is None else _validate_candidate(anchor, dimension)
    directions = _origin_cover(dimension, count)
    candidates = tuple(LEGACY.move_on_trit_torus(origin, direction) for direction in directions)
    raw_phase_images = total * PHASE_ORDER
    return LEGACY.CandidateBatch(
        candidates=candidates,
        proposals=raw_phase_images,
        duplicate_proposals=raw_phase_images - total,
        strategy="dual-trit-complete-phase-orbit-radius1-cover",
    )


def orbit_cover_stats(batch: LEGACY.CandidateBatch) -> OrbitCoverStats:
    """Measure exact finite-space balance and nearest-neighbor coverage."""

    if not batch.candidates:
        raise ValueError("coverage statistics require at least one candidate")
    dimension = len(batch.candidates[0])
    total = _validate_shape(dimension, len(batch.candidates))
    candidates = tuple(_validate_candidate(candidate, dimension) for candidate in batch.candidates)
    if len(candidates) != len(set(candidates)):
        raise ValueError("coverage candidates must be unique")
    selected = set(candidates)

    coordinate_counts = tuple(
        tuple(sum(candidate[index] == trit for candidate in candidates) for trit in LEGACY.TRITS)
        for index in range(dimension)
    )
    coordinate_discrepancy = max(
        abs(3 * observed - len(candidates)) for counts in coordinate_counts for observed in counts
    )
    pair_discrepancy = 0
    for left in range(dimension):
        for right in range(left + 1, dimension):
            for left_trit in LEGACY.TRITS:
                for right_trit in LEGACY.TRITS:
                    observed = sum(
                        candidate[left] == left_trit and candidate[right] == right_trit for candidate in candidates
                    )
                    pair_discrepancy = max(pair_discrepancy, abs(9 * observed - len(candidates)))

    visited = set(candidates)
    frontier = set(candidates)
    nearest_distance_sum = 0
    distance = 0
    radius_one_covered = len(visited)
    while len(visited) < total:
        distance += 1
        following: set[Candidate] = set()
        for candidate in frontier:
            following.update(LEGACY.trit_torus_hypercube_neighbors(candidate))
        following.difference_update(visited)
        if not following:
            raise RuntimeError("finite trit torus became disconnected")
        visited.update(following)
        nearest_distance_sum += distance * len(following)
        frontier = following
        if distance == 1:
            radius_one_covered = len(visited)

    complete_members = sum(
        all(rotate_phase_mod3(candidate, step) in selected for step in range(PHASE_ORDER)) for candidate in candidates
    )
    return OrbitCoverStats(
        candidates=len(candidates),
        total_space=total,
        radius_one_covered=radius_one_covered,
        nearest_distance_sum=nearest_distance_sum,
        covering_radius=distance,
        coordinate_counts=coordinate_counts,
        max_coordinate_discrepancy_scaled_by_three=coordinate_discrepancy,
        max_pair_cell_discrepancy_scaled_by_nine=pair_discrepancy,
        complete_phase_orbit_members=complete_members,
    )
