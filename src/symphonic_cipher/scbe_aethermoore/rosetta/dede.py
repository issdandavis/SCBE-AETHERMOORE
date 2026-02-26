"""DEDE — Dual Entropic Defense Engine.

Two entropy channels feeding SCBE governance:
  - H_behavioral: Shannon entropy of action type distribution
  - H_governance: Entropy of governance decision distribution

Four regime quadrants based on (H_beh, H_gov) thresholds:
  - normal:         low H_beh, low H_gov  → routine operations
  - anomalous:      high H_beh, low H_gov → unusual behavior, governance stable
  - governance_gap: low H_beh, high H_gov → normal behavior, governance unstable
  - critical:       high H_beh, high H_gov → both channels chaotic → block
"""

from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DEDESignal:
    """Output signal from the dual entropy engine."""

    h_behavioral: float     # Shannon entropy of behavioral distribution
    h_governance: float     # Entropy of governance decision distribution
    regime: str             # "normal", "anomalous", "governance_gap", "critical"
    action: str             # "allow", "sandbox", "escalate", "block"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "h_behavioral": round(self.h_behavioral, 4),
            "h_governance": round(self.h_governance, 4),
            "regime": self.regime,
            "action": self.action,
            "timestamp": self.timestamp,
        }


def _shannon_entropy(counts: dict[str, int]) -> float:
    """Compute Shannon entropy H = -sum(p * log2(p)) from count dict."""
    total = sum(counts.values())
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counts.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    return entropy


def _distribution_entropy(scores: list[dict[str, float]]) -> float:
    """Compute entropy of governance score distributions.

    Takes a list of score dicts (each mapping decision -> probability-like weight)
    and computes average entropy across the window.
    """
    if not scores:
        return 0.0

    total_entropy = 0.0
    for score_dict in scores:
        total = sum(abs(v) for v in score_dict.values())
        if total == 0:
            continue
        ent = 0.0
        for v in score_dict.values():
            p = abs(v) / total
            if p > 0:
                ent -= p * math.log2(p)
        total_entropy += ent

    return total_entropy / len(scores)


class DualEntropicDefenseEngine:
    """Watches behavior + governance entropy, classifies into 4 regimes.

    Maintains sliding windows of:
    - Recent action types (behavioral channel)
    - Recent governance score distributions (governance channel)

    Computes dual entropy signal and recommends governance action.
    """

    # Thresholds for (H_beh, H_gov) quadrant classification
    DEFAULT_THRESHOLDS = {"h_beh": 2.0, "h_gov": 1.5}

    # Regime -> action mapping
    REGIME_ACTIONS = {
        "normal": "allow",
        "anomalous": "sandbox",
        "governance_gap": "escalate",
        "critical": "block",
    }

    def __init__(
        self,
        window_size: int = 100,
        h_beh_threshold: float = 2.0,
        h_gov_threshold: float = 1.5,
    ) -> None:
        self.window_size = window_size
        self.h_beh_threshold = h_beh_threshold
        self.h_gov_threshold = h_gov_threshold

        # Behavioral window: recent action type strings
        self._action_window: deque[str] = deque(maxlen=window_size)
        # Governance window: recent governance score dicts
        self._governance_window: deque[dict[str, float]] = deque(maxlen=window_size)
        # Signal history
        self._signal_history: list[DEDESignal] = []

    def observe_action(
        self,
        action_type: str,
        governance_scores: Optional[dict[str, float]] = None,
    ) -> None:
        """Record an action and its governance scores.

        Args:
            action_type: Category of action (e.g., "read", "write", "delete", "admin")
            governance_scores: Dict of governance dimension -> score
                               (e.g., {"allow": 0.7, "deny": 0.2, "quarantine": 0.1})
        """
        self._action_window.append(action_type)
        if governance_scores is not None:
            self._governance_window.append(governance_scores)

    def _behavioral_entropy(self) -> float:
        """Compute Shannon entropy over action type distribution in window."""
        if not self._action_window:
            return 0.0
        counts: dict[str, int] = {}
        for action in self._action_window:
            counts[action] = counts.get(action, 0) + 1
        return _shannon_entropy(counts)

    def _governance_entropy(self) -> float:
        """Compute average entropy over governance decision distributions in window."""
        return _distribution_entropy(list(self._governance_window))

    def _classify_regime(self, h_beh: float, h_gov: float) -> str:
        """Classify into one of four regimes based on thresholds."""
        high_beh = h_beh >= self.h_beh_threshold
        high_gov = h_gov >= self.h_gov_threshold

        if high_beh and high_gov:
            return "critical"
        elif high_beh:
            return "anomalous"
        elif high_gov:
            return "governance_gap"
        else:
            return "normal"

    def compute_signal(self) -> DEDESignal:
        """Compute current dual entropy signal.

        Returns a DEDESignal with entropy values, regime classification,
        and recommended action.
        """
        h_beh = self._behavioral_entropy()
        h_gov = self._governance_entropy()
        regime = self._classify_regime(h_beh, h_gov)
        action = self.REGIME_ACTIONS[regime]

        signal = DEDESignal(
            h_behavioral=h_beh,
            h_governance=h_gov,
            regime=regime,
            action=action,
        )
        self._signal_history.append(signal)
        return signal

    def should_block(self) -> bool:
        """Quick check: is current state critical?"""
        signal = self.compute_signal()
        return signal.regime == "critical"

    def should_sandbox(self) -> bool:
        """Quick check: should actions be sandboxed?"""
        signal = self.compute_signal()
        return signal.regime in ("anomalous", "critical")

    def get_history(self, n: int = 10) -> list[DEDESignal]:
        """Get the last N signals."""
        return self._signal_history[-n:]

    def reset(self) -> None:
        """Clear all windows and history."""
        self._action_window.clear()
        self._governance_window.clear()
        self._signal_history.clear()

    def export_sft(self) -> dict:
        """Export current state as an SFT training record."""
        signal = self.compute_signal()
        return {
            "id": "dede-signal-001",
            "category": "dede-signal",
            "instruction": "What is the current dual entropy defense signal?",
            "response": str(signal.to_dict()),
            "metadata": {
                "source": "scbe_aethermoore",
                "version": "4.0.0",
                "type": "dede_signal",
                "window_size": self.window_size,
                "action_count": len(self._action_window),
                "governance_count": len(self._governance_window),
            },
        }
