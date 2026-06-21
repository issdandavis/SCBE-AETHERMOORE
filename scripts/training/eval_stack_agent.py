"""Validate a stack-agent SFT corpus.

This gate checks the data shape and re-runs execution verification for repair
records. It is deliberately separate from training loss: a corpus can train
cleanly and still be useless if its repair claims are not verified.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.helm import public_bench


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError("invalid json on line %d: %s" % (i, exc)) from exc
    return rows


def _passes(source: str, tests: Sequence[str]) -> bool:
    return bool(public_bench._verify(source, [], tests, [])["hidden_passed"])


def _messages_have_tool_turn(messages: Iterable[Dict[str, Any]]) -> bool:
    return any(str(m.get("content", "")).startswith("TOOL ") for m in messages if m.get("role") == "user")


def _final_has_receipt(messages: Sequence[Dict[str, Any]]) -> bool:
    if not messages:
        return False
    return "RECEIPT:" in str(messages[-1].get("content", ""))


def evaluate(records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    failures: List[Dict[str, Any]] = []
    categories: Dict[str, int] = {}
    task_ids: List[str] = []
    reverified = 0
    teacher_bailout = 0
    self_repair = 0

    for idx, rec in enumerate(records):
        meta = rec.get("meta", {})
        messages = rec.get("messages", [])
        task_id = str(meta.get("task_id", ""))
        category = str(meta.get("category", "unknown"))
        categories[category] = categories.get(category, 0) + 1
        task_ids.append(task_id)

        if not task_id:
            failures.append({"index": idx, "reason": "missing task_id"})
        if not isinstance(messages, list) or len(messages) < 3:
            failures.append({"task_id": task_id, "reason": "too few messages"})
            continue
        if not _messages_have_tool_turn(messages):
            failures.append({"task_id": task_id, "reason": "missing TOOL feedback turn"})
        if not _final_has_receipt(messages):
            failures.append({"task_id": task_id, "reason": "missing final receipt"})
        if meta.get("verified") is not True:
            failures.append({"task_id": task_id, "reason": "meta.verified is not true"})

        if category == "pitfall_repair":
            tests = meta.get("tests", [])
            buggy = meta.get("buggy", "")
            fix = meta.get("fix", "")
            if not tests or not buggy or not fix:
                failures.append({"task_id": task_id, "reason": "pitfall record missing tests/buggy/fix"})
            else:
                buggy_passes = _passes(str(buggy), tests)
                fix_passes = _passes(str(fix), tests)
                if buggy_passes or not fix_passes:
                    failures.append(
                        {
                            "task_id": task_id,
                            "reason": "execution reverify failed",
                            "buggy_passes": buggy_passes,
                            "fix_passes": fix_passes,
                        }
                    )
                else:
                    reverified += 1
            if "TOOL run_code: FAIL" in json.dumps(messages):
                self_repair += 1
            else:
                teacher_bailout += 1

    duplicate_ids = sorted({tid for tid in task_ids if tid and task_ids.count(tid) > 1})
    for tid in duplicate_ids:
        failures.append({"task_id": tid, "reason": "duplicate task_id"})

    total = len(records)
    report = {
        "schema": "scbe.stack_agent_eval.v1",
        "total_records": total,
        "categories": categories,
        "verified_records": sum(1 for r in records if r.get("meta", {}).get("verified") is True),
        "reverified_repair_records": reverified,
        "duplicate_task_ids": duplicate_ids,
        "tool_feedback_records": sum(1 for r in records if _messages_have_tool_turn(r.get("messages", []))),
        "receipt_records": sum(1 for r in records if _final_has_receipt(r.get("messages", []))),
        "self_repair_records": self_repair,
        "teacher_bailout_records": teacher_bailout,
        "failures": failures,
        "pass": not failures and total > 0,
    }
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Validate the SCBE stack-agent SFT corpus")
    ap.add_argument("--corpus", default="training/sft_records/stack_agent_seed.jsonl")
    ap.add_argument("--out", default="training/evals/stack_agent_eval_report.json")
    args = ap.parse_args(list(argv) if argv is not None else None)

    corpus = Path(args.corpus)
    out = Path(args.out)
    records = _load_jsonl(corpus)
    report = evaluate(records)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(
        "STACK_AGENT_EVAL pass=%s records=%d reverified=%d failures=%d out=%s"
        % (report["pass"], report["total_records"], report["reverified_repair_records"], len(report["failures"]), out)
    )
    if report["failures"]:
        print(json.dumps(report["failures"][:5], indent=2, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
