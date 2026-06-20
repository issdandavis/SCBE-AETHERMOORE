"""Tests for the VTC train/measure pipeline: freeze_dataset + vtc_lift.

These cover the pure, GPU-free logic: dataset freezing/provenance/drift-detection, and the lift
measurement on a hand-built problem with controllable ask() callables (no model needed).
"""

from __future__ import annotations

import json

from python.helm.freeze_dataset import dataset_stats, freeze, sha256_file, verify_freeze
from python.helm.vtc_lift import corpus_task_ids, evaluate, held_out, measure_vtc_lift, render

# ---- a tiny self-contained problem (no model, no network) --------------------------------------
PROBLEM = {
    "task_id": 1,
    "text": "Write a function add(a, b) returning their sum.",
    "test_list": ["assert add(1, 2) == 3", "assert add(0, 0) == 0", "assert add(-1, 1) == 0"],
    "test_imports": [],
}
CORRECT = "def add(a, b):\n    return a + b\n"
WRONG = "def add(a, b):\n    return 99\n"


def _correct_ask(_prompt: str) -> str:
    return CORRECT


def _wrong_ask(_prompt: str) -> str:
    return WRONG


def _make_recovering_ask():
    """Wrong on the first attempt, correct on the second -> a genuine recovery (attempts > 1)."""
    state = {"calls": 0}

    def ask(_prompt: str) -> str:
        state["calls"] += 1
        return WRONG if state["calls"] == 1 else CORRECT

    return ask


# ---- freeze_dataset ----------------------------------------------------------------------------
def _write_corpus(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def test_dataset_stats_grades_and_models():
    rows = [
        {"messages": [], "meta": {"verified": True, "task_id": 5, "grade": "station", "model": "a"}},
        {"messages": [], "meta": {"verified": True, "task_id": 9, "grade": "manager", "repaired": True, "model": "b"}},
    ]
    s = dataset_stats(rows)
    assert s["records"] == 2
    assert s["station"] == 1 and s["manager"] == 1 and s["repaired"] == 1
    assert s["per_model"] == {"a": 1, "b": 1}
    assert s["task_id_min"] == 5 and s["task_id_max"] == 9


def test_freeze_writes_manifest_backup_and_detects_drift(tmp_path):
    data = tmp_path / "corpus.jsonl"
    rows = [{"messages": [], "meta": {"verified": True, "task_id": 1, "grade": "station"}}]
    _write_corpus(data, rows)

    manifest_path = tmp_path / "corpus.freeze.json"
    backup_dir = tmp_path / "frozen"
    m = freeze(data, out_path=manifest_path, backup_dir=backup_dir, now="2026-06-20T00:00:00Z")

    assert m["sha256"] == sha256_file(data)
    assert m["records"] == 1 and m["frozen_at"] == "2026-06-20T00:00:00Z"
    assert manifest_path.exists()
    # backup is hash-named and is a byte copy
    backups = list(backup_dir.glob("*.jsonl"))
    assert len(backups) == 1 and m["sha256"][:12] in backups[0].name
    assert sha256_file(backups[0]) == m["sha256"]

    # drift detection: clean match, then mutate the dataset
    assert verify_freeze(manifest_path)["ok"] is True
    with open(data, "a", encoding="utf-8") as f:
        f.write(json.dumps({"messages": [], "meta": {"verified": True, "task_id": 2}}) + "\n")
    assert verify_freeze(manifest_path)["ok"] is False


# ---- vtc_lift ----------------------------------------------------------------------------------
def test_corpus_task_ids_and_held_out(tmp_path):
    data = tmp_path / "c.jsonl"
    _write_corpus(data, [{"meta": {"task_id": 1}}, {"meta": {"task_id": 3}}])
    ids = corpus_task_ids(data)
    assert ids == {1, 3}
    pool = [{"task_id": 1}, {"task_id": 2}, {"task_id": 3}, {"task_id": 4}]
    assert [p["task_id"] for p in held_out(pool, ids)] == [2, 4]


def test_evaluate_solves_and_counts_recovery():
    good = evaluate(_correct_ask, [PROBLEM])
    assert good["solved"] == 1 and good["first_try"] == 1 and good["recovered"] == 0

    bad = evaluate(_wrong_ask, [PROBLEM])
    assert bad["solved"] == 0 and bad["failure_classes"]  # something bucketed

    rec = evaluate(_make_recovering_ask(), [PROBLEM])
    assert rec["solved"] == 1 and rec["recovered"] == 1 and rec["recovery_rate"] == 1.0


def test_measure_vtc_lift_reports_gain_and_recovery():
    report = measure_vtc_lift(_wrong_ask, _correct_ask, [PROBLEM])
    assert report["base_solved"] == 0 and report["trained_solved"] == 1
    assert report["solved_lift"] == 1 and report["gained"] == [1] and report["regressed"] == []
    assert "PROVEN" in render(report)

    # recovery lift: base never recovers, trained solves only after a repair
    rep2 = measure_vtc_lift(_wrong_ask, _make_recovering_ask(), [PROBLEM])
    assert rep2["recovery_lift"] == 1.0

    # no-lift case is reported honestly
    flat = measure_vtc_lift(_correct_ask, _correct_ask, [PROBLEM])
    assert flat["solved_lift"] == 0 and "NO LIFT" in render(flat)
