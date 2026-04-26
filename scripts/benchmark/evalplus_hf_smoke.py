"""Run an official EvalPlus HumanEval+ mini smoke on Hugging Face Jobs.

This intentionally evaluates canonical HumanEval+ solutions, not the SCBE model.
It proves the leaderboard software and execution lane are healthy before spending
GPU time on adapter inference.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from evalplus.data import get_human_eval_plus
from evalplus.data.utils import write_jsonl
from evalplus.evaluate import evaluate


def main() -> None:
    # HF Jobs containers can reject EvalPlus' default setrlimit memory raise.
    # This keeps EvalPlus' destructive-call guard while disabling that limit.
    os.environ.setdefault("EVALPLUS_MAX_MEMORY_BYTES", "-1")
    workdir = Path(os.environ.get("SCBE_EVALPLUS_WORKDIR", "/tmp/scbe-evalplus-smoke"))
    workdir.mkdir(parents=True, exist_ok=True)
    samples_path = workdir / "humaneval_plus_mini_canonical.jsonl"
    results_path = workdir / "humaneval_plus_mini_canonical.eval_results.json"

    problems = get_human_eval_plus(mini=True)
    samples = [
        {
            "task_id": task_id,
            "solution": problem["prompt"] + problem["canonical_solution"],
        }
        for task_id, problem in sorted(problems.items())
    ]
    write_jsonl(str(samples_path), samples, drop_builtin=False)
    if results_path.exists():
        results_path.unlink()

    evaluate(
        dataset="humaneval",
        samples=str(samples_path),
        parallel=2,
        mini=True,
        i_just_wanna_run=False,
    )

    if not results_path.exists():
        matches = sorted(workdir.glob("*.eval_results.json")) + sorted(workdir.glob("*_eval_results.json"))
        if not matches:
            raise FileNotFoundError(f"No EvalPlus result JSON found in {workdir}")
        results_path = matches[0]

    with results_path.open("r", encoding="utf-8") as handle:
        results = json.load(handle)
    summary = {
        "event": "evalplus_hf_smoke_complete",
        "dataset": "humaneval_plus_mini",
        "sample_count": len(samples),
        "results_path": str(results_path),
        "pass_at_k": results.get("pass_at_k", {}),
    }
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
