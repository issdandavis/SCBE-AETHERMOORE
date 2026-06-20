"""Offline tests for tool_trajectory (no model, no network).

Proves the ReAct loop, the deterministic tools, and -- the load-bearing part -- that acceptance is on
HELD-BACK tests (the shown example can't earn a 'solve'), so a model that only satisfies the visible test
is NOT counted as verified tool use.
"""

from __future__ import annotations

from python.helm.tool_trajectory import (
    _factor,
    _is_prime,
    _safe_calc,
    build_tools,
    harvest_tool_traces,
    parse_turn,
    reference_tool_solver,
    solve_with_tools,
)

PROBLEM = {
    "task_id": 1,
    "text": "Write add(a, b) returning a + b.",
    "code": "def add(a, b):\n    return a + b\n",
    "test_list": ["assert add(1, 2) == 3", "assert add(0, 0) == 0", "assert add(-1, 1) == 0"],
    "test_imports": [],
}


# ---- tools ------------------------------------------------------------------------------------
def test_tools_compute():
    assert _safe_calc("2 + 3 * 4") == "14"
    assert _safe_calc("__import__('os')").startswith("calc error")  # no names/calls allowed
    assert _is_prime("7") == "True" and _is_prime("8") == "False"
    assert _factor("12") == "[2, 2, 3]"


def test_run_code_tool_passes_and_fails():
    tools = build_tools(PROBLEM, public_k=1)
    assert tools["run_code"].run("def add(a, b):\n    return a + b\n").startswith("PASS")
    assert tools["run_code"].run("def add(a, b):\n    return 0\n").startswith("FAIL")


# ---- parsing ----------------------------------------------------------------------------------
def test_parse_turn():
    assert parse_turn("ANSWER:\n```python\ndef f():\n    return 1\n```")["kind"] == "answer"
    callt = parse_turn("```python\ndef f():\n    return 1\n```\nCALL run_code")
    assert callt["kind"] == "call" and callt["tool"] == "run_code" and "def f" in callt["arg"]
    assert parse_turn("CALL calc: 6 % 3") == {"kind": "call", "tool": "calc", "arg": "6 % 3"}
    assert parse_turn("hmm let me think")["kind"] == "none"


# ---- the loop + held-back verification --------------------------------------------------------
def test_solve_with_tools_records_verified_trajectory():
    tr = solve_with_tools(PROBLEM, reference_tool_solver(PROBLEM), max_steps=4)
    assert tr["verified"] is True
    assert tr["used_tool"] is True and "run_code" in tr["tools_used"]
    # the transcript contains a tool RESULT turn -> SFT teaches call->use->answer, not just the answer
    assert any(m["role"] == "user" and m["content"].startswith("TOOL run_code:") for m in tr["messages"])


def test_repair_biased_prompt_mode_adds_feedback_loop_instruction():
    seen = {}

    def ask(msgs):
        seen["system"] = msgs[0]["content"]
        seen["user"] = msgs[-1]["content"]
        return "ANSWER:\n```python\ndef add(a, b):\n    return a + b\n```"

    tr = solve_with_tools(PROBLEM, ask, max_steps=1, prompt_mode="repair-biased", few_shot=False)
    assert tr["verified"] is True
    assert "Repair-biased harvest mode" in seen["system"]
    assert "quick minimal candidate" in seen["user"]


def test_held_back_rejects_shown_test_only_pass():
    # a solver that returns code passing ONLY the shown example (add(1,2)==3) but wrong otherwise
    def cheat_ask(_msgs):
        return "ANSWER:\n```python\ndef add(a, b):\n    return 3\n```"

    tr = solve_with_tools(PROBLEM, cheat_ask, max_steps=2, public_k=1)
    assert tr["final_code"]  # it answered
    assert tr["verified"] is False  # but held-back tests (add(0,0)==0) fail -> not a solve


# ---- harvest ----------------------------------------------------------------------------------
def test_harvest_keeps_verified_tooluse_only():
    res = harvest_tool_traces([PROBLEM], reference_tool_solver(PROBLEM), max_steps=4)
    assert res["verified"] == 1 and res["with_tool_use"] == 1
    rec = res["records"][0]
    assert rec["meta"]["verified"] is True and rec["meta"]["tool_calls"] >= 1
    assert rec["meta"]["source"] == "tool_trajectory"
    assert rec["meta"]["prompt_mode"] == "confirm"


def test_harvest_accepts_repair_biased_prompt_mode():
    res = harvest_tool_traces([PROBLEM], reference_tool_solver(PROBLEM), max_steps=4, prompt_mode="repair-biased")
    assert res["verified"] == 1 and res["with_tool_use"] == 1
    assert res["records"][0]["meta"]["prompt_mode"] == "repair-biased"


def test_harvest_drops_no_tool_use_when_required():
    # answers correctly but NEVER calls a tool -> dropped when require_tool_use=True (default)
    def straight_ask(_msgs):
        return "ANSWER:\n```python\ndef add(a, b):\n    return a + b\n```"

    req = harvest_tool_traces([PROBLEM], straight_ask, max_steps=2)
    assert req["verified"] == 0 and req["with_tool_use"] == 0
    # but kept when tool use is not required (it's still a verified solve)
    loose = harvest_tool_traces([PROBLEM], straight_ask, max_steps=2, require_tool_use=False)
    assert loose["verified"] == 1
