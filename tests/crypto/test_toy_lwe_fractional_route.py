from __future__ import annotations

from fractions import Fraction

import pytest

from src.crypto import toy_lwe_box_field as BOX
from src.crypto import toy_lwe_fractional_route as ROUTE


def test_finite_space_fraction_is_exact_for_large_integers() -> None:
    left = ROUTE.TaggedSpaceFraction(10**80 + 1, 3 * 10**80 + 1)
    right = ROUTE.TaggedSpaceFraction(1, 3)
    assert left.ordering_key("last")[1] == Fraction(10**80 + 1, 3 * 10**80 + 1)
    assert left.ordering_key("last") > right.ordering_key("last")


def test_zero_denominator_is_tagged_and_never_passed_to_fraction() -> None:
    resolved = ROUTE.TaggedSpaceFraction(0, 0, "resolved")
    pocket = ROUTE.TaggedSpaceFraction(7, 0, "kernel-pocket")
    finite = ROUTE.TaggedSpaceFraction(1, 2)
    assert resolved.ordering_key("first") < finite.ordering_key("first")
    assert pocket.ordering_key("last") > finite.ordering_key("last")
    assert resolved.finite is False and pocket.finite is False


@pytest.mark.parametrize(
    "args",
    [
        (1, 0, None),
        (1, 2, "resolved"),
        (-1, 2, None),
        (1, -2, None),
        (True, 2, None),
    ],
)
def test_invalid_space_fraction_is_refused(args: tuple[object, object, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        ROUTE.TaggedSpaceFraction(*args)  # type: ignore[arg-type]


def test_matrix_displacement_is_symmetric_and_integer() -> None:
    instance = BOX.generate_toy_lwe(17, dimension=4, samples=7, modulus=97)
    left = (-1, 0, 1, -1)
    right = (1, 1, 0, -1)
    forward = ROUTE.matrix_displacement_squared(instance, left, right)
    assert isinstance(forward, int)
    assert forward == ROUTE.matrix_displacement_squared(instance, right, left)
    assert ROUTE.matrix_displacement_squared(instance, left, left) == 0


def test_zero_matrix_column_forms_an_explicit_kernel_pocket() -> None:
    instance = BOX.ToyLWEInstance(
        modulus=7,
        matrix=((1, 0), (2, 0)),
        public=(0, 0),
        secret_low=-1,
        secret_high=1,
    )
    box = BOX.IntegerBox((0, -1), (0, 1))
    uncertainty = ROUTE.matrix_box_uncertainty(instance, box)
    tagged = ROUTE.space_fraction(box, lower_bound=0, midpoint_score=0, uncertainty=uncertainty)
    assert uncertainty == 0
    assert tagged.zero_state == "kernel-pocket"
    assert ROUTE.matrix_displacement_squared(instance, (0, -1), (0, 1)) == 0


def test_singleton_zero_span_is_resolved_instead_of_entropy() -> None:
    instance = BOX.generate_toy_lwe(19, dimension=4, samples=7, modulus=97)
    point = (0, 1, -1, 0)
    box = BOX.IntegerBox(point, point)
    score = BOX.exact_score(instance, point)
    tagged = ROUTE.space_fraction(box, lower_bound=score, midpoint_score=score, uncertainty=0)
    assert tagged == ROUTE.TaggedSpaceFraction(0, 0, "resolved")


@pytest.mark.parametrize("policy", ["lower-bound", "midpoint", "fractional-space", "random"])
def test_acquisition_then_certification_matches_exhaustive(policy: ROUTE.AcquisitionPolicy) -> None:
    for seed in range(6):
        instance = BOX.generate_toy_lwe(seed, dimension=4, samples=7, modulus=31)
        truth = BOX.exhaustive_search(instance)
        result = ROUTE.acquire_then_certify(instance, policy=policy, random_seed=9000 + seed)
        assert (result.score, result.candidate) == (truth.score, truth.candidate)
        assert result.total_objective_evaluations == (
            result.acquisition_objective_evaluations + result.certification_objective_evaluations
        )
        assert result.total_objective_evaluations <= instance.candidate_count


def test_fractional_route_contains_only_exact_integer_measurements() -> None:
    instance = BOX.generate_toy_lwe(23, dimension=4, samples=7, modulus=31)
    result = ROUTE.acquire_then_certify(instance, policy="fractional-space", zero_policy="last")
    assert result.route
    for step in result.route:
        assert all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in (step.lower_bound, step.midpoint_score, step.matrix_uncertainty)
        )
        if step.fraction.finite:
            assert isinstance(step.fraction.ordering_key("last")[1], Fraction)


def test_random_acquisition_is_deterministic() -> None:
    instance = BOX.generate_toy_lwe(29, dimension=4, samples=7, modulus=31)
    left = ROUTE.acquire_then_certify(instance, policy="random", random_seed=123)
    right = ROUTE.acquire_then_certify(instance, policy="random", random_seed=123)
    assert left == right
