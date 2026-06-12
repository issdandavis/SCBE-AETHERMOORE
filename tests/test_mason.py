"""The mason must build only from stones it verified IN PLACE, and never set an
empty sphere. These tests lock the mechanism: a real schematic builds a runnable
artifact; an injected stub is captured and escalated, not placed.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_mason():
    spec = importlib.util.spec_from_file_location("mason", ROOT / "scripts" / "tools" / "mason.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mason"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


M = _load_mason()


def test_mason_builds_a_complete_verified_town() -> None:
    result = M.build(M.SCHEMATICS["pacman_core"], M.PIECES, stubs=M.STUBS)
    assert result["town_complete"] is True
    assert result["stones_set"] == result["stones_total"] == 4
    assert result["escalation"] is None
    assert all(row["set"] and row["seal"] for row in result["log"])


def test_built_artifact_is_real_and_winnable() -> None:
    result = M.build(M.SCHEMATICS["pacman_core"], M.PIECES, stubs=M.STUBS)
    artifact = ROOT / result["artifact"]
    assert artifact.exists()
    spec = importlib.util.spec_from_file_location("pacman_core_built", artifact)
    game_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(game_mod)
    g = game_mod.Game()
    for mv in ["right", "right", "down", "down", "left", "left", "up"]:
        g.step(mv)
    assert g.score == 7
    assert g.won is True
    assert len(g.maze.dots) == 0
    # a wall blocks movement
    g2 = game_mod.Game()
    before = g2.player.pos
    g2.step("up")
    assert g2.player.pos == before


def test_injected_stub_is_captured_and_escalated_not_placed() -> None:
    result = M.build(M.SCHEMATICS["pacman_core"], M.PIECES, inject_stub="game", stubs=M.STUBS)
    assert result["town_complete"] is False
    assert result["stones_set"] == 3  # world, maze, player set; game captured
    assert result["escalation"] is not None
    assert result["escalation"]["slot"] == "game"
    assert "escalate_to" in result["escalation"]
    # the stub row is captured, not set
    game_row = next(r for r in result["log"] if r["slot"] == "game")
    assert game_row["set"] is False
    assert game_row["captured"] is True
    assert game_row["seal"] is None


# ── Generic pack gates: every pack in mason_stones/ is held to the same bar ──


def test_all_packs_load_without_errors() -> None:
    assert M.PACK_ERRORS == {}, M.PACK_ERRORS
    assert "snake_core" in M.REGISTRY  # the first pack proves the loader


def test_every_registered_schematic_builds_a_complete_town() -> None:
    for name, (schematic, pieces, stubs) in M.REGISTRY.items():
        result = M.build(schematic, pieces, stubs=stubs)
        assert result["town_complete"] is True, (name, result["escalation"])
        assert result["stones_set"] == result["stones_total"]
        assert all(row["set"] and row["seal"] for row in result["log"]), name


def test_every_pack_has_a_stub_and_every_stub_is_captured() -> None:
    """The degenerate-verifier guard: a pack whose stub PASSES its slot request
    has a request that verifies nothing. Every stub must crack."""
    for name, (schematic, pieces, stubs) in M.REGISTRY.items():
        assert stubs, f"pack for {name} ships no stub — no proof its requests reject hollow stones"
        stub_slots = [s for s in schematic.slots if s.piece in stubs]
        assert stub_slots, f"pack for {name} has stubs that match no slot"
        for slot in stub_slots:
            result = M.build(schematic, pieces, inject_stub=slot.name, stubs=stubs)
            assert result["town_complete"] is False, (name, slot.name, "stub was NOT captured — request too weak")
            row = next(r for r in result["log"] if r["slot"] == slot.name)
            assert row["captured"] is True and row["set"] is False, (name, slot.name)
            assert row["stub_injected"] is True, (name, slot.name)


def test_every_built_artifact_actually_runs_standalone() -> None:
    for name, (schematic, pieces, stubs) in M.REGISTRY.items():
        result = M.build(schematic, pieces, stubs=stubs)
        artifact = ROOT / result["artifact"]
        assert artifact.exists(), name
        spec = importlib.util.spec_from_file_location(f"mason_artifact_{name}", artifact)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)  # a hollow artifact would blow up here
