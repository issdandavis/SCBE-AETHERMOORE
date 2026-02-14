"""
Dual Ternary Encoding with Full Negative State Flux - Python Reference

Standard binary: {0, 1} -> amplitude only
Negative binary: {-1, 0, 1} -> amplitude + phase
Dual ternary:   {-1, 0, 1} x {-1, 0, 1} -> 9 states

Full State Space (3x3 = 9 states):
  (-1, -1)  (-1, 0)  (-1, 1)   <- negative coherence row
  ( 0, -1)  ( 0, 0)  ( 0, 1)   <- neutral row
  ( 1, -1)  ( 1, 0)  ( 1, 1)   <- positive coherence row

Energy model: E(p, m) = p^2 + m^2 + p*m

@module ai_brain/dual_ternary
@layer Layer 9, Layer 10, Layer 12, Layer 14
@version 1.0.0
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .unified_state import PHI, BRAIN_EPSILON

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DualTernaryState:
    """A single dual ternary state: primary x mirror in {-1, 0, 1}^2."""
    primary: int  # {-1, 0, 1}
    mirror: int   # {-1, 0, 1}


@dataclass
class StateEnergy:
    """Energy properties of a dual ternary state."""
    energy: float
    primary_energy: float
    mirror_energy: float
    interaction: float
    phase: str  # 'constructive' | 'destructive' | 'neutral' | 'negative_resonance'


@dataclass
class DualTernarySpectrum:
    """Spectral signature of a dual ternary sequence."""
    primary_magnitudes: List[float]
    mirror_magnitudes: List[float]
    cross_correlation: List[float]
    ninefold_energy: float
    coherence: float
    phase_anomaly: float


@dataclass
class FractalDimensionResult:
    """Fractal dimension estimate for dual ternary state sequences."""
    base_dimension: float
    sign_entropy: float
    hausdorff_dimension: float
    symmetry_breaking: float
    self_similarity: float


@dataclass
class DualTernaryConfig:
    """Configuration for the Dual Ternary system."""
    min_sequence_length: int = 8
    phase_anomaly_threshold: float = 0.7
    fractal_deviation_threshold: float = 0.5
    mirror_depth: int = 4
    entropy_normalization: float = math.log(3)


DEFAULT_DUAL_TERNARY_CONFIG = DualTernaryConfig()


# ---------------------------------------------------------------------------
# Full 9-State Space
# ---------------------------------------------------------------------------

FULL_STATE_SPACE: List[DualTernaryState] = [
    DualTernaryState(primary=-1, mirror=-1),
    DualTernaryState(primary=-1, mirror=0),
    DualTernaryState(primary=-1, mirror=1),
    DualTernaryState(primary=0, mirror=-1),
    DualTernaryState(primary=0, mirror=0),
    DualTernaryState(primary=0, mirror=1),
    DualTernaryState(primary=1, mirror=-1),
    DualTernaryState(primary=1, mirror=0),
    DualTernaryState(primary=1, mirror=1),
]


# ---------------------------------------------------------------------------
# State Energy & Phase Classification
# ---------------------------------------------------------------------------

def compute_state_energy(state: DualTernaryState) -> StateEnergy:
    """Compute the energy E(p, m) = p^2 + m^2 + p*m."""
    p, m = state.primary, state.mirror
    primary_energy = p * p
    mirror_energy = m * m
    interaction = p * m
    energy = primary_energy + mirror_energy + interaction

    if p > 0 and m > 0:
        phase = "constructive"
    elif p < 0 and m < 0:
        phase = "negative_resonance"
    elif (p > 0 and m < 0) or (p < 0 and m > 0):
        phase = "destructive"
    else:
        phase = "neutral"

    return StateEnergy(
        energy=energy,
        primary_energy=primary_energy,
        mirror_energy=mirror_energy,
        interaction=interaction,
        phase=phase,
    )


def state_index(state: DualTernaryState) -> int:
    """Map (primary, mirror) -> unique index 0..8."""
    return (state.primary + 1) * 3 + (state.mirror + 1)


def state_from_index(index: int) -> DualTernaryState:
    """Reconstruct dual ternary state from index."""
    clamped = max(0, min(8, int(index)))
    primary = (clamped // 3) - 1
    mirror = (clamped % 3) - 1
    return DualTernaryState(primary=primary, mirror=mirror)


# ---------------------------------------------------------------------------
# State Transitions
# ---------------------------------------------------------------------------

def _clip(value: int) -> int:
    """Clip a value to ternary set {-1, 0, 1}."""
    if value >= 1:
        return 1
    if value <= -1:
        return -1
    return 0


def transition(current: DualTernaryState, delta_p: int, delta_m: int) -> DualTernaryState:
    """Transition from one state to another with deltas."""
    return DualTernaryState(
        primary=_clip(current.primary + delta_p),
        mirror=_clip(current.mirror + delta_m),
    )


# ---------------------------------------------------------------------------
# Encoding: Continuous -> Dual Ternary
# ---------------------------------------------------------------------------

def _quantize(value: float, threshold: float) -> int:
    """Quantize continuous value to ternary."""
    if value > threshold:
        return 1
    if value < -threshold:
        return -1
    return 0


def encode_to_dual_ternary(
    amplitude: float, phase: float, threshold: float = 0.33
) -> DualTernaryState:
    """Encode continuous values into a dual ternary state."""
    return DualTernaryState(
        primary=_quantize(amplitude, threshold),
        mirror=_quantize(phase, threshold),
    )


def encode_sequence(values: List[float], threshold: float = 0.33) -> List[DualTernaryState]:
    """Encode a sequence of values into dual ternary states (pairs)."""
    states: List[DualTernaryState] = []
    i = 0
    while i < len(values) - 1:
        states.append(encode_to_dual_ternary(values[i], values[i + 1], threshold))
        i += 2
    if len(values) % 2 == 1:
        states.append(encode_to_dual_ternary(values[-1], 0, threshold))
    return states


# ---------------------------------------------------------------------------
# DFT (Discrete Fourier Transform)
# ---------------------------------------------------------------------------

def _simple_dft(signal: List[float]) -> List[Tuple[float, float]]:
    """Simple DFT returning list of (re, im) pairs."""
    n = len(signal)
    result: List[Tuple[float, float]] = []
    for k in range(n):
        re = 0.0
        im = 0.0
        for idx in range(n):
            angle = -2.0 * math.pi * k * idx / n
            re += signal[idx] * math.cos(angle)
            im += signal[idx] * math.sin(angle)
        result.append((re, im))
    return result


def _next_pow2(n: int) -> int:
    p = 1
    while p < n:
        p <<= 1
    return p


# ---------------------------------------------------------------------------
# Spectral Analysis
# ---------------------------------------------------------------------------

def _compute_phase_anomaly(sequence: List[DualTernaryState]) -> float:
    """Detect phase anomalies from sign distribution bias via Shannon entropy."""
    if not sequence:
        return 0.0

    histogram = [0] * 9
    for s in sequence:
        histogram[state_index(s)] += 1

    entropy = 0.0
    for count in histogram:
        if count > 0:
            p = count / len(sequence)
            entropy -= p * math.log(p)

    max_entropy = math.log(9)
    normalized = entropy / max_entropy if max_entropy > 0 else 0.0
    return 1.0 - normalized


def compute_spectrum(
    sequence: List[DualTernaryState],
    config: Optional[DualTernaryConfig] = None,
) -> DualTernarySpectrum:
    """Compute spectral signature of a dual ternary sequence."""
    config = config or DEFAULT_DUAL_TERNARY_CONFIG

    if len(sequence) < config.min_sequence_length:
        return DualTernarySpectrum(
            primary_magnitudes=[],
            mirror_magnitudes=[],
            cross_correlation=[],
            ninefold_energy=0.0,
            coherence=0.0,
            phase_anomaly=0.0,
        )

    n = _next_pow2(len(sequence))
    primary_signal = [0.0] * n
    mirror_signal = [0.0] * n
    for i, s in enumerate(sequence):
        primary_signal[i] = float(s.primary)
        mirror_signal[i] = float(s.mirror)

    primary_dft = _simple_dft(primary_signal)
    mirror_dft = _simple_dft(mirror_signal)

    primary_mag = [math.sqrt(re * re + im * im) for re, im in primary_dft]
    mirror_mag = [math.sqrt(re * re + im * im) for re, im in mirror_dft]
    cross = [
        primary_dft[i][0] * mirror_dft[i][0] + primary_dft[i][1] * mirror_dft[i][1]
        for i in range(n)
    ]

    # 9-fold symmetry energy
    histogram = [0] * 9
    for s in sequence:
        histogram[state_index(s)] += 1
    ideal = len(sequence) / 9.0
    chi_squared = sum(
        (c - ideal) ** 2 / max(ideal, BRAIN_EPSILON) for c in histogram
    )
    ninefold_energy = 1.0 - 1.0 / (1.0 + chi_squared / len(sequence))

    # Spectral coherence
    total_primary = sum(v * v for v in primary_mag)
    total_mirror = sum(v * v for v in mirror_mag)
    total_cross = sum(abs(v) for v in cross)
    total_energy = total_primary + total_mirror
    coherence = total_cross / (total_energy + BRAIN_EPSILON) if total_energy > BRAIN_EPSILON else 0.0

    phase_anomaly = _compute_phase_anomaly(sequence)

    return DualTernarySpectrum(
        primary_magnitudes=primary_mag,
        mirror_magnitudes=mirror_mag,
        cross_correlation=cross,
        ninefold_energy=ninefold_energy,
        coherence=min(1.0, coherence),
        phase_anomaly=phase_anomaly,
    )


# ---------------------------------------------------------------------------
# Fractal Dimension
# ---------------------------------------------------------------------------

def _compute_sign_entropy(
    sequence: List[DualTernaryState], config: DualTernaryConfig
) -> float:
    """Sign entropy contribution to fractal dimension."""
    sign_patterns = [0] * 9
    for s in sequence:
        sp = (1 if s.primary > 0 else (-1 if s.primary < 0 else 0)) + 1
        sm = (1 if s.mirror > 0 else (-1 if s.mirror < 0 else 0)) + 1
        sign_patterns[sp * 3 + sm] += 1

    entropy = 0.0
    for count in sign_patterns:
        if count > 0:
            p = count / len(sequence)
            entropy -= p * math.log(p)

    return (entropy / (config.entropy_normalization * 2)) * 0.438


def _compute_symmetry_breaking(sequence: List[DualTernaryState]) -> float:
    """Jensen-Shannon divergence between primary and mirror distributions."""
    p_hist = [0, 0, 0]
    m_hist = [0, 0, 0]
    for s in sequence:
        p_hist[s.primary + 1] += 1
        m_hist[s.mirror + 1] += 1

    n = len(sequence)
    divergence = 0.0
    for i in range(3):
        pp = p_hist[i] / n
        pm = m_hist[i] / n
        mean = (pp + pm) / 2.0
        if pp > 0 and mean > 0:
            divergence += 0.5 * pp * math.log(pp / mean)
        if pm > 0 and mean > 0:
            divergence += 0.5 * pm * math.log(pm / mean)

    return min(1.0, divergence / math.log(2))


def _compute_self_similarity(
    sequence: List[DualTernaryState], config: DualTernaryConfig
) -> float:
    """Self-similarity across scales via energy comparison."""
    max_depth = min(config.mirror_depth, int(math.log2(len(sequence))) if len(sequence) > 1 else 0)
    if max_depth < 2:
        return 0.0

    energy_at_scale: List[float] = []
    for depth in range(max_depth):
        step = 1 << depth
        total_e = 0.0
        count = 0
        i = 0
        while i < len(sequence):
            e = compute_state_energy(sequence[i])
            total_e += e.energy
            count += 1
            i += step
        energy_at_scale.append(total_e / count if count > 0 else 0.0)

    total_corr = 0.0
    pairs = 0
    for i in range(len(energy_at_scale) - 1):
        max_e = max(energy_at_scale[i], energy_at_scale[i + 1])
        if max_e > BRAIN_EPSILON:
            min_e = min(energy_at_scale[i], energy_at_scale[i + 1])
            total_corr += min_e / max_e
            pairs += 1

    return total_corr / pairs if pairs > 0 else 0.0


def estimate_fractal_dimension(
    sequence: List[DualTernaryState],
    config: Optional[DualTernaryConfig] = None,
) -> FractalDimensionResult:
    """Estimate fractal dimension of a dual ternary state sequence.

    D = log(9)/log(3) + sign_entropy + interaction_term
    """
    config = config or DEFAULT_DUAL_TERNARY_CONFIG
    base_dimension = math.log(9) / math.log(3)  # Always 2.0

    if len(sequence) < 4:
        return FractalDimensionResult(
            base_dimension=base_dimension,
            sign_entropy=0.0,
            hausdorff_dimension=base_dimension,
            symmetry_breaking=0.0,
            self_similarity=0.0,
        )

    sign_entropy = _compute_sign_entropy(sequence, config)
    symmetry_breaking = _compute_symmetry_breaking(sequence)
    self_similarity = _compute_self_similarity(sequence, config)

    interaction_term = self_similarity * symmetry_breaking * math.log(PHI) / math.log(3)
    hausdorff_dimension = base_dimension + sign_entropy + interaction_term

    return FractalDimensionResult(
        base_dimension=base_dimension,
        sign_entropy=sign_entropy,
        hausdorff_dimension=hausdorff_dimension,
        symmetry_breaking=symmetry_breaking,
        self_similarity=self_similarity,
    )


# ---------------------------------------------------------------------------
# Dual Ternary System
# ---------------------------------------------------------------------------

class DualTernarySystem:
    """Dual Ternary Encoding System with full negative state flux.

    Manages encoding, spectral analysis, and fractal dimension monitoring
    for security anomaly detection.
    """

    def __init__(self, config: Optional[DualTernaryConfig] = None):
        self.config = config or DualTernaryConfig()
        self._history: List[DualTernaryState] = []
        self._step_counter = 0

    def encode(self, state_21d: List[float], threshold: float = 0.33) -> List[DualTernaryState]:
        """Encode a 21D brain state into dual ternary representation."""
        self._step_counter += 1
        encoded = encode_sequence(state_21d, threshold)
        self._history.extend(encoded)
        if len(self._history) > 1024:
            self._history = self._history[-1024:]
        return encoded

    def analyze_spectrum(self) -> DualTernarySpectrum:
        return compute_spectrum(self._history, self.config)

    def analyze_fractal_dimension(self) -> FractalDimensionResult:
        return estimate_fractal_dimension(self._history, self.config)

    def full_analysis(self) -> Dict[str, Any]:
        """Full security analysis: spectrum + fractal + threat assessment."""
        spectrum = self.analyze_spectrum()
        fractal = self.analyze_fractal_dimension()

        phase_anomaly_detected = spectrum.phase_anomaly >= self.config.phase_anomaly_threshold
        expected_dim = 2.0
        fractal_deviation = abs(fractal.hausdorff_dimension - expected_dim)
        fractal_anomaly_detected = fractal_deviation > self.config.fractal_deviation_threshold

        threat_score = min(
            1.0,
            spectrum.phase_anomaly * 0.4
            + spectrum.ninefold_energy * 0.3
            + (fractal_deviation / 2.0) * 0.3,
        )

        return {
            "spectrum": spectrum,
            "fractal": fractal,
            "phase_anomaly_detected": phase_anomaly_detected,
            "fractal_anomaly_detected": fractal_anomaly_detected,
            "threat_score": threat_score,
        }

    @staticmethod
    def to_tensor_product(state: DualTernaryState) -> List[List[int]]:
        """Convert state to 3x3 tensor product representation."""
        tensor = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        tensor[state.primary + 1][state.mirror + 1] = 1
        return tensor

    @staticmethod
    def tensor_histogram(sequence: List[DualTernaryState]) -> List[List[int]]:
        """Compute distribution across the 3x3 state space."""
        tensor = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        for s in sequence:
            tensor[s.primary + 1][s.mirror + 1] += 1
        return tensor

    @property
    def history_length(self) -> int:
        return len(self._history)

    @property
    def step(self) -> int:
        return self._step_counter

    @property
    def history(self) -> List[DualTernaryState]:
        return list(self._history)

    def reset(self) -> None:
        self._history = []
        self._step_counter = 0
