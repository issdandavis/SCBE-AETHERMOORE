"""
Spiral Sonifier — Audio Proof from Fibonacci Drift
=====================================================

Converts Fibonacci spiral paths into audible tones. Each governance
evaluation produces a unique sound — the "voice" of that operation.

This is the L14 Audio Axis expressed through the Fibonacci spiral:
- Clean operations sound harmonic (consonant intervals)
- Suspicious operations sound dissonant (beating frequencies)
- Adversarial operations sound harsh (clashing partials)

You can literally HEAR if something is wrong.

Frequency mapping (from Aethercode tongue bands):
  KO: 440-523 Hz  (A4-C5)   — Command register
  AV: 330-392 Hz  (E4-G4)   — Flow register
  RU: 262-311 Hz  (C4-Eb4)  — Structure register
  CA: 494-587 Hz  (B4-D5)   — Oracle register
  UM: 370-440 Hz  (F#4-A4)  — Harmony register
  DR: 220-262 Hz  (A3-C4)   — Ledger register (bass)

Chemistry analog: This is spectroscopy. Each element emits specific
frequencies when excited. Each governance operation emits specific
tones when evaluated. The spectrum IS the fingerprint.

@layer Layer 14 (Audio Axis)
@patent USPTO #63/961,403
"""

from __future__ import annotations

import hashlib
import math
import struct
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .tracker import (
    DriftSignature, SpiralPoint, PHI, GOLDEN_ANGLE,
    TONGUE_WEIGHTS, LAYER_TONGUE_RESONANCE
)

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

SAMPLE_RATE = 44100  # CD quality

# Tongue frequency bands (Hz) — from Aethercode
TONGUE_FREQ_BANDS: Dict[str, Tuple[float, float]] = {
    "KO": (440.0, 523.25),    # A4 to C5
    "AV": (329.63, 392.0),    # E4 to G4
    "RU": (261.63, 311.13),   # C4 to Eb4
    "CA": (493.88, 587.33),   # B4 to D5
    "UM": (369.99, 440.0),    # F#4 to A4
    "DR": (220.0, 261.63),    # A3 to C4
}

# Fibonacci ratios for harmonic series
FIBONACCI_RATIOS = [1/1, 1/1, 2/1, 3/2, 5/3, 8/5, 13/8, 21/13, 34/21, 55/34, 89/55, 144/89, 233/144, 377/233]


# ---------------------------------------------------------------------------
#  Data Types
# ---------------------------------------------------------------------------

@dataclass
class AudioProof:
    """Audible proof of a governance evaluation."""
    samples: List[float]        # PCM samples (-1.0 to 1.0)
    sample_rate: int            # Sample rate (Hz)
    duration_ms: float          # Duration in milliseconds
    spiral_hash: str            # Hash of source spiral
    dominant_frequency: float   # Strongest frequency component
    tongue_frequencies: Dict[str, float]  # Per-tongue frequency used
    harmonic_purity: float      # 0.0 = noise, 1.0 = pure tone
    spectral_fingerprint: str   # Hash of frequency content

    def to_wav_bytes(self) -> bytes:
        """Convert to WAV file bytes (16-bit PCM)."""
        num_samples = len(self.samples)
        # WAV header (44 bytes)
        data_size = num_samples * 2  # 16-bit = 2 bytes per sample
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + data_size,
            b"WAVE",
            b"fmt ",
            16,          # chunk size
            1,           # PCM format
            1,           # mono
            self.sample_rate,
            self.sample_rate * 2,  # byte rate
            2,           # block align
            16,          # bits per sample
            b"data",
            data_size,
        )
        # Convert float samples to 16-bit integers
        pcm_data = b""
        for s in self.samples:
            clamped = max(-1.0, min(1.0, s))
            sample_int = int(clamped * 32767)
            pcm_data += struct.pack("<h", sample_int)

        return header + pcm_data

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_rate": self.sample_rate,
            "duration_ms": round(self.duration_ms, 2),
            "num_samples": len(self.samples),
            "spiral_hash": self.spiral_hash,
            "dominant_frequency": round(self.dominant_frequency, 2),
            "tongue_frequencies": {k: round(v, 2) for k, v in self.tongue_frequencies.items()},
            "harmonic_purity": round(self.harmonic_purity, 4),
            "spectral_fingerprint": self.spectral_fingerprint,
        }


# ---------------------------------------------------------------------------
#  Spiral Sonifier
# ---------------------------------------------------------------------------

class SpiralSonifier:
    """
    Converts Fibonacci drift signatures into audio.

    Each spiral point becomes a tone:
    - Frequency = tongue band center ± (value * band width)
    - Amplitude = radius / max_radius
    - Duration = Fibonacci-proportional (longer for higher F_n)
    - Phase = golden angle offset

    The 14 tones are layered (polyphonic) or sequenced (melodic).
    """

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        duration_ms: float = 2000.0,
        mode: str = "polyphonic",  # "polyphonic" or "melodic"
    ):
        self.sample_rate = sample_rate
        self.duration_ms = duration_ms
        self.mode = mode

    def sonify(self, signature: DriftSignature) -> AudioProof:
        """Convert a drift signature into audio."""
        if self.mode == "melodic":
            return self._sonify_melodic(signature)
        return self._sonify_polyphonic(signature)

    def _sonify_polyphonic(self, sig: DriftSignature) -> AudioProof:
        """All 14 layers sound simultaneously — a chord."""
        num_samples = int(self.sample_rate * self.duration_ms / 1000)
        samples = [0.0] * num_samples
        tongue_freqs: Dict[str, float] = {}
        max_radius = max(p.radius for p in sig.points) if sig.points else 1.0

        for point in sig.points:
            # Frequency from tongue band
            lo, hi = TONGUE_FREQ_BANDS[point.tongue]
            freq = lo + point.value * (hi - lo)
            tongue_freqs[point.tongue] = freq

            # Amplitude from spiral radius
            amp = (point.radius / max(max_radius, 0.001)) * 0.15  # Scale down for mixing

            # Phase from golden angle position
            phase = point.theta

            # Envelope: Fibonacci-proportional attack/decay
            fib_weight = point.fibonacci_n / 377  # Normalize to F_14
            attack = int(num_samples * 0.05 * (1 + fib_weight))
            decay = int(num_samples * 0.1 * (1 + fib_weight))

            for i in range(num_samples):
                t = i / self.sample_rate
                # Sine wave with golden phase offset
                wave = math.sin(2 * math.pi * freq * t + phase)

                # Add Fibonacci harmonic (subtle)
                fib_ratio = FIBONACCI_RATIOS[point.layer - 1]
                wave += 0.3 * math.sin(2 * math.pi * freq * fib_ratio * t + phase)

                # Envelope
                env = 1.0
                if i < attack:
                    env = i / max(attack, 1)
                elif i > num_samples - decay:
                    env = (num_samples - i) / max(decay, 1)

                samples[i] += wave * amp * env

        # Normalize to prevent clipping
        peak = max(abs(s) for s in samples) if samples else 1.0
        if peak > 0.001:
            samples = [s / peak * 0.9 for s in samples]

        # Dominant frequency
        dom_tongue = sig.dominant_tongue
        lo, hi = TONGUE_FREQ_BANDS[dom_tongue]
        dom_freq = (lo + hi) / 2

        # Harmonic purity: how close the sound is to a pure harmonic series
        harmonic_purity = sig.phi_coherence

        # Spectral fingerprint
        spec_hash = hashlib.sha256(
            struct.pack("!" + "f" * min(len(samples), 1024), *samples[:1024])
        ).hexdigest()[:16]

        return AudioProof(
            samples=samples,
            sample_rate=self.sample_rate,
            duration_ms=self.duration_ms,
            spiral_hash=sig.spiral_hash,
            dominant_frequency=dom_freq,
            tongue_frequencies=tongue_freqs,
            harmonic_purity=harmonic_purity,
            spectral_fingerprint=spec_hash,
        )

    def _sonify_melodic(self, sig: DriftSignature) -> AudioProof:
        """14 layers play sequentially — a melody."""
        total_fib = sum(p.fibonacci_n for p in sig.points)
        total_samples = int(self.sample_rate * self.duration_ms / 1000)
        samples: List[float] = []
        tongue_freqs: Dict[str, float] = {}
        max_radius = max(p.radius for p in sig.points) if sig.points else 1.0

        for point in sig.points:
            # Duration proportional to Fibonacci number
            note_samples = int(total_samples * point.fibonacci_n / total_fib)
            if note_samples < 10:
                note_samples = 10

            # Frequency
            lo, hi = TONGUE_FREQ_BANDS[point.tongue]
            freq = lo + point.value * (hi - lo)
            tongue_freqs[point.tongue] = freq

            # Amplitude
            amp = (point.radius / max(max_radius, 0.001)) * 0.8

            # Attack/release envelope
            attack = int(note_samples * 0.1)
            release = int(note_samples * 0.2)

            for i in range(note_samples):
                t = i / self.sample_rate
                wave = math.sin(2 * math.pi * freq * t + point.theta)

                # Fibonacci harmonic
                fib_ratio = FIBONACCI_RATIOS[point.layer - 1]
                wave += 0.2 * math.sin(2 * math.pi * freq * fib_ratio * t)

                # Envelope
                env = 1.0
                if i < attack:
                    env = i / max(attack, 1)
                elif i > note_samples - release:
                    env = (note_samples - i) / max(release, 1)

                samples.append(wave * amp * env)

        # Normalize
        peak = max(abs(s) for s in samples) if samples else 1.0
        if peak > 0.001:
            samples = [s / peak * 0.9 for s in samples]

        dom_tongue = sig.dominant_tongue
        lo, hi = TONGUE_FREQ_BANDS[dom_tongue]
        dom_freq = (lo + hi) / 2

        spec_hash = hashlib.sha256(
            struct.pack("!" + "f" * min(len(samples), 1024), *samples[:1024])
        ).hexdigest()[:16]

        return AudioProof(
            samples=samples,
            sample_rate=self.sample_rate,
            duration_ms=len(samples) / self.sample_rate * 1000,
            spiral_hash=sig.spiral_hash,
            dominant_frequency=dom_freq,
            tongue_frequencies=tongue_freqs,
            harmonic_purity=sig.phi_coherence,
            spectral_fingerprint=spec_hash,
        )
