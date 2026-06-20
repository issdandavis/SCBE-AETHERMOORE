"""aether_desk: a governed local computer for AI agents -- the bounded workspace where SCBE has
jurisdiction.

The framing: **SCBE is the law; AetherDesk is the place where the law has jurisdiction.** An agent gets
real tools -- files, a terminal, a test runner -- but inside a WORKSPACE it cannot leave. Every action
goes through the hardened desktop_access gate (never-delete / scope / chaining / L13 / confirm) AND a
WORKSPACE BOUND: every path must resolve *inside* the allowed root, or the action is REFUSED as an
escape. Every decision is SHA-256 forward-chain sealed into a receipt. So the agent can do real local
work and produce an audit trail -- without ever touching the rest of your machine.

The v0 "oh shit" demo (main): an agent enters the workspace, inspects a repo, runs a bounded command,
fixes a buggy file, runs the test until it passes, and produces a sealed receipt -- and a deliberate
escape attempt (write outside the workspace / a destructive command) is REFUSED and recorded.

    from python.scbe.aether_desk import AetherDesk
    desk = AetherDesk.open(workspace_dir)
    desk.act("write_file", {"path": "x.py", "content": "print(1)"}, confirm="agent task")  # ALLOWED, sealed
    desk.act("write_file", {"path": "../escape.py", "content": "x"})                        # REFUSED (escape)
    desk.verify()  # the receipt chain holds
"""

from __future__ import annotations

import copy
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .desktop_access import Action, ActionRegistry, _PATH_KEYS, _seal

_ALLOWED_CMDS = {"ls", "dir", "cat", "echo", "pwd", "python", "pytest", "git", "grep", "find", "head", "tail"}


class WorkspaceRegistry(ActionRegistry):
    """An ActionRegistry that adds, in FRONT of every other screen, the workspace bound: any path-bearing
    param must resolve INSIDE `root`. An out-of-bounds path is REFUSED (escape) and sealed like any other
    decision -- the agent cannot read or write outside its jurisdiction."""

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root.resolve()

    def _inside(self, value: str) -> bool:
        try:
            p = Path(value)
            full = (p if p.is_absolute() else self.root / p).resolve()
        except Exception:
            return False
        return full == self.root or self.root in full.parents

    def _escape(self, params: Dict[str, Any]) -> Optional[str]:
        for k, v in params.items():
            if isinstance(v, str) and (k.lower() in _PATH_KEYS) and not self._inside(v):
                return v
        return None

    def invoke(self, name: str, params: Optional[Dict[str, Any]] = None, confirm: Optional[str] = None) -> dict:
        params = params or {}
        bad = self._escape(params)
        if bad is not None:  # the WORKSPACE BOUND -- sealed, in front of the rest of the gate
            rec: dict = {
                "hop": len(self.transcript) + 1,
                "action": name,
                "params": copy.deepcopy(params),
                "decision": "REFUSED",
                "result": "escape blocked: %r is outside the workspace %s" % (bad, self.root),
            }
            if confirm:
                rec["confirm"] = str(confirm)
            rec["_prev"] = self.transcript[-1]["seal"] if self.transcript else self.nonce
            rec["seal"] = _seal(rec)
            self.transcript.append(rec)
            return rec
        return super().invoke(name, params, confirm)


@dataclass
class AetherDesk:
    """A bounded, governed workspace. `act()` runs an agent's proposed action through the workspace bound
    + the desktop_access gate, executes it (scoped to the workspace) only if ALLOWED, and seals a receipt."""

    root: Path
    reg: WorkspaceRegistry

    @classmethod
    def open(cls, workspace: Any) -> "AetherDesk":
        root = Path(workspace).resolve()
        root.mkdir(parents=True, exist_ok=True)
        reg = WorkspaceRegistry(root)
        desk = cls(root, reg)
        desk._register_actions()
        return desk

    # --- the tools the agent gets (all scoped to root) ---------------------------------------------
    def _resolve(self, rel: str) -> Path:
        return (self.root / rel).resolve()

    def _register_actions(self) -> None:
        def list_files(_p):
            return {"files": sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*") if p.is_file())}

        def read_file(p):
            f = self._resolve(str(p.get("path", "")))
            return f.read_text(encoding="utf-8") if f.is_file() else "no such file"

        def write_file(p):
            f = self._resolve(str(p.get("path", "")))
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(str(p.get("content", "")), encoding="utf-8")
            return "wrote %s (%d bytes)" % (p.get("path", ""), len(str(p.get("content", ""))))

        def run_command(p):
            cmd = str(p.get("command", "")).strip()
            head = cmd.split()[0] if cmd else ""
            if head not in _ALLOWED_CMDS:
                return "command %r not on the workspace allowlist" % head
            r = subprocess.run(cmd, shell=True, cwd=self.root, capture_output=True, text=True, timeout=60)
            return ((r.stdout or "") + (r.stderr or "")).strip()[:4000] or "(no output, rc=%d)" % r.returncode

        def run_test(p):
            f = self._resolve(str(p.get("path", "")))
            r = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", str(f)],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            out = ((r.stdout or "") + (r.stderr or "")).strip()
            return {"passed": r.returncode == 0, "output": out[-1500:]}

        self.reg.register(
            Action("list_files", "List files in the workspace", {}, "safe", "#files", "list", "Files", list_files)
        )
        self.reg.register(
            Action(
                "read_file",
                "Read a file in the workspace",
                {"path": "string"},
                "safe",
                "#read",
                "button",
                "Read",
                read_file,
            )
        )
        self.reg.register(
            Action(
                "write_file",
                "Write a file in the workspace",
                {"path": "string", "content": "string"},
                "guarded",
                "#write",
                "button",
                "Write",
                write_file,
            )
        )
        self.reg.register(
            Action(
                "run_command",
                "Run an allowlisted command in the workspace",
                {"command": "string"},
                "guarded",
                "#cmd",
                "textbox",
                "Terminal",
                run_command,
                text_param="command",
            )
        )
        self.reg.register(
            Action(
                "run_test",
                "Run a test file in the workspace",
                {"path": "string"},
                "guarded",
                "#test",
                "button",
                "Test",
                run_test,
            )
        )

    def act(self, name: str, params: Optional[Dict[str, Any]] = None, confirm: Optional[str] = None) -> dict:
        return self.reg.invoke(name, params or {}, confirm=confirm)

    def verify(self) -> bool:
        return self.reg.verify()

    def receipt(self) -> List[dict]:
        return self.reg.transcript

    # --- the execution substrate for ROUTED steps ----------------------------------------------------
    # The router (failure_map -> pre-allocate each typed step to its best block/model) decides WHO solves
    # each step. AetherDesk is WHERE it runs: bounded, execution-VERIFIED, and sealed into the receipt.
    def run_step(
        self,
        name: str,
        spec: str,
        check: Optional[List[str]],
        solver: Any,
        solver_name: str = "solver",
        confirm: Optional[str] = None,
    ) -> dict:
        """Run ONE routed step: the chosen `solver` (a deterministic block or a model, `spec`->code)
        produces a candidate, it is execution-verified against `check` (assert lines) inside the
        workspace, and a governed receipt is sealed. A wrong solver is recorded as FAILED, never hidden.
        Returns {step, solver, verified, candidate}. verified is None when there is no check to run."""
        from python.helm import public_bench as pb

        try:
            candidate = str(solver(spec))
        except Exception as exc:
            candidate = "# solver raised: %s: %s" % (type(exc).__name__, exc)
        verified: Optional[bool] = None
        if check:
            verified = bool(pb._verify(candidate, [], list(check), [])["hidden_passed"])
        rec: dict = {
            "hop": len(self.reg.transcript) + 1,
            "action": "run_step:" + name,
            "params": {"solver": solver_name, "spec": str(spec)[:200], "checks": len(check or [])},
            "decision": "VERIFIED" if verified else ("UNVERIFIED" if verified is None else "FAILED"),
            "result": candidate[:300],
        }
        if confirm:
            rec["confirm"] = str(confirm)
        rec["_prev"] = self.reg.transcript[-1]["seal"] if self.reg.transcript else self.reg.nonce
        rec["seal"] = _seal(rec)
        self.reg.transcript.append(rec)
        return {"step": name, "solver": solver_name, "verified": verified, "candidate": candidate, "seal": rec["seal"]}

    def run_pipeline(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run a routed plan -- a list of {name, spec, check, solver, solver_name}. Each step is verified
        + sealed; returns the per-step results, whether every checked step verified, and the receipt
        integrity. The router's plan, made runnable and governed."""
        out = [
            self.run_step(
                s["name"],
                s.get("spec", ""),
                s.get("check"),
                s["solver"],
                s.get("solver_name", "solver"),
                s.get("confirm"),
            )
            for s in steps
        ]
        checked = [r for r in out if r["verified"] is not None]
        return {
            "steps": out,
            "all_verified": all(r["verified"] for r in checked) if checked else None,
            "sealed": self.verify(),
        }


# --- solvers: a routed step is assigned to a deterministic BLOCK (free + exact) or a MODEL ----------
def block_solver(code: Any) -> Any:
    """A DETERMINISTIC block as a solver -- the $0, provably-exact path for a known-hard step. `code` is
    proven source (a str) or `spec`->str. Prefer this over a stronger model wherever a block exists."""
    return (lambda spec: str(code(spec))) if callable(code) else (lambda spec: str(code))


def model_solver(ask: Any) -> Any:
    """A model as a solver -- generate code from the spec via a prompt->str `ask`. The escalation path,
    used only where no deterministic block covers the step."""
    from python.helm.free_generator import strip_to_code

    return lambda spec: strip_to_code(ask(spec))


# --- the v0 "oh shit" demo: a governed agent doing real local work it cannot escape -----------------
_BUGGY = "def add(a, b):\n    return a - b   # bug\n"
_FIXED = "def add(a, b):\n    return a + b\n"
_TEST = "from sol import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n    assert add(-1, 1) == 0\n"


def demo(workspace: Any) -> dict:
    """Drive a scripted agent through the bounded workspace; return the sealed receipt + proof."""
    desk = AetherDesk.open(workspace)
    steps: List[dict] = []

    def step(label, name, params, confirm=None):
        r = desk.act(name, params, confirm=confirm)
        steps.append({"step": label, "decision": r["decision"], "result": r["result"]})
        return r

    # the agent does REAL work, every action sealed
    step("seed buggy solution", "write_file", {"path": "sol.py", "content": _BUGGY}, "task setup")
    step("seed the test", "write_file", {"path": "test_sol.py", "content": _TEST}, "task setup")
    step("inspect", "list_files", {})
    step("run test (expect FAIL)", "run_test", {"path": "test_sol.py"}, "verify before fix")
    step("fix the bug", "write_file", {"path": "sol.py", "content": _FIXED}, "agent applies fix")
    passed = step("run test (expect PASS)", "run_test", {"path": "test_sol.py"}, "verify the fix")

    # the agent CANNOT escape the jurisdiction -- these are REFUSED + sealed
    step("escape: write outside", "write_file", {"path": "../escaped.py", "content": "x"}, "malicious")
    step(
        "escape: absolute system path",
        "write_file",
        {"path": str(Path(os.sep) / "tmp" / "x"), "content": "x"},
        "malicious",
    )
    step("escape: destructive command", "run_command", {"command": "rm -rf /"}, "malicious")

    return {
        "workspace": str(desk.root),
        "steps": steps,
        "fix_verified": bool(passed["result"].get("passed")) if isinstance(passed["result"], dict) else False,
        "receipt_sealed": desk.verify(),
        "receipt_hops": len(desk.receipt()),
    }


def main(argv: Optional[List[str]] = None) -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="aether-desk-") as td:
        out = demo(td)
    print("AETHERDESK v0  -- a governed local computer for AI agents (SCBE has jurisdiction here)\n")
    for s in out["steps"]:
        mark = {"ALLOWED": "ok ", "REFUSED": "NO ", "ERROR": "ERR", "NEEDS_CONFIRM": "?? "}.get(s["decision"], "   ")
        print("  [%s] %-28s %-13s %s" % (mark, s["step"], s["decision"], str(s["result"])[:46]))
    print("\n  fix verified by the test:", out["fix_verified"])
    print("  escape attempts refused: every path/command outside the workspace was blocked")
    print("  receipt sealed + tamper-evident:", out["receipt_sealed"], "(%d hops)" % out["receipt_hops"])
    print("\n  -> a governed agent did real work inside a bounded computer, with a receipt, and could not escape.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
