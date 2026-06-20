from __future__ import annotations

import json

from python.helm.governed_tools import ToolGovernanceLedger, build_governed_tools
from python.helm.tool_trajectory import Tool, solve_with_tools

PROBLEM = {
    "task_id": 1,
    "text": "Write add(a, b) returning a + b.",
    "code": "def add(a, b):\n    return a + b\n",
    "test_list": ["assert add(1, 2) == 3", "assert add(0, 0) == 0", "assert add(-1, 1) == 0"],
    "test_imports": [],
}


def _governance_payload(result: str) -> dict:
    first = result.splitlines()[0]
    assert first.startswith("GOVERNANCE ")
    return json.loads(first.removeprefix("GOVERNANCE "))


def test_governed_tool_allows_and_seals_run_code_result():
    ledger = ToolGovernanceLedger()
    tools = build_governed_tools(PROBLEM, ledger=ledger)

    result = tools["run_code"].run("def add(a, b):\n    return a + b\n")

    receipt = _governance_payload(result)
    assert receipt["schema"] == "scbe_tool_governance_v0"
    assert receipt["tool"] == "run_code"
    assert receipt["decision"] == "ALLOWED"
    assert "PASS" in result
    assert ledger.verify() is True


def test_governed_tool_refuses_destructive_code_before_underlying_tool_runs():
    ledger = ToolGovernanceLedger()
    called = {"value": False}

    def dangerous_underlying(_arg: str) -> str:
        called["value"] = True
        return "SHOULD NOT RUN"

    tools = build_governed_tools(
        PROBLEM,
        ledger=ledger,
        base_tools={"run_code": Tool("run_code", dangerous_underlying, "test run_code")},
    )

    result = tools["run_code"].run("import os\nos.remove('important.txt')\n")

    receipt = _governance_payload(result)
    assert receipt["decision"] == "REFUSED"
    assert "DENIED" in result
    assert called["value"] is False
    assert ledger.verify() is True


def test_solve_with_tools_can_use_governed_registry_without_record_shape_change():
    ledger = ToolGovernanceLedger()
    tools = build_governed_tools(PROBLEM, ledger=ledger)

    def ask(msgs):
        if not any(m["role"] == "user" and m["content"].startswith("TOOL run_code:") for m in msgs):
            return "```python\ndef add(a, b):\n    return a + b\n```\nCALL run_code"
        return "ANSWER:\n```python\ndef add(a, b):\n    return a + b\n```"

    tr = solve_with_tools(PROBLEM, ask, tools=tools, max_steps=4, few_shot=False)

    assert tr["verified"] is True
    assert tr["used_tool"] is True
    tool_turn = next(m for m in tr["messages"] if m["role"] == "user" and m["content"].startswith("TOOL run_code:"))
    assert "GOVERNANCE " in tool_turn["content"]
    assert ledger.verify() is True
