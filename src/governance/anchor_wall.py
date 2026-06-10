"""Fixed-anchor enforcement wall — the crystal, bolted down.

The runtime gate's original drift measure used the session's OWN running centroid
as the reference. That center follows the agent: an attacker walking toward the
forbidden region keeps the centroid under their feet and never "drifts," so the
cumulative-cost wall never fires (measured cumulative-cost AUC 0.24 — below
random). See experiments/enforcement_wall_test.py for the failure and
experiments/fixed_anchor_wall.py for the fix this module productizes.

This wall fixes the reference. Two anchors are learned once from labelled data
and never move:

    safe_anchor   = mean unit embedding of benign examples   (home)
    attack_anchor = mean unit embedding of malicious examples (the forbidden core)

Per action, cost rises exponentially with movement toward the forbidden core on a
FIXED axis that does not follow the agent::

    margin(e) = cos(e, attack_anchor) - cos(e, safe_anchor)   # higher = more attack-like
    cost(e)   = exp(k * margin)

Cost accrues across a session (cumulative). The session is QUARANTINEd when the
cumulative cost crosses a threshold calibrated on benign sessions (so a target
fraction of legitimate sessions trip it), and DENYed at a higher multiple.

On real human-attack corpora this holds at cumulative-cost AUC 0.999, ~99%
intruders stopped, ~4% citizens strangled, caught after <2 malicious actions.

The embedder is injected (`embed_fn: List[str] -> np.ndarray [N, D]`, rows need
not be normalized — the wall normalizes), so this module has no heavy
dependency and is fully unit-testable offline.

Caveat (honest): cumulative cost grows with session length, so the calibrated
threshold is for an expected session length — calibrate on benign sessions of
the length you expect. For unbounded/long-lived sessions, prefer a sliding
window or a decay (a `window` mode is a planned extension); raw cumulative will
eventually trip any sufficiently long benign session.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence

import numpy as np

EmbedFn = Callable[[List[str]], np.ndarray]


def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / (n + 1e-8)


@dataclass
class WallStep:
    """Result of feeding one action to the wall."""

    cost: float
    cumulative: float
    decision: str  # "ALLOW" | "QUARANTINE" | "DENY"
    margin: float
    tripped: bool


@dataclass
class FixedAnchorWall:
    """A bolted-down cost wall: fixed anchors, exponential approach cost."""

    embed_fn: EmbedFn
    k: float = 8.0
    deny_multiple: float = 3.0  # DENY threshold = deny_multiple * quarantine threshold

    safe_anchor: Optional[np.ndarray] = None
    attack_anchor: Optional[np.ndarray] = None
    threshold: Optional[float] = None  # cumulative-cost quarantine threshold
    _cumulative: float = field(default=0.0, init=False)

    # --- fitting -----------------------------------------------------------
    def fit(self, benign_texts: Sequence[str], malicious_texts: Sequence[str]) -> "FixedAnchorWall":
        """Learn the two fixed anchors from labelled examples."""
        if not benign_texts or not malicious_texts:
            raise ValueError("fit() needs both benign and malicious examples")
        b = _unit(np.asarray(self.embed_fn(list(benign_texts)), dtype=np.float64))
        m = _unit(np.asarray(self.embed_fn(list(malicious_texts)), dtype=np.float64))
        self.safe_anchor = _unit(b.mean(axis=0))
        self.attack_anchor = _unit(m.mean(axis=0))
        return self

    @property
    def fitted(self) -> bool:
        return self.safe_anchor is not None and self.attack_anchor is not None

    # --- per-action scoring ------------------------------------------------
    def margin(self, text: str) -> float:
        """Signed approach-to-core margin for one action (higher = more attack-like)."""
        if not self.fitted:
            raise RuntimeError("wall is not fitted; call fit() first")
        e = _unit(np.asarray(self.embed_fn([text]), dtype=np.float64)[0])
        return float(np.dot(e, self.attack_anchor) - np.dot(e, self.safe_anchor))

    def cost(self, text: str) -> float:
        """Exponential approach cost for one action."""
        return math.exp(self.k * self.margin(text))

    # --- calibration -------------------------------------------------------
    def calibrate(self, benign_sessions: Sequence[Sequence[str]], target_fpr: float = 0.05) -> float:
        """Set the quarantine threshold from benign sessions so ~target_fpr of
        legitimate sessions trip it. Returns the chosen threshold."""
        if not self.fitted:
            raise RuntimeError("fit() before calibrate()")
        totals = []
        for sess in benign_sessions:
            totals.append(sum(self.cost(t) for t in sess))
        pct = 100.0 * (1.0 - max(0.0, min(1.0, target_fpr)))
        self.threshold = float(np.percentile(totals, pct))
        return self.threshold

    # --- session enforcement ----------------------------------------------
    def reset(self) -> None:
        self._cumulative = 0.0

    @property
    def cumulative(self) -> float:
        return self._cumulative

    def step(self, text: str) -> WallStep:
        """Feed one action; accrue cost; return decision for the session so far."""
        if self.threshold is None:
            raise RuntimeError("wall has no threshold; call calibrate() first")
        m = self.margin(text)
        c = math.exp(self.k * m)
        self._cumulative += c
        deny_threshold = self.deny_multiple * self.threshold
        if self._cumulative >= deny_threshold:
            decision = "DENY"
        elif self._cumulative >= self.threshold:
            decision = "QUARANTINE"
        else:
            decision = "ALLOW"
        return WallStep(
            cost=c,
            cumulative=self._cumulative,
            decision=decision,
            margin=m,
            tripped=decision != "ALLOW",
        )

    def run_session(self, actions: Sequence[str]) -> WallStep:
        """Run a whole session from a clean state; return the final step (first
        trip latches the decision severity)."""
        self.reset()
        worst = WallStep(0.0, 0.0, "ALLOW", 0.0, False)
        sev = {"ALLOW": 0, "QUARANTINE": 1, "DENY": 2}
        for a in actions:
            s = self.step(a)
            if sev[s.decision] > sev[worst.decision]:
                worst = s
        if worst.decision == "ALLOW":
            worst = WallStep(0.0, self._cumulative, "ALLOW", 0.0, False)
        return worst
