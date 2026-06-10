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

Session length (honest): in the default unbounded mode the accrued cost grows
with session length, so the calibrated threshold is for an expected length —
calibrate on benign sessions of the length you expect, or raw cumulative will
eventually trip any sufficiently long benign session. For unbounded/long-lived
sessions set `window=N`: the wall then sums only the cost of the last N actions
(a sliding window), so the score stays bounded regardless of session length.
The window changes the score distribution, so the threshold must be calibrated
WITH the window set — calibrate() and the live enforcement path share one
windowed-accumulation routine so the threshold always matches what step() does.

Threat-model tradeoff (not strictly an upgrade): a window opens a low-and-slow
evasion. An attacker who paces malicious actions so only a few land inside any
single window can keep the windowed score under threshold indefinitely — the
unbounded cumulative mode catches that (cost only ever accrues), the window does
not. Choose the mode for the threat: unbounded (with length-matched calibration)
when total drift over a session matters; window when you must bound false
positives on long-lived sessions and can accept the paced-attack gap.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Deque, List, Optional, Sequence

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
    window: Optional[int] = None  # None = unbounded cumulative; N = sliding window of last N actions

    safe_anchor: Optional[np.ndarray] = None
    attack_anchor: Optional[np.ndarray] = None
    threshold: Optional[float] = None  # (windowed) cumulative-cost quarantine threshold
    _cumulative: float = field(default=0.0, init=False)
    _recent: Deque[float] = field(default_factory=deque, init=False)

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

    def _session_peak(self, costs: Sequence[float]) -> float:
        """Peak (windowed) cumulative cost reached while replaying a session.

        Single source of truth for how cost accrues — used by calibrate() so the
        threshold matches exactly what step() accrues live. With window=None this
        is the final running sum (monotonic, so peak == final); with a window it
        is the max over the session of the sum of the last `window` costs.
        """
        cum = 0.0
        peak = 0.0
        recent: Deque[float] = deque()
        for c in costs:
            cum += c
            if self.window is not None:
                recent.append(c)
                if len(recent) > self.window:
                    cum -= recent.popleft()
            if cum > peak:
                peak = cum
        return peak

    # --- calibration -------------------------------------------------------
    def calibrate(self, benign_sessions: Sequence[Sequence[str]], target_fpr: float = 0.05) -> float:
        """Set the quarantine threshold from benign sessions so ~target_fpr of
        legitimate sessions trip it. Returns the chosen threshold.

        Calibrates against the same (windowed) accrual the live wall uses: the
        per-session peak cumulative. With window=None this reduces to the final
        session sum (unchanged from the original behavior)."""
        if not self.fitted:
            raise RuntimeError("fit() before calibrate()")
        peaks = []
        for sess in benign_sessions:
            peaks.append(self._session_peak([self.cost(t) for t in sess]))
        pct = 100.0 * (1.0 - max(0.0, min(1.0, target_fpr)))
        self.threshold = float(np.percentile(peaks, pct))
        return self.threshold

    # --- session enforcement ----------------------------------------------
    def reset(self) -> None:
        self._cumulative = 0.0
        self._recent.clear()

    @property
    def cumulative(self) -> float:
        return self._cumulative

    def step(self, text: str) -> WallStep:
        """Feed one action; accrue (windowed) cost; return decision so far."""
        if self.threshold is None:
            raise RuntimeError("wall has no threshold; call calibrate() first")
        m = self.margin(text)
        c = math.exp(self.k * m)
        self._cumulative += c
        if self.window is not None:
            self._recent.append(c)
            if len(self._recent) > self.window:
                self._cumulative -= self._recent.popleft()
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
