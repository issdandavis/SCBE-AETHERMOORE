"""SCBE system wrapper -- bridges RuntimeGate into the benchmark interface.

Wraps ``src.governance.runtime_gate.RuntimeGate`` so it conforms to
the same (detected, signals, metadata) interface used by other baselines.

The wrapper:
  - Creates a RuntimeGate instance
  - Calibrates with 5 clean prompts
  - For each attack: gate.evaluate(text) -> {allowed, drift, surface_mismatch}
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Import the RuntimeGate from src/governance/
_SCBE_AVAILABLE = False
_SCBE_IMPORT_ERROR = ""

try:
    from src.governance.runtime_gate import RuntimeGate, Decision
    _SCBE_AVAILABLE = True
except ImportError as exc:
    _SCBE_IMPORT_ERROR = str(exc)
    logger.warning("RuntimeGate not available: %s", _SCBE_IMPORT_ERROR)

# Also try to import the SCBEDetectionGate for fallback
_HARNESS_AVAILABLE = False
try:
    from tests.adversarial.scbe_harness import SCBEDetectionGate
    _HARNESS_AVAILABLE = True
except ImportError:
    pass


class SCBESystem:
    """SCBE RuntimeGate wrapped for benchmark comparison.

    Creates a RuntimeGate instance, calibrates with clean prompts,
    and evaluates each attack through the full 14-layer pipeline.
    Maintains state across prompts (session centroid, cumulative cost,
    trust history) just like in production.
    """

    name = "scbe_system"
    description = "SCBE RuntimeGate (14-layer harmonic + tongue + spin + trust)"

    def __init__(self):
        self._gate: Optional[Any] = None
        self._harness_gate: Optional[Any] = None
        self._available = _SCBE_AVAILABLE or _HARNESS_AVAILABLE
        self._using_runtime_gate = _SCBE_AVAILABLE

        if _SCBE_AVAILABLE:
            self._gate = RuntimeGate()
        elif _HARNESS_AVAILABLE:
            self._harness_gate = SCBEDetectionGate()

    @property
    def available(self) -> bool:
        return self._available

    def calibrate(self, clean_texts: List[str]) -> None:
        """Calibrate the SCBE gate with clean baseline text.

        For RuntimeGate: feed the first 5 clean texts through evaluate()
        to build the session centroid (auto-calibration period).

        For SCBEDetectionGate fallback: call .calibrate() directly.
        """
        if self._gate is not None:
            # RuntimeGate auto-calibrates on first 5 evaluate() calls
            for text in clean_texts[:5]:
                self._gate.evaluate(text)
        elif self._harness_gate is not None:
            self._harness_gate.calibrate(clean_texts)

    def reset(self) -> None:
        """Reset the gate state (new session)."""
        if _SCBE_AVAILABLE:
            self._gate = RuntimeGate()
        elif _HARNESS_AVAILABLE:
            self._harness_gate = SCBEDetectionGate()

    def detect(self, prompt: str) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Process a prompt through SCBE detection.

        For RuntimeGate:
          - gate.evaluate(text) returns a GateResult
          - detected = (decision != ALLOW)
          - drift = cost
          - surface_mismatch = spin_magnitude >= 5

        Returns:
            (detected, signals, metadata)
        """
        if self._gate is not None:
            return self._detect_runtime_gate(prompt)
        elif self._harness_gate is not None:
            return self._detect_harness(prompt)
        else:
            return False, [], {
                "system": self.name,
                "verdict": "UNAVAILABLE",
                "error": "Neither RuntimeGate nor SCBEDetectionGate importable",
            }

    def _detect_runtime_gate(self, prompt: str) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Evaluate via src.governance.runtime_gate.RuntimeGate."""
        result = self._gate.evaluate(prompt)

        # Decision mapping: anything that is not ALLOW is detected
        allowed = result.decision == Decision.ALLOW
        detected = not allowed

        # Drift = harmonic cost
        drift = result.cost

        # Surface mismatch = spin magnitude >= 5
        surface_mismatch = result.spin_magnitude >= 5

        metadata: Dict[str, Any] = {
            "system": self.name,
            "verdict": result.decision.value,
            "allowed": allowed,
            "drift": drift,
            "surface_mismatch": surface_mismatch,
            "harmonic_cost": result.cost,
            "spin_magnitude": result.spin_magnitude,
            "tongue_coords": result.tongue_coords,
            "trust_level": result.trust_level,
            "trust_weight": result.trust_weight,
            "cumulative_cost": result.cumulative_cost,
            "session_query_count": result.session_query_count,
            "action_hash": result.action_hash,
            "flags": {
                "spin_drift": result.spin_magnitude >= 5,
                "tongue_imbalance": False,  # RuntimeGate does not expose this
                "cost_exceeded": result.cost > 50.0,
                "boundary_violation": False,
                "adversarial_lexical": False,
                "cross_lingual_override": False,
                "dispersal_shift": False,
            },
        }

        if result.reroute_to:
            metadata["reroute_to"] = result.reroute_to

        if result.noise is not None:
            metadata["noise_length"] = len(result.noise)

        return detected, result.signals, metadata

    def _detect_harness(self, prompt: str) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Fallback: evaluate via tests.adversarial.scbe_harness.SCBEDetectionGate."""
        result = self._harness_gate.process(prompt)

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
        """Get full SCBE-specific metadata for a single prompt."""
        _, _, metadata = self.detect(prompt)
        return metadata
