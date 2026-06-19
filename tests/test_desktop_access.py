"""desktop_access: one governed action registry, surfaced through all three AI access points.

Every invocation goes through the allowlist (safe/guarded/denied) + a destructive-command screen
(never-delete, no confirm override) and emits a SHA-256 sealed receipt. The same action is
reachable as a verb (MCP), a DOM selector, and a numbered mark -- all generated off one definition.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.desktop_access import cube_moves, default_registry, play_cube  # noqa: E402


def test_verb_channel_governs_and_seals():
    reg = default_registry()
    assert len(reg.actions) == 7
    r = reg.invoke("open_app", {"app": "terminal"})
    assert r["decision"] == "ALLOWED"
    assert r["result"] == "opened terminal"
    assert reg.verify() is True  # receipt is sealed and intact


def test_denied_and_unknown_actions_are_refused():
    reg = default_registry()
    assert reg.invoke("shutdown", {})["decision"] == "DENIED"
    assert reg.invoke("nope", {})["decision"] == "NO_ACTION"


def test_guarded_action_needs_confirm():
    reg = default_registry()
    assert reg.invoke("run_allowed_command", {"command": "ls"})["decision"] == "NEEDS_CONFIRM"
    ok = reg.invoke("run_allowed_command", {"command": "ls"}, confirm="user asked")
    assert ok["decision"] == "ALLOWED"
    assert ok["result"] == "ran: ls"


def test_destructive_command_blocked_even_with_confirm():
    reg = default_registry()
    r = reg.invoke("run_allowed_command", {"command": "rm -rf /"}, confirm="please")
    assert r["decision"] == "REFUSED"  # the never-delete screen; confirm cannot override
    assert "destructive" in r["result"]


def test_tampering_with_a_receipt_is_detected():
    reg = default_registry()
    reg.invoke("open_app", {"app": "files"})
    reg.transcript[0]["result"] = "tampered"
    assert reg.verify() is False  # sealed receipts are tamper-evident


def test_all_three_access_points_cover_the_same_actions():
    reg = default_registry()
    names = set(reg.actions)
    # 1. verb / MCP -- excludes the denied action, well-formed schema
    tools = {t["name"] for t in reg.mcp_tools()}
    assert tools == names - {"shutdown"}
    assert all("inputSchema" in t for t in reg.mcp_tools())
    # 2. DOM manifest -- every action has a selector + role + label
    dom = reg.dom_manifest()
    assert set(dom) == names
    assert all(d["selector"] and d["role"] and d["label"] for d in dom.values())
    # 3. set-of-marks -- numbered 1..N, one per action
    marks = reg.set_of_marks()
    assert [m["mark"] for m in marks] == list(range(1, len(names) + 1))
    assert {m["action"] for m in marks} == names


def test_one_action_reachable_all_three_ways():
    ap = default_registry().access_points("open_app")
    assert ap["verb"]["call"] == "open_app"
    assert ap["dom"]["selector"] == "[data-app]"
    assert ap["pixels"]["mark"] == 2  # the same action, three coordinates


def test_cube_controller_plays_governed_desktop_actions():
    reg = default_registry()
    assert cube_moves()["R"] == "open_app"  # a face-turn selects a desktop action
    r = play_cube(reg, "U R F", confirm="cube turn")  # safe navigation actions
    assert [h["decision"] for h in r["hops"]] == ["ALLOWED", "ALLOWED", "ALLOWED"]
    assert r["route"] == "U:list_apps -> R:open_app -> F:list_windows"
    assert r["sealed"] is True  # every cube-driven action is sealed


def test_cube_controller_still_obeys_governance():
    reg = default_registry()
    # a guarded action selected by the cube still needs confirm (governance is not bypassed)
    assert play_cube(reg, "B")["hops"][0]["decision"] == "NEEDS_CONFIRM"
    # an unknown face is rejected
    assert play_cube(reg, "Z")["hops"][0]["decision"] == "UNKNOWN_MOVE"
