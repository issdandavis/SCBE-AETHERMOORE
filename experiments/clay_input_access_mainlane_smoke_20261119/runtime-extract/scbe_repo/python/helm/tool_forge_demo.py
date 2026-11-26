"""Tool Forge demo: build, verify, repair, and keep a small tool.

Run with:

    python -m python.helm.tool_forge_demo

This is the minimal "agent as tool-maker" loop:

1. propose a tiny tool contract
2. write an implementation
3. verify it against examples
4. repair after a failed verification
5. keep the verified tool and receipt
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import Step, run_dag, upstream

TOOL_NAME = "add_one"


def _write_tool(path: Path, expression: str) -> None:
    path.write_text(
        "\n".join(
            [
                '"""Generated demo tool."""',
                "",
                "def add_one(value):",
                f"    return {expression}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _verify_tool(path: Path) -> Dict[str, Any]:
    examples = [(0, 1), (1, 2), (41, 42), (-2, -1)]
    failures: List[Dict[str, Any]] = []
    try:
        namespace: Dict[str, Any] = {}
        exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace)
        for given, expected in examples:
            actual = namespace["add_one"](given)
            if actual != expected:
                failures.append({"input": given, "expected": expected, "actual": actual})
    except Exception as exc:
        failures.append({"error": f"{type(exc).__name__}: {exc}"})
    return {"passed": not failures, "examples": len(examples), "failures": failures}


def run_tool_forge_demo(workspace: Optional[Path] = None) -> Dict[str, Any]:
    """Run the forge loop and return a receipt dictionary."""

    root = Path(workspace) if workspace is not None else Path(tempfile.mkdtemp(prefix="helm-tool-forge-"))
    root.mkdir(parents=True, exist_ok=True)
    tool_path = root / f"{TOOL_NAME}.py"
    library_dir = root / "tool_library"
    receipt_path = root / "tool_forge_receipt.json"

    def propose(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "tool": TOOL_NAME,
            "contract": "add_one(value) returns value + 1",
            "examples": [[0, 1], [1, 2], [41, 42], [-2, -1]],
            "ready": True,
        }

    def build_bad(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        _write_tool(tool_path, "value + 2")
        return {"path": str(tool_path), "attempt": 1, "wrote": True}

    def verify_bad(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        result = _verify_tool(tool_path)
        result["attempt"] = 1
        return result

    def repair(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        failures = context["results"]["verify_attempt_1"]["failures"]
        return {"needed": True, "reason": "first attempt failed examples", "failures_seen": len(failures)}

    def build_fixed(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        _write_tool(tool_path, "value + 1")
        return {"path": str(tool_path), "attempt": 2, "wrote": True}

    def verify_fixed(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        result = _verify_tool(tool_path)
        result["attempt"] = 2
        return result

    def keep_tool(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        library_dir.mkdir(exist_ok=True)
        kept_path = library_dir / tool_path.name
        shutil.copy2(tool_path, kept_path)
        receipt = {
            "objective": objective,
            "tool": TOOL_NAME,
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
    run = run_dag("forge a verified add_one tool", steps)
    return {
        "workspace": str(root),
        "approved": run.approved,
        "denied": run.denied_count,
        "failed": run.failed,
        "chain": run.chain_digest,
        "first_attempt_passed": run.results["verify_attempt_1"]["passed"],
        "second_attempt_passed": run.results["verify_attempt_2"]["passed"],
        "kept_path": run.results["keep_verified_tool"]["kept_path"],
        "receipt_path": run.results["keep_verified_tool"]["receipt_path"],
        "receipts": [{"step": receipt.step, "status": receipt.status} for receipt in run.receipts],
    }


def render_tool_forge_demo(result: Dict[str, Any]) -> str:
    lines = [
        "Helm Tool Forge demo: make, test, repair, keep",
        f"workspace: {result['workspace']}",
        f"first attempt passed: {result['first_attempt_passed']}",
        f"second attempt passed: {result['second_attempt_passed']}",
        f"kept tool: {result['kept_path']}",
        f"receipt: {result['receipt_path']}",
        f"helm chain: {result['chain']}",
        "",
        "json:",
        json.dumps(result, indent=2, sort_keys=True),
    ]
    return "\n".join(lines)


def main() -> int:
    print(render_tool_forge_demo(run_tool_forge_demo()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
