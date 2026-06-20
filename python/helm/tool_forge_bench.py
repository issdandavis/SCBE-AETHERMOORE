"""Tool Forge Bench: small tool-making tasks with hidden checks and receipts.

The public coding-agent benchmarks mostly measure "use the given tools" or
"patch the given repo." This harness measures the loop we care about:

1. propose a tool contract
2. write an implementation
3. verify against public and hidden examples
4. repair after failure
5. keep the verified tool and receipt

It is intentionally deterministic and stdlib-only. A real model can replace the
bad/fixed source generators later without changing the verifier or receipt
format.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .dag import run_dag
from .machine import Step, upstream

Example = Tuple[Tuple[Any, ...], Any]


@dataclass(frozen=True)
class ToolTask:
    """One tool-making benchmark task."""

    name: str
    function_name: str
    contract: str
    bad_source: str
    fixed_source: str
    public_examples: Tuple[Example, ...]
    hidden_examples: Tuple[Example, ...]


def _module_source(function_name: str, body: str) -> str:
    return "\n".join(
        [
            '"""Generated benchmark tool."""',
            "",
            f"def {function_name}(*args):",
            body,
            "",
        ]
    )


TASKS: Tuple[ToolTask, ...] = (
    ToolTask(
        name="add_one",
        function_name="add_one",
        contract="Return value + 1 for positive, zero, and negative integers.",
        bad_source=_module_source("add_one", "    return args[0] + 2"),
        fixed_source=_module_source("add_one", "    return args[0] + 1"),
        public_examples=(((0,), 1), ((41,), 42)),
        hidden_examples=(((-2,), -1), ((999,), 1000)),
    ),
    ToolTask(
        name="clamp_int",
        function_name="clamp_int",
        contract="Clamp an integer into inclusive [low, high] bounds.",
        bad_source=_module_source("clamp_int", "    value, low, high = args\n    return min(value, high)"),
        fixed_source=_module_source(
            "clamp_int",
            "    value, low, high = args\n    return max(low, min(value, high))",
        ),
        public_examples=(((7, 0, 10), 7), ((12, 0, 10), 10)),
        hidden_examples=(((-3, 0, 10), 0), ((5, 5, 5), 5)),
    ),
    ToolTask(
        name="slugify",
        function_name="slugify",
        contract="Lowercase text, keep alphanumerics, collapse separators to single dashes.",
        bad_source=_module_source(
            "slugify",
            "    text = args[0].strip().lower()\n    return text.replace(' ', '-')",
        ),
        fixed_source=_module_source(
            "slugify",
            "    out = []\n"
            "    dash = False\n"
            "    for ch in args[0].strip().lower():\n"
            "        if ch.isalnum():\n"
            "            out.append(ch)\n"
            "            dash = False\n"
            "        elif not dash:\n"
            "            out.append('-')\n"
            "            dash = True\n"
            "    return ''.join(out).strip('-')",
        ),
        public_examples=((("Hello World",), "hello-world"), (("  Ship It  ",), "ship-it")),
        hidden_examples=((("A--B!! C",), "a-b-c"), (("one_two",), "one-two")),
    ),
    ToolTask(
        name="parse_bool",
        function_name="parse_bool",
        contract="Parse common boolean strings, returning True/False and raising ValueError for unknown values.",
        bad_source=_module_source(
            "parse_bool",
            "    value = str(args[0]).strip().lower()\n"
            "    if value == 'yes':\n"
            "        return True\n"
            "    if value == 'no':\n"
            "        return False\n"
            "    raise ValueError(value)",
        ),
        fixed_source=_module_source(
            "parse_bool",
            "    value = str(args[0]).strip().lower()\n"
            "    if value in {'yes', 'y', 'true', 't', '1', 'on'}:\n"
            "        return True\n"
            "    if value in {'no', 'n', 'false', 'f', '0', 'off'}:\n"
            "        return False\n"
            "    raise ValueError(value)",
        ),
        public_examples=((("yes",), True), (("NO",), False)),
        hidden_examples=((("1",), True), (("off",), False)),
    ),
)


def _write_tool(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")


def _load_function(path: Path, function_name: str) -> Callable[..., Any]:
    namespace: Dict[str, Any] = {}
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace)
    fn = namespace.get(function_name)
    if not callable(fn):
        raise TypeError(f"{function_name} is not callable")
    return fn


def _verify_examples(path: Path, task: ToolTask, examples: Sequence[Example], suite: str) -> Dict[str, Any]:
    failures: List[Dict[str, Any]] = []
    try:
        fn = _load_function(path, task.function_name)
        for args, expected in examples:
            try:
                actual = fn(*args)
            except Exception as exc:
                failures.append(
                    {
                        "suite": suite,
                        "input": list(args),
                        "expected": expected,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                continue
            if actual != expected:
                failures.append({"suite": suite, "input": list(args), "expected": expected, "actual": actual})
    except Exception as exc:
        failures.append({"suite": suite, "error": f"{type(exc).__name__}: {exc}"})
    return {"suite": suite, "passed": not failures, "examples": len(examples), "failures": failures}


def _verify_tool(path: Path, task: ToolTask) -> Dict[str, Any]:
    public = _verify_examples(path, task, task.public_examples, "public")
    hidden = _verify_examples(path, task, task.hidden_examples, "hidden")
    failures = public["failures"] + hidden["failures"]
    return {
        "passed": public["passed"] and hidden["passed"],
        "public_passed": public["passed"],
        "hidden_passed": hidden["passed"],
        "examples": public["examples"] + hidden["examples"],
        "failures": failures,
    }


def run_tool_task(task: ToolTask, workspace: Path) -> Dict[str, Any]:
    """Run one benchmark task through the forge loop."""

    task_dir = workspace / task.name
    task_dir.mkdir(parents=True, exist_ok=True)
    tool_path = task_dir / f"{task.name}.py"
    library_dir = workspace / "tool_library"
    receipt_path = task_dir / "receipt.json"

    def propose(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "task": task.name,
            "function": task.function_name,
            "contract": task.contract,
            "public_examples": len(task.public_examples),
            "hidden_examples": len(task.hidden_examples),
            "ready": True,
        }

    def build_bad(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        _write_tool(tool_path, task.bad_source)
        return {"path": str(tool_path), "attempt": 1, "wrote": True}

    def verify_bad(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        result = _verify_tool(tool_path, task)
        result["attempt"] = 1
        return result

    def repair(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        failures = context["results"]["verify_attempt_1"]["failures"]
        return {"needed": True, "failures_seen": len(failures), "reason": "verification failed"}

    def build_fixed(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        _write_tool(tool_path, task.fixed_source)
        return {"path": str(tool_path), "attempt": 2, "wrote": True}

    def verify_fixed(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        result = _verify_tool(tool_path, task)
        result["attempt"] = 2
        return result

    def keep_tool(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        library_dir.mkdir(exist_ok=True)
        kept_path = library_dir / tool_path.name
        shutil.copy2(tool_path, kept_path)
        receipt = {
            "task": task.name,
            "contract": task.contract,
            "kept_path": str(kept_path),
            "attempts": [
                context["results"]["verify_attempt_1"],
                context["results"]["verify_attempt_2"],
            ],
            "verified": True,
        }
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
        return {"kept_path": str(kept_path), "receipt_path": str(receipt_path), "verified": True}

    steps = [
        Step("propose_contract", "design", propose),
        Step("build_attempt_1", "build", build_bad, criteria=(upstream("propose_contract", "ready", True),)),
        Step("verify_attempt_1", "verify", verify_bad, criteria=(upstream("build_attempt_1", "wrote", True),)),
        Step("repair_plan", "repair", repair, criteria=(upstream("verify_attempt_1", "passed", False),)),
        Step("build_attempt_2", "build", build_fixed, criteria=(upstream("repair_plan", "needed", True),)),
        Step("verify_attempt_2", "verify", verify_fixed, criteria=(upstream("build_attempt_2", "wrote", True),)),
        Step("keep_verified_tool", "store", keep_tool, criteria=(upstream("verify_attempt_2", "passed", True),)),
    ]
    run = run_dag(f"forge verified tool: {task.name}", steps)
    return {
        "task": task.name,
        "approved": run.approved,
        "denied": run.denied_count,
        "failed": run.failed,
        "chain": run.chain_digest,
        "first_attempt_passed": run.results["verify_attempt_1"]["passed"],
        "first_public_passed": run.results["verify_attempt_1"]["public_passed"],
        "first_hidden_passed": run.results["verify_attempt_1"]["hidden_passed"],
        "second_attempt_passed": run.results["verify_attempt_2"]["passed"],
        "kept_path": run.results["keep_verified_tool"]["kept_path"],
        "receipt_path": run.results["keep_verified_tool"]["receipt_path"],
        "repair_failures_seen": run.results["repair_plan"]["failures_seen"],
    }


def run_tool_forge_bench(
    tasks: Iterable[ToolTask] = TASKS,
    workspace: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run all tool forge tasks and return a benchmark receipt."""

    root = Path(workspace) if workspace is not None else Path(tempfile.mkdtemp(prefix="helm-tool-forge-bench-"))
    root.mkdir(parents=True, exist_ok=True)
    results = [run_tool_task(task, root) for task in tasks]
    passed = [row for row in results if row["second_attempt_passed"]]
    hidden_catches = [row for row in results if row["first_public_passed"] and not row["first_hidden_passed"]]
    summary = {
        "workspace": str(root),
        "tasks": len(results),
        "passed_after_repair": len(passed),
        "pass_rate": len(passed) / len(results) if results else 0.0,
        "hidden_catches": len(hidden_catches),
        "results": results,
    }
    (root / "tool_forge_bench_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def render_tool_forge_bench(summary: Dict[str, Any]) -> str:
    lines = [
        "Helm Tool Forge Bench: create, test, repair, keep",
        f"workspace: {summary['workspace']}",
        f"tasks: {summary['tasks']}",
        f"passed after repair: {summary['passed_after_repair']}/{summary['tasks']}",
        f"hidden checks caught public-only attempts: {summary['hidden_catches']}",
        "",
        "tasks:",
    ]
    for row in summary["results"]:
        lines.append(
            "  - {task}: first={first} public={public} hidden={hidden} repaired={second} receipt={receipt}".format(
                task=row["task"],
                first=row["first_attempt_passed"],
                public=row["first_public_passed"],
                hidden=row["first_hidden_passed"],
                second=row["second_attempt_passed"],
                receipt=row["receipt_path"],
            )
        )
    lines.extend(["", "json:", json.dumps(summary, indent=2, sort_keys=True)])
    return "\n".join(lines)


def main() -> int:
    print(render_tool_forge_bench(run_tool_forge_bench()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
