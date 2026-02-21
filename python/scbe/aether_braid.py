"""
Aether Braid: Mirror-Shift-Refactor Algebra + FSGS Hybrid Automaton
=====================================================================

Crystal Cranium v3.0.0 Section 6.3-6.4

Implements the hybrid dynamical system coupling continuous 21D state
with discrete governance modes. The Mirror-Shift-Refactor (MSR)
algebra provides the generators, and the Four-Symbol Governance
System (FSGS) defines the control alphabet.

MSR Algebra Generators:
    M   — Mirror operator         (M² = I)
    S(φ) — Shift by golden ratio  (continuous group)
    Π   — Refactor projector      (Π² = Π, idempotent)
    0   — Zero / annihilator      (absorbing element)

FSGS Control Alphabet:
    σ = (m, s) ∈ {0,1}²  →  4 governance modes:
    (0,0) → RUN       Normal execution
    (0,1) → HOLD      Pause and inspect
    (1,0) → QUAR      Quarantine thought
    (1,1) → ROLLBACK  Revert to last safe state

Update Rule (Section 6.4):
    x⁺ = Π_T(x + m · α(x) · η(s) · d(x))

    where:
        Π_T     = Trust Tube projection
        m       = movement bit (0=halt, 1=step)
        α(x)    = adaptive learning rate from trust ring
        η(s)    = safety dampening from suppression bit
        d(x)    = descent direction from MSR braid

9-State Phase Diagram:
    Resonant Lock, Zero-G Hover, Creative Tension,
    Collapse, Recovery, Deep Sleep, Alarm,
    Braid Weave, Harmonic Bloom

Author: Issac Davis
Version: 3.0.0
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any, Callable
from enum import Enum
import hashlib
import time

# =============================================================================
# Constants
# =============================================================================

PHI = (1 + np.sqrt(5)) / 2          # Golden ratio φ ≈ 1.618
PHI_INV = 2 / (1 + np.sqrt(5))      # 1/φ ≈ 0.618
R_FIFTH = 3 / 2                      # Perfect fifth
PYTHAGOREAN_COMMA = 531441 / 524288  # 3^12 / 2^19


# =============================================================================
# Enums
# =============================================================================

class GovernanceMode(Enum):
    """FSGS governance modes (Section 6.4)."""
    RUN = "RUN"            # (0,0) — Normal execution
    HOLD = "HOLD"          # (0,1) — Pause and inspect
    QUAR = "QUAR"          # (1,0) — Quarantine thought
    ROLLBACK = "ROLLBACK"  # (1,1) — Revert to last safe state


class PhaseState(Enum):
    """9-state phase diagram (Section 6.3)."""
    RESONANT_LOCK = "resonant_lock"       # Stable harmonic convergence
    ZERO_G_HOVER = "zero_g_hover"         # Floating — no net force
    CREATIVE_TENSION = "creative_tension" # Productive instability
    COLLAPSE = "collapse"                 # Thought structure failure
    RECOVERY = "recovery"                 # Rebuilding from collapse
    DEEP_SLEEP = "deep_sleep"             # Minimal activity, self-repair
    ALARM = "alarm"                       # Security trigger
    BRAID_WEAVE = "braid_weave"           # MSR generators active
    HARMONIC_BLOOM = "harmonic_bloom"     # Optimal creative output


class FluxState(Enum):
    """Dimensional breathing states."""
    POLLY = 1.0   # ν ≈ 1.0 — Full capability
    QUASI = 0.5   # ν ≈ 0.5 — Defensive
    DEMI = 0.1    # ν ≈ 0.1 — Survival


# =============================================================================
# FSGS Control Symbol
# =============================================================================

@dataclass
class FSGSSymbol:
    """
    FSGS control symbol σ = (m, s) ∈ {0,1}².

    m = movement bit: 0 = halt, 1 = step forward
    s = suppression bit: 0 = normal, 1 = dampen/suppress
    """
    m: int  # Movement bit
    s: int  # Suppression bit

    def __post_init__(self):
        assert self.m in (0, 1), f"m must be 0 or 1, got {self.m}"
        assert self.s in (0, 1), f"s must be 0 or 1, got {self.s}"

    @property
    def mode(self) -> GovernanceMode:
        """Map (m, s) → governance mode."""
        return _FSGS_MAP[(self.m, self.s)]

    @property
    def label(self) -> str:
        return f"({self.m},{self.s})→{self.mode.value}"


_FSGS_MAP: Dict[Tuple[int, int], GovernanceMode] = {
    (0, 0): GovernanceMode.RUN,
    (0, 1): GovernanceMode.HOLD,
    (1, 0): GovernanceMode.QUAR,
    (1, 1): GovernanceMode.ROLLBACK,
}


def classify_to_fsgs(x: np.ndarray, threshold_quar: float = 0.7,
                     threshold_hold: float = 0.3) -> FSGSSymbol:
    """
    Classify a 21D state vector to an FSGS control symbol.

    Uses the flux dimensions (indices 12-14) and risk norm to
    determine (m, s):
        - Low risk, low flux → RUN (0,0)
        - Low risk, high flux → HOLD (0,1)
        - High risk, low flux → QUAR (1,0)
        - High risk, high flux → ROLLBACK (1,1)
    """
    risk_norm = np.linalg.norm(x[:6])  # Hyperbolic distance proxy
    flux_norm = np.linalg.norm(x[12:15]) if len(x) > 14 else 0.0

    m = 1 if risk_norm > threshold_quar else 0
    s = 1 if flux_norm > threshold_hold else 0

    return FSGSSymbol(m=m, s=s)


# =============================================================================
# MSR Algebra: Mirror-Shift-Refactor
# =============================================================================

class MirrorShiftRefactor:
    """
    Mirror-Shift-Refactor algebra (Section 6.3).

    Four generators operating on state vectors x ∈ ℝ²¹:
        M      — Mirror: negates specified dimensions (M² = I)
        S(φ)   — Shift: translates by φ-scaled direction
        Π      — Refactor: projects onto trust subspace (Π² = Π)
        0      — Zero: maps to origin (absorbing element)

    Relations:
        M² = I          (involution)
        Π² = Π          (idempotent projection)
        M·Π = Π·M       (commuting under mirror)
        0·X = 0         (annihilation)

    The braid signature of MSR cycles has empirical fractal
    dimension d ≈ 1.614 ± 0.08, close to φ ≈ 1.618.
    """

    def __init__(self, dim: int = 21, mirror_dims: Optional[List[int]] = None,
                 trust_subspace_dim: int = 6):
        self.dim = dim
        self.mirror_dims = mirror_dims or list(range(6, 12))  # Mirror phase dims
        self.trust_dim = trust_subspace_dim

        # Build mirror matrix M (diagonal with -1 on mirror dims)
        self._M = np.eye(dim)
        for d in self.mirror_dims:
            if d < dim:
                self._M[d, d] = -1.0

        # Build refactor projector Π (projects onto first trust_dim dims)
        self._Pi = np.zeros((dim, dim))
        for d in range(min(trust_dim, dim)):
            self._Pi[d, d] = 1.0

    # ---- Generators ----

    def mirror(self, x: np.ndarray) -> np.ndarray:
        """M(x): Negate mirror dimensions. M² = I."""
        return self._M @ x

    def shift(self, x: np.ndarray, scale: float = PHI) -> np.ndarray:
        """S(φ)(x): Shift by golden-ratio-scaled descent direction."""
        direction = self._descent_direction(x)
        return x + scale * direction

    def refactor(self, x: np.ndarray) -> np.ndarray:
        """Π(x): Project onto trust subspace. Π² = Π."""
        return self._Pi @ x

    def zero(self, x: np.ndarray) -> np.ndarray:
        """0(x): Map to origin (absorbing element)."""
        return np.zeros(self.dim)

    # ---- Composite Operations ----

    def msr_step(self, x: np.ndarray) -> np.ndarray:
        """
        One MSR braid step: M → S(φ) → Π (Refactor).

        This is the core operation that produces the φ-dimensional
        fractal signature over many iterations.
        """
        x = self.mirror(x)
        x = self.shift(x)
        x = self.refactor(x)
        return x

    def msr_cycle(self, x: np.ndarray, n_steps: int = 500) -> List[np.ndarray]:
        """
        Run n_steps of MSR braid iteration.

        Returns the trajectory for fractal dimension analysis.
        """
        trajectory = [x.copy()]
        for _ in range(n_steps):
            x = self.msr_step(x)
            trajectory.append(x.copy())
        return trajectory

    def braid_signature(self, trajectory: List[np.ndarray]) -> float:
        """
        Compute box-counting fractal dimension of an MSR trajectory.

        The spec reports d ≈ 1.614 ± 0.08 for 500-step cycles
        with tube_radius = 0.15.

        Returns:
            Estimated fractal dimension
        """
        if len(trajectory) < 10:
            return 0.0

        # Use first 3 dimensions for box-counting (3D projection)
        points = np.array([t[:3] for t in trajectory])

        # Remove NaN/Inf
        valid = np.all(np.isfinite(points), axis=1)
        points = points[valid]
        if len(points) < 10:
            return 0.0

        # Box-counting algorithm
        min_coords = points.min(axis=0)
        max_coords = points.max(axis=0)
        extent = max_coords - min_coords
        max_extent = max(extent.max(), 1e-10)

        box_sizes = []
        box_counts = []

        for k in range(2, 8):
            n_boxes = 2 ** k
            box_size = max_extent / n_boxes

            # Count occupied boxes
            indices = ((points - min_coords) / box_size).astype(int)
            indices = np.clip(indices, 0, n_boxes - 1)
            unique_boxes = set(map(tuple, indices))
            count = len(unique_boxes)

            if count > 0:
                box_sizes.append(box_size)
                box_counts.append(count)

        if len(box_sizes) < 2:
            return 0.0

        # Linear regression on log-log plot
        log_sizes = np.log(box_sizes)
        log_counts = np.log(box_counts)

        # d = -slope of log(count) vs log(size)
        coeffs = np.polyfit(log_sizes, log_counts, 1)
        fractal_dim = -coeffs[0]

        return float(fractal_dim)

    # ---- Internal ----

    def _descent_direction(self, x: np.ndarray) -> np.ndarray:
        """
        Compute descent direction d(x) for the shift operator.

        Uses the gradient of the Harmonic Wall potential scaled
        by the inverse golden ratio for stability.
        """
        norm = np.linalg.norm(x[:6])
        if norm < 1e-10:
            return np.zeros(self.dim)

        # Gradient of H(d*) = exp(d*²) is 2*d*·exp(d*²)·x_hat
        grad_H = 2.0 * norm * np.exp(norm ** 2)
        direction = np.zeros(self.dim)
        direction[:6] = -PHI_INV * grad_H * x[:6] / norm

        return direction

    # ---- Verification ----

    def verify_relations(self) -> Dict[str, bool]:
        """Verify MSR algebra relations."""
        x = np.random.randn(self.dim) * 0.3
        results = {}

        # M² = I
        results["M_squared_is_I"] = np.allclose(
            self.mirror(self.mirror(x)), x, atol=1e-10
        )

        # Π² = Π
        pi_x = self.refactor(x)
        results["Pi_squared_is_Pi"] = np.allclose(
            self.refactor(pi_x), pi_x, atol=1e-10
        )

        # 0·X = 0
        results["zero_absorbs"] = np.allclose(
            self.zero(x), np.zeros(self.dim), atol=1e-10
        )

        # M·Π = Π·M (commutation)
        results["M_Pi_commute"] = np.allclose(
            self.mirror(self.refactor(x)),
            self.refactor(self.mirror(x)),
            atol=1e-10
        )

        return results


# =============================================================================
# Hybrid Automaton: FSGS State Machine
# =============================================================================

@dataclass
class HybridState:
    """
    Combined continuous + discrete state of the hybrid automaton.

    Continuous: x ∈ ℝ²¹ (21D state vector)
    Discrete: q ∈ {RUN, HOLD, QUAR, ROLLBACK}
    Phase: p ∈ {9-state phase diagram}
    """
    x: np.ndarray                       # 21D continuous state
    q: GovernanceMode = GovernanceMode.RUN
    phase: PhaseState = PhaseState.RESONANT_LOCK
    flux: FluxState = FluxState.POLLY
    energy: float = 0.0                 # Accumulated energy cost
    step_count: int = 0                 # Steps since last mode change
    safe_checkpoint: Optional[np.ndarray] = None  # Last known safe state

    def snapshot(self) -> 'HybridState':
        """Create a checkpoint of current state."""
        return HybridState(
            x=self.x.copy(),
            q=self.q,
            phase=self.phase,
            flux=self.flux,
            energy=self.energy,
            step_count=self.step_count,
            safe_checkpoint=self.safe_checkpoint.copy() if self.safe_checkpoint is not None else None,
        )


class FSGSAutomaton:
    """
    FSGS Hybrid Automaton (Section 6.4).

    Couples continuous dynamics (MSR algebra on 21D state) with
    discrete mode transitions (FSGS 2-bit symbols).

    The update rule:
        x⁺ = Π_T(x + m · α(x) · η(s) · d(x))

    where:
        Π_T    = Trust Tube projection (closest rail ± ε)
        m      = movement bit from FSGS
        α(x)   = adaptive learning rate (trust-ring dependent)
        η(s)   = safety dampening factor (1.0 or φ⁻¹)
        d(x)   = descent direction from MSR braid
    """

    def __init__(self, dim: int = 21, tube_radius: float = 0.15):
        self.dim = dim
        self.tube_radius = tube_radius
        self.msr = MirrorShiftRefactor(dim=dim)
        self.history: List[Dict[str, Any]] = []

        # Trust ring learning rates (Section 2.1)
        self._alpha_map = {
            "CORE": 1.0,       # Full speed
            "INNER": PHI_INV,  # 0.618
            "OUTER": PHI_INV ** 2,  # 0.382
            "WALL": 0.0,       # Blocked
        }

    def classify_trust_ring(self, x: np.ndarray) -> str:
        """Classify 21D state into trust ring based on hyperbolic distance."""
        r = np.linalg.norm(x[:6])
        if r < 0.3:
            return "CORE"
        elif r < 0.7:
            return "INNER"
        elif r < 0.9:
            return "OUTER"
        else:
            return "WALL"

    def adaptive_alpha(self, x: np.ndarray) -> float:
        """Compute adaptive learning rate α(x) based on trust ring."""
        ring = self.classify_trust_ring(x)
        return self._alpha_map.get(ring, 0.0)

    def safety_eta(self, s: int) -> float:
        """Compute safety dampening η(s)."""
        return PHI_INV if s == 1 else 1.0  # Dampen by 1/φ when suppressed

    def step(self, state: HybridState, sigma: Optional[FSGSSymbol] = None) -> HybridState:
        """
        Execute one step of the hybrid automaton.

        Args:
            state: Current hybrid state
            sigma: FSGS control symbol (auto-classified if None)

        Returns:
            Updated hybrid state
        """
        # Auto-classify if no symbol provided
        if sigma is None:
            sigma = classify_to_fsgs(state.x)

        mode = sigma.mode

        # ---- Mode-dependent logic ----

        if mode == GovernanceMode.ROLLBACK:
            # Revert to last safe checkpoint
            if state.safe_checkpoint is not None:
                new_x = state.safe_checkpoint.copy()
            else:
                new_x = np.zeros(self.dim)
            new_phase = PhaseState.RECOVERY
            new_q = GovernanceMode.HOLD

        elif mode == GovernanceMode.QUAR:
            # Quarantine: project to core (zero phase/flux/audit dims)
            new_x = self.msr.refactor(state.x)
            new_phase = PhaseState.ALARM
            new_q = GovernanceMode.QUAR

        elif mode == GovernanceMode.HOLD:
            # Hold: no movement, inspect state
            new_x = state.x.copy()
            new_phase = PhaseState.ZERO_G_HOVER
            new_q = GovernanceMode.HOLD

        else:  # RUN
            # Apply update rule: x⁺ = Π_T(x + m·α(x)·η(s)·d(x))
            m = sigma.m
            alpha = self.adaptive_alpha(state.x)
            eta = self.safety_eta(sigma.s)
            d = self.msr._descent_direction(state.x)

            raw_update = state.x + m * alpha * eta * d

            # Trust Tube projection (simplified — full version in harmonic_scaling_law)
            new_x = self._project_to_ball(raw_update)
            new_phase = self._classify_phase(new_x, state)
            new_q = GovernanceMode.RUN

        # ---- Compute energy cost ----
        energy_delta = np.linalg.norm(new_x - state.x)

        # ---- Save checkpoint if in safe zone ----
        safe_cp = state.safe_checkpoint
        ring = self.classify_trust_ring(new_x)
        if ring in ("CORE", "INNER"):
            safe_cp = new_x.copy()

        new_state = HybridState(
            x=new_x,
            q=new_q,
            phase=new_phase,
            flux=state.flux,
            energy=state.energy + energy_delta,
            step_count=state.step_count + 1,
            safe_checkpoint=safe_cp,
        )

        # Log
        self.history.append({
            "step": new_state.step_count,
            "sigma": sigma.label,
            "mode": new_q.value,
            "phase": new_phase.value,
            "ring": ring,
            "energy_delta": energy_delta,
            "total_energy": new_state.energy,
        })

        return new_state

    def run(self, initial_x: np.ndarray, n_steps: int = 100) -> List[HybridState]:
        """Run the automaton for n_steps, returning the full trajectory."""
        state = HybridState(x=initial_x.copy(), safe_checkpoint=initial_x.copy())
        trajectory = [state]

        for _ in range(n_steps):
            state = self.step(state)
            trajectory.append(state)

            # Emergency: if in WALL, force ROLLBACK
            if self.classify_trust_ring(state.x) == "WALL":
                sigma_rb = FSGSSymbol(m=1, s=1)
                state = self.step(state, sigma=sigma_rb)
                trajectory.append(state)

        return trajectory

    def _project_to_ball(self, x: np.ndarray) -> np.ndarray:
        """Ensure x stays inside the Poincaré ball (||x[:6]|| < 1)."""
        result = x.copy()
        hyp_norm = np.linalg.norm(result[:6])
        if hyp_norm >= 0.99:
            result[:6] = result[:6] * 0.95 / hyp_norm
        return result

    def _classify_phase(self, x: np.ndarray, prev_state: HybridState) -> PhaseState:
        """
        Classify into 9-state phase diagram based on dynamics.

        Uses energy gradient, trust ring, and flux state to determine phase.
        """
        r = np.linalg.norm(x[:6])
        energy_grad = np.linalg.norm(x - prev_state.x)
        flux_val = prev_state.flux.value

        # Phase classification logic
        if r < 0.1 and energy_grad < 0.01:
            return PhaseState.RESONANT_LOCK
        elif r < 0.3 and energy_grad < 0.05:
            return PhaseState.HARMONIC_BLOOM
        elif energy_grad < 0.001:
            return PhaseState.ZERO_G_HOVER
        elif r > 0.8:
            return PhaseState.ALARM
        elif energy_grad > 0.5:
            return PhaseState.COLLAPSE
        elif prev_state.phase == PhaseState.COLLAPSE:
            return PhaseState.RECOVERY
        elif 0.3 < r < 0.6 and energy_grad > 0.1:
            return PhaseState.CREATIVE_TENSION
        elif flux_val < 0.3:
            return PhaseState.DEEP_SLEEP
        else:
            return PhaseState.BRAID_WEAVE


# =============================================================================
# Transition Function δ(q, σ, x)
# =============================================================================

def transition_function(
    q: GovernanceMode,
    sigma: FSGSSymbol,
    x: np.ndarray
) -> GovernanceMode:
    """
    Discrete transition function δ(q, σ, x).

    Determines the next governance mode based on:
        - Current mode q
        - Control symbol σ = (m, s)
        - Continuous state x (trust ring)

    Section 6.4: The transition table is designed so that
    ROLLBACK is always reachable from any state (safety liveness),
    and RUN requires passing through HOLD (recovery handshake).
    """
    ring_r = np.linalg.norm(x[:6])

    # Wall → always ROLLBACK
    if ring_r >= 0.9:
        return GovernanceMode.ROLLBACK

    mode = sigma.mode

    # From ROLLBACK, must go through HOLD before RUN
    if q == GovernanceMode.ROLLBACK:
        if mode == GovernanceMode.RUN:
            return GovernanceMode.HOLD  # Force inspection first
        return mode

    # From QUAR, can only go to HOLD or ROLLBACK
    if q == GovernanceMode.QUAR:
        if mode == GovernanceMode.RUN:
            return GovernanceMode.HOLD
        return mode

    return mode


# =============================================================================
# Integration Pipeline
# =============================================================================

def think_step(
    intent_21d: np.ndarray,
    automaton: FSGSAutomaton,
    state: HybridState,
) -> Tuple[HybridState, Dict[str, Any]]:
    """
    One step of the think() pipeline:

        embed_to_21d(intent) → classify_to_fsgs(x) → step(state, rails) → mode_to_action(q)

    This wraps the existing governance() function inside the hybrid automaton
    where continuous state x ∈ ℝ²¹ evolves via the update rule, and discrete
    mode q transitions via δ(q, σ, x).

    Args:
        intent_21d: Intent embedded in 21D space
        automaton: The FSGS hybrid automaton
        state: Current hybrid state

    Returns:
        (new_state, action_dict)
    """
    # Blend intent with current state
    blended = state.x * 0.7 + intent_21d * 0.3

    # Classify to FSGS
    sigma = classify_to_fsgs(blended)

    # Apply transition function
    next_mode = transition_function(state.q, sigma, blended)

    # Override sigma if transition function disagrees
    if next_mode != sigma.mode:
        # Find the sigma that maps to next_mode
        for (m, s), mode in _FSGS_MAP.items():
            if mode == next_mode:
                sigma = FSGSSymbol(m=m, s=s)
                break

    # Step the automaton with blended state
    temp_state = HybridState(
        x=blended,
        q=state.q,
        phase=state.phase,
        flux=state.flux,
        energy=state.energy,
        step_count=state.step_count,
        safe_checkpoint=state.safe_checkpoint,
    )
    new_state = automaton.step(temp_state, sigma=sigma)

    # Build action from mode
    action = mode_to_action(new_state.q, new_state.phase)

    return new_state, action


def mode_to_action(q: GovernanceMode, phase: PhaseState) -> Dict[str, Any]:
    """
    Map governance mode + phase state to an action dict.

    This is the output of Layer 13's decision pipeline.
    """
    actions = {
        GovernanceMode.RUN: {
            "execute": True,
            "inspect": False,
            "rollback": False,
            "latency_budget_ms": 5 if phase == PhaseState.RESONANT_LOCK else 30,
        },
        GovernanceMode.HOLD: {
            "execute": False,
            "inspect": True,
            "rollback": False,
            "latency_budget_ms": 200,
        },
        GovernanceMode.QUAR: {
            "execute": False,
            "inspect": True,
            "rollback": False,
            "latency_budget_ms": 500,
        },
        GovernanceMode.ROLLBACK: {
            "execute": False,
            "inspect": False,
            "rollback": True,
            "latency_budget_ms": 50,
        },
    }

    action = actions.get(q, actions[GovernanceMode.HOLD]).copy()
    action["mode"] = q.value
    action["phase"] = phase.value
    return action


# =============================================================================
# Self-Test
# =============================================================================

def self_test() -> Dict[str, Any]:
    """Run self-tests on the Aether Braid module."""
    results = {}
    passed = 0
    total = 0

    # Test 1: MSR algebra relations
    total += 1
    msr = MirrorShiftRefactor(dim=21)
    relations = msr.verify_relations()
    if all(relations.values()):
        passed += 1
        results["msr_relations"] = "PASS (M²=I, Π²=Π, 0·X=0, M·Π=Π·M)"
    else:
        results["msr_relations"] = f"FAIL ({relations})"

    # Test 2: FSGS symbol mapping
    total += 1
    symbols_ok = (
        FSGSSymbol(0, 0).mode == GovernanceMode.RUN and
        FSGSSymbol(0, 1).mode == GovernanceMode.HOLD and
        FSGSSymbol(1, 0).mode == GovernanceMode.QUAR and
        FSGSSymbol(1, 1).mode == GovernanceMode.ROLLBACK
    )
    if symbols_ok:
        passed += 1
        results["fsgs_mapping"] = "PASS (all 4 modes mapped correctly)"
    else:
        results["fsgs_mapping"] = "FAIL"

    # Test 3: Hybrid automaton step
    total += 1
    try:
        auto = FSGSAutomaton(dim=21)
        x0 = np.random.randn(21) * 0.1
        state = HybridState(x=x0, safe_checkpoint=x0.copy())
        new_state = auto.step(state)
        if new_state.step_count == 1:
            passed += 1
            results["automaton_step"] = f"PASS (mode={new_state.q.value})"
        else:
            results["automaton_step"] = "FAIL"
    except Exception as e:
        results["automaton_step"] = f"FAIL ({e})"

    # Test 4: ROLLBACK from WALL
    total += 1
    try:
        x_wall = np.zeros(21)
        x_wall[:6] = 0.95  # Near wall
        state_wall = HybridState(x=x_wall, safe_checkpoint=np.zeros(21))
        sigma_rb = FSGSSymbol(m=1, s=1)
        rb_state = auto.step(state_wall, sigma=sigma_rb)
        if rb_state.phase == PhaseState.RECOVERY:
            passed += 1
            results["rollback_from_wall"] = "PASS (reverted to checkpoint)"
        else:
            results["rollback_from_wall"] = f"FAIL (phase={rb_state.phase.value})"
    except Exception as e:
        results["rollback_from_wall"] = f"FAIL ({e})"

    # Test 5: MSR braid signature
    total += 1
    try:
        x_test = np.random.randn(21) * 0.2
        trajectory = msr.msr_cycle(x_test, n_steps=200)
        fractal_d = msr.braid_signature(trajectory)
        if 0.5 < fractal_d < 3.0:
            passed += 1
            results["braid_signature"] = f"PASS (d={fractal_d:.3f})"
        else:
            results["braid_signature"] = f"FAIL (d={fractal_d:.3f} out of range)"
    except Exception as e:
        results["braid_signature"] = f"FAIL ({e})"

    # Test 6: Transition function safety (WALL always → ROLLBACK)
    total += 1
    x_danger = np.zeros(21)
    x_danger[0] = 0.95
    all_rollback = True
    for m in (0, 1):
        for s in (0, 1):
            next_q = transition_function(GovernanceMode.RUN, FSGSSymbol(m, s), x_danger)
            if next_q != GovernanceMode.ROLLBACK:
                all_rollback = False
    if all_rollback:
        passed += 1
        results["wall_safety"] = "PASS (WALL always → ROLLBACK)"
    else:
        results["wall_safety"] = "FAIL"

    # Test 7: think_step pipeline
    total += 1
    try:
        auto2 = FSGSAutomaton(dim=21)
        x_safe = np.random.randn(21) * 0.05
        state_safe = HybridState(x=x_safe, safe_checkpoint=x_safe.copy())
        intent = np.random.randn(21) * 0.1
        new_s, action = think_step(intent, auto2, state_safe)
        if "mode" in action and "phase" in action:
            passed += 1
            results["think_pipeline"] = f"PASS (mode={action['mode']}, phase={action['phase']})"
        else:
            results["think_pipeline"] = "FAIL (missing keys)"
    except Exception as e:
        results["think_pipeline"] = f"FAIL ({e})"

    return {
        "passed": passed,
        "total": total,
        "results": results,
        "rate": f"{passed}/{total} ({100 * passed / max(1, total):.0f}%)",
    }


if __name__ == "__main__":
    print("=" * 60)
    print("Aether Braid — MSR Algebra + FSGS Hybrid Automaton")
    print("=" * 60)

    test_results = self_test()
    for name, result in test_results["results"].items():
        print(f"  {name}: {result}")
    print("-" * 60)
    print(f"  TOTAL: {test_results['rate']}")
