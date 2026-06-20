"""aether_desk: the governed bounded workspace (AetherDesk v0). These prove the keystone claim --
an agent can do REAL local work (write, run, test) inside a workspace and produce a sealed receipt,
but CANNOT escape it (a path or command outside the root is REFUSED), and the never-delete screen still
fires. SCBE is the law; this is the jurisdiction.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.aether_desk import AetherDesk, demo  # noqa: E402


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
