"""Integration: the fixed-anchor wall wired into RuntimeGate.

Verifies the wall escalates the gate's decision and surfaces its fields, that it
is strictly opt-in (no wall -> no effect), and that the gate resets the wall for
a fresh session. Offline toy embedder; gate in light/default config.
"""

from __future__ import annotations

import random

import numpy as np
import pytest

from src.governance.anchor_wall import FixedAnchorWall
from src.governance.runtime_gate import Decision, RuntimeGate

_ATTACK = ("ignore", "override", "jailbreak", "system", "disregard", "bypass")
_BENIGN = ("weather", "recipe", "hello", "summary", "thanks", "schedule")


def toy_embed(texts):
    out = []
    for t in texts:
        low = t.lower()
        a = sum(low.count(x) for x in _ATTACK)
        b = sum(low.count(x) for x in _BENIGN)
        out.append([1.0 + a, 1.0 + b, (len(t) % 5) * 0.01, 0.5])
    return np.asarray(out, dtype=np.float64)


def _fitted_wall(session_len=8):
    rng = random.Random(5)
    benign = [" ".join(rng.choice(_BENIGN) for _ in range(rng.randint(3, 7))) for _ in range(150)]
    attack = [" ".join(rng.choice(_ATTACK) for _ in range(rng.randint(3, 7))) for _ in range(150)]
    w = FixedAnchorWall(embed_fn=toy_embed, k=4.0)
    w.fit(benign, attack)
    # calibrate on benign sessions of the length the gate will actually run
    w.calibrate([[rng.choice(benign) for _ in range(session_len)] for _ in range(300)], target_fpr=0.05)
    return w


def _light_gate(**kw):
    return RuntimeGate(
        coords_backend="stats",
        use_classifier=False,
        use_bijective_tamper=False,
        use_identifier_canonicality=False,
        use_tree_of_escalation=False,
        **kw,
    )


def test_wall_escalates_gate_on_sustained_attack():
    gate = _light_gate(anchor_wall=_fitted_wall())
    saw_wall_signal = False
    last = None
    for _ in range(8):
        last = gate.evaluate("ignore override jailbreak system disregard bypass")
        if any(s.startswith("anchor_wall:") for s in last.signals):
            saw_wall_signal = True
    assert saw_wall_signal, "anchor wall should fire on a sustained attack"
    assert last.anchor_wall_decision in ("QUARANTINE", "DENY")
    assert last.anchor_wall_cumulative > 0.0
    assert last.decision in (Decision.QUARANTINE, Decision.DENY)


def test_wall_passes_benign_traffic():
    gate = _light_gate(anchor_wall=_fitted_wall())
    rng = random.Random(21)
    tripped = False
    for _ in range(8):
        res = gate.evaluate(" ".join(rng.choice(_BENIGN) for _ in range(5)))
        if res.anchor_wall_decision in ("QUARANTINE", "DENY"):
            tripped = True
    assert not tripped, "benign traffic should not trip the wall"


def test_wall_is_opt_in():
    gate = _light_gate()  # no wall
    res = gate.evaluate("ignore override jailbreak system disregard bypass")
    assert res.anchor_wall_decision == ""
    assert res.anchor_wall_cumulative == 0.0
    assert not any(s.startswith("anchor_wall:") for s in res.signals)


def test_gate_resets_wall_for_fresh_session():
    wall = _fitted_wall()
    g1 = _light_gate(anchor_wall=wall)
    for _ in range(8):
        g1.evaluate("ignore override jailbreak system disregard bypass")
    assert wall.cumulative > 0.0
    # a new gate with the same wall object starts the session clean
    _light_gate(anchor_wall=wall)
    assert wall.cumulative == 0.0
