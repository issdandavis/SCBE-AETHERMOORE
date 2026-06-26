"""PR-blocking tests for the unified verified pipeline (logic proof AND emit-faithfulness proof).

In CORE_SMOKE_PATHS via tests/crypto. Cross-face tests need node and skip cleanly without it.
"""
from __future__ import annotations

import shutil

import pytest

from src.crypto import verified_pipeline as V

requires_node = pytest.mark.skipif(shutil.which("node") is None, reason="cross-face needs node")


@requires_node
def test_valid_frame_ships_faithful_portable_code() -> None:
    lib = V.good_library()
    r = V.pipeline(lib, lib[0], lambda emits: max(emits) <= 3)
    assert r["ok"], r
    assert r["logic_proven"] and r["emit_faithful"]
    assert "def f(x)" in r["py"] and "function f(x)" in r["js"]


@requires_node
def test_buggy_emit_caught_despite_proven_logic() -> None:
    bad = V.Brick("half_badjs", lambda x: x // 2, range(8), lambda x: x // 2, "({x}//2)", "({x}/2)")
    assert bad.proven[0] is True                       # logic proof passes...
    lib = [V.good_library()[0], V.good_library()[1], bad]
    r = V.pipeline(lib, lib[0], lambda emits: max(emits) <= 3)
    assert r["ok"] is False                            # ...but the emit proof fails
    assert "UNFAITHFUL" in r["reason"] and r["witness"] is not None


def test_buggy_logic_caught_before_emit() -> None:
    fake = V.Brick("fake", lambda x: x + 1, range(8), lambda x: x, "({x})", "({x})")
    assert fake.proven[0] is False
    r = V.pipeline([fake], fake, lambda emits: True)
    assert r["ok"] is False
    assert "fails its spec" in r["reason"]


def test_unreachable_goal_fails_honestly() -> None:
    lib = V.good_library()
    r = V.pipeline(lib, lib[0], lambda emits: emits == frozenset([999]))
    assert r["ok"] is False
    assert "no conserving arrangement" in r["reason"]
