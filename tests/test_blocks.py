"""Block safety system — destructive double-check + shape interlock."""

import pytest

from python.scbe.blocks import BlockProgram, BlockError, CATALOG, Safety


def test_catalog_has_safety_classes():
    assert any(b.safety is Safety.DESTRUCTIVE for b in CATALOG.values())
    assert CATALOG["delete_dir"].safety is Safety.DESTRUCTIVE
    assert CATALOG["read_file"].safety is Safety.SAFE
    assert CATALOG["add"].safety is Safety.SAFE


def test_shape_interlock():
    assert BlockProgram().add("add").add("mul").shape_ok(seed=3)
    # add pops 2 from depth 1 -> underflow (blocks do not interlock)
    assert not BlockProgram().add("add").add("add").add("add").shape_ok(seed=2)


def test_safe_program_clears():
    p = BlockProgram().add("add").add("read_file", "notes.md")
    assert p.run_plan()["cleared"] is True


def test_destructive_blocked_without_confirm():
    p = BlockProgram().add("delete_file", "scratch/tmp.log")
    with pytest.raises(BlockError) as e:
        p.run_plan()
    assert "BLOCKED" in str(e.value)


def test_destructive_clears_with_confirm():
    p = BlockProgram().add("delete_file", "scratch/tmp.log", confirm="temp scratch log")
    assert p.run_plan()["cleared"] is True


@pytest.mark.parametrize(
    "block,target",
    [
        ("delete_dir", "C:\\Users\\issda"),
        ("delete_dir", "/"),
        ("format_disk", "C:"),
        ("wipe", "C:\\"),
        ("delete_file", "C:\\Windows\\System32\\kernel32.dll"),
    ],
)
def test_drive_and_system_scope_refused_even_with_confirm(block, target):
    p = BlockProgram().add(block, target, confirm="cleanup")
    with pytest.raises(BlockError) as e:
        p.run_plan()
    assert "REFUSED" in str(e.value)


def test_invalid_shape_refused():
    p = BlockProgram().add("add")  # seed default 3 ok; force underflow
    assert not BlockProgram().add("mul").add("mul").add("mul").shape_ok(seed=1)
    assert p.run_plan()["cleared"] is True
