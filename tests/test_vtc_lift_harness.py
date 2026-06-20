"""vtc lift harness: the honest train/held-out split + the base-vs-trained code-lift math, tested
HERMETICALLY -- offline, no GPU, no network, no real model. These tests lock the two things that must
be true before any Colab time is spent: (1) train and eval task_ids are provably DISJOINT, and (2) the
lift number counts only REAL (execution-verified) solves and can never manufacture a lift that is not
there. The actual capability run (a QLoRA fine-tune + base-vs-trained eval) lives in the Colab notebook.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm import public_bench as pb  # noqa: E402
from python.helm.code_lift import lift_from_solve, measure_code_lift, solve_rate  # noqa: E402
from python.helm.vtc_split import _task_ids, load_corpus, split_by_task_id, write_train_sft  # noqa: E402

FIXTURE = ROOT / "python" / "helm" / "vtc_fixture.jsonl"


# --- the split: honest, disjoint, reproducible ---------------------------------


def test_load_corpus_roundtrips_the_fixture():
    recs = load_corpus(str(FIXTURE))
    assert len(recs) == 4
    assert all("messages" in r and "meta" in r for r in recs)
    assert _task_ids(recs) == {2, 11, 100, 200}


def test_split_excludes_training_ids_and_is_disjoint():
    recs = load_corpus(str(FIXTURE))
    split = split_by_task_id(recs, pb.load_fixture(), public_k=1)
    # the corpus covers task 2 (also in the MBPP sample) -> task 2 MUST be excluded from eval
    assert split["train_ids"] == {2, 11, 100, 200}
    assert split["eval_ids"] == {6, 8}  # mbpp sample {2,6,8} minus the training ids
    assert not (split["train_ids"] & split["eval_ids"])  # provably disjoint
    assert all(len(p["test_list"]) > 1 for p in split["eval_problems"])  # every eval problem has a hidden test


def test_split_drops_records_without_a_task_id():
    recs = load_corpus(str(FIXTURE)) + [{"messages": [{"role": "user", "content": "x"}], "meta": {}}]
    split = split_by_task_id(recs, pb.load_fixture(), public_k=1)
    assert split["dropped_no_task_id"] == 1  # the id-less record cannot be split honestly


# --- the lift: counts only real solves, cannot fake a lift ---------------------


def test_solve_rate_runs_hidden_tests():
    probs = [p for p in pb.load_fixture() if p["task_id"] in (6, 8)]
    assert solve_rate(probs, pb.reference_generator)["solved"] == 2  # answer key passes hidden tests
    assert solve_rate(probs, pb.naive_generator)["solved"] == 0  # the stub fails


def test_measure_code_lift_counts_only_real_solves():
    eval_problems = [p for p in pb.load_fixture() if p["task_id"] in (6, 8)]
    rep = measure_code_lift(pb.naive_generator, pb.reference_generator, eval_problems)
    assert rep["base_solved"] == 0 and rep["trained_solved"] == 2
    assert rep["newly_solved"] == {6, 8}  # trained passes hidden tests the base could not
    assert rep["regressed"] == set()
    assert rep["net_lift"] == 2


def test_harness_cannot_manufacture_lift():
    probs = [p for p in pb.load_fixture() if p["task_id"] in (6, 8)]
    # identical generator on both sides -> ZERO lift (the honesty guard)
    same = measure_code_lift(pb.reference_generator, pb.reference_generator, probs)
    assert same["newly_solved"] == set() and same["regressed"] == set() and same["net_lift"] == 0
    # both failing -> also zero, and zero solved
    nada = measure_code_lift(pb.naive_generator, pb.naive_generator, probs)
    assert nada["base_solved"] == 0 and nada["trained_solved"] == 0 and nada["net_lift"] == 0


def test_lift_from_solve_matches_the_adapter_toggle_path():
    # the Colab path computes solve_rate twice (LoRA off vs on) then builds the report; same result
    probs = [p for p in pb.load_fixture() if p["task_id"] in (6, 8)]
    base = solve_rate(probs, pb.naive_generator)
    trained = solve_rate(probs, pb.reference_generator)
    rep = lift_from_solve(base, trained)
    assert rep == measure_code_lift(pb.naive_generator, pb.reference_generator, probs)
    assert rep["newly_solved"] == {6, 8} and rep["net_lift"] == 2


def test_regression_is_surfaced_not_hidden():
    probs = [p for p in pb.load_fixture() if p["task_id"] in (6, 8)]
    # base solves (answer key), trained breaks (stub) -> net lift is NEGATIVE and regressed is shown
    rep = measure_code_lift(pb.reference_generator, pb.naive_generator, probs)
    assert rep["regressed"] == {6, 8} and rep["newly_solved"] == set()
    assert rep["net_lift"] == -2  # the harness never headlines only the positive


# --- the SFT passthrough: messages format the notebook ingests -----------------


def test_write_train_sft_emits_messages_jsonl(tmp_path):
    recs = load_corpus(str(FIXTURE))
    out = tmp_path / "train.sft.jsonl"
    res = write_train_sft(recs, str(out))
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert res["written"] == len(lines) == 4
    for ln in lines:
        obj = json.loads(ln)
        assert obj["messages"][0]["role"] == "system"  # the chat format apply_chat_template ingests
    # a manager trace stays multi-turn (the repair loop is preserved, not flattened)
    mgr = next(json.loads(ln) for ln in lines if json.loads(ln)["meta"].get("grade") == "manager")
    assert len(mgr["messages"]) == 5 and [m["role"] for m in mgr["messages"]].count("assistant") == 2
