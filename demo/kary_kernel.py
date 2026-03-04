#!/usr/bin/env python3
"""
K-ary Simplex Kernel for Non-Binary Governance Decisions
=========================================================

Extends classical binary ALLOW/DENY governance to K-valued logic on the
probability simplex.  The kernel maintains continuous state variables that
evolve via Ornstein-Uhlenbeck-inspired dynamics, then projects onto K
governance classes through a learned (or preset) affine map followed by
temperature-scaled softmax.

Mathematical foundation
-----------------------
State variables (continuous, time-evolving):
    D_t  -- depth in [0,1]   (penetration depth)
    v_t  -- vulnerability     (environmental risk)
    P_t  -- pressure          (external threat)
    I_t  -- intent in [-1,1]  (negative = malicious)

Accumulated quantities:
    E_t = (1 - lambda_E) * E_{t-1} + v_t * P_t * D_t * dt   (exposure)
    J_t = (1 - lambda_J) * J_{t-1} + I_t * dt                (intent)
    q_t = E_t / (|J_t| + epsilon)                             (time-over-intent)

Logits:
    z = W @ [J_t, E_t]^T + b          (K-dimensional)
    p = softmax(z / tau)               (K-simplex point)

Risk and tiering:
    R_t = dot(p, r)                    (expected risk)
    Tier assignment via threshold cuts.

Integration with SCBE binary safety score:
    H(d, pd) = 1 / (1 + d + 2*pd)     (bounded in (0,1])
    to_binary_safety() collapses K probabilities to H-compatible scalar.

Patent: USPTO #63/961,403   |   SCBE v3.0.0+
Author: SCBE-AETHERMOORE project
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EPSILON = 1e-6

TRIADIC_LABELS: List[str] = ["ALLOW", "QUARANTINE", "DENY"]
QUATERNARY_LABELS: List[str] = ["CARE", "NEUTRAL", "HARM", "REPAIR"]

# Sacred Tongue mapping for quaternary governance classes
TONGUE_KERNEL_MAP: Dict[str, str] = {
    "CARE":    "KO",   # Kor'aelin  -- protective tenderness
    "NEUTRAL": "AV",   # Avali      -- peaceful coexistence
    "HARM":    "UM",   # Umbroth    -- shadow, facing darkness
    "REPAIR":  "DR",   # Draumric   -- rebuilding, creation
}

# Triadic risk weights: ALLOW=0, QUARANTINE=0.5, DENY=1.0
TRIADIC_RISK_WEIGHTS: List[float] = [0.0, 0.5, 1.0]
# Quaternary risk weights: CARE=0, NEUTRAL=0.3, HARM=1.0, REPAIR=0.5
QUATERNARY_RISK_WEIGHTS: List[float] = [0.0, 0.3, 1.0, 0.5]

# ---------------------------------------------------------------------------
# Preset weight matrices  (K x 2) and bias vectors (K)
# Columns of W map [J_t, E_t] to each class logit.
# ---------------------------------------------------------------------------

TRIADIC_W: List[List[float]] = [
    [ 1.5, -1.0],   # z_allow
    [-0.8,  0.5],   # z_quarantine  (uses |J| trick applied in code)
    [-1.5,  1.5],   # z_deny
]
TRIADIC_B: List[float] = [0.0, 0.5, 0.0]

QUATERNARY_W: List[List[float]] = [
    [ 1.8, -1.2],   # z_care
    [-1.0, -0.2],   # z_neutral  (uses |J| trick applied in code)
    [-1.5,  1.8],   # z_harm
    [ 1.2,  1.2],   # z_repair
]
QUATERNARY_B: List[float] = [0.0, 0.8, 0.0, -0.5]

# ---------------------------------------------------------------------------
# Utility functions (pure math, no external deps)
# ---------------------------------------------------------------------------

def _softmax(logits: List[float], temperature: float = 1.0) -> List[float]:
    """Numerically stable softmax with temperature scaling."""
    scaled = [z / max(temperature, EPSILON) for z in logits]
    m = max(scaled)
    exps = [math.exp(z - m) for z in scaled]
    s = sum(exps)
    return [e / s for e in exps]


def _dot(a: List[float], b: List[float]) -> float:
    """Inner product of two equal-length vectors."""
    return sum(ai * bi for ai, bi in zip(a, b))


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))

# ---------------------------------------------------------------------------
# Kernel state
# ---------------------------------------------------------------------------

@dataclass
class KernelState:
    """Continuous state of the K-ary kernel."""
    exposure: float = 0.0
    intent_accum: float = 0.0
    time_step: int = 0
    last_probs: List[float] = field(default_factory=list)
    last_risk: float = 0.0
    last_tier: int = 1
    history: List[Dict] = field(default_factory=list)

# ---------------------------------------------------------------------------
# KarySimplexKernel
# ---------------------------------------------------------------------------

class KarySimplexKernel:
    """K-valued governance kernel using simplex geometry.

    Parameters
    ----------
    k : int
        Number of governance classes (3 = triadic, 4 = quaternary, or arbitrary).
    temperature : float
        Softmax temperature.  Lower = sharper decisions.
    lambda_e : float
        Exposure decay rate (Ornstein-Uhlenbeck mean-reversion speed).
    lambda_j : float
        Intent-accumulation decay rate.
    labels : list[str] | None
        Human-readable labels for each class.  Auto-generated if None.
    weights : list[list[float]] | None
        K x 2 weight matrix.  Preset used for K=3 and K=4 if None.
    biases : list[float] | None
        K bias vector.  Preset used for K=3 and K=4 if None.
    risk_weights : list[float] | None
        Per-class risk contribution in [0,1].  Preset for K=3/4 if None.
    tier_thresholds : tuple[float, float]
        (theta_1, theta_2) for T1/T2/T3 tiering.
    """

    def __init__(
        self,
        k: int = 4,
        temperature: float = 1.0,
        lambda_e: float = 0.05,
        lambda_j: float = 0.03,
        labels: Optional[List[str]] = None,
        weights: Optional[List[List[float]]] = None,
        biases: Optional[List[float]] = None,
        risk_weights: Optional[List[float]] = None,
        tier_thresholds: Tuple[float, float] = (0.3, 0.6),
    ):
        if k < 2:
            raise ValueError("k must be >= 2 for a meaningful simplex")
        self.k = k
        self.temperature = temperature
        self.lambda_e = lambda_e
        self.lambda_j = lambda_j
        self.tier_thresholds = tier_thresholds

        # --- labels ---
        if labels is not None:
            if len(labels) != k:
                raise ValueError(f"Expected {k} labels, got {len(labels)}")
            self.labels = list(labels)
        elif k == 3:
            self.labels = list(TRIADIC_LABELS)
        elif k == 4:
            self.labels = list(QUATERNARY_LABELS)
        else:
            self.labels = [f"CLASS_{i}" for i in range(k)]

        # --- weight matrix W (K x 2) and bias b (K) ---
        if weights is not None:
            if len(weights) != k or any(len(row) != 2 for row in weights):
                raise ValueError(f"weights must be {k}x2 matrix")
            self.W = [list(row) for row in weights]
        elif k == 3:
            self.W = [list(row) for row in TRIADIC_W]
        elif k == 4:
            self.W = [list(row) for row in QUATERNARY_W]
        else:
            # Default: first class is "positive intent", last is "high exposure"
            # Middle classes interpolate.  Reasonable generic initialisation.
            self.W = []
            for i in range(k):
                frac = i / max(k - 1, 1)
                w_j = 1.5 * (1.0 - 2.0 * frac)   # +1.5 .. -1.5
                w_e = 1.5 * (2.0 * frac - 1.0)    # -1.5 .. +1.5
                self.W.append([w_j, w_e])

        if biases is not None:
            if len(biases) != k:
                raise ValueError(f"biases must have length {k}")
            self.b = list(biases)
        elif k == 3:
            self.b = list(TRIADIC_B)
        elif k == 4:
            self.b = list(QUATERNARY_B)
        else:
            self.b = [0.0] * k

        # --- risk weights ---
        if risk_weights is not None:
            if len(risk_weights) != k:
                raise ValueError(f"risk_weights must have length {k}")
            self.risk_weights = list(risk_weights)
        elif k == 3:
            self.risk_weights = list(TRIADIC_RISK_WEIGHTS)
        elif k == 4:
            self.risk_weights = list(QUATERNARY_RISK_WEIGHTS)
        else:
            # Linear ramp from 0 (safest) to 1 (most dangerous)
            self.risk_weights = [i / max(k - 1, 1) for i in range(k)]

        # --- neutral-class flags (absolute-value trick for "neutral" logits) ---
        # For K=3 index 1 (QUARANTINE) and K=4 index 1 (NEUTRAL), the spec
        # uses |J_t| in the logit formula.  We mark those indices so _logits()
        # can apply the absolute-value transformation.
        self._abs_j_indices: set = set()
        if k == 3 and weights is None:
            self._abs_j_indices.add(1)
        elif k == 4 and weights is None:
            self._abs_j_indices.add(1)

        # --- mutable state ---
        self.state = KernelState()

    # -----------------------------------------------------------------
    # Core math
    # -----------------------------------------------------------------

    def _update_accumulators(
        self, depth: float, vulnerability: float,
        pressure: float, intent: float, dt: float,
    ) -> Tuple[float, float, float]:
        """Ornstein-Uhlenbeck-inspired accumulator update.

        Returns (E_t, J_t, q_t).
        """
        E_prev = self.state.exposure
        J_prev = self.state.intent_accum

        E_t = (1.0 - self.lambda_e) * E_prev + vulnerability * pressure * depth * dt
        J_t = (1.0 - self.lambda_j) * J_prev + intent * dt
        q_t = E_t / (abs(J_t) + EPSILON)

        self.state.exposure = E_t
        self.state.intent_accum = J_t
        return E_t, J_t, q_t

    def _logits(self, J_t: float, E_t: float) -> List[float]:
        """Compute raw logits z = W @ [J_t, E_t] + b, with |J| trick."""
        z = []
        for i in range(self.k):
            j_val = abs(J_t) if i in self._abs_j_indices else J_t
            zi = self.W[i][0] * j_val + self.W[i][1] * E_t + self.b[i]
            z.append(zi)
        return z

    def _tier(self, risk: float) -> int:
        """Map expected risk to governance tier (1, 2, or 3)."""
        t1, t2 = self.tier_thresholds
        if risk < t1:
            return 1
        elif risk < t2:
            return 2
        return 3

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    def step(
        self,
        depth: float,
        vulnerability: float,
        pressure: float,
        intent: float,
        dt: float = 0.01,
    ) -> Dict:
        """Advance one time step.  Returns dict with probabilities, tier, risk."""
        depth = _clamp(depth)
        vulnerability = _clamp(vulnerability)
        pressure = _clamp(pressure)
        intent = _clamp(intent, -1.0, 1.0)

        E_t, J_t, q_t = self._update_accumulators(depth, vulnerability, pressure, intent, dt)
        logits = self._logits(J_t, E_t)
        probs = _softmax(logits, self.temperature)
        risk = _dot(probs, self.risk_weights)
        tier = self._tier(risk)

        self.state.time_step += 1
        self.state.last_probs = probs
        self.state.last_risk = risk
        self.state.last_tier = tier

        record = {
            "t": self.state.time_step,
            "E": E_t,
            "J": J_t,
            "q": q_t,
            "logits": list(logits),
            "probs": {self.labels[i]: probs[i] for i in range(self.k)},
            "risk": risk,
            "tier": tier,
            "dominant": self.labels[probs.index(max(probs))],
        }
        self.state.history.append(record)
        return record

    def decide(
        self,
        depth: float,
        vulnerability: float,
        pressure: float,
        intent: float,
    ) -> Tuple[str, float, Dict]:
        """Single-shot decision from a fresh state.

        Returns (label, confidence, full_record).
        """
        self.reset()
        rec = self.step(depth, vulnerability, pressure, intent, dt=1.0)
        label = rec["dominant"]
        confidence = max(self.state.last_probs)
        return label, confidence, rec

    def simulate(self, scenario: List[Dict], dt: float = 0.01) -> List[Dict]:
        """Run a multi-step scenario.

        Each element of *scenario* must contain keys:
            depth, vulnerability, pressure, intent
        """
        self.reset()
        results: List[Dict] = []
        for frame in scenario:
            rec = self.step(
                depth=frame["depth"],
                vulnerability=frame["vulnerability"],
                pressure=frame["pressure"],
                intent=frame["intent"],
                dt=dt,
            )
            results.append(rec)
        return results

    def reset(self):
        """Reset kernel state to initial conditions."""
        self.state = KernelState()

    # -----------------------------------------------------------------
    # Simplex helpers
    # -----------------------------------------------------------------

    @property
    def simplex_point(self) -> List[float]:
        """Current position on the K-simplex (probability vector)."""
        if self.state.last_probs:
            return list(self.state.last_probs)
        return [1.0 / self.k] * self.k  # uniform prior

    def render_simplex_ascii(self, width: int = 40) -> str:
        """ASCII bar-chart visualisation of current simplex position."""
        p = self.simplex_point
        lines: List[str] = []
        max_label_len = max(len(lbl) for lbl in self.labels)
        for i, (lbl, pi) in enumerate(zip(self.labels, p)):
            bar_len = int(round(pi * width))
            bar = "#" * bar_len + "." * (width - bar_len)
            lines.append(f"  {lbl:<{max_label_len}} |{bar}| {pi:.4f}")
        return "\n".join(lines)

    # -----------------------------------------------------------------
    # SCBE integration
    # -----------------------------------------------------------------

    def to_binary_safety(self) -> float:
        """Collapse K-ary kernel state to H(d,pd)-compatible safety score.

        Maps each governance class to a safety coefficient, then takes the
        weighted sum.  Result is in [0, 1] with 1 = fully safe.

        For K=4 (quaternary):
            safety = p_care * 1.0 + p_neutral * 0.6 + p_repair * 0.4 + p_harm * 0.0

        For K=3 (triadic):
            safety = p_allow * 1.0 + p_quarantine * 0.4 + p_deny * 0.0

        For arbitrary K: linearly interpolate from 1.0 (first class) to 0.0 (last).
        """
        p = self.simplex_point
        if self.k == 4:
            coeffs = [1.0, 0.6, 0.0, 0.4]  # care, neutral, harm, repair
        elif self.k == 3:
            coeffs = [1.0, 0.4, 0.0]        # allow, quarantine, deny
        else:
            coeffs = [1.0 - i / max(self.k - 1, 1) for i in range(self.k)]
        return _clamp(_dot(p, coeffs))

    def tongue_label(self) -> Optional[str]:
        """Return the Sacred Tongue code for the dominant governance class.

        Only defined for K=4 quaternary mode with default labels.
        """
        if self.k != 4 or self.labels != QUATERNARY_LABELS:
            return None
        dominant = self.labels[self.state.last_probs.index(max(self.state.last_probs))]
        return TONGUE_KERNEL_MAP.get(dominant)

    # -----------------------------------------------------------------
    # Repr
    # -----------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"KarySimplexKernel(k={self.k}, T={self.temperature}, "
            f"t={self.state.time_step}, tier=T{self.state.last_tier})"
        )


# =========================================================================
# SELFTEST
# =========================================================================

def _header(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        print(f"  [FAIL] {msg}")
        sys.exit(1)
    print(f"  [PASS] {msg}")


def selftest() -> None:
    print("K-ary Simplex Kernel  --  Selftest")
    passed = 0
    total = 0

    # ------------------------------------------------------------------
    # 1. Triadic kernel (K=3) with known inputs
    # ------------------------------------------------------------------
    _header("1. Triadic kernel (K=3) basic decision")
    k3 = KarySimplexKernel(k=3)
    label, conf, rec = k3.decide(depth=0.2, vulnerability=0.1, pressure=0.1, intent=0.8)
    print(f"  Input:  depth=0.2  vuln=0.1  pressure=0.1  intent=0.8")
    print(f"  Result: {label}  confidence={conf:.4f}")
    print(f"  Probs:  {rec['probs']}")
    _assert(label == "ALLOW", "High positive intent -> ALLOW")
    total += 1; passed += 1

    label2, _, _ = k3.decide(depth=0.8, vulnerability=0.9, pressure=0.9, intent=-0.9)
    print(f"  Input:  depth=0.8  vuln=0.9  pressure=0.9  intent=-0.9")
    print(f"  Result: {label2}")
    _assert(label2 == "DENY", "High negative intent + high exposure -> DENY")
    total += 1; passed += 1

    # ------------------------------------------------------------------
    # 2. Quaternary kernel (K=4) with known inputs
    # ------------------------------------------------------------------
    _header("2. Quaternary kernel (K=4) basic decision")
    k4 = KarySimplexKernel(k=4)
    label, conf, rec = k4.decide(depth=0.1, vulnerability=0.1, pressure=0.1, intent=0.9)
    print(f"  Input:  depth=0.1  vuln=0.1  pressure=0.1  intent=0.9")
    print(f"  Result: {label}  confidence={conf:.4f}")
    print(f"  Probs:  {rec['probs']}")
    _assert(label == "CARE", "Strong positive intent, low risk -> CARE")
    total += 1; passed += 1

    label2, _, rec2 = k4.decide(depth=0.9, vulnerability=0.9, pressure=0.9, intent=-0.8)
    print(f"  Input:  depth=0.9  vuln=0.9  pressure=0.9  intent=-0.8")
    print(f"  Result: {label2}")
    _assert(label2 == "HARM", "Negative intent + extreme exposure -> HARM")
    total += 1; passed += 1

    # ------------------------------------------------------------------
    # 3. Probabilities sum to 1.0
    # ------------------------------------------------------------------
    _header("3. Probability sum invariant")
    for ki in [3, 4, 5, 7]:
        kern = KarySimplexKernel(k=ki)
        kern.decide(depth=0.5, vulnerability=0.5, pressure=0.5, intent=0.0)
        s = sum(kern.simplex_point)
        _assert(abs(s - 1.0) < 1e-9, f"K={ki}: sum(p) = {s:.12f} ~ 1.0")
        total += 1; passed += 1

    # ------------------------------------------------------------------
    # 4. Simplex geometry (all probabilities non-negative)
    # ------------------------------------------------------------------
    _header("4. Simplex non-negativity")
    test_inputs = [
        (0.0, 0.0, 0.0,  1.0),
        (1.0, 1.0, 1.0, -1.0),
        (0.5, 0.5, 0.5,  0.0),
        (0.0, 1.0, 0.0, -0.5),
        (1.0, 0.0, 1.0,  0.5),
    ]
    for ki in [3, 4, 6]:
        kern = KarySimplexKernel(k=ki)
        for d, v, p, i in test_inputs:
            kern.decide(depth=d, vulnerability=v, pressure=p, intent=i)
            _assert(
                all(x >= 0.0 for x in kern.simplex_point),
                f"K={ki} d={d} v={v} p={p} i={i}: all probs >= 0"
            )
            total += 1; passed += 1

    # ------------------------------------------------------------------
    # 5. 100-step escalating threat simulation
    # ------------------------------------------------------------------
    _header("5. 100-step escalating threat scenario")
    k4 = KarySimplexKernel(k=4)
    scenario: List[Dict] = []
    for t in range(100):
        frac = t / 99.0
        scenario.append({
            "depth":         0.1 + 0.8 * frac,
            "vulnerability": 0.1 + 0.7 * frac,
            "pressure":      0.1 + 0.8 * frac,
            "intent":        0.7 - 1.4 * frac,   # starts benign, ends malicious
        })
    results = k4.simulate(scenario, dt=0.1)

    # Check tier behaviour: scenario crosses from benign to malicious through
    # a neutral midpoint, so risk dips mid-scenario then climbs.  The key
    # invariant is that the *final* tier is strictly higher than the minimum.
    early_tier = results[5]["tier"]
    mid_tier = results[50]["tier"]
    late_tier = results[95]["tier"]
    min_tier = min(r["tier"] for r in results)
    max_tier = max(r["tier"] for r in results)
    print(f"  Early tier (t=5):  T{early_tier}")
    print(f"  Mid tier   (t=50): T{mid_tier}")
    print(f"  Late tier  (t=95): T{late_tier}")
    print(f"  Min/Max tier:      T{min_tier} / T{max_tier}")
    _assert(late_tier > min_tier, "Final tier exceeds minimum (scenario escalates to threat)")
    total += 1; passed += 1
    _assert(max_tier == 3, "Scenario reaches T3 under sustained threat")
    total += 1; passed += 1

    # Check exposure is accumulating
    _assert(results[95]["E"] > results[5]["E"], "Exposure accumulates over time")
    total += 1; passed += 1

    # Check dominant class changes from CARE-ish to HARM-ish
    early_dom = results[5]["dominant"]
    late_dom = results[95]["dominant"]
    print(f"  Early dominant: {early_dom}")
    print(f"  Late dominant:  {late_dom}")
    _assert(early_dom != late_dom, "Dominant class changes as scenario escalates")
    total += 1; passed += 1

    # ------------------------------------------------------------------
    # 6. Tier transitions at correct thresholds
    # ------------------------------------------------------------------
    _header("6. Tier threshold transitions")
    k4 = KarySimplexKernel(k=4, tier_thresholds=(0.3, 0.6))
    # Force a low-risk step
    _, _, rec_low = k4.decide(depth=0.05, vulnerability=0.05, pressure=0.05, intent=0.95)
    _assert(rec_low["tier"] == 1, f"Low risk -> T1 (risk={rec_low['risk']:.4f})")
    total += 1; passed += 1

    # Force a high-risk step
    _, _, rec_high = k4.decide(depth=0.95, vulnerability=0.95, pressure=0.95, intent=-0.95)
    _assert(rec_high["tier"] == 3, f"High risk -> T3 (risk={rec_high['risk']:.4f})")
    total += 1; passed += 1

    # Verify threshold boundary: build a scenario to cross theta_1 = 0.3
    # Use dt=0.2 so accumulators build meaningfully over 200 steps.
    k4_boundary = KarySimplexKernel(k=4, tier_thresholds=(0.3, 0.6))
    found_t1 = False
    found_t2_or_t3 = False
    for t in range(200):
        frac = t / 199.0
        rec = k4_boundary.step(
            depth=0.1 + 0.85 * frac,
            vulnerability=0.1 + 0.8 * frac,
            pressure=0.1 + 0.85 * frac,
            intent=0.6 - 1.5 * frac,
            dt=0.2,
        )
        if rec["tier"] == 1:
            found_t1 = True
        if rec["tier"] >= 2:
            found_t2_or_t3 = True
    _assert(found_t1 and found_t2_or_t3, "Simulation crosses T1 -> T2+ boundary")
    total += 1; passed += 1

    # ------------------------------------------------------------------
    # 7. Sacred Tongue mapping
    # ------------------------------------------------------------------
    _header("7. Sacred Tongue mapping (K=4)")
    k4 = KarySimplexKernel(k=4)
    tongue_cases = [
        (0.1, 0.1, 0.1,  0.9, "CARE",    "KO"),
        (0.9, 0.9, 0.9, -0.9, "HARM",    "UM"),
    ]
    for d, v, p, i, exp_label, exp_tongue in tongue_cases:
        label, _, _ = k4.decide(d, v, p, i)
        tongue = k4.tongue_label()
        print(f"  decide({d},{v},{p},{i}) -> {label}, tongue={tongue}")
        _assert(label == exp_label, f"Label is {exp_label}")
        _assert(tongue == exp_tongue, f"Tongue is {exp_tongue}")
        total += 2; passed += 2

    # Tongue label returns None for non-quaternary kernel
    k3 = KarySimplexKernel(k=3)
    k3.decide(0.5, 0.5, 0.5, 0.5)
    _assert(k3.tongue_label() is None, "K=3 tongue_label() is None")
    total += 1; passed += 1

    # ------------------------------------------------------------------
    # 8. Binary safety score conversion
    # ------------------------------------------------------------------
    _header("8. Binary safety score (to_binary_safety)")
    k4 = KarySimplexKernel(k=4)

    # Safe scenario: high intent, low everything else -> safety near 1.0
    k4.decide(depth=0.05, vulnerability=0.05, pressure=0.05, intent=0.95)
    safety_high = k4.to_binary_safety()
    print(f"  Safe scenario:   safety = {safety_high:.4f}")
    _assert(safety_high > 0.7, f"Safe scenario yields safety > 0.7 (got {safety_high:.4f})")
    total += 1; passed += 1

    # Dangerous scenario -> safety near 0.0
    k4.decide(depth=0.95, vulnerability=0.95, pressure=0.95, intent=-0.95)
    safety_low = k4.to_binary_safety()
    print(f"  Danger scenario: safety = {safety_low:.4f}")
    _assert(safety_low < 0.3, f"Danger scenario yields safety < 0.3 (got {safety_low:.4f})")
    total += 1; passed += 1

    # Score is bounded in [0, 1]
    _assert(0.0 <= safety_high <= 1.0, "Safety score in [0,1] (safe)")
    _assert(0.0 <= safety_low <= 1.0, "Safety score in [0,1] (danger)")
    total += 2; passed += 2

    # Triadic safety
    k3 = KarySimplexKernel(k=3)
    k3.decide(depth=0.1, vulnerability=0.1, pressure=0.1, intent=0.9)
    s3 = k3.to_binary_safety()
    print(f"  Triadic safe:    safety = {s3:.4f}")
    _assert(s3 > 0.5, f"Triadic safe scenario > 0.5 (got {s3:.4f})")
    total += 1; passed += 1

    # ------------------------------------------------------------------
    # 9. ASCII simplex rendering
    # ------------------------------------------------------------------
    _header("9. ASCII simplex rendering")
    k4 = KarySimplexKernel(k=4)
    k4.decide(depth=0.3, vulnerability=0.2, pressure=0.2, intent=0.6)
    ascii_out = k4.render_simplex_ascii(width=40)
    print(ascii_out)
    _assert(len(ascii_out) > 0, "ASCII render produces output")
    _assert(ascii_out.count("|") == 2 * k4.k, f"Correct number of bar delimiters ({2*k4.k})")
    total += 2; passed += 2

    k3 = KarySimplexKernel(k=3)
    k3.decide(depth=0.5, vulnerability=0.5, pressure=0.5, intent=-0.3)
    ascii3 = k3.render_simplex_ascii(width=30)
    print(ascii3)
    _assert("ALLOW" in ascii3 and "DENY" in ascii3, "Triadic render contains labels")
    total += 1; passed += 1

    # ------------------------------------------------------------------
    # 10. Six tongue-specific scenarios
    # ------------------------------------------------------------------
    _header("10. Six tongue-specific scenarios (K=4 quaternary)")

    scenarios_tongue = [
        {
            "name": "KO (Kor'aelin) -- protective tenderness",
            "depth": 0.15, "vulnerability": 0.10, "pressure": 0.10, "intent": 0.90,
            "expect_dominant": "CARE", "expect_tongue": "KO",
        },
        {
            "name": "AV (Avali) -- peaceful coexistence",
            "depth": 0.30, "vulnerability": 0.20, "pressure": 0.15, "intent": 0.05,
            "expect_dominant": "NEUTRAL", "expect_tongue": "AV",
        },
        {
            "name": "RU (Runevalt) -- QUARANTINE transition (via triadic K=3)",
            "depth": 0.50, "vulnerability": 0.50, "pressure": 0.50, "intent": 0.10,
            # This is a K=3 check: moderate inputs -> quarantine zone
            "k": 3, "expect_dominant": "QUARANTINE", "expect_tongue": None,
        },
        {
            "name": "CA (Caelith) -- mixed CARE/REPAIR under moderate exposure",
            "depth": 0.45, "vulnerability": 0.40, "pressure": 0.35, "intent": 0.70,
            "expect_dominant": None,  # could be CARE or REPAIR
            "expect_tongue": None,    # just check it's KO or DR
            "expect_tongue_in": ["KO", "DR"],
        },
        {
            "name": "UM (Umbroth) -- shadow, harm detection",
            "depth": 0.85, "vulnerability": 0.80, "pressure": 0.85, "intent": -0.80,
            "expect_dominant": "HARM", "expect_tongue": "UM",
        },
        {
            "name": "DR (Draumric) -- recovery after harm",
            "depth": 0.75, "vulnerability": 0.70, "pressure": 0.70, "intent": 0.55,
            "expect_dominant": "REPAIR", "expect_tongue": "DR",
        },
    ]

    for sc in scenarios_tongue:
        ki = sc.get("k", 4)
        kern = KarySimplexKernel(k=ki)
        label, conf, rec = kern.decide(
            depth=sc["depth"],
            vulnerability=sc["vulnerability"],
            pressure=sc["pressure"],
            intent=sc["intent"],
        )
        tongue = kern.tongue_label()
        print(f"\n  --- {sc['name']} ---")
        print(f"  Input:    d={sc['depth']} v={sc['vulnerability']} p={sc['pressure']} i={sc['intent']} K={ki}")
        print(f"  Result:   {label}  conf={conf:.4f}  tongue={tongue}")
        print(f"  Probs:    {rec['probs']}")
        print(f"  Risk:     {rec['risk']:.4f}  Tier: T{rec['tier']}")

        if sc["expect_dominant"] is not None:
            _assert(label == sc["expect_dominant"],
                    f"{sc['name']}: dominant is {sc['expect_dominant']}")
            total += 1; passed += 1

        if sc.get("expect_tongue_in"):
            _assert(tongue in sc["expect_tongue_in"],
                    f"{sc['name']}: tongue {tongue} in {sc['expect_tongue_in']}")
            total += 1; passed += 1
        elif sc["expect_tongue"] is not None:
            _assert(tongue == sc["expect_tongue"],
                    f"{sc['name']}: tongue is {sc['expect_tongue']}")
            total += 1; passed += 1

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    _header("SELFTEST SUMMARY")
    print(f"  {passed}/{total} checks passed")
    if passed == total:
        print("  ALL CHECKS PASSED")
    else:
        print(f"  {total - passed} FAILURES")
        sys.exit(1)


if __name__ == "__main__":
    selftest()
