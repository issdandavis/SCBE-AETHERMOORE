"""
Compatibility SDK wrapper for Sacred Tongue intent classification.
"""

from __future__ import annotations

from typing import Tuple

from src.symphonic_cipher.ai_verifier import AIVerifier


class SpiralverseSDK:
    """Adapter exposing classify_intent for the live runtime path."""

    def __init__(self):
        self._verifier = AIVerifier(strict_mode=False)

    def _risk_to_confidence(self, risk_level: str) -> float:
        if risk_level == "critical":
            return 0.60
        if risk_level == "high":
            return 0.72
        if risk_level == "medium":
            return 0.84
        if risk_level == "low":
            return 0.96
        return 0.5

    def classify_intent(self, message: str) -> Tuple[str, float]:
        result = self._verifier.classify_intent(message)
        intent = result.get("intent", "unknown")
        confidence = self._risk_to_confidence(result.get("risk_level", "medium"))
        return intent, confidence
