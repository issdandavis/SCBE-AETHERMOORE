"""
Harmonic Cipher — RWP v3.0 Audio-Cryptographic Verification
=============================================================
Implements the full harmonic cipher specification from:
  docs/08-reference/archive/RWP_v3_SACRED_TONGUE_HARMONIC_VERIFICATION.md

Chain (sender):
  token IDs → Feistel permutation (4-round, HMAC-keyed)
            → harmonic synthesis: x(t) = Σᵢ Σₕ∈ℳ(M) (1/h)·sin(2π(f₀ + v'ᵢ·Δf)·h·t)
            → audio payload in RWP v3 envelope with HMAC signature

Chain (receiver):
  envelope → MAC verify → inverse Feistel → recover token order
          → optional: re-synthesize + compare energy (harmonic integrity check)

Modality masks (ℳ):
  STRICT   → odd harmonics {1, 3, 5}      — clarinet-like, odd-only spectrum
  ADAPTIVE → full series {1, 2, 3, 4, 5}  — full harmonic content
  PROBE    → fundamental only {1}          — pure sine, zero overtone content

Spectral parameters (from spec):
  BASE_F = 440 Hz  (A4 — Kor'aelin tonic, intent clarity)
  Δf     = 30 Hz   (step per token ID)
  H_max  = 5       (maximum overtone)
  SR     = 44100 Hz, T_sec = 0.5 s

Nyquist handling: overtones exceeding SR/2 are skipped per-token
(256-token vocab × Δf=30 → max fundamental 8090 Hz; H5 would be 40450 Hz).

Integration:
  - L9 spectral coherence: tongue harmonic frequencies validated against ℳ(M)
  - L14 audio axis: harmonic cipher waveforms as governance telemetry
  - RWP v3.0: replaces SHA-256 proxy in compute_harmonic_fingerprint()

Version: 1.0.0
Spec ref: RWP_v3_SACRED_TONGUE_HARMONIC_VERIFICATION.md §3–§9
"""

from __future__ import annotations

import base64
import hashlib
import hmac as hmac_mod
import json
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

# ============================================================
# Constants (from spec §9)
# ============================================================

BASE_F: float = 440.0  # Hz — A4, intent tonic
DELTA_F: float = 30.0  # Hz per token ID unit
H_MAX: int = 5  # Maximum overtone index
SAMPLE_RATE: int = 44_100  # CD quality
T_SEC: float = 0.5  # Audio payload duration (seconds)
FEISTEL_ROUNDS: int = 4  # R in spec §5
TAU_MAX_S: int = 60  # Replay window (seconds)
EPS_F: float = 2.0  # Frequency tolerance for FFT verification (Hz)
EPS_A: float = 0.15  # Amplitude tolerance for overtone pattern check

NYQUIST: float = SAMPLE_RATE / 2.0


# ============================================================
# Modality
# ============================================================


class Modality(Enum):
    """Intent-encoding modality — selects which overtone set ℳ(M) is emitted."""

    STRICT = "STRICT"  # Odd harmonics only: {1,3,5} — like a clarinet
    ADAPTIVE = "ADAPTIVE"  # Full series: {1,2,3,4,5}
    PROBE = "PROBE"  # Fundamental only: {1}


# Overtone sets ℳ(M) per spec §3
MODALITY_MASKS: Dict[Modality, List[int]] = {
    Modality.STRICT: [1, 3, 5],
    Modality.ADAPTIVE: [1, 2, 3, 4, 5],
    Modality.PROBE: [1],
}


# ============================================================
# Key Derivation  (spec §4)
# ============================================================


def derive_message_key(k_master: bytes, nonce: bytes) -> bytes:
    """K_msg = HMAC-SHA256(k_master, b'msg_key' ‖ nonce)"""
    return hmac_mod.new(k_master, b"msg_key" + nonce, hashlib.sha256).digest()


def _round_subkey(k_msg: bytes, r: int) -> bytes:
    """k⁽ʳ⁾ = HMAC-SHA256(K_msg, b'round' ‖ r) — one subkey per Feistel round."""
    return hmac_mod.new(k_msg, b"round" + bytes([r]), hashlib.sha256).digest()


# ============================================================
# Feistel Permutation  (spec §5)
# ============================================================
# Balanced Feistel on the token-ID vector.
# One Feistel round: (L, R) → (R, L ⊕ F(R, k_r))
# where F(x, k) = byte-wise XOR: F(x,k)_i = x_i ⊕ k_{i mod |k|}
#
# Inverse round (given output L', R'): L = R' ⊕ F(L', k_r) ; R = L'
# Applying rounds in reversed order restores the original vector.


def _feistel_round_forward(L: List[int], R: List[int], k_r: bytes) -> Tuple[List[int], List[int]]:
    """One forward Feistel round: (L, R) → (R, L ⊕ F(R, k_r))"""
    F = [R[i] ^ k_r[i % len(k_r)] for i in range(len(R))]
    new_R = [L[i] ^ F[i % len(F)] for i in range(len(L))]
    return R, new_R


def _feistel_round_inverse(L: List[int], R: List[int], k_r: bytes) -> Tuple[List[int], List[int]]:
    """Inverse of one Feistel round: (L', R') → (L, R)"""
    # L' = R_old → R_old = L'
    # R' = L_old ⊕ F(R_old, k_r) = L_old ⊕ F(L', k_r) → L_old = R' ⊕ F(L', k_r)
    F = [L[i] ^ k_r[i % len(k_r)] for i in range(len(L))]
    orig_L = [R[i] ^ F[i % len(F)] for i in range(len(R))]
    orig_R = L
    return orig_L, orig_R


def feistel_permute(token_ids: List[int], k_msg: bytes, rounds: int = FEISTEL_ROUNDS) -> List[int]:
    """
    Apply balanced Feistel permutation to token-ID vector.

    Args:
        token_ids: List of byte-valued token IDs (0–255)
        k_msg: Per-message key from derive_message_key()
        rounds: Number of Feistel rounds (default 4)

    Returns:
        Permuted token-ID vector of equal length
    """
    m = len(token_ids)
    if m <= 1:
        # Trivial case: balanced Feistel requires at least one element on each side.
        # Single-element and empty vectors are returned as-is (identity permutation).
        return list(token_ids)
    half = m // 2
    L = list(token_ids[:half])
    R = list(token_ids[half:])  # Right side gets the extra element if m is odd

    for r in range(rounds):
        k_r = _round_subkey(k_msg, r)
        L, R = _feistel_round_forward(L, R, k_r)

    return L + R


def feistel_inverse(permuted_ids: List[int], k_msg: bytes, rounds: int = FEISTEL_ROUNDS) -> List[int]:
    """
    Invert Feistel permutation to recover original token-ID vector.

    Args:
        permuted_ids: Permuted token-ID vector from feistel_permute()
        k_msg: Same per-message key used for permutation
        rounds: Same round count

    Returns:
        Original token-ID vector
    """
    m = len(permuted_ids)
    if m <= 1:
        return list(permuted_ids)
    half = m // 2
    L = list(permuted_ids[:half])
    R = list(permuted_ids[half:])

    for r in reversed(range(rounds)):
        k_r = _round_subkey(k_msg, r)
        L, R = _feistel_round_inverse(L, R, k_r)

    return L + R


# ============================================================
# Harmonic Synthesis  (spec §6)
# ============================================================
# x(t) = Σᵢ₌₀ᵐ⁻¹ Σₕ∈ℳ(M) (1/h) sin(2π(f₀ + v'ᵢ·Δf)·h·t)
#
# Nyquist cap: overtones where (f₀ + v'ᵢ·Δf)·h > SR/2 are skipped.
# At 256 tokens × Δf=30: max fundamental = 440 + 255×30 = 8090 Hz.
# H5 = 40450 Hz exceeds Nyquist; H2 = 16180 Hz also exceeds.
# Dynamic skip ensures synthesized waveform stays within band.


def harmonic_synthesis(
    permuted_ids: List[int],
    modality: Modality,
    sample_rate: int = SAMPLE_RATE,
    t_sec: float = T_SEC,
) -> np.ndarray:
    """
    Synthesize audio payload from permuted token IDs.

    Each token i contributes sinusoids at harmonics h of its fundamental
    frequency f₀ + v'ᵢ·Δf, with amplitude 1/h.

    Args:
        permuted_ids: Feistel-permuted token IDs
        modality: Selects overtone mask ℳ(M)
        sample_rate: Audio sample rate
        t_sec: Payload duration in seconds

    Returns:
        Audio waveform x ∈ ℝᴸ, L = sample_rate × t_sec
    """
    L = int(sample_rate * t_sec)
    t = np.linspace(0, t_sec, L, endpoint=False, dtype=np.float64)
    x = np.zeros(L, dtype=np.float64)
    nyquist = sample_rate / 2.0
    mask = MODALITY_MASKS[modality]

    for vid in permuted_ids:
        f_i = BASE_F + float(vid) * DELTA_F
        for h in mask:
            f_h = f_i * h
            if f_h >= nyquist:
                # Skip this overtone — beyond Nyquist for this token's fundamental
                continue
            x += (1.0 / h) * np.sin(2.0 * np.pi * f_h * t)

    return x.astype(np.float32)


# ============================================================
# Harmonic Verification  (spec §8 Step 4)
# ============================================================
# Re-synthesis approach: given the expected permuted IDs (recovered via
# inverse Feistel on the received permuted IDs — but wait, the receiver
# needs to reconstruct permuted IDs from audio first).
#
# Practical approach used here:
#   1. MAC verify first (covers audio integrity)
#   2. Optional: given recovered token IDs (post-inverse-Feistel), re-synthesize
#      expected audio and compare energy in the difference signal.
#   3. FFT peak check: verify peaks exist at expected fundamental frequencies
#      within EPS_F Hz, with amplitude pattern following 1/h within EPS_A.


def _harmonic_verify(
    audio: np.ndarray,
    expected_ids: List[int],
    modality: Modality,
    sample_rate: int = SAMPLE_RATE,
    t_sec: float = T_SEC,
) -> Tuple[bool, str]:
    """
    Verify audio encodes expected token IDs with correct harmonic structure.

    Two checks:
    1. Energy similarity: difference energy < 10% of expected energy
    2. Peak presence: fundamental peaks within EPS_F Hz of expected positions

    Args:
        audio: Received audio payload
        expected_ids: Token IDs recovered via inverse Feistel
        modality: Modality from envelope header

    Returns:
        (pass: bool, reason: str)
    """
    if len(expected_ids) == 0:
        return True, "empty token vector — trivially valid"

    # Re-synthesize expected audio
    expected_audio = harmonic_synthesis(expected_ids, modality, sample_rate, t_sec)
    L = min(len(audio), len(expected_audio))
    if L == 0:
        return False, "zero-length audio"

    a = audio[:L]
    e = expected_audio[:L]

    # Check 1: Energy of difference signal
    diff_energy = float(np.sum((a - e) ** 2))
    expected_energy = float(np.sum(e**2))
    if expected_energy > 0:
        relative_error = diff_energy / expected_energy
        if relative_error > 0.10:
            return False, f"re-synthesis energy mismatch: relative error {relative_error:.3f} > 0.10"

    # Check 2: FFT peak presence at expected fundamentals
    fft_mag = np.abs(np.fft.rfft(a))
    freqs = np.fft.rfftfreq(L, 1.0 / sample_rate)
    nyquist = sample_rate / 2.0

    for vid in expected_ids:
        f_i = BASE_F + float(vid) * DELTA_F
        if f_i >= nyquist:
            continue  # Skip tokens whose fundamental exceeds Nyquist
        # Find nearest FFT bin to expected fundamental
        bin_idx = int(np.argmin(np.abs(freqs - f_i)))
        actual_freq = float(freqs[bin_idx])
        if abs(actual_freq - f_i) > EPS_F:
            return (
                False,
                f"missing peak at {f_i:.1f}Hz (nearest: {actual_freq:.1f}Hz, deviation {abs(actual_freq-f_i):.2f}Hz > {EPS_F}Hz)",
            )

        # Check 1/h amplitude pattern (relative to fundamental bin)
        fundamental_mag = fft_mag[bin_idx]
        if fundamental_mag < 1e-8:
            return False, f"zero-magnitude fundamental at {f_i:.1f}Hz"

        mask = MODALITY_MASKS[modality]
        for h in mask[1:]:  # Skip h=1 (that's the fundamental we just checked)
            f_h = f_i * h
            if f_h >= nyquist:
                continue
            h_bin = int(np.argmin(np.abs(freqs - f_h)))
            expected_amp = fundamental_mag / h
            actual_amp = fft_mag[h_bin]
            if abs(actual_amp - expected_amp) > EPS_A * expected_amp + 1e-6:
                return False, (
                    f"amplitude pattern mismatch at h={h} of {f_i:.1f}Hz: "
                    f"expected {expected_amp:.4f}, got {actual_amp:.4f}"
                )

    return True, "OK"


# ============================================================
# Envelope Construction  (spec §7)
# ============================================================


@dataclass
class HarmonicEnvelope:
    """RWP v3 harmonic envelope — structured representation."""

    ver: str
    tongue: str
    aad: Dict[str, str]
    ts: int  # Unix ms
    nonce_b64: str
    kid: str
    mode: str  # Modality.value
    payload_b64: str  # base64url-encoded float32 audio samples
    sig: str  # HMAC-SHA256 hex over canonical string


def _aad_canonical(aad: Dict[str, str]) -> str:
    """Canonical AAD string: key=value; pairs sorted by key."""
    return "".join(f"{k}={v};" for k, v in sorted(aad.items()))


def _canonical_string(envelope: HarmonicEnvelope) -> str:
    """C = 'v3.' ‖ σ ‖ AAD_canon ‖ ts ‖ nonce_b64 ‖ payload_b64"""
    return (
        f"v3.{envelope.tongue}"
        f"{_aad_canonical(envelope.aad)}"
        f"{envelope.ts}"
        f"{envelope.nonce_b64}"
        f"{envelope.payload_b64}"
    )


def build_envelope(
    k_master: bytes,
    token_ids: List[int],
    tongue: str,
    aad: Optional[Dict[str, str]] = None,
    modality: Modality = Modality.ADAPTIVE,
    kid: str = "master",
    sample_rate: int = SAMPLE_RATE,
    t_sec: float = T_SEC,
) -> HarmonicEnvelope:
    """
    Build a RWP v3 harmonic envelope from token IDs.

    Args:
        k_master: Master key (≥32 bytes)
        token_ids: Byte-valued Sacred Tongue token IDs to encode
        tongue: Sacred Tongue domain identifier (e.g. 'ko', 'av')
        aad: Additional authenticated data dict
        modality: Overtone mask selection
        kid: Key identifier
        sample_rate: Audio sample rate
        t_sec: Audio duration

    Returns:
        HarmonicEnvelope ready for serialization
    """
    if aad is None:
        aad = {}

    # Fresh random nonce (96 bits)
    nonce = os.urandom(12)
    nonce_b64 = base64.urlsafe_b64encode(nonce).decode()

    # Per-message key
    k_msg = derive_message_key(k_master, nonce)

    # Feistel permutation of token IDs
    permuted = feistel_permute(token_ids, k_msg)

    # Harmonic synthesis
    audio = harmonic_synthesis(permuted, modality, sample_rate, t_sec)

    # Encode audio as base64url float32 bytes
    payload_b64 = base64.urlsafe_b64encode(audio.astype(np.float32).tobytes()).decode()

    ts = int(time.time() * 1000)

    envelope = HarmonicEnvelope(
        ver="3",
        tongue=tongue,
        aad=aad,
        ts=ts,
        nonce_b64=nonce_b64,
        kid=kid,
        mode=modality.value,
        payload_b64=payload_b64,
        sig="",  # Filled below
    )

    # HMAC over canonical string (spec §7)
    canonical = _canonical_string(envelope)
    sig = hmac_mod.new(k_master, canonical.encode(), hashlib.sha256).hexdigest()
    envelope.sig = sig

    return envelope


# ============================================================
# Envelope Serialization
# ============================================================


def envelope_to_dict(env: HarmonicEnvelope) -> Dict:
    return {
        "header": {
            "ver": env.ver,
            "tongue": env.tongue,
            "aad": env.aad,
            "ts": env.ts,
            "nonce": env.nonce_b64,
            "kid": env.kid,
            "mode": env.mode,
        },
        "payload": env.payload_b64,
        "sig": env.sig,
    }


def envelope_from_dict(d: Dict) -> HarmonicEnvelope:
    h = d["header"]
    return HarmonicEnvelope(
        ver=h["ver"],
        tongue=h["tongue"],
        aad=h.get("aad", {}),
        ts=h["ts"],
        nonce_b64=h["nonce"],
        kid=h.get("kid", "master"),
        mode=h.get("mode", Modality.ADAPTIVE.value),
        payload_b64=d["payload"],
        sig=d["sig"],
    )


# ============================================================
# Verification  (spec §8)
# ============================================================


@dataclass
class VerificationResult:
    valid: bool
    token_ids: List[int]  # Recovered original token IDs (empty if invalid)
    reason: str


def verify_envelope(
    envelope: HarmonicEnvelope,
    k_master: bytes,
    tau_max_s: int = TAU_MAX_S,
    harmonic_check: bool = True,
    sample_rate: int = SAMPLE_RATE,
    t_sec: float = T_SEC,
) -> VerificationResult:
    """
    Verify a RWP v3 harmonic envelope and recover original token IDs.

    Steps (spec §8):
      1. Replay check: |t_now - ts| ≤ τ_max
      2. MAC verify (constant-time): HMAC over canonical string
      3. Inverse Feistel: recover original token order from permuted IDs
      4. Optional harmonic verify: re-synthesize and compare

    Args:
        envelope: Parsed harmonic envelope
        k_master: Master key
        tau_max_s: Maximum age in seconds
        harmonic_check: If True, run re-synthesis energy + FFT peak check

    Returns:
        VerificationResult with valid flag, recovered token_ids, and reason
    """
    # Step 1: Replay check
    t_now_ms = int(time.time() * 1000)
    age_s = abs(t_now_ms - envelope.ts) / 1000.0
    if age_s > tau_max_s:
        return VerificationResult(False, [], f"replay: envelope age {age_s:.1f}s > {tau_max_s}s")

    # Step 2: MAC verify (constant-time)
    canonical = _canonical_string(envelope)
    expected_sig = hmac_mod.new(k_master, canonical.encode(), hashlib.sha256).hexdigest()
    if not hmac_mod.compare_digest(expected_sig, envelope.sig):
        return VerificationResult(False, [], "MAC verification failed")

    # Step 3: Recover original token IDs via inverse Feistel
    nonce = base64.urlsafe_b64decode(envelope.nonce_b64)
    k_msg = derive_message_key(k_master, nonce)

    payload_bytes = base64.urlsafe_b64decode(envelope.payload_b64)
    modality = Modality(envelope.mode)

    n_tokens_hint = envelope.aad.get("n_tokens")
    payload_enc = envelope.aad.get("payload_enc", "audio")

    if payload_enc == "xor" and n_tokens_hint is not None:
        # seal() convenience API: payload is XOR-masked permuted token bytes.
        # Audio is synthesized on demand (not stored in the envelope).
        n_tokens = int(n_tokens_hint)
        if n_tokens == 0:
            return VerificationResult(True, [], "OK")
        xor_stream = _payload_xor_stream(k_msg, n_tokens)
        permuted_ids = [payload_bytes[i] ^ xor_stream[i] for i in range(n_tokens)]
        original_ids = feistel_inverse(permuted_ids, k_msg)

        # Step 4: Optional harmonic check — synthesize from recovered permuted IDs
        # and verify the spectral structure is non-degenerate.
        if harmonic_check:
            audio = harmonic_synthesis(permuted_ids, modality, sample_rate, t_sec)
            ok, reason = _harmonic_verify(audio, permuted_ids, modality, sample_rate, t_sec)
            if not ok:
                return VerificationResult(False, [], f"harmonic verify failed: {reason}")

        return VerificationResult(True, original_ids, "OK")

    # Audio payload path (build_envelope() / raw harmonic mode):
    # payload_b64 is float32 audio — use FFT peak detection to recover permuted IDs.
    audio = np.frombuffer(payload_bytes, dtype=np.float32)

    if n_tokens_hint is None:
        return VerificationResult(
            True,  # MAC passed — envelope is authentic
            [],
            "MAC valid; harmonic recovery skipped (n_tokens not in aad)",
        )

    n_tokens = int(n_tokens_hint)
    permuted_ids = _extract_ids_from_audio(audio, n_tokens, modality, sample_rate)
    original_ids = feistel_inverse(permuted_ids, k_msg)

    # Step 4: Optional harmonic integrity check against received audio
    if harmonic_check:
        ok, reason = _harmonic_verify(audio, permuted_ids, modality, sample_rate, t_sec)
        if not ok:
            return VerificationResult(False, [], f"harmonic verify failed: {reason}")

    return VerificationResult(True, original_ids, "OK")


def _extract_ids_from_audio(
    audio: np.ndarray,
    n_tokens: int,
    modality: Modality,
    sample_rate: int = SAMPLE_RATE,
) -> List[int]:
    """
    Recover permuted token IDs from audio via FFT peak detection.

    For each of the n_tokens expected tokens, find the strongest FFT peak
    at a position consistent with BASE_F + id·DELTA_F and return the
    corresponding token IDs.

    This is a greedy match: sort all candidate peaks by magnitude and
    assign the top n_tokens to unique IDs.
    """
    fft_mag = np.abs(np.fft.rfft(audio))
    freqs = np.fft.rfftfreq(len(audio), 1.0 / sample_rate)
    nyquist = sample_rate / 2.0

    # Build expected fundamental frequency grid: f_id = BASE_F + id * DELTA_F
    # for id in 0..255, within Nyquist
    candidate_freqs = {
        vid: BASE_F + float(vid) * DELTA_F for vid in range(256) if BASE_F + float(vid) * DELTA_F < nyquist
    }

    # For each candidate, compute total energy in fundamental bin
    candidate_energy: List[Tuple[float, int]] = []
    for vid, f_i in candidate_freqs.items():
        bin_idx = int(np.argmin(np.abs(freqs - f_i)))
        # Sum energy in fundamental ± 2 bins (to handle FFT bin width)
        lo = max(0, bin_idx - 2)
        hi = min(len(fft_mag), bin_idx + 3)
        energy = float(np.sum(fft_mag[lo:hi] ** 2))
        candidate_energy.append((energy, vid))

    # Sort by energy descending; take top n_tokens
    candidate_energy.sort(key=lambda x: x[0], reverse=True)
    top_ids = [vid for _, vid in candidate_energy[:n_tokens]]

    # Pad with zeros if fewer candidates than expected
    while len(top_ids) < n_tokens:
        top_ids.append(0)

    return top_ids


# ============================================================
# Payload XOR Encryption (seal/unseal convenience layer)
# ============================================================
# When using the seal()/unseal() API the payload carries XOR-masked
# permuted token IDs (recoverable), not raw audio bytes.
# Audio is synthesized on demand during harmonic_check.
# Detection: len(payload_bytes) == n_tokens → XOR-masked bytes.
#            len(payload_bytes) > n_tokens  → audio (float32) payload.
#
# XOR key stream: k_i = HMAC(K_msg, b'payload_xor' ‖ floor(i/32).to_bytes(4))
# One 32-byte HMAC block per 32 bytes of payload — deterministic, reversible.


def _payload_xor_stream(k_msg: bytes, n: int) -> bytes:
    """Generate n-byte XOR key stream from K_msg for payload masking."""
    stream = bytearray()
    block = 0
    while len(stream) < n:
        stream += hmac_mod.new(k_msg, b"payload_xor" + block.to_bytes(4, "big"), hashlib.sha256).digest()
        block += 1
    return bytes(stream[:n])


# ============================================================
# Convenience: encode Sacred Tongue token strings → IDs
# ============================================================


def tokens_to_ids(token_strings: List[str], tongue_code: str) -> List[int]:
    """
    Convert Sacred Tongue token strings to byte IDs for harmonic cipher input.

    Args:
        token_strings: List of spell-text tokens (e.g. ["sil'a", "kor'ae"])
        tongue_code: Tongue code ('ko', 'av', 'ru', 'ca', 'um', 'dr')

    Returns:
        List of byte values (0–255)
    """
    from crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER

    t2b = SACRED_TONGUE_TOKENIZER.token_to_byte[tongue_code]
    return [t2b[t] for t in token_strings if t in t2b]


# ============================================================
# Full round-trip helper
# ============================================================


def seal(
    k_master: bytes,
    data: bytes,
    tongue: str,
    aad: Optional[Dict[str, str]] = None,
    modality: Modality = Modality.ADAPTIVE,
) -> str:
    """
    Encode raw bytes as a harmonic cipher envelope (JSON string).

    Each byte becomes a Sacred Tongue token in the specified tongue,
    then the full harmonic cipher is applied.

    Args:
        k_master: Master key
        data: Raw bytes to encode
        tongue: Sacred Tongue to use for byte encoding
        aad: Additional authenticated data
        modality: Overtone mask

    Returns:
        JSON-serialized envelope string
    """
    token_ids = list(data)  # byte values 0–255 directly as IDs

    if aad is None:
        aad = {}
    # Embed n_tokens in aad so verifier knows payload length
    aad = {**aad, "n_tokens": str(len(token_ids)), "payload_enc": "xor"}

    # Fresh nonce for this seal call
    nonce = os.urandom(12)
    nonce_b64 = base64.urlsafe_b64encode(nonce).decode()
    k_msg = derive_message_key(k_master, nonce)

    # Feistel-permute token IDs
    permuted = feistel_permute(token_ids, k_msg)

    # XOR-mask permuted bytes so payload is not plaintext token IDs.
    # Audio synthesis is NOT stored here — it's computed on demand in verify.
    xor_stream = _payload_xor_stream(k_msg, max(len(permuted), 1))
    masked = bytes(p ^ xor_stream[i] for i, p in enumerate(permuted)) if permuted else b""
    payload_b64 = base64.urlsafe_b64encode(masked).decode()

    ts = int(time.time() * 1000)
    envelope = HarmonicEnvelope(
        ver="3",
        tongue=tongue,
        aad=aad,
        ts=ts,
        nonce_b64=nonce_b64,
        kid="master",
        mode=modality.value,
        payload_b64=payload_b64,
        sig="",
    )
    canonical = _canonical_string(envelope)
    envelope.sig = hmac_mod.new(k_master, canonical.encode(), hashlib.sha256).hexdigest()
    return json.dumps(envelope_to_dict(envelope))


def unseal(k_master: bytes, envelope_json: str, harmonic_check: bool = True) -> VerificationResult:
    """
    Verify and decode a harmonic cipher envelope.

    Args:
        k_master: Master key
        envelope_json: JSON string from seal()
        harmonic_check: Run harmonic integrity check

    Returns:
        VerificationResult — token_ids contain recovered byte values
    """
    d = json.loads(envelope_json)
    env = envelope_from_dict(d)
    return verify_envelope(env, k_master, harmonic_check=harmonic_check)
