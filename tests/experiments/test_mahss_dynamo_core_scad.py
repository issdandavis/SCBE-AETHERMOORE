"""Tests for the Dynamo Core OpenSCAD emitter.

Covers determinism, structural validity, parameter threading, the
crossover guarantee that Python sim and OpenSCAD source use bit-identical
perturbation values, and the geometry manifest shape.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

from python.scbe.mahss_crypto_lattice import derive_perturbation_field
from python.scbe.mahss_dynamo_core_scad import (
    DynamoCoreGeometry,
    manifest_with_geometry,
    render_dynamo_core_scad,
    write_dynamo_core_scad,
)


def test_default_geometry_matches_user_spec():
    geom = DynamoCoreGeometry()
    assert geom.R_tung == 1.5
    assert geom.t_sheath == 3.0
    assert geom.r_throat == 1.5
    assert geom.c_z == 0.8
    assert geom.num_ridges == 16
    assert geom.mesh_height == 60.0


def test_render_is_deterministic_for_same_seed():
    a = render_dynamo_core_scad(seed=42)
    b = render_dynamo_core_scad(seed=42)
    assert a == b


def test_render_differs_for_different_seeds():
    a = render_dynamo_core_scad(seed=1)
    b = render_dynamo_core_scad(seed=2)
    assert a != b


def test_render_includes_seed_value_and_hex():
    seed = 0xCAFEBABE_DEADBEEF
    src = render_dynamo_core_scad(seed)
    assert f"seed = {seed};" in src
    assert "cafebabedeadbeef" in src


def test_render_threads_geometry_parameters():
    geom = DynamoCoreGeometry(R_tung=2.0, t_sheath=4.5, num_ridges=24, mesh_height=80.0)
    src = render_dynamo_core_scad(seed=7, geometry=geom)
    assert "R_tung = 2.0;" in src
    assert "t_sheath = 4.5;" in src
    assert "num_ridges = 24;" in src
    assert "mesh_height = 80.0;" in src


def test_render_has_required_openscad_structure():
    src = render_dynamo_core_scad(seed=99)
    # Top-level constants exist
    assert "phi = (1 + sqrt(5)) / 2;" in src
    assert "golden_angle =" in src
    # Required modules
    assert "module seeded_hyperbolic_ridge(k)" in src
    assert "module auxetic_sheath()" in src
    # Top-level construction
    assert "difference()" in src
    assert "cylinder(h=mesh_height, r=R_tung * 1.15" in src  # tungsten shell
    assert "cylinder(h=mesh_height, r=R_tung * 0.85" in src  # ferrofluid cavity
    # Auxetic sheath rendered red
    assert 'color("Red") auxetic_sheath();' in src


def test_render_perturb_table_length_matches_num_ridges():
    geom = DynamoCoreGeometry(num_ridges=8)
    src = render_dynamo_core_scad(seed=12345, geometry=geom)
    match = re.search(r"perturb_mm = \[([^\]]+)\];", src)
    assert match is not None
    values = match.group(1).split(",")
    assert len(values) == 8


def test_render_perturb_values_are_python_field_times_scale():
    """The crossover guarantee: the OpenSCAD literal array must be the
    Python-computed perturbation field multiplied by perturb_scale_mm,
    NOT a recomputed value with floating-point drift."""

    geom = DynamoCoreGeometry(num_ridges=11, perturb_scale_mm=0.7)
    seed = 0xDEADBEEF
    src = render_dynamo_core_scad(seed, geom)

    expected = derive_perturbation_field(seed, 11, bound=geom.perturb_bound) * 0.7

    match = re.search(r"perturb_mm = \[([^\]]+)\];", src)
    assert match is not None
    parsed = [float(x.strip()) for x in match.group(1).split(",")]

    assert np.allclose(parsed, expected, atol=1e-6)


def test_render_perturb_respects_physical_bound():
    """No baked perturbation may exceed perturb_scale_mm * perturb_bound mm."""

    geom = DynamoCoreGeometry(perturb_scale_mm=0.5, perturb_bound=0.05)
    src = render_dynamo_core_scad(seed=1234567, geometry=geom)
    match = re.search(r"perturb_mm = \[([^\]]+)\];", src)
    parsed = [float(x.strip()) for x in match.group(1).split(",")]
    bound_mm = 0.5 * 0.05
    assert all(abs(v) <= bound_mm + 1e-9 for v in parsed)


def test_write_dynamo_core_scad_round_trip(tmp_path: Path):
    out = tmp_path / "subdir" / "alice.scad"
    written = write_dynamo_core_scad(out, seed=0xABCDEF)
    assert written.exists()
    src = written.read_text(encoding="utf-8")
    assert "seed = 11259375;" in src  # 0xabcdef as decimal


def test_manifest_with_geometry_is_json_serializable():
    seed = 0x1234_5678_9ABC_DEF0
    manifest = manifest_with_geometry(seed)
    blob = json.dumps(manifest)
    decoded = json.loads(blob)
    assert decoded["seed"] == seed
    assert decoded["seed_hex"] == f"{seed:016x}"
    assert decoded["geometry"]["R_tung"] == 1.5
    assert decoded["geometry"]["num_ridges"] == 16
    assert len(decoded["perturb_field_mm"]) == 16
    assert decoded["perturb_max_abs_mm"] >= 0.0


def test_manifest_perturb_max_abs_within_physical_bound():
    geom = DynamoCoreGeometry(perturb_scale_mm=0.5, perturb_bound=0.05)
    manifest = manifest_with_geometry(seed=987654321, geometry=geom)
    assert manifest["perturb_max_abs_mm"] <= 0.5 * 0.05 + 1e-9


def test_two_seeds_produce_two_distinct_perturb_tables():
    src_a = render_dynamo_core_scad(seed=1)
    src_b = render_dynamo_core_scad(seed=2)
    a_table = re.search(r"perturb_mm = \[([^\]]+)\];", src_a).group(1)
    b_table = re.search(r"perturb_mm = \[([^\]]+)\];", src_b).group(1)
    assert a_table != b_table
