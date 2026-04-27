from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import build_cross_tongue_project as builder  # noqa: E402

_SPEC = importlib.util.spec_from_file_location(
    "_emit_cross_tongue_sft_under_test",
    ROOT / "scripts" / "emit_cross_tongue_sft.py",
)
emitter = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
sys.modules["_emit_cross_tongue_sft_under_test"] = emitter
_SPEC.loader.exec_module(emitter)


def _bundle(project: str = "arithmetic_basics") -> dict:
    return builder.build_bundle(project, builder.PROJECT_SPECS[project])


@pytest.mark.parametrize("project", sorted(builder.PROJECT_SPECS.keys()))
def test_emit_pairs_counts_translate_and_identify_rows(project: str) -> None:
    bundle = _bundle(project)
    rows = emitter.emit_pairs(bundle)

    n_algos = len(bundle["algorithms"])
    n_tongues = 6
    expected_translate = n_algos * n_tongues * (n_tongues - 1)
    expected_identify = n_algos * n_tongues
    assert len(rows) == expected_translate + expected_identify
    assert sum(1 for row in rows if row["meta"]["task"] == "translate_one") == expected_translate
    assert sum(1 for row in rows if row["meta"]["task"] == "identify") == expected_identify


def test_translate_rows_preserve_slot_map_and_tongues() -> None:
    rows = emitter.emit_pairs(_bundle())
    row = next(
        item
        for item in rows
        if item["meta"]["task"] == "translate_one"
        and item["meta"]["algorithm"] == "sum_list"
        and item["meta"]["src"] == "KO"
        and item["meta"]["dst"] == "RU"
    )

    assert "Source tongue: KO (Python)" in row["messages"][1]["content"]
    assert "Translate to tongue RU (Rust)" in row["messages"][1]["content"]
    assert "Slot map: sig, init, loop_open, loop_body, ret" in row["messages"][2]["content"]


def test_identify_rows_include_algorithm_description() -> None:
    rows = emitter.emit_pairs(_bundle())
    row = next(
        item
        for item in rows
        if item["meta"]["task"] == "identify"
        and item["meta"]["algorithm"] == "is_palindrome"
        and item["meta"]["tongue"] == "DR"
    )

    assert "algorithm: is_palindrome" in row["messages"][2]["content"]
    assert "description: True when s reads the same forward and reversed" in row["messages"][2]["content"]


def test_refuses_non_green_bundle() -> None:
    bundle = copy.deepcopy(_bundle())
    bundle["summary"]["all_green"] = False

    try:
        emitter.emit_pairs(bundle)
    except ValueError as exc:
        assert "not all-green" in str(exc)
    else:
        raise AssertionError("broken bundle should not emit SFT")

