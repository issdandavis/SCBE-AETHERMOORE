"""Governed tool wrappers for verified tool-use trajectories.

This keeps the training loop's record shape intact while making each TOOL result carry an auditable
governance receipt. The wrapper is intentionally outside ``tool_trajectory.py`` so harvest prompt work
can continue independently: pass ``tools=build_governed_tools(problem)`` to ``solve_with_tools``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from python.helm.tool_trajectory import Tool, build_tools
from python.scbe.desktop_access import _DESTRUCTIVE, _gate, _seal

_PYTHON_RCE = re.compile(
    r"__import__\s*\(|\b(?:eval|exec|compile|open)\s*\(|\b(?:subprocess|socket|requests|urllib)\b|"
    r"\bos\.system\b|\bos\.popen\b|\bpathlib\.Path\s*\([^)]*\)\.unlink\b",
    re.IGNORECASE,
)


@dataclass
class ToolGovernanceLedger:
    """Forward-chain receipts for one tool registry.

    The seal is the same unkeyed, in-process integrity primitive used by ``desktop_access``. That makes
    these receipts tamper-evident inside a harvested transcript; it is not custody against a privileged
    in-process re-chainer.
    """

    transcript: List[dict] = field(default_factory=list)
    nonce: str = field(default_factory=lambda: hashlib.sha256(os.urandom(16)).hexdigest()[:16])

    def decide(self, tool_name: str, arg: str) -> dict:
        gate = _gate(arg) if arg.strip() else None
        reason = ""
        decision = "ALLOWED"
        if tool_name == "run_code" and _DESTRUCTIVE.search(arg):
            decision = "REFUSED"
            reason = "destructive Python blocked"
        elif tool_name == "run_code" and _PYTHON_RCE.search(arg):
            decision = "REFUSED"
            reason = "unsafe Python capability blocked"
        elif gate in ("DENY", "ESCALATE"):
            decision = "REFUSED"
            reason = "L13 gate %s" % gate
        else:
            reason = "allowed"

        rec = {
            "hop": len(self.transcript) + 1,
            "tool": tool_name,
            "decision": decision,
            "reason": reason,
            "arg_digest": hashlib.sha256(arg.encode("utf-8")).hexdigest(),
            "l13": "consulted" if gate is not None else ("n/a" if not arg.strip() else "unavailable"),
            "gate": gate,
            "_prev": self.transcript[-1]["seal"] if self.transcript else self.nonce,
        }
        rec["seal"] = _seal(rec)
        self.transcript.append(rec)
        return rec

    def verify(self) -> bool:
        prev = self.nonce
        for rec in self.transcript:
            if rec.get("_prev") != prev or rec.get("seal") != _seal(rec):
                return False
            prev = rec["seal"]
        return True


def _receipt_line(receipt: dict) -> str:
    public = {
        "schema": "scbe_tool_governance_v0",
        "tool": receipt["tool"],
        "decision": receipt["decision"],
        "reason": receipt["reason"],
        "arg_digest": receipt["arg_digest"],
        "seal": receipt["seal"],
        "prev": receipt["_prev"],
    }
    return "GOVERNANCE " + json.dumps(public, sort_keys=True, separators=(",", ":"))


def build_governed_tools(
    problem: Dict[str, Any],
    public_k: int = 1,
    ledger: Optional[ToolGovernanceLedger] = None,
    base_tools: Optional[Dict[str, Tool]] = None,
) -> Dict[str, Tool]:
    """Return ``tool_trajectory`` tools wrapped with governance receipts.

    A refused tool never calls the underlying tool implementation. For ``run_code`` this means model
    supplied destructive/RCE-shaped Python is denied before the verifier's subprocess path is reached.
    """

    ledger = ledger or ToolGovernanceLedger()
    base = base_tools or build_tools(problem, public_k)

    def wrap(tool: Tool) -> Tool:
        def run(arg: str) -> str:
            receipt = ledger.decide(tool.name, arg)
            if receipt["decision"] != "ALLOWED":
                return "%s\nDENIED: %s" % (_receipt_line(receipt), receipt["reason"])
            result = tool.run(arg)
            return "%s\n%s" % (_receipt_line(receipt), result)

        return Tool(tool.name, run, tool.doc + " (governed + sealed)")

    return {name: wrap(tool) for name, tool in base.items()}
