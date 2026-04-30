"""Lock in scoring semantics for the SCBE Bijective Tongue Coder Round-Trip benchmark.

Guards against silent drift in the public scorer (`score.py`) — a Kaggle leaderboard
must produce stable, reproducible numbers across runs.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCORE_PATH = REPO_ROOT / "scripts" / "benchmarks" / "scbe_bijective_round_trip" / "score.py"


def _load_score_module():
    spec = importlib.util.spec_from_file_location("scbe_round_trip_score", SCORE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def score_mod():
    return _load_score_module()


def test_schema_constant(score_mod):
    assert score_mod.SCHEMA == "scbe_bijective_round_trip_score_v1"


def test_empty_prediction_hard_fails(score_mod):
    s = score_mod.score_row("", "```py\nprint(1)\n```", {"task": "identify"})
    assert s["hard_fail"] is True
    assert s["row_score"] == 0.0
    assert s["token_recall"] == 0.0


def test_decode_error_hard_fails(score_mod):
    s = score_mod.score_row("DECODE_ERROR: bad input", "```py\nprint(1)\n```", {"task": "identify"})
    assert s["hard_fail"] is True
    assert s["row_score"] == 0.0


def test_perfect_echo_scores_one(score_mod):
    ref = "```python\nprint('hi')\n```\n"
    s = score_mod.score_row(ref, ref, {"task": "translate_one"})
    assert s["hard_fail"] is False
    assert s["token_recall"] == pytest.approx(1.0)
    assert s["structural_preservation"] == pytest.approx(1.0)
    assert s["row_score"] == pytest.approx(1.0)


def test_partial_recall(score_mod):
    ref = "```py\nprint('hello world')\n```"
    pred = "```py\nprint('hello')\n```"
    s = score_mod.score_row(pred, ref, {"task": "translate_one"})
    assert s["hard_fail"] is False
    assert 0.0 < s["token_recall"] < 1.0
    assert s["structural_preservation"] == pytest.approx(1.0)


def test_missing_codeblock_drops_structure(score_mod):
    ref = "```py\nprint('x')\n```"
    pred = "print('x')"
    s = score_mod.score_row(pred, ref, {"task": "translate_one"})
    assert s["structural_preservation"] == pytest.approx(0.0)
    assert s["row_score"] == pytest.approx(0.0)


def test_tongue_header_counted(score_mod):
    ref = "### TONGUE: KO\n```py\nx=1\n```\n### TONGUE: AV\n```js\nlet x=1;\n```"
    pred_full = ref
    pred_one = "### TONGUE: KO\n```py\nx=1\n```"
    s_full = score_mod.score_row(pred_full, ref, {"task": "translate_all"})
    s_one = score_mod.score_row(pred_one, ref, {"task": "translate_all"})
    assert s_full["structural_preservation"] == pytest.approx(1.0)
    assert s_one["structural_preservation"] < s_full["structural_preservation"]


def test_overall_aggregation(score_mod):
    holdout = [
        {"id": "a", "reference": "```py\nx=1\n```", "meta": {"task": "identify", "tongue": "KO"}},
        {"id": "b", "reference": "```py\ny=2\n```", "meta": {"task": "identify", "tongue": "KO"}},
    ]
    submission = {"a": "```py\nx=1\n```", "b": ""}
    report = score_mod.score(holdout, submission)
    assert report["schema"] == "scbe_bijective_round_trip_score_v1"
    assert report["n_rows"] == 2
    assert report["overall_score"] == pytest.approx(0.5)
    assert report["task_breakdown"]["identify"]["n"] == 2
    assert report["tongue_breakdown"]["KO"]["n"] == 2


def test_tokenizer_handles_punctuation(score_mod):
    toks = score_mod._tokenize("foo(bar, 42)")
    assert "foo" in toks
    assert "bar" in toks
    assert "42" in toks
    assert "(" in toks
    assert "," in toks
