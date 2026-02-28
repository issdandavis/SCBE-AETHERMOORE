"""Spin Engine -- ModelMatrix conversation spin wrapper.

Uses conversation_spin() to generate context-enriched spin data
that informs governance decisions.  Each spin cycle produces
Lorentz-force trajectory data tagged by Sacred Tongue.

@layer Layer 5, Layer 9
@component AetherIDE.SpinEngine
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

PHI = (1 + math.sqrt(5)) / 2
TONGUE_NAMES = ["KO", "AV", "RU", "CA", "UM", "DR"]

try:
    from src.fleet.model_matrix import ModelMatrix
    _HAS_MODEL_MATRIX = True
except ImportError:
    _HAS_MODEL_MATRIX = False


class SpinEngine:
    """Generate context-relevant spin data for IDE governance."""

    def __init__(self) -> None:
        self._matrix: Optional[Any] = None
        self._spin_count = 0
        if _HAS_MODEL_MATRIX:
            try:
                self._matrix = ModelMatrix()
            except Exception:
                self._matrix = None

    def spin(self, topic: str, spins: int = 3) -> Dict[str, Any]:
        """Run a conversation spin cycle on the given topic.

        Returns spin result with tongue-tagged trajectory data.
        Falls back to a deterministic phi-based mock if ModelMatrix
        is unavailable.
        """
        self._spin_count += 1

        if self._matrix is not None and hasattr(self._matrix, "conversation_spin"):
            try:
                raw = self._matrix.conversation_spin(
                    bundle_id=f"aide-spin-{self._spin_count}",
                    seed_topic=topic,
                    spins=spins,
                )
                # Normalize return: ModelMatrix may return a list of dicts
                if isinstance(raw, dict):
                    return raw
                if isinstance(raw, list):
                    return {
                        "topic": topic,
                        "spins": spins,
                        "trajectory": raw,
                        "dominant_tongue": raw[0].get("tongue", "KO") if raw else "KO",
                        "fallback": False,
                    }
            except Exception:
                pass

        # Deterministic fallback: phi-based pseudo-spin
        trajectory: List[Dict[str, float]] = []
        for i in range(spins):
            angle = (2 * math.pi * i) / spins
            entry: Dict[str, float] = {}
            for j, tongue in enumerate(TONGUE_NAMES):
                phase = angle + (j * PHI)
                entry[tongue] = math.cos(phase) * (1.0 / (1 + i * 0.1))
            trajectory.append(entry)

        return {
            "topic": topic,
            "spins": spins,
            "trajectory": trajectory,
            "dominant_tongue": TONGUE_NAMES[hash(topic) % 6],
            "fallback": True,
        }

    @property
    def available(self) -> bool:
        return self._matrix is not None

    @property
    def spin_count(self) -> int:
        return self._spin_count
