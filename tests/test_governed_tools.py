"""governed_tools: the agent's deterministic tools, but gate-screened + sealed. These prove the value
the harvester's raw in-process tools lack: a destructive run_code is REFUSED before it executes (the
never-delete screen), benign work runs and is correct, and every call -- allowed or refused -- is sealed
into a tamper-evident chain, so a harvested tool-use trajectory is governed by construction.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.governed_tools import GovernedToolbox, demo, governed_callables  # noqa: E402
from python.helm.governed_tools import build_governed_tools  # noqa: E402
from python.helm.tool_trajectory import solve_with_tools  # noqa: E402

PROBLEM = {
    "task_id": 1,
    "text": "Write add(a, b) returning a + b.",
    "code": "def add(a, b):\n    return a + b\n",
    "test_list": ["assert add(1, 2) == 3", "assert add(0, 0) == 0", "assert add(-1, 1) == 0"],
    "test_imports": [],
}


def test_destructive_run_code_is_refused_before_running():
    box = GovernedToolbox()
    for snippet in (
        "import shutil\nshutil.rmtree('/x')",
        "import os\nos.remove('/x')",
        "def f():\n    pass  # rm -rf /",
    ):
        r = box.call("run_code", snippet, problem={"test_list": ["assert f() == 1"]})
        assert r["decision"] == "REFUSED" and r["result"].startswith("REFUSED"), snippet
    assert box.verify() is True  # the refusals are sealed too


def test_benign_run_code_passes_against_the_example_test():
    box = GovernedToolbox()
    r = box.call("run_code", "def add(a, b):\n    return a + b", problem={"test_list": ["assert add(2, 3) == 5"]})
    assert r["decision"] == "ALLOWED" and r["result"].startswith("PASS")


def test_wrong_run_code_fails_not_refused():
    box = GovernedToolbox()
    r = box.call("run_code", "def add(a, b):\n    return a - b", problem={"test_list": ["assert add(2, 3) == 5"]})
    assert r["decision"] == "ALLOWED" and r["result"].startswith("FAIL")


def test_numeric_tools_are_deterministic():
    box = GovernedToolbox()
    assert box.call("calc", "2 + 3 * 4")["result"] == "14"
    assert box.call("is_prime", "97")["result"] == "True"
    assert box.call("is_prime", "9")["result"] == "False"
    assert box.call("factor", "84")["result"] == "[2, 2, 3, 7]"


def test_calc_refuses_non_arithmetic():
    box = GovernedToolbox()
    assert box.call("calc", "__import__('os').system('echo hi')")["result"].startswith("calc error")


def test_every_call_is_sealed_and_tamper_evident():
    box = GovernedToolbox()
    box.call("calc", "1 + 1")
    box.call("is_prime", "13")
    assert box.verify() is True
    box.receipts[0]["result"] = "tampered"
    assert box.verify() is False


def test_governed_callables_are_a_drop_in_for_build_tools():
    problem = {"test_list": ["assert add(2, 3) == 5"]}
    tools, box = governed_callables(problem=problem)
    assert set(tools) == {"run_code", "calc", "is_prime", "factor"}
    assert tools["calc"]("2 + 3 * 4") == "14"  # callable(arg) -> str, the harvester's tool convention
    assert tools["run_code"]("def add(a, b):\n    return a + b").startswith("PASS")
    assert len(box.receipts) == 2 and box.verify() is True  # the shared box recorded + sealed both calls


def test_demo_refuses_destructive_and_seals():
    out = demo()
    assert out["destructive_refused"] is True
    assert out["benign_passed"] is True
    assert out["sealed"] is True


def test_helm_adapter_feeds_governed_tools_to_tool_trajectory():
    tools, box = build_governed_tools(PROBLEM)

    def ask(msgs):
        if not any(m["role"] == "user" and m["content"].startswith("TOOL run_code:") for m in msgs):
            return "```python\ndef add(a, b):\n    return a + b\n```\nCALL run_code"
        return "ANSWER:\n```python\ndef add(a, b):\n    return a + b\n```"

    tr = solve_with_tools(PROBLEM, ask, tools=tools, max_steps=4)

    assert tr["verified"] is True
    assert tr["used_tool"] is True
    assert box.verify() is True
    assert box.receipts[0]["tool"] == "run_code"
