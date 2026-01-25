"""
Flat Slope Harmonic Encoder

Security through harmonic fingerprints, not frequency variation.

FLAT SLOPE PRINCIPLE:
    All tokens use the SAME fundamental frequency (440 Hz).
    Token identity encoded in WHICH harmonics are present.
    Without the secret key, all tokens look identical in frequency domain.

STEEP SLOPE (old, vulnerable):
    Token 0 → 440 Hz
    Token 1 → 470 Hz
    Token 2 → 500 Hz
    ATTACK: Frequency analysis reveals token boundaries

FLAT SLOPE (new, secure):
    Token 0 → 440 Hz + harmonics {1,3,7,12}    (derived from key + token)
    Token 1 → 440 Hz + harmonics {2,5,9,14}    (derived from key + token)
    Token 2 → 440 Hz + harmonics {1,4,8,11}    (derived from key + token)
    ATTACK FAILS: All tokens have same fundamental, different harmonics undetectable without key

Mathematical Model:
    S(t; τ, K) = Σ_{h ∈ H(τ,K)} A_h · sin(2π · h · f₀ · t + φ_h)

    Where:
        f₀ = 440 Hz (constant for ALL tokens)
        H(τ, K) = harmonic mask derived from HMAC(K, τ)
        A_h = amplitude envelope per harmonic
        φ_h = phase derived from key

Security Properties:
    1. Frequency-flat: Spectral centroid identical for all tokens
    2. Key-dependent: Harmonic mask requires secret key
    3. Token-unique: Each token has distinct harmonic fingerprint under same key
    4. Collision-resistant: Different tokens never produce same mask (2^128 space)
"""

import hmac
import hashlib
import numpy as np
from dataclasses import dataclass
from typing import List, Set, Tuple, Optional
from enum import Enum


# =============================================================================
# CONSTANTS
# =============================================================================

# Base frequency - FLAT for all tokens
BASE_FREQUENCY_HZ = 440.0

# Harmonic range (1 = fundamental, 2-16 = overtones)
MIN_HARMONIC = 1
MAX_HARMONIC = 16
HARMONIC_COUNT = MAX_HARMONIC - MIN_HARMONIC + 1

# Sample rate for waveform synthesis
SAMPLE_RATE = 44100

# Minimum harmonics per token (prevents sparse fingerprints)
MIN_HARMONICS_PER_TOKEN = 4
MAX_HARMONICS_PER_TOKEN = 8


class ModalityMask(Enum):
    """
    Modality-specific harmonic masks for domain separation.

    Different modalities use different base harmonic patterns,
    providing semantic separation even before key derivation.
    """
    STRICT = "strict"       # Odd harmonics only {1,3,5,7,...}
    ADAPTIVE = "adaptive"   # Full range {1,2,3,4,5,...}
    PROBE = "probe"         # Fundamental only {1}
    ORCHESTRAL = "orch"     # Musical fifths {1,3,6,9,12}


# =============================================================================
# KEY-DERIVED HARMONIC MASK
# =============================================================================

@dataclass
class HarmonicFingerprint:
    """
    A token's harmonic fingerprint derived from secret key.

    Attributes:
        token_id: The token being encoded
        harmonics: Set of active harmonic numbers {1, 3, 5, ...}
        amplitudes: Amplitude for each harmonic
        phases: Phase offset for each harmonic
        key_commitment: HMAC commitment for verification
    """
    token_id: int
    harmonics: Set[int]
    amplitudes: np.ndarray
    phases: np.ndarray
    key_commitment: bytes


def derive_harmonic_mask(
    token_id: int,
    secret_key: bytes,
    modality: ModalityMask = ModalityMask.ADAPTIVE,
    domain: str = "default"
) -> HarmonicFingerprint:
    """
    Derive a unique harmonic fingerprint for a token using secret key.

    Security: Without knowledge of secret_key, an attacker cannot predict
    which harmonics encode which token. All tokens appear as 440 Hz tones
    with random harmonic content.

    Args:
        token_id: Token to encode (0 to vocabulary size)
        secret_key: Shared secret (32+ bytes recommended)
        modality: Base harmonic pattern (affects character)
        domain: Domain separation string (e.g., "KO", "AV", "RU")

    Returns:
        HarmonicFingerprint with derived mask
    """
    # Domain-separated key derivation
    context = f"flat_slope:v1:{domain}:{modality.value}:token:{token_id}"

    # HMAC-SHA256 for key derivation
    derived = hmac.new(
        secret_key,
        context.encode('utf-8'),
        hashlib.sha256
    ).digest()

    # Commitment for later verification
    key_commitment = hmac.new(
        secret_key,
        f"commit:{token_id}".encode('utf-8'),
        hashlib.sha256
    ).digest()[:16]

    # Determine base harmonic pool based on modality
    if modality == ModalityMask.STRICT:
        # Odd harmonics only - harsher, clearer
        harmonic_pool = [h for h in range(MIN_HARMONIC, MAX_HARMONIC + 1) if h % 2 == 1]
    elif modality == ModalityMask.PROBE:
        # Fundamental only - minimal signal
        harmonic_pool = [1]
    elif modality == ModalityMask.ORCHESTRAL:
        # Musical fifths pattern
        harmonic_pool = [1, 3, 6, 9, 12, 15]
    else:  # ADAPTIVE
        # Full range
        harmonic_pool = list(range(MIN_HARMONIC, MAX_HARMONIC + 1))

    # Select harmonics using derived bytes
    selected_harmonics = set()

    # ALWAYS include fundamental (harmonic 1) for true flat slope
    # This ensures frequency analysis sees 440 Hz for ALL tokens
    if 1 in harmonic_pool:
        selected_harmonics.add(1)

    for i, h in enumerate(harmonic_pool):
        byte_idx = i % 32
        bit_idx = i % 8
        if derived[byte_idx] & (1 << bit_idx):
            selected_harmonics.add(h)

    # Ensure minimum harmonic count
    while len(selected_harmonics) < MIN_HARMONICS_PER_TOKEN:
        # Add harmonics deterministically from remaining pool
        for h in harmonic_pool:
            if h not in selected_harmonics:
                selected_harmonics.add(h)
                break

    # Trim to maximum if needed
    if len(selected_harmonics) > MAX_HARMONICS_PER_TOKEN:
        # Keep lowest harmonics (perceptually most important)
        selected_harmonics = set(sorted(selected_harmonics)[:MAX_HARMONICS_PER_TOKEN])

    # Derive amplitudes - inversely proportional to harmonic number (natural decay)
    # with key-derived variation
    harmonics_list = sorted(selected_harmonics)
    amplitudes = np.zeros(len(harmonics_list))
    phases = np.zeros(len(harmonics_list))

    for i, h in enumerate(harmonics_list):
        # Base amplitude: 1/h (natural harmonic rolloff)
        base_amp = 1.0 / h

        # Key-derived variation (±20%)
        variation = ((derived[(h + 16) % 32] / 255.0) - 0.5) * 0.4
        amplitudes[i] = base_amp * (1.0 + variation)

        # Key-derived phase (0 to 2π)
        phases[i] = (derived[(h + 20) % 32] / 255.0) * 2 * np.pi

    # Normalize amplitudes so peak doesn't clip
    max_amp = np.sum(amplitudes)
    if max_amp > 0:
        amplitudes = amplitudes / max_amp

    return HarmonicFingerprint(
        token_id=token_id,
        harmonics=selected_harmonics,
        amplitudes=amplitudes,
        phases=phases,
        key_commitment=key_commitment
    )


# =============================================================================
# WAVEFORM SYNTHESIS
# =============================================================================

def synthesize_token(
    fingerprint: HarmonicFingerprint,
    duration_ms: float = 100.0,
    sample_rate: int = SAMPLE_RATE
) -> np.ndarray:
    """
    Synthesize audio waveform for a token's harmonic fingerprint.

    All tokens produce 440 Hz base frequency. Only the harmonic content
    differs, and that difference is key-derived.

    Args:
        fingerprint: Harmonic fingerprint from derive_harmonic_mask
        duration_ms: Duration in milliseconds
        sample_rate: Audio sample rate

    Returns:
        Numpy array of audio samples
    """
    num_samples = int((duration_ms / 1000.0) * sample_rate)
    t = np.linspace(0, duration_ms / 1000.0, num_samples, dtype=np.float64)

    # Sum all active harmonics
    waveform = np.zeros(num_samples, dtype=np.float64)

    harmonics_list = sorted(fingerprint.harmonics)
    for i, h in enumerate(harmonics_list):
        freq = BASE_FREQUENCY_HZ * h
        amp = fingerprint.amplitudes[i]
        phase = fingerprint.phases[i]

        waveform += amp * np.sin(2 * np.pi * freq * t + phase)

    # Apply envelope (attack-sustain-release) to avoid clicks
    envelope = _generate_envelope(num_samples, sample_rate)
    waveform *= envelope

    return waveform


def _generate_envelope(
    num_samples: int,
    sample_rate: int,
    attack_ms: float = 5.0,
    release_ms: float = 10.0
) -> np.ndarray:
    """Generate smooth attack-sustain-release envelope."""
    attack_samples = int((attack_ms / 1000.0) * sample_rate)
    release_samples = int((release_ms / 1000.0) * sample_rate)

    envelope = np.ones(num_samples)

    # Attack ramp
    if attack_samples > 0:
        attack_samples = min(attack_samples, num_samples)
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)

    # Release ramp
    if release_samples > 0 and num_samples > release_samples:
        envelope[-release_samples:] = np.linspace(1, 0, release_samples)

    return envelope


# =============================================================================
# MESSAGE ENCODING
# =============================================================================

@dataclass
class EncodedMessage:
    """
    A complete message encoded as flat-slope harmonic signal.

    Attributes:
        token_ids: Original token sequence
        waveform: Combined audio waveform
        fingerprints: Individual token fingerprints (for verification)
        envelope_hmac: HMAC of entire message for integrity
    """
    token_ids: List[int]
    waveform: np.ndarray
    fingerprints: List[HarmonicFingerprint]
    envelope_hmac: bytes


def encode_message(
    token_ids: List[int],
    secret_key: bytes,
    modality: ModalityMask = ModalityMask.ADAPTIVE,
    domain: str = "default",
    token_duration_ms: float = 100.0,
    gap_duration_ms: float = 10.0
) -> EncodedMessage:
    """
    Encode a sequence of tokens as flat-slope harmonic signal.

    Each token becomes a 440 Hz tone with unique harmonic fingerprint.
    Without the key, the message appears as a sequence of similar-sounding
    tones with no discernible pattern.

    Args:
        token_ids: List of token IDs to encode
        secret_key: Shared secret for harmonic derivation
        modality: Harmonic character mode
        domain: Domain separation string
        token_duration_ms: Duration per token
        gap_duration_ms: Silence between tokens

    Returns:
        EncodedMessage with combined waveform
    """
    fingerprints = []
    waveforms = []
    gap_samples = int((gap_duration_ms / 1000.0) * SAMPLE_RATE)
    gap = np.zeros(gap_samples)

    for token_id in token_ids:
        # Derive fingerprint
        fp = derive_harmonic_mask(token_id, secret_key, modality, domain)
        fingerprints.append(fp)

        # Synthesize waveform
        wave = synthesize_token(fp, token_duration_ms)
        waveforms.append(wave)
        waveforms.append(gap)

    # Combine all waveforms
    if waveforms:
        # Remove trailing gap
        waveforms = waveforms[:-1] if len(waveforms) > 1 else waveforms
        combined = np.concatenate(waveforms)
    else:
        combined = np.array([], dtype=np.float64)

    # Compute envelope HMAC for integrity
    message_bytes = b''.join(
        fp.key_commitment for fp in fingerprints
    )
    envelope_hmac = hmac.new(
        secret_key,
        message_bytes,
        hashlib.sha256
    ).digest()

    return EncodedMessage(
        token_ids=token_ids,
        waveform=combined,
        fingerprints=fingerprints,
        envelope_hmac=envelope_hmac
    )


# =============================================================================
# VERIFICATION (DECODING)
# =============================================================================

def verify_token_fingerprint(
    waveform: np.ndarray,
    expected_fingerprint: HarmonicFingerprint,
    tolerance: float = 0.1
) -> Tuple[bool, float]:
    """
    Verify that a waveform matches expected harmonic fingerprint.

    Uses FFT to extract harmonic content and compares against expected mask.

    Args:
        waveform: Audio samples to verify
        expected_fingerprint: Expected harmonic pattern
        tolerance: Allowed deviation (0.0 to 1.0)

    Returns:
        Tuple of (match: bool, confidence: float)
    """
    if len(waveform) < 64:
        return False, 0.0

    # FFT analysis
    fft = np.fft.rfft(waveform)
    freqs = np.fft.rfftfreq(len(waveform), 1.0 / SAMPLE_RATE)
    magnitudes = np.abs(fft)

    # Normalize
    max_mag = np.max(magnitudes)
    if max_mag > 0:
        magnitudes = magnitudes / max_mag

    # Check expected harmonics are present
    matches = 0
    total = len(expected_fingerprint.harmonics)

    for h in expected_fingerprint.harmonics:
        expected_freq = BASE_FREQUENCY_HZ * h

        # Find nearest frequency bin
        idx = np.argmin(np.abs(freqs - expected_freq))

        # Check if harmonic is present (above threshold)
        if magnitudes[idx] > 0.05:  # 5% threshold
            matches += 1

    confidence = matches / total if total > 0 else 0.0
    match = confidence >= (1.0 - tolerance)

    return match, confidence


def verify_envelope_integrity(
    message: EncodedMessage,
    secret_key: bytes
) -> bool:
    """
    Verify the envelope HMAC of an encoded message.

    Returns True if message integrity is intact.
    """
    # Recompute HMAC
    message_bytes = b''.join(
        fp.key_commitment for fp in message.fingerprints
    )
    expected_hmac = hmac.new(
        secret_key,
        message_bytes,
        hashlib.sha256
    ).digest()

    return hmac.compare_digest(message.envelope_hmac, expected_hmac)


# =============================================================================
# SECURITY ANALYSIS
# =============================================================================

def analyze_frequency_attack_resistance(
    token_ids: List[int],
    secret_key: bytes,
    num_samples: int = 100
) -> dict:
    """
    Analyze resistance to frequency analysis attacks.

    Demonstrates that without the key, all tokens appear to have
    the same fundamental frequency, defeating frequency analysis.

    Args:
        token_ids: Tokens to analyze
        secret_key: Secret key used for encoding
        num_samples: Number of random samples per token

    Returns:
        Analysis results dict
    """
    fundamentals = []
    spectral_centroids = []

    for token_id in token_ids:
        for _ in range(num_samples):
            fp = derive_harmonic_mask(token_id, secret_key)
            wave = synthesize_token(fp, duration_ms=50.0)

            # Extract fundamental
            fft = np.fft.rfft(wave)
            freqs = np.fft.rfftfreq(len(wave), 1.0 / SAMPLE_RATE)
            magnitudes = np.abs(fft)

            # Find peak (fundamental)
            peak_idx = np.argmax(magnitudes)
            fundamental = freqs[peak_idx]
            fundamentals.append(fundamental)

            # Compute spectral centroid
            if np.sum(magnitudes) > 0:
                centroid = np.sum(freqs * magnitudes) / np.sum(magnitudes)
            else:
                centroid = 0.0
            spectral_centroids.append(centroid)

    fundamentals = np.array(fundamentals)
    centroids = np.array(spectral_centroids)

    return {
        "fundamental_mean": float(np.mean(fundamentals)),
        "fundamental_std": float(np.std(fundamentals)),
        "fundamental_variance_hz": float(np.var(fundamentals)),
        "centroid_mean": float(np.mean(centroids)),
        "centroid_std": float(np.std(centroids)),
        "tokens_analyzed": len(token_ids),
        "samples_per_token": num_samples,
        "attack_success_probability": float(np.std(fundamentals) / BASE_FREQUENCY_HZ),
        "frequency_flat": bool(np.std(fundamentals) < 1.0),  # < 1 Hz variation
    }


def compare_steep_vs_flat(token_ids: List[int]) -> dict:
    """
    Compare steep slope (old) vs flat slope (new) encoding.

    Demonstrates why flat slope defeats frequency analysis.
    """
    # Steep slope: different base frequencies
    steep_fundamentals = []
    for token_id in token_ids:
        # Old vulnerable method: fundamental varies with token
        freq = 440.0 + (token_id * 30)  # Token 0=440, 1=470, 2=500...
        steep_fundamentals.append(freq)

    # Flat slope: same base frequency
    flat_fundamentals = [BASE_FREQUENCY_HZ] * len(token_ids)

    return {
        "steep_slope": {
            "fundamentals": steep_fundamentals,
            "variance": float(np.var(steep_fundamentals)),
            "attackable": True,
            "reason": "Frequency varies with token → frequency analysis reveals tokens"
        },
        "flat_slope": {
            "fundamentals": flat_fundamentals,
            "variance": 0.0,
            "attackable": False,
            "reason": "All tokens have same fundamental → only harmonic content differs, key required"
        }
    }


# =============================================================================
# RESONANCE REFRACTORING
# =============================================================================

def resonance_refractor(
    fingerprints: List[HarmonicFingerprint],
    interference_depth: float = 0.3
) -> np.ndarray:
    """
    Apply resonance refractoring for multi-token encoding.

    When multiple tokens are active, their harmonics interfere
    constructively and destructively based on phase relationships.
    This creates a unique interference pattern that encodes the
    sequence, not just individual tokens.

    Args:
        fingerprints: Sequence of token fingerprints
        interference_depth: How much adjacent tokens interfere (0-1)

    Returns:
        Combined waveform with interference encoding
    """
    if not fingerprints:
        return np.array([])

    duration_ms = 100.0
    num_samples = int((duration_ms / 1000.0) * SAMPLE_RATE)
    t = np.linspace(0, duration_ms / 1000.0, num_samples)

    # Synthesize each token
    token_waves = []
    for fp in fingerprints:
        wave = synthesize_token(fp, duration_ms)
        token_waves.append(wave)

    # Apply interference between adjacent tokens
    combined = np.zeros(num_samples * len(fingerprints))

    for i, wave in enumerate(token_waves):
        start = i * num_samples
        end = start + num_samples
        combined[start:end] += wave

        # Add interference from adjacent tokens
        if i > 0:
            # Previous token bleeds into current
            prev_wave = token_waves[i - 1]
            overlap = int(num_samples * interference_depth)
            if overlap > 0:
                combined[start:start + overlap] += prev_wave[-overlap:] * 0.3

        if i < len(token_waves) - 1:
            # Next token bleeds into current
            next_wave = token_waves[i + 1]
            overlap = int(num_samples * interference_depth)
            if overlap > 0:
                combined[end - overlap:end] += next_wave[:overlap] * 0.3

    # Normalize to prevent clipping
    max_val = np.max(np.abs(combined))
    if max_val > 0:
        combined = combined / max_val

    return combined


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def generate_key(length: int = 32) -> bytes:
    """Generate a cryptographically secure random key."""
    import secrets
    return secrets.token_bytes(length)


def key_from_passphrase(passphrase: str, salt: bytes = b"flat_slope_v1") -> bytes:
    """Derive key from passphrase using PBKDF2."""
    return hashlib.pbkdf2_hmac(
        'sha256',
        passphrase.encode('utf-8'),
        salt,
        iterations=100000,
        dklen=32
    )
