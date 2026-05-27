"""Persistence tests for RuntimeGate.save_state / load_state.

Contract:
  1. round-trip preserves the decision path for a novel probe (same config)
  2. _immune persists; _reflex is rebuilt empty (not a stale bypass)
  3. centroid=None (fresh gate) round-trips
  4. config drift warns (never refuses) and surfaces a signal in the next
     evaluate(); the signal appears exactly once
  5. same config => no warning, no drift signal
  6. atomic write leaves no .tmp and a schema-tagged JSON
  7. missing / empty / corrupted / wrong-schema files raise cleanly
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.governance.runtime_gate import Decision, RuntimeGate  # noqa: E402

# Benign warm-up traffic (stats backend, dependency-free, deterministic).
WARMUP = (
    "read the project README file",
    "list the files in the docs folder",
    "open the changelog and show recent entries",
    "summarize the contents of the config directory",
    "count the test files under the tests folder",
    "show the table of contents for the manual",
    "describe the layout of the source tree",
    "report the size of the build output",
)
PROBE = "summarize the meeting notes from yesterday afternoon"


def _warm(gate: RuntimeGate) -> None:
    for text in WARMUP:
        gate.evaluate(text)


# --------------------------------------------------------------------------- #
#  1. round-trip preserves the decision path
# --------------------------------------------------------------------------- #


def test_round_trip_preserves_decision_for_novel_probe(tmp_path):
    a = RuntimeGate()
    _warm(a)
    state_file = tmp_path / "gate.json"
    a.save_state(state_file)

    b = RuntimeGate()
    b.load_state(state_file)

    # State scalars are restored exactly.
    assert b._query_count == a._query_count
    assert b._centroid_count == a._centroid_count
    assert b._cumulative_cost == pytest.approx(a._cumulative_cost)
    assert b._trust_history == a._trust_history
    assert b._centroid.tolist() == pytest.approx(a._centroid.tolist())

    # A novel probe (not in A's reflex) takes the full path on both → identical.
    ra = a.evaluate(PROBE)
    rb = b.evaluate(PROBE)
    assert ra.decision == rb.decision
    assert ra.spin_magnitude == rb.spin_magnitude
    assert ra.trust_level == rb.trust_level
    assert ra.cost == pytest.approx(rb.cost)
    assert ra.tongue_coords == pytest.approx(rb.tongue_coords)


# --------------------------------------------------------------------------- #
#  2. immune persists; reflex is rebuilt empty
# --------------------------------------------------------------------------- #


def test_immune_persists_reflex_does_not(tmp_path):
    a = RuntimeGate()
    _warm(a)
    a._immune.add("deadbeefcafef00d")
    a._reflex["abc123previouslyallowed"] = True
    assert a._reflex  # A has a warmed reflex cache

    state_file = tmp_path / "gate.json"
    a.save_state(state_file)

    b = RuntimeGate()
    b.load_state(state_file)

    assert "deadbeefcafef00d" in b._immune  # attack memory survives
    assert b._reflex == {}  # fast-path cache rebuilt empty, no stale bypass

    # The snapshot self-documents what it intentionally drops.
    snapshot = json.loads(state_file.read_text(encoding="utf-8"))
    assert "reflex" in snapshot["derived_not_persisted"]


# --------------------------------------------------------------------------- #
#  3. fresh gate (centroid None) round-trips
# --------------------------------------------------------------------------- #


def test_fresh_gate_centroid_none_round_trips(tmp_path):
    a = RuntimeGate()
    assert a._centroid is None
    state_file = tmp_path / "fresh.json"
    a.save_state(state_file)

    b = RuntimeGate()
    b.load_state(state_file)
    assert b._centroid is None
    assert b._query_count == 0
    assert b._immune == set()


# --------------------------------------------------------------------------- #
#  4. config drift warns + surfaces a signal exactly once
# --------------------------------------------------------------------------- #


def test_config_drift_warns_and_signals_once(tmp_path):
    a = RuntimeGate(cost_deny=200.0)
    _warm(a)
    state_file = tmp_path / "gate.json"
    a.save_state(state_file)

    b = RuntimeGate(cost_deny=999.0)  # drifted threshold
    with pytest.warns(RuntimeWarning, match="different config"):
        b.load_state(state_file)

    first = b.evaluate(PROBE)
    assert any(s.startswith("state_loaded_config_drift") for s in first.signals)
    assert any("cost_deny" in s for s in first.signals if s.startswith("state_loaded_config_drift"))

    # The warning is consumed — it does not repeat on the next action.
    second = b.evaluate("another unrelated benign request")
    assert not any(s.startswith("state_loaded_config_drift") for s in second.signals)


def test_backend_drift_is_detected(tmp_path):
    a = RuntimeGate(coords_backend="stats")
    _warm(a)
    state_file = tmp_path / "gate.json"
    a.save_state(state_file)

    b = RuntimeGate(coords_backend="semantic")
    with pytest.warns(RuntimeWarning):
        b.load_state(state_file)
    result = b.evaluate(PROBE)
    drift = [s for s in result.signals if s.startswith("state_loaded_config_drift")]
    assert drift and "coords_backend" in drift[0]


# --------------------------------------------------------------------------- #
#  5. same config => no warning, no drift signal
# --------------------------------------------------------------------------- #


def test_same_config_no_warning(tmp_path):
    a = RuntimeGate()
    _warm(a)
    state_file = tmp_path / "gate.json"
    a.save_state(state_file)

    b = RuntimeGate()
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # any warning fails the test
        b.load_state(state_file)

    result = b.evaluate(PROBE)
    assert not any(s.startswith("state_loaded_config_drift") for s in result.signals)


# --------------------------------------------------------------------------- #
#  6. atomic write hygiene
# --------------------------------------------------------------------------- #


def test_atomic_write_leaves_no_tmp(tmp_path):
    gate = RuntimeGate()
    _warm(gate)
    state_file = tmp_path / "nested" / "dir" / "gate.json"
    gate.save_state(state_file)

    assert state_file.exists()
    assert not (state_file.parent / "gate.json.tmp").exists()
    assert list(state_file.parent.glob("*.tmp")) == []

    snapshot = json.loads(state_file.read_text(encoding="utf-8"))
    assert snapshot["schema"] == RuntimeGate.STATE_SCHEMA
    assert "immune" in snapshot["state"]


# --------------------------------------------------------------------------- #
#  7. bad inputs raise cleanly
# --------------------------------------------------------------------------- #


def test_missing_file_raises_filenotfound(tmp_path):
    gate = RuntimeGate()
    with pytest.raises(FileNotFoundError):
        gate.load_state(tmp_path / "does-not-exist.json")


def test_empty_file_raises_valueerror(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    gate = RuntimeGate()
    with pytest.raises(ValueError, match="empty"):
        gate.load_state(p)


def test_corrupted_json_raises_valueerror(tmp_path):
    p = tmp_path / "corrupt.json"
    p.write_text("{not valid json at all", encoding="utf-8")
    gate = RuntimeGate()
    with pytest.raises(ValueError, match="corrupted"):
        gate.load_state(p)


def test_wrong_schema_raises_valueerror(tmp_path):
    p = tmp_path / "wrong.json"
    p.write_text(json.dumps({"schema": "something-else/v9", "state": {}}), encoding="utf-8")
    gate = RuntimeGate()
    with pytest.raises(ValueError, match="unrecognized"):
        gate.load_state(p)


def test_decision_enum_importable():
    # Guards the import surface the persistence tests rely on.
    assert Decision.ALLOW.value == "ALLOW"
