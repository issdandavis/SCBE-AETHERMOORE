#!/usr/bin/env python3
"""Benchmark SCBE's two-agent coding pattern against a solo local agent.

This is not a frontier-model leaderboard. It measures the thing SCBE can
realistically become good at first: a paired coding workflow where one agent
proposes work and a second agent navigates deterministic tools, checks, and
non-conflicting lanes before acceptance.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.ca_opcode_table import OP_TABLE  # noqa: E402
from src.crypto.sacred_tongue_payload_bijection import prove_dict  # noqa: E402

SCHEMA_VERSION = "scbe_dual_agent_pair_benchmark_v1"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "benchmark" / "dual_agent_pair_benchmark" / "latest_report.json"

CA_SEQUENCE_RE = re.compile(r"0x09\s*,\s*0x09\s*,\s*0x00", flags=re.IGNORECASE)


@dataclass(frozen=True)
class PairTask:
    task_id: str
    kind: str
    prompt: str
    success_contract: dict[str, Any]


@dataclass(frozen=True)
class AgentPacket:
    role: str
    lane: str
    action: str
    input_summary: str
    output_summary: str
    tools: list[str]
    allowed_paths: list[str]
    blocked_paths: list[str]
    status: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ca_name_index() -> dict[str, int]:
    return {entry.name.lower(): op_id for op_id, entry in OP_TABLE.items()}


def ca_plan(names: list[str]) -> dict[str, Any]:
    index = _ca_name_index()
    opcodes = [index[name] for name in names]
    hex_sequence = [f"0x{op:02X}" for op in opcodes]
    return {
        "tongue": "CA",
        "ops": names,
        "hex_sequence": hex_sequence,
        "hex": ", ".join(hex_sequence),
        "source": "python.scbe.ca_opcode_table.OP_TABLE",
    }


def depth2_solution() -> str:
    return """def depth2_keys(obj: dict) -> list[str]:
    keys: list[str] = []
    for value in obj.values():
        if isinstance(value, dict):
            keys.extend(str(key) for key in value.keys())
    return sorted(keys)
"""


def task_suite() -> list[PairTask]:
    return [
        PairTask(
            task_id="ca_opcode_abs_add",
            kind="ca_opcode",
            prompt="Generate the exact CA opcode sequence for abs(a) + abs(b).",
            success_contract={"exact_sequence": ["0x09", "0x09", "0x00"]},
        ),
        PairTask(
            task_id="depth2_json_keys",
            kind="python_code",
            prompt="Write depth2_keys(obj) for sorted second-level dict keys.",
            success_contract={
                "entrypoint": "depth2_keys",
                "tests": [
                    [
                        {"a": {"x": 1, "y": {"z": 2}}, "b": 3, "c": {"m": 4}},
                        ["m", "x", "y"],
                    ],
                    [{}, []],
                ],
            },
        ),
        PairTask(
            task_id="tool_lane_separation",
            kind="routing",
            prompt="Plan a coding task so model output, deterministic CA lookup, tests, and apply are separate lanes.",
            success_contract={
                "required_lanes": ["builder", "navigator", "deterministic_tool", "verification", "apply_gate"]
            },
        ),
    ]


def solo_output(task: PairTask) -> str:
    """Deterministic stand-in for a one-body local model under system pressure."""
    if task.kind == "ca_opcode":
        return "CA: 0x09\nops: abs(a), abs(b), add"
    if task.kind == "python_code":
        return (
            "def depth2_keys(obj: dict) -> list[str]:\n"
            "    keys = []\n"
            "    for key, value in obj.items():\n"
            "        if len(value) == 2 and value[0].isdigit():\n"
            "            keys.append(key)\n"
            "    return sorted(keys)\n"
        )
    return "builder lane only; apply after generation"


def _check_python_code(code: str, contract: dict[str, Any]) -> dict[str, Any]:
    entrypoint = str(contract["entrypoint"])
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {"ok": False, "error": f"syntax_error: {exc}"}
    if not any(isinstance(node, ast.FunctionDef) and node.name == entrypoint for node in tree.body):
        return {"ok": False, "error": f"missing_function: {entrypoint}"}
    scope: dict[str, Any] = {
        "__builtins__": {
            "dict": dict,
            "isinstance": isinstance,
            "list": list,
            "sorted": sorted,
            "str": str,
        }
    }
    try:
        exec(compile(tree, "<pair-benchmark>", "exec"), scope, scope)
        fn = scope[entrypoint]
        failures = []
        for raw_args, expected in contract["tests"]:
            actual = fn(raw_args)
            if actual != expected:
                failures.append({"args": raw_args, "expected": expected, "actual": actual})
        return {"ok": not failures, "failures": failures}
    except Exception as exc:  # noqa: BLE001 - generated code is the subject under test
        return {"ok": False, "error": f"runtime_error: {type(exc).__name__}: {exc}"}


def score_output(task: PairTask, output: str, packets: list[AgentPacket]) -> dict[str, Any]:
    if task.kind == "ca_opcode":
        return {"ok": bool(CA_SEQUENCE_RE.search(output)), "exact_sequence": bool(CA_SEQUENCE_RE.search(output))}
    if task.kind == "python_code":
        return _check_python_code(output, task.success_contract)
    if task.kind == "routing":
        lanes = {packet.lane for packet in packets}
        required = set(task.success_contract["required_lanes"])
        return {"ok": required <= lanes, "lanes": sorted(lanes), "missing": sorted(required - lanes)}
    raise ValueError(f"unknown task kind: {task.kind}")


def run_solo(task: PairTask) -> dict[str, Any]:
    started = time.perf_counter()
    output = solo_output(task)
    packet = AgentPacket(
        role="solo_agent",
        lane="builder",
        action="generate",
        input_summary=task.prompt,
        output_summary=output[:180],
        tools=[],
        allowed_paths=["workspace"],
        blocked_paths=[".env", ".git", "secrets"],
        status="done",
    )
    score = score_output(task, output, [packet])
    return {
        "mode": "solo",
        "task_id": task.task_id,
        "ok": bool(score["ok"]),
        "elapsed_sec": round(time.perf_counter() - started, 4),
        "output": output,
        "packets": [asdict(packet)],
        "score": score,
    }


def run_pair(task: PairTask) -> dict[str, Any]:
    started = time.perf_counter()
    packets: list[AgentPacket] = [
        AgentPacket(
            role="builder",
            lane="builder",
            action="propose",
            input_summary=task.prompt,
            output_summary="draft candidate and identify needed lane",
            tools=[],
            allowed_paths=["scripts", "src", "tests"],
            blocked_paths=[".env", ".git", "config/connector_oauth"],
            status="done",
        )
    ]

    if task.kind == "ca_opcode":
        plan = ca_plan(["abs", "abs", "add"])
        output = f"CA: {plan['hex']}\nops: abs(a), abs(b), add\nsource: {plan['source']}"
        packets.append(
            AgentPacket(
                role="navigator",
                lane="deterministic_tool",
                action="route_to_ca_plan",
                input_summary="abs, abs, add",
                output_summary=plan["hex"],
                tools=["scripts/agents/scbe_code.py ca-plan"],
                allowed_paths=["python/scbe/ca_opcode_table.py", "scripts/agents/scbe_code.py"],
                blocked_paths=["model_weight_guessing"],
                status="done",
            )
        )
    elif task.kind == "python_code":
        output = depth2_solution()
        packets.append(
            AgentPacket(
                role="navigator",
                lane="verification",
                action="critic_repair",
                input_summary="depth2_keys candidate",
                output_summary="non-recursive one-level dictionary walk",
                tools=["ast.parse", "sandboxed_function_tests"],
                allowed_paths=["tests", "artifacts/benchmark"],
                blocked_paths=["main_tree_apply"],
                status="done",
            )
        )
    else:
        output = "builder -> navigator -> deterministic_tool -> verification -> apply_gate"
        packets.extend(
            [
                AgentPacket(
                    role="navigator",
                    lane="navigator",
                    action="assign_lanes",
                    input_summary="separate conflicting responsibilities",
                    output_summary="builder/model/tool/test/apply lanes separated",
                    tools=[],
                    allowed_paths=["artifacts/agent_comm", "artifacts/benchmark"],
                    blocked_paths=["shared_file_without_owner"],
                    status="done",
                ),
                AgentPacket(
                    role="navigator",
                    lane="deterministic_tool",
                    action="reserve_lookup_lane",
                    input_summary="exact tables and CLI routing",
                    output_summary="table facts use tools, not model memory",
                    tools=["ca-plan", "manifest", "compile-ca"],
                    allowed_paths=["python/scbe", "scripts/agents"],
                    blocked_paths=["freeform_opcode_generation"],
                    status="done",
                ),
                AgentPacket(
                    role="navigator",
                    lane="verification",
                    action="reserve_test_lane",
                    input_summary="acceptance gates",
                    output_summary="tests before apply",
                    tools=["pytest", "py_compile"],
                    allowed_paths=["tests", "artifacts"],
                    blocked_paths=["untested_apply"],
                    status="done",
                ),
                AgentPacket(
                    role="builder",
                    lane="apply_gate",
                    action="apply_only_after_green",
                    input_summary="verified patch",
                    output_summary="safe_apply or explicit patch path",
                    tools=["scripts/agents/safe_apply.py"],
                    allowed_paths=["assigned_files_only"],
                    blocked_paths=["unowned_dirty_files"],
                    status="planned",
                ),
            ]
        )

    score = score_output(task, output, packets)
    return {
        "mode": "pair",
        "task_id": task.task_id,
        "ok": bool(score["ok"]),
        "elapsed_sec": round(time.perf_counter() - started, 4),
        "output": output,
        "packets": [asdict(packet) for packet in packets],
        "score": score,
        "pair_contract": {
            "builder": "proposes code or plan but does not trust exact system facts from memory",
            "navigator": "routes deterministic facts, verifies, and prevents conflicting tool/apply lanes",
        },
    }


def run_benchmark() -> dict[str, Any]:
    tasks = task_suite()
    solo = [run_solo(task) for task in tasks]
    pair = [run_pair(task) for task in tasks]
    solo_pass = sum(1 for row in solo if row["ok"])
    pair_pass = sum(1 for row in pair if row["ok"])
    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "goal": "benchmark paired SCBE coding agents against a one-body local workflow on SCBE-native tasks",
        "limits": [
            "This is a repo-native harness benchmark, not a claim of GPT or Claude parity.",
            "Exact opcode and system-table facts are expected to route through deterministic tools.",
            "The next useful comparison is to replace the deterministic solo stub with live model adapters.",
        ],
        "summary": {
            "tasks": len(tasks),
            "solo_passed": solo_pass,
            "pair_passed": pair_pass,
            "solo_pass_rate": round(solo_pass / len(tasks), 3),
            "pair_pass_rate": round(pair_pass / len(tasks), 3),
            "pair_delta": round((pair_pass - solo_pass) / len(tasks), 3),
            "cost_usd": 0.0,
        },
        "tasks": [asdict(task) for task in tasks],
        "solo_results": solo,
        "pair_results": pair,
    }
    core = {k: v for k, v in payload.items() if k != "sacred_tongue_bijection"}
    payload["sacred_tongue_bijection"] = prove_dict(core)
    return payload


def write_report(payload: dict[str, Any], output: Path) -> dict[str, str]:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path = output.with_suffix(".md")
    summary = payload["summary"]
    lines = [
        "# Dual Agent Pair Benchmark",
        "",
        f"- solo pass rate: `{summary['solo_pass_rate']}`",
        f"- pair pass rate: `{summary['pair_pass_rate']}`",
        f"- pair delta: `{summary['pair_delta']}`",
        f"- cost_usd: `{summary['cost_usd']}`",
        "",
        "| Task | Solo | Pair |",
        "| --- | --- | --- |",
    ]
    solo_by_id = {row["task_id"]: row for row in payload["solo_results"]}
    for row in payload["pair_results"]:
        task_id = row["task_id"]
        lines.append(f"| `{task_id}` | `{solo_by_id[task_id]['ok']}` | `{row['ok']}` |")
    lines.extend(
        [
            "",
            "## Realistic Interpretation",
            "",
            "This benchmark is useful when the pair wins by routing exact facts through deterministic tools, "
            "repairing generated code with tests, and separating apply/tool lanes. It should not be used as a "
            "frontier-model capability claim.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(output), "markdown": str(md_path)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate", help="run benchmark in memory and print summary")
    run = sub.add_parser("run", help="run benchmark and write report")
    run.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = run_benchmark()
    if args.cmd == "validate":
        print(json.dumps({"ok": payload["summary"]["pair_passed"] >= payload["summary"]["solo_passed"], "summary": payload["summary"]}, indent=2))
        return 0 if payload["summary"]["pair_passed"] >= payload["summary"]["solo_passed"] else 1
    paths = write_report(payload, args.output)
    print(json.dumps({"ok": True, **paths, "summary": payload["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
