"""PR-blocking tests for the verified+portable alphabet: every op logic-proven + emit-faithful."""
from __future__ import annotations

import shutil

import pytest

from src.crypto import portable_alphabet as A
from src.crypto import verified_pipeline as V

requires_node = pytest.mark.skipif(shutil.which("node") is None, reason="emit check needs node")


def test_every_op_logic_proven() -> None:
    for b in A.ALPHABET:
        assert b.proven[0] is True, (b.name, b.proven)


@requires_node
def test_every_op_emit_faithful() -> None:
    for r in A.verify_alphabet():
        assert r["emit_faithful"] is True, (r["op"], r["witness"])


@requires_node
def test_naive_negmod_emit_is_caught() -> None:
    # an UNguarded dec js emit diverges from python at x=0 (py 15 vs js -1) -> faithfulness must catch
    naive = V.Brick("dn", lambda x: (x - 1) % 16, range(16), lambda x: (x - 1) % 16, "(({x}-1)%16)", "(({x}-1)%16)")
    cf = V.cross_face("def f(x):\n    return " + naive.py.format(x="x"),
                      "function f(x){ return " + naive.js.format(x="x") + "; }", naive.fn, naive.domain)
    assert cf["all_agree"] is False and cf["witness"] is not None
