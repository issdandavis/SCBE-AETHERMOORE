"""Exact toy-LWE interval search with optional, fully charged seed probes.

This isolates the proposed geometry-then-algebra experiment without changing
the previously measured box-field implementation.  Seed candidates may improve
the incumbent used for pruning, but every seed objective call is included in
the total.  Safe interval lower bounds remain the only pruning authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from typing import Sequence

from src.crypto import toy_lwe_box_field as BOX

Candidate = tuple[int, ...]


@dataclass(frozen=True)
class SeededBoundResult:
    candidate: Candidate
    score: int
    total_objective_evaluations: int
    initial_unique_evaluations: int
    post_seed_objective_evaluations: int
    boxes_opened: int
    boxes_pruned: int
    candidate_volume_pruned: int
    strategy: str


def _validated_seed(instance: BOX.ToyLWEInstance, candidate: Sequence[int]) -> Candidate:
    value = tuple(candidate)
    if len(value) != instance.dimension:
        raise ValueError("seed candidate has the wrong dimension")
    if any(
        not isinstance(item, int) or isinstance(item, bool) or not instance.secret_low <= item <= instance.secret_high
        for item in value
    ):
        raise ValueError("seed candidate lies outside the exact integer domain")
    return value


def seeded_box_field_search(
    instance: BOX.ToyLWEInstance,
    initial_candidates: Sequence[Sequence[int]],
) -> SeededBoundResult:
    """Return the exact optimum while charging every unique initial probe."""

    BOX.validate_instance(instance)
    seeds = tuple(dict.fromkeys(_validated_seed(instance, candidate) for candidate in initial_candidates))
    root = BOX.IntegerBox(
        (instance.secret_low,) * instance.dimension,
        (instance.secret_high,) * instance.dimension,
    )
    score_cache: dict[Candidate, int] = {}
    best_candidate: Candidate | None = None
    best_score: int | None = None
    opened = 0
    pruned = 0
    pruned_volume = 0
    serial = 0
    queue: list[tuple[tuple[int, int], int, BOX.IntegerBox]] = []

    def measure(candidate: Candidate) -> None:
        nonlocal best_candidate, best_score
        if candidate not in score_cache:
            score_cache[candidate] = BOX.exact_score(instance, candidate)
        score = score_cache[candidate]
        if best_score is None or (score, candidate) < (best_score, best_candidate):
            best_score, best_candidate = score, candidate

    for candidate in seeds:
        measure(candidate)

    def enqueue(box: BOX.IntegerBox) -> None:
        nonlocal serial, pruned, pruned_volume
        lower = BOX.box_lower_bound(instance, box)
        if best_score is not None and lower > best_score:
            pruned += 1
            pruned_volume += box.volume
            return
        measure(box.midpoint)
        if best_score is not None and lower > best_score:
            pruned += 1
            pruned_volume += box.volume
            return
        serial += 1
        heappush(queue, ((lower, box.volume), serial, box))

    enqueue(root)
    while queue:
        rank, _, box = heappop(queue)
        if best_score is not None and rank[0] > best_score:
            pruned += 1
            pruned_volume += box.volume
            continue
        opened += 1
        if box.singleton:
            measure(box.low)
            continue
        dimension = BOX._split_dimension(instance, box)
        for child in BOX._split_box(box, dimension):
            enqueue(child)

    if best_candidate is None or best_score is None:
        raise RuntimeError("exact seeded search produced no candidate")
    initial_unique = len(seeds)
    return SeededBoundResult(
        candidate=best_candidate,
        score=best_score,
        total_objective_evaluations=len(score_cache),
        initial_unique_evaluations=initial_unique,
        post_seed_objective_evaluations=len(score_cache) - initial_unique,
        boxes_opened=opened,
        boxes_pruned=pruned,
        candidate_volume_pruned=pruned_volume,
        strategy="exact-interval-bound-with-fully-charged-seeds",
    )
