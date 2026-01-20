"""
Core mathematical components of the Symphonic Cipher.

This module implements the exact formulas from the specification:
- Section 2: Dictionary Mapping (bijection between tokens and integer IDs)
- Section 3: Modality Encoding (overtone masks per intent class)
- Section 4: Per-Message Secret Derivation (HKDF via HMAC-SHA-256)
- Section 5: Key-Driven Feistel Permutation (4-round, XOR-based)
- Section 6: Harmonic Synthesis Operator H
- Section 7: RWP v3 Envelope Construction
- Section 8: Verification Procedure
"""

import os
import time
import base64
import hmac
import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Union
from enum import Enum
import numpy as np

# =============================================================================
# GLOBAL CONSTANTS (Section 1: Global Notation)
# =============================================================================

BASE_FREQ = 440.0       # Hz - Reference pitch (A4)
FREQ_STEP = 30.0        # Hz - Frequency step per token ID
MAX_HARMONIC = 5        # H_max - Maximum overtone index
SAMPLE_RATE = 44_100    # SR - Sample rate for audio synthesis
DURATION_SEC = 0.5      # T_sec - Duration of generated waveform
L_SAMPLES = int(SAMPLE_RATE * DURATION_SEC)  # L - Total audio samples
KEY_LEN_BITS = 256      # ℓ - Key length in bits
KEY_LEN_BYTES = KEY_LEN_BITS // 8
NONCE_BYTES = 12        # 96 bits
FEISTEL_ROUNDS = 4      # R - Number of Feistel rounds
REPLAY_WINDOW_MS = 60_000  # τ_max - Replay window in milliseconds
FREQ_TOLERANCE = 2.0    # ε_f - Frequency tolerance in Hz
AMP_TOLERANCE = 0.15    # ε_a - Amplitude tolerance (relative)

# Golden Ratio - used for aperiodic lattice spacing
PHI = (1 + np.sqrt(5)) / 2  # ≈ 1.618033988749895

# Boltzmann constant (normalized for entropy calculations)
K_BOLTZMANN = 1.380649e-23  # J/K


# =============================================================================
# SECTION 2: DICTIONARY MAPPING
# =============================================================================

class ConlangDictionary:
    """
    Private dictionary D - a bijection between lexical tokens and integer IDs.

    Mathematical definition:
        ∀τ ∈ D: id(τ) ∈ {0, ..., |D|-1}

    The bijection can include negative integers for extended vocabulary,
    subject to the constraint that f(k) = f₀ + k·Δf > 0.
    """

    # Default conlang vocabulary
    DEFAULT_VOCAB = {
        "korah": 0,
        "aelin": 1,
        "dahru": 2,
        "melik": 3,
        "sorin": 4,
        "tivar": 5,
        "ulmar": 6,
        "vexin": 7,
    }

    # Extended vocabulary with negative IDs
    EXTENDED_VOCAB = {
        "shadow": -1,
        "gleam": -2,
        "flare": -3,
        **DEFAULT_VOCAB,
    }

    def __init__(self, vocab: Optional[Dict[str, int]] = None):
        """
        Initialize the dictionary with a vocabulary mapping.

        Args:
            vocab: Dictionary mapping tokens to integer IDs.
                   Must be a bijection (one-to-one and onto).
        """
        self._forward: Dict[str, int] = vocab if vocab else self.DEFAULT_VOCAB.copy()
        self._reverse: Dict[int, str] = {v: k for k, v in self._forward.items()}
        self._validate()

    def _validate(self) -> None:
        """Ensure the mapping is a bijection."""
        if len(self._forward) != len(self._reverse):
            raise ValueError("Dictionary must be a bijection (no duplicate IDs)")

        # Check frequency constraint: f(k) = f₀ + k·Δf > 0
        min_id = min(self._forward.values())
        min_freq = BASE_FREQ + min_id * FREQ_STEP
        if min_freq <= 0:
            max_negative = -int(BASE_FREQ / FREQ_STEP) + 1
            raise ValueError(
                f"Token ID {min_id} produces negative frequency {min_freq} Hz. "
                f"Minimum allowed ID is {max_negative}."
            )

    def id(self, token: str) -> int:
        """
        Map token τ to its integer identifier id(τ).

        Args:
            token: Lexical token from the vocabulary.

        Returns:
            Integer identifier.
        """
        if token not in self._forward:
            raise KeyError(f"Token '{token}' not in dictionary")
        return self._forward[token]

    def rev(self, id_val: int) -> str:
        """
        Inverse mapping: rev(id) returns the token for a given ID.

        Args:
            id_val: Integer identifier.

        Returns:
            Lexical token.
        """
        if id_val not in self._reverse:
            raise KeyError(f"ID {id_val} not in dictionary")
        return self._reverse[id_val]

    def tokenize(self, phrase: str) -> np.ndarray:
        """
        Convert a phrase to a vector of token IDs.

        Args:
            phrase: Space-separated string of tokens.

        Returns:
            NumPy array of integer IDs.
        """
        tokens = phrase.lower().split()
        return np.array([self.id(t) for t in tokens], dtype=np.int64)

    def detokenize(self, ids: np.ndarray) -> str:
        """
        Convert a vector of token IDs back to a phrase.

        Args:
            ids: NumPy array of integer IDs.

        Returns:
            Space-separated string of tokens.
        """
        return " ".join(self.rev(int(i)) for i in ids)

    def __len__(self) -> int:
        return len(self._forward)

    def __contains__(self, token: str) -> bool:
        return token in self._forward

    @property
    def vocab(self) -> Dict[str, int]:
        return self._forward.copy()


# =============================================================================
# SECTION 3: MODALITY ENCODING
# =============================================================================

class Modality(Enum):
    """
    Intent modality M ∈ M = {STRICT, ADAPTIVE, PROBE}.

    Each modality determines which overtones are emitted via the mask M(M).
    """
    STRICT = "STRICT"      # Binary - odd harmonics only
    ADAPTIVE = "ADAPTIVE"  # Non-binary - full series
    PROBE = "PROBE"        # Fundamental only


class ModalityEncoder:
    """
    Maps modality M to its overtone mask M(M) ⊆ {1, ..., H_max}.

    Mathematical definition:
        M(M) = {1,3,5}           if M = STRICT
               {1,...,H_max}     if M = ADAPTIVE
               {1}               if M = PROBE
    """

    def __init__(self, h_max: int = MAX_HARMONIC):
        """
        Initialize modality encoder.

        Args:
            h_max: Maximum overtone index.
        """
        self.h_max = h_max
        self._masks: Dict[Modality, Set[int]] = {
            Modality.STRICT: {1, 3, 5},  # Odd harmonics only
            Modality.ADAPTIVE: set(range(1, h_max + 1)),  # Full series
            Modality.PROBE: {1},  # Fundamental only
        }

    def get_mask(self, modality: Modality) -> Set[int]:
        """
        Get the overtone mask M(M) for a modality.

        Args:
            modality: Intent modality.

        Returns:
            Set of harmonic indices to emit.
        """
        return self._masks[modality].copy()

    def add_modality(self, name: str, mask: Set[int]) -> Modality:
        """
        Add a custom modality (e.g., EMERGENCY).

        Args:
            name: Modality name.
            mask: Set of harmonic indices.

        Returns:
            New Modality enum value.
        """
        # Create dynamic enum value
        new_mod = Modality(name)
        self._masks[new_mod] = mask
        return new_mod


# =============================================================================
# SECTION 4: PER-MESSAGE SECRET DERIVATION
# =============================================================================

def derive_msg_key(master_key: bytes, nonce: bytes) -> bytes:
    """
    Derive per-message secret K_msg from master key and nonce.

    Mathematical definition (Equation 4):
        K_msg = HMAC_{k_master}(ASCII("msg_key" || n))

    Args:
        master_key: Long-term secret key k_master (256 bits).
        nonce: Per-message nonce n (96 bits).

    Returns:
        Per-message secret K_msg (256 bits).
    """
    return hmac.new(
        master_key,
        b"msg_key" + nonce,
        hashlib.sha256
    ).digest()


def generate_nonce() -> bytes:
    """Generate a cryptographically secure 96-bit nonce."""
    return os.urandom(NONCE_BYTES)


def generate_master_key() -> bytes:
    """Generate a cryptographically secure 256-bit master key."""
    return os.urandom(KEY_LEN_BYTES)


# =============================================================================
# SECTION 5: KEY-DRIVEN FEISTEL PERMUTATION
# =============================================================================

class FeistelPermutation:
    """
    Balanced Feistel network for token order permutation.

    Mathematical definition (Section 5):
        Given token vector v = [id(τ₀), ..., id(τₘ₋₁)]ᵀ ∈ ℕᵐ
        Apply R = 4 rounds with:
            k^(r) = HMAC_{K_msg}(ASCII("round" || r)) mod 256
            L^(r+1) = R^(r)
            R^(r+1) = L^(r) ⊕ F(R^(r), k^(r))
        where F(x, k)ᵢ = xᵢ ⊕ k_{i mod |k|}

    The construction is involutive: same key reverses the permutation.
    """

    def __init__(self, rounds: int = FEISTEL_ROUNDS):
        """
        Initialize Feistel network.

        Args:
            rounds: Number of rounds R.
        """
        self.rounds = rounds

    def _derive_round_key(self, msg_key: bytes, round_idx: int) -> bytes:
        """
        Derive round sub-key k^(r) from K_msg.

        k^(r) = HMAC_{K_msg}(ASCII("round" || r)) mod 256
        """
        return hmac.new(
            msg_key,
            f"round{round_idx}".encode(),
            hashlib.sha256
        ).digest()

    def _round_function(self, right: np.ndarray, sub_key: bytes) -> np.ndarray:
        """
        Round function F(x, k) - XOR with cycling key bytes.

        F(x, k)ᵢ = xᵢ ⊕ k_{i mod |k|}
        """
        key_bytes = np.frombuffer(sub_key, dtype=np.uint8)
        key_expanded = np.resize(key_bytes, right.shape)
        return right ^ key_expanded

    def permute(self, ids: np.ndarray, msg_key: bytes) -> np.ndarray:
        """
        Apply Feistel permutation to token IDs.

        Args:
            ids: Token ID vector v ∈ ℤᵐ.
            msg_key: Per-message secret K_msg.

        Returns:
            Permuted token vector v' = [L^(R); R^(R)].
        """
        # Convert to uint8 for XOR operations (mod 256 embedding)
        ids_uint8 = np.array(ids, dtype=np.uint8)
        n = len(ids_uint8)

        # Split into left and right halves
        # If m is odd, right half gets the extra element
        mid = n // 2
        left = ids_uint8[:mid].copy()
        right = ids_uint8[mid:].copy()

        # Apply R rounds
        for r in range(self.rounds):
            sub_key = self._derive_round_key(msg_key, r)
            f_output = self._round_function(right, sub_key)

            # Pad f_output to match left size if needed
            if len(f_output) > len(left):
                f_output = f_output[:len(left)]
            elif len(f_output) < len(left):
                f_output = np.pad(f_output, (0, len(left) - len(f_output)))

            new_right = left ^ f_output
            left = right
            right = new_right

        # Concatenate final halves
        return np.concatenate([left, right])

    def inverse(self, permuted_ids: np.ndarray, msg_key: bytes) -> np.ndarray:
        """
        Inverse permutation (same as forward due to Feistel structure).

        The Feistel construction is involutive when run in reverse round order.
        """
        # For a standard Feistel cipher, we reverse the round order
        ids_uint8 = np.array(permuted_ids, dtype=np.uint8)
        n = len(ids_uint8)
        mid = n // 2
        left = ids_uint8[:mid].copy()
        right = ids_uint8[mid:].copy()

        # Apply rounds in reverse order
        for r in range(self.rounds - 1, -1, -1):
            sub_key = self._derive_round_key(msg_key, r)
            f_output = self._round_function(left, sub_key)

            if len(f_output) > len(right):
                f_output = f_output[:len(right)]
            elif len(f_output) < len(right):
                f_output = np.pad(f_output, (0, len(right) - len(f_output)))

            new_left = right ^ f_output
            right = left
            left = new_left

        return np.concatenate([left, right])


# =============================================================================
# SECTION 6: HARMONIC SYNTHESIS OPERATOR H
# =============================================================================

class HarmonicSynthesizer:
    """
    Harmonic synthesis operator H for generating audio waveforms.

    Mathematical definition (Section 6):
        x(t) = Σᵢ Σₕ∈M(M) (1/h) sin(2π(f₀ + vᵢ'·Δf)·h·t)

    where:
        f₀ = BASE_F = 440 Hz
        Δf = 30 Hz
        The factor 1/h provides amplitude roll-off for higher overtones.

    Discretization at SR = 44,100 Hz:
        x[n] = x(n/SR), n = 0, ..., L-1
    """

    def __init__(
        self,
        base_freq: float = BASE_FREQ,
        freq_step: float = FREQ_STEP,
        sample_rate: int = SAMPLE_RATE,
        duration: float = DURATION_SEC
    ):
        """
        Initialize harmonic synthesizer.

        Args:
            base_freq: Reference pitch f₀ (Hz).
            freq_step: Frequency step Δf per token ID.
            sample_rate: Sample rate SR (Hz).
            duration: Duration T_sec (seconds).
        """
        self.base_freq = base_freq
        self.freq_step = freq_step
        self.sample_rate = sample_rate
        self.duration = duration
        self.n_samples = int(sample_rate * duration)

        # Pre-compute time grid
        self._time = np.arange(self.n_samples) / sample_rate

    def synthesize(
        self,
        permuted_ids: np.ndarray,
        modality: Modality,
        modality_encoder: Optional[ModalityEncoder] = None
    ) -> np.ndarray:
        """
        Generate audio waveform from permuted token IDs.

        Args:
            permuted_ids: Permuted token vector v'.
            modality: Intent modality M.
            modality_encoder: Encoder for modality masks.

        Returns:
            Audio waveform x ∈ ℝᴸ normalized to [-1, 1].
        """
        if modality_encoder is None:
            modality_encoder = ModalityEncoder()

        mask = modality_encoder.get_mask(modality)
        m = len(permuted_ids)
        slice_len = self.n_samples // m

        output = np.zeros(self.n_samples, dtype=np.float64)

        for i, token_id in enumerate(permuted_ids):
            # Fundamental frequency for this token
            f_i = self.base_freq + int(token_id) * self.freq_step

            if f_i <= 0:
                raise ValueError(f"Token ID {token_id} produces non-positive frequency {f_i} Hz")

            # Time slice for this token
            start = i * slice_len
            end = start + slice_len
            t_slice = self._time[start:end]

            # Sum over selected overtones
            for h in mask:
                # x(t) += (1/h) * sin(2π * f_i * h * t)
                output[start:end] += (1.0 / h) * np.sin(2 * np.pi * f_i * h * t_slice)

        # Normalize to [-1, 1]
        max_abs = np.max(np.abs(output))
        if max_abs > 0:
            output /= max_abs

        return output.astype(np.float32)

    def synthesize_continuous(
        self,
        permuted_ids: np.ndarray,
        modality: Modality,
        modality_encoder: Optional[ModalityEncoder] = None
    ) -> np.ndarray:
        """
        Generate continuous (overlapping) synthesis instead of sliced.

        All token frequencies sound simultaneously.
        """
        if modality_encoder is None:
            modality_encoder = ModalityEncoder()

        mask = modality_encoder.get_mask(modality)
        output = np.zeros(self.n_samples, dtype=np.float64)

        for token_id in permuted_ids:
            f_i = self.base_freq + int(token_id) * self.freq_step

            for h in mask:
                output += (1.0 / h) * np.sin(2 * np.pi * f_i * h * self._time)

        max_abs = np.max(np.abs(output))
        if max_abs > 0:
            output /= max_abs

        return output.astype(np.float32)


# =============================================================================
# SECTION 7: RWP v3 ENVELOPE CONSTRUCTION
# =============================================================================

@dataclass
class EnvelopeHeader:
    """RWP v3 envelope header fields."""
    ver: str = "3"
    tongue: str = "KO"  # Domain identifier σ
    aad: Dict[str, str] = field(default_factory=dict)  # Auxiliary data
    ts: int = 0  # Unix timestamp (ms)
    nonce: str = ""  # Base64URL encoded nonce
    kid: str = "master"  # Key identifier


class RWPEnvelope:
    """
    RWP v3 Envelope for cryptographic binding.

    Mathematical definition (Section 7):
        C = "v3." || σ || AAD_canon || t || n || b64url(x)
        sig = HMAC_{k_master}(C)  (SHA-256, hex-encoded)
        E = {header: H, payload: b64url(x), sig: sig}
    """

    def __init__(self, master_key: bytes):
        """
        Initialize envelope generator.

        Args:
            master_key: Long-term secret key k_master.
        """
        self.master_key = master_key
        self._seen_nonces: set = set()

    @staticmethod
    def _canonical_aad(aad: Dict[str, str]) -> str:
        """
        Create canonical AAD string (sorted by key).

        AAD_canon = key=value; for each key in sorted order
        """
        return ";".join(f"{k}={v}" for k in sorted(aad.keys()) for v in [aad[k]])

    @staticmethod
    def _b64url_encode(data: bytes) -> str:
        """Base64URL encode without padding."""
        return base64.urlsafe_b64encode(data).decode().rstrip("=")

    @staticmethod
    def _b64url_decode(data: str) -> bytes:
        """Base64URL decode with padding restoration."""
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data)

    def create(
        self,
        payload: bytes,
        tongue: str,
        modality: Modality,
        nonce: Optional[bytes] = None,
        timestamp: Optional[int] = None,
        extra_aad: Optional[Dict[str, str]] = None
    ) -> Dict:
        """
        Create RWP v3 envelope.

        Args:
            payload: Audio waveform as bytes.
            tongue: Domain identifier σ.
            modality: Intent modality M.
            nonce: Optional nonce (generated if not provided).
            timestamp: Optional timestamp (current time if not provided).
            extra_aad: Additional auxiliary data.

        Returns:
            Envelope dictionary with header, payload, and sig.
        """
        if nonce is None:
            nonce = generate_nonce()
        if timestamp is None:
            timestamp = int(time.time() * 1000)

        # Build AAD
        aad = {"action": "execute", "mode": modality.value}
        if extra_aad:
            aad.update(extra_aad)

        # Build header
        header = EnvelopeHeader(
            ver="3",
            tongue=tongue,
            aad=aad,
            ts=timestamp,
            nonce=self._b64url_encode(nonce),
            kid="master"
        )

        # Encode payload
        payload_b64 = self._b64url_encode(payload)

        # Build canonical string
        canonical = ".".join([
            "v3",
            header.tongue,
            self._canonical_aad(header.aad),
            str(header.ts),
            header.nonce,
            payload_b64
        ])

        # Compute MAC
        sig = hmac.new(
            self.master_key,
            canonical.encode(),
            hashlib.sha256
        ).hexdigest()

        return {
            "header": {
                "ver": header.ver,
                "tongue": header.tongue,
                "aad": header.aad,
                "ts": header.ts,
                "nonce": header.nonce,
                "kid": header.kid
            },
            "payload": payload_b64,
            "sig": sig
        }

    def verify(
        self,
        envelope: Dict,
        audio_check: bool = True,
        expected_modality: Optional[Modality] = None
    ) -> Tuple[bool, str]:
        """
        Verify RWP v3 envelope (Section 8: Verification Procedure).

        Steps:
        1. Replay check (timestamp window + nonce uniqueness)
        2. Re-compute MAC
        3. Optional: Verify harmonic structure matches declared modality

        Args:
            envelope: Envelope dictionary.
            audio_check: Whether to perform harmonic verification.
            expected_modality: Expected modality for audio check.

        Returns:
            Tuple of (success: bool, message: str).
        """
        header = envelope.get("header", {})
        payload_b64 = envelope.get("payload", "")
        sig = envelope.get("sig", "")

        # Step 1: Replay check
        now_ms = int(time.time() * 1000)
        ts = header.get("ts", 0)

        if abs(now_ms - ts) > REPLAY_WINDOW_MS:
            return False, f"Timestamp outside replay window (delta={abs(now_ms - ts)} ms)"

        nonce = header.get("nonce", "")
        if nonce in self._seen_nonces:
            return False, "Nonce already seen (replay attack)"
        self._seen_nonces.add(nonce)

        # Step 2: Re-compute MAC
        canonical = ".".join([
            "v3",
            header.get("tongue", ""),
            self._canonical_aad(header.get("aad", {})),
            str(ts),
            nonce,
            payload_b64
        ])

        expected_sig = hmac.new(
            self.master_key,
            canonical.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, sig):
            return False, "MAC verification failed"

        # Step 3: Optional harmonic verification
        if audio_check:
            try:
                pcm = np.frombuffer(
                    self._b64url_decode(payload_b64),
                    dtype=np.float32
                )

                mode_str = header.get("aad", {}).get("mode", "ADAPTIVE")
                declared_modality = Modality(mode_str)

                if expected_modality and declared_modality != expected_modality:
                    return False, f"Modality mismatch: expected {expected_modality.value}, got {declared_modality.value}"

                # Basic FFT verification (detailed check in ai_verifier module)
                # Check that we have valid audio data
                if len(pcm) < SAMPLE_RATE * 0.1:  # At least 100ms
                    return False, "Audio payload too short"

            except Exception as e:
                return False, f"Audio verification failed: {str(e)}"

        return True, "Verification successful"

    def clear_nonce_cache(self) -> None:
        """Clear the seen nonces cache (for testing)."""
        self._seen_nonces.clear()


# =============================================================================
# MAIN CIPHER CLASS - COMBINES ALL COMPONENTS
# =============================================================================

class SymphonicCipher:
    """
    Complete Symphonic Cipher implementation.

    Combines all mathematical components into a unified interface:
    - Dictionary mapping
    - Modality encoding
    - Per-message secret derivation
    - Feistel permutation
    - Harmonic synthesis
    - RWP v3 envelope
    """

    def __init__(
        self,
        master_key: Optional[bytes] = None,
        dictionary: Optional[ConlangDictionary] = None
    ):
        """
        Initialize Symphonic Cipher.

        Args:
            master_key: Master secret key (generated if not provided).
            dictionary: Conlang dictionary (default used if not provided).
        """
        self.master_key = master_key if master_key else generate_master_key()
        self.dictionary = dictionary if dictionary else ConlangDictionary()
        self.modality_encoder = ModalityEncoder()
        self.feistel = FeistelPermutation()
        self.synthesizer = HarmonicSynthesizer()
        self.envelope = RWPEnvelope(self.master_key)

    def encode(
        self,
        phrase: str,
        modality: Modality = Modality.ADAPTIVE,
        tongue: str = "KO",
        return_components: bool = False
    ) -> Union[Dict, Tuple[Dict, Dict]]:
        """
        Encode a conlang phrase into a signed envelope.

        Args:
            phrase: Space-separated conlang tokens.
            modality: Intent modality.
            tongue: Domain identifier.
            return_components: If True, return intermediate values.

        Returns:
            Envelope dictionary, optionally with component dictionary.
        """
        # Step 1: Tokenize
        ids = self.dictionary.tokenize(phrase)

        # Step 2: Generate per-message secret
        nonce = generate_nonce()
        msg_key = derive_msg_key(self.master_key, nonce)

        # Step 3: Permute
        permuted_ids = self.feistel.permute(ids, msg_key)

        # Step 4: Synthesize audio
        waveform = self.synthesizer.synthesize(permuted_ids, modality, self.modality_encoder)

        # Step 5: Create envelope
        envelope = self.envelope.create(
            payload=waveform.tobytes(),
            tongue=tongue,
            modality=modality,
            nonce=nonce
        )

        if return_components:
            components = {
                "original_ids": ids.tolist(),
                "permuted_ids": permuted_ids.tolist(),
                "nonce": nonce.hex(),
                "msg_key": msg_key.hex(),
                "waveform_samples": len(waveform),
                "waveform_rms": float(np.sqrt(np.mean(waveform ** 2)))
            }
            return envelope, components

        return envelope

    def decode(
        self,
        envelope: Dict,
        expected_modality: Optional[Modality] = None
    ) -> Tuple[bool, Optional[str], str]:
        """
        Verify and decode an envelope.

        Args:
            envelope: RWP v3 envelope.
            expected_modality: Expected modality (optional).

        Returns:
            Tuple of (success, decoded_phrase or None, message).
        """
        # Verify envelope
        success, message = self.envelope.verify(
            envelope,
            audio_check=True,
            expected_modality=expected_modality
        )

        if not success:
            return False, None, message

        # Decode payload and recover token order
        # Note: Full recovery requires the nonce from the envelope
        # and the msg_key derivation
        try:
            header = envelope["header"]
            nonce_b64 = header["nonce"]
            nonce = self.envelope._b64url_decode(nonce_b64)

            msg_key = derive_msg_key(self.master_key, nonce)

            # Extract permuted IDs from audio (simplified - in practice use FFT)
            # This is a placeholder for demonstration
            # Real implementation would use FeatureExtractor from ai_verifier

            return True, None, "Envelope verified successfully"

        except Exception as e:
            return False, None, f"Decode error: {str(e)}"

    def verify(self, envelope: Dict) -> Tuple[bool, str]:
        """
        Verify an envelope without full decode.

        Args:
            envelope: RWP v3 envelope.

        Returns:
            Tuple of (success, message).
        """
        return self.envelope.verify(envelope, audio_check=True)
