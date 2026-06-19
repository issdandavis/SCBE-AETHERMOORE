"""context_ledger: a command-driven self-context ledger + deterministic packer for AIs.

The AI keeps working memory by RUNNING COMMANDS (it is better at commands than prose); pack()
forwards the attention-heavy items, drops the cleared/stale, and rewrites the survivors in a fixed
reversible shorthand. Every command is sealed (tamper-evident). Pure, deterministic, no network.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.context_ledger import Ledger, expand, shorten  # noqa: E402


def test_commands_drive_the_memory():
    led = Ledger("a7")
    assert led.run("set goal sum-loop")["result"] == "goal=sum-loop"
    assert led.run("get goal") == {"ok": True, "result": "sum-loop"}
    assert led.run("get nope")["ok"] is False
    assert led.run("todo write-loop")["ok"] is True
    led.run("todo verify")
    assert led.run("done write-loop")["result"] == "done: write-loop"
    rc = led.run("recall")["result"]
    assert "goal=sum-loop" in rc and "verify" in rc


def test_unknown_command_is_rejected():
    assert Ledger().run("frobnicate x")["ok"] is False


def test_pack_forwards_heavy_drops_cleared_and_shorthands():
    led = Ledger("a7")
    led.run("set goal sum-loop")
    led.run("todo verify")
    led.run("todo write-loop")
    led.run("done write-loop")  # cleared -> should be dropped by pack
    led.run("note loop emits 15")
    p = led.pack()
    assert "write-loop" in p["dropped"]  # the cleared todo is dropped
    assert p["kept"]["open_todos"] == ["verify"]  # the open one is forwarded
    assert "goal" in p["kept"]["kv"]  # anchor fact kept
    assert p["chars_after"] <= p["chars_before"]  # shorthand never grows
    assert p["ratio"] <= 1.0


def test_pack_command_compacts_in_place():
    led = Ledger()
    led.run("todo a")
    led.run("done a")
    led.run("pack")  # the command packs with compact=True
    assert led.done_todos == []  # cleared todos removed from the ledger


def test_shorthand_is_reversible():
    assert expand(shorten("goal write loop verify test")) == "goal write loop verify test"
    assert shorten("loop") == "lp" and expand("lp") == "loop"


def test_event_log_is_sealed_and_tamper_evident():
    led = Ledger()
    led.run("set k v")
    assert led.verify() is True
    led.events[0]["result"] = "tampered"
    assert led.verify() is False


def test_ledger_persists_for_next_session():
    led = Ledger("a7")
    led.run("set goal g")
    led.run("todo t")
    back = Ledger.from_json(led.to_json())
    assert back.kv == {"goal": "g"}
    assert back.open_todos == ["t"]
    assert back.verify() is True
