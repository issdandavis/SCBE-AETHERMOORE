#!/usr/bin/env python3
"""AetherDesk mechanical coding benchmark.

Benchmarks the SCBE-AETHERMOORE mechanical coding mechanism (zero-LLM
opcode->source compilation via scripts/agents/scbe_code.py) against
real local LLM baselines and a cost-estimate baseline for hosted
provider APIs.

For each task we measure:
  - wall_ms                    wall-clock latency of generating the function
  - input_tokens               prompt tokens (LLM arms only)
  - output_tokens              generated tokens (LLM arms only)
  - estimated_cost_usd         what a Sonnet-class API call would have cost
  - correctness                does the generated function pass the test cases
  - receipt_path               GeoSeal receipt written for every op

Comparator arms:
  - mechanical                 scbe_code compile-ca (zero compute)
  - ollama_qwen_coder_05b      qwen2.5-coder:0.5b via local Ollama
  - ollama_qwen_coder_15b      qwen2.5-coder:1.5b via local Ollama
  - cost_estimate_sonnet       Sonnet-class API call, priced from tokens

The output is a single aetherdesk_bench_report_v0 JSON artifact plus a
short stdout summary suitable for the AetherDesk receipt pane.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
RECEIPTS_DIR = ARTIFACTS_DIR / "aetherdesk_receipts"
REPORT_DIR = ARTIFACTS_DIR / "aetherdesk_bench"

# Published rates as of 2026-05 (USD / million tokens). These are the
# rates a hosted Sonnet-class call would pay; using them keeps the
# cost estimate honest and reproducible.
SONNET_INPUT_USD_PER_MTOK = 3.0
SONNET_OUTPUT_USD_PER_MTOK = 15.0

OLLAMA_BASE = "http://127.0.0.1:11434"


# ---------------------------------------------------------------------------
# Task definitions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Task:
    """One benchmarkable coding task.

    The mechanical arm is fully specified by (opcodes, args, target).
    The LLM arms get a natural-language prompt with the same intent.
    The verifier is what makes the comparison fair: every generated
    function (mechanical OR LLM) is exec'd and called against test
    inputs that must all return the expected output.
    """

    id: str
    description: str
    opcodes: str  # e.g. "0x09 0x09 0x00"
    args: str  # e.g. "a,b"
    target: str  # "python" | "typescript" | "go"
    fn_name: str
    llm_prompt: str
    test_cases: Tuple[Tuple[Tuple[Any, ...], Any], ...]  # ((args, expected), ...)


TASKS: Tuple[Task, ...] = (
    Task(
        id="abs_add_py",
        description="abs(a)+abs(b) in Python (swap-aware)",
        # 0x40 swap, 0x09 abs, 0x40 swap, 0x09 abs, 0x00 add
        opcodes="0x40 0x09 0x40 0x09 0x00",
        args="a,b",
        target="python",
        fn_name="abs_add",
        llm_prompt=(
            "Write a Python function named abs_add(a, b) that returns abs(a) + abs(b). "
            "Reply with ONLY the function source, no commentary, no markdown fences."
        ),
        test_cases=(
            ((3, -4), 7),
            ((-5, 2), 7),
            ((0, 0), 0),
            ((-10, -10), 20),
        ),
    ),
    Task(
        id="abs_add_py2",
        description="abs(a)+abs(b) in Python (variance run, swap-aware)",
        opcodes="0x40 0x09 0x40 0x09 0x00",
        args="a,b",
        target="python",
        fn_name="abs_add",
        llm_prompt=(
            "Define a Python function abs_add(a, b) that computes the sum of the absolute "
            "values of a and b. Output the function definition only."
        ),
        test_cases=(
            ((7, -3), 10),
            ((-1, -1), 2),
            ((100, 0), 100),
        ),
    ),
    Task(
        id="add_py",
        description="a+b in Python",
        opcodes="0x00",
        args="a,b",
        target="python",
        fn_name="add",
        llm_prompt=("Write a Python function named add(a, b) that returns a + b. " "Output only the function source."),
        test_cases=(
            ((1, 2), 3),
            ((-5, 5), 0),
            ((10, 20), 30),
        ),
    ),
    Task(
        id="sub_py",
        description="a-b in Python",
        opcodes="0x01",
        args="a,b",
        target="python",
        fn_name="sub",
        llm_prompt=("Write a Python function named sub(a, b) that returns a - b. " "Output only the function source."),
        test_cases=(
            ((10, 3), 7),
            ((0, 5), -5),
            ((-2, -2), 0),
        ),
    ),
    Task(
        id="mul_py",
        description="a*b in Python",
        opcodes="0x02",
        args="a,b",
        target="python",
        fn_name="mul",
        llm_prompt=("Write a Python function named mul(a, b) that returns a * b. " "Output only the function source."),
        test_cases=(
            ((3, 4), 12),
            ((0, 100), 0),
            ((-2, 5), -10),
        ),
    ),
    Task(
        id="abs_py",
        description="abs(a) in Python",
        opcodes="0x09",
        args="a",
        target="python",
        fn_name="abs_fn",
        llm_prompt=("Write a Python function named abs_fn(a) that returns abs(a). " "Output only the function source."),
        test_cases=(
            ((5,), 5),
            ((-7,), 7),
            ((0,), 0),
        ),
    ),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def estimate_tokens(text: str) -> int:
    """Rule-of-thumb token estimator for English + code: ~4 chars/token."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def estimate_sonnet_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000.0) * SONNET_INPUT_USD_PER_MTOK + (
        output_tokens / 1_000_000.0
    ) * SONNET_OUTPUT_USD_PER_MTOK


def strip_markdown_fence(text: str) -> str:
    """Pull the Python function source out of an LLM response that may
    have included a ```python ... ``` fence or commentary."""
    if "```" in text:
        m = re.search(r"```(?:python|py)?\s*(.*?)```", text, re.DOTALL)
        if m:
            return m.group(1).strip()
    # Trim any preface before the first def line
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("def "):
            return "\n".join(lines[i:]).strip()
    return text.strip()


def verify_python_fn(source: str, fn_name: str, test_cases: Tuple) -> Tuple[bool, str]:
    """Exec the source in an isolated namespace and call fn_name against
    each test case. Returns (success, reason)."""
    if not source.strip():
        return False, "empty source"
    ns: Dict[str, Any] = {"__name__": "_bench_arm"}
    try:
        exec(compile(source, "<bench>", "exec"), ns)  # noqa: S102
    except SyntaxError as e:
        return False, f"syntax_error: {e}"
    except Exception as e:  # noqa: BLE001
        return False, f"exec_error: {type(e).__name__}: {e}"
    fn = ns.get(fn_name)
    if fn is None:
        candidates = [k for k in ns if callable(ns[k]) and not k.startswith("_")]
        return False, f"fn_not_defined (have: {candidates})"
    if not callable(fn):
        return False, f"{fn_name} is not callable"
    for inputs, expected in test_cases:
        try:
            got = fn(*inputs)
        except Exception as e:  # noqa: BLE001
            return False, f"call_error inputs={inputs}: {type(e).__name__}: {e}"
        if got != expected:
            return False, f"wrong_value inputs={inputs} got={got} expected={expected}"
    return True, "pass"


# ---------------------------------------------------------------------------
# Comparator arms
# ---------------------------------------------------------------------------


@dataclass
class ArmResult:
    arm: str
    task_id: str
    wall_ms: float
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    success: bool
    reason: str
    source: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


def arm_mechanical(task: Task) -> ArmResult:
    """SCBE compile-ca: opcodes -> source. No LLM. Pure dispatcher."""
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "agents" / "scbe_code.py"),
        "compile-ca",
        "--opcodes",
        task.opcodes,
        "--target",
        task.target,
        "--fn",
        task.fn_name,
        "--args",
        task.args,
        "--json",
    ]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    wall_ms = (time.perf_counter() - t0) * 1000.0
    if proc.returncode != 0:
        return ArmResult(
            arm="mechanical",
            task_id=task.id,
            wall_ms=wall_ms,
            input_tokens=0,
            output_tokens=0,
            estimated_cost_usd=0.0,
            success=False,
            reason=f"compile_ca_failed: exit={proc.returncode} stderr={proc.stderr[:200]}",
        )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return ArmResult(
            arm="mechanical",
            task_id=task.id,
            wall_ms=wall_ms,
            input_tokens=0,
            output_tokens=0,
            estimated_cost_usd=0.0,
            success=False,
            reason=f"json_decode_error: {e}",
        )
    source = payload.get("source", "")
    if task.target == "python":
        ok, reason = verify_python_fn(source, task.fn_name, task.test_cases)
    else:
        # For non-python targets the round_trip_ok flag is the available signal.
        ok = bool(payload.get("round_trip_ok"))
        reason = "round_trip_ok" if ok else "round_trip_failed"
    return ArmResult(
        arm="mechanical",
        task_id=task.id,
        wall_ms=wall_ms,
        input_tokens=0,
        output_tokens=0,
        estimated_cost_usd=0.0,
        success=ok,
        reason=reason,
        source=source,
        extra={"round_trip_ok": payload.get("round_trip_ok"), "op_trace": payload.get("op_trace")},
    )


def ollama_generate(model: str, prompt: str, timeout: float = 90.0) -> Optional[Dict[str, Any]]:
    """Hit the local Ollama /api/generate endpoint with a non-streaming call."""
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 256},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return {"error": str(e)}


def arm_ollama(task: Task, model: str, arm_label: str) -> ArmResult:
    t0 = time.perf_counter()
    result = ollama_generate(model, task.llm_prompt)
    wall_ms = (time.perf_counter() - t0) * 1000.0
    if not result or "error" in result:
        return ArmResult(
            arm=arm_label,
            task_id=task.id,
            wall_ms=wall_ms,
            input_tokens=estimate_tokens(task.llm_prompt),
            output_tokens=0,
            estimated_cost_usd=0.0,
            success=False,
            reason=f"ollama_error: {(result or {}).get('error', 'no_response')}",
        )
    response = result.get("response", "")
    source = strip_markdown_fence(response)
    in_tok = result.get("prompt_eval_count") or estimate_tokens(task.llm_prompt)
    out_tok = result.get("eval_count") or estimate_tokens(response)
    if task.target == "python":
        ok, reason = verify_python_fn(source, task.fn_name, task.test_cases)
    else:
        ok, reason = False, "non_python_llm_arm_not_verified"
    return ArmResult(
        arm=arm_label,
        task_id=task.id,
        wall_ms=wall_ms,
        input_tokens=in_tok,
        output_tokens=out_tok,
        estimated_cost_usd=0.0,
        success=ok,
        reason=reason,
        source=source,
        extra={"raw_response_first_120": response[:120]},
    )


def arm_cost_estimate_sonnet(task: Task, reference_result: ArmResult) -> ArmResult:
    """No call. Estimate what a Sonnet-class API would have cost given
    the same prompt and an output of comparable size to the LLM arm
    (uses the medium model's output token count as the reference)."""
    in_tok = estimate_tokens(task.llm_prompt)
    out_tok = reference_result.output_tokens or estimate_tokens(reference_result.source or "")
    cost = estimate_sonnet_cost_usd(in_tok, out_tok)
    return ArmResult(
        arm="cost_estimate_sonnet",
        task_id=task.id,
        wall_ms=0.0,
        input_tokens=in_tok,
        output_tokens=out_tok,
        estimated_cost_usd=cost,
        success=reference_result.success,
        reason=f"projected_from {reference_result.arm}",
        extra={
            "reference_arm": reference_result.arm,
            "rates_usd_per_mtok_in_out": [SONNET_INPUT_USD_PER_MTOK, SONNET_OUTPUT_USD_PER_MTOK],
        },
    )


# ---------------------------------------------------------------------------
# Receipt emission
# ---------------------------------------------------------------------------


def emit_receipt(arm_result: ArmResult) -> str:
    """Write an aetherdesk_receipt_v0 JSON for one (arm, task) op."""
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    task_id = f"{utc_stamp()}_bench_{arm_result.arm}_{arm_result.task_id}"
    receipt = {
        "schema": "aetherdesk_receipt_v0",
        "task_id": task_id,
        "command_id": f"bench:{arm_result.arm}",
        "command_label": f"benchmark {arm_result.arm} :: {arm_result.task_id}",
        "command": f"bench/{arm_result.arm}/{arm_result.task_id}",
        "command_digest": sha256(f"{arm_result.arm}|{arm_result.task_id}|{arm_result.source[:200]}"),
        "risk_tier": "read-only",
        "allowed_paths": ["<repo-readonly>"],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": int(arm_result.wall_ms),
        "exit_code": 0 if arm_result.success else 1,
        "result": "pass" if arm_result.success else "fail",
        "stdout_tail": (arm_result.source or "")[-4096:],
        "stderr_tail": "" if arm_result.success else arm_result.reason[:4096],
        "artifact_path": "",
        "bench": {
            "arm": arm_result.arm,
            "task_id": arm_result.task_id,
            "input_tokens": arm_result.input_tokens,
            "output_tokens": arm_result.output_tokens,
            "estimated_cost_usd": arm_result.estimated_cost_usd,
            "reason": arm_result.reason,
            "extra": arm_result.extra,
        },
    }
    path = RECEIPTS_DIR / f"{task_id}.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    receipt["artifact_path"] = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    return receipt["artifact_path"]


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def discover_ollama_models() -> List[str]:
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE}/api/tags", timeout=2) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:  # noqa: BLE001
        return []


def aggregate(results: List[ArmResult]) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for r in results:
        bucket = out.setdefault(
            r.arm,
            {
                "runs": 0,
                "passed": 0,
                "total_wall_ms": 0.0,
                "total_in_tokens": 0,
                "total_out_tokens": 0,
                "total_cost_usd": 0.0,
            },
        )
        bucket["runs"] += 1
        bucket["passed"] += 1 if r.success else 0
        bucket["total_wall_ms"] += r.wall_ms
        bucket["total_in_tokens"] += r.input_tokens
        bucket["total_out_tokens"] += r.output_tokens
        bucket["total_cost_usd"] += r.estimated_cost_usd
    for arm, bucket in out.items():
        bucket["pass_rate"] = bucket["passed"] / max(bucket["runs"], 1)
        bucket["mean_wall_ms"] = bucket["total_wall_ms"] / max(bucket["runs"], 1)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--task-ids",
        default="",
        help="comma-separated subset of TASKS to run (default: all)",
    )
    parser.add_argument(
        "--no-ollama",
        action="store_true",
        help="skip Ollama arms (e.g. CI without local models)",
    )
    parser.add_argument(
        "--small-model",
        default="qwen2.5-coder:0.5b",
        help="Ollama model id for the small-LLM arm",
    )
    parser.add_argument(
        "--medium-model",
        default="qwen2.5-coder:1.5b",
        help="Ollama model id for the medium-LLM arm",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress per-task stdout",
    )
    args = parser.parse_args(argv)

    if args.task_ids:
        wanted = set(args.task_ids.split(","))
        tasks = tuple(t for t in TASKS if t.id in wanted)
    else:
        tasks = TASKS
    if not tasks:
        print("no tasks selected", file=sys.stderr)
        return 2

    available_models = set() if args.no_ollama else set(discover_ollama_models())
    run_small = (not args.no_ollama) and (args.small_model in available_models)
    run_medium = (not args.no_ollama) and (args.medium_model in available_models)

    all_results: List[ArmResult] = []
    receipts: List[str] = []
    for task in tasks:
        if not args.quiet:
            print(f"== {task.id} :: {task.description}", flush=True)

        mech = arm_mechanical(task)
        all_results.append(mech)
        receipts.append(emit_receipt(mech))
        if not args.quiet:
            print(
                f"  mechanical            {mech.wall_ms:7.1f} ms  {'PASS' if mech.success else 'FAIL'}  {mech.reason}"
            )

        medium_ref: Optional[ArmResult] = None
        if run_small:
            small = arm_ollama(
                task, args.small_model, f"ollama_{args.small_model.replace(':','_').replace('.','_').replace('/','_')}"
            )
            all_results.append(small)
            receipts.append(emit_receipt(small))
            if not args.quiet:
                print(
                    f"  {small.arm:22s}{small.wall_ms:7.1f} ms  {'PASS' if small.success else 'FAIL'}  in={small.input_tokens} out={small.output_tokens}  {small.reason[:60]}"
                )
        if run_medium:
            medium = arm_ollama(
                task,
                args.medium_model,
                f"ollama_{args.medium_model.replace(':','_').replace('.','_').replace('/','_')}",
            )
            all_results.append(medium)
            medium_ref = medium
            receipts.append(emit_receipt(medium))
            if not args.quiet:
                print(
                    f"  {medium.arm:22s}{medium.wall_ms:7.1f} ms  {'PASS' if medium.success else 'FAIL'}  in={medium.input_tokens} out={medium.output_tokens}  {medium.reason[:60]}"
                )

        ref = medium_ref or (all_results[-2] if (run_small or run_medium) else None)
        if ref is not None:
            cost_est = arm_cost_estimate_sonnet(task, ref)
            all_results.append(cost_est)
            receipts.append(emit_receipt(cost_est))
            if not args.quiet:
                print(
                    f"  cost_estimate_sonnet  in={cost_est.input_tokens} out={cost_est.output_tokens}  ${cost_est.estimated_cost_usd:.6f}  (projected from {ref.arm})"
                )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    aggregates = aggregate(all_results)
    report = {
        "schema": "aetherdesk_bench_report_v0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT).replace("\\", "/"),
        "n_tasks": len(tasks),
        "ran_ollama_small": run_small,
        "ran_ollama_medium": run_medium,
        "small_model": args.small_model if run_small else None,
        "medium_model": args.medium_model if run_medium else None,
        "arms": aggregates,
        "results": [asdict(r) for r in all_results],
        "receipts": receipts,
    }
    out_path = REPORT_DIR / f"bench_report_{utc_stamp()}.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n")
    relpath = str(out_path.relative_to(REPO_ROOT)).replace("\\", "/")

    print()
    print(f"Report: {relpath}")
    print()
    print(
        f"{'arm':<32s} {'runs':>5s} {'pass':>5s} {'pass%':>6s} {'mean_ms':>10s} {'in_tok':>8s} {'out_tok':>8s} {'cost_usd':>12s}"
    )
    for arm, bucket in aggregates.items():
        print(
            f"{arm:<32s} {int(bucket['runs']):>5d} {int(bucket['passed']):>5d} "
            f"{bucket['pass_rate']*100:>5.1f}% {bucket['mean_wall_ms']:>10.1f} "
            f"{int(bucket['total_in_tokens']):>8d} {int(bucket['total_out_tokens']):>8d} "
            f"${bucket['total_cost_usd']:>11.6f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
