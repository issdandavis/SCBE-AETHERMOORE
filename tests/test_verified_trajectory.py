"""verified_trajectory: rejection-sampling SFT engine -- keep only execution-verified trajectories."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm import verified_trajectory as vt  # noqa: E402
from python.helm.curriculum import CURRICULUM  # noqa: E402

PROBS = [p for tier in CURRICULUM for p in tier["problems"]]


def test_reference_solutions_all_verify_and_are_harvested():
    r = vt.harvest(PROBS, vt.reference_generator)
    assert r["verified"] == r["attempted"] == len(PROBS)  # every reference solution passes hidden tests
    assert r["verified_rate"] == 1.0


def test_naive_floor_harvests_nothing():
    r = vt.harvest(PROBS, vt.naive_generator)
    assert r["verified"] == 0  # a failing stub is never harvested -- no unverified data leaks in


def test_records_are_well_formed_sft_marked_verified():
    r = vt.harvest(PROBS, vt.reference_generator)
    rec = r["records"][0]
    assert [m["role"] for m in rec["messages"]] == ["system", "user", "assistant"]
    assert rec["meta"]["verified"] is True and rec["meta"]["task_id"]


def test_write_dataset_emits_jsonl_and_manifest(tmp_path):
    r = vt.harvest(PROBS, vt.reference_generator)
    out = tmp_path / "vtc.jsonl"
    m = vt.write_dataset(r, str(out))
    assert out.exists() and out.with_suffix(".manifest.json").exists()
    assert m["verified"] == len(r["records"]) and m["verified_rate"] == 1.0


def test_solve_with_trace_records_the_repair_loop():
    # wrong first, correct after feedback -> the trace captures the loop and verifies
    calls = []

    def ask(prompt):
        calls.append(prompt)
        return "def add(a, b):\n    return a - b" if len(calls) == 1 else "def add(a, b):\n    return a + b"

    prob = {"prompt": "add a and b", "test_list": ["assert add(1,2)==3", "assert add(2,2)==4"], "test_imports": []}
    tr = vt.solve_with_trace(prob, ask, public_k=1, rounds=3)
    assert tr["verified"] is True and tr["attempts"] >= 2  # repaired, then passed hidden
    roles = [t["role"] for t in tr["turns"]]
    assert roles[0] == "user" and roles[1] == "assistant" and "user" in roles[2:]  # loop captured


def test_harvest_traces_keeps_only_verified_multiturn():
    def good(prompt):
        return "def add(a, b):\n    return a + b"

    prob = {"prompt": "add a and b", "test_list": ["assert add(1,2)==3", "assert add(2,2)==4"], "test_imports": []}
    r = vt.harvest_traces([prob], good)
    assert r["verified"] == 1
    rec = r["records"][0]
    assert rec["messages"][0]["role"] == "system" and rec["meta"]["verified"] is True


def test_refine_dedups_prefers_repair_and_tags_station_manager():
    def rec(task, repaired, final="def f():\n    return 1"):
        return {
            "messages": [{"role": "user", "content": "p"}, {"role": "assistant", "content": final}],
            "meta": {"task_id": task, "repaired": repaired, "attempts": 2 if repaired else 1, "verified": True},
        }

    recs = [rec("A", False), rec("A", True), rec("B", False), rec("C", False, "x")]  # C is degenerate
    out = vt.refine(recs)
    assert out["total"] == 2  # A deduped (repair kept) + B; C dropped as degenerate
    grades = {r["meta"]["task_id"]: r["meta"]["grade"] for r in out["records"]}
    assert grades["A"] == "manager" and grades["B"] == "station"
    assert out["manager"] == 1 and out["station"] == 1 and out["deduped_from"] == 4
