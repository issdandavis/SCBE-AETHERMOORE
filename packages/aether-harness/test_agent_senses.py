"""Tests for the governed agent senses (see / act / remember / recall).

Each sense must (1) do its job and (2) carry a GeoSeal receipt, proving the
call passed through the governance seam. State is redirected to a temp dir so
the suite never touches the real .scbe ledger.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


@pytest.fixture()
def senses(tmp_path, monkeypatch):
    mod = importlib.import_module("agent_senses")
    state = tmp_path / "senses"
    monkeypatch.setattr(mod, "_STATE_DIR", state)
    monkeypatch.setattr(mod, "_WORLD_PATH", state / "world.json")
    monkeypatch.setattr(mod, "_MEMORY_PATH", state / "memory.json")
    # receipts to a temp ledger too
    seam = mod.GovernanceSeam(receipts_path=tmp_path / "receipts.jsonl")
    return mod.AgentSenses(seam=seam)


def _has_receipt(result: dict) -> bool:
    return "receipt" in result and result["receipt"].get("decision") in {
        "ALLOW",
        "REVIEW",
        "QUARANTINE",
        "ESCALATE",
        "DENY",
    }


def test_look_sees_a_world(senses):
    out = senses.look()
    assert out["ok"]
    assert isinstance(out["grid"], list) and out["grid"], "should render a non-empty board"
    assert out["entities"], "should see at least one movable entity"
    assert _has_receipt(out), "every perception is receipted"


def test_act_moves_an_entity(senses):
    before = senses.look()
    eid = next(iter(before["entities"]))
    x0 = before["entities"][eid]["x"]
    out = senses.act(eid, 1, 0)
    assert _has_receipt(out)
    after = senses.look()
    # either it moved one east, or terrain blocked it (both are honest outcomes)
    assert after["entities"][eid]["x"] in (x0, x0 + 1)
    if out["moved"]:
        assert after["entities"][eid]["x"] == x0 + 1


def test_act_on_unknown_entity_fails_cleanly(senses):
    out = senses.act("no_such_entity", 1, 0)
    assert out["ok"] is False
    assert _has_receipt(out), "even a failed action is governed + receipted"


def test_remember_then_recall_roundtrips(senses):
    senses.remember("river", "a band of water cuts across the middle of the map")
    senses.remember("goal", "the treasure chest sits in the far north-east corner")
    out = senses.recall("where is the treasure", k=2)
    assert out["ok"] and _has_receipt(out)
    keys = [m["key"] for m in out["matches"]]
    assert "goal" in keys, "semantic recall should surface the treasure note"
    # the closest match should be the treasure note, not the river
    assert out["matches"][0]["key"] == "goal"


def test_memory_persists_across_instances(senses, tmp_path, monkeypatch):
    senses.remember("note", "the hero walked east along the second row")
    mod = importlib.import_module("agent_senses")
    seam2 = mod.GovernanceSeam(receipts_path=tmp_path / "receipts.jsonl")
    fresh = mod.AgentSenses(seam=seam2)  # reloads from disk
    out = fresh.recall("which way did the hero go", k=1)
    assert out["matches"] and out["matches"][0]["key"] == "note"


def test_embed_is_deterministic():
    mod = importlib.import_module("agent_senses")
    a = mod.embed_text("the quick brown fox")
    b = mod.embed_text("the quick brown fox")
    assert (a == b).all(), "same text must embed identically across calls"
