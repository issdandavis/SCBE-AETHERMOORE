"""
Fibonacci Drift Tracker — Spiral Fingerprinting of Governance Operations
=========================================================================

Every governance evaluation produces 14 layer values. This module maps them
onto a Fibonacci spiral using the golden angle (137.5077...degrees). The
resulting spiral path is a unique fingerprint of that operation.

The key insight: Fibonacci spirals are nature's way of packing information
efficiently (sunflower seeds, pinecones, galaxies). By mapping governance
layer outputs to spiral coordinates, we get:

1. A VISUAL fingerprint (polar plot of the spiral)
2. An AUDIO signal (sonification of radial distances)
3. A DRIFT detector (deviation from expected Fibonacci ratios)
4. A NATURAL entropy source (spiral path hash)

This is a BYPRODUCT of normal operations — zero extra computation cost.
The data was already computed; we just read it differently.

Chemistry analog: Each layer is an orbital. The spiral is the electron
cloud shape. Drift = the molecule is becoming unstable.

Sound analog: Each layer is a partial. The spiral is the timbre.
Drift = the instrument is going out of tune.

@layer All layers (transversal)
@patent USPTO #63/961,403
"""

from __future__ import annotations

import hashlib
import math
import struct
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio 1.618033...
GOLDEN_ANGLE = math.pi * (3 - math.sqrt(5))  # ~137.5077 degrees in radians = ~2.39996
FIBONACCI_SEQ = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]  # First 14

# Sacred Tongue weights (phi-scaled)
TONGUE_WEIGHTS = {
    "KO": 1.0, "AV": PHI, "RU": PHI**2,
    "CA": PHI**3, "UM": PHI**4, "DR": PHI**5,
}

# Layer-to-tongue resonance mapping
LAYER_TONGUE_RESONANCE = {
    1: "KO", 2: "KO", 3: "AV", 4: "AV",
    5: "RU", 6: "RU", 7: "CA", 8: "CA",
    9: "UM", 10: "UM", 11: "DR", 12: "DR",
    13: "DR", 14: "KO",  # L14 loops back to KO (composition axiom)
}


# ---------------------------------------------------------------------------
#  Data Types
# ---------------------------------------------------------------------------

@dataclass
class LayerSnapshot:
    """Raw output from one governance evaluation, all 14 layers."""
    values: Dict[int, float]  # layer_number → value (0.0 to 1.0+)
    tongue: str = "KO"
    risk_score: float = 0.0
    decision: str = "ALLOW"
    harmonic_wall: float = 1.0
    hyperbolic_distance: float = 0.0
    timestamp: float = field(default_factory=time.time)
    source_hash: str = ""

    @classmethod
    def from_governance_result(cls, result: Dict[str, Any]) -> "LayerSnapshot":
        """Create from governance SaaS API result."""
        ls = result.get("layer_summary", {})
        d_h = result.get("hyperbolic_distance", 0.0)
        h_wall = result.get("harmonic_wall", 1.0)
        risk = result.get("risk_score", 0.0)
        coherence = result.get("coherence", 1.0)

        # Map known layer values; estimate others from available data
        values = {}
        values[1] = min(risk * 0.5, 1.0)                        # Context complexity
        values[2] = min(risk * 0.3, 1.0)                        # Realification
        values[3] = min(d_h / 5.0, 1.0)                         # Weighted transform
        values[4] = min(d_h / 3.0, 1.0)                         # Poincare embedding
        values[5] = min(d_h / 5.0, 1.0)                         # Hyperbolic distance
        values[6] = min(abs(math.sin(d_h * PHI)), 1.0)          # Breathing transform
        values[7] = min(abs(math.cos(d_h * PHI)), 1.0)          # Mobius phase
        values[8] = min(h_wall / 100.0, 1.0)                    # Multi-well potential
        values[9] = coherence                                     # Spectral coherence
        values[10] = max(0, 1.0 - risk)                          # Spin coherence
        # Temporal binding (deterministic): inverse harmonic pressure.
        # High harmonic-wall values (adversarial drift) should reduce this weight.
        values[11] = min(1.0, 1.0 / max(1.0, h_wall))
        values[12] = min(math.log(max(h_wall, 1.0)) / 10.0, 1.0) # Harmonic wall (log-scaled)
        values[13] = {"ALLOW": 0.1, "QUARANTINE": 0.5, "ESCALATE": 0.8, "DENY": 1.0}.get(
            result.get("decision", "ALLOW"), 0.5
        )
        values[14] = risk * coherence  # Audit telemetry composite

        return cls(
            values=values,
            tongue=result.get("tongue", "KO"),
            risk_score=risk,
            decision=result.get("decision", "ALLOW"),
            harmonic_wall=h_wall,
            hyperbolic_distance=d_h,
            source_hash=ls.get("L1_4_encoding", ""),
        )


@dataclass
class SpiralPoint:
    """A single point on the Fibonacci spiral."""
    layer: int           # Which layer (1-14)
    theta: float         # Angle in radians (golden angle * layer index)
    radius: float        # Distance from center (layer value * Fibonacci weight)
    x: float             # Cartesian x
    y: float             # Cartesian y
    tongue: str          # Resonant tongue for this layer
    tongue_weight: float # Phi-based weight of the tongue
    fibonacci_n: int     # Fibonacci number for this position
    value: float         # Raw layer value
    decimal_drift: float # Deviation from Fibonacci ratio expectation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer": self.layer,
            "theta": round(self.theta, 6),
            "radius": round(self.radius, 6),
            "x": round(self.x, 6),
            "y": round(self.y, 6),
            "tongue": self.tongue,
            "tongue_weight": round(self.tongue_weight, 4),
            "fibonacci_n": self.fibonacci_n,
            "value": round(self.value, 6),
            "decimal_drift": round(self.decimal_drift, 6),
        }


@dataclass
class DriftSignature:
    """Complete Fibonacci drift fingerprint for one governance evaluation."""
    points: List[SpiralPoint]
    spiral_hash: str              # SHA-256 of the spiral path
    total_drift: float            # Sum of all decimal drifts
    mean_drift: float             # Average decimal drift
    max_drift: float              # Peak drift (worst layer)
    max_drift_layer: int          # Which layer has max drift
    dominant_tongue: str          # Tongue with highest spiral energy
    spiral_energy: float          # Total radial energy
    phi_coherence: float          # How well the spiral follows golden ratio
    anomaly_score: float          # 0.0 = normal, 1.0 = fully anomalous
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spiral_hash": self.spiral_hash,
            "total_drift": round(self.total_drift, 6),
            "mean_drift": round(self.mean_drift, 6),
            "max_drift": round(self.max_drift, 6),
            "max_drift_layer": self.max_drift_layer,
            "dominant_tongue": self.dominant_tongue,
            "spiral_energy": round(self.spiral_energy, 6),
            "phi_coherence": round(self.phi_coherence, 6),
            "anomaly_score": round(self.anomaly_score, 6),
            "points": [p.to_dict() for p in self.points],
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
#  Fibonacci Drift Tracker
# ---------------------------------------------------------------------------

class FibonacciDriftTracker:
    """
    Maps 14-layer governance outputs onto Fibonacci spiral paths.

    The golden angle (137.5077°) ensures each new point is maximally
    separated from all previous points — nature's optimal packing.
    This means EVERY layer gets its own unique angular position,
    and the radial distance encodes the layer's value.

    The resulting spiral is:
    - Deterministic (same input → same spiral)
    - Unique (different inputs → different spirals)
    - Self-similar (Fibonacci scaling at each layer)
    - Audible (radial distances → frequency/amplitude)
    - Hashable (spiral → 256-bit fingerprint)
    """

    def __init__(self, history_size: int = 100):
        self._history: List[DriftSignature] = []
        self._history_size = history_size
        self._baseline: Optional[DriftSignature] = None

    def track(self, snapshot: LayerSnapshot) -> DriftSignature:
        """
        Map a LayerSnapshot onto the Fibonacci spiral and compute drift.

        Each layer L_i gets:
          theta_i = i * GOLDEN_ANGLE
          radius_i = value_i * (F_i / F_14) * tongue_weight

        Where F_i is the i-th Fibonacci number and tongue_weight is the
        phi-scaled weight of the layer's resonant tongue.
        """
        points: List[SpiralPoint] = []
        max_fib = FIBONACCI_SEQ[13]  # F_14 = 377

        for i in range(14):
            layer_num = i + 1
            value = snapshot.values.get(layer_num, 0.0)
            tongue = LAYER_TONGUE_RESONANCE[layer_num]
            tw = TONGUE_WEIGHTS[tongue]
            fib_n = FIBONACCI_SEQ[i]

            # Fibonacci-weighted radius
            fib_scale = fib_n / max_fib
            radius = value * fib_scale * tw

            # Golden angle placement
            theta = (i + 1) * GOLDEN_ANGLE

            # Cartesian
            x = radius * math.cos(theta)
            y = radius * math.sin(theta)

            # Decimal drift: deviation of the spiral radius from the ideal
            # golden spiral r = a * PHI^(theta / (2*pi)).
            # For a clean (ALLOW) operation, values cluster near zero,
            # producing a tight spiral. Adversarial operations push values
            # outward, distorting the spiral shape.
            #
            # We measure drift as: |actual_radius - expected_radius| / expected
            # where expected follows the golden spiral equation.
            expected_radius = fib_scale * tw * 0.3  # "ideal" clean radius
            if expected_radius > 0.001:
                decimal_drift = abs(radius - expected_radius) / expected_radius
            else:
                decimal_drift = radius  # Any radius is drift from zero

            points.append(SpiralPoint(
                layer=layer_num,
                theta=theta,
                radius=radius,
                x=x,
                y=y,
                tongue=tongue,
                tongue_weight=tw,
                fibonacci_n=fib_n,
                value=value,
                decimal_drift=decimal_drift,
            ))

        # Compute signature metrics
        drifts = [p.decimal_drift for p in points]
        total_drift = sum(drifts)
        mean_drift = total_drift / 14
        max_drift = max(drifts)
        max_drift_layer = drifts.index(max_drift) + 1

        # Tongue energy: sum of radii per tongue
        tongue_energy: Dict[str, float] = {}
        for p in points:
            tongue_energy[p.tongue] = tongue_energy.get(p.tongue, 0.0) + p.radius
        dominant_tongue = max(tongue_energy, key=tongue_energy.get)

        # Total spiral energy
        spiral_energy = sum(p.radius for p in points)

        # Phi coherence: how well the spiral shape follows the golden spiral.
        # In a clean operation, most layer values are low (near origin),
        # creating a tight spiral. We measure this as the ratio of
        # spiral energy to maximum possible energy — low = coherent/tight.
        max_possible_energy = sum(
            (FIBONACCI_SEQ[i] / max_fib) * TONGUE_WEIGHTS[LAYER_TONGUE_RESONANCE[i + 1]]
            for i in range(14)
        )
        if max_possible_energy > 0:
            phi_coherence = max(0.0, 1.0 - spiral_energy / max_possible_energy)
        else:
            phi_coherence = 1.0

        # Anomaly score: normalized risk indicator.
        # Low drift + high phi_coherence = low anomaly (clean operation).
        # High drift + low phi_coherence = high anomaly (adversarial).
        normalized_drift = min(1.0, mean_drift / 3.0)  # Cap at 3.0 mean drift
        anomaly_score = min(1.0, normalized_drift * 0.5 + (1.0 - phi_coherence) * 0.5)

        # Spiral hash: deterministic fingerprint of the entire spiral
        hash_input = struct.pack(
            "!" + "d" * 14,
            *[p.radius for p in points]
        )
        spiral_hash = hashlib.sha256(hash_input).hexdigest()[:32]

        sig = DriftSignature(
            points=points,
            spiral_hash=spiral_hash,
            total_drift=total_drift,
            mean_drift=mean_drift,
            max_drift=max_drift,
            max_drift_layer=max_drift_layer,
            dominant_tongue=dominant_tongue,
            spiral_energy=spiral_energy,
            phi_coherence=phi_coherence,
            anomaly_score=anomaly_score,
        )

        # Store in history
        self._history.append(sig)
        if len(self._history) > self._history_size:
            self._history.pop(0)

        # Set baseline from first clean operation
        if self._baseline is None and snapshot.decision == "ALLOW":
            self._baseline = sig

        return sig

    def compare(self, sig: DriftSignature) -> Dict[str, Any]:
        """Compare a signature against the baseline."""
        if not self._baseline:
            return {"status": "no_baseline", "deviation": 0.0}

        # Compare spiral hashes
        if sig.spiral_hash == self._baseline.spiral_hash:
            return {"status": "identical", "deviation": 0.0}

        # Compare point-by-point radii
        deviations = []
        for sp, bp in zip(sig.points, self._baseline.points):
            if bp.radius > 0.001:
                dev = abs(sp.radius - bp.radius) / bp.radius
            else:
                dev = sp.radius
            deviations.append(dev)

        mean_dev = sum(deviations) / len(deviations) if deviations else 0.0
        max_dev = max(deviations) if deviations else 0.0

        return {
            "status": "compared",
            "mean_deviation": round(mean_dev, 6),
            "max_deviation": round(max_dev, 6),
            "max_deviation_layer": deviations.index(max_dev) + 1 if deviations else 0,
            "energy_delta": round(sig.spiral_energy - self._baseline.spiral_energy, 6),
            "anomaly_delta": round(sig.anomaly_score - self._baseline.anomaly_score, 6),
        }

    def trend(self, window: int = 10) -> Dict[str, Any]:
        """Analyze drift trend over recent history."""
        recent = self._history[-window:]
        if len(recent) < 2:
            return {"status": "insufficient_data", "count": len(recent)}

        anomalies = [s.anomaly_score for s in recent]
        energies = [s.spiral_energy for s in recent]
        drifts = [s.mean_drift for s in recent]

        # Trend direction (simple linear slope)
        def slope(values: List[float]) -> float:
            n = len(values)
            if n < 2:
                return 0.0
            x_mean = (n - 1) / 2
            y_mean = sum(values) / n
            num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
            den = sum((i - x_mean) ** 2 for i in range(n))
            return num / den if den > 0 else 0.0

        return {
            "status": "analyzed",
            "window": len(recent),
            "anomaly_trend": round(slope(anomalies), 6),
            "energy_trend": round(slope(energies), 6),
            "drift_trend": round(slope(drifts), 6),
            "mean_anomaly": round(sum(anomalies) / len(anomalies), 6),
            "mean_energy": round(sum(energies) / len(energies), 6),
            "tongues": [s.dominant_tongue for s in recent],
        }

    @property
    def history(self) -> List[DriftSignature]:
        return list(self._history)

    @property
    def baseline(self) -> Optional[DriftSignature]:
        return self._baseline
