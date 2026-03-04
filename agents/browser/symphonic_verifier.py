"""Symphonic Cipher-inspired action verifier.

Uses FFT signatures of action/target command vectors to detect incoherent
(hallucinated/corrupted) action patterns before execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

EPS = 1e-9


@dataclass
class SymphonicVerificationResult:
    passed: bool
    confidence: float
    expected_harmonics: List[float]
    observed_peaks: List[float]
    reason: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "passed": self.passed,
            "confidence": self.confidence,
            "expected_harmonics": self.expected_harmonics,
            "observed_peaks": self.observed_peaks,
            "reason": self.reason,
        }


class SymphonicVerifier:
    """Fast spectral verification for browser action commands."""

    ACTION_BASE_FREQ = {
        "navigate": 3.0,
        "click": 5.0,
        "type": 7.0,
        "extract": 11.0,
        "scroll": 13.0,
        "screenshot": 17.0,
        "snapshot": 19.0,
    }

    def __init__(self, min_confidence: float = 0.65):
        self.min_confidence = min_confidence

    @staticmethod
    def _encode_signal(action: str, target: str, length: int = 128) -> np.ndarray:
        seed = f"{action}|{target}".encode("utf-8")
        arr = np.frombuffer(seed, dtype=np.uint8).astype(np.float64)
        if arr.size == 0:
            arr = np.array([0.0], dtype=np.float64)
        tiled = np.tile(arr, int(np.ceil(length / arr.size)))[:length]
        centered = tiled - np.mean(tiled)
        scale = np.std(centered)
        if scale < EPS:
            return centered
        return centered / scale

    @staticmethod
    def _topk_peaks(magnitude: np.ndarray, k: int = 5) -> List[float]:
        if magnitude.size == 0:
            return []
        idx = np.argsort(magnitude)[-k:][::-1]
        return [float(i) for i in idx]

    def verify(self, action: str, target: str) -> SymphonicVerificationResult:
        base = self.ACTION_BASE_FREQ.get(action.lower(), 9.0)
        expected = [base, base * 2.0, base * 3.0]

        signal = self._encode_signal(action, target)
        spectrum = np.fft.rfft(signal)
        magnitude = np.abs(spectrum)
        peaks = self._topk_peaks(magnitude, k=6)

        matches = 0
        for f in expected:
            if any(abs(p - f) <= 2.0 for p in peaks):
                matches += 1

        confidence = matches / max(1, len(expected))
        passed = confidence >= self.min_confidence

        reason = "harmonics_verified" if passed else "overtone_mismatch"
        return SymphonicVerificationResult(
            passed=passed,
            confidence=float(confidence),
            expected_harmonics=[float(x) for x in expected],
            observed_peaks=peaks,
            reason=reason,
        )
