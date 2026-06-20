"""Tests for inscribe — ratios, extrapolation, and tokens-as-numbers."""

import math
from fractions import Fraction

import pytest

from python.inscribe import (
    TokenNumbers,
    bijective_decode,
    bijective_encode,
    continued_fraction,
    convergents,
    extrapolate,
    fit_polynomial,
    inscribe,
    ladder,
    reconstruction_error,
)

# --- ratios (inscription) ----------------------------------------------------


def test_inscribe_simple_decimals():
    assert inscribe(0.5)["ratio"] == (1, 2)
    assert inscribe(0.1)["ratio"] == (1, 10)
    assert inscribe(0.25)["ratio"] == (1, 4)


def test_inscribe_pi_is_355_over_113():
    res = inscribe(math.pi, max_denominator=1000)
    assert res["ratio"] == (355, 113)
    assert res["error"] < 1e-6  # three tiny integers, high accuracy


def test_continued_fraction_and_convergents():
    assert continued_fraction(Fraction(22, 7)) == [3, 7]
    conv = convergents([3, 7, 15, 1])  # pi's first terms
    assert conv[:4] == [Fraction(3), Fraction(22, 7), Fraction(333, 106), Fraction(355, 113)]


def test_ladder_accuracy_is_monotonic():
    rungs = ladder(math.pi, max_terms=6)
    errs = [r["error"] for r in rungs]
    assert errs == sorted(errs, reverse=True)  # each rung at least as accurate
    assert errs[-1] < 1e-4


# --- extrapolation -----------------------------------------------------------


def test_fit_quadratic_exactly():
    coeffs = fit_polynomial([(0, 0), (1, 1), (2, 4)])  # y = x^2
    assert coeffs == [Fraction(0), Fraction(0), Fraction(1)]


def test_extrapolate_far_point_is_exact():
    # three points of x^2 reconstruct it; predicting x=100 is exact
    assert extrapolate([(0, 0), (1, 1), (2, 4)], 100) == Fraction(10000)
    assert extrapolate([(0, 0), (1, 1), (2, 4)], [3, 10]) == [Fraction(9), Fraction(100)]


def test_cubic_from_four_points_zero_error_on_holdout():
    # y = 2x^3 - x + 5 sampled at 4 points -> exact reconstruction -> 0 error elsewhere
    def f(x):
        return 2 * x**3 - x + 5

    train = [(x, f(x)) for x in (-1, 0, 1, 2)]
    test = [(x, f(x)) for x in (5, 9, -4)]
    assert reconstruction_error(train, test) == 0.0


def test_fit_rejects_duplicate_x():
    with pytest.raises(ValueError):
        fit_polynomial([(1, 2), (1, 3)])


# --- tokens as numbers (bijective numeration) --------------------------------


@pytest.mark.parametrize("alphabet", [["a", "b"], list("0123456789"), "KO AV RU CA UM DR".split()])
def test_bijection_round_trips(alphabet):
    for n in range(0, 500):
        assert bijective_decode(bijective_encode(n, alphabet), alphabet) == n


def test_bijective_is_unique_no_leading_symbol_ambiguity():
    seen = {}
    for n in range(0, 300):
        key = tuple(bijective_encode(n, ["a", "b"]))
        assert key not in seen  # every integer -> a distinct token sequence
        seen[key] = n


def test_zero_is_empty_sequence():
    assert bijective_encode(0, ["a", "b"]) == []
    assert bijective_decode([], ["a", "b"]) == 0


def test_token_numbers_arithmetic():
    tn = TokenNumbers("KO AV RU CA UM DR".split())  # base 6
    assert tn.decode(tn.add(tn.encode(7), tn.encode(8))) == 15
    assert tn.decode(tn.mul(tn.encode(6), tn.encode(7))) == 42


def test_token_numbers_rejects_bad_alphabet():
    with pytest.raises(ValueError):
        TokenNumbers(["a", "a"])  # not unique
    with pytest.raises(ValueError):
        bijective_decode(["z"], ["a", "b"])  # token not in alphabet
