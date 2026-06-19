"""toolkit_map: the interactive staged map the AI walks to learn + use every SCBE system.

Tests prove the map starts with one area open, routing names the right tool for a plain task (and
flags locked areas), traversal clears the pure-python core + seals progress, and the Pazaak strategy
layer counts the task portfolio and recommends a move.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.toolkit_map import TaskMap  # noqa: E402

_CORE = {"Sieve Gate", "Prime Region Map", "Stepwise Loomflow", "Reversible Board", "Context Ledger"}


def test_map_starts_with_one_area_available():
    m = TaskMap()
    avail = [a.name for a in m.areas if a.status == "AVAILABLE"]
    assert avail == ["Sieve Gate"]  # only the start is open
    assert all(a.status == "LOCKED" for a in m.areas if a.unlock_after is not None)


def test_route_names_the_right_tool_for_a_task():
    m = TaskMap()
    assert m.route("classify the number 91")["area"] == "Sieve Gate"
    assert m.route("make sure this code agrees in every language")["area"] == "Cross-Face Verify"
    assert m.route("remember my context")["area"] == "Context Ledger"
    assert m.route("how hard is this level")["area"] == "Leveling Track"


def test_guide_flags_a_locked_area():
    m = TaskMap()
    g = m.guide("remember my context")  # Context Ledger is locked at the start
    assert "Context Ledger" in g and "locked" in g


def test_traverse_clears_the_core_and_seals_progress():
    m = TaskMap()
    summary = m.traverse()
    assert summary["sealed"] is True
    assert summary["cleared"] >= 8  # pure-python areas always clear; toolchain ones may vary
    cleared = set(summary["cleared_areas"])
    assert _CORE <= cleared  # the reliable core all cleared
    assert summary["tool_calls"] >= 25  # every area drove its system through the sealed toolkit


def test_clearing_unlocks_the_next_area():
    m = TaskMap()
    assert m._area("Prime Region Map").status == "LOCKED"
    m.advance("Sieve Gate")
    assert m._area("Sieve Gate").status == "CLEARED"
    assert m._area("Prime Region Map").status == "AVAILABLE"  # unlocked by clearing its predecessor


def test_strategize_counts_and_recommends_a_move():
    m = TaskMap()
    s = m.strategize()
    assert isinstance(s["bitboards"], dict) and "high_value" in s["bitboards"]
    rec = s["recommended"]
    assert rec and rec["lane"] and rec["card"] and isinstance(rec["score"], float)
