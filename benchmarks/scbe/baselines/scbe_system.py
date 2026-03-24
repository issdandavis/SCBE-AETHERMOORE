"""SCBE system wrapper -- bridges SCBEDetectionGate into the benchmark interface.

Wraps the existing ``tests.adversarial.scbe_harness.SCBEDetectionGate``
so it conforms to the same (detected, signals, metadata) interface
used by other baselines.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Import the real SCBE gate
try:
    from tests.adversarial.scbe_harness import SCBEDetectionGate
    _SCBE_AVAILABLE = True
except ImportError as exc:
    _SCBE_AVAILABLE = False
    _SCBE_IMPORT_ERROR = str(exc)
    logger.warning("SCBEDetectionGate not available: %s", _SCBE_IMPORT_ERROR)


class SCBESystem:
    """SCBE Detection Gate wrapped for benchmark comparison.

    This is our system under test. Maintains state across prompts
    (session suspicion, cost history) just like in production.
    """

    name = "scbe_system"
    description = "SCBE 14-layer Detection Gate (harmonic + lexical + session)"

    def __init__(self):
        self._gate: Optional[Any] = None
        self._available = _SCBE_AVAILABLE
        if self._available:
            self._gate = SCBEDetectionGate()

    @property
    def available(self) -> bool:
        return self._available

    def calibrate(self, clean_texts: List[str]) -> None:
        """Calibrate the SCBE gate with clean baseline text."""
        if self._gate is not None:
            self._gate.calibrate(clean_texts)

    def reset(self) -> None:
        """Reset the gate state (new session)."""
        if self._available:
            self._gate = SCBEDetectionGate()

    def detect(self, prompt: str) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Process a prompt through SCBE detection.

        Returns:
            (detected, signals, metadata)
        """
        if not self._available or self._gate is None:
            return False, [], {
                "system": self.name,
                "verdict": "UNAVAILABLE",
                "error": "SCBEDetectionGate not importable",
            }

        result = self._gate.process(prompt)

        metadata: Dict[str, Any] = {
            "system": self.name,
            "verdict": "DENY" if result.detected else "ALLOW",
            "harmonic_cost": result.harmonic_cost,
            "spin_code": result.spin_code,
            "spin_magnitude": result.spin_magnitude,
            "dispersal_cost": result.dispersal_cost,
            "dominant_tongue": result.dominant_tongue,
            "tongue_coords": result.tongue_coords,
            "flags": {
                "spin_drift": result.spin_drift,
                "tongue_imbalance": result.tongue_imbalance,
                "cost_exceeded": result.cost_exceeded,
                "boundary_violation": result.boundary_violation,
                "adversarial_lexical": result.adversarial_lexical,
                "cross_lingual_override": result.cross_lingual_override,
                "dispersal_shift": result.dispersal_shift,
            },
        }

        return result.detected, result.detection_signals, metadata

    def detect_batch(
        self, prompts: List[str]
    ) -> List[Tuple[bool, List[str], Dict[str, Any]]]:
        """Process a batch of prompts. SCBE is stateful, so order matters."""
        return [self.detect(p) for p in prompts]

    def get_scbe_metadata(self, prompt: str) -> Dict[str, Any]:
        """Get full SCBE-specific metadata for a single prompt.

        Returns the complete AttackResult dataclass fields as a dict,
        useful for SCBE-specific metrics (drift, dispersal, audio).
        """
        if not self._available or self._gate is None:
            return {}

        result = self._gate.process(prompt)
        return {
            "harmonic_cost": result.harmonic_cost,
            "spin_code": result.spin_code,
            "spin_magnitude": result.spin_magnitude,
            "dispersal_cost": result.dispersal_cost,
            "dominant_tongue": result.dominant_tongue,
            "tongue_coords": result.tongue_coords,
            "spin_drift": result.spin_drift,
            "tongue_imbalance": result.tongue_imbalance,
            "cost_exceeded": result.cost_exceeded,
            "boundary_violation": result.boundary_violation,
            "adversarial_lexical": result.adversarial_lexical,
            "cross_lingual_override": result.cross_lingual_override,
            "dispersal_shift": result.dispersal_shift,
            "detected": result.detected,
            "detection_signals": result.detection_signals,
        }
