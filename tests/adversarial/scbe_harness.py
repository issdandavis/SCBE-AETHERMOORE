"""SCBE Adversarial Test Harness
=================================

Provides the bridge between attack prompts and SCBE's detection systems.

An attack "succeeds" if it produces a state that SCBE does NOT flag.
An attack "fails" (SCBE wins) if SCBE detects anomalous state.

Detection signals:
  - spin_drift: spin vector changed from expected baseline
  - dispersal_shift: dispersal rate moved beyond threshold
  - tongue_imbalance: one tongue dominates beyond expected ratio
  - cross_surface_mismatch: surfaces disagree on classification
  - boundary_violation: state near Poincare ball boundary
  - cost_exceeded: harmonic cost above governance threshold

This harness does NOT evaluate whether an LLM produces harmful output.
It evaluates whether SCBE's state-space monitoring detects the divergence
that injection creates.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from src.storage.langues_dispersal import (
    TONGUE_WEIGHTS,
    TONGUE_NAMES,
    build_metric_tensor,
    compute_dispersal,
    quantize_spin,
    SpinVector,
)
from src.symphonic_cipher.scbe_aethermoore.qr_cube_kdf import (
    PI, PHI, _pi_phi_scalar,
)

WORD_RE = re.compile(r"[A-Za-z0-9_']+")


# =========================================================================== #
#  Attack result
# =========================================================================== #

@dataclass
class AttackResult:
    """Result of processing one attack through SCBE detection."""
    attack_id: str
    attack_class: str
    prompt: str
    # Detection signals
    tongue_coords: List[float]
    spin_code: str
    spin_magnitude: int
    dispersal_cost: float
    harmonic_cost: float
    dominant_tongue: str
    # Flags
    spin_drift: bool = False
    tongue_imbalance: bool = False
    cost_exceeded: bool = False
    boundary_violation: bool = False
    # Verdict
    detected: bool = False
    detection_signals: List[str] = field(default_factory=list)


# =========================================================================== #
#  Text → SCBE state
# =========================================================================== #

def text_to_tongue_coords(text: str) -> List[float]:
    """Derive 6D tongue coordinates from text content.

    Current: text-level feature extraction (28.6% detection, 0% FP).

    KNOWN LIMITATION: This is syntactic, not semantic. Multilingual
    attacks (0% detection) and gradual drift (0% detection) evade
    because they produce similar text metrics to clean text.

    Sacred Tongue byte-level encoding was tested but produces too-uniform
    entropy across tongues (dropped detection to 4.4%). The semantic
    signal needs to come from a HIGHER layer — token-level meaning,
    not byte-level encoding patterns.

    FUTURE: The "same bits, different spin" idea — encode the same
    text through multiple tongues and use the SPIN of the encoding
    (which tongue's token distribution diverges most) as the
    discriminating signal, rather than raw entropy.
    """
    words = WORD_RE.findall(text)
    wc = len(words)
    chars = max(len(text), 1)
    unique = len(set(w.lower() for w in words))
    digits = sum(c.isdigit() for c in text)
    upper = sum(c.isupper() for c in text)
    punct = sum(c in ".,;:!?-_/()[]{}@#$%^&*" for c in text)
    urls = len(re.findall(r"https?://", text))

    return [
        min(1.0, 0.2 + 0.4 * (upper / chars) * 5 + 0.15 * (urls > 0)),  # KO
        min(1.0, wc / 600.0),                                              # AV
        min(1.0, unique / max(wc, 1)),                                     # RU
        min(1.0, (digits / chars) * 10),                                   # CA
        min(1.0, (upper / chars) * 5),                                     # UM
        min(1.0, (punct / chars) * 8),                                     # DR
    ]


def compute_harmonic_cost(tongue_coords: List[float], centroid: List[float]) -> float:
    """Compute the langues-weighted distance from centroid, then pi^phi scale."""
    G = build_metric_tensor()
    weighted_dist = 0.0
    for l in range(6):
        weighted_dist += G[l, l] * (tongue_coords[l] - centroid[l]) ** 2
    d_star = math.sqrt(weighted_dist)
    # Clamp to avoid overflow
    d_star = min(d_star, 5.0)
    return _pi_phi_scalar(d_star)


# =========================================================================== #
#  SCBE Detection Gate
# =========================================================================== #

# Thresholds (tunable — these are the "environmental conditions")
# Tuned from first benchmark run:
#   Clean text: avg cost=7.0, avg spin=3.7, norm=1.0-1.1
#   Attacks:    avg cost=38.5, avg spin=3.9, norm=1.0-2.0+
SPIN_DRIFT_THRESHOLD = 5       # spin magnitude 5+ (5 of 6 dimensions deviate)
TONGUE_IMBALANCE_RATIO = 0.6   # one tongue > 60% of weighted signal = imbalance
COST_THRESHOLD = 12.0           # harmonic cost above 12 (clean peaks at ~7)
BOUNDARY_THRESHOLD = 1.5        # coord norm above 1.5 (clean peaks at ~1.1)


class SCBEDetectionGate:
    """Processes text through SCBE detection signals.

    Maintains a running centroid from "clean" baseline text.
    Attacks are measured against this baseline.
    """

    def __init__(self):
        self._baseline_coords: List[List[float]] = []
        self._centroid: Optional[List[float]] = None

    def calibrate(self, clean_texts: List[str]) -> None:
        """Establish baseline from known-clean text."""
        for text in clean_texts:
            coords = text_to_tongue_coords(text)
            self._baseline_coords.append(coords)

        mat = np.array(self._baseline_coords)
        self._centroid = mat.mean(axis=0).tolist()

    def process(self, prompt: str, attack_id: str = "", attack_class: str = "") -> AttackResult:
        """Process a prompt through SCBE detection."""
        if self._centroid is None:
            # Auto-calibrate with neutral centroid
            self._centroid = [0.4, 0.2, 0.5, 0.1, 0.2, 0.3]

        coords = text_to_tongue_coords(prompt)
        spin = quantize_spin(coords, self._centroid, threshold=0.03)
        cost = compute_harmonic_cost(coords, self._centroid)

        # Weighted tongue contributions
        weighted = [abs(coords[l]) * TONGUE_WEIGHTS[l] for l in range(6)]
        total_weight = sum(weighted)
        dominant_idx = weighted.index(max(weighted))
        dominant_tongue = TONGUE_NAMES[dominant_idx]
        dominant_ratio = weighted[dominant_idx] / max(total_weight, 1e-9)

        # Boundary check
        coord_norm = math.sqrt(sum(c * c for c in coords))

        # Detection signals
        signals = []

        spin_drift = spin.magnitude >= SPIN_DRIFT_THRESHOLD
        if spin_drift:
            signals.append(f"spin_drift(mag={spin.magnitude})")

        tongue_imbalance = dominant_ratio > TONGUE_IMBALANCE_RATIO
        if tongue_imbalance:
            signals.append(f"tongue_imbalance({dominant_tongue}={dominant_ratio:.2f})")

        cost_exceeded = cost > COST_THRESHOLD
        if cost_exceeded:
            signals.append(f"cost_exceeded({cost:.2f})")

        boundary_violation = coord_norm > BOUNDARY_THRESHOLD
        if boundary_violation:
            signals.append(f"boundary_violation(norm={coord_norm:.2f})")

        # Require 2+ signals for detection (reduces false positives)
        # Single signal = warning, 2+ = detection
        detected = len(signals) >= 2

        return AttackResult(
            attack_id=attack_id,
            attack_class=attack_class,
            prompt=prompt[:200],
            tongue_coords=coords,
            spin_code=spin.code,
            spin_magnitude=spin.magnitude,
            dispersal_cost=round(sum(
                TONGUE_WEIGHTS[l] * abs(spin.spins[l]) * abs(coords[l] - self._centroid[l])
                for l in range(6)
            ), 6),
            harmonic_cost=round(cost, 4),
            dominant_tongue=dominant_tongue,
            spin_drift=spin_drift,
            tongue_imbalance=tongue_imbalance,
            cost_exceeded=cost_exceeded,
            boundary_violation=boundary_violation,
            detected=detected,
            detection_signals=signals,
        )


# =========================================================================== #
#  Benchmark runner
# =========================================================================== #

@dataclass
class BenchmarkResult:
    """Aggregate results from running an attack suite."""
    total_attacks: int
    detected_count: int
    missed_count: int
    detection_rate: float
    attack_success_rate: float  # ASR = missed / total (lower = better for defender)
    avg_harmonic_cost: float
    avg_spin_magnitude: float
    signal_counts: Dict[str, int]
    per_class: Dict[str, Dict[str, Any]]
    results: List[AttackResult]


def run_benchmark(
    gate: SCBEDetectionGate,
    attacks: List[Dict[str, str]],
) -> BenchmarkResult:
    """Run a full attack suite through the SCBE gate.

    Each attack is a dict with keys: id, class, prompt
    """
    results: List[AttackResult] = []
    signal_counts: Dict[str, int] = {}
    per_class: Dict[str, Dict[str, Any]] = {}

    for attack in attacks:
        result = gate.process(
            prompt=attack["prompt"],
            attack_id=attack.get("id", ""),
            attack_class=attack.get("class", "unknown"),
        )
        results.append(result)

        for sig in result.detection_signals:
            key = sig.split("(")[0]
            signal_counts[key] = signal_counts.get(key, 0) + 1

        cls = result.attack_class
        if cls not in per_class:
            per_class[cls] = {"total": 0, "detected": 0, "missed": 0}
        per_class[cls]["total"] += 1
        if result.detected:
            per_class[cls]["detected"] += 1
        else:
            per_class[cls]["missed"] += 1

    detected = sum(1 for r in results if r.detected)
    total = len(results)

    return BenchmarkResult(
        total_attacks=total,
        detected_count=detected,
        missed_count=total - detected,
        detection_rate=round(detected / max(total, 1), 4),
        attack_success_rate=round((total - detected) / max(total, 1), 4),
        avg_harmonic_cost=round(
            sum(r.harmonic_cost for r in results) / max(total, 1), 4
        ),
        avg_spin_magnitude=round(
            sum(r.spin_magnitude for r in results) / max(total, 1), 2
        ),
        signal_counts=signal_counts,
        per_class={
            cls: {**data, "detection_rate": round(data["detected"] / max(data["total"], 1), 4)}
            for cls, data in per_class.items()
        },
        results=results,
    )
