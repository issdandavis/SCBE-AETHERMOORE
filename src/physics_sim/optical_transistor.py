"""
Optical Transistor - Synchronously-Pumped Nonlinear Microcavity (iterated-map model)

Models the cascadable optical transistor (Lagoudakis-style room-temperature
polariton transistor architecture: mirrors + pulsed surface injection +
multi-beam) as three coupled pieces of math:

1. Round-trip power map with saturable gain x saturable absorber:
       P_{n+1} = f(P_n) = R1*R2 * exp[(g(P) - a(P)) * L] * P_n
   Bistable restoration requires an S-curve map with two stable fixed
   points (clean "0", clean "1") separated by an unstable threshold.

2. Adler phase equation (injection locking, the active clock):
       d(dphi)/dt = dw - K * sin(dphi)      locks iff |dw| < K
   Only the phase-coherent (locked) drive transfers energy; a
   phase-scrambled drive averages to nothing.

3. Multi-beam rate equations with one shared inversion N:
       dN/dt   = pump - N/tau2 - N * sum_k sigma_k * n_k
       dn_k/dt = (sigma_k * N - alpha_k) * n_k + sum_j kappa * n_j
   Cross-saturation through N is the transistor coupling; kappa -> 0
   gives independent WDM channels instead.

Cascadability figure of merit - all three at once:
       gain G >= 1   *   fan-out F >= 2   *   restoration |f'(P*)| < 1

Null gates (falsification controls, must FAIL when the physics is removed):
- constant absorber      -> bistability must collapse to a linear amp
- phase-scrambled drive  -> locked energy transfer must collapse to ~0
- severed shared gain    -> the gate beam must become decorative
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

# =============================================================================
# 1. ROUND-TRIP MAP: saturable gain x saturable absorber
# =============================================================================


@dataclass
class CavityConfig:
    """Parameters of the round-trip power map.

    The absorber must saturate at lower power than the gain
    (sat_power_absorber < sat_power_gain) for the map to be bistable:
    low P -> loss wins (stable "0"); mid P -> absorber bleaches first
    (unstable threshold); high P -> gain saturates (stable "1").
    """

    mirror_product: float = 0.81  # R1 * R2
    cavity_length: float = 1.0  # L
    gain_peak: float = 2.0  # g0
    sat_power_gain: float = 2.0  # gain saturation power
    absorber_peak: float = 1.5  # a0 (saturable part of the loss)
    sat_power_absorber: float = 0.1  # absorber saturation power
    linear_loss: float = 0.6  # unsaturable background loss

    def gain(self, power: float) -> float:
        """Saturable gain g(P) = g0 / (1 + P / P_sat_g)."""
        return self.gain_peak / (1.0 + power / self.sat_power_gain)

    def loss(self, power: float) -> float:
        """Total loss a(P) = a_lin + a0 / (1 + P / P_sat_a)."""
        if math.isinf(self.sat_power_absorber):
            saturable = self.absorber_peak  # null gate: absorber never bleaches
        else:
            saturable = self.absorber_peak / (1.0 + power / self.sat_power_absorber)
        return self.linear_loss + saturable

    def round_trip_gain(self, power: float) -> float:
        """Net single-pass multiplier G(P) = R1*R2 * exp[(g - a) * L]."""
        return self.mirror_product * math.exp((self.gain(power) - self.loss(power)) * self.cavity_length)


def round_trip_map(power: float, config: CavityConfig) -> float:
    """One bounce: P_{n+1} = G(P_n) * P_n."""
    return config.round_trip_gain(power) * power


@dataclass
class FixedPoint:
    """A fixed point P* of the round-trip map with its local stability."""

    power: float
    derivative: float  # f'(P*)

    @property
    def stable(self) -> bool:
        """Contraction criterion |f'(P*)| < 1: noise shrinks each pass."""
        return abs(self.derivative) < 1.0


def _map_derivative(power: float, config: CavityConfig, rel_step: float = 1e-6) -> float:
    """Central-difference derivative f'(P) of the round-trip map."""
    h = max(power, 1e-9) * rel_step
    return (round_trip_map(power + h, config) - round_trip_map(power - h, config)) / (2.0 * h)


def find_fixed_points(
    config: CavityConfig,
    p_min: float = 1e-6,
    p_max: float = 100.0,
    n_grid: int = 4000,
) -> List[FixedPoint]:
    """Locate all fixed points of the map on [0, p_max].

    P = 0 is always a fixed point of the multiplicative map; its stability is
    G(0). Nonzero fixed points are roots of G(P) = 1, found by log-grid sign
    scan plus bisection refinement.
    """
    points = [FixedPoint(power=0.0, derivative=config.round_trip_gain(0.0))]

    log_lo, log_hi = math.log(p_min), math.log(p_max)
    grid = [math.exp(log_lo + (log_hi - log_lo) * i / (n_grid - 1)) for i in range(n_grid)]
    residual = [config.round_trip_gain(p) - 1.0 for p in grid]

    for i in range(n_grid - 1):
        if residual[i] == 0.0 or residual[i] * residual[i + 1] >= 0.0:
            continue
        lo, hi = grid[i], grid[i + 1]
        for _ in range(80):  # bisection
            mid = 0.5 * (lo + hi)
            if (config.round_trip_gain(lo) - 1.0) * (config.round_trip_gain(mid) - 1.0) <= 0.0:
                hi = mid
            else:
                lo = mid
        p_star = 0.5 * (lo + hi)
        points.append(FixedPoint(power=p_star, derivative=_map_derivative(p_star, config)))

    return points


def is_bistable(config: CavityConfig) -> bool:
    """True if the map has two stable fixed points separated by an unstable one."""
    pts = find_fixed_points(config)
    stable = [p for p in pts if p.stable]
    unstable = [p for p in pts if not p.stable]
    if len(stable) < 2 or not unstable:
        return False
    lo, hi = min(s.power for s in stable), max(s.power for s in stable)
    return any(lo < u.power < hi for u in unstable)


def iterate_cascade(
    power_in: float,
    config: CavityConfig,
    n_stages: int,
    noise_amplitude: float = 0.0,
    rng: Optional[random.Random] = None,
) -> List[float]:
    """Push a signal through n_stages identical cavities, optionally noisy.

    With a bistable map the per-stage contraction |f'(P*)| < 1 regenerates the
    logic level; with a linear amp the noise is carried (or grown) instead.
    """
    rng = rng or random.Random(0)
    levels = [power_in]
    p = power_in
    for _ in range(n_stages):
        p = round_trip_map(p, config)
        if noise_amplitude:
            p = max(0.0, p * (1.0 + rng.uniform(-noise_amplitude, noise_amplitude)))
        levels.append(p)
    return levels


# =============================================================================
# 2. ADLER EQUATION: injection-locking window
# =============================================================================


@dataclass
class AdlerConfig:
    """Parameters for the Adler phase equation d(dphi)/dt = dw - K sin(dphi)."""

    locking_bandwidth: float = 1.0  # K
    detuning: float = 0.0  # dw
    dt: float = 1e-3
    t_max: float = 200.0
    scramble_phase: bool = False  # null gate: random phase kicks each step
    scramble_strength: float = math.pi


@dataclass
class AdlerResult:
    """Outcome of an Adler integration."""

    locked: bool
    mean_energy_transfer: float  # time-average of cos(dphi), late window
    final_phase: float


def integrate_adler(config: AdlerConfig, rng: Optional[random.Random] = None) -> AdlerResult:
    """Integrate the Adler equation; report locking and mean energy transfer.

    Energy flows from drive to cavity at a rate proportional to cos(dphi).
    Locked: dphi settles to arcsin(dw/K), giving cos(dphi*) > 0.
    Unlocked or scrambled: cos(dphi) averages toward zero.
    """
    rng = rng or random.Random(1)
    phi = 0.0
    n_steps = int(config.t_max / config.dt)
    tail_start = int(0.5 * n_steps)
    acc = 0.0
    count = 0
    for step in range(n_steps):
        dphi_dt = config.detuning - config.locking_bandwidth * math.sin(phi)
        phi += dphi_dt * config.dt
        if config.scramble_phase:
            phi += rng.uniform(-config.scramble_strength, config.scramble_strength)
        if step >= tail_start:
            acc += math.cos(phi)
            count += 1
    mean_transfer = acc / max(count, 1)
    # Locked iff the phase velocity has died out (and we are not scrambling).
    final_velocity = abs(config.detuning - config.locking_bandwidth * math.sin(phi))
    locked = (not config.scramble_phase) and final_velocity < 1e-3 * max(config.locking_bandwidth, 1e-12)
    return AdlerResult(locked=locked, mean_energy_transfer=mean_transfer, final_phase=phi)


def locking_window(
    locking_bandwidth: float,
    detunings: Sequence[float],
    dt: float = 1e-3,
    t_max: float = 200.0,
) -> Dict[float, bool]:
    """Map detuning -> locked? The boundary sits at |dw| = K (Adler)."""
    out: Dict[float, bool] = {}
    for dw in detunings:
        cfg = AdlerConfig(locking_bandwidth=locking_bandwidth, detuning=dw, dt=dt, t_max=t_max)
        out[dw] = integrate_adler(cfg).locked
    return out


# =============================================================================
# 3. MULTI-BEAM: shared inversion, gain competition, fan-out
# =============================================================================


@dataclass
class MultiBeamConfig:
    """Two-beam (signal + gate) rate model sharing one inversion reservoir.

    For transistor action the gate must clamp the shared inversion BELOW the
    signal's threshold: alpha_gate/sigma_gate < alpha_signal/sigma_signal.
    The defaults give the gate twice the cross-section, so gate-on pins N at
    1.0 while the signal needs N >= 2.0 — the signal sees net loss and dies.
    """

    pump: float = 6.0  # inversion replenishment rate
    inversion_lifetime: float = 1.0  # tau2
    cross_sections: Tuple[float, float] = (1.0, 2.0)  # sigma_k (signal, gate)
    losses: Tuple[float, float] = (2.0, 2.0)  # alpha_k
    coupling: float = 0.0  # kappa (direct linear cross-feed)
    shared_reservoir: bool = True  # null gate: False = severed gain sharing
    seed_photons: float = 1e-6  # spontaneous seed keeping n_k > 0
    dt: float = 1e-3
    t_max: float = 60.0


@dataclass
class MultiBeamResult:
    """Steady-state photon numbers and the inversion(s) that produced them."""

    photons: Tuple[float, float]
    inversion: Tuple[float, float]  # equal entries when the reservoir is shared


def integrate_multibeam(config: MultiBeamConfig, gate_on: bool) -> MultiBeamResult:
    """Integrate the coupled rate equations to steady state.

    With a shared reservoir, turning the gate beam on depletes N and pulls the
    signal beam's gain down (cross-saturation = transistor action). With
    severed reservoirs the gate cannot reach the signal except through kappa.
    """
    sig_sigma, gate_sigma = config.cross_sections
    sig_alpha, gate_alpha = config.losses
    n_sig, n_gate = config.seed_photons, config.seed_photons
    inv_sig = inv_gate = config.pump * config.inversion_lifetime  # start pumped

    steps = int(config.t_max / config.dt)
    for _ in range(steps):
        gate_drive = gate_sigma * n_gate if gate_on else 0.0
        if config.shared_reservoir:
            depletion = sig_sigma * n_sig + gate_drive
            d_inv = config.pump - inv_sig / config.inversion_lifetime - inv_sig * depletion
            inv_sig = max(0.0, inv_sig + d_inv * config.dt)
            inv_gate = inv_sig
        else:
            d_sig = config.pump - inv_sig / config.inversion_lifetime - inv_sig * sig_sigma * n_sig
            d_gate = config.pump - inv_gate / config.inversion_lifetime - inv_gate * gate_drive
            inv_sig = max(0.0, inv_sig + d_sig * config.dt)
            inv_gate = max(0.0, inv_gate + d_gate * config.dt)

        dn_sig = (sig_sigma * inv_sig - sig_alpha) * n_sig + config.coupling * n_gate
        dn_gate = ((gate_sigma * inv_gate - gate_alpha) * n_gate) if gate_on else -n_gate
        n_sig = max(config.seed_photons, n_sig + dn_sig * config.dt)
        n_gate = max(config.seed_photons if gate_on else 0.0, n_gate + dn_gate * config.dt)

    return MultiBeamResult(photons=(n_sig, n_gate), inversion=(inv_sig, inv_gate))


def gate_extinction_ratio(config: MultiBeamConfig) -> float:
    """Signal output with gate OFF divided by signal output with gate ON.

    >> 1 means the gate beam really switches the signal (transistor action);
    ~ 1 means the coupling is decorative.
    """
    off = integrate_multibeam(config, gate_on=False).photons[0]
    on = integrate_multibeam(config, gate_on=True).photons[0]
    return off / max(on, 1e-300)


# =============================================================================
# 4. FIGURE OF MERIT + NULL GATES
# =============================================================================


@dataclass
class TransistorVerdict:
    """The triple inequality a cascadable element must satisfy at once."""

    gain_above_unity: bool  # G >= 1 somewhere on the high branch
    fan_out: int  # how many downstream stages one output can switch
    contraction: float  # |f'(P*)| at the high stable point
    bistable: bool

    @property
    def cascadable(self) -> bool:
        """G >= 1 and F >= 2 and |f'(P*)| < 1, with real bistability."""
        return self.gain_above_unity and self.fan_out >= 2 and self.contraction < 1.0 and self.bistable


def evaluate_transistor(config: CavityConfig, max_fan_out: int = 64) -> TransistorVerdict:
    """Score a cavity against the cascadability figure of merit.

    Fan-out is measured operationally: split the high-state output P* into
    F equal parts and ask whether P*/F still clears the unstable threshold
    (so each downstream stage regenerates to "1").
    """
    pts = find_fixed_points(config)
    stable_nonzero = [p for p in pts if p.stable and p.power > 0.0]
    unstable_nonzero = [p for p in pts if not p.stable and p.power > 0.0]
    bistable = is_bistable(config)

    if not stable_nonzero or not unstable_nonzero:
        return TransistorVerdict(
            gain_above_unity=any(config.round_trip_gain(p.power) >= 1.0 for p in pts),
            fan_out=0,
            contraction=float("inf"),
            bistable=bistable,
        )

    high = max(stable_nonzero, key=lambda p: p.power)
    threshold = min(unstable_nonzero, key=lambda p: p.power)

    fan_out = 0
    for f in range(1, max_fan_out + 1):
        if high.power / f > threshold.power:
            fan_out = f
        else:
            break

    return TransistorVerdict(
        gain_above_unity=True,  # an unstable threshold exists, so G crossed 1
        fan_out=fan_out,
        contraction=abs(high.derivative),
        bistable=bistable,
    )


@dataclass
class NullGateReport:
    """One falsification control: the effect must DIE when physics is removed."""

    name: str
    effect_with_physics: float
    effect_without: float
    collapse_ratio: float
    passed: bool


def run_null_gates(
    cavity: Optional[CavityConfig] = None,
    adler_bandwidth: float = 1.0,
    multibeam: Optional[MultiBeamConfig] = None,
    collapse_factor: float = 10.0,
) -> List[NullGateReport]:
    """Run all three null gates and report whether each effect collapses.

    1. Bistability needs the saturable absorber (else: linear amp).
    2. Energy transfer needs phase coherence (else: scrambled ~ zero).
    3. Transistor action needs the shared reservoir (else: decorative gate).
    """
    cavity = cavity or CavityConfig()
    multibeam = multibeam or MultiBeamConfig()
    reports: List[NullGateReport] = []

    # Gate 1: remove absorber saturation -> bistability must vanish.
    no_absorber = CavityConfig(**{**cavity.__dict__, "sat_power_absorber": float("inf")})
    with_b = 1.0 if is_bistable(cavity) else 0.0
    without_b = 1.0 if is_bistable(no_absorber) else 0.0
    reports.append(
        NullGateReport(
            name="saturable_absorber",
            effect_with_physics=with_b,
            effect_without=without_b,
            collapse_ratio=float("inf") if without_b == 0.0 and with_b > 0.0 else 1.0,
            passed=with_b == 1.0 and without_b == 0.0,
        )
    )

    # Gate 2: scramble the drive phase -> energy transfer must collapse.
    coherent = integrate_adler(AdlerConfig(locking_bandwidth=adler_bandwidth, detuning=0.3 * adler_bandwidth))
    scrambled = integrate_adler(
        AdlerConfig(locking_bandwidth=adler_bandwidth, detuning=0.3 * adler_bandwidth, scramble_phase=True)
    )
    ratio = abs(coherent.mean_energy_transfer) / max(abs(scrambled.mean_energy_transfer), 1e-12)
    reports.append(
        NullGateReport(
            name="phase_coherence",
            effect_with_physics=coherent.mean_energy_transfer,
            effect_without=scrambled.mean_energy_transfer,
            collapse_ratio=ratio,
            passed=coherent.locked and ratio > collapse_factor,
        )
    )

    # Gate 3: sever the shared reservoir -> gate extinction must go to ~1.
    shared = gate_extinction_ratio(multibeam)
    severed_cfg = MultiBeamConfig(**{**multibeam.__dict__, "shared_reservoir": False})
    severed = gate_extinction_ratio(severed_cfg)
    reports.append(
        NullGateReport(
            name="shared_gain_reservoir",
            effect_with_physics=shared,
            effect_without=severed,
            collapse_ratio=shared / max(severed, 1e-12),
            passed=shared > collapse_factor * severed and abs(severed - 1.0) < 0.5,
        )
    )

    return reports
