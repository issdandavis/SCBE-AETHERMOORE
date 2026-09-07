"""Exact-integer multiscale box search on deliberately tiny LWE instances.

This module is a research instrument, not an ML-KEM or ML-DSA attack.  It
translates a coarse/fine, near/far "value field" idea into an exact search whose
pruning decisions are justified by interval bounds.  It is intentionally
limited to toy secret domains that can also be searched exhaustively.
"""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import product
import random
from typing import Iterable, Sequence


@dataclass(frozen=True)
class ToyLWEInstance:
    modulus: int
    matrix: tuple[tuple[int, ...], ...]
    public: tuple[int, ...]
    secret_low: int
    secret_high: int
    planted_secret: tuple[int, ...] | None = None
    error: tuple[int, ...] | None = None

    @property
    def dimension(self) -> int:
        return len(self.matrix[0])

    @property
    def samples(self) -> int:
        return len(self.matrix)

    @property
    def candidate_count(self) -> int:
        return (self.secret_high - self.secret_low + 1) ** self.dimension


@dataclass(frozen=True)
class IntegerBox:
    low: tuple[int, ...]
    high: tuple[int, ...]

    @property
    def volume(self) -> int:
        result = 1
        for low, high in zip(self.low, self.high, strict=True):
            result *= high - low + 1
        return result

    @property
    def singleton(self) -> bool:
        return self.low == self.high

    @property
    def midpoint(self) -> tuple[int, ...]:
        return tuple((low + high) // 2 for low, high in zip(self.low, self.high, strict=True))


@dataclass(frozen=True)
class PivotField:
    """Four exact anchors selected from full and coarse views of one box."""

    near_full: tuple[int, ...]
    far_full: tuple[int, ...]
    near_coarse: tuple[int, ...]
    far_coarse: tuple[int, ...]
    near_full_score: int
    far_full_score: int
    near_coarse_score: int
    far_coarse_score: int


@dataclass(frozen=True)
class SearchResult:
    candidate: tuple[int, ...]
    score: int
    evaluated_candidates: int
    boxes_opened: int
    boxes_pruned: int
    candidate_volume_pruned: int
    total_candidates: int
    strategy: str


def _plain_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_instance(instance: ToyLWEInstance) -> None:
    if not _plain_int(instance.modulus) or instance.modulus < 3 or instance.modulus % 2 == 0:
        raise ValueError("toy modulus must be an odd integer of at least three")
    if not instance.matrix or not instance.matrix[0]:
        raise ValueError("matrix must be nonempty")
    width = len(instance.matrix[0])
    if len(instance.public) != len(instance.matrix) or any(len(row) != width for row in instance.matrix):
        raise ValueError("matrix and public-vector shapes disagree")
    if not _plain_int(instance.secret_low) or not _plain_int(instance.secret_high):
        raise ValueError("secret bounds must be integers")
    if instance.secret_low > instance.secret_high:
        raise ValueError("secret bounds are reversed")
    values: Iterable[object] = (*instance.public, *(value for row in instance.matrix for value in row))
    if any(not _plain_int(value) for value in values):
        raise ValueError("LWE values must be integers")
    if instance.planted_secret is not None:
        if len(instance.planted_secret) != width:
            raise ValueError("planted secret has the wrong dimension")
        if any(
            not _plain_int(value) or not instance.secret_low <= value <= instance.secret_high
            for value in instance.planted_secret
        ):
            raise ValueError("planted secret is outside the declared integer domain")
    if instance.error is not None:
        if len(instance.error) != len(instance.matrix):
            raise ValueError("error has the wrong sample count")
        if any(not _plain_int(value) for value in instance.error):
            raise ValueError("error values must be integers")


def centered_residue(value: int, modulus: int) -> int:
    """Return the unique odd-modulus representative in [-q//2, q//2]."""

    residue = value % modulus
    return residue - modulus if residue > modulus // 2 else residue


def generate_toy_lwe(
    seed: int,
    *,
    dimension: int = 8,
    samples: int = 14,
    modulus: int = 97,
    secret_radius: int = 1,
    error_radius: int = 1,
) -> ToyLWEInstance:
    """Generate a reproducible tiny instance with a contiguous secret cube."""

    for name, value, minimum in (
        ("seed", seed, 0),
        ("dimension", dimension, 1),
        ("samples", samples, 1),
        ("secret radius", secret_radius, 0),
        ("error radius", error_radius, 0),
    ):
        if not _plain_int(value) or value < minimum:
            raise ValueError(f"{name} must be an integer of at least {minimum}")
    if not _plain_int(modulus) or modulus < 3 or modulus % 2 == 0:
        raise ValueError("modulus must be an odd integer of at least three")

    rng = random.Random(seed)
    matrix = tuple(tuple(rng.randrange(modulus) for _ in range(dimension)) for _ in range(samples))
    secret = tuple(rng.randint(-secret_radius, secret_radius) for _ in range(dimension))
    error = tuple(rng.randint(-error_radius, error_radius) for _ in range(samples))
    public = tuple(
        (sum(coefficient * value for coefficient, value in zip(row, secret, strict=True)) + noise) % modulus
        for row, noise in zip(matrix, error, strict=True)
    )
    instance = ToyLWEInstance(
        modulus=modulus,
        matrix=matrix,
        public=public,
        secret_low=-secret_radius,
        secret_high=secret_radius,
        planted_secret=secret,
        error=error,
    )
    validate_instance(instance)
    return instance


def residual_vector(instance: ToyLWEInstance, candidate: Sequence[int]) -> tuple[int, ...]:
    if len(candidate) != instance.dimension or any(not _plain_int(value) for value in candidate):
        raise ValueError("candidate has the wrong shape or type")
    return tuple(
        centered_residue(
            target - sum(coefficient * value for coefficient, value in zip(row, candidate, strict=True)),
            instance.modulus,
        )
        for row, target in zip(instance.matrix, instance.public, strict=True)
    )


def exact_score(instance: ToyLWEInstance, candidate: Sequence[int]) -> int:
    """Squared centered modular residual, using integer arithmetic only."""

    return sum(value * value for value in residual_vector(instance, candidate))


def coarse_score(instance: ToyLWEInstance, candidate: Sequence[int], *, bucket_width: int) -> int:
    """A lossy integer view used for ordering only, never for pruning."""

    if not _plain_int(bucket_width) or bucket_width < 1:
        raise ValueError("bucket width must be a positive integer")
    return sum((abs(value) // bucket_width) ** 2 for value in residual_vector(instance, candidate))


def interval_mod_distance(target: int, low: int, high: int, modulus: int) -> int:
    """Minimum modular distance from target to any integer in [low, high]."""

    if any(not _plain_int(value) for value in (target, low, high, modulus)) or modulus < 1:
        raise ValueError("interval distance requires integers and a positive modulus")
    if low > high:
        raise ValueError("interval is reversed")
    left_index = (low - target) // modulus
    right_index = (high - target) // modulus
    indices = {
        left_index - 1,
        left_index,
        left_index + 1,
        right_index - 1,
        right_index,
        right_index + 1,
    }

    def distance(index: int) -> int:
        point = target + index * modulus
        if point < low:
            return low - point
        if point > high:
            return point - high
        return 0

    return min(distance(index) for index in indices)


def box_lower_bound(instance: ToyLWEInstance, box: IntegerBox) -> int:
    """Safe score bound from a modular interval hull of every equation."""

    if len(box.low) != instance.dimension or len(box.high) != instance.dimension:
        raise ValueError("box dimension differs from instance")
    if any(low > high for low, high in zip(box.low, box.high, strict=True)):
        raise ValueError("box contains reversed bounds")

    result = 0
    for row, target in zip(instance.matrix, instance.public, strict=True):
        dot_low = 0
        dot_high = 0
        for coefficient, low, high in zip(row, box.low, box.high, strict=True):
            signed = centered_residue(coefficient, instance.modulus)
            left = signed * low
            right = signed * high
            dot_low += min(left, right)
            dot_high += max(left, right)
        distance = interval_mod_distance(target, dot_low, dot_high, instance.modulus)
        result += distance * distance
    return result


def _candidate_points(box: IntegerBox) -> tuple[tuple[int, ...], ...]:
    middle = box.midpoint
    low = box.low
    high = box.high
    alternating = tuple(low[index] if index % 2 == 0 else high[index] for index in range(len(low)))
    reverse = tuple(high[index] if index % 2 == 0 else low[index] for index in range(len(low)))
    return tuple(dict.fromkeys((middle, low, high, alternating, reverse)))


def pivot_field(
    instance: ToyLWEInstance,
    box: IntegerBox,
    *,
    bucket_width: int,
    score_cache: dict[tuple[int, ...], int] | None = None,
) -> PivotField:
    """Select closest/farthest anchors independently in exact and coarse views."""

    cache = score_cache if score_cache is not None else {}
    points = _candidate_points(box)

    def full(point: tuple[int, ...]) -> int:
        if point not in cache:
            cache[point] = exact_score(instance, point)
        return cache[point]

    full_ranked = sorted(points, key=lambda point: (full(point), point))
    coarse_ranked = sorted(points, key=lambda point: (coarse_score(instance, point, bucket_width=bucket_width), point))
    near_full, far_full = full_ranked[0], full_ranked[-1]
    near_coarse, far_coarse = coarse_ranked[0], coarse_ranked[-1]
    return PivotField(
        near_full=near_full,
        far_full=far_full,
        near_coarse=near_coarse,
        far_coarse=far_coarse,
        near_full_score=full(near_full),
        far_full_score=full(far_full),
        near_coarse_score=coarse_score(instance, near_coarse, bucket_width=bucket_width),
        far_coarse_score=coarse_score(instance, far_coarse, bucket_width=bucket_width),
    )


def _split_dimension(instance: ToyLWEInstance, box: IntegerBox) -> int:
    """Choose the widest coordinate, weighted by exact equation sensitivity."""

    choices = []
    for index, (low, high) in enumerate(zip(box.low, box.high, strict=True)):
        width = high - low
        sensitivity = sum(abs(centered_residue(row[index], instance.modulus)) for row in instance.matrix)
        choices.append((width * (sensitivity + 1), width, -index, index))
    return max(choices)[-1]


def _split_box(box: IntegerBox, index: int) -> tuple[IntegerBox, IntegerBox]:
    low, high = box.low[index], box.high[index]
    if low == high:
        raise ValueError("cannot split a fixed coordinate")
    middle = (low + high) // 2
    left_high = list(box.high)
    right_low = list(box.low)
    left_high[index] = middle
    right_low[index] = middle + 1
    return IntegerBox(box.low, tuple(left_high)), IntegerBox(tuple(right_low), box.high)


def exhaustive_search(instance: ToyLWEInstance) -> SearchResult:
    validate_instance(instance)
    domain = range(instance.secret_low, instance.secret_high + 1)
    best_candidate: tuple[int, ...] | None = None
    best_score: int | None = None
    evaluated = 0
    for candidate in product(domain, repeat=instance.dimension):
        score = exact_score(instance, candidate)
        evaluated += 1
        if best_score is None or (score, candidate) < (best_score, best_candidate):
            best_score, best_candidate = score, candidate
    assert best_candidate is not None and best_score is not None
    return SearchResult(
        candidate=best_candidate,
        score=best_score,
        evaluated_candidates=evaluated,
        boxes_opened=0,
        boxes_pruned=0,
        candidate_volume_pruned=0,
        total_candidates=instance.candidate_count,
        strategy="exhaustive",
    )


def box_field_search(
    instance: ToyLWEInstance,
    *,
    bucket_width: int = 4,
    strategy: str = "multiscale",
) -> SearchResult:
    """Find the exact optimum with safe bounds and optional four-anchor ordering."""

    validate_instance(instance)
    if strategy not in {"multiscale", "bound-only"}:
        raise ValueError("unknown search strategy")
    if not _plain_int(bucket_width) or bucket_width < 1:
        raise ValueError("bucket width must be a positive integer")

    root = IntegerBox(
        (instance.secret_low,) * instance.dimension,
        (instance.secret_high,) * instance.dimension,
    )
    score_cache: dict[tuple[int, ...], int] = {}
    best_candidate: tuple[int, ...] | None = None
    best_score: int | None = None
    opened = 0
    pruned = 0
    pruned_volume = 0
    serial = 0
    queue: list[tuple[tuple[int, ...], int, IntegerBox]] = []

    def measure(candidate: tuple[int, ...]) -> int:
        nonlocal best_candidate, best_score
        if candidate not in score_cache:
            score_cache[candidate] = exact_score(instance, candidate)
        score = score_cache[candidate]
        if best_score is None or (score, candidate) < (best_score, best_candidate):
            best_score, best_candidate = score, candidate
        return score

    root_field = None
    if strategy == "multiscale":
        root_field = pivot_field(instance, root, bucket_width=bucket_width, score_cache=score_cache)
        for point in (
            root_field.near_full,
            root_field.far_full,
            root_field.near_coarse,
            root_field.far_coarse,
        ):
            measure(point)

    def enqueue(box: IntegerBox) -> None:
        nonlocal serial, pruned, pruned_volume
        lower = box_lower_bound(instance, box)
        if best_score is not None and lower > best_score:
            pruned += 1
            pruned_volume += box.volume
            return
        midpoint = box.midpoint
        midpoint_score = measure(midpoint)
        if best_score is not None and lower > best_score:
            pruned += 1
            pruned_volume += box.volume
            return
        if root_field is None:
            rank = (lower, box.volume)
        else:
            near_distance = sum(abs(left - right) for left, right in zip(midpoint, root_field.near_full, strict=True))
            far_distance = sum(abs(left - right) for left, right in zip(midpoint, root_field.far_full, strict=True))
            rank = (
                lower,
                coarse_score(instance, midpoint, bucket_width=bucket_width),
                midpoint_score,
                near_distance,
                -far_distance,
                box.volume,
            )
        serial += 1
        heappush(queue, (rank, serial, box))

    enqueue(root)
    while queue:
        rank, _, box = heappop(queue)
        lower = rank[0]
        if best_score is not None and lower > best_score:
            pruned += 1
            pruned_volume += box.volume
            continue
        opened += 1
        if box.singleton:
            measure(box.low)
            continue
        dimension = _split_dimension(instance, box)
        children = _split_box(box, dimension)
        if root_field is not None:
            preferred = best_candidate[dimension]
            children = tuple(
                sorted(
                    children,
                    key=lambda child: (not (child.low[dimension] <= preferred <= child.high[dimension]), child.low),
                )
            )
        for child in children:
            enqueue(child)

    assert best_candidate is not None and best_score is not None
    return SearchResult(
        candidate=best_candidate,
        score=best_score,
        evaluated_candidates=len(score_cache),
        boxes_opened=opened,
        boxes_pruned=pruned,
        candidate_volume_pruned=pruned_volume,
        total_candidates=instance.candidate_count,
        strategy=strategy,
    )
