"""aether_desk: the governed bounded workspace (AetherDesk v0). These prove the keystone claim --
an agent can do REAL local work (write, run, test) inside a workspace and produce a sealed receipt,
but CANNOT escape it (a path or command outside the root is REFUSED), and the never-delete screen still
fires. SCBE is the law; this is the jurisdiction.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.aether_desk import AetherDesk, block_solver, demo, model_solver  # noqa: E402


def test_real_work_inside_the_workspace_is_allowed(tmp_path):
    desk = AetherDesk.open(tmp_path / "ws")
    assert desk.act("write_file", {"path": "a/b.txt", "content": "hi"}, confirm="task")["decision"] == "ALLOWED"
    assert desk.act("read_file", {"path": "a/b.txt"})["decision"] == "ALLOWED"
    assert desk.act("read_file", {"path": "a/b.txt"})["result"] == "hi"
    assert desk.act("list_files", {})["decision"] == "ALLOWED"


def test_agent_cannot_escape_the_workspace(tmp_path):
    desk = AetherDesk.open(tmp_path / "ws")
    # relative traversal out, and an absolute path outside the root -> REFUSED as an escape
    for bad in ("../escaped.txt", "a/../../escaped.txt", str(tmp_path / "sibling.txt")):
        r = desk.act("write_file", {"path": bad, "content": "x"}, confirm="malicious")
        assert r["decision"] == "REFUSED" and "escape blocked" in r["result"], bad
    # the escapes did not write anything outside the workspace
    assert not (tmp_path / "escaped.txt").exists() and not (tmp_path / "sibling.txt").exists()


def test_never_delete_still_fires_inside(tmp_path):
    desk = AetherDesk.open(tmp_path / "ws")
    r = desk.act("run_command", {"command": "rm -rf /"}, confirm="please")
    assert r["decision"] == "REFUSED" and "destructive" in r["result"]


def test_run_command_uses_allowlisted_argv_not_shell_chaining(tmp_path):
    desk = AetherDesk.open(tmp_path / "ws")
    ok = desk.act("run_command", {"command": "python --version"}, confirm="task")
    assert ok["decision"] == "ALLOWED"
    assert "Python" in ok["result"]

    chained = desk.act("run_command", {"command": "echo hello; echo smuggled"}, confirm="task")
    assert chained["decision"] == "REFUSED"
    assert "chaining" in chained["result"]


def test_guarded_actions_need_confirm(tmp_path):
    desk = AetherDesk.open(tmp_path / "ws")
    assert desk.act("write_file", {"path": "x.txt", "content": "y"})["decision"] == "NEEDS_CONFIRM"
    assert desk.act("read_file", {"path": "x.txt"})["decision"] == "ALLOWED"  # reads are safe


def test_receipt_is_sealed_and_tamper_evident(tmp_path):
    desk = AetherDesk.open(tmp_path / "ws")
    desk.act("write_file", {"path": "x.txt", "content": "1"}, confirm="t")
    desk.act("escape_attempt_outside", {"path": "../e"}, confirm="m")  # unknown action + escape -> still sealed
    assert desk.verify() is True
    desk.receipt()[0]["result"] = "tampered"
    assert desk.verify() is False


def test_demo_does_real_work_and_blocks_escape(tmp_path):
    out = demo(tmp_path / "demo")
    assert out["fix_verified"] is True  # the agent fixed the bug and the test passed (real execution)
    assert out["receipt_sealed"] is True
    decisions = [s["decision"] for s in out["steps"]]
    assert decisions.count("ALLOWED") >= 6  # the real-work steps
    assert decisions.count("REFUSED") == 3  # the three escape attempts


# --- the routed-step execution substrate (the router's plan, made runnable + governed) --------------


def test_run_step_verifies_a_block_solver(tmp_path):
    desk = AetherDesk.open(tmp_path / "ws")
    # a known-hard step routed to a DETERMINISTIC block (proven code) -> verified, sealed
    r = desk.run_step(
        "add", "add two numbers", ["assert add(2, 3) == 5"], block_solver("def add(a, b):\n    return a + b"), "block"
    )
    assert r["verified"] is True and r["solver"] == "block"
    assert desk.verify() is True


def test_run_step_records_a_wrong_solver_as_failed_not_hidden(tmp_path):
    desk = AetherDesk.open(tmp_path / "ws")
    r = desk.run_step(
        "add",
        "add two numbers",
        ["assert add(2, 3) == 5"],
        block_solver("def add(a, b):\n    return a - b"),
        "bad_block",
    )
    assert r["verified"] is False  # wrong code is caught by execution, not hidden
    assert desk.receipt()[-1]["decision"] == "FAILED" and desk.verify() is True


def test_model_solver_strips_fences(tmp_path):
    desk = AetherDesk.open(tmp_path / "ws")
    ask = lambda spec: "Here you go:\n```python\ndef mul(a, b):\n    return a * b\n```"  # noqa: E731
    r = desk.run_step("mul", "multiply", ["assert mul(2, 3) == 6"], model_solver(ask), "model")
    assert r["verified"] is True


def test_run_pipeline_routes_each_step_and_seals(tmp_path):
    desk = AetherDesk.open(tmp_path / "ws")
    steps = [
        {
            "name": "add",
            "spec": "add",
            "check": ["assert add(2, 3) == 5"],
            "solver": block_solver("def add(a, b):\n    return a + b"),
            "solver_name": "block",
        },
        {
            "name": "mul",
            "spec": "mul",
            "check": ["assert mul(2, 3) == 6"],
            "solver": model_solver(lambda s: "def mul(a, b):\n    return a * b"),
            "solver_name": "model",
        },
    ]
    out = desk.run_pipeline(steps)
    assert out["all_verified"] is True and out["sealed"] is True
    assert [s["solver"] for s in out["steps"]] == ["block", "model"]  # the router's assignment is recorded
