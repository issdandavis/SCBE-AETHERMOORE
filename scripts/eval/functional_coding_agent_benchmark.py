#!/usr/bin/env python3
"""Functional benchmark for SCBE coding agents.

Generates TypeScript `evaluate(input, state)` functions from a local HF model
or LoRA adapter, runs each candidate through the TypeScript game-debug harness,
and scores executable behavior.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE_MODEL = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "coding_agent_benchmarks"


@dataclass(frozen=True)
class FunctionalTask:
    task_id: str
    prompt: str
    checks: list[dict[str, Any]]


TASKS = [
    FunctionalTask(
        task_id="score_add",
        prompt=(
            "Write TypeScript only. Define function evaluate(input, state). "
            "It must add input.points to state.score, mutate state.score, and return the new score."
        ),
        checks=[
            {"input": {"points": 5}, "initialState": {"score": 8}, "expectedResult": 13, "expectedState": {"score": 13}},
            {"input": {"points": -2}, "initialState": {"score": 10}, "expectedResult": 8, "expectedState": {"score": 8}},
        ],
    ),
    FunctionalTask(
        task_id="heal_clamp",
        prompt=(
            "Write TypeScript only. Define function evaluate(input, state). "
            "It must increase state.hp by input.heal, cap hp at state.maxHp, "
            "push 'healed' into state.events, and return state.hp."
        ),
        checks=[
            {
                "input": {"heal": 4},
                "initialState": {"hp": 6, "maxHp": 10, "events": []},
                "expectedResult": 10,
                "expectedState": {"hp": 10, "maxHp": 10, "events": ["healed"]},
            },
            {
                "input": {"heal": 2},
                "initialState": {"hp": 3, "maxHp": 10, "events": ["start"]},
                "expectedResult": 5,
                "expectedState": {"hp": 5, "maxHp": 10, "events": ["start", "healed"]},
            },
        ],
    ),
    FunctionalTask(
        task_id="inventory_unique",
        prompt=(
            "Write TypeScript only. Define function evaluate(input, state). "
            "If input.item is not already in state.inventory, append it. "
            "Return the inventory length."
        ),
        checks=[
            {
                "input": {"item": "key"},
                "initialState": {"inventory": ["coin"]},
                "expectedResult": 2,
                "expectedState": {"inventory": ["coin", "key"]},
            },
            {
                "input": {"item": "coin"},
                "initialState": {"inventory": ["coin"]},
                "expectedResult": 1,
                "expectedState": {"inventory": ["coin"]},
            },
        ],
    ),
    FunctionalTask(
        task_id="cooldown_gate",
        prompt=(
            "Write TypeScript only. Define function evaluate(input, state). "
            "If state.cooldown is greater than 0, decrement state.cooldown by 1 and return false. "
            "Otherwise set state.cooldown to input.cooldown, increment state.actions by 1, and return true."
        ),
        checks=[
            {
                "input": {"cooldown": 3},
                "initialState": {"cooldown": 0, "actions": 2},
                "expectedResult": True,
                "expectedState": {"cooldown": 3, "actions": 3},
            },
            {
                "input": {"cooldown": 3},
                "initialState": {"cooldown": 2, "actions": 2},
                "expectedResult": False,
                "expectedState": {"cooldown": 1, "actions": 2},
            },
        ],
    ),
    FunctionalTask(
        task_id="quest_flags",
        prompt=(
            "Write TypeScript only. Define function evaluate(input, state). "
            "If every string in input.required is present in state.flags, add input.reward to state.rewards if it is not already present, then return true. "
            "If any required flag is missing, do not change state.rewards and return false."
        ),
        checks=[
            {
                "input": {"required": ["gate", "key"], "reward": "amulet"},
                "initialState": {"flags": ["gate", "key"], "rewards": []},
                "expectedResult": True,
                "expectedState": {"flags": ["gate", "key"], "rewards": ["amulet"]},
            },
            {
                "input": {"required": ["gate", "key"], "reward": "amulet"},
                "initialState": {"flags": ["gate"], "rewards": ["coin"]},
                "expectedResult": False,
                "expectedState": {"flags": ["gate"], "rewards": ["coin"]},
            },
            {
                "input": {"required": ["gate"], "reward": "coin"},
                "initialState": {"flags": ["gate"], "rewards": ["coin"]},
                "expectedResult": True,
                "expectedState": {"flags": ["gate"], "rewards": ["coin"]},
            },
        ],
    ),
    FunctionalTask(
        task_id="weighted_choice",
        prompt=(
            "Write TypeScript only. Define function evaluate(input, state). "
            "input.options is an array of objects with id and weight. Return the id of the first option where the cumulative weight is greater than input.roll. "
            "If no option crosses the roll, return the final option id. Do not mutate state."
        ),
        checks=[
            {
                "input": {"roll": 0.2, "options": [{"id": "a", "weight": 0.5}, {"id": "b", "weight": 0.5}]},
                "initialState": {"seen": 1},
                "expectedResult": "a",
                "expectedState": {"seen": 1},
            },
            {
                "input": {"roll": 0.7, "options": [{"id": "a", "weight": 0.5}, {"id": "b", "weight": 0.5}]},
                "initialState": {"seen": 1},
                "expectedResult": "b",
                "expectedState": {"seen": 1},
            },
        ],
    ),
]


def load_task_file(path: Path) -> list[FunctionalTask]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_tasks = payload.get("tasks") if isinstance(payload, dict) else payload
    if not isinstance(raw_tasks, list):
        raise ValueError("task file must be a JSON list or an object with a 'tasks' list")
    tasks: list[FunctionalTask] = []
    for row in raw_tasks:
        tasks.append(
            FunctionalTask(
                task_id=str(row["task_id"]),
                prompt=str(row["prompt"]),
                checks=list(row["checks"]),
            )
        )
    return tasks


def selected_tasks(args: argparse.Namespace) -> list[FunctionalTask]:
    tasks = [] if args.replace_default_tasks else list(TASKS)
    for path in args.task_file or []:
        tasks.extend(load_task_file(path))
    return tasks[: args.task_limit] if args.task_limit else tasks


def safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.") or "model"


def extract_typescript(text: str) -> str:
    fence = re.search(r"```(?:typescript|ts|javascript|js)?\s*(.*?)```", text, flags=re.I | re.S)
    if fence:
        return fence.group(1).strip()
    idx = text.find("function evaluate")
    if idx >= 0:
        return text[idx:].strip()
    export_idx = text.find("export function evaluate")
    if export_idx >= 0:
        return text[export_idx:].strip()
    return text.strip()


def load_model(base_model: str, adapter: str, dtype_arg: str, use_4bit: bool):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    cuda_avail = torch.cuda.is_available()
    if dtype_arg == "auto":
        dtype = torch.bfloat16 if cuda_avail and torch.cuda.get_device_capability(0)[0] >= 8 else torch.float16
        if not cuda_avail:
            dtype = torch.float32
    else:
        dtype = {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": torch.float32}[dtype_arg]

    tokenizer = AutoTokenizer.from_pretrained(base_model, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    kwargs: dict[str, Any] = {"torch_dtype": dtype, "low_cpu_mem_usage": True}
    if cuda_avail:
        kwargs["device_map"] = "auto"
    if use_4bit and cuda_avail:
        try:
            from transformers import BitsAndBytesConfig

            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=dtype,
                bnb_4bit_use_double_quant=True,
            )
        except Exception as exc:
            print(f"WARN: 4-bit unavailable, falling back: {exc}", file=sys.stderr)

    model = AutoModelForCausalLM.from_pretrained(base_model, **kwargs)
    if adapter != "BASE":
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, adapter)
    model.eval()
    return tokenizer, model


def generate_code(tokenizer, model, prompt: str, max_new_tokens: int) -> str:
    import torch

    messages = [
        {
            "role": "system",
            "content": (
                "You are a coding agent. Return only TypeScript code. "
                "Do not use markdown. Define exactly function evaluate(input, state)."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(next(model.parameters()).device)
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    new_tokens = out[0][inputs["input_ids"].shape[-1] :]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def run_harness(source: str, check: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    scenario = {
        "id": scenario_id,
        "source": source,
        "input": check["input"],
        "initialState": check["initialState"],
        "timeoutMs": 250,
    }
    node = shutil.which("node")
    if not node:
        return {
            "status": "harness_error",
            "error": "node executable not found on PATH",
            "stdout": "",
        }
    proc = subprocess.run(
        [node, "scripts/run_typescript_debug_scenario.cjs", "--json", json.dumps(scenario)],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=8,
    )
    if proc.returncode != 0:
        return {
            "status": "harness_error",
            "error": proc.stderr.strip(),
            "stdout": proc.stdout.strip(),
        }
    return json.loads(proc.stdout)


def deep_equal(a: Any, b: Any) -> bool:
    return a == b


def score_candidate(source: str, task: FunctionalTask) -> dict[str, Any]:
    check_results = []
    for index, check in enumerate(task.checks):
        receipt = run_harness(source, check, f"{task.task_id}-{index}")
        passed = (
            receipt.get("status") == "passed"
            and deep_equal(receipt.get("result"), check["expectedResult"])
            and deep_equal(receipt.get("finalState"), check["expectedState"])
        )
        check_results.append(
            {
                "index": index,
                "passed": passed,
                "expected_result": check["expectedResult"],
                "actual_result": receipt.get("result"),
                "expected_state": check["expectedState"],
                "actual_state": receipt.get("finalState"),
                "receipt_status": receipt.get("status"),
                "error": receipt.get("error"),
            }
        )
    return {
        "task_id": task.task_id,
        "passed": all(row["passed"] for row in check_results),
        "checks": check_results,
    }


def run_model_benchmark(args: argparse.Namespace, adapter: str) -> dict[str, Any]:
    t0 = time.time()
    tokenizer, model = load_model(args.base_model, adapter, args.dtype, use_4bit=not args.no_4bit)
    tasks = selected_tasks(args)
    rows = []
    for task in tasks:
        raw = generate_code(tokenizer, model, task.prompt, args.max_new_tokens)
        code = extract_typescript(raw)
        score = score_candidate(code, task)
        rows.append(
            {
                "task_id": task.task_id,
                "prompt": task.prompt,
                "raw_generation": raw,
                "extracted_code": code,
                **score,
            }
        )
        print(f"  {adapter} {task.task_id}: {'PASS' if score['passed'] else 'FAIL'}")
    passed = sum(1 for row in rows if row["passed"])
    return {
        "adapter": adapter,
        "base_model": args.base_model,
        "elapsed_s": round(time.time() - t0, 1),
        "summary": {
            "tasks": len(rows),
            "passed": passed,
            "pass_rate": passed / len(rows) if rows else 0.0,
        },
        "tasks": rows,
    }


def load_candidate_file(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("candidates"), list):
        return payload["candidates"]
    raise ValueError("candidate file must be a JSON list or an object with a 'candidates' list")


def candidate_source_for_task(candidate: dict[str, Any], task: FunctionalTask) -> str | None:
    task_map = candidate.get("tasks")
    if isinstance(task_map, dict) and task.task_id in task_map:
        return str(task_map[task.task_id])
    if candidate.get("task_id") == task.task_id:
        return str(candidate.get("code") or candidate.get("source") or "")
    return None


def run_candidate_benchmark(args: argparse.Namespace, candidate: dict[str, Any]) -> dict[str, Any]:
    name = str(candidate.get("name") or candidate.get("model") or candidate.get("id") or "candidate")
    tasks = selected_tasks(args)
    rows = []
    for task in tasks:
        raw = candidate_source_for_task(candidate, task)
        if raw is None:
            rows.append(
                {
                    "task_id": task.task_id,
                    "prompt": task.prompt,
                    "raw_generation": "",
                    "extracted_code": "",
                    "passed": False,
                    "checks": [],
                    "error": "candidate did not provide code for this task",
                }
            )
            print(f"  {name} {task.task_id}: MISSING")
            continue
        code = extract_typescript(raw)
        score = score_candidate(code, task)
        rows.append(
            {
                "task_id": task.task_id,
                "prompt": task.prompt,
                "raw_generation": raw,
                "extracted_code": code,
                **score,
            }
        )
        print(f"  {name} {task.task_id}: {'PASS' if score['passed'] else 'FAIL'}")
    passed = sum(1 for row in rows if row["passed"])
    return {
        "adapter": name,
        "base_model": "candidate_file",
        "elapsed_s": 0,
        "summary": {
            "tasks": len(rows),
            "passed": passed,
            "pass_rate": passed / len(rows) if rows else 0.0,
        },
        "tasks": rows,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--models", nargs="+", default=["BASE"], help="Adapters to score; use BASE for base model.")
    p.add_argument("--candidate-file", type=Path, default=None, help="JSON file containing external-agent code candidates.")
    p.add_argument(
        "--task-file",
        type=Path,
        action="append",
        default=[],
        help="Additional executable task JSON file. May be repeated.",
    )
    p.add_argument("--replace-default-tasks", action="store_true", help="Use only tasks from --task-file.")
    p.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    p.add_argument("--task-limit", type=int, default=0)
    p.add_argument("--max-new-tokens", type=int, default=180)
    p.add_argument("--dtype", choices=["auto", "bf16", "fp16", "fp32"], default="auto")
    p.add_argument("--no-4bit", action="store_true")
    p.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.output_root / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    if args.candidate_file:
        for candidate in load_candidate_file(args.candidate_file):
            print(f"Benchmarking candidate {candidate.get('name') or candidate.get('model') or candidate.get('id')}")
            results.append(run_candidate_benchmark(args, candidate))
    else:
        for adapter in args.models:
            print(f"Benchmarking {adapter}")
            results.append(run_model_benchmark(args, adapter))

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark": "typescript_game_debug_functional_v1",
        "results": results,
    }
    report_path = out_dir / "report.json"
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    md_lines = [
        "# Functional Coding Agent Benchmark",
        "",
        "| Model | Tasks | Passed | Pass Rate |",
        "| --- | ---: | ---: | ---: |",
    ]
    for result in results:
        summary = result["summary"]
        md_lines.append(
            f"| `{result['adapter']}` | {summary['tasks']} | {summary['passed']} | {summary['pass_rate']:.2%} |"
        )
    for result in results:
        md_lines.extend(
            [
                "",
                f"## {result['adapter']}",
                "",
                "| Task | Status | First Failure |",
                "| --- | --- | --- |",
            ]
        )
        for task in result["tasks"]:
            status = "PASS" if task["passed"] else "FAIL"
            failure = ""
            if not task["passed"]:
                checks = task.get("checks") or []
                first_bad = next((check for check in checks if not check.get("passed")), None)
                if first_bad:
                    failure = (
                        f"check {first_bad.get('index')}: "
                        f"status={first_bad.get('receipt_status')}, "
                        f"error={json.dumps(first_bad.get('error'))}, "
                        f"expected_result={json.dumps(first_bad.get('expected_result'))}, "
                        f"actual_result={json.dumps(first_bad.get('actual_result'))}, "
                        f"expected_state={json.dumps(first_bad.get('expected_state'))}, "
                        f"actual_state={json.dumps(first_bad.get('actual_state'))}"
                    )
                else:
                    failure = str(task.get("error") or "missing failed-check details")
                failure = failure.replace("|", "\\|")
            md_lines.append(f"| `{task['task_id']}` | {status} | {failure} |")
    md_path = out_dir / "report.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    latest = args.output_root / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    (latest / "report.json").write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")
    (latest / "report.md").write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Report JSON: {report_path}")
    print(f"Report MD:   {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
