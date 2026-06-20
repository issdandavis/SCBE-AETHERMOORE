"""Tests for the VTC pipeline pieces this session added/consolidated:
  * freeze_dataset -- corpus freezing, provenance, drift detection (GPU-free).
  * code_lift recovery -- solve-after-failure measurement via the repair loop (the VTC thesis number).

The lift here is exercised on a hand-built problem with controllable ask() callables, so no model or
network is needed. (Single-shot solve_rate / split logic is covered by tests/test_vtc_lift_harness.py.)
"""

from __future__ import annotations

import json

from python.helm.code_lift import measure_recovery_lift, recovery_lift, render, solve_rate_with_repair
from python.helm.freeze_dataset import dataset_stats, freeze, sha256_file, verify_freeze

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
    backups = list(backup_dir.glob("*.jsonl"))
    assert len(backups) == 1 and m["sha256"][:12] in backups[0].name
    assert sha256_file(backups[0]) == m["sha256"]

    assert verify_freeze(manifest_path)["ok"] is True
    with open(data, "a", encoding="utf-8") as f:
        f.write(json.dumps({"messages": [], "meta": {"verified": True, "task_id": 2}}) + "\n")
    assert verify_freeze(manifest_path)["ok"] is False


# ---- code_lift recovery (solve-after-failure via the repair loop) -------------------------------
def test_solve_rate_with_repair_counts_recovery():
    good = solve_rate_with_repair([PROBLEM], _correct_ask)
    assert good["solved"] == 1 and good["recovered"] == 0 and good["recovery_rate"] == 0.0

    bad = solve_rate_with_repair([PROBLEM], _wrong_ask)
    assert bad["solved"] == 0

    rec = solve_rate_with_repair([PROBLEM], _make_recovering_ask())
    assert rec["solved"] == 1 and rec["recovered"] == 1 and rec["recovery_rate"] == 1.0


def test_recovery_lift_reports_solve_and_recovery_delta():
    # base never recovers (0 solved), trained solves only after a repair -> both solve-lift and recovery-lift
    base = solve_rate_with_repair([PROBLEM], _wrong_ask)
    trained = solve_rate_with_repair([PROBLEM], _make_recovering_ask())
    rep = recovery_lift(base, trained)
    assert rep["net_lift"] == 1 and rep["newly_solved"] == {1}
    assert rep["recovery_lift"] == 1.0
    out = render(rep)
    assert "RECOVERY LIFT" in out and "NET LIFT" in out


def test_measure_recovery_lift_end_to_end_and_no_lift_case():
    rep = measure_recovery_lift(_wrong_ask, _correct_ask, [PROBLEM])
    assert rep["base_solved"] == 0 and rep["trained_solved"] == 1 and rep["net_lift"] == 1

    flat = measure_recovery_lift(_correct_ask, _correct_ask, [PROBLEM])
    assert flat["net_lift"] == 0 and flat["recovery_lift"] == 0.0  # honest: no lift reported as no lift
