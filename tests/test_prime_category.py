"""Tests for prime-coded categories (src/prime_category.py)."""

import pytest

from src.prime_category import PrimeCategories


def test_stable_prime_assignment():
    pc = PrimeCategories(["red", "green", "blue", "alpha"])
    assert pc.mapping == {"red": 2, "green": 3, "blue": 5, "alpha": 7}


def test_assignment_dedupes_and_keeps_order():
    pc = PrimeCategories(["a", "b", "a", "c", " b "])
    assert pc.mapping == {"a": 2, "b": 3, "c": 5}


def test_code_is_product_of_primes():
    pc = PrimeCategories(["red", "green", "blue", "alpha"])
    assert pc.code(["red", "blue"]) == 2 * 5
    assert pc.code(["green", "alpha"]) == 3 * 7
    assert pc.code([]) == 1


def test_code_is_squarefree_on_repeats():
    pc = PrimeCategories(["red", "green"])
    assert pc.code(["red", "red", "green"]) == 2 * 3  # repeats collapse


def test_decode_roundtrips_code():
    pc = PrimeCategories(["red", "green", "blue", "alpha"])
    for combo in (["red"], ["red", "blue"], ["green", "alpha", "red"]):
        code = pc.code(combo)
        assert sorted(pc.decode(code)) == sorted(set(combo))


def test_in_category_is_divisibility():
    pc = PrimeCategories(["red", "green", "blue"])
    code = pc.code(["red", "blue"])  # 2 * 5 = 10
    assert pc.in_category(code, "red") is True
    assert pc.in_category(code, "blue") is True
    assert pc.in_category(code, "green") is False


def test_sort_by_category_sieves_items():
    pc = PrimeCategories(["urgent", "billing", "bug"])
    items = {
        "ticket-1": ["urgent", "bug"],
        "ticket-2": ["billing"],
        "ticket-3": ["urgent", "billing"],
        "ticket-4": ["bug"],
    }
    assert pc.sort_by_category(items, "urgent") == ["ticket-1", "ticket-3"]
    assert pc.sort_by_category(items, "billing") == ["ticket-2", "ticket-3"]
    assert pc.sort_by_category(items, "bug") == ["ticket-1", "ticket-4"]


def test_unknown_category_raises():
    pc = PrimeCategories(["a", "b"])
    with pytest.raises(KeyError):
        pc.prime_of("z")
    with pytest.raises(KeyError):
        pc.code(["a", "z"])


def test_decode_rejects_unassigned_prime():
    pc = PrimeCategories(["a", "b"])  # primes 2, 3
    with pytest.raises(ValueError):
        pc.decode(11)  # 11 has no category
    with pytest.raises(ValueError):
        pc.decode(0)


def test_empty_universe_raises():
    with pytest.raises(ValueError):
        PrimeCategories([])
