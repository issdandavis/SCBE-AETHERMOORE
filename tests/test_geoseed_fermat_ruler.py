from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src.geoseed.fermat_ruler import (
    FERMAT_UNIT,
    add_fermat_pairs,
    build_fermat_coordinate,
    build_fermat_semigroup_summary,
    build_operation_report,
    build_prime_residue_sample,
    enumerate_fermat_generated,
    multiply_fermat_pairs,
    recompose_fermat_pair,
)

ROOT = Path(__file__).resolve().parents[1]


def test_fermat_coordinate_tracks_diagonal_binary_identity() -> None:
    coordinate = build_fermat_coordinate(FERMAT_UNIT * 2 + 5)

    assert coordinate.quotient == 2
    assert coordinate.residue == 5
    assert coordinate.low_sum == 7
    assert coordinate.binary_high == 2
    assert coordinate.binary_low == 7
    assert coordinate.diagonal_identity_holds is True
    assert coordinate.is_on_spine is False


def test_fermat_coordinate_places_65537_on_the_spine() -> None:
    coordinate = build_fermat_coordinate(FERMAT_UNIT)

    assert coordinate.quotient == 1
    assert coordinate.residue == 0
    assert coordinate.is_on_spine is True
    assert coordinate.is_prime is True
    assert coordinate.fermat_generated is True
    assert coordinate.factor_vector == {"p65537": 1}


def test_fermat_pair_arithmetic_recomposes_exactly() -> None:
    left = build_fermat_coordinate(FERMAT_UNIT * 3 + 9)
    right = build_fermat_coordinate(FERMAT_UNIT + 11)

    sum_pair = add_fermat_pairs((left.quotient, left.residue), (right.quotient, right.residue))
    product_pair = multiply_fermat_pairs((left.quotient, left.residue), (right.quotient, right.residue))

    assert recompose_fermat_pair(*sum_pair) == left.n + right.n
    assert recompose_fermat_pair(*product_pair) == left.n * right.n


def test_operation_report_matches_direct_integer_arithmetic() -> None:
    report = build_operation_report(90, 17)

    assert report.sum_coordinate.n == 107
    assert recompose_fermat_pair(*report.sum_pair) == 107
    assert report.product_coordinate.n == 1530
    assert recompose_fermat_pair(*report.product_pair) == 1530


def test_prime_residue_sample_detects_65537_zero_lane() -> None:
    sample = build_prime_residue_sample(FERMAT_UNIT, top=4)

    assert sample.total_primes > 0
    assert sample.zero_residue_primes == (FERMAT_UNIT,)
    assert sample.occupied_nonzero_lanes >= 4


def test_fermat_generated_semigroup_summary_stays_in_generator_family() -> None:
    values = enumerate_fermat_generated(100)
    assert values[:10] == (1, 2, 3, 4, 5, 6, 8, 9, 10, 12)
    assert 90 in values
    assert 7 not in values

    summary = build_fermat_semigroup_summary(100, sample=8)
    assert summary.total_members == len(values)
    assert summary.first_members == values[:8]
    assert all(coordinate.fermat_generated for coordinate in summary.sample_coordinates)


def test_fermat_ruler_cli_emits_coordinate_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseed.fermat_ruler",
            "coordinate",
            str(FERMAT_UNIT + 3),
            "--json",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["quotient"] == 1
    assert payload["residue"] == 3
    assert payload["diagonal_identity_holds"] is True
