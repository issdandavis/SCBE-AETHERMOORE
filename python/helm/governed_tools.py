"""Helm adapter for SCBE governed tool execution.

``python.scbe.governed_tools`` owns the policy, gate, execution, and sealed receipt chain. This module
only adapts that backend to ``python.helm.tool_trajectory.Tool`` so ``solve_with_tools(..., tools=...)``
can harvest governed tool-use records without changing the trajectory loop.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from python.helm.tool_trajectory import Tool
from python.scbe.governed_tools import GovernedToolbox


def build_governed_tools(
    problem: Optional[Dict[str, Any]] = None,
    public_k: int = 1,
    box: Optional[GovernedToolbox] = None,
) -> tuple[Dict[str, Tool], GovernedToolbox]:
    """Return ``tool_trajectory`` Tool objects backed by one governed toolbox.

    The returned toolbox is shared by every tool so callers can verify the forward-chain receipts after
    the trajectory run. Tool result strings stay compatible with the existing CALL/TOOL/ANSWER transcript.
    """

    box = box or GovernedToolbox()

    def make_tool(name: str, doc: str) -> Tool:
        return Tool(
            name=name,
            run=lambda arg, tool_name=name: box.call(tool_name, arg, problem=problem, public_k=public_k)["result"],
            doc=doc + " (governed + sealed)",
        )

    return (
        {
            "run_code": make_tool("run_code", "run the code block against the example test"),
            "calc": make_tool("calc", "evaluate arithmetic"),
            "is_prime": make_tool("is_prime", "primality test"),
            "factor": make_tool("factor", "prime factorization"),
        },
        box,
    )
