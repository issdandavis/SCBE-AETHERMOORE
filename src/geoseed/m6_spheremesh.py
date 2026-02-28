"""
M6 SphereMesh
=============

Executable scaffold for the 6-seed, 6-sphere multi-nodal model.

Design alignment:
- Six Sacred Tongue seed nodes (KO/AV/RU/CA/UM/DR)
- 6 interconnected icosahedral sphere grids in 6D semantic space
- 21D canonical state projection
- Sacred Egg gate for privileged graph mutation
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import math
from typing import Dict, List, Mapping, Sequence, Tuple

import numpy as np

from src.geoseed.composition import DressedBitComposer, SemanticUnit
from src.geoseed.dressing import BitDresser
from src.geoseed.sphere_grid import PHI_WEIGHTS, TONGUE_NAMES, TONGUE_PHASES, SphereGridNetwork


@dataclass
class M6Event:
    record_id: str
    summary: str
    tongue_vector: Dict[str, float]
    metadata: Dict[str, object]


@dataclass
class SacredEgg:
    egg_id: str
    required_tongues: List[str]
    min_phi_weight: float
    ttl_seconds: int
    created_at_utc: str
    hatched: bool = False


class M6SphereMesh:
    """Six-seed multi-nodal sphere mesh runtime scaffold."""

    def __init__(self, *, resolution: int = 1, signal_dim: int = 64):
        self.network = SphereGridNetwork(resolution=resolution, signal_dim=signal_dim)
        self.bit_dresser = BitDresser(layer_count=14)
        self.composer = DressedBitComposer()
        self.eggs: Dict[str, SacredEgg] = {}
        self.history: List[Dict[str, object]] = []

    @staticmethod
    def _normalize_tongue_vector(raw: Mapping[str, float] | None) -> Dict[str, float]:
        vector = {k: 0.0 for k in TONGUE_NAMES}
        if raw:
            for key, value in raw.items():
                tongue = str(key).upper().strip()
                if tongue in vector:
                    vector[tongue] = float(value)
        total = sum(abs(v) for v in vector.values())
        if total <= 1e-9:
            vector["KO"] = 1.0
            return vector
        return {k: v / total for k, v in vector.items()}

    @staticmethod
    def _event_to_tokens(event: M6Event) -> Dict[str, List[str]]:
        tokens = [t for t in event.summary.split() if t]
        strongest = max(event.tongue_vector.items(), key=lambda kv: abs(kv[1]))[0]
        return {strongest: tokens}

    @staticmethod
    def _tongue_position(tongue: str) -> np.ndarray:
        phase = TONGUE_PHASES[tongue]
        return np.array([math.cos(phase), math.sin(phase), 0.25], dtype=float)

    @staticmethod
    def _clip01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def _project_state21d(self, global_state: np.ndarray, tongue_vector: Dict[str, float]) -> List[float]:
        # Deterministic projection from 6*signal_dim -> 21 dimensions.
        # Keep simple, stable, and bounded in [-1, 1].
        if global_state.size == 0:
            return [0.0] * 21

        idx = np.linspace(0, len(global_state) - 1, 21, dtype=int)
        projected = [float(np.tanh(global_state[i])) for i in idx]

        # Inject tongue-domain priors into dims 10-15 (0-indexed 9-14) for explainability.
        tongue_order = ["KO", "AV", "RU", "CA", "UM", "DR"]
        for i, tongue in enumerate(tongue_order):
            projected[9 + i] = float(np.clip(tongue_vector.get(tongue, 0.0), -1.0, 1.0))

        return [round(v, 6) for v in projected]

    def score_transition(self, source_tongue: str, target_tongue: str) -> Dict[str, float]:
        s = source_tongue.upper().strip()
        t = target_tongue.upper().strip()
        if s not in TONGUE_NAMES or t not in TONGUE_NAMES:
            return {"compatibility": 0.0, "harmonic_cost": 1.0, "score": -1.0}

        phase_delta = abs(TONGUE_PHASES[s] - TONGUE_PHASES[t])
        phase_term = (1.0 + math.cos(phase_delta)) / 2.0
        weight_ratio = min(PHI_WEIGHTS[s], PHI_WEIGHTS[t]) / max(PHI_WEIGHTS[s], PHI_WEIGHTS[t])
        compatibility = self._clip01(0.6 * phase_term + 0.4 * weight_ratio)
        harmonic_cost = float(math.exp((1.0 - compatibility) ** 2))
        score = round(compatibility - (harmonic_cost - 1.0), 6)

        return {
            "compatibility": round(compatibility, 6),
            "harmonic_cost": round(harmonic_cost, 6),
            "score": score,
        }

    def ingest_event(self, event: M6Event, *, steps: int = 1) -> Dict[str, object]:
        tongue_vector = self._normalize_tongue_vector(event.tongue_vector)

        for tongue, magnitude in tongue_vector.items():
            if abs(magnitude) < 1e-9:
                continue
            signal = np.zeros(self.network.signal_dim, dtype=float)
            signal[0] = magnitude
            signal[1] = PHI_WEIGHTS[tongue] / PHI_WEIGHTS["DR"]
            signal[2] = math.cos(TONGUE_PHASES[tongue])
            signal[3] = math.sin(TONGUE_PHASES[tongue])
            self.network.deposit(tongue, self._tongue_position(tongue), signal)

        self.network.forward(n_steps=max(1, int(steps)))
        global_state = self.network.read_global_state()
        state21d = self._project_state21d(global_state, tongue_vector)

        dressed = self.bit_dresser.dress_tokens(
            self._event_to_tokens(event),
            run_id=event.record_id,
        )
        semantic_unit: SemanticUnit = self.composer.compose(dressed, unit_id=event.record_id)

        record = {
            "record_id": event.record_id,
            "state21d": state21d,
            "tongue_vector": tongue_vector,
            "semantic_unit": {
                "unit_id": semantic_unit.unit_id,
                "tongues": semantic_unit.tongues,
                "confidence": semantic_unit.confidence,
            },
            "metadata": event.metadata,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        self.history.append(record)
        return record

    def register_egg(
        self,
        *,
        egg_id: str,
        required_tongues: Sequence[str],
        min_phi_weight: float,
        ttl_seconds: int = 3600,
    ) -> SacredEgg:
        tongues = []
        for tongue in required_tongues:
            t = str(tongue).upper().strip()
            if t in TONGUE_NAMES and t not in tongues:
                tongues.append(t)

        egg = SacredEgg(
            egg_id=egg_id,
            required_tongues=tongues,
            min_phi_weight=float(min_phi_weight),
            ttl_seconds=max(1, int(ttl_seconds)),
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        )
        self.eggs[egg_id] = egg
        return egg

    def hatch_egg(self, egg_id: str, declared_tongues: Sequence[str]) -> Tuple[bool, str]:
        egg = self.eggs.get(egg_id)
        if egg is None:
            return False, "egg_not_found"
        if egg.hatched:
            return False, "egg_already_hatched"

        created = datetime.fromisoformat(egg.created_at_utc.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > created + timedelta(seconds=egg.ttl_seconds):
            return False, "egg_expired"

        declared = []
        for tongue in declared_tongues:
            t = str(tongue).upper().strip()
            if t in TONGUE_NAMES and t not in declared:
                declared.append(t)

        required = set(egg.required_tongues)
        if not required.issubset(set(declared)):
            missing = sorted(required - set(declared))
            return False, f"missing_required_tongues:{','.join(missing)}"

        phi_sum = sum(PHI_WEIGHTS[t] for t in declared)
        if phi_sum < egg.min_phi_weight:
            return False, f"insufficient_phi_weight:{phi_sum:.3f}"

        egg.hatched = True
        return True, "hatched"

    def snapshot(self) -> Dict[str, object]:
        return {
            "history_count": len(self.history),
            "eggs": {
                key: {
                    "required_tongues": egg.required_tongues,
                    "min_phi_weight": egg.min_phi_weight,
                    "ttl_seconds": egg.ttl_seconds,
                    "hatched": egg.hatched,
                }
                for key, egg in self.eggs.items()
            },
            "last_record": self.history[-1] if self.history else None,
        }
