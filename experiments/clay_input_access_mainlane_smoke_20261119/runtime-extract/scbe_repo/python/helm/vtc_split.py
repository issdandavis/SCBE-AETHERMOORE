"""vtc_split: the honest train / held-out partition for the VTC capability-lift harness.

verified_trajectory.py HARVESTS execution-verified SFT trajectories from MBPP problems; this module
SPLITS them for a base-vs-trained lift measurement. The rule is deliberately simple and provably
honest: a model is trained on the corpus's task_ids, and evaluated ONLY on MBPP problems whose
task_id is NOT in that training set. Disjointness is asserted, so any train/eval leak fails loudly
instead of inflating a fake "lift". Within each eval problem, public_bench still holds its hidden
asserts out -- so the split is two-level: cross-problem (train vs eval) AND per-problem (public vs
hidden).

HONEST LIMIT: this guarantees id-disjointness, not content-disjointness. If the same spec recurs
under a different task_id, the split is honest by id yet leaky by content -- and MBPP is on GitHub, so
a "solve" can be memorization. Treat newly_solved as an upper bound on novel capability, not proof.

    SCBE_VTC_CORPUS=path/to/vtc.jsonl python -m python.helm.vtc_split --out train.sft.jsonl --limit 200
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import public_bench as pb


def load_corpus(path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Read a VTC JSONL corpus. Path comes from the arg or $SCBE_VTC_CORPUS -- never hardcoded to a
    specific checkout, so this runs anywhere the file is mounted (a Colab upload, the other repo, ...)."""
    path = path or os.environ.get("SCBE_VTC_CORPUS")
    if not path:
        raise ValueError("no corpus path: pass --corpus or set SCBE_VTC_CORPUS")
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError("VTC corpus not found: %s" % p)
    out: List[Dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _task_ids(records: Sequence[Dict[str, Any]]) -> set:
    ids = set()
    for r in records:
        tid = (r.get("meta") or {}).get("task_id")
        if tid is not None:
            ids.add(tid)
    return ids


def split_by_task_id(
    records: Sequence[Dict[str, Any]],
    mbpp_problems: Sequence[Dict[str, Any]],
    public_k: int = 1,
) -> Dict[str, Any]:
    """Train = the corpus records carrying a task_id; eval = MBPP problems whose task_id is NOT a
    training id AND that have MORE than public_k tests (so at least one HIDDEN test exists -- a
    1-test problem at public_k=1 has an empty hidden set, making 'solved' trivially true). Disjointness
    of train vs eval task_ids is asserted."""
    train_ids = _task_ids(records)
    train_records = [r for r in records if (r.get("meta") or {}).get("task_id") in train_ids]
    eval_problems = [
        p for p in mbpp_problems if p.get("task_id") not in train_ids and len(p.get("test_list", [])) > public_k
    ]
    eval_ids = {p.get("task_id") for p in eval_problems}
    leak = train_ids & eval_ids
    if leak:  # cannot happen given the filter above -- a loud guard against a future refactor breaking it
        raise AssertionError("train/eval leakage on task_ids: %s" % sorted(leak))
    return {
        "train_records": train_records,
        "train_ids": train_ids,
        "eval_problems": eval_problems,
        "eval_ids": eval_ids,
        "dropped_no_task_id": len(records) - len(train_records),
    }


def write_train_sft(records: Sequence[Dict[str, Any]], out_path: str) -> Dict[str, Any]:
    """Write the train split as {messages, meta} JSONL -- already the format the qwen QLoRA notebook's
    convert()/apply_chat_template ingests. Records pass through verbatim (station AND manager traces),
    so a multi-turn repair trace is preserved as a multi-turn conversation, never flattened to one turn."""
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with p.open("w", encoding="utf-8") as f:
        for r in records:
            if not r.get("messages"):
                continue
            f.write(json.dumps({"messages": r["messages"], "meta": r.get("meta", {})}, ensure_ascii=False) + "\n")
            n += 1
    return {"path": str(p), "written": n}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scbe-vtc-split", description="honest train/held-out split for the VTC lift harness"
    )
    ap.add_argument("--corpus", default=None, help="VTC JSONL path (or set $SCBE_VTC_CORPUS)")
    ap.add_argument("--out", default="train.sft.jsonl", help="where to write the train SFT JSONL")
    ap.add_argument(
        "--limit", type=int, default=None, help="MBPP problems to pull for the eval pool (0/None = all 427)"
    )
    ap.add_argument("--public-k", type=int, default=1)
    ap.add_argument("--fixture", action="store_true", help="use the offline 3-problem MBPP sample instead of pulling")
    ap.add_argument("--eval-out", default=None, help="optional: also write the held-out eval problems to this JSON")
    a = ap.parse_args(list(argv) if argv is not None else None)
    records = load_corpus(a.corpus)
    problems = pb.load_fixture() if a.fixture else pb.pull_mbpp(limit=a.limit or None)
    split = split_by_task_id(records, problems, public_k=a.public_k)
    w = write_train_sft(split["train_records"], a.out)
    print(
        "VTC SPLIT  train_records=%d  train_ids=%d  eval_problems=%d  (train/eval task_ids disjoint: OK)"
        % (len(split["train_records"]), len(split["train_ids"]), len(split["eval_problems"]))
    )
    print("  wrote %d train SFT records -> %s" % (w["written"], w["path"]))
    if split["dropped_no_task_id"]:
        print("  dropped %d records with no meta.task_id (cannot be split honestly)" % split["dropped_no_task_id"])
    if a.eval_out:
        Path(a.eval_out).write_text(json.dumps(split["eval_problems"], indent=2), encoding="utf-8")
        print("  wrote %d held-out eval problems -> %s" % (len(split["eval_problems"]), a.eval_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
