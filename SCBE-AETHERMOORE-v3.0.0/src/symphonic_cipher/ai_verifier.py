"""
AI-based Feature Extraction and Verification for Symphonic Cipher.

This module implements:
- Section 4.1: Feature Vector B extraction (RMS, spectral centroid, MFCC, etc.)
- Section 4.2: Neural Network Classifier for authentication
- Harmonic verification via FFT peak analysis

The AI verifier provides an additional security layer beyond the cryptographic
envelope, detecting synthetic/replayed audio through spectral analysis.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum


# =============================================================================
# CONSTANTS
# =============================================================================

DEFAULT_SAMPLE_RATE = 44_100
BASE_FREQ = 440.0
FREQ_STEP = 30.0
FREQ_TOLERANCE = 2.0  # Hz - tolerance for peak detection
AMP_TOLERANCE = 0.15  # Relative amplitude tolerance


# =============================================================================
# FEATURE VECTOR DEFINITION (Section 4.1)
# =============================================================================

@dataclass
class AudioFeatures:
    """
    Feature vector b for AI classification.

    Contains spectral and temporal features extracted from audio:
        b = [RMS, C, SF, MFCC_1..13, m_h, DR, PanSpread]^T ∈ ℝ^d

    Typical dimension d ≈ 30.
    """
    rms: float                      # Root Mean Square (overall level)
    spectral_centroid: float        # Brightness measure
    spectral_flatness: float        # Noise-like vs tone-like
    mfcc: np.ndarray               # Mel-frequency cepstral coefficients (13)
    harmonic_mask: np.ndarray      # Binary vector m_h for harmonic presence
    dynamic_range: float           # 20 log10(max/rms)
    pan_spread: float              # Stereo width (0 for mono)
    zero_crossing_rate: float      # Temporal texture measure
    spectral_rolloff: float        # Frequency below which 85% energy
    spectral_bandwidth: float      # Spread around centroid

    # Additional security features
    jitter: float                  # Pitch instability (F0 variance)
    shimmer: float                 # Amplitude instability
    sideband_energy_ratio: float   # Energy in sidebands vs fundamentals
    phase_coherence: float         # Phase alignment across harmonics

    def to_vector(self) -> np.ndarray:
        """Convert to flat feature vector for neural network input."""
        return np.concatenate([
            [self.rms],
            [self.spectral_centroid],
            [self.spectral_flatness],
            self.mfcc,
            self.harmonic_mask,
            [self.dynamic_range],
            [self.pan_spread],
            [self.zero_crossing_rate],
            [self.spectral_rolloff],
            [self.spectral_bandwidth],
            [self.jitter],
            [self.shimmer],
            [self.sideband_energy_ratio],
            [self.phase_coherence]
        ])

    @property
    def dimension(self) -> int:
        """Get feature vector dimension d."""
        return len(self.to_vector())


# =============================================================================
# FEATURE EXTRACTOR
# =============================================================================

class FeatureExtractor:
    """
    Extract audio features for AI-based verification.

    Implements the feature extraction formulas from Section 4.1:
        - RMS = sqrt(1/N * sum(L[n]^2 + R[n]^2))
        - Spectral Centroid C = sum(f_k * |X_k|) / sum(|X_k|)
        - Spectral Flatness SF = exp(mean(ln|X_k|)) / mean(|X_k|)
        - MFCC via Mel filterbank + DCT
        - Peak-Mask Consistency m_h
        - Dynamic Range DR = 20 log10(max/rms)
    """

    def __init__(
        self,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        n_mfcc: int = 13,
        n_mels: int = 40,
        fft_size: int = 2048,
        hop_size: int = 512
    ):
        """
        Initialize feature extractor.

        Args:
            sample_rate: Sample rate F_s.
            n_mfcc: Number of MFCC coefficients.
            n_mels: Number of Mel filterbank bands.
            fft_size: FFT window size.
            hop_size: Hop size between frames.
        """
        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc
        self.n_mels = n_mels
        self.fft_size = fft_size
        self.hop_size = hop_size

        # Pre-compute Mel filterbank
        self._mel_filterbank = self._create_mel_filterbank()

    def _create_mel_filterbank(self) -> np.ndarray:
        """
        Create Mel-scale filterbank matrix.

        Mel scale: m = 2595 * log10(1 + f/700)
        """
        # Frequency range
        low_freq = 0
        high_freq = self.sample_rate / 2

        # Mel scale conversion
        def hz_to_mel(f): return 2595 * np.log10(1 + f / 700)
        def mel_to_hz(m): return 700 * (10 ** (m / 2595) - 1)

        # Mel points
        low_mel = hz_to_mel(low_freq)
        high_mel = hz_to_mel(high_freq)
        mel_points = np.linspace(low_mel, high_mel, self.n_mels + 2)
        hz_points = mel_to_hz(mel_points)

        # FFT bin frequencies
        fft_bins = np.floor((self.fft_size + 1) * hz_points / self.sample_rate).astype(int)

        # Create filterbank
        filterbank = np.zeros((self.n_mels, self.fft_size // 2 + 1))
        for m in range(self.n_mels):
            for k in range(fft_bins[m], fft_bins[m + 1]):
                filterbank[m, k] = (k - fft_bins[m]) / (fft_bins[m + 1] - fft_bins[m])
            for k in range(fft_bins[m + 1], fft_bins[m + 2]):
                filterbank[m, k] = (fft_bins[m + 2] - k) / (fft_bins[m + 2] - fft_bins[m + 1])

        return filterbank

    def _compute_rms(self, signal: np.ndarray) -> float:
        """
        Compute Root Mean Square.

        RMS = sqrt(1/N * sum(x[n]^2))
        """
        return float(np.sqrt(np.mean(signal ** 2)))

    def _compute_spectral_centroid(
        self,
        magnitudes: np.ndarray,
        frequencies: np.ndarray
    ) -> float:
        """
        Compute spectral centroid (brightness measure).

        C = sum(f_k * |X_k|) / sum(|X_k|)
        """
        total_mag = np.sum(magnitudes)
        if total_mag == 0:
            return 0.0
        return float(np.sum(frequencies * magnitudes) / total_mag)

    def _compute_spectral_flatness(self, magnitudes: np.ndarray) -> float:
        """
        Compute spectral flatness (Wiener entropy).

        SF = exp(mean(ln|X_k|)) / mean(|X_k|)

        Values close to 1 indicate noise-like spectrum.
        Values close to 0 indicate tone-like spectrum.
        """
        magnitudes = np.maximum(magnitudes, 1e-10)  # Avoid log(0)
        geometric_mean = np.exp(np.mean(np.log(magnitudes)))
        arithmetic_mean = np.mean(magnitudes)
        if arithmetic_mean == 0:
            return 0.0
        return float(geometric_mean / arithmetic_mean)

    def _compute_mfcc(self, signal: np.ndarray) -> np.ndarray:
        """
        Compute Mel-Frequency Cepstral Coefficients.

        Steps:
        1. FFT
        2. Apply Mel filterbank
        3. Log compression
        4. DCT
        """
        # Pad signal if needed
        if len(signal) < self.fft_size:
            signal = np.pad(signal, (0, self.fft_size - len(signal)))

        # Compute FFT magnitude spectrum (average over frames)
        n_frames = max(1, (len(signal) - self.fft_size) // self.hop_size + 1)
        mel_spec = np.zeros(self.n_mels)

        for i in range(n_frames):
            start = i * self.hop_size
            frame = signal[start:start + self.fft_size]
            if len(frame) < self.fft_size:
                frame = np.pad(frame, (0, self.fft_size - len(frame)))

            # Apply window
            windowed = frame * np.hanning(self.fft_size)

            # FFT
            spectrum = np.abs(np.fft.rfft(windowed))

            # Apply Mel filterbank
            mel_spec += self._mel_filterbank @ spectrum

        mel_spec /= n_frames

        # Log compression
        mel_spec = np.log(np.maximum(mel_spec, 1e-10))

        # DCT to get MFCC
        mfcc = np.zeros(self.n_mfcc)
        for n in range(self.n_mfcc):
            mfcc[n] = np.sum(mel_spec * np.cos(np.pi * n * (np.arange(self.n_mels) + 0.5) / self.n_mels))

        return mfcc

    def _compute_zero_crossing_rate(self, signal: np.ndarray) -> float:
        """
        Compute zero-crossing rate (temporal texture).

        ZCR = 1/(N-1) * sum(|sign(x[n]) - sign(x[n-1])|) / 2
        """
        signs = np.sign(signal)
        sign_changes = np.abs(np.diff(signs))
        return float(np.mean(sign_changes) / 2)

    def _compute_spectral_rolloff(
        self,
        magnitudes: np.ndarray,
        frequencies: np.ndarray,
        threshold: float = 0.85
    ) -> float:
        """
        Compute spectral rolloff frequency.

        Frequency below which threshold% of total energy is contained.
        """
        cumulative_energy = np.cumsum(magnitudes ** 2)
        total_energy = cumulative_energy[-1]
        if total_energy == 0:
            return 0.0
        rolloff_idx = np.searchsorted(cumulative_energy, threshold * total_energy)
        return float(frequencies[min(rolloff_idx, len(frequencies) - 1)])

    def _compute_spectral_bandwidth(
        self,
        magnitudes: np.ndarray,
        frequencies: np.ndarray,
        centroid: float
    ) -> float:
        """
        Compute spectral bandwidth (spread around centroid).

        BW = sqrt(sum((f_k - C)^2 * |X_k|) / sum(|X_k|))
        """
        total_mag = np.sum(magnitudes)
        if total_mag == 0:
            return 0.0
        variance = np.sum(((frequencies - centroid) ** 2) * magnitudes) / total_mag
        return float(np.sqrt(variance))

    def _compute_jitter(self, signal: np.ndarray) -> float:
        """
        Compute jitter (F0 instability).

        Estimated via zero-crossing interval variance.
        """
        zero_crossings = np.where(np.diff(np.signbit(signal)))[0]
        if len(zero_crossings) < 3:
            return 0.0
        intervals = np.diff(zero_crossings)
        return float(np.std(intervals) / np.mean(intervals)) if np.mean(intervals) > 0 else 0.0

    def _compute_shimmer(self, signal: np.ndarray) -> float:
        """
        Compute shimmer (amplitude instability).

        Estimated via envelope variance.
        """
        envelope = np.abs(signal)
        mean_env = np.mean(envelope)
        if mean_env == 0:
            return 0.0
        return float(np.std(envelope) / mean_env)

    def _detect_harmonics(
        self,
        magnitudes: np.ndarray,
        frequencies: np.ndarray,
        fundamental: float,
        max_harmonic: int = 5
    ) -> Tuple[np.ndarray, float]:
        """
        Detect harmonic peaks and compute sideband energy ratio.

        Returns:
            Tuple of (harmonic mask binary vector, sideband energy ratio).
        """
        harmonic_mask = np.zeros(max_harmonic)
        fundamental_energy = 0.0
        sideband_energy = 0.0

        for h in range(1, max_harmonic + 1):
            target_freq = fundamental * h

            # Find peaks near target frequency
            tolerance_hz = FREQ_TOLERANCE
            mask = np.abs(frequencies - target_freq) <= tolerance_hz
            if np.any(mask):
                peak_mag = np.max(magnitudes[mask])
                if peak_mag > 0.1 * np.max(magnitudes):  # Significant peak
                    harmonic_mask[h - 1] = 1
                    fundamental_energy += peak_mag ** 2

            # Check for sidebands (energy in between harmonics)
            if h < max_harmonic:
                sideband_freq = (target_freq + fundamental * (h + 1)) / 2
                sideband_mask = np.abs(frequencies - sideband_freq) <= 10  # Wider tolerance
                if np.any(sideband_mask):
                    sideband_energy += np.sum(magnitudes[sideband_mask] ** 2)

        total_energy = fundamental_energy + sideband_energy
        sideband_ratio = sideband_energy / total_energy if total_energy > 0 else 0.0

        return harmonic_mask, float(sideband_ratio)

    def _compute_phase_coherence(
        self,
        fft_complex: np.ndarray,
        frequencies: np.ndarray,
        fundamental: float,
        max_harmonic: int = 5
    ) -> float:
        """
        Compute phase coherence across harmonics.

        Biological signals have less coherent phase relationships.
        Synthetic signals often have perfectly aligned phases.
        """
        phases = []
        for h in range(1, max_harmonic + 1):
            target_freq = fundamental * h
            idx = np.argmin(np.abs(frequencies - target_freq))
            if np.abs(fft_complex[idx]) > 0:
                phases.append(np.angle(fft_complex[idx]))

        if len(phases) < 2:
            return 1.0  # Perfect coherence (suspicious)

        # Compute phase variance
        phase_diffs = np.diff(phases)
        # Normalize to [-π, π]
        phase_diffs = np.mod(phase_diffs + np.pi, 2 * np.pi) - np.pi
        coherence = 1.0 - np.std(phase_diffs) / np.pi

        return float(np.clip(coherence, 0.0, 1.0))

    def extract(self, signal: np.ndarray) -> AudioFeatures:
        """
        Extract all audio features from signal.

        Args:
            signal: Audio signal (mono).

        Returns:
            AudioFeatures dataclass with all extracted features.
        """
        # Ensure mono
        if signal.ndim > 1:
            signal = np.mean(signal, axis=0)

        # Basic statistics
        rms = self._compute_rms(signal)
        max_val = np.max(np.abs(signal))
        dynamic_range = 20 * np.log10(max_val / rms) if rms > 0 else 0.0

        # FFT
        fft_complex = np.fft.rfft(signal)
        magnitudes = np.abs(fft_complex)
        frequencies = np.fft.rfftfreq(len(signal), 1 / self.sample_rate)

        # Spectral features
        spectral_centroid = self._compute_spectral_centroid(magnitudes, frequencies)
        spectral_flatness = self._compute_spectral_flatness(magnitudes)
        spectral_rolloff = self._compute_spectral_rolloff(magnitudes, frequencies)
        spectral_bandwidth = self._compute_spectral_bandwidth(magnitudes, frequencies, spectral_centroid)

        # MFCC
        mfcc = self._compute_mfcc(signal)

        # Temporal features
        zero_crossing_rate = self._compute_zero_crossing_rate(signal)

        # Voice quality features
        jitter = self._compute_jitter(signal)
        shimmer = self._compute_shimmer(signal)

        # Harmonic analysis
        # Estimate fundamental frequency (simple peak detection)
        peak_idx = np.argmax(magnitudes[1:]) + 1  # Skip DC
        fundamental = frequencies[peak_idx]

        harmonic_mask, sideband_ratio = self._detect_harmonics(
            magnitudes, frequencies, fundamental
        )
        phase_coherence = self._compute_phase_coherence(
            fft_complex, frequencies, fundamental
        )

        return AudioFeatures(
            rms=rms,
            spectral_centroid=spectral_centroid,
            spectral_flatness=spectral_flatness,
            mfcc=mfcc,
            harmonic_mask=harmonic_mask,
            dynamic_range=dynamic_range,
            pan_spread=0.0,  # Computed separately for stereo
            zero_crossing_rate=zero_crossing_rate,
            spectral_rolloff=spectral_rolloff,
            spectral_bandwidth=spectral_bandwidth,
            jitter=jitter,
            shimmer=shimmer,
            sideband_energy_ratio=sideband_ratio,
            phase_coherence=phase_coherence
        )

    def extract_stereo(self, stereo_signal: np.ndarray) -> AudioFeatures:
        """
        Extract features from stereo signal.

        Args:
            stereo_signal: Stereo audio (shape: 2, N).

        Returns:
            AudioFeatures with pan_spread computed.
        """
        if stereo_signal.ndim == 1:
            return self.extract(stereo_signal)

        left = stereo_signal[0]
        right = stereo_signal[1]

        # Extract mono features from sum
        mono = (left + right) / 2
        features = self.extract(mono)

        # Compute pan spread (stereo width)
        # Using instantaneous pan angle variance
        with np.errstate(divide='ignore', invalid='ignore'):
            pan_angle = np.arctan2(right, left)
            pan_angle = np.nan_to_num(pan_angle, nan=0.0)
            features.pan_spread = float(np.std(pan_angle))

        return features


# =============================================================================
# HARMONIC VERIFIER
# =============================================================================

class VerificationResult(Enum):
    """Verification outcome."""
    PASS = "pass"
    FAIL_REPLAY = "fail_replay"
    FAIL_SYNTHETIC = "fail_synthetic"
    FAIL_MODALITY = "fail_modality"
    FAIL_TAMPERED = "fail_tampered"
    FAIL_UNKNOWN = "fail_unknown"


@dataclass
class VerificationReport:
    """Detailed verification report."""
    result: VerificationResult
    confidence: float  # 0.0 to 1.0
    harmonic_match: bool
    sideband_check: bool
    phase_check: bool
    jitter_check: bool
    message: str
    details: Dict


class HarmonicVerifier:
    """
    FFT-based harmonic verification.

    Verifies that the audio payload matches the declared modality by checking:
    1. Fundamental frequency peaks at expected locations (f₀ + id·Δf)
    2. Overtone set matches the modality mask M(M)
    3. Sideband energy indicates biological (not synthetic) origin
    4. Phase coherence is within expected range
    """

    def __init__(
        self,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        base_freq: float = BASE_FREQ,
        freq_step: float = FREQ_STEP,
        freq_tolerance: float = FREQ_TOLERANCE,
        amp_tolerance: float = AMP_TOLERANCE
    ):
        """
        Initialize harmonic verifier.

        Args:
            sample_rate: Sample rate F_s.
            base_freq: Base frequency f₀.
            freq_step: Frequency step Δf.
            freq_tolerance: Frequency tolerance ε_f.
            amp_tolerance: Amplitude tolerance ε_a.
        """
        self.sample_rate = sample_rate
        self.base_freq = base_freq
        self.freq_step = freq_step
        self.freq_tolerance = freq_tolerance
        self.amp_tolerance = amp_tolerance

        self._modality_masks = {
            "STRICT": {1, 3, 5},
            "ADAPTIVE": {1, 2, 3, 4, 5},
            "PROBE": {1},
        }

    def _find_peaks(
        self,
        magnitudes: np.ndarray,
        frequencies: np.ndarray,
        threshold_ratio: float = 0.2
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Find significant peaks in spectrum.

        Args:
            magnitudes: FFT magnitude spectrum.
            frequencies: Corresponding frequencies.
            threshold_ratio: Minimum amplitude relative to max peak.

        Returns:
            Tuple of (peak frequencies, peak magnitudes).
        """
        threshold = threshold_ratio * np.max(magnitudes)
        peak_mask = magnitudes > threshold

        # Simple local maxima detection
        local_max = np.zeros_like(magnitudes, dtype=bool)
        for i in range(1, len(magnitudes) - 1):
            if magnitudes[i] > magnitudes[i-1] and magnitudes[i] > magnitudes[i+1]:
                local_max[i] = True

        combined_mask = peak_mask & local_max

        return frequencies[combined_mask], magnitudes[combined_mask]

    def verify_fundamentals(
        self,
        peak_freqs: np.ndarray,
        expected_ids: np.ndarray
    ) -> Tuple[bool, List[int]]:
        """
        Verify that expected fundamental frequencies are present.

        Args:
            peak_freqs: Detected peak frequencies.
            expected_ids: Expected token IDs.

        Returns:
            Tuple of (all present, list of missing ID indices).
        """
        missing = []
        for idx, token_id in enumerate(expected_ids):
            expected_freq = self.base_freq + int(token_id) * self.freq_step
            found = np.any(np.abs(peak_freqs - expected_freq) <= self.freq_tolerance)
            if not found:
                missing.append(idx)

        return len(missing) == 0, missing

    def verify_overtone_mask(
        self,
        peak_freqs: np.ndarray,
        fundamental: float,
        expected_mask: Set[int]
    ) -> Tuple[bool, Set[int], Set[int]]:
        """
        Verify that overtone pattern matches expected modality mask.

        Args:
            peak_freqs: Detected peak frequencies.
            fundamental: Fundamental frequency.
            expected_mask: Expected harmonic indices from M(M).

        Returns:
            Tuple of (match, present harmonics, missing harmonics).
        """
        present = set()
        for h in range(1, 16):  # Check up to 15th harmonic
            target_freq = fundamental * h
            if np.any(np.abs(peak_freqs - target_freq) <= self.freq_tolerance):
                present.add(h)

        # Check if expected harmonics are present
        missing = expected_mask - present

        # For STRICT mode, also check that even harmonics are NOT present
        if expected_mask == {1, 3, 5}:
            unexpected_evens = present & {2, 4, 6, 8}
            if unexpected_evens:
                # Even harmonics present in STRICT mode - suspicious
                return False, present, missing

        return len(missing) == 0, present, missing

    def verify(
        self,
        signal: np.ndarray,
        declared_modality: str,
        expected_ids: Optional[np.ndarray] = None
    ) -> VerificationReport:
        """
        Perform complete harmonic verification.

        Args:
            signal: Audio signal to verify.
            declared_modality: Declared modality ("STRICT", "ADAPTIVE", "PROBE").
            expected_ids: Optional expected token IDs.

        Returns:
            VerificationReport with detailed results.
        """
        details = {}

        # Ensure mono
        if signal.ndim > 1:
            signal = np.mean(signal, axis=0)

        # FFT
        fft_complex = np.fft.rfft(signal)
        magnitudes = np.abs(fft_complex)
        frequencies = np.fft.rfftfreq(len(signal), 1 / self.sample_rate)

        # Find peaks
        peak_freqs, peak_mags = self._find_peaks(magnitudes, frequencies)
        details["num_peaks"] = len(peak_freqs)

        # Get expected mask
        expected_mask = self._modality_masks.get(declared_modality, {1, 2, 3, 4, 5})

        # Estimate fundamental (strongest peak in expected range)
        base_range_mask = (peak_freqs >= self.base_freq - 50) & (peak_freqs <= self.base_freq + 300)
        if not np.any(base_range_mask):
            return VerificationReport(
                result=VerificationResult.FAIL_TAMPERED,
                confidence=0.0,
                harmonic_match=False,
                sideband_check=False,
                phase_check=False,
                jitter_check=False,
                message="No peaks found in expected frequency range",
                details=details
            )

        filtered_peaks = peak_freqs[base_range_mask]
        filtered_mags = peak_mags[base_range_mask]
        fundamental_idx = np.argmax(filtered_mags)
        fundamental = filtered_peaks[fundamental_idx]
        details["fundamental"] = float(fundamental)

        # Verify overtone mask
        mask_ok, present_harmonics, missing_harmonics = self.verify_overtone_mask(
            peak_freqs, fundamental, expected_mask
        )
        details["present_harmonics"] = list(present_harmonics)
        details["missing_harmonics"] = list(missing_harmonics)

        if not mask_ok:
            return VerificationReport(
                result=VerificationResult.FAIL_MODALITY,
                confidence=0.3,
                harmonic_match=False,
                sideband_check=False,
                phase_check=False,
                jitter_check=False,
                message=f"Harmonic mask mismatch for {declared_modality}",
                details=details
            )

        # Check sideband energy (indicates biological origin)
        sideband_energy = 0.0
        fundamental_energy = 0.0
        for h in expected_mask:
            target = fundamental * h
            fund_mask = np.abs(frequencies - target) <= self.freq_tolerance
            if np.any(fund_mask):
                fundamental_energy += np.sum(magnitudes[fund_mask] ** 2)

            # Sidebands between this and next harmonic
            if h + 1 in expected_mask:
                sideband_freq = (fundamental * h + fundamental * (h + 1)) / 2
                sb_mask = (frequencies >= sideband_freq - 10) & (frequencies <= sideband_freq + 10)
                sideband_energy += np.sum(magnitudes[sb_mask] ** 2)

        total = fundamental_energy + sideband_energy
        sideband_ratio = sideband_energy / total if total > 0 else 0.0
        details["sideband_ratio"] = float(sideband_ratio)

        # Biological signals have sideband ratio > 0.01 due to vibrato/jitter
        # Synthetic signals often have ratio < 0.005
        sideband_check = sideband_ratio > 0.005 or declared_modality == "PROBE"

        # Phase coherence check
        phases = []
        for h in expected_mask:
            target = fundamental * h
            idx = np.argmin(np.abs(frequencies - target))
            if magnitudes[idx] > 0:
                phases.append(np.angle(fft_complex[idx]))

        if len(phases) > 1:
            phase_diffs = np.diff(phases)
            phase_std = np.std(np.mod(phase_diffs + np.pi, 2 * np.pi) - np.pi)
            phase_coherence = 1.0 - phase_std / np.pi
            details["phase_coherence"] = float(phase_coherence)
            # Perfect coherence (> 0.95) is suspicious (likely synthetic)
            phase_check = phase_coherence < 0.95
        else:
            phase_check = True
            details["phase_coherence"] = 0.0

        # Jitter check via zero-crossing variance
        zero_crossings = np.where(np.diff(np.signbit(signal)))[0]
        if len(zero_crossings) > 2:
            intervals = np.diff(zero_crossings)
            jitter_ratio = np.std(intervals) / np.mean(intervals) if np.mean(intervals) > 0 else 0
            details["jitter_ratio"] = float(jitter_ratio)
            # Biological signals have jitter > 0.01, synthetic often < 0.005
            jitter_check = jitter_ratio > 0.003
        else:
            jitter_check = True
            details["jitter_ratio"] = 0.0

        # Calculate overall confidence
        checks = [mask_ok, sideband_check, phase_check, jitter_check]
        confidence = sum(checks) / len(checks)

        if not sideband_check or not phase_check:
            return VerificationReport(
                result=VerificationResult.FAIL_SYNTHETIC,
                confidence=confidence,
                harmonic_match=mask_ok,
                sideband_check=sideband_check,
                phase_check=phase_check,
                jitter_check=jitter_check,
                message="Audio appears to be synthetic/replayed",
                details=details
            )

        if not jitter_check:
            return VerificationReport(
                result=VerificationResult.FAIL_REPLAY,
                confidence=confidence,
                harmonic_match=mask_ok,
                sideband_check=sideband_check,
                phase_check=phase_check,
                jitter_check=jitter_check,
                message="Audio lacks expected jitter (possible replay)",
                details=details
            )

        return VerificationReport(
            result=VerificationResult.PASS,
            confidence=confidence,
            harmonic_match=mask_ok,
            sideband_check=sideband_check,
            phase_check=phase_check,
            jitter_check=jitter_check,
            message="Verification successful",
            details=details
        )


# =============================================================================
# NEURAL NETWORK INTENT CLASSIFIER (Section 4.2)
# =============================================================================

class IntentClassifier:
    """
    Neural network classifier for authentication.

    Architecture (from Section 4.2):
        - Input: Feature vector b ∈ ℝ^d (d ≈ 30)
        - Hidden 1: 64 neurons, ReLU activation
        - Hidden 2: 32 neurons, ReLU activation
        - Output: 1 neuron, sigmoid activation (binary classification)

    Loss: Binary cross-entropy
        L = -(y log ŷ + (1-y) log(1-ŷ))

    Classification:
        Positive: Correctly processed audio (legitimate)
        Negative: Tampered/replayed/synthetic audio
    """

    def __init__(
        self,
        input_dim: int = 30,
        hidden_dims: Tuple[int, int] = (64, 32),
        threshold: float = 0.85
    ):
        """
        Initialize classifier.

        Args:
            input_dim: Feature vector dimension d.
            hidden_dims: Hidden layer sizes (H1, H2).
            threshold: Classification threshold τ.
        """
        self.input_dim = input_dim
        self.hidden_dims = hidden_dims
        self.threshold = threshold

        # Initialize weights (Xavier initialization)
        self._init_weights()

    def _init_weights(self) -> None:
        """Initialize network weights using Xavier initialization."""
        np.random.seed(42)  # Reproducibility

        d = self.input_dim
        h1, h2 = self.hidden_dims

        # Layer 1: d -> h1
        self.W1 = np.random.randn(h1, d) * np.sqrt(2.0 / d)
        self.b1 = np.zeros(h1)

        # Layer 2: h1 -> h2
        self.W2 = np.random.randn(h2, h1) * np.sqrt(2.0 / h1)
        self.b2 = np.zeros(h2)

        # Output: h2 -> 1
        self.W3 = np.random.randn(1, h2) * np.sqrt(2.0 / h2)
        self.b3 = np.zeros(1)

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        """ReLU activation."""
        return np.maximum(0, x)

    @staticmethod
    def _sigmoid(x: np.ndarray) -> np.ndarray:
        """Sigmoid activation."""
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))

    def forward(self, x: np.ndarray) -> float:
        """
        Forward pass through network.

        Args:
            x: Input feature vector b.

        Returns:
            Output probability ŷ ∈ [0, 1].
        """
        # Layer 1
        z1 = self.W1 @ x + self.b1
        a1 = self._relu(z1)

        # Layer 2
        z2 = self.W2 @ a1 + self.b2
        a2 = self._relu(z2)

        # Output
        z3 = self.W3 @ a2 + self.b3
        y_hat = self._sigmoid(z3)

        return float(y_hat[0])

    def classify(self, features: AudioFeatures) -> Tuple[bool, float]:
        """
        Classify audio features.

        Args:
            features: Extracted audio features.

        Returns:
            Tuple of (is_authentic, confidence).
        """
        x = features.to_vector()

        # Ensure correct dimension
        if len(x) != self.input_dim:
            # Pad or truncate
            if len(x) < self.input_dim:
                x = np.pad(x, (0, self.input_dim - len(x)))
            else:
                x = x[:self.input_dim]

        # Normalize features
        x = (x - np.mean(x)) / (np.std(x) + 1e-8)

        probability = self.forward(x)
        is_authentic = probability >= self.threshold

        return is_authentic, probability

    def train_step(
        self,
        x: np.ndarray,
        y: int,
        learning_rate: float = 0.01
    ) -> float:
        """
        Single training step with backpropagation.

        Args:
            x: Input feature vector.
            y: Ground truth label (0 or 1).
            learning_rate: Learning rate.

        Returns:
            Loss value.
        """
        # Forward pass (with caching)
        z1 = self.W1 @ x + self.b1
        a1 = self._relu(z1)
        z2 = self.W2 @ a1 + self.b2
        a2 = self._relu(z2)
        z3 = self.W3 @ a2 + self.b3
        y_hat = self._sigmoid(z3)[0]

        # Compute loss
        eps = 1e-8
        loss = -(y * np.log(y_hat + eps) + (1 - y) * np.log(1 - y_hat + eps))

        # Backward pass
        # Output layer
        dz3 = y_hat - y
        dW3 = dz3 * a2.reshape(1, -1)
        db3 = np.array([dz3])

        # Layer 2
        da2 = self.W3.T @ np.array([dz3])
        dz2 = da2.flatten() * (z2 > 0)
        dW2 = np.outer(dz2, a1)
        db2 = dz2

        # Layer 1
        da1 = self.W2.T @ dz2
        dz1 = da1 * (z1 > 0)
        dW1 = np.outer(dz1, x)
        db1 = dz1

        # Update weights
        self.W3 -= learning_rate * dW3
        self.b3 -= learning_rate * db3
        self.W2 -= learning_rate * dW2
        self.b2 -= learning_rate * db2
        self.W1 -= learning_rate * dW1
        self.b1 -= learning_rate * db1

        return float(loss)

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        epochs: int = 100,
        learning_rate: float = 0.01,
        verbose: bool = False
    ) -> List[float]:
        """
        Train the classifier on a dataset.

        Args:
            X: Feature matrix (N x d).
            y: Labels (N,).
            epochs: Number of training epochs.
            learning_rate: Learning rate.
            verbose: Print progress.

        Returns:
            Loss history.
        """
        losses = []

        for epoch in range(epochs):
            epoch_loss = 0.0

            # Shuffle data
            indices = np.random.permutation(len(X))

            for i in indices:
                loss = self.train_step(X[i], y[i], learning_rate)
                epoch_loss += loss

            avg_loss = epoch_loss / len(X)
            losses.append(avg_loss)

            if verbose and (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.4f}")

        return losses

    def save_weights(self, path: str) -> None:
        """Save network weights to file."""
        np.savez(
            path,
            W1=self.W1, b1=self.b1,
            W2=self.W2, b2=self.b2,
            W3=self.W3, b3=self.b3,
            threshold=self.threshold
        )

    def load_weights(self, path: str) -> None:
        """Load network weights from file."""
        data = np.load(path)
        self.W1 = data['W1']
        self.b1 = data['b1']
        self.W2 = data['W2']
        self.b2 = data['b2']
        self.W3 = data['W3']
        self.b3 = data['b3']
        self.threshold = float(data['threshold'])
