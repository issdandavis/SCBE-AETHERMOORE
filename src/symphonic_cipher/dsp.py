"""
Digital Signal Processing (DSP) Pipeline for Symphonic Cipher.

This module implements the studio engineering stages as mathematical operators:
- Section 3.2: Gain Staging (linear gain g)
- Section 3.3: Mic Pattern Filter (polar pattern weighting)
- Section 3.6: DAW Routing Matrix M ∈ ℝ^{C×C}
- Section 3.7: Parametric EQ (Biquad IIR filter)
- Section 3.8: Dynamic Range Compressor
- Section 3.9: Convolution Reverb
- Section 3.10: Stereo Panning (constant-power law)

Each stage is a deterministic, mathematically defined transform.
"""

import numpy as np
from typing import Optional, Tuple, List, Union
from dataclasses import dataclass
from enum import Enum


# =============================================================================
# CONSTANTS
# =============================================================================

DEFAULT_SAMPLE_RATE = 44_100


# =============================================================================
# SECTION 3.2: GAIN STAGING
# =============================================================================

class GainStage:
    """
    Linear gain stage for preamp emulation and level normalization.

    Mathematical definition:
        v₁ = g · v₀
        where g = 10^(G_dB / 20), G_dB ∈ ℝ

    Purpose: Normalize dynamic range before non-linear processing.
    """

    def __init__(self, gain_db: float = 0.0):
        """
        Initialize gain stage.

        Args:
            gain_db: Gain in decibels (0 dB = unity gain).
        """
        self.gain_db = gain_db
        self._linear_gain = 10 ** (gain_db / 20.0)

    @property
    def linear_gain(self) -> float:
        """Get linear gain factor g."""
        return self._linear_gain

    def set_gain_db(self, gain_db: float) -> None:
        """Set gain in decibels."""
        self.gain_db = gain_db
        self._linear_gain = 10 ** (gain_db / 20.0)

    def process(self, signal: np.ndarray) -> np.ndarray:
        """
        Apply gain to signal.

        Args:
            signal: Input signal v₀.

        Returns:
            Gained signal v₁ = g · v₀.
        """
        return signal * self._linear_gain

    @staticmethod
    def db_to_linear(db: float) -> float:
        """Convert decibels to linear gain."""
        return 10 ** (db / 20.0)

    @staticmethod
    def linear_to_db(linear: float) -> float:
        """Convert linear gain to decibels."""
        if linear <= 0:
            return -np.inf
        return 20.0 * np.log10(linear)


# =============================================================================
# SECTION 3.3: MIC PATTERN FILTER
# =============================================================================

class MicPattern(Enum):
    """Microphone polar pattern types."""
    OMNI = "omni"            # a = 0
    CARDIOID = "cardioid"    # a = 0.5
    SUPERCARDIOID = "supercardioid"  # a = 0.63
    HYPERCARDIOID = "hypercardioid"  # a = 0.75
    FIGURE_8 = "figure_8"    # a = 1.0


class MicPatternFilter:
    """
    Directional weighting based on microphone polar pattern.

    Mathematical definition (Section 3.3):
        v₂[i] = v₁[i] · (a + (1-a) · cos(θᵢ - θ_axis))

    where:
        a ∈ [0,1] - cardioid coefficient
            0 = omnidirectional (no spatial selectivity)
            1 = figure-8 (bidirectional)
        θ_axis - direction the mic points (typically 0)
        θᵢ - angle of source i

    If spatial modeling not needed, set a = 0 (omnidirectional).
    """

    PATTERN_COEFFICIENTS = {
        MicPattern.OMNI: 0.0,
        MicPattern.CARDIOID: 0.5,
        MicPattern.SUPERCARDIOID: 0.63,
        MicPattern.HYPERCARDIOID: 0.75,
        MicPattern.FIGURE_8: 1.0,
    }

    def __init__(
        self,
        pattern: MicPattern = MicPattern.OMNI,
        axis_angle: float = 0.0
    ):
        """
        Initialize mic pattern filter.

        Args:
            pattern: Polar pattern type.
            axis_angle: Direction mic points (radians).
        """
        self.pattern = pattern
        self.axis_angle = axis_angle
        self.a = self.PATTERN_COEFFICIENTS[pattern]

    def process(
        self,
        signal: np.ndarray,
        source_angles: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Apply directional weighting to signal.

        Args:
            signal: Input signal v₁ (can be multi-channel).
            source_angles: Angles of sources θᵢ (radians).
                          If None, assumes on-axis (θ = θ_axis).

        Returns:
            Weighted signal v₂.
        """
        if self.a == 0.0:  # Omnidirectional - no change
            return signal

        if source_angles is None:
            # Assume on-axis
            return signal

        # Calculate angular gain for each source
        angle_diff = source_angles - self.axis_angle
        gain = self.a + (1 - self.a) * np.cos(angle_diff)

        # Apply to signal (broadcast if needed)
        if signal.ndim == 1:
            # Single channel - average gain
            return signal * np.mean(gain)
        else:
            # Multi-channel - per-channel gain
            return signal * gain.reshape(-1, 1)


# =============================================================================
# SECTION 3.6: DAW ROUTING MATRIX
# =============================================================================

class DAWRoutingMatrix:
    """
    DAW-style signal routing using matrix multiplication.

    Mathematical definition (Section 3.6):
        X = M · x_raw
        where M ∈ ℝ^{C×C} is upper-triangular (typical DAW routing)

    Single-track: M = [1]
    Parallel bus (dry/wet): M = [[1, 0], [α, 1]] where α ∈ [0,1]
    """

    def __init__(self, num_channels: int = 1):
        """
        Initialize routing matrix.

        Args:
            num_channels: Number of virtual tracks C.
        """
        self.num_channels = num_channels
        self._matrix = np.eye(num_channels, dtype=np.float64)

    @property
    def matrix(self) -> np.ndarray:
        """Get routing matrix M."""
        return self._matrix.copy()

    def set_matrix(self, matrix: np.ndarray) -> None:
        """
        Set custom routing matrix.

        Args:
            matrix: Square matrix M ∈ ℝ^{C×C}.
        """
        if matrix.shape != (self.num_channels, self.num_channels):
            raise ValueError(f"Matrix must be {self.num_channels}x{self.num_channels}")
        self._matrix = matrix.astype(np.float64)

    def set_send(self, from_ch: int, to_ch: int, level: float) -> None:
        """
        Set send level from one channel to another.

        Args:
            from_ch: Source channel index.
            to_ch: Destination channel index.
            level: Send level (0.0 to 1.0).
        """
        self._matrix[to_ch, from_ch] = level

    def create_parallel_bus(self, dry_wet_ratio: float = 0.5) -> None:
        """
        Create a 2-channel parallel bus (dry + wet).

        Args:
            dry_wet_ratio: Amount of signal sent to wet bus (α).
        """
        self.num_channels = 2
        self._matrix = np.array([
            [1.0, 0.0],
            [dry_wet_ratio, 1.0]
        ], dtype=np.float64)

    def process(self, signal: np.ndarray) -> np.ndarray:
        """
        Apply routing matrix to signal.

        Args:
            signal: Input signal x_raw (1D or 2D).

        Returns:
            Routed signal X = M · x_raw.
        """
        if self.num_channels == 1:
            return signal

        if signal.ndim == 1:
            # Expand mono to multi-channel
            signal_2d = np.tile(signal, (self.num_channels, 1))
        else:
            signal_2d = signal

        return self._matrix @ signal_2d


# =============================================================================
# SECTION 3.7: PARAMETRIC EQ (BIQUAD)
# =============================================================================

class EQType(Enum):
    """Types of biquad EQ filters."""
    LOWPASS = "lowpass"
    HIGHPASS = "highpass"
    BANDPASS = "bandpass"
    NOTCH = "notch"
    PEAK = "peak"
    LOWSHELF = "lowshelf"
    HIGHSHELF = "highshelf"


@dataclass
class BiquadCoefficients:
    """Biquad filter coefficients."""
    b0: float
    b1: float
    b2: float
    a0: float
    a1: float
    a2: float


class ParametricEQ:
    """
    Parametric equalizer using biquad (second-order IIR) filter.

    Mathematical definition (Section 3.7):
        y[n] = b₀x[n] + b₁x[n-1] + b₂x[n-2] - a₁y[n-1] - a₂y[n-2]

    Coefficients for peaking EQ at center frequency f_c with gain G (dB) and Q:
        ω = 2π f_c / F_s
        α = sin(ω) / (2Q)
        A = 10^(G/40)

        b₀ = 1 + α·A
        b₁ = -2 cos(ω)
        b₂ = 1 - α·A
        a₀ = 1 + α/A
        a₁ = -2 cos(ω)
        a₂ = 1 - α/A

    All coefficients normalized by a₀.
    """

    def __init__(self, sample_rate: int = DEFAULT_SAMPLE_RATE):
        """
        Initialize parametric EQ.

        Args:
            sample_rate: Sample rate F_s (Hz).
        """
        self.sample_rate = sample_rate
        self._coeffs: Optional[BiquadCoefficients] = None
        self._state = np.zeros(2)  # Filter state [x[n-1], x[n-2]]
        self._output_state = np.zeros(2)  # [y[n-1], y[n-2]]

    def calculate_peak_coefficients(
        self,
        center_freq: float,
        gain_db: float,
        q: float
    ) -> BiquadCoefficients:
        """
        Calculate biquad coefficients for peaking EQ.

        Args:
            center_freq: Center frequency f_c (Hz).
            gain_db: Gain G (dB).
            q: Q factor (bandwidth control).

        Returns:
            Biquad filter coefficients.
        """
        omega = 2 * np.pi * center_freq / self.sample_rate
        alpha = np.sin(omega) / (2 * q)
        A = 10 ** (gain_db / 40)

        b0 = 1 + alpha * A
        b1 = -2 * np.cos(omega)
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * np.cos(omega)
        a2 = 1 - alpha / A

        # Normalize by a0
        return BiquadCoefficients(
            b0=b0 / a0,
            b1=b1 / a0,
            b2=b2 / a0,
            a0=1.0,
            a1=a1 / a0,
            a2=a2 / a0
        )

    def calculate_lowpass_coefficients(
        self,
        cutoff_freq: float,
        q: float = 0.707
    ) -> BiquadCoefficients:
        """Calculate biquad coefficients for lowpass filter."""
        omega = 2 * np.pi * cutoff_freq / self.sample_rate
        alpha = np.sin(omega) / (2 * q)
        cos_omega = np.cos(omega)

        b0 = (1 - cos_omega) / 2
        b1 = 1 - cos_omega
        b2 = (1 - cos_omega) / 2
        a0 = 1 + alpha
        a1 = -2 * cos_omega
        a2 = 1 - alpha

        return BiquadCoefficients(
            b0=b0 / a0, b1=b1 / a0, b2=b2 / a0,
            a0=1.0, a1=a1 / a0, a2=a2 / a0
        )

    def calculate_highpass_coefficients(
        self,
        cutoff_freq: float,
        q: float = 0.707
    ) -> BiquadCoefficients:
        """Calculate biquad coefficients for highpass filter."""
        omega = 2 * np.pi * cutoff_freq / self.sample_rate
        alpha = np.sin(omega) / (2 * q)
        cos_omega = np.cos(omega)

        b0 = (1 + cos_omega) / 2
        b1 = -(1 + cos_omega)
        b2 = (1 + cos_omega) / 2
        a0 = 1 + alpha
        a1 = -2 * cos_omega
        a2 = 1 - alpha

        return BiquadCoefficients(
            b0=b0 / a0, b1=b1 / a0, b2=b2 / a0,
            a0=1.0, a1=a1 / a0, a2=a2 / a0
        )

    def set_peak(self, center_freq: float, gain_db: float, q: float) -> None:
        """Configure as peaking EQ."""
        self._coeffs = self.calculate_peak_coefficients(center_freq, gain_db, q)
        self.reset()

    def set_lowpass(self, cutoff_freq: float, q: float = 0.707) -> None:
        """Configure as lowpass filter."""
        self._coeffs = self.calculate_lowpass_coefficients(cutoff_freq, q)
        self.reset()

    def set_highpass(self, cutoff_freq: float, q: float = 0.707) -> None:
        """Configure as highpass filter."""
        self._coeffs = self.calculate_highpass_coefficients(cutoff_freq, q)
        self.reset()

    def reset(self) -> None:
        """Reset filter state."""
        self._state = np.zeros(2)
        self._output_state = np.zeros(2)

    def process(self, signal: np.ndarray) -> np.ndarray:
        """
        Apply biquad filter to signal.

        Args:
            signal: Input signal x[n].

        Returns:
            Filtered signal y[n].
        """
        if self._coeffs is None:
            return signal

        c = self._coeffs
        output = np.zeros_like(signal)

        for n in range(len(signal)):
            # y[n] = b₀x[n] + b₁x[n-1] + b₂x[n-2] - a₁y[n-1] - a₂y[n-2]
            x_n = signal[n]
            y_n = (c.b0 * x_n +
                   c.b1 * self._state[0] +
                   c.b2 * self._state[1] -
                   c.a1 * self._output_state[0] -
                   c.a2 * self._output_state[1])

            # Update state
            self._state[1] = self._state[0]
            self._state[0] = x_n
            self._output_state[1] = self._output_state[0]
            self._output_state[0] = y_n

            output[n] = y_n

        return output

    def process_vectorized(self, signal: np.ndarray) -> np.ndarray:
        """
        Vectorized biquad filter (faster for long signals).

        Uses scipy-style direct form II implementation.
        """
        if self._coeffs is None:
            return signal

        from scipy.signal import lfilter
        c = self._coeffs
        b = [c.b0, c.b1, c.b2]
        a = [1.0, c.a1, c.a2]
        return lfilter(b, a, signal)


# =============================================================================
# SECTION 3.8: DYNAMIC RANGE COMPRESSOR
# =============================================================================

class DynamicCompressor:
    """
    Dynamic range compressor with attack/release envelope.

    Mathematical definition (Section 3.8):
        Piecewise-linear gain reduction:
            G_comp(x) = x                           if |x| ≤ T
                      = sgn(x) · (T + (|x|-T)/R)    if |x| > T

        where T = threshold, R = ratio (R ≥ 1)

        Attack/release smoothing (first-order filter):
            g[n] = α_a · g[n-1] + (1-α_a) · G_comp(x[n])
            α_a = exp(-1 / (F_s · τ_a))

        Output: y[n] = g[n] · x[n]
    """

    def __init__(
        self,
        threshold_db: float = -20.0,
        ratio: float = 4.0,
        attack_ms: float = 10.0,
        release_ms: float = 100.0,
        sample_rate: int = DEFAULT_SAMPLE_RATE
    ):
        """
        Initialize compressor.

        Args:
            threshold_db: Threshold T in dB (below which no compression).
            ratio: Compression ratio R (e.g., 4:1 means 4 dB input → 1 dB output above threshold).
            attack_ms: Attack time τ_a in milliseconds.
            release_ms: Release time τ_r in milliseconds.
            sample_rate: Sample rate F_s.
        """
        self.sample_rate = sample_rate
        self.threshold_db = threshold_db
        self.threshold_linear = 10 ** (threshold_db / 20)
        self.ratio = ratio
        self.attack_ms = attack_ms
        self.release_ms = release_ms

        # Calculate smoothing coefficients
        self._alpha_attack = np.exp(-1.0 / (sample_rate * attack_ms / 1000))
        self._alpha_release = np.exp(-1.0 / (sample_rate * release_ms / 1000))
        self._gain_state = 1.0

    def _compute_gain(self, x_abs: float) -> float:
        """
        Compute instantaneous gain reduction.

        G_comp(x) = x                           if |x| ≤ T
                  = sgn(x) · (T + (|x|-T)/R)    if |x| > T
        """
        if x_abs <= self.threshold_linear:
            return 1.0

        # Above threshold: reduce gain
        excess = x_abs - self.threshold_linear
        compressed = self.threshold_linear + excess / self.ratio
        return compressed / x_abs if x_abs > 0 else 1.0

    def process(self, signal: np.ndarray) -> np.ndarray:
        """
        Apply compression to signal.

        Args:
            signal: Input signal x[n].

        Returns:
            Compressed signal y[n].
        """
        output = np.zeros_like(signal)

        for n in range(len(signal)):
            x_n = signal[n]
            x_abs = abs(x_n)

            # Compute target gain
            target_gain = self._compute_gain(x_abs)

            # Apply attack/release smoothing
            if target_gain < self._gain_state:
                # Attack (gain decreasing)
                alpha = self._alpha_attack
            else:
                # Release (gain increasing)
                alpha = self._alpha_release

            self._gain_state = alpha * self._gain_state + (1 - alpha) * target_gain

            # Apply gain
            output[n] = x_n * self._gain_state

        return output

    def reset(self) -> None:
        """Reset compressor state."""
        self._gain_state = 1.0


# =============================================================================
# SECTION 3.9: CONVOLUTION REVERB
# =============================================================================

class ConvolutionReverb:
    """
    Convolution reverb using room impulse response (RIR).

    Mathematical definition (Section 3.9):
        z[n] = (x * h)[n] = Σₖ x[n-k] · h[k]

        where h[k] is the RIR sampled at F_s.

        Dry/wet mix:
            y_reverb[n] = (1-w) · x[n] + w · z[n]

        where w ∈ [0,1] is wet mix amount.
    """

    def __init__(
        self,
        impulse_response: Optional[np.ndarray] = None,
        wet_mix: float = 0.3,
        sample_rate: int = DEFAULT_SAMPLE_RATE
    ):
        """
        Initialize convolution reverb.

        Args:
            impulse_response: Room impulse response h[k].
                             If None, generates a simple decay.
            wet_mix: Wet mix amount w ∈ [0,1].
            sample_rate: Sample rate F_s.
        """
        self.sample_rate = sample_rate
        self.wet_mix = wet_mix

        if impulse_response is not None:
            self._ir = impulse_response.astype(np.float64)
        else:
            # Generate simple exponential decay IR (0.5 second)
            self._ir = self._generate_simple_ir(0.5)

    def _generate_simple_ir(self, decay_time: float) -> np.ndarray:
        """
        Generate a simple exponential decay impulse response.

        Args:
            decay_time: Time for -60dB decay (seconds).

        Returns:
            Impulse response array.
        """
        n_samples = int(self.sample_rate * decay_time)
        t = np.arange(n_samples) / self.sample_rate

        # Exponential decay: A · exp(-t/τ)
        # τ chosen so that exp(-decay_time/τ) = 0.001 (-60dB)
        tau = decay_time / np.log(1000)
        ir = np.exp(-t / tau)

        # Add some early reflections
        for delay_ms, amp in [(10, 0.7), (25, 0.5), (40, 0.3)]:
            delay_samples = int(self.sample_rate * delay_ms / 1000)
            if delay_samples < n_samples:
                ir[delay_samples] += amp

        return ir / np.max(np.abs(ir))

    def set_impulse_response(self, ir: np.ndarray) -> None:
        """Set custom impulse response."""
        self._ir = ir.astype(np.float64)

    def set_wet_mix(self, wet_mix: float) -> None:
        """Set wet mix amount."""
        self.wet_mix = np.clip(wet_mix, 0.0, 1.0)

    def process(self, signal: np.ndarray) -> np.ndarray:
        """
        Apply convolution reverb to signal.

        Args:
            signal: Input signal x[n].

        Returns:
            Signal with reverb y_reverb[n].
        """
        # Convolve: z[n] = (x * h)[n]
        wet = np.convolve(signal, self._ir, mode='full')[:len(signal)]

        # Mix: y = (1-w)·x + w·z
        return (1 - self.wet_mix) * signal + self.wet_mix * wet

    def process_fft(self, signal: np.ndarray) -> np.ndarray:
        """
        Apply convolution reverb using FFT (faster for long signals).

        Uses overlap-add method for efficiency.
        """
        from scipy.signal import fftconvolve
        wet = fftconvolve(signal, self._ir, mode='full')[:len(signal)]
        return (1 - self.wet_mix) * signal + self.wet_mix * wet


# =============================================================================
# SECTION 3.10: STEREO PANNING
# =============================================================================

class StereoPanner:
    """
    Stereo panning using constant-power law.

    Mathematical definition (Section 3.10):
        For mono input y[n] and pan position p ∈ [-1,1]:
            L[n] = y[n] · cos(π/4 · (p+1))
            R[n] = y[n] · sin(π/4 · (p+1))

        where:
            p = -1 → hard left
            p = 0  → center
            p = +1 → hard right

    Output: X_stereo = [L^T, R^T]^T
    """

    def __init__(self, pan_position: float = 0.0):
        """
        Initialize stereo panner.

        Args:
            pan_position: Pan position p ∈ [-1,1].
        """
        self.set_pan(pan_position)

    def set_pan(self, pan_position: float) -> None:
        """
        Set pan position.

        Args:
            pan_position: Pan position p ∈ [-1,1].
        """
        self.pan_position = np.clip(pan_position, -1.0, 1.0)

        # Pre-calculate gains using constant-power law
        angle = np.pi / 4 * (self.pan_position + 1)
        self._gain_left = np.cos(angle)
        self._gain_right = np.sin(angle)

    def process(self, signal: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply stereo panning to mono signal.

        Args:
            signal: Mono input y[n].

        Returns:
            Tuple of (left channel L[n], right channel R[n]).
        """
        left = signal * self._gain_left
        right = signal * self._gain_right
        return left, right

    def process_to_stereo(self, signal: np.ndarray) -> np.ndarray:
        """
        Apply stereo panning and return as stereo array.

        Args:
            signal: Mono input y[n].

        Returns:
            Stereo array X_stereo with shape (2, N).
        """
        left, right = self.process(signal)
        return np.array([left, right])

    @staticmethod
    def mix_stereo(stereo_signals: List[np.ndarray]) -> np.ndarray:
        """
        Mix multiple stereo signals together.

        Args:
            stereo_signals: List of stereo arrays (each shape (2, N)).

        Returns:
            Mixed stereo signal.
        """
        mixed = np.sum(stereo_signals, axis=0)
        # Normalize to prevent clipping
        max_val = np.max(np.abs(mixed))
        if max_val > 1.0:
            mixed /= max_val
        return mixed


# =============================================================================
# DSP CHAIN - COMBINES ALL STAGES
# =============================================================================

class DSPChain:
    """
    Complete DSP processing chain combining all studio stages.

    Signal flow:
        Input → Gain Stage → Mic Pattern → EQ → Compressor →
        Reverb → Stereo Panner → Output
    """

    def __init__(self, sample_rate: int = DEFAULT_SAMPLE_RATE):
        """
        Initialize DSP chain with default settings.

        Args:
            sample_rate: Sample rate F_s.
        """
        self.sample_rate = sample_rate

        # Initialize all stages with defaults
        self.gain_stage = GainStage(gain_db=0.0)
        self.mic_filter = MicPatternFilter(pattern=MicPattern.OMNI)
        self.routing = DAWRoutingMatrix(num_channels=1)
        self.eq = ParametricEQ(sample_rate=sample_rate)
        self.compressor = DynamicCompressor(sample_rate=sample_rate)
        self.reverb = ConvolutionReverb(sample_rate=sample_rate)
        self.panner = StereoPanner(pan_position=0.0)

        # Enable/disable flags
        self._enable_gain = True
        self._enable_mic = False  # Off by default (omnidirectional)
        self._enable_eq = True
        self._enable_compression = True
        self._enable_reverb = True
        self._enable_panning = True

    def configure_eq(self, center_freq: float, gain_db: float, q: float) -> None:
        """Configure the EQ as a peaking filter."""
        self.eq.set_peak(center_freq, gain_db, q)

    def configure_compressor(
        self,
        threshold_db: float = -20.0,
        ratio: float = 4.0,
        attack_ms: float = 10.0,
        release_ms: float = 100.0
    ) -> None:
        """Configure compressor parameters."""
        self.compressor = DynamicCompressor(
            threshold_db=threshold_db,
            ratio=ratio,
            attack_ms=attack_ms,
            release_ms=release_ms,
            sample_rate=self.sample_rate
        )

    def configure_reverb(self, wet_mix: float = 0.3, decay_time: float = 0.5) -> None:
        """Configure reverb parameters."""
        self.reverb = ConvolutionReverb(
            wet_mix=wet_mix,
            sample_rate=self.sample_rate
        )
        if decay_time != 0.5:
            self.reverb._ir = self.reverb._generate_simple_ir(decay_time)

    def configure_panning(self, pan_position: float) -> None:
        """Configure stereo pan position."""
        self.panner.set_pan(pan_position)

    def enable_stage(self, stage: str, enabled: bool = True) -> None:
        """
        Enable or disable a processing stage.

        Args:
            stage: Stage name ('gain', 'mic', 'eq', 'compression', 'reverb', 'panning').
            enabled: Whether stage is enabled.
        """
        stage_map = {
            'gain': '_enable_gain',
            'mic': '_enable_mic',
            'eq': '_enable_eq',
            'compression': '_enable_compression',
            'reverb': '_enable_reverb',
            'panning': '_enable_panning',
        }
        if stage in stage_map:
            setattr(self, stage_map[stage], enabled)

    def reset(self) -> None:
        """Reset all stateful stages."""
        self.eq.reset()
        self.compressor.reset()

    def process(self, signal: np.ndarray) -> np.ndarray:
        """
        Process signal through the complete DSP chain.

        Args:
            signal: Input mono signal.

        Returns:
            Processed stereo signal (shape: (2, N)).
        """
        x = signal.copy()

        # Stage 1: Gain
        if self._enable_gain:
            x = self.gain_stage.process(x)

        # Stage 2: Mic Pattern Filter
        if self._enable_mic:
            x = self.mic_filter.process(x)

        # Stage 3: EQ
        if self._enable_eq and self.eq._coeffs is not None:
            x = self.eq.process_vectorized(x)

        # Stage 4: Compression
        if self._enable_compression:
            x = self.compressor.process(x)

        # Stage 5: Reverb
        if self._enable_reverb:
            x = self.reverb.process_fft(x)

        # Stage 6: Stereo Panning
        if self._enable_panning:
            stereo = self.panner.process_to_stereo(x)
        else:
            stereo = np.array([x, x])  # Dual mono

        return stereo

    def process_mono(self, signal: np.ndarray) -> np.ndarray:
        """
        Process signal through DSP chain, returning mono.

        Args:
            signal: Input mono signal.

        Returns:
            Processed mono signal.
        """
        stereo = self.process(signal)
        # Sum to mono
        return (stereo[0] + stereo[1]) / 2
