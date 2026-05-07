"""Tests for the structural Dynamo Core SCAD validator.

Covers the failure modes the validator is designed to catch:
unmatched braces, missing constants/modules, perturb-table length
mismatch, seed decimal/hex inconsistency, and absent geometry."""

from __future__ import annotations

from pathlib import Path


from python.scbe.mahss_dynamo_core_scad import render_dynamo_core_scad, write_dynamo_core_scad
from python.scbe.mahss_dynamo_core_scad_validator import (
    validate_dynamo_core_scad,
    validate_scad_file,
)

# --------------------------------------------------------------------------
# Happy path: emitter output passes validation
# --------------------------------------------------------------------------


def test_emitter_output_validates_clean():
    src = render_dynamo_core_scad(seed=42)
    result = validate_dynamo_core_scad(src)
    assert result.ok, f"clean output should validate; errors: {result.errors}"
    assert result.errors == []
    assert result.facts.get("num_ridges") == 16
    assert result.facts.get("perturb_table_length") == 16


def test_emitter_output_seed_decimal_equals_hex():
    src = render_dynamo_core_scad(seed=0xCAFEBABE_DEADBEEF)
    result = validate_dynamo_core_scad(src)
    assert result.ok
    assert result.facts["seed_decimal"] == 0xCAFEBABE_DEADBEEF
    assert result.facts["seed_hex"] == "cafebabedeadbeef"


def test_validate_scad_file_round_trip(tmp_path: Path):
    out = tmp_path / "alice.scad"
    write_dynamo_core_scad(out, seed=7)
    result = validate_scad_file(out)
    assert result.ok
    assert result.path == str(out)


def test_validate_missing_file_returns_failure(tmp_path: Path):
    result = validate_scad_file(tmp_path / "nope.scad")
    assert not result.ok
    assert any("file not found" in e for e in result.errors)


# --------------------------------------------------------------------------
# Negative tests: validator catches the failure modes it's supposed to
# --------------------------------------------------------------------------


def test_unmatched_brace_fails():
    src = render_dynamo_core_scad(seed=1)
    # Drop a closing brace
    broken = src.replace('color("Red") auxetic_sheath();\n', 'color("Red") auxetic_sheath();\n{ // hanging\n', 1)
    result = validate_dynamo_core_scad(broken)
    assert not result.ok
    assert any("unclosed" in e or "unmatched" in e for e in result.errors)


def test_mismatched_bracket_fails():
    src = "module x() { print([1, 2, 3); }"  # ']' missing, ')' instead
    result = validate_dynamo_core_scad(src)
    assert not result.ok


def test_missing_required_module_fails():
    src = render_dynamo_core_scad(seed=1)
    broken = src.replace("module auxetic_sheath()", "module __not_auxetic__()")
    result = validate_dynamo_core_scad(broken)
    assert not result.ok
    assert any("auxetic_sheath" in e for e in result.errors)


def test_missing_required_constant_fails():
    src = render_dynamo_core_scad(seed=1)
    broken = src.replace("R_tung = 1.5;", "// R_tung omitted")
    result = validate_dynamo_core_scad(broken)
    assert not result.ok
    assert any("R_tung" in e for e in result.errors)


def test_perturb_table_length_mismatch_fails():
    src = render_dynamo_core_scad(seed=1)
    # Surgically truncate the perturb table to length 5
    import re

    broken = re.sub(
        r"perturb_mm = \[([^\]]+)\];",
        "perturb_mm = [0.0, 0.0, 0.0, 0.0, 0.0];",
        src,
    )
    result = validate_dynamo_core_scad(broken)
    assert not result.ok
    assert any("perturb_mm length" in e for e in result.errors)


def test_seed_decimal_hex_mismatch_fails():
    src = render_dynamo_core_scad(seed=42)
    # Replace just the hex comment with a wrong hex
    broken = src.replace("// hex 000000000000002a", "// hex 000000000000002b")
    result = validate_dynamo_core_scad(broken)
    assert not result.ok
    assert any("seed decimal" in e for e in result.errors)


def test_missing_difference_block_fails():
    src = "module auxetic_sheath() {} module seeded_hyperbolic_ridge(k) {}"
    # plus required constants stubbed
    src = (
        (
            "phi=1; golden_angle=137; R_tung=1; t_sheath=1; r_throat=1; c_z=1; "
            "num_ridges=2; mesh_height=10; seed=1; perturb_mm=[0,0]; "
        )
        + src
        + " auxetic_sheath();"
    )
    result = validate_dynamo_core_scad(src)
    assert not result.ok
    assert any("difference" in e for e in result.errors)


def test_warning_on_oversized_perturb_does_not_fail():
    """Perturbations > 1 mm warn but don't fail — they might be
    intentional under a non-default perturb_scale_mm."""

    src = render_dynamo_core_scad(seed=1)
    import re

    broken = re.sub(
        r"perturb_mm = \[([^\]]+)\];",
        "perturb_mm = [" + ", ".join(["3.5"] * 16) + "];",
        src,
    )
    result = validate_dynamo_core_scad(broken)
    assert result.ok
    assert result.warnings
    assert any("> 1 mm" in w for w in result.warnings)
