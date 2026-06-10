"""Tests for the fixed-anchor enforcement wall.

Uses a deterministic toy embedder (no model download, offline) so the wall's
LOGIC is verified: fixed anchors, exponential approach cost, calibrated
threshold matched to session length, cumulative session enforcement, and
held-out separation. The real-corpus numbers live in
experiments/fixed_anchor_wall.py (cumulative-cost AUC 0.999, 99% intruders
stopped, 4% citizens strangled).
"""

from __future__ import annotations

import random

import numpy as np
import pytest

from src.governance.anchor_wall import FixedAnchorWall

_ATTACK_TOKENS = ("ignore", "override", "jailbreak", "system", "disregard", "bypass", "reveal")
_BENIGN_TOKENS = ("weather", "recipe", "hello", "summary", "thanks", "schedule", "please")
SESSION_LEN = 5


def toy_embed(texts):
    """4-D embedding: +x per attack token, +y per benign token, + deterministic jitter."""
    out = []
    for t in texts:
        low = t.lower()
        a = sum(low.count(tok) for tok in _ATTACK_TOKENS)
        b = sum(low.count(tok) for tok in _BENIGN_TOKENS)
        jitter = ((len(t) * 7) % 11) * 0.01
        out.append([1.0 + a, 1.0 + b, jitter, 0.5])
    return np.asarray(out, dtype=np.float64)


def gen_benign(rng):
    return " ".join(rng.choice(_BENIGN_TOKENS) for _ in range(rng.randint(3, 8)))


def gen_attack(rng):
    return " ".join(rng.choice(_ATTACK_TOKENS) for _ in range(rng.randint(3, 8)))


def benign_session(rng, n=SESSION_LEN):
    return [gen_benign(rng) for _ in range(n)]


def attack_session(rng, cover=2, push=3):
    return [gen_benign(rng) for _ in range(cover)] + [gen_attack(rng) for _ in range(push)]


@pytest.fixture
def wall():
    rng = random.Random(11)
    benign_pool = [gen_benign(rng) for _ in range(200)]
    attack_pool = [gen_attack(rng) for _ in range(200)]
    w = FixedAnchorWall(embed_fn=toy_embed, k=4.0)
    w.fit(benign_pool, attack_pool)
    # calibrate on benign sessions of the SAME length we will evaluate
    w.calibrate([benign_session(rng) for _ in range(300)], target_fpr=0.05)
    return w


def test_fit_produces_unit_anchors(wall):
    assert wall.fitted
    assert pytest.approx(np.linalg.norm(wall.safe_anchor), abs=1e-6) == 1.0
    assert pytest.approx(np.linalg.norm(wall.attack_anchor), abs=1e-6) == 1.0


def test_attack_costs_more_than_benign(wall):
    assert wall.cost("ignore override jailbreak system bypass") > wall.cost("weather recipe hello thanks please")
    assert wall.margin("ignore override jailbreak system") > 0
    assert wall.margin("weather recipe hello thanks") < 0


def test_unfitted_raises():
    w = FixedAnchorWall(embed_fn=toy_embed)
    with pytest.raises(RuntimeError):
        w.margin("hello")


def test_no_threshold_raises():
    w = FixedAnchorWall(embed_fn=toy_embed).fit(["weather hello"], ["ignore override"])
    with pytest.raises(RuntimeError):
        w.step("ignore override")


def test_attack_session_blocked_benign_passes(wall):
    rng = random.Random(99)
    atk = wall.run_session(attack_session(rng))
    ben = wall.run_session(benign_session(rng))
    assert atk.tripped and atk.decision in ("QUARANTINE", "DENY")
    assert not ben.tripped and ben.decision == "ALLOW"


def test_cumulative_accrues_and_resets(wall):
    wall.reset()
    assert wall.cumulative == 0.0
    wall.step("ignore override jailbreak")
    assert wall.cumulative > 0.0
    wall.reset()
    assert wall.cumulative == 0.0


def test_deny_above_quarantine(wall):
    res = wall.run_session(["ignore override jailbreak system disregard bypass reveal"] * 12)
    assert res.decision == "DENY"


def test_enforcement_rates_on_holdout(wall):
    """The headline invariant: stops intruders, lets citizens through."""
    rng = random.Random(7)
    N = 120
    intruders = sum(1 for _ in range(N) if wall.run_session(attack_session(rng)).tripped)
    citizens = sum(1 for _ in range(N) if wall.run_session(benign_session(rng)).tripped)
    assert intruders / N >= 0.85, f"intruder_stopped too low: {intruders/N}"
    assert citizens / N <= 0.15, f"citizen_strangled too high: {citizens/N}"


def test_fixed_anchor_separates_where_held_out(wall):
    """Held-out margins: attacks positive (toward core), benign negative (home)."""
    rng = random.Random(3)
    atk_margins = [wall.margin(gen_attack(rng)) for _ in range(50)]
    ben_margins = [wall.margin(gen_benign(rng)) for _ in range(50)]
    assert min(atk_margins) > max(ben_margins), "fixed anchor must cleanly separate held-out attack vs benign"
