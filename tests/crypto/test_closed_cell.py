"""PR-blocking tests for the correct-by-construction verification cell (src/crypto/closed_cell.py).

In CORE_SMOKE_PATHS via tests/crypto, so this gates merges. Pure-Python, no network/ollama/node -- it
graduates because it runs in the pytest harness with no external life-support. Proves the cell: compiles
verified frames, rejects fakes from the inside, fails honestly on the unreachable, and is genuinely closed.
"""
from __future__ import annotations

import re

from src.crypto import closed_cell as C


def test_compiles_a_verified_frame_with_complete_proof() -> None:
    lib = C.standard_library()
    r = C.run_cell(lib, lib[0], lambda emits: max(emits) <= 3)
    assert r["ok"], r
    assert all(b["proven"] in (True, "primitive") for b in r["proof"]["bricks"]), r["proof"]
    assert all(j["conserved"] for j in r["proof"]["joints"]), r["proof"]
    frame = r["frame"]
    assert all(frame.fn(x) <= 3 for x in frame.domain)


def test_a_fake_vessel_cannot_survive_the_cell() -> None:
    fake = C.Brick("fake_half", lambda x: (x + 1) // 2, range(8), spec=lambda x: x // 2)  # off-by-one
    assert fake.proven[0] is False
    r = C.run_cell([fake], fake, lambda emits: True)
    assert r["ok"] is False
    assert "FAILS its spec" in r["reason"]


def test_unreachable_spec_fails_honestly() -> None:
    lib = C.standard_library()
    r = C.run_cell(lib, lib[0], lambda emits: emits == frozenset([999]))
    assert r["ok"] is False
    assert "no conserving arrangement" in r["reason"]


def test_a_nonconserving_joint_is_rejected() -> None:
    import pytest

    lib = {b.name: b for b in C.standard_library()}
    with pytest.raises(C.ContractError):
        C.bond(lib["inc4"], lib["half"])   # inc4 emits 0..15, half accepts only 0..7


def test_every_standard_vessel_is_proven() -> None:
    for b in C.standard_library():
        assert b.proven[0] in (True, "primitive"), (b.name, b.proven)


def test_the_cell_is_actually_closed_no_external_imports() -> None:
    src = open(C.__file__, encoding="utf-8").read()
    imports = re.findall(r"^\s*(?:import|from)\s+([\w.]+)", src, re.M)
    banned = {"requests", "ollama", "subprocess", "socket", "urllib", "http", "particle_chem"}
    leaked = [m for m in imports if m.split(".")[0] in banned]
    assert not leaked, f"closed cell leaked external dependency: {leaked}"
