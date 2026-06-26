"""PR-blocking tests for the GeoSeal CORRECTNESS gate (the cross-face half of the seal).

Mirrors test_geoseal_execution_gate.py (the SAFETY half) so this gate joins the same CI core-smoke lane
(tests/crypto is in scripts/system/run_core_python_checks.py CORE_SMOKE_PATHS). Where the safety gate
asks "is this code dangerous?", the correctness gate asks "do the language faces AGREE by execution?":
  SEAL   -- all faces agree on every in-domain input
  REJECT -- faces diverge (a generation/portability bug) + a witness input
  FLAG   -- a face won't run / coverage too thin -> route to AI review

The JS face needs node; tests that must RUN it skip cleanly when node is absent (so CI without node
can't false-fail). node IS present on standard GitHub runners, so these run as real merge blockers there.
"""
from __future__ import annotations

import shutil

import pytest

from src.crypto.geoseal_correctness_gate import correctness_gate

requires_node = pytest.mark.skipif(shutil.which("node") is None, reason="JS face needs node")

PY_ADD = "def add(a, b):\n    return a + b"
JS_ADD = "function add(a, b){ return a + b; }"
JS_BUG = "function add(a, b){ return a - b; }"   # divergent face = a real generation bug
SEEDS = [(2, 3), (5, 7)]


@requires_node
def test_agreeing_faces_seal() -> None:
    r = correctness_gate({"python": PY_ADD, "javascript": JS_ADD}, "add", SEEDS)
    assert r["verdict"] == "SEAL", r


@requires_node
def test_divergent_face_rejects_with_witness() -> None:
    r = correctness_gate({"python": PY_ADD, "javascript": JS_BUG}, "add", SEEDS)
    assert r["verdict"] == "REJECT", r
    w = r["witness"]
    assert w["python"][0] == "ok" and w["javascript"][0] == "ok"
    # python a+b must differ from javascript a-b on the witness input (the divergence)
    assert w["python"][1] != w["javascript"][1], w


def test_unrunnable_face_flags_for_review() -> None:
    # a broken face -> FLAG regardless of whether node is present (both paths route to AI review)
    r = correctness_gate({"python": PY_ADD, "javascript": "function add( syntax error"}, "add", SEEDS)
    assert r["verdict"] == "FLAG", r
    assert r.get("route") == "ai_review", r


@requires_node
def test_floor_div_vs_true_div_is_caught() -> None:
    # a real polyglot-emit bug: Python `//` (floor) vs JS `/` (true) -> diverge on the seed itself.
    py = "def idiv(a, b):\n    return a // b"
    js = "function idiv(a, b){ return a / b; }"
    r = correctness_gate({"python": py, "javascript": js}, "idiv", [(7, 2), (10, 3)])
    assert r["verdict"] == "REJECT", r   # 7 // 2 == 3  but  7 / 2 == 3.5
