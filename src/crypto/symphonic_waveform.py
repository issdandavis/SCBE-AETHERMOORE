"""
Symphonic Waveform Export - Audio Synthesis from Hyperpath Traversals
=====================================================================

"The visual or auditory structure of the data itself becomes a proof of validity."
  - AetherMoore Protocol Blueprint

This module closes the loop between:
  Hyperpath Geodesic → Token Intents → Symphonic Frequencies → .WAV Audio

Features:
- Map Poincaré ball positions to token polarity (light/shadow/balanced)
- Convert positions to signed frequencies (±Hz from 440 base)
- Generate actual waveforms with envelope shaping
- Export to .wav via scipy.io.wavfile (or pure numpy fallback)
- Real-time audio rendering support
- Harmonic fingerprint extraction for octree storage

Integration Points:
- Hyperbolic Octree: Store harmonic fingerprints in voxel nodes
- Hyperpath Finder: Emit waveforms during geodesic traversal
- HYDRA Ledger: Log audio hashes as cryptographic proofs
"""

import sys
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import struct
import os

# Try scipy for .wav export, fallback to pure numpy
try:
    from scipy.io import wavfile
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("[WAVEFORM] scipy not available, using pure numpy wav export", file=sys.stderr)


# =============================================================================
# Constants
# =============================================================================

SAMPLE_RATE = 44100      # CD quality
BASE_FREQ = 440.0        # A4 = 440 Hz
FREQ_STEP = 30.0         # Hz per token ID unit
MAX_FREQ = 880.0         # Upper bound (A5)
MIN_FREQ = 220.0         # Lower bound (A3)


# =============================================================================
# Position to Intent Mapping
# =============================================================================

@dataclass
class SymphonicIntent:
    """Intent derived from Poincaré ball position."""
    position: np.ndarray       # 3D position in ball
    polarity: str              # "light", "shadow", "balanced"
    intensity: float           # 0-1, derived from distance to origin
    frequency: float           # Hz
    token_id: int              # Signed token ID
    phase: float               # Phase angle (radians)


def position_to_intent(point: np.ndarray) -> SymphonicIntent:
    """
    Map a Poincaré ball position to symphonic intent.

    Mapping:
    - Distance from origin → intensity (closer = calmer, further = intense)
    - Quadrant/direction → polarity (positive coords = light, negative = shadow)
    - Angle → phase
    - Combined → frequency
    """
    # Ensure 3D
    if len(point) < 3:
        point = np.concatenate([point, np.zeros(3 - len(point))])
    point = point[:3]

    # Distance from origin (0 to ~1)
    distance = np.linalg.norm(point)
    distance = min(distance, 0.99)  # Clamp to ball interior

    # Intensity: further from origin = more intense
    intensity = distance

    # Polarity: based on dominant coordinate sign
    coord_sum = np.sum(point)
    if coord_sum > 0.1:
        polarity = "light"
        polarity_multiplier = 1.0
    elif coord_sum < -0.1:
        polarity = "shadow"
        polarity_multiplier = -1.0
    else:
        polarity = "balanced"
        polarity_multiplier = 0.0

    # Token ID: scaled by distance and polarity (-10 to +10 range)
    token_id = int(round(distance * 10 * polarity_multiplier))
    token_id = max(-10, min(10, token_id))  # Clamp

    # Frequency: base + step * token_id, with intensity modulation
    frequency = BASE_FREQ + FREQ_STEP * token_id
    # Add intensity-based vibrato range
    frequency += intensity * 10 * np.sin(np.sum(point) * np.pi)
    frequency = max(MIN_FREQ, min(MAX_FREQ, frequency))

    # Phase from position angle
    if distance > 1e-6:
        phase = np.arctan2(point[1], point[0])
    else:
        phase = 0.0

    return SymphonicIntent(
        position=point,
        polarity=polarity,
        intensity=intensity,
        frequency=frequency,
        token_id=token_id,
        phase=phase
    )


def hyperpath_to_intents(path: List[np.ndarray]) -> List[SymphonicIntent]:
    """Convert a hyperpath (list of positions) to sequence of intents."""
    return [position_to_intent(p) for p in path]


# =============================================================================
# Waveform Generation
# =============================================================================

def generate_tone(
    frequency: float,
    duration: float,
    sample_rate: int = SAMPLE_RATE,
    amplitude: float = 0.5,
    phase: float = 0.0
) -> np.ndarray:
    """Generate a pure sine tone."""
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    return amplitude * np.sin(2 * np.pi * frequency * t + phase)


def apply_envelope(
    samples: np.ndarray,
    attack: float = 0.01,
    decay: float = 0.05,
    sustain: float = 0.7,
    release: float = 0.05,
    sample_rate: int = SAMPLE_RATE
) -> np.ndarray:
    """Apply ADSR envelope to samples."""
    n = len(samples)

    attack_samples = int(attack * sample_rate)
    decay_samples = int(decay * sample_rate)
    release_samples = int(release * sample_rate)
    sustain_samples = n - attack_samples - decay_samples - release_samples

    if sustain_samples < 0:
        # Too short for full ADSR, use simple fade
        fade_samples = n // 10
        envelope = np.ones(n)
        envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
        envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
        return samples * envelope

    envelope = np.concatenate([
        np.linspace(0, 1, attack_samples),                    # Attack
        np.linspace(1, sustain, decay_samples),               # Decay
        np.full(sustain_samples, sustain),                    # Sustain
        np.linspace(sustain, 0, release_samples)              # Release
    ])

    # Ensure same length
    if len(envelope) != n:
        envelope = np.resize(envelope, n)

    return samples * envelope


def add_harmonics(
    fundamental: np.ndarray,
    frequency: float,
    duration: float,
    harmonics: List[Tuple[int, float]] = None,
    sample_rate: int = SAMPLE_RATE
) -> np.ndarray:
    """Add harmonic overtones to fundamental."""
    if harmonics is None:
        # Default: 2nd, 3rd, 4th harmonics with decreasing amplitude
        harmonics = [(2, 0.3), (3, 0.15), (4, 0.07)]

    result = fundamental.copy()

    for harmonic_num, amplitude in harmonics:
        harmonic_freq = frequency * harmonic_num
        if harmonic_freq < MAX_FREQ * 2:  # Don't exceed reasonable range
            t = np.linspace(0, duration, len(fundamental), dtype=np.float32)
            result += amplitude * np.sin(2 * np.pi * harmonic_freq * t)

    # Normalize
    max_val = np.max(np.abs(result))
    if max_val > 0:
        result = result / max_val * 0.9

    return result


# =============================================================================
# Hyperpath to Waveform
# =============================================================================

def hyperpath_to_waveform(
    path: List[np.ndarray],
    note_duration: float = 0.3,
    crossfade: float = 0.02,
    include_harmonics: bool = True,
    sample_rate: int = SAMPLE_RATE
) -> Tuple[np.ndarray, List[SymphonicIntent]]:
    """
    Convert a hyperpath traversal to a symphonic waveform.

    Each point on the path generates a tone based on its position.
    Light realm points → higher frequencies (above 440 Hz)
    Shadow realm points → lower frequencies (below 440 Hz)

    Args:
        path: List of 3D points in Poincaré ball
        note_duration: Duration of each note in seconds
        crossfade: Crossfade between notes for smooth transitions
        include_harmonics: Add harmonic overtones
        sample_rate: Audio sample rate

    Returns:
        (audio_samples, intents) tuple
    """
    if not path:
        return np.array([], dtype=np.float32), []

    intents = hyperpath_to_intents(path)
    segments = []

    for intent in intents:
        # Generate base tone
        tone = generate_tone(
            intent.frequency,
            note_duration,
            sample_rate,
            amplitude=0.5 + intent.intensity * 0.3,  # Louder when intense
            phase=intent.phase
        )

        # Add harmonics for richer sound
        if include_harmonics:
            # Shadow tones get more harmonics (darker timbre)
            if intent.polarity == "shadow":
                harmonics = [(2, 0.4), (3, 0.25), (4, 0.15), (5, 0.08)]
            elif intent.polarity == "light":
                harmonics = [(2, 0.2), (3, 0.1)]
            else:
                harmonics = [(2, 0.3), (3, 0.15)]

            tone = add_harmonics(tone, intent.frequency, note_duration, harmonics, sample_rate)

        # Apply envelope
        tone = apply_envelope(tone, sample_rate=sample_rate)

        segments.append(tone)

    # Concatenate with crossfade
    if len(segments) == 1:
        return segments[0], intents

    crossfade_samples = int(crossfade * sample_rate)

    # Build final waveform
    result = segments[0]
    for seg in segments[1:]:
        if crossfade_samples > 0 and len(result) >= crossfade_samples and len(seg) >= crossfade_samples:
            # Crossfade
            fade_out = np.linspace(1, 0, crossfade_samples)
            fade_in = np.linspace(0, 1, crossfade_samples)

            result[-crossfade_samples:] *= fade_out
            seg[:crossfade_samples] *= fade_in

            # Overlap-add
            result[-crossfade_samples:] += seg[:crossfade_samples]
            result = np.concatenate([result, seg[crossfade_samples:]])
        else:
            result = np.concatenate([result, seg])

    return result.astype(np.float32), intents


# =============================================================================
# Waveform Export
# =============================================================================

def export_wav(
    samples: np.ndarray,
    filename: str,
    sample_rate: int = SAMPLE_RATE
) -> bool:
    """
    Export waveform to .wav file.

    Uses scipy.io.wavfile if available, otherwise pure numpy fallback.
    """
    # Normalize to int16 range
    max_val = np.max(np.abs(samples))
    if max_val > 0:
        normalized = samples / max_val
    else:
        normalized = samples

    int16_samples = (normalized * 32767).astype(np.int16)

    if SCIPY_AVAILABLE:
        wavfile.write(filename, sample_rate, int16_samples)
        return True
    else:
        # Pure numpy WAV export (basic)
        return _export_wav_numpy(int16_samples, filename, sample_rate)


def _export_wav_numpy(samples: np.ndarray, filename: str, sample_rate: int) -> bool:
    """Fallback WAV export using pure numpy."""
    try:
        n_samples = len(samples)
        n_channels = 1
        bits_per_sample = 16
        byte_rate = sample_rate * n_channels * bits_per_sample // 8
        block_align = n_channels * bits_per_sample // 8
        data_size = n_samples * block_align

        with open(filename, 'wb') as f:
            # RIFF header
            f.write(b'RIFF')
            f.write(struct.pack('<I', 36 + data_size))  # File size - 8
            f.write(b'WAVE')

            # fmt chunk
            f.write(b'fmt ')
            f.write(struct.pack('<I', 16))  # Chunk size
            f.write(struct.pack('<H', 1))   # Audio format (PCM)
            f.write(struct.pack('<H', n_channels))
            f.write(struct.pack('<I', sample_rate))
            f.write(struct.pack('<I', byte_rate))
            f.write(struct.pack('<H', block_align))
            f.write(struct.pack('<H', bits_per_sample))

            # data chunk
            f.write(b'data')
            f.write(struct.pack('<I', data_size))
            f.write(samples.tobytes())

        return True
    except Exception as e:
        print(f"[WAVEFORM] Export error: {e}", file=sys.stderr)
        return False


# =============================================================================
# Harmonic Fingerprint (for Octree Storage)
# =============================================================================

@dataclass
class HarmonicFingerprint:
    """Spectral fingerprint for octree node storage."""
    dominant_freq: float
    polarity: str
    intensity: float
    spectral_centroid: float
    energy: float
    hash: str


def compute_harmonic_fingerprint(
    samples: np.ndarray,
    sample_rate: int = SAMPLE_RATE
) -> HarmonicFingerprint:
    """
    Compute harmonic fingerprint from waveform segment.

    Can be stored in octree nodes for spectral clustering.
    """
    # Simple FFT analysis
    n = len(samples)
    if n < 256:
        # Pad short signals
        samples = np.pad(samples, (0, 256 - n))
        n = 256

    # FFT
    fft = np.fft.rfft(samples)
    magnitude = np.abs(fft)
    freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)

    # Dominant frequency
    dominant_idx = np.argmax(magnitude[1:]) + 1  # Skip DC
    dominant_freq = freqs[dominant_idx]

    # Polarity from frequency
    if dominant_freq > BASE_FREQ + 15:
        polarity = "light"
    elif dominant_freq < BASE_FREQ - 15:
        polarity = "shadow"
    else:
        polarity = "balanced"

    # Spectral centroid
    total_magnitude = np.sum(magnitude[1:])
    if total_magnitude > 0:
        spectral_centroid = np.sum(freqs[1:] * magnitude[1:]) / total_magnitude
    else:
        spectral_centroid = BASE_FREQ

    # Energy
    energy = np.sum(samples ** 2) / n

    # Intensity from energy
    intensity = min(1.0, np.sqrt(energy) * 10)

    # Hash for unique identification
    hash_input = f"{dominant_freq:.2f}:{polarity}:{spectral_centroid:.2f}:{energy:.6f}"
    hash_val = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    return HarmonicFingerprint(
        dominant_freq=dominant_freq,
        polarity=polarity,
        intensity=intensity,
        spectral_centroid=spectral_centroid,
        energy=energy,
        hash=hash_val
    )


# =============================================================================
# Geodesic Traversal Integration
# =============================================================================

def poincare_geodesic(u: np.ndarray, v: np.ndarray, t: float, eps: float = 1e-8) -> np.ndarray:
    """Point on geodesic from u to v at parameter t ∈ [0,1]."""
    def mobius_add(x, y):
        xy = np.dot(x, y)
        xx = np.dot(x, x)
        yy = np.dot(y, y)
        num = (1 + 2 * xy + yy) * x + (1 - xx) * y
        den = 1 + 2 * xy + xx * yy
        return num / (den + eps)

    # Hyperbolic distance (simplified)
    nx, ny = np.dot(u, u), np.dot(v, v)
    if nx >= 1.0 or ny >= 1.0:
        return u + t * (v - u)  # Fallback to linear

    diff_sq = np.dot(u - v, u - v)
    denom = (1 - nx) * (1 - ny)
    arg = 1 + 2 * diff_sq / (denom + eps)
    d = np.arccosh(max(1.0, arg))

    if d < eps:
        return u.copy()

    direction = mobius_add(-u, v)
    norm = np.linalg.norm(direction)
    if norm > eps:
        direction /= norm

    tanh_term = np.tanh(t * d / 2.0)
    result = mobius_add(u, tanh_term * direction)

    # Ensure inside ball
    result_norm = np.linalg.norm(result)
    if result_norm >= 1.0:
        result = result / (result_norm + 0.01) * 0.95

    return result


def geodesic_to_waveform(
    start: np.ndarray,
    end: np.ndarray,
    n_points: int = 20,
    note_duration: float = 0.25,
    sample_rate: int = SAMPLE_RATE
) -> Tuple[np.ndarray, List[SymphonicIntent], str]:
    """
    Generate waveform from geodesic traversal between two points.

    Returns:
        (audio_samples, intents, output_filename)
    """
    # Sample geodesic
    path = []
    for i in range(n_points):
        t = i / (n_points - 1) if n_points > 1 else 0
        point = poincare_geodesic(start, end, t)
        path.append(point)

    # Generate waveform
    samples, intents = hyperpath_to_waveform(
        path, note_duration, sample_rate=sample_rate
    )

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"geodesic_traversal_{timestamp}.wav"

    return samples, intents, filename


# =============================================================================
# Real-Time Rendering Support
# =============================================================================

class RealTimeRenderer:
    """
    Real-time audio rendering for geodesic traversals.

    Generates audio chunks as the traversal progresses,
    suitable for streaming to audio output.
    """

    def __init__(self, sample_rate: int = SAMPLE_RATE, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.buffer = np.array([], dtype=np.float32)
        self.intents: List[SymphonicIntent] = []

    def feed_position(self, position: np.ndarray, duration: float = 0.1) -> np.ndarray:
        """
        Feed a new position and get audio chunk.

        Returns audio samples for this position.
        """
        intent = position_to_intent(position)
        self.intents.append(intent)

        # Generate tone
        tone = generate_tone(
            intent.frequency,
            duration,
            self.sample_rate,
            amplitude=0.5 + intent.intensity * 0.3,
            phase=intent.phase
        )

        # Simple envelope
        fade = int(0.01 * self.sample_rate)
        if len(tone) > fade * 2:
            tone[:fade] *= np.linspace(0, 1, fade)
            tone[-fade:] *= np.linspace(1, 0, fade)

        return tone

    def get_chunk(self) -> Optional[np.ndarray]:
        """Get next audio chunk if available."""
        if len(self.buffer) >= self.chunk_size:
            chunk = self.buffer[:self.chunk_size]
            self.buffer = self.buffer[self.chunk_size:]
            return chunk
        return None

    def get_fingerprint(self) -> Optional[HarmonicFingerprint]:
        """Get harmonic fingerprint of accumulated audio."""
        if len(self.buffer) > 256:
            return compute_harmonic_fingerprint(self.buffer, self.sample_rate)
        return None


# =============================================================================
# Demo
# =============================================================================

def demo():
    """Demonstrate hyperpath to waveform export."""
    print("")
    print("=" * 79)
    print("         SYMPHONIC WAVEFORM EXPORT - Hyperpath Audio Synthesis")
    print('    "The auditory structure of the data becomes a proof of validity"')
    print("=" * 79)
    print("")

    # Demo 1: Light realm geodesic (near origin)
    print("  Demo 1: Light Realm Traversal")
    print("  " + "-" * 60)
    start_light = np.array([0.1, 0.1, 0.1])
    end_light = np.array([0.3, 0.2, 0.15])

    samples_light, intents_light, filename_light = geodesic_to_waveform(
        start_light, end_light, n_points=10, note_duration=0.3
    )

    print(f"    Start: {start_light} -> End: {end_light}")
    print(f"    Points: 10, Duration: {len(samples_light)/SAMPLE_RATE:.2f}s")
    print(f"    Frequencies: {[f'{i.frequency:.0f}Hz' for i in intents_light[:5]]}...")
    print(f"    Polarity: {intents_light[0].polarity} -> {intents_light[-1].polarity}")

    # Export
    export_wav(samples_light, filename_light)
    print(f"    Exported: {filename_light}")

    # Fingerprint
    fp_light = compute_harmonic_fingerprint(samples_light)
    print(f"    Fingerprint: {fp_light.hash} (centroid: {fp_light.spectral_centroid:.1f}Hz)")
    print()

    # Demo 2: Shadow realm geodesic (near boundary)
    print("  Demo 2: Shadow Realm Traversal")
    print("  " + "-" * 60)
    start_shadow = np.array([-0.7, -0.5, -0.3])
    end_shadow = np.array([-0.85, -0.2, 0.1])

    samples_shadow, intents_shadow, filename_shadow = geodesic_to_waveform(
        start_shadow, end_shadow, n_points=15, note_duration=0.25
    )

    print(f"    Start: {start_shadow} -> End: {end_shadow}")
    print(f"    Points: 15, Duration: {len(samples_shadow)/SAMPLE_RATE:.2f}s")
    print(f"    Frequencies: {[f'{i.frequency:.0f}Hz' for i in intents_shadow[:5]]}...")
    print(f"    Polarity: {intents_shadow[0].polarity} -> {intents_shadow[-1].polarity}")

    export_wav(samples_shadow, filename_shadow)
    print(f"    Exported: {filename_shadow}")

    fp_shadow = compute_harmonic_fingerprint(samples_shadow)
    print(f"    Fingerprint: {fp_shadow.hash} (centroid: {fp_shadow.spectral_centroid:.1f}Hz)")
    print()

    # Demo 3: Cross-realm traversal (light -> shadow)
    print("  Demo 3: Cross-Realm Traversal (Light -> Shadow)")
    print("  " + "-" * 60)
    start_cross = np.array([0.2, 0.2, 0.1])   # Light
    end_cross = np.array([-0.8, -0.3, 0.0])   # Shadow

    samples_cross, intents_cross, filename_cross = geodesic_to_waveform(
        start_cross, end_cross, n_points=25, note_duration=0.2
    )

    print(f"    Start (light): {start_cross}")
    print(f"    End (shadow):  {end_cross}")
    print(f"    Points: 25, Duration: {len(samples_cross)/SAMPLE_RATE:.2f}s")

    # Show frequency progression
    freqs = [i.frequency for i in intents_cross]
    print(f"    Frequency range: {min(freqs):.0f}Hz -> {max(freqs):.0f}Hz")
    print(f"    Polarity transition: {intents_cross[0].polarity} -> {intents_cross[-1].polarity}")

    export_wav(samples_cross, filename_cross)
    print(f"    Exported: {filename_cross}")

    fp_cross = compute_harmonic_fingerprint(samples_cross)
    print(f"    Fingerprint: {fp_cross.hash}")
    print()

    # Summary
    print("  " + "=" * 60)
    print("  Summary:")
    print(f"    Light traversal:  {fp_light.dominant_freq:.0f}Hz dominant, {fp_light.polarity}")
    print(f"    Shadow traversal: {fp_shadow.dominant_freq:.0f}Hz dominant, {fp_shadow.polarity}")
    print(f"    Cross-realm:      {fp_cross.dominant_freq:.0f}Hz dominant, {fp_cross.polarity}")
    print()
    print("  Audio files generated. Play to hear the 'proof of validity'.")
    print()


if __name__ == "__main__":
    demo()
