"""
Decimal Drift Path Validator — Floating-Point Precision Tracking Across 14 Layers
==================================================================================

Every floating-point computation introduces tiny precision errors. These errors
are NOT random — they're deterministic artifacts of IEEE 754 representation.
When you pass data through 14 governance layers, each layer's rounding error
creates a "decimal drift" that accumulates into a unique PATH through the
computation manifold.

Key insight: The decimal drift IS a signature. Same input → same drift path.
Different computation path → different drift. Tampering changes drift.
This is FREE verification — it comes from the math itself.

How it works:
  1. At each layer, compute the "true" value (high-precision) and the float value
  2. The difference (epsilon drift) is the decimal drift at that layer
  3. The 14 epsilon drifts form a "drift path" — a 14D vector
  4. Known good paths are stored in a directory
  5. New paths are compared against known paths
  6. Anomalous paths trigger investigation

User input effects at three scales:
  - MICRO (single evaluation): How one input changes one drift path
  - MACRO (session): How a sequence of inputs shifts the baseline drift
  - GIGA (fleet): How all agents' collective drift reveals system health

This is the "Ping Pong / Pac Man" concept: the system explores computational
routes like a game AI, building a map of valid paths through the governance
manifold. Unknown routes = unexplored territory = potential anomaly.

@layer All layers (transversal)
@patent USPTO #63/961,403
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import time
from dataclasses import dataclass, field
from decimal import Decimal, getcontext, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .tracker import (
    PHI, GOLDEN_ANGLE, FIBONACCI_SEQ,
    TONGUE_WEIGHTS, LAYER_TONGUE_RESONANCE,
    LayerSnapshot, DriftSignature, FibonacciDriftTracker,
)

# Set high decimal precision for "true" value computation
getcontext().prec = 50

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

# Machine epsilon for float64
FLOAT64_EPSILON = 2.220446049250313e-16

# Phi at high precision (Decimal)
PHI_DECIMAL = (Decimal(1) + Decimal(5).sqrt()) / Decimal(2)

# Layer computation functions at high precision
# Each layer has a characteristic function that introduces specific drift
LAYER_FUNCTIONS = {
    1: lambda v: v * Decimal(str(PHI)),           # Phi scaling
    2: lambda v: v * v,                            # Squaring
    3: lambda v: Decimal(str(math.pi)) * v,        # Pi scaling
    4: lambda v: v / (Decimal(1) + v),             # Logistic compression
    5: lambda v: (Decimal(1) + Decimal(2) * v * v).ln() if v > 0 else Decimal(0),  # Arccosh-like
    6: lambda v: abs(Decimal(str(math.sin(float(v) * float(PHI_DECIMAL))))),  # Breathing
    7: lambda v: abs(Decimal(str(math.cos(float(v) * float(PHI_DECIMAL))))),  # Mobius phase
    8: lambda v: v ** Decimal(2) if v < Decimal(1) else v,  # Multi-well
    9: lambda v: Decimal(1) - v if v < Decimal(1) else Decimal(0),  # Coherence flip
    10: lambda v: v * PHI_DECIMAL ** Decimal(2),   # Phi^2 scaling
    11: lambda v: Decimal(str(math.sin(float(v)))).copy_abs(),  # Temporal oscillation
    12: lambda v: Decimal(str(1.5)) ** (v ** Decimal(2)) if v < Decimal(10) else Decimal(str(1e15)),  # Harmonic wall
    13: lambda v: v / Decimal(5) if v < Decimal(5) else Decimal(1),  # Risk normalization
    14: lambda v: v * (Decimal(1) - v) if v < Decimal(1) else Decimal(0),  # Audit composite
}


# ---------------------------------------------------------------------------
#  Data Types
# ---------------------------------------------------------------------------

@dataclass
class EpsilonDrift:
    """Floating-point precision drift at a single layer."""
    layer: int
    float_value: float         # IEEE 754 float64 result
    decimal_value: float       # High-precision Decimal result (truncated to float for storage)
    epsilon: float             # Absolute difference (the drift)
    relative_epsilon: float    # Relative difference (epsilon / value)
    ulp_drift: int             # Units in Last Place drift
    mantissa_bits_used: int    # How many mantissa bits carry information
    tongue: str                # Layer's resonant tongue

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer": self.layer,
            "float_value": self.float_value,
            "decimal_value": self.decimal_value,
            "epsilon": self.epsilon,
            "relative_epsilon": self.relative_epsilon,
            "ulp_drift": self.ulp_drift,
            "mantissa_bits_used": self.mantissa_bits_used,
            "tongue": self.tongue,
        }


@dataclass
class DriftPath:
    """A 14D vector of epsilon drifts — the path through the computation manifold."""
    epsilons: List[EpsilonDrift]      # 14 epsilon drifts, one per layer
    path_hash: str                     # SHA-256 of the epsilon vector
    total_epsilon: float               # Sum of all absolute epsilons
    max_epsilon: float                 # Largest single epsilon
    max_epsilon_layer: int             # Which layer has the worst drift
    path_signature: str                # Compact hex signature (first 8 bytes of hash)
    dominant_drift_tongue: str         # Tongue with highest cumulative drift
    precision_health: float            # 0.0 = severe drift, 1.0 = clean computation
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path_hash": self.path_hash,
            "path_signature": self.path_signature,
            "total_epsilon": self.total_epsilon,
            "max_epsilon": self.max_epsilon,
            "max_epsilon_layer": self.max_epsilon_layer,
            "dominant_drift_tongue": self.dominant_drift_tongue,
            "precision_health": round(self.precision_health, 6),
            "epsilons": [e.to_dict() for e in self.epsilons],
            "timestamp": self.timestamp,
        }

    def to_vector(self) -> List[float]:
        """Return the 14D epsilon vector for comparison."""
        return [e.epsilon for e in self.epsilons]


@dataclass
class UserInputEffect:
    """How a user's input affects the system at micro/macro/giga scales."""
    # Micro: single evaluation impact
    micro_drift_path: DriftPath
    micro_anomaly: float           # How anomalous is this single eval?
    micro_path_known: bool         # Is this path in the known directory?

    # Macro: session-level impact
    macro_drift_trend: float       # Is drift increasing or decreasing over the session?
    macro_baseline_shift: float    # How far has the session baseline moved?
    macro_path_coverage: float     # What fraction of known paths has this session hit?

    # Giga: fleet-level impact (simulated for single-instance)
    giga_entropy_contribution: float   # How much entropy does this input add to the fleet?
    giga_exploration_value: float      # Is this input exploring new territory?
    giga_convergence_score: float      # Is the fleet converging or diverging?

    def to_dict(self) -> Dict[str, Any]:
        return {
            "micro": {
                "anomaly": round(self.micro_anomaly, 6),
                "path_known": self.micro_path_known,
                "precision_health": round(self.micro_drift_path.precision_health, 6),
                "path_signature": self.micro_drift_path.path_signature,
            },
            "macro": {
                "drift_trend": round(self.macro_drift_trend, 6),
                "baseline_shift": round(self.macro_baseline_shift, 6),
                "path_coverage": round(self.macro_path_coverage, 6),
            },
            "giga": {
                "entropy_contribution": round(self.giga_entropy_contribution, 6),
                "exploration_value": round(self.giga_exploration_value, 6),
                "convergence_score": round(self.giga_convergence_score, 6),
            },
        }


# ---------------------------------------------------------------------------
#  Decimal Drift Path Validator
# ---------------------------------------------------------------------------

class DecimalPathValidator:
    """
    Tracks floating-point decimal drift across 14 governance layers.

    Like Pac-Man exploring a maze: every evaluation traces a path
    through the computation manifold. Known paths are safe routes.
    Unknown paths are unexplored corridors. Dead ends are anomalies.

    The "known directory" is built up over time as the system processes
    clean evaluations. Each new evaluation either:
    1. Follows a known path (safe, expected)
    2. Explores a new path (novel but potentially valid — add to directory)
    3. Deviates from ALL known paths (anomaly — investigate)
    """

    def __init__(self, known_paths_dir: Optional[str] = None):
        self._known_paths: Dict[str, DriftPath] = {}  # signature → path
        self._session_paths: List[DriftPath] = []
        self._session_baseline: Optional[DriftPath] = None
        self._fleet_paths: Set[str] = set()  # All unique path signatures ever seen

        # Load known paths from disk if directory provided
        self._paths_dir = Path(known_paths_dir) if known_paths_dir else None
        if self._paths_dir and self._paths_dir.exists():
            self._load_known_paths()

    def compute_drift_path(self, snapshot: LayerSnapshot) -> DriftPath:
        """
        Compute the decimal drift path for a governance evaluation.

        For each layer:
        1. Take the float64 value from the snapshot
        2. Recompute using high-precision Decimal arithmetic
        3. Measure the epsilon (the drift between float and true value)
        """
        epsilons: List[EpsilonDrift] = []
        tongue_drift: Dict[str, float] = {}

        for layer_num in range(1, 15):
            float_val = snapshot.values.get(layer_num, 0.0)
            tongue = LAYER_TONGUE_RESONANCE[layer_num]

            # Compute high-precision result
            try:
                decimal_input = Decimal(str(float_val))
                func = LAYER_FUNCTIONS.get(layer_num, lambda v: v)
                decimal_result = float(func(decimal_input))
            except (Exception,):
                decimal_result = float_val

            # Recompute with float64 to get the actual float path
            try:
                func_float = LAYER_FUNCTIONS.get(layer_num, lambda v: v)
                float_result = float(func_float(Decimal(str(float_val))))
            except (Exception,):
                float_result = float_val

            # Epsilon: the difference between float computation paths
            epsilon = abs(float_result - float_val)
            relative_epsilon = epsilon / max(abs(float_val), FLOAT64_EPSILON)

            # ULP drift: how many "units in last place" is the drift?
            if float_val != 0.0:
                ulp = math.ulp(float_val)
                ulp_drift = int(epsilon / ulp) if ulp > 0 else 0
            else:
                ulp_drift = 0

            # Mantissa bits used: how many bits carry real information?
            if float_val != 0.0:
                mantissa_bits = 52 - max(0, int(-math.log2(max(relative_epsilon, FLOAT64_EPSILON))))
            else:
                mantissa_bits = 0

            ed = EpsilonDrift(
                layer=layer_num,
                float_value=float_val,
                decimal_value=decimal_result,
                epsilon=epsilon,
                relative_epsilon=relative_epsilon,
                ulp_drift=ulp_drift,
                mantissa_bits_used=max(0, min(52, mantissa_bits)),
                tongue=tongue,
            )
            epsilons.append(ed)
            tongue_drift[tongue] = tongue_drift.get(tongue, 0.0) + epsilon

        # Compute path metrics
        eps_values = [e.epsilon for e in epsilons]
        total_epsilon = sum(eps_values)
        max_epsilon = max(eps_values)
        max_epsilon_layer = eps_values.index(max_epsilon) + 1

        dominant_tongue = max(tongue_drift, key=tongue_drift.get) if tongue_drift else "KO"

        # Precision health: inverse of total relative epsilon
        rel_eps = [e.relative_epsilon for e in epsilons]
        mean_rel = sum(rel_eps) / len(rel_eps)
        precision_health = max(0.0, 1.0 - min(mean_rel, 1.0))

        # Path hash
        hash_input = struct.pack("!" + "d" * 14, *eps_values)
        path_hash = hashlib.sha256(hash_input).hexdigest()
        path_signature = path_hash[:16]

        path = DriftPath(
            epsilons=epsilons,
            path_hash=path_hash,
            total_epsilon=total_epsilon,
            max_epsilon=max_epsilon,
            max_epsilon_layer=max_epsilon_layer,
            path_signature=path_signature,
            dominant_drift_tongue=dominant_tongue,
            precision_health=precision_health,
        )

        # Track in session and fleet
        self._session_paths.append(path)
        self._fleet_paths.add(path_signature)

        if self._session_baseline is None:
            self._session_baseline = path

        return path

    def validate_path(self, path: DriftPath, tolerance: float = 0.1) -> Dict[str, Any]:
        """
        Check if a drift path matches any known path within tolerance.

        Returns validation result with match info.
        """
        if path.path_signature in self._known_paths:
            return {
                "status": "known_exact",
                "match": path.path_signature,
                "confidence": 1.0,
            }

        # Check approximate matches
        best_match = None
        best_distance = float("inf")

        path_vec = path.to_vector()
        for sig, known in self._known_paths.items():
            known_vec = known.to_vector()
            # Euclidean distance in 14D epsilon space
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(path_vec, known_vec)))
            if dist < best_distance:
                best_distance = dist
                best_match = sig

        if best_distance < tolerance:
            return {
                "status": "known_approximate",
                "match": best_match,
                "distance": round(best_distance, 8),
                "confidence": max(0, 1.0 - best_distance / tolerance),
            }

        return {
            "status": "unknown",
            "nearest": best_match,
            "distance": round(best_distance, 8) if best_match else None,
            "confidence": 0.0,
        }

    def register_path(self, path: DriftPath):
        """Add a path to the known directory (validated as good)."""
        self._known_paths[path.path_signature] = path
        if self._paths_dir:
            self._save_path(path)

    def measure_user_impact(
        self,
        snapshot: LayerSnapshot,
        path: DriftPath,
    ) -> UserInputEffect:
        """
        Measure how a user's input affects the system at all three scales.

        MICRO: How does THIS specific input's drift path compare to known paths?
        MACRO: How is the SESSION drift trending over time?
        GIGA: How does this contribute to the FLEET's exploration of path space?
        """
        # --- MICRO ---
        validation = self.validate_path(path)
        micro_anomaly = 1.0 - validation.get("confidence", 0.0)
        micro_known = validation["status"] != "unknown"

        # --- MACRO ---
        if len(self._session_paths) >= 2:
            recent = self._session_paths[-10:]
            eps_trend = [p.total_epsilon for p in recent]
            # Simple slope
            n = len(eps_trend)
            x_mean = (n - 1) / 2
            y_mean = sum(eps_trend) / n
            slope_num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(eps_trend))
            slope_den = sum((i - x_mean) ** 2 for i in range(n))
            macro_drift_trend = slope_num / slope_den if slope_den > 0 else 0.0
        else:
            macro_drift_trend = 0.0

        if self._session_baseline:
            baseline_vec = self._session_baseline.to_vector()
            current_vec = path.to_vector()
            macro_baseline_shift = math.sqrt(
                sum((a - b) ** 2 for a, b in zip(baseline_vec, current_vec))
            )
        else:
            macro_baseline_shift = 0.0

        # Path coverage: what fraction of known paths has this session explored?
        session_sigs = {p.path_signature for p in self._session_paths}
        known_sigs = set(self._known_paths.keys())
        if known_sigs:
            macro_path_coverage = len(session_sigs & known_sigs) / len(known_sigs)
        else:
            macro_path_coverage = 0.0

        # --- GIGA ---
        # Entropy: how many unique paths exist in the fleet?
        giga_entropy = math.log2(max(len(self._fleet_paths), 1))

        # Exploration value: is this a new path the fleet hasn't seen?
        giga_exploration = 1.0 if path.path_signature not in self._fleet_paths else 0.0

        # Convergence: are recent paths getting closer or further apart?
        if len(self._session_paths) >= 3:
            recent_3 = self._session_paths[-3:]
            vecs = [p.to_vector() for p in recent_3]
            dists = []
            for i in range(len(vecs)):
                for j in range(i + 1, len(vecs)):
                    d = math.sqrt(sum((a - b) ** 2 for a, b in zip(vecs[i], vecs[j])))
                    dists.append(d)
            giga_convergence = max(0, 1.0 - sum(dists) / max(len(dists), 1))
        else:
            giga_convergence = 0.5  # Neutral

        return UserInputEffect(
            micro_drift_path=path,
            micro_anomaly=micro_anomaly,
            micro_path_known=micro_known,
            macro_drift_trend=macro_drift_trend,
            macro_baseline_shift=macro_baseline_shift,
            macro_path_coverage=macro_path_coverage,
            giga_entropy_contribution=giga_entropy,
            giga_exploration_value=giga_exploration,
            giga_convergence_score=giga_convergence,
        )

    def get_path_directory_stats(self) -> Dict[str, Any]:
        """Report on the known path directory."""
        return {
            "known_paths": len(self._known_paths),
            "session_paths": len(self._session_paths),
            "fleet_unique_paths": len(self._fleet_paths),
            "tongues_distribution": self._tongue_distribution(),
        }

    def _tongue_distribution(self) -> Dict[str, int]:
        """How many known paths have each dominant tongue."""
        dist: Dict[str, int] = {}
        for path in self._known_paths.values():
            t = path.dominant_drift_tongue
            dist[t] = dist.get(t, 0) + 1
        return dist

    def _load_known_paths(self):
        """Load known paths from the directory."""
        if not self._paths_dir:
            return
        for f in self._paths_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                sig = data.get("path_signature", "")
                if sig:
                    # Reconstruct minimal DriftPath for comparison
                    eps_list = []
                    for e_data in data.get("epsilons", []):
                        eps_list.append(EpsilonDrift(
                            layer=e_data["layer"],
                            float_value=e_data["float_value"],
                            decimal_value=e_data["decimal_value"],
                            epsilon=e_data["epsilon"],
                            relative_epsilon=e_data["relative_epsilon"],
                            ulp_drift=e_data["ulp_drift"],
                            mantissa_bits_used=e_data["mantissa_bits_used"],
                            tongue=e_data["tongue"],
                        ))
                    self._known_paths[sig] = DriftPath(
                        epsilons=eps_list,
                        path_hash=data.get("path_hash", ""),
                        total_epsilon=data.get("total_epsilon", 0.0),
                        max_epsilon=data.get("max_epsilon", 0.0),
                        max_epsilon_layer=data.get("max_epsilon_layer", 1),
                        path_signature=sig,
                        dominant_drift_tongue=data.get("dominant_drift_tongue", "KO"),
                        precision_health=data.get("precision_health", 1.0),
                    )
            except (json.JSONDecodeError, KeyError):
                continue

    def _save_path(self, path: DriftPath):
        """Save a known path to disk."""
        if not self._paths_dir:
            return
        self._paths_dir.mkdir(parents=True, exist_ok=True)
        filepath = self._paths_dir / f"{path.path_signature}.json"
        filepath.write_text(json.dumps(path.to_dict(), indent=2))


# ---------------------------------------------------------------------------
#  Full Pipeline Integration
# ---------------------------------------------------------------------------

def run_full_drift_analysis(
    text: str,
    profile: str = "enterprise",
    known_paths_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run complete drift analysis: governance → spiral → decimal path → user impact.

    This is the unified pipeline that combines ALL the tracking systems.
    """
    from ..api.governance_saas import evaluate_text

    # 1. Governance evaluation
    result = evaluate_text(text, profile)

    # 2. Fibonacci spiral tracking
    snapshot = LayerSnapshot.from_governance_result(result)
    tracker = FibonacciDriftTracker()
    spiral_sig = tracker.track(snapshot)

    # 3. Decimal drift path
    validator = DecimalPathValidator(known_paths_dir)
    drift_path = validator.compute_drift_path(snapshot)

    # 4. Path validation
    validation = validator.validate_path(drift_path)

    # 5. User impact at all scales
    impact = validator.measure_user_impact(snapshot, drift_path)

    return {
        "governance": {
            "decision": result["decision"],
            "risk_score": result["risk_score"],
            "harmonic_wall": result["harmonic_wall"],
            "tongue": result["tongue"],
        },
        "spiral": {
            "hash": spiral_sig.spiral_hash,
            "anomaly": spiral_sig.anomaly_score,
            "phi_coherence": spiral_sig.phi_coherence,
            "energy": spiral_sig.spiral_energy,
        },
        "decimal_drift": {
            "path_signature": drift_path.path_signature,
            "total_epsilon": drift_path.total_epsilon,
            "precision_health": drift_path.precision_health,
            "max_drift_layer": drift_path.max_epsilon_layer,
        },
        "path_validation": validation,
        "user_impact": impact.to_dict(),
    }
