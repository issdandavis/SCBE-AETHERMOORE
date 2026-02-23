#!/usr/bin/env python3
"""Audio Spectral Pipeline — Feature Extraction, SFT Generation, and Music DNA.

Part of the SCBE-AETHERMOORE Ouroboros training loop.

Performs three stages on any WAV file:
  1. Spectral Feature Extraction   (mel spectrogram, chromagram, MFCCs, etc.)
  2. SFT Pair Generation           (instruction/response pairs from features)
  3. Music Generation Prep         (chord progression, key/scale, segment DNA)

Usage:
    python scripts/audio_spectral_pipeline.py path/to/file.wav
    python scripts/audio_spectral_pipeline.py                   # uses default WAV
"""

from __future__ import annotations

import argparse
import json
import math
import os
import struct
import sys
import time
import uuid
import wave
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAINING_DATA_DIR = PROJECT_ROOT / "training-data" / "audio"
OUTPUT_PLOTS_DIR = TRAINING_DATA_DIR / "plots"
SFT_OUTPUT = TRAINING_DATA_DIR / "audio_sft_pairs.jsonl"
DEFAULT_WAV = Path(r"C:\Users\issda\OneDrive\Downloads\Static Between Us.wav")

# ---------------------------------------------------------------------------
# Backend detection — prefer librosa; fall back to scipy/numpy
# ---------------------------------------------------------------------------
BACKEND = "none"
try:
    import librosa
    import librosa.display
    import numpy as np

    BACKEND = "librosa"
except ImportError:
    pass

if BACKEND == "none":
    try:
        import numpy as np
        from numpy.fft import rfft, rfftfreq

        # scipy.io.wavfile hangs on Python 3.14 — use stdlib wave + numpy instead
        scipy_wav = None
        scipy_stft = None

        BACKEND = "scipy"  # feature extraction code works with numpy FFT fallback
    except ImportError:
        pass

# matplotlib is optional — we skip plots if unavailable
try:
    import matplotlib

    matplotlib.use("Agg")  # headless
    import matplotlib.pyplot as plt

    HAS_MPL = True
except ImportError:
    HAS_MPL = False


# ===================================================================
# Utility helpers
# ===================================================================

def _ensure_dirs() -> None:
    """Create output directories if they don't exist."""
    TRAINING_DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _uid() -> str:
    return uuid.uuid4().hex[:12]


def _fmt(val: Any, decimals: int = 4) -> Any:
    """Round floats for readable JSON output."""
    if isinstance(val, float):
        return round(val, decimals)
    if isinstance(val, np.floating):
        return round(float(val), decimals)
    if isinstance(val, np.integer):
        return int(val)
    if isinstance(val, np.ndarray):
        return [_fmt(v, decimals) for v in val.tolist()]
    if isinstance(val, (list, tuple)):
        return [_fmt(v, decimals) for v in val]
    return val


# ===================================================================
# Stage 1 — Spectral Feature Extraction
# ===================================================================

class SpectralFeatures:
    """Container holding all extracted features from a WAV file."""

    def __init__(self) -> None:
        # raw signal
        self.sr: int = 0
        self.y: Optional[np.ndarray] = None
        self.duration: float = 0.0
        self.n_samples: int = 0

        # spectral
        self.mel_spectrogram: Optional[np.ndarray] = None
        self.chromagram: Optional[np.ndarray] = None
        self.mfccs: Optional[np.ndarray] = None
        self.spectral_centroid: Optional[np.ndarray] = None
        self.spectral_bandwidth: Optional[np.ndarray] = None
        self.zero_crossing_rate: Optional[np.ndarray] = None

        # rhythm
        self.tempo: float = 0.0
        self.beat_frames: Optional[np.ndarray] = None
        self.beat_times: Optional[np.ndarray] = None

        # music generation prep
        self.chroma_cqt: Optional[np.ndarray] = None
        self.segment_boundaries: Optional[np.ndarray] = None
        self.estimated_key: str = "unknown"
        self.estimated_scale: str = "unknown"
        self.chord_progression: List[str] = []

        # metadata
        self.source_path: str = ""
        self.extraction_time: str = ""


def _load_wav_scipy(path: str) -> Tuple[np.ndarray, int]:
    """Load WAV via scipy (or stdlib wave + numpy as last resort)."""
    try:
        if scipy_wav is None:
            raise ImportError("scipy.io.wavfile unavailable")
        sr, data = scipy_wav.read(path)
    except Exception:
        # stdlib wave fallback
        with wave.open(path, "rb") as wf:
            sr = wf.getframerate()
            n_frames = wf.getnframes()
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            raw = wf.readframes(n_frames)

        fmt_map = {1: "b", 2: "h", 4: "i"}
        fmt_char = fmt_map.get(sampwidth, "h")
        total_samples = n_frames * n_channels
        data = np.array(struct.unpack(f"<{total_samples}{fmt_char}", raw), dtype=np.float64)
        if n_channels > 1:
            data = data.reshape(-1, n_channels)

    # convert to mono float
    if data.ndim > 1:
        data = data.mean(axis=1)
    if data.dtype != np.float64 and data.dtype != np.float32:
        max_val = np.iinfo(data.dtype).max if np.issubdtype(data.dtype, np.integer) else 1.0
        data = data.astype(np.float64) / max_val
    return data.astype(np.float32), sr


def _mel_filterbank(sr: int, n_fft: int, n_mels: int = 128) -> np.ndarray:
    """Build a simple mel filterbank matrix (n_mels x (n_fft//2+1))."""
    def hz_to_mel(hz: float) -> float:
        return 2595.0 * math.log10(1.0 + hz / 700.0)

    def mel_to_hz(mel: float) -> float:
        return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)

    n_freqs = n_fft // 2 + 1
    low_mel = hz_to_mel(0)
    high_mel = hz_to_mel(sr / 2)
    mel_points = np.linspace(low_mel, high_mel, n_mels + 2)
    hz_points = np.array([mel_to_hz(m) for m in mel_points])
    bin_points = np.floor((n_fft + 1) * hz_points / sr).astype(int)

    fb = np.zeros((n_mels, n_freqs))
    for i in range(n_mels):
        left, center, right = bin_points[i], bin_points[i + 1], bin_points[i + 2]
        for j in range(left, center):
            if center != left:
                fb[i, j] = (j - left) / (center - left)
        for j in range(center, right):
            if right != center:
                fb[i, j] = (right - j) / (right - center)
    return fb


def _extract_features_librosa(path: str) -> SpectralFeatures:
    """Full extraction using librosa."""
    feat = SpectralFeatures()
    feat.source_path = path
    feat.extraction_time = _timestamp()

    print("  [librosa] Loading audio...")
    y, sr = librosa.load(path, sr=None, mono=True)
    feat.y, feat.sr = y, sr
    feat.duration = float(len(y)) / sr
    feat.n_samples = len(y)

    print("  [librosa] Mel spectrogram...")
    feat.mel_spectrogram = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)

    print("  [librosa] Chromagram...")
    feat.chromagram = librosa.feature.chroma_stft(y=y, sr=sr)

    print("  [librosa] MFCCs...")
    feat.mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)

    print("  [librosa] Spectral centroid...")
    feat.spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]

    print("  [librosa] Spectral bandwidth...")
    feat.spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]

    print("  [librosa] Zero-crossing rate...")
    feat.zero_crossing_rate = librosa.feature.zero_crossing_rate(y)[0]

    print("  [librosa] Tempo / beats...")
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    # librosa >= 0.10 returns tempo as array
    feat.tempo = float(np.atleast_1d(tempo)[0])
    feat.beat_frames = beat_frames
    feat.beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    # Music prep: CQT chroma, segments, key
    print("  [librosa] CQT chroma (chord estimation)...")
    feat.chroma_cqt = librosa.feature.chroma_cqt(y=y, sr=sr)

    print("  [librosa] Segment boundaries...")
    try:
        feat.segment_boundaries = librosa.onset.onset_detect(y=y, sr=sr, units="time")
    except Exception:
        feat.segment_boundaries = np.array([])

    # Key estimation from chroma
    _estimate_key(feat)

    # Chord progression estimation
    _estimate_chords(feat)

    return feat


def _extract_features_scipy(path: str) -> SpectralFeatures:
    """Fallback extraction using scipy + numpy."""
    feat = SpectralFeatures()
    feat.source_path = path
    feat.extraction_time = _timestamp()

    print("  [scipy] Loading audio...")
    y, sr = _load_wav_scipy(path)
    feat.y, feat.sr = y, sr
    feat.duration = float(len(y)) / sr
    feat.n_samples = len(y)

    n_fft = 2048
    hop = 512

    # STFT (pure numpy — scipy.signal.stft hangs on Python 3.14)
    print("  [numpy] STFT for spectral features...")
    window = np.hanning(n_fft)
    n_frames = 1 + (len(y) - n_fft) // hop
    Zxx = np.zeros((n_fft // 2 + 1, n_frames), dtype=np.complex128)
    for i in range(n_frames):
        frame = y[i * hop : i * hop + n_fft] * window
        Zxx[:, i] = rfft(frame)
    magnitude = np.abs(Zxx)

    # Mel spectrogram
    print("  [scipy] Mel spectrogram (approximate)...")
    mel_fb = _mel_filterbank(sr, n_fft, n_mels=128)
    n_freq_bins = min(mel_fb.shape[1], magnitude.shape[0])
    feat.mel_spectrogram = mel_fb[:, :n_freq_bins] @ magnitude[:n_freq_bins, :]

    # Chromagram (simplified: 12-bin energy from STFT)
    print("  [scipy] Chromagram (approximate)...")
    n_chroma = 12
    freqs = np.linspace(0, sr / 2, magnitude.shape[0])
    chroma = np.zeros((n_chroma, magnitude.shape[1]))
    for i, f in enumerate(freqs):
        if f > 0:
            midi = 69 + 12 * np.log2(f / 440.0)
            chroma_bin = int(round(midi)) % 12
            chroma[chroma_bin] += magnitude[i]
    feat.chromagram = chroma

    # MFCCs (simplified DCT of log-mel, pure numpy)
    print("  [numpy] MFCCs (approximate)...")
    log_mel = np.log1p(feat.mel_spectrogram)
    N = log_mel.shape[0]
    n_mfcc = 20
    # DCT-II via matrix multiply (no scipy dependency)
    k = np.arange(n_mfcc)[:, None]
    n = np.arange(N)[None, :]
    dct_matrix = np.cos(np.pi * k * (2 * n + 1) / (2 * N))
    dct_matrix *= np.sqrt(2.0 / N)
    dct_matrix[0, :] *= 1.0 / np.sqrt(2.0)
    feat.mfccs = dct_matrix @ log_mel

    # Spectral centroid
    print("  [scipy] Spectral centroid...")
    freqs_col = np.linspace(0, sr / 2, magnitude.shape[0])
    mag_sum = magnitude.sum(axis=0)
    mag_sum[mag_sum == 0] = 1e-10
    feat.spectral_centroid = (freqs_col[:, None] * magnitude).sum(axis=0) / mag_sum

    # Spectral bandwidth
    print("  [scipy] Spectral bandwidth...")
    deviation = (freqs_col[:, None] - feat.spectral_centroid[None, :]) ** 2
    feat.spectral_bandwidth = np.sqrt((deviation * magnitude).sum(axis=0) / mag_sum)

    # Zero-crossing rate
    print("  [scipy] Zero-crossing rate...")
    frame_len = n_fft
    n_frames = 1 + (len(y) - frame_len) // hop
    zcr = np.zeros(n_frames)
    for i in range(n_frames):
        start = i * hop
        frame = y[start : start + frame_len]
        zcr[i] = np.sum(np.abs(np.diff(np.sign(frame))) > 0) / (2 * frame_len)
    feat.zero_crossing_rate = zcr

    # Tempo (onset-based estimate)
    print("  [scipy] Tempo estimation (onset-based)...")
    spectral_flux = np.sum(np.diff(magnitude, axis=1) ** 2, axis=0)
    threshold = np.mean(spectral_flux) + 1.5 * np.std(spectral_flux)
    onset_frames = np.where(spectral_flux > threshold)[0]
    if len(onset_frames) > 1:
        onset_times = onset_frames * hop / sr
        intervals = np.diff(onset_times)
        intervals = intervals[(intervals > 0.2) & (intervals < 2.0)]  # 30-300 BPM
        if len(intervals) > 0:
            feat.tempo = 60.0 / np.median(intervals)
        else:
            feat.tempo = 120.0
    else:
        feat.tempo = 120.0
    feat.beat_frames = onset_frames
    feat.beat_times = onset_frames * hop / sr if len(onset_frames) > 0 else np.array([])

    # Segment boundaries
    feat.segment_boundaries = feat.beat_times[:20] if len(feat.beat_times) > 0 else np.array([])

    # CQT chroma alias
    feat.chroma_cqt = feat.chromagram

    # Key / chord estimation
    _estimate_key(feat)
    _estimate_chords(feat)

    return feat


# ---------------------------------------------------------------------------
# Key and chord helpers
# ---------------------------------------------------------------------------

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Krumhansl-Kessler key profiles
_MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def _estimate_key(feat: SpectralFeatures) -> None:
    """Estimate musical key from chromagram using Krumhansl-Kessler profiles."""
    if feat.chromagram is None or feat.chromagram.size == 0:
        feat.estimated_key = "unknown"
        feat.estimated_scale = "unknown"
        return

    chroma_mean = feat.chromagram.mean(axis=1)
    if chroma_mean.sum() == 0:
        feat.estimated_key = "unknown"
        feat.estimated_scale = "unknown"
        return

    chroma_mean = chroma_mean / (chroma_mean.max() + 1e-10)

    best_corr = -2.0
    best_key = 0
    best_mode = "major"

    for shift in range(12):
        rolled = np.roll(chroma_mean, -shift)
        corr_maj = float(np.corrcoef(rolled, _MAJOR_PROFILE)[0, 1])
        corr_min = float(np.corrcoef(rolled, _MINOR_PROFILE)[0, 1])
        if corr_maj > best_corr:
            best_corr = corr_maj
            best_key = shift
            best_mode = "major"
        if corr_min > best_corr:
            best_corr = corr_min
            best_key = shift
            best_mode = "minor"

    feat.estimated_key = _NOTE_NAMES[best_key]
    feat.estimated_scale = best_mode


def _estimate_chords(feat: SpectralFeatures) -> None:
    """Simple chord estimation: dominant triad per chroma segment."""
    chroma = feat.chroma_cqt if feat.chroma_cqt is not None else feat.chromagram
    if chroma is None or chroma.size == 0:
        feat.chord_progression = []
        return

    # major triad intervals: root, +4, +7
    # minor triad intervals: root, +3, +7
    major_template = np.zeros(12)
    major_template[[0, 4, 7]] = 1.0
    minor_template = np.zeros(12)
    minor_template[[0, 3, 7]] = 1.0

    n_frames = chroma.shape[1]
    segment_size = max(1, n_frames // 16)  # up to 16 chord segments
    chords: List[str] = []

    for seg_start in range(0, n_frames, segment_size):
        seg_end = min(seg_start + segment_size, n_frames)
        seg_chroma = chroma[:, seg_start:seg_end].mean(axis=1)
        if seg_chroma.sum() < 1e-10:
            chords.append("N.C.")
            continue

        seg_chroma = seg_chroma / (seg_chroma.max() + 1e-10)

        best_score = -2.0
        best_chord = "C"
        for root in range(12):
            maj_rolled = np.roll(major_template, root)
            min_rolled = np.roll(minor_template, root)
            score_maj = float(np.dot(seg_chroma, maj_rolled))
            score_min = float(np.dot(seg_chroma, min_rolled))
            if score_maj > best_score:
                best_score = score_maj
                best_chord = _NOTE_NAMES[root]
            if score_min > best_score:
                best_score = score_min
                best_chord = _NOTE_NAMES[root] + "m"
        chords.append(best_chord)

    # deduplicate consecutive
    deduped: List[str] = []
    for c in chords:
        if not deduped or deduped[-1] != c:
            deduped.append(c)
    feat.chord_progression = deduped


def extract_features(wav_path: str) -> SpectralFeatures:
    """Top-level dispatcher for feature extraction."""
    if BACKEND == "librosa":
        return _extract_features_librosa(wav_path)
    elif BACKEND == "scipy":
        return _extract_features_scipy(wav_path)
    else:
        raise RuntimeError(
            "Neither librosa nor scipy+numpy are installed. "
            "Install one of them:\n"
            "  pip install librosa numpy matplotlib\n"
            "  pip install scipy numpy matplotlib"
        )


# ===================================================================
# Stage 1b — Visualization (plots)
# ===================================================================

# ===================================================================
# Stage 1.5 — Source Separation (Spectral Masking)
# ===================================================================
# Splits audio into stems: vocals, instruments, percussion.
# Uses harmonic/percussive separation (HPSS) + vocal isolation via
# frequency band masking.  Pure numpy — no external ML models needed.
# For production quality, run Demucs/Spleeter on Colab GPU.
# ===================================================================

@dataclass
class SeparatedStems:
    """Container for separated audio stems and their analyses."""
    vocals: Optional[np.ndarray] = None
    instruments: Optional[np.ndarray] = None
    percussion: Optional[np.ndarray] = None
    sr: int = 0
    # Per-stem spectral features
    vocal_centroid: float = 0.0
    vocal_bandwidth: float = 0.0
    vocal_zcr: float = 0.0
    vocal_energy: float = 0.0
    instrument_centroid: float = 0.0
    instrument_bandwidth: float = 0.0
    instrument_energy: float = 0.0
    percussion_centroid: float = 0.0
    percussion_zcr: float = 0.0
    percussion_energy: float = 0.0
    # Intersection metrics (where stems overlap in 4D space)
    vocal_instrument_coherence: float = 0.0
    vocal_percussion_coherence: float = 0.0
    instrument_percussion_coherence: float = 0.0
    total_energy: float = 0.0


def _hpss_masks(magnitude: np.ndarray, kernel_h: int = 31, kernel_p: int = 31) -> Tuple[np.ndarray, np.ndarray]:
    """Harmonic/Percussive Source Separation via median filtering on the spectrogram.

    Harmonic content is smooth across time (horizontal) and percussive is smooth
    across frequency (vertical).  We build soft masks from the ratio of median-
    filtered spectrograms.
    """
    # Median filter along time axis (harmonic = temporally smooth)
    pad_h = kernel_h // 2
    padded_t = np.pad(magnitude, ((0, 0), (pad_h, pad_h)), mode="reflect")
    harmonic_enhanced = np.zeros_like(magnitude)
    for i in range(magnitude.shape[1]):
        harmonic_enhanced[:, i] = np.median(padded_t[:, i : i + kernel_h], axis=1)

    # Median filter along frequency axis (percussive = spectrally smooth)
    pad_p = kernel_p // 2
    padded_f = np.pad(magnitude, ((pad_p, pad_p), (0, 0)), mode="reflect")
    percussive_enhanced = np.zeros_like(magnitude)
    for i in range(magnitude.shape[0]):
        percussive_enhanced[i, :] = np.median(padded_f[i : i + kernel_p, :], axis=0)

    # Soft masks via Wiener-like ratio
    eps = 1e-10
    total = harmonic_enhanced + percussive_enhanced + eps
    harmonic_mask = harmonic_enhanced / total
    percussive_mask = percussive_enhanced / total

    return harmonic_mask, percussive_mask


def _vocal_mask(sr: int, n_fft: int, n_freq_bins: int) -> np.ndarray:
    """Frequency-band mask isolating typical vocal range (80 Hz - 4000 Hz)."""
    freqs = np.linspace(0, sr / 2, n_freq_bins)
    mask = np.zeros(n_freq_bins)
    # Vocal fundamental + harmonics: 80-4000 Hz with smooth rolloff
    for i, f in enumerate(freqs):
        if 80 <= f <= 4000:
            # Peak sensitivity 200-3000 Hz
            if 200 <= f <= 3000:
                mask[i] = 1.0
            elif f < 200:
                mask[i] = (f - 80) / 120.0  # ramp up
            else:
                mask[i] = 1.0 - (f - 3000) / 1000.0  # ramp down
    return np.clip(mask, 0, 1)


def _istft(Zxx: np.ndarray, hop: int, n_fft: int, n_samples: int) -> np.ndarray:
    """Inverse STFT via overlap-add (Griffin-Lim-style, single pass)."""
    from numpy.fft import irfft
    window = np.hanning(n_fft)
    n_frames = Zxx.shape[1]
    output = np.zeros(n_samples, dtype=np.float64)
    window_sum = np.zeros(n_samples, dtype=np.float64)

    for i in range(n_frames):
        start = i * hop
        end = start + n_fft
        if end > n_samples:
            break
        frame = irfft(Zxx[:, i], n=n_fft) * window
        output[start:end] += frame
        window_sum[start:end] += window ** 2

    # Normalize by window overlap
    window_sum = np.maximum(window_sum, 1e-10)
    output /= window_sum
    return output.astype(np.float32)


def _spectral_stats(y: np.ndarray, sr: int, n_fft: int = 2048, hop: int = 512) -> Dict[str, float]:
    """Quick spectral stats for a mono signal."""
    window = np.hanning(n_fft)
    n_frames = max(1, 1 + (len(y) - n_fft) // hop)
    centroid_sum = 0.0
    bw_sum = 0.0
    zcr_sum = 0.0

    freqs = np.linspace(0, sr / 2, n_fft // 2 + 1)

    for i in range(min(n_frames, 200)):  # sample up to 200 frames for speed
        start = i * hop
        frame = y[start : start + n_fft]
        if len(frame) < n_fft:
            break
        spectrum = np.abs(rfft(frame * window))
        total = spectrum.sum() + 1e-10

        # Centroid
        c = np.sum(freqs * spectrum) / total
        centroid_sum += c

        # Bandwidth
        bw_sum += np.sqrt(np.sum(((freqs - c) ** 2) * spectrum) / total)

        # ZCR
        zcr_sum += np.sum(np.abs(np.diff(np.sign(frame))) > 0) / (2 * len(frame))

    n = min(n_frames, 200)
    energy = float(np.sum(y ** 2))

    return {
        "centroid": centroid_sum / max(n, 1),
        "bandwidth": bw_sum / max(n, 1),
        "zcr": zcr_sum / max(n, 1),
        "energy": energy,
    }


def _coherence(a: np.ndarray, b: np.ndarray) -> float:
    """Cross-correlation coherence between two signals (0=uncorrelated, 1=identical)."""
    min_len = min(len(a), len(b))
    if min_len == 0:
        return 0.0
    a_seg = a[:min_len].astype(np.float64)
    b_seg = b[:min_len].astype(np.float64)
    norm = np.sqrt(np.sum(a_seg ** 2) * np.sum(b_seg ** 2))
    if norm < 1e-10:
        return 0.0
    return float(np.abs(np.sum(a_seg * b_seg)) / norm)


def separate_sources(feat: SpectralFeatures) -> SeparatedStems:
    """Separate audio into vocals, instruments, and percussion stems.

    Uses harmonic/percussive source separation (HPSS) via median filtering,
    then isolates vocals from the harmonic component using frequency-band masking.
    Analyzes each stem and measures inter-stem coherence (intersection in 4D space).
    """
    y = feat.y
    sr = feat.sr
    n_fft = 2048
    hop = 512

    print("  [HPSS] Computing STFT...")
    window = np.hanning(n_fft)
    n_frames = 1 + (len(y) - n_fft) // hop
    Zxx = np.zeros((n_fft // 2 + 1, n_frames), dtype=np.complex128)
    for i in range(n_frames):
        frame = y[i * hop : i * hop + n_fft] * window
        Zxx[:, i] = rfft(frame)

    magnitude = np.abs(Zxx)
    phase = np.angle(Zxx)

    # Step 1: Harmonic/Percussive split
    print("  [HPSS] Median filtering for harmonic/percussive masks...")
    h_mask, p_mask = _hpss_masks(magnitude, kernel_h=17, kernel_p=17)

    harmonic_spec = magnitude * h_mask * np.exp(1j * phase)
    percussive_spec = magnitude * p_mask * np.exp(1j * phase)

    # Step 2: Split harmonic into vocals + instruments via frequency masking
    print("  [HPSS] Isolating vocals from harmonic component...")
    v_mask = _vocal_mask(sr, n_fft, magnitude.shape[0])
    v_mask_2d = v_mask[:, np.newaxis]  # broadcast across time

    vocal_spec = harmonic_spec * v_mask_2d
    instrument_spec = harmonic_spec * (1 - v_mask_2d)

    # Step 3: Reconstruct time-domain stems
    print("  [HPSS] Reconstructing stems via iSTFT...")
    n_samples = len(y)
    vocals = _istft(vocal_spec, hop, n_fft, n_samples)
    instruments = _istft(instrument_spec, hop, n_fft, n_samples)
    percussion = _istft(percussive_spec, hop, n_fft, n_samples)

    stems = SeparatedStems(
        vocals=vocals,
        instruments=instruments,
        percussion=percussion,
        sr=sr,
    )

    # Step 4: Analyze each stem in parallel
    print("  [HPSS] Analyzing stems...")
    v_stats = _spectral_stats(vocals, sr)
    i_stats = _spectral_stats(instruments, sr)
    p_stats = _spectral_stats(percussion, sr)

    stems.vocal_centroid = v_stats["centroid"]
    stems.vocal_bandwidth = v_stats["bandwidth"]
    stems.vocal_zcr = v_stats["zcr"]
    stems.vocal_energy = v_stats["energy"]
    stems.instrument_centroid = i_stats["centroid"]
    stems.instrument_bandwidth = i_stats["bandwidth"]
    stems.instrument_energy = i_stats["energy"]
    stems.percussion_centroid = p_stats["centroid"]
    stems.percussion_zcr = p_stats["zcr"]
    stems.percussion_energy = p_stats["energy"]
    stems.total_energy = v_stats["energy"] + i_stats["energy"] + p_stats["energy"]

    # Step 5: Measure intersections (coherence in 4D time-freq-amp-phase space)
    print("  [HPSS] Measuring inter-stem coherence (4D intersections)...")
    stems.vocal_instrument_coherence = _coherence(vocals, instruments)
    stems.vocal_percussion_coherence = _coherence(vocals, percussion)
    stems.instrument_percussion_coherence = _coherence(instruments, percussion)

    return stems


def save_stems_wav(stems: SeparatedStems, wav_name: str) -> List[str]:
    """Save separated stems as individual WAV files."""
    import wave as wave_mod

    prefix = wav_name.replace(" ", "_")
    stems_dir = TRAINING_DATA_DIR / "stems"
    stems_dir.mkdir(parents=True, exist_ok=True)
    saved = []

    for name, data in [("vocals", stems.vocals), ("instruments", stems.instruments), ("percussion", stems.percussion)]:
        if data is None:
            continue
        path = str(stems_dir / f"{prefix}_{name}.wav")
        # Convert float32 back to int16
        pcm = np.clip(data * 32767, -32768, 32767).astype(np.int16)
        with wave_mod.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(stems.sr)
            wf.writeframes(pcm.tobytes())
        saved.append(path)

    return saved


def save_separation_plots(stems: SeparatedStems, wav_name: str) -> List[str]:
    """Save source separation visualizations."""
    if not HAS_MPL:
        return []

    prefix = wav_name.replace(" ", "_").replace(".", "_")
    saved = []
    n_fft = 2048
    hop = 512

    # --- Plot 1: Three-stem waveform comparison ---
    fig, axes = plt.subplots(3, 1, figsize=(14, 8), sharex=True)
    for ax, (label, data, color) in zip(axes, [
        ("Vocals", stems.vocals, "#e74c3c"),
        ("Instruments", stems.instruments, "#3498db"),
        ("Percussion", stems.percussion, "#2ecc71"),
    ]):
        if data is not None:
            t = np.linspace(0, len(data) / stems.sr, len(data))
            ax.plot(t, data, color=color, linewidth=0.3, alpha=0.8)
        ax.set_ylabel(label)
        ax.set_xlim(0, len(stems.vocals) / stems.sr if stems.vocals is not None else 1)
    axes[-1].set_xlabel("Time (s)")
    fig.suptitle(f"Source Separation — {wav_name}", fontsize=14)
    fig.tight_layout()
    p = str(OUTPUT_PLOTS_DIR / f"{prefix}_stems_waveform.png")
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    saved.append(p)

    # --- Plot 2: Stem spectrograms side by side ---
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    window = np.hanning(n_fft)
    for ax, (label, data, cmap) in zip(axes, [
        ("Vocals", stems.vocals, "Reds"),
        ("Instruments", stems.instruments, "Blues"),
        ("Percussion", stems.percussion, "Greens"),
    ]):
        if data is not None:
            n_frames = min(500, 1 + (len(data) - n_fft) // hop)  # cap for speed
            spec = np.zeros((n_fft // 2 + 1, n_frames))
            for i in range(n_frames):
                frame = data[i * hop : i * hop + n_fft]
                if len(frame) < n_fft:
                    break
                spec[:, i] = np.abs(rfft(frame * window))
            spec_db = 10 * np.log10(spec + 1e-10)
            ax.imshow(spec_db, aspect="auto", origin="lower", cmap=cmap,
                      extent=[0, n_frames * hop / stems.sr, 0, stems.sr / 2])
        ax.set_ylabel(f"{label}\n(Hz)")
    axes[-1].set_xlabel("Time (s)")
    fig.suptitle(f"Stem Spectrograms — {wav_name}", fontsize=14)
    fig.tight_layout()
    p = str(OUTPUT_PLOTS_DIR / f"{prefix}_stems_spectrograms.png")
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    saved.append(p)

    # --- Plot 3: Energy intersection diagram ---
    fig, ax = plt.subplots(figsize=(8, 8))
    total = stems.total_energy + 1e-10
    v_pct = stems.vocal_energy / total * 100
    i_pct = stems.instrument_energy / total * 100
    p_pct = stems.percussion_energy / total * 100

    # Venn-like circles
    from matplotlib.patches import Circle
    c1 = Circle((-0.3, 0.3), 0.6, alpha=0.3, color="#e74c3c", label=f"Vocals ({v_pct:.1f}%)")
    c2 = Circle((0.3, 0.3), 0.6, alpha=0.3, color="#3498db", label=f"Instruments ({i_pct:.1f}%)")
    c3 = Circle((0.0, -0.3), 0.6, alpha=0.3, color="#2ecc71", label=f"Percussion ({p_pct:.1f}%)")
    for c in [c1, c2, c3]:
        ax.add_patch(c)

    # Coherence labels at intersections
    ax.text(0.0, 0.55, f"V-I: {stems.vocal_instrument_coherence:.3f}", ha="center", fontsize=10, fontweight="bold")
    ax.text(-0.2, -0.1, f"V-P: {stems.vocal_percussion_coherence:.3f}", ha="center", fontsize=10, fontweight="bold")
    ax.text(0.2, -0.1, f"I-P: {stems.instrument_percussion_coherence:.3f}", ha="center", fontsize=10, fontweight="bold")

    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)
    ax.set_aspect("equal")
    ax.legend(loc="upper left", fontsize=11)
    ax.set_title(f"Stem Energy & Coherence — {wav_name}", fontsize=14)
    ax.axis("off")
    p = str(OUTPUT_PLOTS_DIR / f"{prefix}_stems_intersection.png")
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    saved.append(p)

    return saved


def print_separation_summary(stems: SeparatedStems, wav_name: str) -> None:
    """Print stem analysis summary."""
    total = stems.total_energy + 1e-10
    print(f"\n{'=' * 70}")
    print(f"  SOURCE SEPARATION SUMMARY -- {wav_name}")
    print(f"{'=' * 70}")
    print(f"  {'Stem':<15} {'Centroid (Hz)':<16} {'Bandwidth (Hz)':<16} {'ZCR':<10} {'Energy %':<10}")
    print(f"  {'-'*67}")
    print(f"  {'Vocals':<15} {stems.vocal_centroid:<16.1f} {stems.vocal_bandwidth:<16.1f} {stems.vocal_zcr:<10.4f} {stems.vocal_energy/total*100:<10.1f}")
    print(f"  {'Instruments':<15} {stems.instrument_centroid:<16.1f} {stems.instrument_bandwidth:<16.1f} {'--':<10} {stems.instrument_energy/total*100:<10.1f}")
    print(f"  {'Percussion':<15} {stems.percussion_centroid:<16.1f} {'--':<16} {stems.percussion_zcr:<10.4f} {stems.percussion_energy/total*100:<10.1f}")
    print(f"\n  4D Intersections (cross-correlation coherence):")
    print(f"    Vocal x Instrument:  {stems.vocal_instrument_coherence:.4f}")
    print(f"    Vocal x Percussion:  {stems.vocal_percussion_coherence:.4f}")
    print(f"    Instrument x Perc:   {stems.instrument_percussion_coherence:.4f}")
    print(f"{'=' * 70}\n")


def save_plots(feat: SpectralFeatures, wav_name: str) -> List[str]:
    """Save spectral feature visualizations as PNGs. Returns list of paths."""
    if not HAS_MPL:
        print("  [SKIP] matplotlib not available — skipping plots.")
        return []

    saved: List[str] = []
    prefix = wav_name.replace(" ", "_").replace(".", "_")

    # 1. Mel spectrogram
    fig, ax = plt.subplots(figsize=(12, 4))
    mel_db = 10 * np.log10(feat.mel_spectrogram + 1e-10)
    im = ax.imshow(mel_db, aspect="auto", origin="lower", cmap="magma")
    ax.set_title(f"Mel Spectrogram — {wav_name}")
    ax.set_xlabel("Frame")
    ax.set_ylabel("Mel Bin")
    fig.colorbar(im, ax=ax, label="dB")
    p = str(OUTPUT_PLOTS_DIR / f"{prefix}_mel_spectrogram.png")
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    saved.append(p)

    # 2. Chromagram
    fig, ax = plt.subplots(figsize=(12, 3))
    ax.imshow(feat.chromagram, aspect="auto", origin="lower", cmap="coolwarm")
    ax.set_yticks(range(12))
    ax.set_yticklabels(_NOTE_NAMES)
    ax.set_title(f"Chromagram — {wav_name}")
    ax.set_xlabel("Frame")
    fig.savefig(str(OUTPUT_PLOTS_DIR / f"{prefix}_chromagram.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    saved.append(str(OUTPUT_PLOTS_DIR / f"{prefix}_chromagram.png"))

    # 3. MFCCs
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.imshow(feat.mfccs, aspect="auto", origin="lower", cmap="viridis")
    ax.set_title(f"MFCCs (20 coefficients) — {wav_name}")
    ax.set_xlabel("Frame")
    ax.set_ylabel("MFCC #")
    fig.savefig(str(OUTPUT_PLOTS_DIR / f"{prefix}_mfccs.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    saved.append(str(OUTPUT_PLOTS_DIR / f"{prefix}_mfccs.png"))

    # 4. Spectral centroid + bandwidth overlay
    fig, ax = plt.subplots(figsize=(12, 4))
    frames = np.arange(len(feat.spectral_centroid))
    ax.plot(frames, feat.spectral_centroid, label="Centroid (Hz)", color="#e74c3c", linewidth=0.8)
    ax.fill_between(
        frames,
        feat.spectral_centroid - feat.spectral_bandwidth,
        feat.spectral_centroid + feat.spectral_bandwidth,
        alpha=0.2,
        color="#3498db",
        label="Bandwidth",
    )
    ax.set_title(f"Spectral Centroid & Bandwidth — {wav_name}")
    ax.set_xlabel("Frame")
    ax.set_ylabel("Hz")
    ax.legend()
    fig.savefig(str(OUTPUT_PLOTS_DIR / f"{prefix}_centroid_bandwidth.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    saved.append(str(OUTPUT_PLOTS_DIR / f"{prefix}_centroid_bandwidth.png"))

    # 5. Zero-crossing rate
    fig, ax = plt.subplots(figsize=(12, 3))
    ax.plot(feat.zero_crossing_rate, color="#2ecc71", linewidth=0.8)
    ax.set_title(f"Zero-Crossing Rate — {wav_name}")
    ax.set_xlabel("Frame")
    ax.set_ylabel("ZCR")
    fig.savefig(str(OUTPUT_PLOTS_DIR / f"{prefix}_zcr.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    saved.append(str(OUTPUT_PLOTS_DIR / f"{prefix}_zcr.png"))

    # 6. Waveform + beat markers
    fig, ax = plt.subplots(figsize=(12, 3))
    time_axis = np.linspace(0, feat.duration, feat.n_samples)
    ax.plot(time_axis, feat.y, color="#7f8c8d", linewidth=0.3, alpha=0.7)
    if feat.beat_times is not None and len(feat.beat_times) > 0:
        for bt in feat.beat_times:
            ax.axvline(x=bt, color="#e74c3c", alpha=0.4, linewidth=0.5)
    ax.set_title(f"Waveform & Beat Markers — {wav_name}")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    fig.savefig(str(OUTPUT_PLOTS_DIR / f"{prefix}_waveform_beats.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    saved.append(str(OUTPUT_PLOTS_DIR / f"{prefix}_waveform_beats.png"))

    return saved


def print_feature_summary(feat: SpectralFeatures) -> None:
    """Print a human-readable summary of extracted features."""
    print("\n" + "=" * 70)
    print("  SPECTRAL FEATURE SUMMARY")
    print("=" * 70)
    print(f"  Source:            {feat.source_path}")
    print(f"  Sample rate:       {feat.sr} Hz")
    print(f"  Duration:          {feat.duration:.2f} s ({feat.duration / 60:.1f} min)")
    print(f"  Samples:           {feat.n_samples:,}")
    print(f"  Mel spectrogram:   {feat.mel_spectrogram.shape}")
    print(f"  Chromagram:        {feat.chromagram.shape}")
    print(f"  MFCCs:             {feat.mfccs.shape}")
    print(f"  Spectral centroid: mean={np.mean(feat.spectral_centroid):.1f} Hz, "
          f"std={np.std(feat.spectral_centroid):.1f} Hz")
    print(f"  Spectral bw:       mean={np.mean(feat.spectral_bandwidth):.1f} Hz, "
          f"std={np.std(feat.spectral_bandwidth):.1f} Hz")
    print(f"  ZCR:               mean={np.mean(feat.zero_crossing_rate):.4f}, "
          f"max={np.max(feat.zero_crossing_rate):.4f}")
    print(f"  Tempo:             {feat.tempo:.1f} BPM")
    n_beats = len(feat.beat_times) if feat.beat_times is not None else 0
    print(f"  Beats detected:    {n_beats}")
    print(f"  Estimated key:     {feat.estimated_key} {feat.estimated_scale}")
    print(f"  Chord progression: {' -> '.join(feat.chord_progression[:12])}"
          f"{'...' if len(feat.chord_progression) > 12 else ''}")
    print("=" * 70 + "\n")


# ===================================================================
# Stage 2 — SFT Pair Generation
# ===================================================================

def _classify_energy(centroid_mean: float, bandwidth_mean: float, zcr_mean: float, tempo: float) -> str:
    """Heuristic mood/energy classification from spectral features."""
    energy_score = 0
    if centroid_mean > 3000:
        energy_score += 2
    elif centroid_mean > 1500:
        energy_score += 1

    if bandwidth_mean > 3000:
        energy_score += 1

    if zcr_mean > 0.1:
        energy_score += 1

    if tempo > 140:
        energy_score += 2
    elif tempo > 100:
        energy_score += 1

    if energy_score >= 5:
        return "very high energy / aggressive"
    elif energy_score >= 3:
        return "high energy / upbeat"
    elif energy_score >= 2:
        return "moderate energy / balanced"
    elif energy_score >= 1:
        return "low energy / calm"
    else:
        return "very low energy / ambient / meditative"


def _dominant_frequency_bands(mel_spec: np.ndarray) -> Dict[str, float]:
    """Estimate relative energy in frequency bands from mel spectrogram."""
    n_mels = mel_spec.shape[0]
    total = mel_spec.sum() + 1e-10

    # Approximate band boundaries in mel bins (128 mel bins)
    bands = {
        "sub_bass_20_60Hz": (0, max(1, n_mels // 16)),
        "bass_60_250Hz": (max(1, n_mels // 16), max(2, n_mels // 6)),
        "low_mid_250_500Hz": (max(2, n_mels // 6), max(3, n_mels // 4)),
        "mid_500_2000Hz": (max(3, n_mels // 4), max(4, n_mels // 2)),
        "upper_mid_2000_4000Hz": (max(4, n_mels // 2), max(5, 3 * n_mels // 4)),
        "presence_4000_6000Hz": (max(5, 3 * n_mels // 4), max(6, 7 * n_mels // 8)),
        "brilliance_6000Hz_plus": (max(6, 7 * n_mels // 8), n_mels),
    }
    result = {}
    for name, (lo, hi) in bands.items():
        band_energy = float(mel_spec[lo:hi, :].sum())
        result[name] = round(band_energy / total * 100, 2)
    return result


def generate_sft_pairs(feat: SpectralFeatures) -> List[Dict[str, Any]]:
    """Generate SFT instruction/response pairs from extracted features."""
    pairs: List[Dict[str, Any]] = []
    wav_name = Path(feat.source_path).stem
    run_id = _uid()

    centroid_mean = float(np.mean(feat.spectral_centroid))
    centroid_std = float(np.std(feat.spectral_centroid))
    bw_mean = float(np.mean(feat.spectral_bandwidth))
    bw_std = float(np.std(feat.spectral_bandwidth))
    zcr_mean = float(np.mean(feat.zero_crossing_rate))
    zcr_max = float(np.max(feat.zero_crossing_rate))
    n_beats = len(feat.beat_times) if feat.beat_times is not None else 0
    mfcc_means = _fmt(feat.mfccs.mean(axis=1))
    bands = _dominant_frequency_bands(feat.mel_spectrogram)
    energy_label = _classify_energy(centroid_mean, bw_mean, zcr_mean, feat.tempo)

    meta = {
        "source": f"audio_spectral_pipeline/{wav_name}",
        "run_id": run_id,
        "backend": BACKEND,
        "version": "1.0.0",
        "author": "SCBE-AETHERMOORE",
    }

    # --- Pair 1: Spectral characteristics ---
    pairs.append({
        "instruction": (
            f"Describe the spectral characteristics of the audio file '{wav_name}'."
        ),
        "response": (
            f"The audio '{wav_name}' has a duration of {feat.duration:.2f} seconds "
            f"sampled at {feat.sr} Hz ({feat.n_samples:,} samples). "
            f"The spectral centroid averages {centroid_mean:.1f} Hz (std {centroid_std:.1f} Hz), "
            f"indicating the center of spectral mass sits in the "
            f"{'treble' if centroid_mean > 3000 else 'midrange' if centroid_mean > 1000 else 'bass'} region. "
            f"Spectral bandwidth averages {bw_mean:.1f} Hz (std {bw_std:.1f} Hz), "
            f"suggesting {'wide, rich harmonic spread' if bw_mean > 3000 else 'moderate harmonic complexity' if bw_mean > 1500 else 'narrow, focused tonal character'}. "
            f"The zero-crossing rate averages {zcr_mean:.4f} (max {zcr_max:.4f}), "
            f"{'characteristic of noisy or percussive content' if zcr_mean > 0.1 else 'consistent with tonal/melodic content'}. "
            f"The mel spectrogram has shape {feat.mel_spectrogram.shape} and "
            f"the MFCC mean vector (20 coefficients) is: {mfcc_means}."
        ),
        "metadata": {**meta, "category": "spectral_description"},
    })

    # --- Pair 2: Tempo and rhythmic structure ---
    beat_interval_desc = ""
    if n_beats > 1:
        intervals = np.diff(feat.beat_times)
        avg_interval = float(np.mean(intervals))
        beat_interval_desc = (
            f"The average inter-beat interval is {avg_interval:.3f} seconds. "
            f"Beat regularity (std of intervals): {float(np.std(intervals)):.3f} s "
            f"({'very regular/metronomic' if np.std(intervals) < 0.05 else 'moderately regular' if np.std(intervals) < 0.15 else 'irregular/rubato'}). "
        )

    pairs.append({
        "instruction": (
            f"What is the tempo and rhythmic structure of '{wav_name}'?"
        ),
        "response": (
            f"The estimated tempo is {feat.tempo:.1f} BPM "
            f"({'fast' if feat.tempo > 140 else 'moderate' if feat.tempo > 90 else 'slow'}). "
            f"{n_beats} beat frames were detected across {feat.duration:.1f} seconds. "
            f"{beat_interval_desc}"
            f"First five beat times (seconds): {_fmt(feat.beat_times[:5]) if n_beats > 0 else 'N/A'}."
        ),
        "metadata": {**meta, "category": "tempo_rhythm"},
    })

    # --- Pair 3: Mood / energy classification ---
    pairs.append({
        "instruction": (
            f"Classify the mood and energy level of the audio '{wav_name}'."
        ),
        "response": (
            f"Based on spectral analysis, '{wav_name}' is classified as: {energy_label}. "
            f"Contributing factors: spectral centroid at {centroid_mean:.0f} Hz "
            f"(higher values correlate with brighter, more energetic sound), "
            f"bandwidth of {bw_mean:.0f} Hz "
            f"(wider bandwidth suggests richer harmonic content), "
            f"zero-crossing rate of {zcr_mean:.4f} "
            f"({'high noisiness/percussion' if zcr_mean > 0.1 else 'smooth tonal quality'}), "
            f"and tempo of {feat.tempo:.0f} BPM. "
            f"The estimated key is {feat.estimated_key} {feat.estimated_scale}, "
            f"which {'typically conveys a brighter, more uplifting character' if feat.estimated_scale == 'major' else 'often suggests a darker, more introspective mood'}."
        ),
        "metadata": {**meta, "category": "mood_energy"},
    })

    # --- Pair 4: Frequency band dominance ---
    sorted_bands = sorted(bands.items(), key=lambda x: x[1], reverse=True)
    top3 = sorted_bands[:3]
    pairs.append({
        "instruction": (
            f"What frequency bands dominate the audio '{wav_name}'?"
        ),
        "response": (
            f"Frequency band energy distribution (from mel spectrogram analysis):\n"
            + "\n".join(f"  - {name}: {pct:.1f}%" for name, pct in sorted_bands)
            + f"\n\nThe top three dominant bands are: "
            + ", ".join(f"{name} ({pct:.1f}%)" for name, pct in top3)
            + ". "
            + (f"The dominance of sub-bass and bass bands suggests heavy low-frequency content."
               if top3[0][0].startswith(("sub_bass", "bass"))
               else f"The dominance of mid/high bands suggests bright, articulate content.")
        ),
        "metadata": {**meta, "category": "frequency_bands"},
    })

    # --- Pair 5: Key and chord progression ---
    pairs.append({
        "instruction": (
            f"What is the estimated key and chord progression of '{wav_name}'?"
        ),
        "response": (
            f"The estimated key is {feat.estimated_key} {feat.estimated_scale}, "
            f"determined via Krumhansl-Kessler key-profile correlation against the chromagram. "
            f"The estimated chord progression (simplified triadic analysis over {len(feat.chord_progression)} segments) is: "
            f"{' -> '.join(feat.chord_progression)}. "
            f"Note: this is a rough estimate from chroma energy; complex harmonies, "
            f"extended chords, and non-Western tunings may not be captured accurately."
        ),
        "metadata": {**meta, "category": "key_chords"},
    })

    # --- Pair 6: MFCC timbral analysis ---
    pairs.append({
        "instruction": (
            f"Analyze the timbral characteristics of '{wav_name}' using MFCCs."
        ),
        "response": (
            f"The 20-coefficient MFCC analysis reveals the following timbral signature:\n"
            f"  MFCC means: {mfcc_means}\n"
            f"  MFCC stds:  {_fmt(feat.mfccs.std(axis=1))}\n"
            f"The first coefficient (MFCC-0 = {mfcc_means[0]}) represents overall spectral energy/loudness. "
            f"MFCC-1 ({mfcc_means[1]}) captures the balance between low and high frequencies — "
            f"{'positive values suggest brighter timbre' if mfcc_means[1] > 0 else 'negative values suggest warmer/darker timbre'}. "
            f"Higher coefficients capture increasingly fine spectral texture details. "
            f"The MFCC matrix has shape {feat.mfccs.shape} "
            f"({feat.mfccs.shape[0]} coefficients x {feat.mfccs.shape[1]} time frames)."
        ),
        "metadata": {**meta, "category": "timbre_mfcc"},
    })

    # --- Pair 7: SCBE governance context ---
    pairs.append({
        "instruction": (
            "How would the SCBE-AETHERMOORE framework govern audio content "
            "based on spectral analysis?"
        ),
        "response": (
            f"In the SCBE-AETHERMOORE 14-layer framework, audio spectral features map to "
            f"governance primitives as follows:\n"
            f"  - Spectral centroid ({centroid_mean:.0f} Hz) maps to the Poincare Ball radial position: "
            f"higher centroids push content toward OUTER trust rings.\n"
            f"  - Zero-crossing rate ({zcr_mean:.4f}) correlates with FSGS state transitions: "
            f"high ZCR may trigger HOLD for review.\n"
            f"  - Tempo ({feat.tempo:.0f} BPM) informs the Harmonic Wall cost function H(d,R): "
            f"faster tempos increase traversal cost at layer boundaries.\n"
            f"  - The estimated key ({feat.estimated_key} {feat.estimated_scale}) maps to "
            f"Sacred Tongue selection: "
            f"{'major keys align with Koraelin (Dopamine/reward)' if feat.estimated_scale == 'major' else 'minor keys align with Umbroth (GABA/inhibition)'}.\n"
            f"  - Chord complexity ({len(feat.chord_progression)} unique chords) informs "
            f"polyhedra zone routing: richer progressions route through Cortex zone Archimedean solids."
        ),
        "metadata": {**meta, "category": "scbe_governance"},
    })

    # --- Pair 8: Audio segment comparison prep ---
    if feat.segment_boundaries is not None and len(feat.segment_boundaries) > 2:
        n_segs = min(len(feat.segment_boundaries), 10)
        seg_times = _fmt(feat.segment_boundaries[:n_segs])
        pairs.append({
            "instruction": (
                f"Identify the structural segments in '{wav_name}'."
            ),
            "response": (
                f"Onset/segment detection identified {len(feat.segment_boundaries)} boundary points. "
                f"First {n_segs} segment boundaries (seconds): {seg_times}. "
                f"These boundaries can be used to split the audio into sections for "
                f"per-segment chroma, MFCC, or energy analysis. "
                f"The average segment length is "
                f"{float(np.mean(np.diff(feat.segment_boundaries[:20]))):.3f} seconds."
            ),
            "metadata": {**meta, "category": "segmentation"},
        })

    return pairs


def save_sft_pairs(pairs: List[Dict[str, Any]]) -> str:
    """Append SFT pairs to the JSONL output file. Returns path."""
    with open(SFT_OUTPUT, "a", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")
    return str(SFT_OUTPUT)


# ===================================================================
# Stage 3 — Music Generation Prep (DNA manifest)
# ===================================================================

def build_music_dna(feat: SpectralFeatures) -> Dict[str, Any]:
    """Build a structured JSON manifest of the audio's 'musical DNA'."""
    bands = _dominant_frequency_bands(feat.mel_spectrogram)
    chroma_profile = _fmt(feat.chromagram.mean(axis=1)) if feat.chromagram is not None else []

    # Per-segment chroma snapshots (up to 8)
    chroma_segments: List[Dict[str, Any]] = []
    if feat.chroma_cqt is not None:
        n_frames = feat.chroma_cqt.shape[1]
        n_segs = min(8, max(1, n_frames // 100))
        seg_size = n_frames // n_segs
        for i in range(n_segs):
            start = i * seg_size
            end = min(start + seg_size, n_frames)
            seg_chroma = feat.chroma_cqt[:, start:end].mean(axis=1)
            chroma_segments.append({
                "segment": i,
                "start_frame": int(start),
                "end_frame": int(end),
                "chroma_profile": _fmt(seg_chroma),
            })

    dna: Dict[str, Any] = {
        "manifest_version": "1.0.0",
        "generated_at": _timestamp(),
        "source_file": feat.source_path,
        "audio_info": {
            "sample_rate": feat.sr,
            "duration_seconds": _fmt(feat.duration),
            "n_samples": feat.n_samples,
        },
        "key_and_scale": {
            "estimated_key": feat.estimated_key,
            "estimated_scale": feat.estimated_scale,
            "chroma_profile": chroma_profile,
            "note_labels": _NOTE_NAMES,
        },
        "tempo_and_rhythm": {
            "bpm": _fmt(feat.tempo),
            "n_beats": int(len(feat.beat_times)) if feat.beat_times is not None else 0,
            "beat_times_first_16": _fmt(feat.beat_times[:16]) if feat.beat_times is not None and len(feat.beat_times) > 0 else [],
            "beat_regularity_std": _fmt(float(np.std(np.diff(feat.beat_times))))
            if feat.beat_times is not None and len(feat.beat_times) > 1
            else None,
        },
        "chord_progression": {
            "chords": feat.chord_progression,
            "n_unique_chords": len(set(feat.chord_progression)),
        },
        "frequency_bands": bands,
        "spectral_summary": {
            "centroid_mean_hz": _fmt(float(np.mean(feat.spectral_centroid))),
            "centroid_std_hz": _fmt(float(np.std(feat.spectral_centroid))),
            "bandwidth_mean_hz": _fmt(float(np.mean(feat.spectral_bandwidth))),
            "bandwidth_std_hz": _fmt(float(np.std(feat.spectral_bandwidth))),
            "zcr_mean": _fmt(float(np.mean(feat.zero_crossing_rate))),
            "zcr_max": _fmt(float(np.max(feat.zero_crossing_rate))),
        },
        "mfcc_summary": {
            "n_coefficients": int(feat.mfccs.shape[0]),
            "n_frames": int(feat.mfccs.shape[1]),
            "means": _fmt(feat.mfccs.mean(axis=1)),
            "stds": _fmt(feat.mfccs.std(axis=1)),
        },
        "segment_boundaries": {
            "n_boundaries": int(len(feat.segment_boundaries))
            if feat.segment_boundaries is not None
            else 0,
            "first_20": _fmt(feat.segment_boundaries[:20])
            if feat.segment_boundaries is not None and len(feat.segment_boundaries) > 0
            else [],
        },
        "chroma_segments": chroma_segments,
        "generation_hints": {
            "suggested_key": feat.estimated_key,
            "suggested_scale": feat.estimated_scale,
            "suggested_tempo_bpm": _fmt(feat.tempo),
            "dominant_band": max(bands, key=bands.get) if bands else "unknown",
            "energy_classification": _classify_energy(
                float(np.mean(feat.spectral_centroid)),
                float(np.mean(feat.spectral_bandwidth)),
                float(np.mean(feat.zero_crossing_rate)),
                feat.tempo,
            ),
        },
    }
    return dna


def save_music_dna(dna: Dict[str, Any], wav_name: str) -> str:
    """Save music DNA manifest as JSON."""
    filename = wav_name.replace(" ", "_").replace(".", "_") + "_music_dna.json"
    path = TRAINING_DATA_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dna, f, indent=2, ensure_ascii=False)
    return str(path)


# ===================================================================
# Main
# ===================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audio Spectral Pipeline: extract features, generate SFT pairs, build music DNA."
    )
    parser.add_argument(
        "wav_path",
        nargs="?",
        default=str(DEFAULT_WAV),
        help=f"Path to WAV file (default: {DEFAULT_WAV})",
    )
    args = parser.parse_args()

    wav_path = args.wav_path
    wav_name = Path(wav_path).stem

    print(f"\n{'=' * 70}")
    print(f"  SCBE Audio Spectral Pipeline")
    print(f"  Backend: {BACKEND}")
    print(f"  Input:   {wav_path}")
    print(f"{'=' * 70}\n")

    if not Path(wav_path).exists():
        print(f"ERROR: WAV file not found: {wav_path}")
        print("  Provide a valid path as argument, or place a WAV at the default location.")
        sys.exit(1)

    if BACKEND == "none":
        print("ERROR: No audio backend available.")
        print("  Install one of:")
        print("    pip install librosa numpy matplotlib")
        print("    pip install scipy numpy matplotlib")
        sys.exit(1)

    _ensure_dirs()
    t0 = time.time()

    # --- Stage 1: Feature Extraction ---
    print("[STAGE 1] Extracting spectral features...")
    feat = extract_features(wav_path)
    print_feature_summary(feat)

    # --- Stage 1b: Plots ---
    print("[STAGE 1b] Generating visualization plots...")
    plot_paths = save_plots(feat, wav_name)
    if plot_paths:
        print(f"  Saved {len(plot_paths)} plots to {OUTPUT_PLOTS_DIR}/")
        for p in plot_paths:
            print(f"    -> {p}")
    print()

    # --- Stage 1.5: Source Separation ---
    print("[STAGE 1.5] Separating sources (vocals / instruments / percussion)...")
    stems = separate_sources(feat)
    print_separation_summary(stems, wav_name)

    print("[STAGE 1.5b] Saving stem WAVs and plots...")
    stem_paths = save_stems_wav(stems, wav_name)
    if stem_paths:
        print(f"  Saved {len(stem_paths)} stem WAVs:")
        for sp in stem_paths:
            print(f"    -> {sp}")
    stem_plots = save_separation_plots(stems, wav_name)
    if stem_plots:
        print(f"  Saved {len(stem_plots)} separation plots:")
        for sp in stem_plots:
            print(f"    -> {sp}")
    print()

    # --- Stage 2: SFT Pair Generation ---
    print("[STAGE 2] Generating SFT pairs...")
    pairs = generate_sft_pairs(feat)
    sft_path = save_sft_pairs(pairs)
    print(f"  Generated {len(pairs)} SFT pairs")
    print(f"  Appended to {sft_path}")
    print()

    # --- Stage 3: Music DNA Manifest ---
    print("[STAGE 3] Building music generation DNA manifest...")
    dna = build_music_dna(feat)
    dna_path = save_music_dna(dna, wav_name)
    print(f"  Saved music DNA to {dna_path}")
    print()

    elapsed = time.time() - t0
    print(f"{'=' * 70}")
    print(f"  Pipeline complete in {elapsed:.2f} seconds")
    print(f"  Output directory: {TRAINING_DATA_DIR}")
    print(f"  SFT pairs:        {sft_path} ({len(pairs)} pairs)")
    print(f"  Music DNA:        {dna_path}")
    if plot_paths:
        print(f"  Plots:            {len(plot_paths)} PNGs in {OUTPUT_PLOTS_DIR}/")
    if stem_paths:
        print(f"  Stems:            {len(stem_paths)} WAVs in {TRAINING_DATA_DIR / 'stems'}/")
    if stem_plots:
        print(f"  Stem plots:       {len(stem_plots)} PNGs in {OUTPUT_PLOTS_DIR}/")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
