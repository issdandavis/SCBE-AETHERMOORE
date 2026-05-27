"""Wiring tests for RuntimeGate autosave/checkpoint plumbing in the API server.

These exercise the server-side helpers (not the gate methods directly):

  1. periodic checkpoint fires every Nth evaluate(), and a cold restart through
     _get_gate() continues _query_count / centroid / trust_history / immune while
     _reflex does NOT persist  -> the user's literal acceptance test
  2. a checkpoint rotates the prior snapshot to <name>.prev (rollback fallback)
  3. the new-gate path resets the eval counter
  4. the shutdown hook persists (and rotates) when configured
  5. no state path  -> evaluate() still works, nothing is written
  6. the manual checkpoint endpoint fails closed without an admin token,
     401s on a bad token, and returns {ok, path, query_count} with the right one
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (REPO_ROOT, REPO_ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

WARMUP = (
    "read the project README file",
    "list the files in the docs folder",
    "open the changelog and show recent entries",
    "summarize the contents of the config directory",
    "count the test files under the tests folder",
    "show the table of contents for the manual",
)


def _load_server():
    path = (REPO_ROOT / "scripts" / "aetherbrowser" / "api_server.py").resolve()
    spec = importlib.util.spec_from_file_location("aether_api_server_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def server():
    return _load_server()


@pytest.fixture
def srv(server, monkeypatch):
    server._runtime_gate = None
    server._gate_eval_counter = 0
    monkeypatch.setenv("SCBE_COORDS_BACKEND", "stats")  # dependency-free backend
    monkeypatch.delenv("SCBE_RUNTIME_GATE_STATE_PATH", raising=False)
    monkeypatch.delenv("SCBE_RUNTIME_GATE_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("SCBE_RUNTIME_GATE_CHECKPOINT_EVERY", raising=False)
    yield server
    server._runtime_gate = None
    server._gate_eval_counter = 0


# --------------------------------------------------------------------------- #
#  1. periodic checkpoint + cold-restart continuity (the acceptance test)
# --------------------------------------------------------------------------- #


def test_periodic_checkpoint_survives_restart(srv, monkeypatch, tmp_path):
    state = tmp_path / "gate" / "state.json"
    monkeypatch.setenv("SCBE_RUNTIME_GATE_STATE_PATH", str(state))
    monkeypatch.setenv("SCBE_RUNTIME_GATE_CHECKPOINT_EVERY", "3")

    gate = srv._get_gate()
    assert gate is not None

    # 3 evaluations -> exactly one periodic checkpoint.
    for text in WARMUP[:3]:
        srv._gate_evaluate(gate, text)
    assert state.exists()
    assert srv._gate_eval_counter == 0  # reset after firing

    # Plant learned attack memory + a fast-path reflex entry, then a 2nd save.
    gate._immune.add("feedfacecafe0000")
    gate._reflex["should_not_persist"] = True
    for text in WARMUP[3:6]:
        srv._gate_evaluate(gate, text)

    assert state.with_name(state.name + ".prev").exists()  # rollback snapshot

    q_before = gate._query_count
    trust_before = list(gate._trust_history)
    centroid_before = gate._centroid.tolist()
    assert q_before == 6

    # Cold restart: drop the singleton, dirty the counter, rebuild from disk.
    srv._runtime_gate = None
    srv._gate_eval_counter = 99
    gate2 = srv._get_gate()

    assert gate2 is not gate
    assert srv._gate_eval_counter == 0  # rebuilding resets the counter
    assert gate2._query_count == q_before  # drift trajectory continued
    assert gate2._trust_history == trust_before
    assert gate2._centroid.tolist() == pytest.approx(centroid_before)
    assert "feedfacecafe0000" in gate2._immune  # immune memory continued
    assert gate2._reflex == {}  # reflex did NOT persist (no stale bypass)


# --------------------------------------------------------------------------- #
#  4. shutdown hook persists + rotates
# --------------------------------------------------------------------------- #


def test_shutdown_hook_persists_and_rotates(srv, monkeypatch, tmp_path):
    state = tmp_path / "state.json"
    monkeypatch.setenv("SCBE_RUNTIME_GATE_STATE_PATH", str(state))
    monkeypatch.setenv("SCBE_RUNTIME_GATE_CHECKPOINT_EVERY", "0")  # periodic OFF

    gate = srv._get_gate()
    for text in WARMUP[:4]:
        srv._gate_evaluate(gate, text)
    assert not state.exists()  # periodic disabled -> nothing yet

    asyncio.run(srv._save_gate_state_on_shutdown())
    assert state.exists()
    assert not state.with_name(state.name + ".prev").exists()  # first save, no prior

    asyncio.run(srv._save_gate_state_on_shutdown())
    assert state.with_name(state.name + ".prev").exists()  # rotation on 2nd save


# --------------------------------------------------------------------------- #
#  5. no state path -> evaluate works, nothing written
# --------------------------------------------------------------------------- #


def test_no_state_path_is_noop(srv, tmp_path):
    gate = srv._get_gate()
    for text in WARMUP:
        result = srv._gate_evaluate(gate, text)
        assert result.decision is not None
    assert srv._persist_gate_state(keep_previous=True) is False
    assert list(tmp_path.iterdir()) == []


# --------------------------------------------------------------------------- #
#  6. manual checkpoint endpoint is admin-guarded and fails closed
# --------------------------------------------------------------------------- #


def _req(token: str | None):
    headers = {} if token is None else {"x-admin-token": token}
    return SimpleNamespace(headers=headers)


def test_checkpoint_endpoint_disabled_without_token(srv, monkeypatch, tmp_path):
    monkeypatch.setenv("SCBE_RUNTIME_GATE_STATE_PATH", str(tmp_path / "s.json"))
    with pytest.raises(srv.HTTPException) as exc:
        asyncio.run(srv.runtime_gate_checkpoint(_req(None)))
    assert exc.value.status_code == 403


def test_checkpoint_endpoint_rejects_bad_token(srv, monkeypatch, tmp_path):
    monkeypatch.setenv("SCBE_RUNTIME_GATE_STATE_PATH", str(tmp_path / "s.json"))
    monkeypatch.setenv("SCBE_RUNTIME_GATE_ADMIN_TOKEN", "correct-horse")
    with pytest.raises(srv.HTTPException) as exc:
        asyncio.run(srv.runtime_gate_checkpoint(_req("wrong")))
    assert exc.value.status_code == 401


def test_checkpoint_endpoint_saves_with_valid_token(srv, monkeypatch, tmp_path):
    state = tmp_path / "s.json"
    monkeypatch.setenv("SCBE_RUNTIME_GATE_STATE_PATH", str(state))
    monkeypatch.setenv("SCBE_RUNTIME_GATE_ADMIN_TOKEN", "correct-horse")

    gate = srv._get_gate()
    srv._gate_evaluate(gate, WARMUP[0])

    body = asyncio.run(srv.runtime_gate_checkpoint(_req("correct-horse")))
    assert body["ok"] is True
    assert body["path"] == str(state)
    assert body["query_count"] == gate._query_count
    assert state.exists()
