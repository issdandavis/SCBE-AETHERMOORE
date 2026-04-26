"""Smoke tests for scripts/dsl/synthesize_triples.py.

Per L_dsl_synthesis Step 2, every meta dict drawn from the supported task set
must produce a depth<=3 program whose final state satisfies the structural
shape predicate, AND every emitted program must round-trip through
`parse_program` so the BFS output is also valid DSL source.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.dsl.primitives import parse_program, run_program  # noqa: E402

_SPEC = importlib.util.spec_from_file_location(
    "_synth_under_test",
    ROOT / "scripts" / "dsl" / "synthesize_triples.py",
)
_synth = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
sys.modules["_synth_under_test"] = _synth
_SPEC.loader.exec_module(_synth)


def _do_synth(meta: Dict[str, Any]):
    result = _synth.synthesize(meta)
    assert result is not None, f"no program for meta={meta}"
    program, final = result
    assert 1 <= len(program) <= _synth.DEPTH
    return program, final


@pytest.mark.parametrize(
    "meta,expect_tongue,expect_well",
    [
        ({"task": "translate_one", "src": "RU", "dst": "DR"}, "DR", "TRANSLATED"),
        ({"task": "translate_all", "src": "KO"}, "KO", "TRANSLATED_ALL"),
        ({"task": "identify", "tongue": "AV"}, "AV", "IDENTIFIED"),
        ({"task": "edit_slot_one", "dst": "RU", "slot": "body"}, "RU", "EDIT_BODY"),
        ({"task": "edit_slot_all", "src": "AV", "slot": "init"}, "AV", "EDIT_ALL_INIT"),
        ({"task": "align", "src": "KO", "dst": "CA"}, "CA", "ALIGNED"),
        ({"task": "governance_tag", "tongue": "UM"}, "UM", "GOVERNANCE"),
        ({"task": "multiline_edit", "src": "KO"}, "KO", "MULTILINE"),
        ({"category": "dialogue", "speaker_tongue": "AV", "listener_tongue": "KO"}, "KO", "SEALED"),
    ],
)
def test_synth_shape_predicates(meta, expect_tongue, expect_well):
    program, final = _do_synth(meta)
    assert final.tongue == expect_tongue
    assert final.well == expect_well


@pytest.mark.parametrize(
    "meta",
    [
        {"task": "translate_one", "src": "RU", "dst": "DR"},
        {"task": "identify", "tongue": "KO"},
        {"task": "edit_slot_one", "dst": "AV", "slot": "loop_body"},
        {"task": "align", "src": "KO", "dst": "CA"},
        {"category": "dialogue", "speaker_tongue": "AV", "listener_tongue": "KO"},
    ],
)
def test_emitted_program_parses_and_runs(meta):
    program, expected_final = _do_synth(meta)
    src = "\n".join(_synth._emit_op(n, a) for n, a in program)
    ops = parse_program(src)
    assert [op.name for op in ops] == [n for n, _ in program]
    init_tongue = _synth._shape_for(meta)[2]
    from python.scbe.dsl.primitives import initial_state

    final = run_program(ops, initial_state(init_tongue))
    assert final.tongue == expected_final.tongue
    assert final.well == expected_final.well


def test_synth_unknown_task_returns_none():
    assert _synth.synthesize({"task": "not_a_real_task"}) is None
    assert _synth.synthesize({}) is None


def test_synth_bfs_does_not_explode():
    """Pathological-looking but valid meta should still terminate quickly."""
    meta = {"task": "translate_one", "src": "KO", "dst": "DR", "extra": "noise"}
    program, _final = _do_synth(meta)
    assert len(program) <= _synth.DEPTH


def test_split_routing():
    assert _synth._split_for("training-data/sft/foo_train.sft.jsonl") == "train"
    assert _synth._split_for("training-data/sft/foo_holdout.sft.jsonl") == "holdout"


def test_coverage_gate_constants_are_in_canon_range():
    assert 0.0 < _synth.COVERAGE_GATE <= 1.0
    assert _synth.DEPTH >= 1
