#!/usr/bin/env python3
"""Score ARC Rubix JSON attempts against visible solution files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(r"C:\Users\issda\kaggle\arc_agi2_2026")
DEFAULT_COMP = ROOT / "competition"


def main() -> None:
    ap = argparse.ArgumentParser(description="Score ARC submission attempts against a solution JSON.")
    ap.add_argument("--submission", default=str(ROOT / "eval_submission.json"))
    ap.add_argument("--solutions", default=str(DEFAULT_COMP / "arc-agi_evaluation_solutions.json"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    sub = json.loads(Path(args.submission).read_text(encoding="utf-8"))
    sol = json.loads(Path(args.solutions).read_text(encoding="utf-8"))
    total = 0
    correct = 0
    missing = []
    malformed = []
    wrong_examples = []
    for task_id, expected_list in sol.items():
        pred_list = sub.get(task_id)
        if pred_list is None:
            missing.append(task_id)
            total += len(expected_list)
            continue
        if len(pred_list) != len(expected_list):
            malformed.append(task_id)
        for i, expected in enumerate(expected_list):
            total += 1
            pred = pred_list[i] if i < len(pred_list) else {}
            hit = pred.get("attempt_1") == expected or pred.get("attempt_2") == expected
            if hit:
                correct += 1
            elif len(wrong_examples) < 10:
                wrong_examples.append({"task_id": task_id, "index": i})
    payload = {
        "ok": True,
        "correct": correct,
        "total": total,
        "score": correct / total if total else 0.0,
        "missing_tasks": missing[:20],
        "malformed_tasks": malformed[:20],
        "wrong_examples": wrong_examples,
    }
    print(json.dumps(payload, indent=2) if args.json else f"ARC score {correct}/{total} = {payload['score']:.6f}")


if __name__ == "__main__":
    main()
