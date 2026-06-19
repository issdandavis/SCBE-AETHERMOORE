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


def test_run_diagnoses_a_failure_and_keeps_the_chain():
    m = TaskMap()
    out = m.run("run_level", [])  # guarded, no confirm
    assert out["decision"] == "NEEDS_CONFIRM"
    assert out["diagnosis"]["cause"] == "needs_confirm" and out["diagnosis"]["retry_safe"] is False
    assert out["chain_ok"] is True  # chain verification still passes after the sealed diagnosis


def test_run_allowed_call_has_no_diagnosis():
    m = TaskMap()
    out = m.run("is_prime", 7)
    assert out["decision"] == "ALLOWED" and "diagnosis" not in out and out["chain_ok"] is True


def test_confirmation_required_failure_is_not_auto_retried():
    m = TaskMap()
    m.run("run_level", [])  # must NOT silently retry with a confirm
    allowed_runs = [r for r in m.tk.transcript if r.get("tool") == "run_level" and r.get("decision") == "ALLOWED"]
    assert allowed_runs == []  # no auto-retry happened


def test_diagnose_drift_localizes_the_wall_via_failure_map():
    from python.scbe.sieve_calc import classify_number_task
    from python.scbe.stepwise import scripted_proposer

    m = TaskMap()
    # 91 is composite; a model that always says 'prime' drifts at the label step
    drift = m.diagnose_drift(classify_number_task(91), scripted_proposer(["prime", "prime", "prime", "prime"]))
    assert drift["cleared"] is False
    assert drift["drift"]["stuck_at"] == "label"  # failure_map localizes the wall step
    assert "offload" in drift["recovery"] and "sieve_calc" in drift["recovery"]


def test_run_with_drifted_stepwise_diagnoses_and_localizes_live():
    from python.scbe.sieve_calc import classify_number_task
    from python.scbe.stepwise import scripted_proposer

    m = TaskMap()
    out = m.run("run_stepwise", classify_number_task(91), scripted_proposer(["prime", "prime", "prime", "prime"]))
    assert out["decision"] == "ALLOWED"  # the tool call itself succeeded; the RESULT drifted
    assert out["diagnosis"]["cause"] == "step_drift" and out["diagnosis"]["retry_safe"] is False
    assert out["chain_ok"] is True
    # the LIVE run() path actually ran failure_map.localize -> the wall step
    assert out["drift"]["drift"]["stuck_at"] == "label" and "offload" in out["drift"]["recovery"]
