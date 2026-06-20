"""Verify the gate-effectiveness benchmark: every bad patch blocked, every good one preserved."""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_BENCH = REPO_ROOT / "scripts" / "benchmark" / "gate_effectiveness_benchmark.py"

_spec = importlib.util.spec_from_file_location("gate_effectiveness_benchmark", _BENCH)
gate_bench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate_bench)


def test_no_bad_patch_is_promoted():
    report = gate_bench.run()
    assert report["leaks"] == []  # no bad proposal slipped through the gate
    assert report["gated"]["bad_reaching_tree"] == 0


def test_every_good_patch_is_preserved():
    report = gate_bench.run()
    assert report["false_blocks"] == []  # the gate did not wrongly block a good proposal
    assert report["gated"]["good_preserved"] == report["totals"]["good"]


def test_gate_changes_the_outcome():
    # the whole point: bad patches reach the tree without the gate, none with it
    report = gate_bench.run()
    assert report["no_gate"]["bad_reaching_tree"] == report["totals"]["bad"] > 0
    assert report["gated"]["bad_reaching_tree"] == 0


def test_each_bad_case_individually_blocked():
    report = gate_bench.run()
    for row in report["rows"]:
        if row["label"] == "bad":
            assert row["promoted"] is False, f"{row['name']} should be blocked but was promoted"
            assert row["flags"], f"{row['name']} should raise at least one quality flag"
