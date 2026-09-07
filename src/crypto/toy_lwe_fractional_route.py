"""Exact fractional acquisition followed by a certified toy-LWE route.

This module tests two related ideas without changing the earlier box-field
instrument:

* the public matrix induces an exact pseudometric on candidate differences;
* an integer box can be ranked by the exact fraction

      (midpoint score - safe lower bound) / matrix uncertainty.

The fraction is ordering evidence only.  The existing interval lower bound is
the sole pruning authority.  A zero denominator is never converted into a
number: a singleton is tagged ``resolved`` and a non-singleton with no visible
matrix span is tagged ``kernel-pocket``.  The latter is uncertainty metadata,
not Shannon entropy unless a probability distribution is separately supplied.

Acquisition descends one route first, retaining every sibling.  Certification
then drains those siblings with the existing exact branch-and-bound rule.  One
score cache spans both stages, so every objective call is charged once and no
"free scout" can manufacture a speedup.

This remains a deliberately tiny research instrument.  It is not an attack on
ML-KEM, ML-DSA, or a security primitive.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
from heapq import heappop, heappush
from typing import Literal

from src.crypto import toy_lwe_box_field as BOX

Candidate = tuple[int, ...]
AcquisitionPolicy = Literal["lower-bound", "midpoint", "fractional-space", "random"]
ZeroPolicy = Literal["first", "last"]
ZeroState = Literal["resolved", "kernel-pocket"]


@dataclass(frozen=True)
class TaggedSpaceFraction:
    """An exact nonnegative ratio or an explicit zero-denominator state."""

    numerator: int
    denominator: int
    zero_state: ZeroState | None = None

    def __post_init__(self) -> None:
        values = (self.numerator, self.denominator)
        if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
            raise TypeError("space fractions require plain integers")
        if self.numerator < 0 or self.denominator < 0:
            raise ValueError("space fractions require nonnegative values")
        if self.denominator == 0 and self.zero_state not in {"resolved", "kernel-pocket"}:
            raise ValueError("a zero denominator requires an explicit state")
        if self.denominator > 0 and self.zero_state is not None:
            raise ValueError("a finite fraction cannot carry a zero state")

    @property
    def finite(self) -> bool:
        return self.denominator > 0

    def ordering_key(self, zero_policy: ZeroPolicy) -> tuple[int, Fraction]:
        """Return an exact sortable key; ``Fraction`` never sees denominator zero."""

        if zero_policy not in {"first", "last"}:
            raise ValueError("zero policy must be first or last")
        if self.finite:
            return 1, Fraction(self.numerator, self.denominator)
        return (0 if zero_policy == "first" else 2), Fraction(0, 1)


@dataclass(frozen=True)
class RouteStep:
    low: Candidate
    high: Candidate
    midpoint: Candidate
    lower_bound: int
    midpoint_score: int
    matrix_uncertainty: int
    fraction: TaggedSpaceFraction


@dataclass(frozen=True)
class FractionalRouteResult:
    candidate: Candidate
    score: int
    acquired_candidate: Candidate
    acquired_score: int
    acquisition_objective_evaluations: int
    certification_objective_evaluations: int
    total_objective_evaluations: int
    boxes_opened: int
    boxes_pruned: int
    candidate_volume_pruned: int
    resolved_zero_states: int
    kernel_pocket_states: int
    route: tuple[RouteStep, ...]
    strategy: str


@dataclass(frozen=True)
class _BoxInfo:
    lower_bound: int
    midpoint_score: int
    matrix_uncertainty: int
    fraction: TaggedSpaceFraction


def _plain_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def matrix_displacement_squared(instance: BOX.ToyLWEInstance, left: Candidate, right: Candidate) -> int:
    """Return ``||A(left-right)||_q^2`` using centered integer residues.

    This is a pseudometric after taking a square root: distinct candidates may
    have zero displacement when their difference lies in the matrix kernel.
    """

    BOX.validate_instance(instance)
    if len(left) != instance.dimension or len(right) != instance.dimension:
        raise ValueError("candidate dimensions differ from the matrix")
    if any(not _plain_int(value) for value in (*left, *right)):
        raise TypeError("matrix displacement requires integer candidates")
    difference = tuple(a - b for a, b in zip(left, right, strict=True))
    return sum(
        BOX.centered_residue(
            sum(coefficient * value for coefficient, value in zip(row, difference, strict=True)), instance.modulus
        )
        ** 2
        for row in instance.matrix
    )


def matrix_box_uncertainty(instance: BOX.ToyLWEInstance, box: BOX.IntegerBox) -> int:
    """Return the squared unwrapped matrix span of an integer candidate box."""

    if len(box.low) != instance.dimension or len(box.high) != instance.dimension:
        raise ValueError("box dimension differs from the matrix")
    if any(low > high for low, high in zip(box.low, box.high, strict=True)):
        raise ValueError("box contains reversed bounds")
    total = 0
    for row in instance.matrix:
        dot_low = 0
        dot_high = 0
        for coefficient, low, high in zip(row, box.low, box.high, strict=True):
            signed = BOX.centered_residue(coefficient, instance.modulus)
            left = signed * low
            right = signed * high
            dot_low += min(left, right)
            dot_high += max(left, right)
        total += (dot_high - dot_low) ** 2
    return total


def space_fraction(
    box: BOX.IntegerBox, *, lower_bound: int, midpoint_score: int, uncertainty: int
) -> TaggedSpaceFraction:
    """Build the exact routing fraction and preserve a zero-span pocket."""

    if any(not _plain_int(value) for value in (lower_bound, midpoint_score, uncertainty)):
        raise TypeError("space-fraction inputs must be plain integers")
    if lower_bound < 0 or midpoint_score < lower_bound or uncertainty < 0:
        raise ValueError("invalid score bound or matrix uncertainty")
    zero_state: ZeroState | None = None
    if uncertainty == 0:
        zero_state = "resolved" if box.singleton else "kernel-pocket"
    return TaggedSpaceFraction(midpoint_score - lower_bound, uncertainty, zero_state)


def _random_box_rank(seed: int, box: BOX.IntegerBox) -> int:
    payload = f"{seed}|{box.low}|{box.high}".encode("ascii")
    return int.from_bytes(hashlib.sha256(payload).digest()[:16], "big")


def acquire_then_certify(
    instance: BOX.ToyLWEInstance,
    *,
    policy: AcquisitionPolicy,
    zero_policy: ZeroPolicy = "last",
    random_seed: int = 0,
) -> FractionalRouteResult:
    """Acquire one complete route, then certify the exact optimum."""

    BOX.validate_instance(instance)
    if policy not in {"lower-bound", "midpoint", "fractional-space", "random"}:
        raise ValueError("unknown acquisition policy")
    if zero_policy not in {"first", "last"}:
        raise ValueError("zero policy must be first or last")
    if not _plain_int(random_seed) or random_seed < 0:
        raise ValueError("random seed must be a nonnegative integer")

    root = BOX.IntegerBox(
        (instance.secret_low,) * instance.dimension,
        (instance.secret_high,) * instance.dimension,
    )
    score_cache: dict[Candidate, int] = {}
    best_candidate: Candidate | None = None
    best_score: int | None = None
    queue: list[tuple[tuple[int, int], int, int, BOX.IntegerBox]] = []
    serial = 0
    boxes_opened = 0
    boxes_pruned = 0
    pruned_volume = 0
    resolved_zero_states = 0
    kernel_pocket_states = 0
    route: list[RouteStep] = []

    def measure(candidate: Candidate) -> int:
        nonlocal best_candidate, best_score
        if candidate not in score_cache:
            score_cache[candidate] = BOX.exact_score(instance, candidate)
        score = score_cache[candidate]
        if best_score is None or (score, candidate) < (best_score, best_candidate):
            best_candidate, best_score = candidate, score
        return score

    def inspect(box: BOX.IntegerBox) -> _BoxInfo | None:
        nonlocal boxes_pruned, pruned_volume, resolved_zero_states, kernel_pocket_states
        lower = BOX.box_lower_bound(instance, box)
        if best_score is not None and lower > best_score:
            boxes_pruned += 1
            pruned_volume += box.volume
            return None
        midpoint_score = measure(box.midpoint)
        if best_score is not None and lower > best_score:
            boxes_pruned += 1
            pruned_volume += box.volume
            return None
        uncertainty = matrix_box_uncertainty(instance, box)
        fraction = space_fraction(
            box,
            lower_bound=lower,
            midpoint_score=midpoint_score,
            uncertainty=uncertainty,
        )
        if fraction.zero_state == "resolved":
            resolved_zero_states += 1
        elif fraction.zero_state == "kernel-pocket":
            kernel_pocket_states += 1
        return _BoxInfo(lower, midpoint_score, uncertainty, fraction)

    def acquisition_rank(box: BOX.IntegerBox, info: _BoxInfo) -> tuple[object, ...]:
        if policy == "lower-bound":
            return info.lower_bound, box.volume, box.low
        if policy == "midpoint":
            return info.midpoint_score, info.lower_bound, box.volume, box.low
        if policy == "fractional-space":
            return (*info.fraction.ordering_key(zero_policy), info.lower_bound, box.volume, box.low)
        return _random_box_rank(random_seed, box), info.lower_bound, box.volume, box.low

    def defer(box: BOX.IntegerBox, info: _BoxInfo) -> None:
        nonlocal serial
        serial += 1
        heappush(queue, ((info.lower_bound, box.volume), serial, info.lower_bound, box))

    current = root
    current_info = inspect(current)
    if current_info is None:
        raise RuntimeError("root box was unexpectedly pruned")
    route.append(
        RouteStep(
            current.low,
            current.high,
            current.midpoint,
            current_info.lower_bound,
            current_info.midpoint_score,
            current_info.matrix_uncertainty,
            current_info.fraction,
        )
    )

    while not current.singleton:
        boxes_opened += 1
        inspected: list[tuple[BOX.IntegerBox, _BoxInfo]] = []
        for child in BOX._split_box(current, BOX._split_dimension(instance, current)):
            info = inspect(child)
            if info is not None:
                inspected.append((child, info))
        if best_score is None:
            raise RuntimeError("acquisition lost its measured incumbent")
        inspected = [(box, info) for box, info in inspected if info.lower_bound <= best_score]
        if not inspected:
            break
        chosen, chosen_info = min(inspected, key=lambda item: acquisition_rank(*item))
        for sibling, sibling_info in inspected:
            if sibling != chosen:
                defer(sibling, sibling_info)
        current, current_info = chosen, chosen_info
        route.append(
            RouteStep(
                current.low,
                current.high,
                current.midpoint,
                current_info.lower_bound,
                current_info.midpoint_score,
                current_info.matrix_uncertainty,
                current_info.fraction,
            )
        )

    if best_candidate is None or best_score is None:
        raise RuntimeError("acquisition produced no candidate")
    acquired_candidate, acquired_score = best_candidate, best_score
    acquisition_evaluations = len(score_cache)

    while queue:
        _, _, lower, box = heappop(queue)
        if best_score is not None and lower > best_score:
            boxes_pruned += 1
            pruned_volume += box.volume
            continue
        boxes_opened += 1
        if box.singleton:
            continue
        for child in BOX._split_box(box, BOX._split_dimension(instance, box)):
            info = inspect(child)
            if info is not None:
                defer(child, info)

    if best_candidate is None or best_score is None:
        raise RuntimeError("certification produced no candidate")
    return FractionalRouteResult(
        candidate=best_candidate,
        score=best_score,
        acquired_candidate=acquired_candidate,
        acquired_score=acquired_score,
        acquisition_objective_evaluations=acquisition_evaluations,
        certification_objective_evaluations=len(score_cache) - acquisition_evaluations,
        total_objective_evaluations=len(score_cache),
        boxes_opened=boxes_opened,
        boxes_pruned=boxes_pruned,
        candidate_volume_pruned=pruned_volume,
        resolved_zero_states=resolved_zero_states,
        kernel_pocket_states=kernel_pocket_states,
        route=tuple(route),
        strategy=f"{policy}-acquisition-then-exact-bound-certification-zero-{zero_policy}",
    )
