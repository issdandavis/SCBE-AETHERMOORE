"""
Spectrogram Bridge — Raw Audio → Gallery Color Field Projection
================================================================

Takes a WAV file (lava, wind, water, earthquake, fire, etc.),
runs FFT via scipy, and projects the frequency bins onto the
GalleryColorField grid from gallery_chromatics.py.

The key insight: a spectrogram IS a color grid of sound.
Frequency on Y, time on X, amplitude as intensity.
Our gallery already maps hue→frequency and chroma→amplitude.
This module closes the loop: real audio → same coordinate space.

Pipeline:
    .wav → scipy.io.wavfile → STFT → magnitude spectrogram
        → frequency bins → hue mapping (log scale)
        → amplitude → chroma mapping
        → time frames → temporal slices
        → tongue affinity scoring (which tongue "owns" each band)

Tongue-frequency bands (from dead tone + acoustic physics):
    DR (grounded)   : 20-150 Hz   — earthquake rumble, sub-bass
    UM (shadow)     : 150-400 Hz  — wind hum, low resonance
    RU (governance) : 400-1000 Hz — water flow, mid authority
    KO (intent)     : 1000-2500 Hz — fire crackle, voice clarity
    AV (wisdom)     : 2500-6000 Hz — bird song, harmonic overtones
    CA (compute)    : 6000-20000 Hz — electrical hiss, high precision

No torch. No librosa. Just numpy + scipy.

@layer Layer 14 (Audio Axis)
@component Spectrogram Bridge
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import fft as sp_fft
from scipy.io import wavfile

# ============================================================================
# Constants
# ============================================================================

PHI = 1.618033988749895

# Tongue → frequency band mapping (Hz)
# Each tongue "owns" a frequency range based on its acoustic character
TONGUE_FREQ_BANDS: Dict[str, Tuple[float, float]] = {
    "dr": (20.0,    150.0),    # earthquake, sub-bass, grounded
    "um": (150.0,   400.0),    # wind hum, low resonance, shadow
    "ru": (400.0,   1000.0),   # water flow, mid authority, governance
    "ko": (1000.0,  2500.0),   # fire crackle, voice clarity, intent
    "av": (2500.0,  6000.0),   # bird song, overtones, wisdom
    "ca": (6000.0,  20000.0),  # electrical hiss, precision, compute
}

# Gallery sonifier frequency range (must match gallery_sonifier.py)
GALLERY_FREQ_MIN = 100.0
GALLERY_FREQ_MAX = 4000.0

# Default STFT parameters
DEFAULT_FFT_SIZE = 2048
DEFAULT_HOP_SIZE = 512
DEFAULT_WINDOW = "hann"

# Tongue order (consistent with all other modules)
TONGUE_ORDER = ("ko", "av", "ru", "ca", "um", "dr")


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class SpectrogramFrame:
    """One time-slice of the spectrogram, projected onto tongue space."""
    time_sec: float
    frequencies: np.ndarray       # frequency bin centers (Hz)
    magnitudes: np.ndarray        # magnitude per bin (linear)
    tongue_energies: Dict[str, float]   # energy per tongue band
    dominant_tongue: str
    total_energy: float
    spectral_centroid: float      # weighted mean frequency (Hz)
    hf_ratio: float               # fraction of energy above 2500 Hz


@dataclass
class SpectrogramAnalysis:
    """Full spectrogram analysis of an audio file."""
    filename: str
    sample_rate: int
    duration_sec: float
    n_frames: int
    fft_size: int
    hop_size: int
    frames: List[SpectrogramFrame]

    # Aggregate tongue profile across entire clip
    tongue_profile: Dict[str, float] = field(default_factory=dict)
    dominant_tongue: str = ""
    mean_centroid: float = 0.0
    mean_hf_ratio: float = 0.0

    @property
    def frame_rate(self) -> float:
        """Frames per second."""
        return self.sample_rate / self.hop_size if self.hop_size > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "sample_rate": self.sample_rate,
            "duration_sec": round(self.duration_sec, 3),
            "n_frames": self.n_frames,
            "fft_size": self.fft_size,
            "tongue_profile": {k: round(v, 4) for k, v in self.tongue_profile.items()},
            "dominant_tongue": self.dominant_tongue,
            "mean_centroid_hz": round(self.mean_centroid, 1),
            "mean_hf_ratio": round(self.mean_hf_ratio, 4),
        }


@dataclass(frozen=True)
class GalleryProjection:
    """One spectrogram frame projected onto gallery color coordinates.

    Maps frequency → hue (0-360), amplitude → chroma, tongue → material band.
    """
    time_sec: float
    hue_degrees: float          # dominant frequency mapped to hue
    chroma: float               # energy mapped to chroma [0, 130]
    lightness: float            # spectral centroid mapped to L* [0, 100]
    tongue: str                 # dominant tongue for this frame
    material: str               # material band from tongue character


# ============================================================================
# Core Functions
# ============================================================================

def load_wav(filepath: str) -> Tuple[int, np.ndarray]:
    """Load a WAV file, return (sample_rate, mono_signal).

    Converts stereo to mono by averaging channels.
    Normalizes to [-1, 1] float range.
    """
    sr, data = wavfile.read(filepath)

    # Convert to float
    if data.dtype == np.int16:
        data = data.astype(np.float64) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float64) / 2147483648.0
    elif data.dtype == np.uint8:
        data = (data.astype(np.float64) - 128.0) / 128.0
    else:
        data = data.astype(np.float64)

    # Stereo → mono
    if data.ndim == 2:
        data = data.mean(axis=1)

    return sr, data


def compute_stft(
    signal: np.ndarray,
    fft_size: int = DEFAULT_FFT_SIZE,
    hop_size: int = DEFAULT_HOP_SIZE,
    window: str = DEFAULT_WINDOW,
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute Short-Time Fourier Transform.

    Returns:
        magnitudes: (n_frames, n_bins) magnitude spectrogram
        frequencies: (n_bins,) frequency bin centers (not Hz — need sample_rate)
    """
    # Build window
    if window == "hann":
        win = np.hanning(fft_size)
    elif window == "hamming":
        win = np.hamming(fft_size)
    else:
        win = np.ones(fft_size)

    # Pad signal
    n_pad = fft_size // 2
    padded = np.pad(signal, (n_pad, n_pad), mode="reflect")

    # Compute frames
    n_frames = 1 + (len(padded) - fft_size) // hop_size
    magnitudes = np.zeros((n_frames, fft_size // 2 + 1))

    for i in range(n_frames):
        start = i * hop_size
        frame = padded[start:start + fft_size] * win
        spectrum = sp_fft.rfft(frame)
        magnitudes[i] = np.abs(spectrum)

    return magnitudes, np.arange(magnitudes.shape[1])


def bin_to_hz(bin_indices: np.ndarray, sample_rate: int, fft_size: int) -> np.ndarray:
    """Convert FFT bin indices to frequency in Hz."""
    return bin_indices * sample_rate / fft_size


def tongue_band_energy(
    magnitudes: np.ndarray,
    frequencies_hz: np.ndarray,
) -> Dict[str, float]:
    """Compute energy in each tongue's frequency band.

    Returns dict of tongue → normalized energy [0, 1].
    """
    total = float(np.sum(magnitudes ** 2)) + 1e-12
    energies = {}

    for tongue, (lo, hi) in TONGUE_FREQ_BANDS.items():
        mask = (frequencies_hz >= lo) & (frequencies_hz < hi)
        band_energy = float(np.sum(magnitudes[mask] ** 2))
        energies[tongue] = band_energy / total

    return energies


def spectral_centroid(magnitudes: np.ndarray, frequencies_hz: np.ndarray) -> float:
    """Weighted mean frequency (spectral center of mass)."""
    total = float(np.sum(magnitudes)) + 1e-12
    return float(np.sum(magnitudes * frequencies_hz)) / total


def hf_ratio(magnitudes: np.ndarray, frequencies_hz: np.ndarray, cutoff: float = 2500.0) -> float:
    """Fraction of energy above cutoff frequency."""
    total = float(np.sum(magnitudes ** 2)) + 1e-12
    hf_mask = frequencies_hz >= cutoff
    hf_energy = float(np.sum(magnitudes[hf_mask] ** 2))
    return hf_energy / total


# ============================================================================
# Analysis Pipeline
# ============================================================================

def analyze_audio(
    filepath: str,
    fft_size: int = DEFAULT_FFT_SIZE,
    hop_size: int = DEFAULT_HOP_SIZE,
) -> SpectrogramAnalysis:
    """Full spectrogram analysis of a WAV file.

    Loads audio, computes STFT, projects each frame onto tongue space,
    and aggregates tongue profile across the entire clip.

    Args:
        filepath: Path to .wav file.
        fft_size: FFT window size (default 2048).
        hop_size: Hop between frames (default 512).

    Returns:
        SpectrogramAnalysis with per-frame and aggregate tongue data.
    """
    sr, signal = load_wav(filepath)
    duration = len(signal) / sr

    mags, bins = compute_stft(signal, fft_size, hop_size)
    freq_hz = bin_to_hz(bins, sr, fft_size)

    frames: List[SpectrogramFrame] = []
    agg_tongue = {t: 0.0 for t in TONGUE_ORDER}

    for i in range(mags.shape[0]):
        frame_mag = mags[i]
        time_sec = i * hop_size / sr

        t_energies = tongue_band_energy(frame_mag, freq_hz)
        dominant = max(t_energies, key=t_energies.get)
        total_e = float(np.sum(frame_mag ** 2))
        centroid = spectral_centroid(frame_mag, freq_hz)
        hfr = hf_ratio(frame_mag, freq_hz)

        frames.append(SpectrogramFrame(
            time_sec=time_sec,
            frequencies=freq_hz,
            magnitudes=frame_mag,
            tongue_energies=t_energies,
            dominant_tongue=dominant,
            total_energy=total_e,
            spectral_centroid=centroid,
            hf_ratio=hfr,
        ))

        for t in TONGUE_ORDER:
            agg_tongue[t] += t_energies[t]

    # Normalize aggregate
    agg_total = sum(agg_tongue.values()) or 1e-12
    tongue_profile = {t: v / agg_total for t, v in agg_tongue.items()}
    dominant_tongue = max(tongue_profile, key=tongue_profile.get)

    mean_centroid = sum(f.spectral_centroid for f in frames) / max(len(frames), 1)
    mean_hfr = sum(f.hf_ratio for f in frames) / max(len(frames), 1)

    analysis = SpectrogramAnalysis(
        filename=filepath,
        sample_rate=sr,
        duration_sec=duration,
        n_frames=len(frames),
        fft_size=fft_size,
        hop_size=hop_size,
        frames=frames,
        tongue_profile=tongue_profile,
        dominant_tongue=dominant_tongue,
        mean_centroid=mean_centroid,
        mean_hf_ratio=mean_hfr,
    )

    return analysis


# ============================================================================
# Gallery Projection
# ============================================================================

# Tongue → material band mapping (consistent with gallery_chromatics.py)
_TONGUE_MATERIAL: Dict[str, str] = {
    "dr": "matte",         # heavy, grounded → dark, low chroma
    "um": "matte",         # shadow → dark
    "ru": "metallic",      # governance → structured, warm
    "ko": "fluorescent",   # intent → bright, green-shifted
    "av": "fluorescent",   # wisdom → bright, airy
    "ca": "neon",          # compute → max chroma, saturated
}


def freq_to_hue(freq_hz: float) -> float:
    """Map frequency (Hz) to hue angle (0-360 degrees).

    Log scale so equal frequency ratios = equal hue distance.
    Inverse of gallery_sonifier.hue_to_frequency().
    """
    freq_hz = max(GALLERY_FREQ_MIN, min(GALLERY_FREQ_MAX, freq_hz))
    log_min = math.log(GALLERY_FREQ_MIN)
    log_max = math.log(GALLERY_FREQ_MAX)
    t = (math.log(freq_hz) - log_min) / (log_max - log_min)
    return t * 360.0


def energy_to_chroma(energy: float, max_energy: float = 1.0) -> float:
    """Map frame energy to CIELAB chroma (0-130).

    Uses sqrt scaling for perceptual linearity.
    """
    t = min(1.0, math.sqrt(energy / max(max_energy, 1e-12)))
    return t * 130.0


def centroid_to_lightness(centroid_hz: float) -> float:
    """Map spectral centroid to CIELAB lightness (0-100).

    Higher centroid (brighter sound) → higher lightness.
    """
    t = freq_to_hue(centroid_hz) / 360.0  # normalized position
    return 20.0 + t * 60.0  # range 20-80


def project_frame_to_gallery(frame: SpectrogramFrame) -> GalleryProjection:
    """Project one spectrogram frame onto gallery color coordinates.

    Maps:
        dominant frequency → hue
        total energy → chroma
        spectral centroid → lightness
        dominant tongue → material band
    """
    hue = freq_to_hue(frame.spectral_centroid)
    chroma = energy_to_chroma(frame.total_energy)
    lightness = centroid_to_lightness(frame.spectral_centroid)
    material = _TONGUE_MATERIAL.get(frame.dominant_tongue, "matte")

    return GalleryProjection(
        time_sec=frame.time_sec,
        hue_degrees=hue,
        chroma=chroma,
        lightness=lightness,
        tongue=frame.dominant_tongue,
        material=material,
    )


def project_analysis_to_gallery(
    analysis: SpectrogramAnalysis,
) -> List[GalleryProjection]:
    """Project all frames of an analysis onto gallery color space.

    Returns one GalleryProjection per frame — a time series of
    color coordinates that can be cross-referenced with the
    GalleryColorField from gallery_chromatics.py.
    """
    return [project_frame_to_gallery(f) for f in analysis.frames]


# ============================================================================
# Synthetic Test Signal Generator (for testing without real WAV files)
# ============================================================================

def generate_test_signal(
    duration_sec: float = 1.0,
    sample_rate: int = 44100,
    frequencies: Optional[List[float]] = None,
    amplitudes: Optional[List[float]] = None,
) -> Tuple[int, np.ndarray]:
    """Generate a synthetic test signal (sum of sinusoids).

    Useful for testing the pipeline without real audio files.

    Args:
        duration_sec: Signal duration.
        sample_rate: Sample rate in Hz.
        frequencies: List of frequencies to sum (default: [440]).
        amplitudes: Amplitude per frequency (default: [1.0]).

    Returns:
        (sample_rate, signal) matching load_wav() output format.
    """
    if frequencies is None:
        frequencies = [440.0]
    if amplitudes is None:
        amplitudes = [1.0] * len(frequencies)

    t = np.arange(int(duration_sec * sample_rate)) / sample_rate
    signal = np.zeros_like(t)

    for freq, amp in zip(frequencies, amplitudes):
        signal += amp * np.sin(2.0 * np.pi * freq * t)

    # Normalize to [-1, 1]
    peak = np.max(np.abs(signal)) or 1.0
    signal = signal / peak

    return sample_rate, signal


# ============================================================================
# Dead Tone Detection in Audio Spectrum
# ============================================================================

# Dead tone target ratios (phi-unreachable intervals)
DEAD_TONE_RATIOS = {
    "perfect_fifth": 3.0 / 2.0,    # 1.500
    "minor_sixth": 8.0 / 5.0,      # 1.600
    "minor_seventh": 16.0 / 9.0,   # 1.778
}


def detect_dead_tones_in_spectrum(
    magnitudes: np.ndarray,
    frequencies_hz: np.ndarray,
    threshold_ratio: float = 0.1,
    tolerance: float = 0.05,
) -> Dict[str, float]:
    """Detect dead tone frequency ratios in one FFT frame.

    Finds prominent spectral peaks and checks all pairwise frequency
    ratios against the three phi-unreachable intervals.

    Args:
        magnitudes: |FFT| values for one frame.
        frequencies_hz: corresponding Hz values.
        threshold_ratio: minimum peak height relative to max.
        tolerance: max allowed ratio error (0.05 = 5%).

    Returns:
        dict of dead tone name → detection strength [0, 1].
    """
    from scipy.signal import find_peaks

    detections = {name: 0.0 for name in DEAD_TONE_RATIOS}
    max_mag = float(np.max(magnitudes)) if len(magnitudes) > 0 else 0.0
    if max_mag < 1e-12:
        return detections

    peak_idx, _ = find_peaks(magnitudes, height=max_mag * threshold_ratio, distance=5)
    if len(peak_idx) < 2:
        return detections

    peak_freqs = frequencies_hz[peak_idx]
    peak_mags = magnitudes[peak_idx]

    # Top 10 peaks by magnitude
    order = np.argsort(peak_mags)[::-1][:10]
    top_freqs = peak_freqs[order]

    for i in range(len(top_freqs)):
        for j in range(i + 1, len(top_freqs)):
            f_hi = max(top_freqs[i], top_freqs[j])
            f_lo = min(top_freqs[i], top_freqs[j])
            if f_lo < 1.0:
                continue
            ratio = f_hi / f_lo

            for name, target in DEAD_TONE_RATIOS.items():
                error = abs(ratio - target)
                if error < tolerance:
                    strength = 1.0 - (error / tolerance)
                    detections[name] = max(detections[name], strength)

    return detections


def detect_dead_tones_aggregate(analysis: SpectrogramAnalysis) -> Dict[str, float]:
    """Detect dead tones across all frames, return max strength per tone."""
    freq_hz = bin_to_hz(np.arange(analysis.fft_size // 2 + 1),
                        analysis.sample_rate, analysis.fft_size)

    agg = {name: 0.0 for name in DEAD_TONE_RATIOS}
    for frame in analysis.frames:
        frame_det = detect_dead_tones_in_spectrum(frame.magnitudes, freq_hz)
        for name in agg:
            agg[name] = max(agg[name], frame_det[name])

    return agg


# ============================================================================
# Cross-Modal Alignment: Audio ↔ Text Color Field
# ============================================================================

def audio_text_alignment(
    audio_analysis: SpectrogramAnalysis,
    text_color_dict: dict,
) -> float:
    """Cosine similarity between audio tongue profile and text color field.

    Takes a SpectrogramAnalysis and a text GalleryColorField.to_dict()
    and measures how closely the audio's tongue distribution matches
    the text's chromatic tongue distribution.

    This is the core metric for audio-visual contrastive learning:
    when alignment is high, the audio and text are in the same
    region of the manifold.

    Returns: cosine similarity [0, 1].
    """
    # Audio vector: tongue profile (already normalized)
    a_vec = [audio_analysis.tongue_profile.get(t, 0.0) for t in TONGUE_ORDER]

    # Text vector: extract from left iris dominant tongue + chroma
    left = text_color_dict.get("left_iris", {})
    chords = left.get("chords", {})
    dom = left.get("dominant_tongue", "dr")
    dom_idx = list(TONGUE_ORDER).index(dom) if dom in TONGUE_ORDER else 5

    # Build text tongue vector from chroma distribution
    t_vec = [0.0] * 6
    for tone_name in ["perfect_fifth", "minor_sixth", "minor_seventh"]:
        chord = chords.get(tone_name, {})
        chroma = chord.get("mean_chroma", 0.0)
        for j in range(6):
            dist = min(abs(j - dom_idx), 6 - abs(j - dom_idx))
            weight = PHI ** (-dist)
            t_vec[j] += chroma * weight

    t_total = sum(t_vec) or 1e-9
    t_vec = [v / t_total for v in t_vec]

    # Cosine similarity
    dot = sum(a * b for a, b in zip(a_vec, t_vec))
    mag_a = math.sqrt(sum(x**2 for x in a_vec)) or 1e-9
    mag_t = math.sqrt(sum(x**2 for x in t_vec)) or 1e-9

    return max(0.0, min(1.0, dot / (mag_a * mag_t)))


# ============================================================================
# Sound Vault Batch Processor
# ============================================================================

def analyze_sound_vault(
    vault_dir: str,
    pattern: str = "*.wav",
) -> List[Dict]:
    """Batch-analyze all WAV files in a physics sound vault directory.

    Processes: lava, wind, water, earthquake, fire, electrical arc,
    rockslide, thunder, rain, birdsong, etc.

    Each file gets:
        - Full spectrogram analysis with tongue profile
        - Gallery color projection timeline
        - Dead tone detection
        - Material classification from spectral shape

    Returns list of summary dicts, one per file.
    """
    from pathlib import Path

    vault = Path(vault_dir)
    wav_files = sorted(vault.glob(pattern))

    results = []
    for wav_path in wav_files:
        try:
            analysis = analyze_audio(str(wav_path))
            projections = project_analysis_to_gallery(analysis)
            dead_tones = detect_dead_tones_aggregate(analysis)

            # Classify material from spectral shape
            mean_hf = analysis.mean_hf_ratio
            if mean_hf > 0.4:
                material = "neon"          # bright, high-frequency dominated
            elif mean_hf > 0.2:
                material = "fluorescent"   # presence-heavy
            elif mean_hf < 0.05:
                material = "matte"         # sub-bass dominated
            else:
                material = "metallic"      # broadband

            results.append({
                "file": wav_path.name,
                "duration_s": round(analysis.duration_sec, 2),
                "sample_rate": analysis.sample_rate,
                "n_frames": analysis.n_frames,
                "tongue_profile": {k: round(v, 4) for k, v in analysis.tongue_profile.items()},
                "dominant_tongue": analysis.dominant_tongue,
                "mean_centroid_hz": round(analysis.mean_centroid, 1),
                "material": material,
                "dead_tones": {k: round(v, 4) for k, v in dead_tones.items()},
                "n_projections": len(projections),
            })
        except Exception as e:
            results.append({"file": wav_path.name, "error": str(e)})

    return results
