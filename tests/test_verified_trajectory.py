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
