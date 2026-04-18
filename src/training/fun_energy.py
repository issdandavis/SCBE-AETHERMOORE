"""
fun_energy.py

Fun as a thermodynamic energy quotient — not a static attractor.

CORE FORMULA:
  F(t) = V(t) / (C(t) - R(t) + epsilon)

  V(t) = value gained         — governance improvement + task quality
  C(t) = compute cost         — capped at system budget, NOT full power
  R(t) = energy recovered     — via echolation: phase-coherent reflection
                                 from established layer phases

SYSTEM CONSTRAINTS (fixed, normalized):
  P_budget  = 1.0   — total capacity envelope (the hard ceiling)
  P_base    = 0.10  — steady-state kinetic engagement (trickle mode)
  P_burst   = 0.72  — peak burst amplitude
  P_recover = 0.18  — budget reserved for echo recovery
  (P_base + P_burst + P_recover = 1.0 — must sum to budget)

FLOW DYNAMICS:
  Most training steps run at P_base (low kinetic engagement, steady stream).
  When accumulated fun-potential exceeds burst_threshold, a burst pulse fires:
    1. Forward pulse: energy P_burst propagates through layers 1..14
    2. Each layer absorbs and reflects based on phase coherence
    3. Echo returns carry frequency-shifted information about layer state
    4. Echo energy is harvested as R(t) — reduces net cost of the burst
    5. System returns to P_base; burst_potential resets

ECHOLATION (reverse frequency mapping):
  Inspired by bat sonar. The forward pulse carries a frequency signature.
  Each layer has an established phase (built from prior training steps).
  When the pulse hits a layer whose phase matches, constructive interference:
    high coherence → high echo energy → high R → lower net cost → higher fun
  When the pulse hits a novel layer (phase mismatch):
    low coherence → low echo energy → high net cost → lower fun (novel territory)

  This creates natural curriculum pressure:
    - Familiar territory: cheap (high echo recovery), safe to process continuously
    - Novel territory: expensive (low echo), triggers conservative engagement
    - FUN territory: novel enough for high V, coherent enough for high R

PULSE PATTERN FORMATION:
  Bursts fire at phi-spaced intervals: T, T*phi, T*phi^2, ...
  creating a non-periodic but structured burst pattern.
  The phi-spacing ensures no two bursts share a harmonic — avoiding
  destructive resonance buildup in any single layer.

  Within a burst, the pulse envelope follows a Gaussian:
    P(t) = P_base + (P_burst - P_base) * exp(-( (t-t0)/width )^2)

  The 14-layer propagation delay staggers the pulse arrival at each layer:
    arrival_l = t0 + l * propagation_delay
  so the burst forms a travelling wave through the pipeline, not a
  simultaneous spike across all layers.

TRAINING LOSS INTEGRATION:
  L_fun = -log(clamp(F(t), min=epsilon))
  This is minimized when F(t) is large (high value, low net cost).

  Combined with gyro dual loss:
    L = alpha * L_sonar + (1-alpha) * L_gov + fun_weight * L_fun

  But the SCHEDULER controls which steps run at P_base (most steps)
  vs P_burst (occasional pulses). The dual loss only runs at P_burst.
  P_base steps run sonar-only (cheap, fast, low-KE).
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

# =============================================================================
# GOVERNANCE TIER — phase-gate mapping for kinetic modes
# =============================================================================


class GovernanceTier(str, Enum):
    """
    SCBE governance tiers mapped to kinetic scheduler modes.

    ALLOW      ← TRICKLE mode: safe steady-state, low kinetic engagement.
                 Loss runs at baseline weight. No extra scrutiny.

    QUARANTINE ← BURST mode: elevated energy, high-value pulse but needs
                 governance scrutiny before it propagates. A governance
                 penalty term is added to the loss to force the model to
                 justify the energy expenditure with real value.

    ESCALATE   ← ECHO mode: phase-recovery territory, novel pattern
                 formation. Learning rate effectively clamped (loss scaled
                 down to P_recover fraction). The system is mapping new
                 territory — watch but don't suppress aggressively.

    OVERSIGHT  ← COLLAPSE condition (any mode): F drops below oversight_floor
                 for N consecutive steps. Model is energy-negative — consuming
                 more than it recovers with near-zero value. A large loss spike
                 signals halt / human intervention. NOT a normal training state.
    """

    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    ESCALATE = "ESCALATE"
    OVERSIGHT = "OVERSIGHT"


# Map from kinetic mode string → default governance tier (primary signal)
_MODE_TO_TIER: Dict[str, GovernanceTier] = {
    "trickle": GovernanceTier.ALLOW,
    "burst": GovernanceTier.QUARANTINE,
    "echo": GovernanceTier.ESCALATE,
}

# Loss scale factors per tier
TIER_LOSS_SCALE: Dict[GovernanceTier, float] = {
    GovernanceTier.ALLOW: 1.0,
    GovernanceTier.QUARANTINE: 1.0,  # governance penalty added separately
    GovernanceTier.ESCALATE: 0.18,  # clamped to P_RECOVER — watchful, not suppressed
    GovernanceTier.OVERSIGHT: 5.0,  # large spike — halt signal
}

# Governance penalty weight added during QUARANTINE bursts
QUARANTINE_GOV_PENALTY_WEIGHT = 0.25

# Oversight collapse trigger: F below floor for N consecutive steps
OVERSIGHT_F_FLOOR = 0.05
OVERSIGHT_MIN_STEPS = 3


# =============================================================================
# SYSTEM CONSTRAINTS
# =============================================================================

PHI = 1.618033988749895
N_LAYERS = 14

# Fixed normalized budget (sums to 1.0)
P_BUDGET = 1.0
P_BASE = 0.10  # steady trickle
P_BURST = 0.72  # burst peak amplitude
P_RECOVER = 0.18  # echo recovery window


def composite_gate(
    V: float,
    coherence: float,
    net_cost: float,
    mode_tier: GovernanceTier,
    *,
    oversight_active: bool = False,
    # hysteresis: previous tier — requires a stronger drop to leave ALLOW
    prev_tier: Optional[GovernanceTier] = None,
) -> GovernanceTier:
    """
    Composite governance gate — multi-signal, hysteresis-aware.

    Mode-based tier is the PRIMARY signal (it controls energy budget).
    This function can OVERRIDE upward (worse tier) based on signal quality,
    but never OVERRIDES DOWNWARD past what the mode warrants in the same step.
    (You can't be ALLOW during a BURST — the energy expenditure itself
     warrants QUARANTINE scrutiny regardless of how clean the signal looks.)

    Override rules:
      - OVERSIGHT condition (F-collapse): overrides everything → OVERSIGHT
      - V < 0.3 (low value) in any mode → ESCALATE minimum
      - V > 0.8 AND coherence > 0.7 AND net_cost < 0.08 → ALLOW maximum
        (A very cheap, high-value burst can be demoted from QUARANTINE → ALLOW)
      - Otherwise: take the worse of (mode_tier, signal-inferred tier)

    Hysteresis:
      If prev_tier == ALLOW, require V < 0.25 to leave (stickier upper bound).
      If prev_tier == OVERSIGHT, require V > 0.7 to return to ALLOW.

    Args:
      V:                value score ∈ (0, 1]
      coherence:        mean layer coherence ∈ [0, 1]
      net_cost:         C - R (normalized)
      mode_tier:        tier from _MODE_TO_TIER[mode]
      oversight_active: True if FunEnergyLoss detected F-collapse
      prev_tier:        previous step's tier (for hysteresis)
    """
    # OVERSIGHT overrides everything — collapse is collapse
    if oversight_active:
        return GovernanceTier.OVERSIGHT

    # Hysteresis adjustment to V thresholds
    v_low_threshold = 0.25 if prev_tier == GovernanceTier.ALLOW else 0.30
    v_high_threshold = 0.70 if prev_tier == GovernanceTier.OVERSIGHT else 0.80

    # "Novelty phase" vs "divergence" distinction:
    # Coherence near zero can mean two different things:
    #   (a) No phase patterns established yet (early training) → benign
    #   (b) Phase was established but has since diverged → danger
    # We separate these by looking at whether coherence has EVER been > 0.1.
    # Since we don't track history here, we use V and F-implicitly via net_cost.
    # Proxy: if coherence < 0.1 AND F is healthy (implied by V > 0.3 and net_cost moderate),
    # treat as novelty — defer to mode_tier rather than escalating.
    novelty_phase = coherence < 0.10 and V > 0.30 and net_cost < 0.50

    # Echo mode (ESCALATE) has lower V expectations — it's phase recovery,
    # not value generation. Only OVERSIGHT or F-collapse can push it higher.
    # V thresholds are halved in echo mode to avoid false OVERSIGHT.
    if mode_tier == GovernanceTier.ESCALATE:
        v_low_threshold *= 0.50  # ~0.13 — only flag true collapse
        v_high_threshold *= 0.70  # ~0.56 — attainable in echo

    # Signal-inferred tier (independent of mode)
    if V < v_low_threshold or net_cost > 0.65:
        # Low value or very expensive — escalate regardless of mode
        signal_tier = GovernanceTier.ESCALATE
    elif V > v_high_threshold and coherence > 0.5 and net_cost < 0.15:
        # High value, coherent, cheap — cleanest signal
        signal_tier = GovernanceTier.ALLOW
    elif V > 0.40 and (coherence > 0.30 or novelty_phase):
        # Reasonable signal, OR novelty phase — defer to mode
        signal_tier = mode_tier
    elif novelty_phase:
        # Novelty: one step above mode (watchful but not blocking)
        _order = [GovernanceTier.ALLOW, GovernanceTier.QUARANTINE, GovernanceTier.ESCALATE, GovernanceTier.OVERSIGHT]
        idx = _order.index(mode_tier)
        signal_tier = _order[min(idx + 1, len(_order) - 1)]
    else:
        # Low coherence AND unhealthy signal: established divergence, escalate
        _order = [GovernanceTier.ALLOW, GovernanceTier.QUARANTINE, GovernanceTier.ESCALATE, GovernanceTier.OVERSIGHT]
        idx = _order.index(mode_tier)
        signal_tier = _order[min(idx + 1, len(_order) - 1)]

    # Take the WORSE tier of mode vs signal (never downgrade beyond mode)
    _order = [GovernanceTier.ALLOW, GovernanceTier.QUARANTINE, GovernanceTier.ESCALATE, GovernanceTier.OVERSIGHT]
    mode_idx = _order.index(mode_tier)
    signal_idx = _order.index(signal_tier)

    # ECHO mode safeguard: already at ESCALATE, which is "watchful but not blocking".
    # Only genuine F-collapse (oversight_active) pushes echo to OVERSIGHT.
    # Normal-range V/coherence variation during recovery is expected — don't penalize.
    if mode_tier == GovernanceTier.ESCALATE and not oversight_active:
        result_idx = min(max(mode_idx, signal_idx), _order.index(GovernanceTier.ESCALATE))
        return _order[result_idx]

    # QUARANTINE burst: allow demotion to ALLOW only if the burst is genuinely
    # cheap + high-value (truly energy-efficient burst)
    if signal_tier == GovernanceTier.ALLOW and mode_tier == GovernanceTier.QUARANTINE:
        if net_cost < 0.05:
            return GovernanceTier.ALLOW

    # All other modes: take worse of the two
    result_idx = max(mode_idx, signal_idx)
    return _order[result_idx]


@dataclass
class SystemConstraints:
    """
    Fixed capacity envelope for training. Set once; never changes during a run.
    Training should NOT run at full power — it should feel like a stream with
    occasional pulses, not a constant flood.
    """

    p_budget: float = P_BUDGET  # total envelope (normalized = 1.0)
    p_base: float = P_BASE  # low-KE steady engagement
    p_burst: float = P_BURST  # burst peak (above base)
    p_recover: float = P_RECOVER  # reserved for echo window
    burst_threshold: float = 0.55  # fun-potential to trigger burst
    burst_width: int = 8  # steps for burst envelope (Gaussian halfwidth)
    propagation_delay: float = 0.5  # steps per layer for travelling wave
    echo_decay_len: float = 4.0  # layers over which echo decays
    n_layers: int = N_LAYERS
    phi_burst_spacing: bool = True  # space bursts at phi-harmonic intervals

    def __post_init__(self):
        total = self.p_base + self.p_burst + self.p_recover
        if abs(total - self.p_budget) > 1e-6:
            raise ValueError(
                f"p_base+p_burst+p_recover = {total:.4f} != p_budget {self.p_budget}. " "Budget must close."
            )


# =============================================================================
# PHASE MEMORY — established frequency/phase patterns per layer
# =============================================================================


@dataclass
class LayerPhase:
    """
    Running phase estimate for one pipeline layer.
    Tracks the dominant frequency content from previous pulses.
    """

    layer_idx: int
    phase: float = 0.0  # current dominant phase angle (radians)
    frequency: float = 0.0  # dominant frequency (normalized 0..1)
    amplitude: float = 0.0  # established amplitude (grows with use)
    n_hits: int = 0  # how many pulses have touched this layer
    coherence: float = 0.0  # rolling coherence with incoming pulses


class PhaseMemory:
    """
    Maintains established phase state for all 14 pipeline layers.
    Updated by each burst pulse; consulted by the echolation engine.
    """

    def __init__(self, n_layers: int = N_LAYERS, decay: float = 0.95):
        self.n_layers = n_layers
        self.decay = decay  # exponential decay for old phase info
        self.layers: List[LayerPhase] = [LayerPhase(layer_idx=i) for i in range(n_layers)]

    def update(self, layer_idx: int, incoming_phase: float, incoming_freq: float, pulse_amplitude: float) -> float:
        """
        Update layer phase from an incoming pulse. Returns coherence [0,1].

        Coherence = dot product between established phase vector and incoming:
          coherence = cos(established_phase - incoming_phase) * amplitude_match
        """
        lp = self.layers[layer_idx]
        coherence = 0.0

        if lp.amplitude > 1e-6:
            phase_diff = lp.phase - incoming_phase
            # Frequency coherence: how close are the two frequencies?
            freq_match = math.exp(-abs(lp.frequency - incoming_freq) * 4.0)
            phase_align = (1.0 + math.cos(phase_diff)) / 2.0  # in [0,1]
            coherence = phase_align * freq_match

        # Exponential moving average update
        lp.phase = self.decay * lp.phase + (1 - self.decay) * incoming_phase
        lp.frequency = self.decay * lp.frequency + (1 - self.decay) * incoming_freq
        lp.amplitude = self.decay * lp.amplitude + (1 - self.decay) * pulse_amplitude
        lp.coherence = self.decay * lp.coherence + (1 - self.decay) * coherence
        lp.n_hits += 1

        return coherence

    def mean_coherence(self) -> float:
        coh = [lp.coherence for lp in self.layers if lp.n_hits > 0]
        return sum(coh) / len(coh) if coh else 0.0

    def layer_coherences(self) -> List[float]:
        return [lp.coherence for lp in self.layers]


# =============================================================================
# ECHOLATION ENGINE — forward pulse + echo computation
# =============================================================================


@dataclass
class EchoEvent:
    """One returned echo from a specific layer."""

    origin_layer: int
    echo_layer: int  # which layer reflected it
    amplitude: float  # echo amplitude (attenuated forward pulse)
    phase_shift: float  # phase shift from reflection (carries layer info)
    coherence: float  # coherence at hit point
    energy: float  # total recovered energy from this echo


class EcholationEngine:
    """
    Sonar-style echolation through the 14-layer pipeline.

    Forward propagation:
      pulse(l) = A0 * exp(-l / decay_len)   — attenuates through layers

    Echo at layer k:
      echo_amplitude(k) = pulse(k) * reflection_coeff
      reflection_coeff  = coherence(layer_k_phase, pulse_frequency)

    Total recovered energy:
      R = sum_k [ echo_amplitude(k) * coherence(k) ]

    Reverse frequency mapping:
      The echo carries the frequency signature of what it hit.
      echo_frequency(k) = pulse_frequency * (1 + frequency_shift_from_layer_k)
      If echo_frequency matches pulse_frequency → resonance hit → bonus energy
    """

    def __init__(self, constraints: SystemConstraints, phase_memory: PhaseMemory):
        self.C = constraints
        self.pm = phase_memory

    def fire_pulse(
        self,
        pulse_frequency: float,
        pulse_phase: float,
        pulse_amplitude: float,
        origin_layer: int = 0,
    ) -> Tuple[List[EchoEvent], float]:
        """
        Fire a pulse from origin_layer through all subsequent layers.

        Returns:
          echoes:       list of EchoEvent (one per layer hit)
          R:            total recovered energy
        """
        echoes: List[EchoEvent] = []
        R = 0.0

        for l in range(origin_layer, self.C.n_layers):
            # Forward pulse amplitude at this layer (exponential decay)
            depth = l - origin_layer
            fwd_amp = pulse_amplitude * math.exp(-depth / self.C.echo_decay_len)

            # Update layer phase and get coherence
            coherence = self.pm.update(l, pulse_phase, pulse_frequency, fwd_amp)

            # Echo amplitude: portion reflected back based on coherence
            # Non-coherent layers still reflect a little (noise floor = 0.05)
            reflection_coeff = 0.05 + 0.95 * coherence
            echo_amp = fwd_amp * reflection_coeff

            # Phase shift from reflection: Ï€/2 for perfectly incoherent,
            # 0 for perfectly coherent (coherent → same phase returns)
            phase_shift = (1.0 - coherence) * (math.pi / 2.0)

            # Frequency shift: coherent → no shift; incoherent → shifted by phi ratio
            # (reverse frequency mapping — the echo tells you what phase the layer holds)
            freq_shift = (1.0 - coherence) * (pulse_frequency * (PHI - 1.0))
            echo_freq = pulse_frequency + freq_shift

            # Energy from this echo
            # Resonance bonus: if echo_freq is close to pulse_frequency → standing wave
            resonance = math.exp(-abs(echo_freq - pulse_frequency) * 6.0)
            echo_energy = echo_amp * coherence * (1.0 + resonance)

            # Cap echo energy contribution to P_RECOVER budget
            echo_energy = min(echo_energy, self.C.p_recover / self.C.n_layers)

            ev = EchoEvent(
                origin_layer=origin_layer,
                echo_layer=l,
                amplitude=echo_amp,
                phase_shift=phase_shift,
                coherence=coherence,
                energy=echo_energy,
            )
            echoes.append(ev)
            R += echo_energy

        # Cap total R at p_recover budget
        R = min(R, self.C.p_recover)
        return echoes, R


# =============================================================================
# KINETIC SCHEDULER — controls burst/trickle flow pattern
# =============================================================================


@dataclass
class SchedulerState:
    step: int = 0
    fun_potential: float = 0.0  # accumulated potential (triggers burst)
    mode: str = "trickle"  # "trickle" | "burst" | "echo"
    burst_step: int = 0  # step within current burst
    next_burst_step: int = 20  # next scheduled burst (phi-spaced)
    burst_count: int = 0  # total bursts fired
    last_R: float = 0.0  # last recovered energy
    last_F: float = 0.0  # last fun quotient
    oversight_count: int = 0  # consecutive steps with F < OVERSIGHT_F_FLOOR
    oversight_active: bool = False  # True when F-collapse triggered
    tier: str = "ALLOW"  # current governance tier string


class KineticScheduler:
    """
    Controls the flow pattern: steady trickle → burst pulse → echo recovery.

    State machine:
      TRICKLE: run at P_base, accumulate fun_potential each step
      BURST:   fire for burst_width steps at P_burst envelope
      ECHO:    harvest echo energy for a few steps (P_recover mode)
      → back to TRICKLE

    Burst timing:
      If phi_burst_spacing=True, schedule bursts at phi-harmonic intervals:
        t0, t0 + T, t0 + T*phi, t0 + T*phi^2, ...
      This creates an aperiodic but structured pulse train that doesn't
      build destructive resonance in any single layer.
    """

    def __init__(self, constraints: SystemConstraints):
        self.C = constraints
        self.state = SchedulerState()
        self._burst_interval = 20  # base interval (steps between bursts)
        self._echo_steps = 4  # steps in echo recovery mode

    def current_power(self) -> float:
        """Return normalized power level for this step [0, P_budget]."""
        s = self.state
        if s.mode == "trickle":
            return self.C.p_base
        elif s.mode == "burst":
            # Gaussian envelope over burst_width steps
            t_center = self.C.burst_width / 2.0
            t_rel = s.burst_step - t_center
            envelope = math.exp(-((t_rel / (self.C.burst_width / 3.0)) ** 2))
            return self.C.p_base + (self.C.p_burst - self.C.p_base) * envelope
        elif s.mode == "echo":
            return self.C.p_recover / self._echo_steps
        return self.C.p_base

    def step(self, fun_score: float, value: float) -> SchedulerState:
        """
        Advance one training step.

        fun_score: current F(t) value [0, ∞)
        value:     task value V(t) [0, 1]

        Returns updated state (mode, power, tier, oversight_active, etc.)
        """
        s = self.state
        s.step += 1
        s.last_F = fun_score

        # --- Oversight collapse check (any mode) ---
        if fun_score < OVERSIGHT_F_FLOOR:
            s.oversight_count += 1
        else:
            # Decay oversight counter: requires sustained recovery to clear
            s.oversight_count = max(0, s.oversight_count - 1)
        s.oversight_active = s.oversight_count >= OVERSIGHT_MIN_STEPS

        # --- Mode state machine ---
        if s.mode == "trickle":
            potential_gain = 0.05 * fun_score * (1.0 + value)
            s.fun_potential = min(1.0, s.fun_potential + potential_gain)
            if s.fun_potential >= self.C.burst_threshold:
                s.mode = "burst"
                s.burst_step = 0
                s.burst_count += 1

        elif s.mode == "burst":
            s.burst_step += 1
            if s.burst_step >= self.C.burst_width:
                s.mode = "echo"
                s.burst_step = 0

        elif s.mode == "echo":
            s.burst_step += 1
            if s.burst_step >= self._echo_steps:
                s.mode = "trickle"
                s.burst_step = 0
                s.fun_potential = 0.0
                if self.C.phi_burst_spacing:
                    self._burst_interval = int(self._burst_interval * PHI)

        # --- Update tier string on state (set by FunEnergyLoss.forward) ---
        # (FunEnergyLoss calls composite_gate and sets s.tier directly)

        return s


# =============================================================================
# FUN ENERGY QUOTIENT LOSS
# =============================================================================


class FunEnergyLoss(nn.Module):
    """
    Fun as a thermodynamic energy quotient.

    F(t) = V(t) / (C(t) - R(t) + epsilon)

    where:
      V(t)  = value gained
            = harmonic_wall_score * motif_coherence (task quality)
              + governance_improvement (delta from baseline)
      C(t)  = compute cost = p_current * n_tokens * phi_mass_factor
              (CAPPED at p_budget — never trains at full power)
      R(t)  = echo recovery = sum of phase-coherent echo energies
              from EcholationEngine.fire_pulse()

    Training loss: L_fun = -log(clamp(F, min=1e-8))
    Higher F → lower loss → more fun → model is rewarded.

    Args:
      hidden_dim:    model hidden dimension (default 384)
      constraints:   SystemConstraints (fixed normalized budget)
      fun_weight:    scale factor for loss term
      burst_freq:    dominant burst frequency (0..1 normalized)
    """

    def __init__(
        self,
        hidden_dim: int = 384,
        constraints: SystemConstraints = None,
        fun_weight: float = 0.15,
        burst_freq: float = 0.25,  # phi-harmonic base frequency
        exec_alpha: float = 0.4,  # blend weight for execution ground truth
    ):
        super().__init__()
        self.C = constraints or SystemConstraints()
        self.fun_weight = fun_weight
        self.burst_freq = burst_freq
        self._exec_alpha = exec_alpha  # V_grounded = (1-α)*V_learned + α*v_signal

        # Learnable head: hidden state → (value_score, phi_mass_factor)
        self.value_head = nn.Linear(hidden_dim, 1)
        self.cost_head = nn.Linear(hidden_dim, 1)

        # Phi-weight vector (tongue governance costs)
        phi_weights = torch.tensor([1.00, 1.62, 2.62, 4.24, 6.85, 11.09])
        self.register_buffer("phi_weights", phi_weights)

        # Phase memory and echolation engine
        self.phase_memory = PhaseMemory(n_layers=self.C.n_layers)
        self.echo_engine = EcholationEngine(self.C, self.phase_memory)
        self.scheduler = KineticScheduler(self.C)

        # Running baseline for governance improvement delta
        self._baseline_V: float = 0.5

    def _compute_V(
        self,
        h: torch.Tensor,
        execution_signal: Optional[float] = None,
    ) -> torch.Tensor:
        """
        Value estimate from hidden state, optionally anchored by execution ground truth.

        When execution_signal is provided (v_signal from ExecutionFeedback):
            V_grounded = (1 - exec_alpha) * V_learned + exec_alpha * v_signal

        exec_alpha=0.0 → pure learned head (original behaviour)
        exec_alpha=0.4 → 40% execution ground truth, 60% learned (default)
        exec_alpha=1.0 → pure execution signal (no learned contribution)
        """
        V = torch.sigmoid(self.value_head(h)).squeeze(-1)  # (B,)
        if execution_signal is not None and self._exec_alpha > 0.0:
            exec_t = torch.full_like(V, float(execution_signal))
            V = (1.0 - self._exec_alpha) * V + self._exec_alpha * exec_t
        return V

    def _compute_C(self, h: torch.Tensor, p_current: float) -> torch.Tensor:
        """
        Compute cost estimate.
        C = p_current * phi_mass_factor
        phi_mass_factor estimated from hidden state (proxy for token-level phi usage).
        Capped at p_budget.
        """
        phi_factor = torch.sigmoid(self.cost_head(h)).squeeze(-1)  # (B,) in (0,1)
        C = p_current * (0.5 + phi_factor)  # (B,) in [0, p_budget]
        return C.clamp(max=self.C.p_budget)

    def _compute_R(self, p_current: float) -> float:
        """
        Fire a pulse and recover echo energy.
        Uses current power level to determine pulse amplitude.

        Returns scalar R (mean recovered energy across layers).
        """
        # Pulse frequency: phi-scaled harmonic of base frequency
        step = self.scheduler.state.step
        freq = self.burst_freq * (PHI ** (step % self.C.n_layers / self.C.n_layers))
        freq = freq % 1.0  # keep normalized
        phase = (2.0 * math.pi * step / self.C.n_layers) % (2.0 * math.pi)

        _, R = self.echo_engine.fire_pulse(
            pulse_frequency=freq,
            pulse_phase=phase,
            pulse_amplitude=p_current,
            origin_layer=0,
        )
        return R

    def fun_quotient(
        self,
        V: torch.Tensor,  # (B,)
        C: torch.Tensor,  # (B,)
        R: float,
    ) -> torch.Tensor:
        """
        F(t) = V / (C - R + epsilon)

        R is scalar (system-level recovery, same for whole batch).
        C and V are per-sample tensors.

        When R >= C (energy-positive step), net cost → epsilon.
        We cap F at F_MAX = 20.0 to prevent astronomical values from
        dominating the loss and destabilizing gradient flow.
        An energy-positive step is genuinely good but not infinitely so.
        """
        F_MAX = 20.0
        # Floor at 1% of P_base so energy-positive steps get a clear positive
        # reward without blowing up — not a tiny epsilon
        eps_floor = max(1e-4, self.C.p_base * 0.01)
        net_cost = (C - R).clamp(min=eps_floor)
        F = V / net_cost
        return F.clamp(min=1e-8, max=F_MAX)

    def forward(
        self,
        hidden_states: torch.Tensor,  # (B, S, D)
        step: int = 0,
        execution_signal: Optional[float] = None,  # v_signal from ExecutionFeedback (0..1)
        atomic_profile: Optional[object] = None,  # AtomicCodeProfile from ExecutionFeedback
    ) -> Tuple[torch.Tensor, dict]:
        """
        Compute fun energy loss and diagnostics.

        Args:
          hidden_states:    model hidden states (B, S, D)
          step:             global training step
          execution_signal: ground-truth V anchor from ExecutionFeedback.evaluate()
                            (1.0=clean pass, 0.0=crash/timeout). When provided,
                            V(t) is partially anchored by actual code execution via exec_alpha.
          atomic_profile:   AtomicCodeProfile from ExecutionFeedback. When provided,
                            tau_quality is blended into the composite gate coherence signal.

        Returns:
          loss:   scalar fun loss, tier-scaled
          info:   dict with F, V, C, R, mode, p_current, tier for logging
        """
        # Mean-pool sequence → (B, D)
        h = hidden_states.mean(dim=1)

        # Get current power level from scheduler
        p_current = self.scheduler.current_power()

        # Compute value (optionally anchored by execution ground truth), cost, echo recovery
        V = self._compute_V(h, execution_signal=execution_signal)  # (B,)
        C = self._compute_C(h, p_current)  # (B,)
        R = self._compute_R(p_current)  # scalar

        # Fun quotient
        F = self.fun_quotient(V, C, R)  # (B,)
        mean_F = F.mean()
        fun_scalar = mean_F.item()
        val_scalar = V.mean().item()
        net_cost = (C.mean() - R).item()

        # Base fun loss
        base_loss = self.fun_weight * (-torch.log(mean_F + 1e-8))

        # Update scheduler (sets oversight_active, last_F, mode)
        state = self.scheduler.step(fun_scalar, val_scalar)

        # --- Composite governance gate ---
        mode_tier = _MODE_TO_TIER.get(state.mode, GovernanceTier.ALLOW)
        prev_tier = GovernanceTier(state.tier) if state.tier else None

        # When an atomic profile is available, blend its tau_quality into coherence.
        # tau_quality is a pre-execution semantic quality signal: high DR/CA tokens
        # (formal structure, compute) push coherence up; high RU/negation push it down.
        base_coherence = self.phase_memory.mean_coherence()
        tau_quality = atomic_profile.tau_quality if atomic_profile is not None else None
        if tau_quality is not None:
            # 70% phase memory coherence, 30% atomic semantic quality
            blended_coherence = 0.70 * base_coherence + 0.30 * tau_quality
        else:
            blended_coherence = base_coherence

        tier = composite_gate(
            V=val_scalar,
            coherence=blended_coherence,
            net_cost=net_cost,
            mode_tier=mode_tier,
            oversight_active=state.oversight_active,
            prev_tier=prev_tier,
        )
        state.tier = tier.value  # persist on scheduler state

        # --- Tier-scaled loss ---
        scale = TIER_LOSS_SCALE[tier]
        loss = base_loss * scale

        # QUARANTINE: add governance penalty (cost above budget penalized)
        if tier == GovernanceTier.QUARANTINE:
            # Penalize when cost exceeds base budget (burst wasn't worth it)
            cost_excess = F.new_tensor(max(0.0, net_cost - self.C.p_base))
            gov_penalty = QUARANTINE_GOV_PENALTY_WEIGHT * cost_excess
            loss = loss + gov_penalty

        # OVERSIGHT: add a fixed large penalty (halt signal — not clipped)
        if tier == GovernanceTier.OVERSIGHT:
            loss = loss + self.fun_weight * 2.0  # flat penalty on top of 5x scale

        # Update baseline
        self._baseline_V = 0.95 * self._baseline_V + 0.05 * val_scalar

        info = {
            "fun/F": fun_scalar,
            "fun/V": val_scalar,
            "fun/C": C.mean().item(),
            "fun/R": R,
            "fun/net_cost": net_cost,
            "fun/p_current": p_current,
            "fun/mode": state.mode,
            "fun/tier": tier.value,
            "fun/tier_scale": scale,
            "fun/burst_count": state.burst_count,
            "fun/potential": state.fun_potential,
            "fun/mean_coherence": base_coherence,
            "fun/blended_coherence": blended_coherence,
            "fun/oversight_count": state.oversight_count,
            "fun/oversight_active": state.oversight_active,
            # Execution feedback fields (None when not grounded)
            "fun/exec_v_signal": execution_signal,
            "fun/exec_alpha": self._exec_alpha if execution_signal is not None else None,
            "fun/tau_quality": tau_quality,
        }

        return loss, info


# =============================================================================
# BURST TRAINER MIXIN
# =============================================================================


class BurstTrainerMixin:
    """
    Mixin for HuggingFace Trainer that implements burst/trickle scheduling.

    Most steps run at P_base (sonar-only, no governance loss, low KE).
    When the scheduler fires a burst, runs full triple loss (sonar+gov+fun).
    Echo recovery steps run fun-only (cheap, just update phase memory).

    Usage:
      class MyTrainer(BurstTrainerMixin, Trainer): ...
      → override compute_loss to call self.burst_compute_loss(...)
    """

    def _get_fun_module(self) -> Optional[FunEnergyLoss]:
        """Find the FunEnergyLoss module on the model if it exists."""
        if not hasattr(self, "model"):
            return None
        for module in self.model.modules():
            if isinstance(module, FunEnergyLoss):
                return module
        return None

    def burst_mode(self) -> str:
        """Current kinetic mode: 'trickle' | 'burst' | 'echo'."""
        fun = self._get_fun_module()
        if fun is None:
            return "trickle"
        return fun.scheduler.state.mode

    def burst_compute_loss(
        self,
        model,
        inputs,
        sonar_loss_fn,  # callable: (model, inputs) -> sonar_loss
        gov_loss_fn=None,  # callable: (model, inputs) -> gov_loss (optional)
        return_outputs=False,
        rotation_alpha: float = 0.5,
    ) -> torch.Tensor:
        """
        Compute loss according to current burst mode:

          TRICKLE: sonar_loss only, weight=1.0 * P_base (cheap, steady)
          BURST:   alpha*sonar + (1-alpha)*gov + fun_weight*fun
          ECHO:    fun only (no sonar, no gov — just update phase memory)
        """
        mode = self.burst_mode()
        fun = self._get_fun_module()

        if mode == "trickle":
            # Cheap: sonar only, scaled down by P_base
            loss = sonar_loss_fn(model, inputs) * P_BASE
            return loss

        elif mode == "burst":
            # Full power: rotating dual + fun quotient
            sonar_loss = sonar_loss_fn(model, inputs)
            gov_loss = gov_loss_fn(model, inputs) if gov_loss_fn else torch.zeros(1)
            rotated = rotation_alpha * sonar_loss + (1.0 - rotation_alpha) * gov_loss

            if fun is not None:
                # Need hidden states for fun — re-run forward if needed
                outputs = model(**inputs, output_hidden_states=True)
                hs = outputs.hidden_states[-1]  # last layer
                step = getattr(self, "state", None)
                step_n = step.global_step if step else 0
                fun_loss, fun_info = fun(hs, step=step_n)
                total = rotated + fun_loss
            else:
                total = rotated

            return total

        elif mode == "echo":
            # Echo recovery: only advance phase memory, no gradient on sonar
            if fun is not None:
                outputs = model(**inputs, output_hidden_states=True)
                hs = outputs.hidden_states[-1]
                step_n = getattr(getattr(self, "state", None), "global_step", 0)
                fun_loss, _ = fun(hs, step=step_n)
                return fun_loss * P_RECOVER  # very small loss, mostly for memory update
            return torch.zeros(1, requires_grad=True)

        # Fallback
        return sonar_loss_fn(model, inputs)


# =============================================================================
# PULSE VISUALIZER — for demo / diagnostics
# =============================================================================


def visualize_pulse_pattern(
    n_steps: int = 100,
    constraints: SystemConstraints = None,
) -> List[dict]:
    """
    Simulate the burst/trickle pattern for n_steps without a real model.
    Returns list of per-step dicts for plotting.
    """
    C = constraints or SystemConstraints()
    pm = PhaseMemory(n_layers=C.n_layers)
    echo_eng = EcholationEngine(C, pm)
    scheduler = KineticScheduler(C)

    records = []
    fun_potential = 0.0

    prev_tier: Optional[GovernanceTier] = None

    for step in range(n_steps):
        p = scheduler.current_power()

        # Simulate a pulse at current power
        freq = 0.25 * (PHI ** (step % C.n_layers / C.n_layers)) % 1.0
        phase = (2.0 * math.pi * step / C.n_layers) % (2.0 * math.pi)
        _, R = echo_eng.fire_pulse(freq, phase, p)

        # Synthetic V: random task value in [0.3, 0.9]
        import random

        V = 0.3 + 0.6 * random.random()

        # Net cost and fun quotient
        # Floor at 1% of P_base (same as FunEnergyLoss.fun_quotient)
        C_cost = p * 0.8
        eps_floor = max(1e-4, C.p_base * 0.01)
        net = max(C_cost - R, eps_floor)
        F = min(V / net, 20.0)  # cap at F_MAX

        state = scheduler.step(F, V)

        # Governance gate
        mode_tier = _MODE_TO_TIER.get(state.mode, GovernanceTier.ALLOW)
        tier = composite_gate(
            V=V,
            coherence=pm.mean_coherence(),
            net_cost=net,
            mode_tier=mode_tier,
            oversight_active=state.oversight_active,
            prev_tier=prev_tier,
        )
        prev_tier = tier

        records.append(
            {
                "step": step,
                "mode": state.mode,
                "tier": tier.value,
                "power": p,
                "V": round(V, 3),
                "C": round(C_cost, 4),
                "R": round(R, 4),
                "net": round(net, 4),
                "F": round(F, 3),
                "mean_coh": round(pm.mean_coherence(), 3),
                "potential": round(state.fun_potential, 3),
                "bursts": state.burst_count,
                "oversight": state.oversight_active,
            }
        )

    return records


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    print("FUN ENERGY QUOTIENT DEMO")
    print("=" * 72)

    C = SystemConstraints()
    print(f"System constraints:")
    print(f"  P_budget  = {C.p_budget}")
    print(f"  P_base    = {C.p_base}  (trickle — most steps)")
    print(f"  P_burst   = {C.p_burst}  (burst envelope peak)")
    print(f"  P_recover = {C.p_recover}  (echo window)")
    print(f"  burst_threshold = {C.burst_threshold}")
    print()

    print("Simulating 60 training steps...")
    records = visualize_pulse_pattern(n_steps=60)
    print()

    # Show power profile
    print(
        f"{'Step':>4}  {'Mode':<7}  {'Tier':<12}  {'Power':>6}  {'V':>5}  "
        f"{'C':>6}  {'R':>6}  {'F':>6}  {'Coh':>5}  {'Pot':>5}"
    )
    print("-" * 80)

    burst_steps = []
    for r in records:
        mode_str = r["mode"][:7]
        tier_str = r["tier"]
        flag = ""
        if r["mode"] == "burst":
            burst_steps.append(r["step"])
            flag = " <<BURST>>"
        elif r["mode"] == "echo":
            flag = " ~echo~"
        if r.get("oversight"):
            flag = " [OVERSIGHT]"
        print(
            f"{r['step']:>4}  {mode_str:<7}  {tier_str:<12}  {r['power']:>6.3f}  "
            f"{r['V']:>5.3f}  {r['C']:>6.4f}  {r['R']:>6.4f}  {r['F']:>6.2f}  "
            f"{r['mean_coh']:>5.3f}  {r['potential']:>5.3f}{flag}"
        )

    print()
    print(f"Burst steps: {burst_steps}")
    print(f"Total bursts fired: {records[-1]['bursts']}")
    print(f"Final mean layer coherence: {records[-1]['mean_coh']:.3f}")

    # Budget accounting
    total_energy = sum(r["power"] for r in records)
    trickle_energy = sum(r["power"] for r in records if r["mode"] == "trickle")
    burst_energy = sum(r["power"] for r in records if r["mode"] == "burst")
    echo_energy = sum(r["power"] for r in records if r["mode"] == "echo")
    print()
    print("Energy budget breakdown:")
    print(f"  Trickle:  {trickle_energy:.3f}  ({100*trickle_energy/total_energy:.1f}%)")
    print(f"  Burst:    {burst_energy:.3f}  ({100*burst_energy/total_energy:.1f}%)")
    print(f"  Echo:     {echo_energy:.3f}  ({100*echo_energy/total_energy:.1f}%)")
    print(f"  Total:    {total_energy:.3f}")

    # FunEnergyLoss module demo
    print()
    print("FunEnergyLoss module (torch):")
    fun_module = FunEnergyLoss(hidden_dim=64, fun_weight=0.15)
    B, S, D = 4, 16, 64
    fake_hidden = torch.randn(B, S, D)
    loss, info = fun_module(fake_hidden, step=0)
    print(f"  Loss:       {loss.item():.4f}")
    for k, v in info.items():
        if isinstance(v, (int, float)):
            print(f"  {k:<35}: {v:.4f}" if isinstance(v, float) else f"  {k:<35}: {v}")
        else:
            print(f"  {k:<35}: {v}")
    print()
    print("Tier distribution (5 steps):")
    tiers = []
    for i in range(5):
        fake_h = torch.randn(B, S, D)
        _, inf = fun_module(fake_h, step=i + 1)
        tiers.append(inf["fun/tier"])
        print(
            f"  step {i + 1}: mode={inf['fun/mode']:<7}  tier={inf['fun/tier']:<12}  "
            f"F={inf['fun/F']:.3f}  scale={inf['fun/tier_scale']:.2f}"
        )
