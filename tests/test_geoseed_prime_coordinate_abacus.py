from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.geoseed.prime_coordinate_abacus import (
    build_prime_coordinate,
    build_prime_coordinate_abacus,
    factorize,
    prime_pi,
)

ROOT = Path(__file__).resolve().parents[1]


def test_prime_coordinate_maps_composite_neighbor_structure() -> None:
    coordinate = build_prime_coordinate(90)

    assert coordinate.n == 90
    assert coordinate.is_prime is False
    assert coordinate.prime_index == 24
    assert coordinate.anchor_prime == 89
    assert coordinate.next_prime == 97
    assert coordinate.gap_to_anchor == 1
    assert coordinate.gap_to_next == 7
    assert coordinate.big_omega == 4
    assert coordinate.little_omega == 3
    assert coordinate.factor_vector == {"p2": 1, "p3": 2, "p5": 1}
    assert coordinate.residues == {"mod30": 0, "mod210": 90, "mod2310": 90}
    assert coordinate.wheel_units["mod30"] is False


def test_prime_coordinate_marks_anchor_contact_for_primes() -> None:
    coordinate = build_prime_coordinate(97)

    assert coordinate.is_prime is True
    assert coordinate.prime_index == 25
    assert coordinate.anchor_prime == 97
    assert coordinate.next_prime == 101
    assert coordinate.gap_to_anchor == 0
    assert coordinate.gap_to_next == 4
    assert coordinate.big_omega == 1
    assert coordinate.little_omega == 1
    assert coordinate.factor_vector == {"p97": 1}
    assert coordinate.residues["mod30"] == 7
    assert coordinate.wheel_units["mod30"] is True


def test_prime_coordinate_handles_unit_as_depth_zero() -> None:
    coordinate = build_prime_coordinate(1)

    assert coordinate.prime_index == 0
    assert coordinate.anchor_prime is None
    assert coordinate.next_prime == 2
    assert coordinate.gap_to_anchor is None
    assert coordinate.gap_to_next == 1
    assert coordinate.big_omega == 0
    assert coordinate.little_omega == 0
    assert coordinate.factor_vector == {}


def test_prime_coordinate_abacus_emits_anchor_factor_and_residue_layers() -> None:
    abacus = build_prime_coordinate_abacus(90)

    assert abacus.schema_version == "geoseed_prime_coordinate_abacus_v1"
    assert [layer["id"] for layer in abacus.layers] == [
        "prime-coordinate-anchor-90",
        "prime-factor-vector-90",
        "prime-residue-compass-90",
    ]
    factor_rows = abacus.layers[1]["rows"]
    material_load = sum(row["value"] * row["count"] for row in factor_rows)
    assert material_load == 13
    anchor_rows = {row["id"]: row for row in abacus.layers[0]["rows"]}
    assert anchor_rows["prime-index"]["count"] == 24
    assert anchor_rows["big-omega"]["count"] == 4


def test_factorize_and_prime_pi_reference_values() -> None:
    assert factorize(100) == {2: 2, 5: 2}
    assert factorize(97) == {97: 1}
    assert prime_pi(100) == 25


def test_prime_coordinate_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        build_prime_coordinate(0)

    with pytest.raises(ValueError, match="residue bases"):
        build_prime_coordinate(10, residue_bases=(1,))


def test_prime_coordinate_cli_outputs_machine_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseed.prime_coordinate_abacus",
            "90",
            "--json",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["coordinate"]["n"] == 90
    assert payload["coordinate"]["prime_index"] == 24
    assert payload["coordinate"]["factor_vector"] == {"p2": 1, "p3": 2, "p5": 1}
    assert len(payload["layers"]) == 3
