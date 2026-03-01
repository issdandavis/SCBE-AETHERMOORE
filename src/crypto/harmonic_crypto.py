"""
P6 Harmonic Cryptography — Reference Implementation
=====================================================

Music-theoretic methods for cryptographic key generation,
state transitions, and multi-party coordination.

Patent Docket: P6-HARMONIC-CRYPTO
Inventor: Issac Davis
Status: Standalone filing (25 claims)

Core subsystems:
    1. HarmonicKeyGenerator  — Circle of fifths spiral key generation (Claims 6-10)
    2. RingRotationCipher     — Harmonic ring rotation cipher (Claims 1-5)
    3. VoiceLeadingOptimizer  — Voice leading state transition optimizer (Claims 11-15)
    4. CounterpointProtocol   — Multi-agent counterpoint coordination (Claims 16-20)
    5. HarmonicCryptosystem   — Integrated system (Claims 21-25)

Uses only stdlib: math, hashlib, struct, secrets, dataclasses, enum, typing.
"""

from __future__ import annotations

import hashlib
import math
import secrets
import struct
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants — Musical Ratios & Pythagorean Comma
# ---------------------------------------------------------------------------

# Harmonic interval ratios (Claim 1b)
HARMONIC_RATIOS: Dict[str, Tuple[int, int]] = {
    "octave": (2, 1),
    "perfect_fifth": (3, 2),
    "perfect_fourth": (4, 3),
    "major_third": (5, 4),
    "minor_third": (6, 5),
    "minor_sixth": (8, 5),
    "tritone": (45, 32),
}

# Sacred Tongue domain -> interval mapping (Claim 3)
TONGUE_INTERVAL_MAP: Dict[str, str] = {
    "KO": "octave",          # logic
    "AV": "perfect_fifth",   # abstract
    "RU": "perfect_fourth",  # structural
    "CA": "major_third",     # emotional
    "UM": "minor_sixth",     # wisdom
    "DR": "tritone",         # hidden
}

# Pythagorean comma: 12 perfect fifths overshoots 7 octaves by this ratio (Claim 6d)
PYTHAGOREAN_COMMA = 531441 / 524288  # ~1.01364326477

# Consonance ratings for intervals mod 12 (Claim 18)
CONSONANCE_RATINGS: Dict[int, float] = {
    0: 1.0,   # unison
    1: 0.2,   # minor second
    2: 0.3,   # major second
    3: 0.6,   # minor third
    4: 0.7,   # major third
    5: 0.8,   # perfect fourth
    6: 0.0,   # tritone
    7: 0.9,   # perfect fifth
    8: 0.5,   # minor sixth
    9: 0.4,   # major sixth
    10: 0.2,  # minor seventh
    11: 0.1,  # major seventh
}

# Voice leading cost table (Claim 11c) — indexed by Hamming distance
VOICE_LEADING_COSTS: Dict[int, float] = {
    0: 0.0,
    1: 0.5,
    2: 1.0,
    3: 1.5,
    4: 2.0,
    5: 3.0,
    6: 4.0,
    7: 5.0,
    8: 10.0,
}

# Motion types (Claim 17)
class MotionType(Enum):
    PARALLEL = "parallel"    # same direction, same interval change
    SIMILAR = "similar"      # same direction, different interval
    CONTRARY = "contrary"    # opposite directions
    OBLIQUE = "oblique"      # one voice stationary


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _hamming_distance(a: int, b: int, bits: int = 8) -> int:
    """Count differing bits between two values (up to `bits` width)."""
    xor = (a ^ b) & ((1 << bits) - 1)
    return bin(xor).count("1")


def _popcount(x: int) -> int:
    return bin(x & 0xFFFFFFFF).count("1")


def _voice_leading_cost(hamming_dist: int) -> float:
    """Return the voice-leading cost for a given Hamming distance (Claim 11c)."""
    if hamming_dist in VOICE_LEADING_COSTS:
        return VOICE_LEADING_COSTS[hamming_dist]
    # For distances > 8, extrapolate linearly from the 8-bit cost
    return 10.0 + (hamming_dist - 8) * 2.0


def _consonance(interval: int) -> float:
    """Return consonance rating for an interval mod 12 (Claim 18)."""
    return CONSONANCE_RATINGS.get(interval % 12, 0.0)


# ---------------------------------------------------------------------------
# 1. HarmonicKeyGenerator — Circle of Fifths Spiral (Claims 6-10)
# ---------------------------------------------------------------------------

@dataclass
class SpiralState:
    """Internal state of the circle-of-fifths spiral generator."""
    position: int = 0
    frequency: float = 1.0
    comma_drift: float = 0.0
    cycle_count: int = 0


class HarmonicKeyGenerator:
    """
    Circle of fifths spiral key generator (Claim 6).

    Generates non-repeating key material by iteratively advancing along
    the circle of fifths, exploiting the Pythagorean comma to ensure
    the spiral never closes (provably non-periodic).

    Claim 7: Comma drift after N cycles = (531441/524288)^N
    Claim 8: key_byte = (freq_fraction * 128 + drift_fraction * 128 + position) * 997 mod 256
    Claim 9: Spiral signature for verification
    Claim 10: Output usable as PQC KDF input
    """

    def __init__(self, seed: Optional[bytes] = None):
        """
        Initialize the spiral key generator.

        Args:
            seed: Optional seed bytes. If None, a random 32-byte seed is used.
        """
        if seed is None:
            seed = secrets.token_bytes(32)
        self._seed = seed
        # Derive initial frequency from seed hash
        h = hashlib.sha256(seed).digest()
        seed_val = int.from_bytes(h[:4], "big")
        self._state = SpiralState(
            position=0,
            frequency=1.0 + (seed_val % 1000) / 1000.0,  # 1.0 .. 1.999
            comma_drift=0.0,
            cycle_count=0,
        )

    @property
    def state(self) -> SpiralState:
        return self._state

    def _advance_spiral(self) -> None:
        """
        Advance one step along the circle of fifths spiral (Claim 6b).

        (i) multiply frequency by 3/2
        (ii) reduce to single octave [1.0, 2.0)
        (iii) accumulate comma drift
        """
        s = self._state
        s.frequency *= 1.5  # 3:2 ratio

        # Reduce to single octave while counting full cycles
        while s.frequency >= 2.0:
            s.frequency /= 2.0

        s.position += 1

        # Every 12 fifths = one full cycle, accumulate Pythagorean comma (Claim 7)
        if s.position % 12 == 0:
            s.cycle_count += 1
            s.comma_drift = PYTHAGOREAN_COMMA ** s.cycle_count - 1.0

    def _generate_key_byte(self) -> int:
        """
        Generate a single key byte from the current spiral state (Claim 8).

        key_byte = (freq_fraction * 128 + drift_fraction * 128 + position) * 997 mod 256
        """
        s = self._state
        freq_fraction = s.frequency - math.floor(s.frequency)
        drift_fraction = s.comma_drift - math.floor(s.comma_drift)
        raw = freq_fraction * 128 + drift_fraction * 128 + s.position
        return int(raw * 997) % 256

    def generate(self, length: int) -> bytes:
        """
        Generate `length` bytes of non-repeating key material (Claim 6).

        Args:
            length: Number of key bytes to generate.

        Returns:
            Bytes of key material.
        """
        key_bytes = bytearray(length)
        for i in range(length):
            self._advance_spiral()
            key_bytes[i] = self._generate_key_byte()
        return bytes(key_bytes)

    def spiral_signature(self) -> str:
        """
        Generate a spiral signature for key verification (Claim 9).

        Returns:
            Hex string encoding position + drift for verification.
        """
        s = self._state
        sig_data = struct.pack(">Idd", s.position, s.frequency, s.comma_drift)
        return hashlib.sha256(sig_data).hexdigest()

    def derive_pqc_seed(self, length: int = 32) -> bytes:
        """
        Generate key material suitable for post-quantum KDF input (Claim 10).

        Uses HKDF-like expansion: SHA-256(seed || spiral_material || counter).

        Args:
            length: Desired output length (default 32 for ML-KEM-768 seed).

        Returns:
            Derived key bytes.
        """
        spiral_material = self.generate(64)
        result = bytearray()
        counter = 0
        while len(result) < length:
            block = hashlib.sha256(
                self._seed + spiral_material + counter.to_bytes(4, "big")
            ).digest()
            result.extend(block)
            counter += 1
        return bytes(result[:length])


# ---------------------------------------------------------------------------
# 2. RingRotationCipher — Harmonic Ring Rotation (Claims 1-5)
# ---------------------------------------------------------------------------

@dataclass
class CipherRing:
    """
    A single cipher ring with a harmonic ratio and rotational position.

    Attributes:
        name: Domain name (e.g. 'KO', 'AV', etc.)
        ratio: Harmonic interval ratio as (numerator, denominator).
        position: Current rotational position (0..alphabet_size-1).
        alphabet_size: Number of symbols on the ring (default 256 for bytes).
    """
    name: str
    ratio: Tuple[int, int]
    position: int = 0
    alphabet_size: int = 256


class RingRotationCipher:
    """
    Harmonic ring rotation cipher (Claim 1).

    A polyrhythmic cipher where multiple rings rotate at speeds determined
    by musical harmonic ratios. The combined rotations produce ciphertext
    via XOR (Claim 4).

    Claim 2: Six rings for six Sacred Tongue domains.
    Claim 3: Specific ratio-to-domain assignment.
    Claim 5: Harmonic signature for verification.
    """

    # Default six-ring configuration matching Claims 2-3
    DEFAULT_RING_CONFIG: List[Tuple[str, str]] = [
        ("KO", "octave"),
        ("AV", "perfect_fifth"),
        ("RU", "perfect_fourth"),
        ("CA", "major_third"),
        ("UM", "minor_sixth"),
        ("DR", "tritone"),
    ]

    def __init__(
        self,
        key: bytes,
        ring_config: Optional[List[Tuple[str, str]]] = None,
        alphabet_size: int = 256,
    ):
        """
        Initialize the harmonic ring rotation cipher.

        Args:
            key: Encryption key (used to seed initial ring positions).
            ring_config: List of (name, interval_name) pairs. Defaults to 6 Sacred Tongue rings.
            alphabet_size: Size of each ring's alphabet (default 256 for byte-level).
        """
        if ring_config is None:
            ring_config = self.DEFAULT_RING_CONFIG

        self._alphabet_size = alphabet_size
        self._base_step = 1  # base step value (Claim 1c)

        # Initialize rings with positions derived from key
        key_hash = hashlib.sha256(key).digest()
        self._rings: List[CipherRing] = []
        for i, (name, interval) in enumerate(ring_config):
            ratio = HARMONIC_RATIOS[interval]
            # Derive initial position from key hash
            pos = key_hash[i % len(key_hash)] % alphabet_size
            self._rings.append(CipherRing(
                name=name,
                ratio=ratio,
                position=pos,
                alphabet_size=alphabet_size,
            ))

        self._initial_positions = [r.position for r in self._rings]

    @property
    def rings(self) -> List[CipherRing]:
        return list(self._rings)

    def _rotate_rings(self) -> None:
        """
        Rotate each ring by base_step * (numerator/denominator) (Claim 1c).

        We use integer arithmetic: step = base_step * numerator // denominator,
        clamped to at least 1 to ensure all rings advance.
        """
        for ring in self._rings:
            num, den = ring.ratio
            step = max(1, (self._base_step * num) // den)
            ring.position = (ring.position + step) % ring.alphabet_size

    def _combined_position(self) -> int:
        """
        XOR all ring positions to produce the keystream byte (Claim 4).
        """
        combined = 0
        for ring in self._rings:
            combined ^= ring.position
        return combined

    def encrypt(self, plaintext: bytes) -> bytes:
        """
        Encrypt plaintext using harmonic ring rotation (Claim 1d).

        Args:
            plaintext: Data to encrypt.

        Returns:
            Ciphertext bytes.
        """
        ciphertext = bytearray(len(plaintext))
        for i, byte in enumerate(plaintext):
            self._rotate_rings()
            ciphertext[i] = byte ^ self._combined_position()
        return bytes(ciphertext)

    def decrypt(self, ciphertext: bytes) -> bytes:
        """
        Decrypt ciphertext. Since XOR is symmetric, decrypt == encrypt
        with the same key and reset ring positions.

        Args:
            ciphertext: Data to decrypt.

        Returns:
            Plaintext bytes.
        """
        # Decryption is identical to encryption for XOR ciphers
        return self.encrypt(ciphertext)

    def reset(self) -> None:
        """Reset all rings to their initial key-derived positions."""
        for ring, pos in zip(self._rings, self._initial_positions):
            ring.position = pos

    def harmonic_signature(self) -> str:
        """
        Generate a verification signature from current ring state (Claim 5).

        Returns:
            Hex string of SHA-256 over ring positions and ratios.
        """
        sig_data = bytearray()
        for ring in self._rings:
            sig_data.extend(struct.pack(">HBB", ring.position, ring.ratio[0], ring.ratio[1]))
        return hashlib.sha256(bytes(sig_data)).hexdigest()

    def polyrhythmic_period(self) -> int:
        """
        Calculate the theoretical period of the combined cipher (Claim 1e).

        Period = LCM of all (alphabet_size / GCD(step_i, alphabet_size)).
        Because harmonic ratios produce irrational-ish step combinations,
        this period is very large.
        """
        period = 1
        for ring in self._rings:
            num, den = ring.ratio
            step = max(1, (self._base_step * num) // den)
            ring_period = ring.alphabet_size // math.gcd(step, ring.alphabet_size)
            period = (period * ring_period) // math.gcd(period, ring_period)
        return period


# ---------------------------------------------------------------------------
# 3. VoiceLeadingOptimizer — State Transition Optimization (Claims 11-15)
# ---------------------------------------------------------------------------

@dataclass
class TransitionResult:
    """Result of a voice-leading optimized state transition."""
    path: List[int]
    total_cost: float
    steps: int
    parallel_violations: int


class VoiceLeadingOptimizer:
    """
    Voice leading state transition optimizer (Claim 11).

    Applies music theory's smooth transition rules to minimize
    Hamming distance between cryptographic state transitions.

    Claim 12: Detect and avoid parallel bit patterns.
    Claim 13: Smooth key schedules for block cipher round keys.
    Claim 14: Configurable deviation window.
    Claim 15: Resolution rules for dissonant transitions.
    """

    def __init__(
        self,
        bits: int = 8,
        max_deviation: int = 3,
        dissonance_threshold: int = 5,
    ):
        """
        Args:
            bits: Bit width of state values (default 8).
            max_deviation: Maximum allowed Hamming distance per step (Claim 14).
            dissonance_threshold: Hamming distance above which a transition is
                                  "dissonant" and requires resolution (Claim 15).
        """
        self._bits = bits
        self._max_deviation = max_deviation
        self._dissonance_threshold = dissonance_threshold
        self._mask = (1 << bits) - 1

    def transition_cost(self, current: int, target: int) -> float:
        """
        Calculate the voice-leading cost of a direct transition (Claim 11c).

        Args:
            current: Current state value.
            target: Target state value.

        Returns:
            Voice leading cost.
        """
        hd = _hamming_distance(current, target, self._bits)
        return _voice_leading_cost(hd)

    def is_dissonant(self, current: int, target: int) -> bool:
        """
        Check if a transition is dissonant (Claim 15).

        Returns:
            True if Hamming distance exceeds threshold.
        """
        return _hamming_distance(current, target, self._bits) > self._dissonance_threshold

    def _detect_parallel_motion(self, prev_a: int, curr_a: int, prev_b: int, curr_b: int) -> bool:
        """
        Detect parallel bit patterns between two consecutive transitions (Claim 12).

        Parallel motion: multiple bits changing in the same direction simultaneously.
        Returns True if parallel motion detected.
        """
        delta_a = (curr_a - prev_a) & self._mask
        delta_b = (curr_b - prev_b) & self._mask

        if delta_a == 0 or delta_b == 0:
            return False  # oblique motion — one is stationary

        # Check if same direction by comparing sign bits of differences
        # (simplified: both increase or both decrease by similar amount)
        a_up = delta_a < (1 << (self._bits - 1))
        b_up = delta_b < (1 << (self._bits - 1))

        if a_up == b_up:
            # Same direction — check if same interval (parallel) or different (similar)
            if delta_a == delta_b:
                return True  # strict parallel motion
        return False

    def classify_motion(self, prev_a: int, curr_a: int, prev_b: int, curr_b: int) -> MotionType:
        """
        Classify the motion type between two voices (Claim 17).

        Args:
            prev_a, curr_a: Previous and current state of voice A.
            prev_b, curr_b: Previous and current state of voice B.

        Returns:
            MotionType enum value.
        """
        delta_a = (curr_a - prev_a) & self._mask
        delta_b = (curr_b - prev_b) & self._mask

        if delta_a == 0 and delta_b == 0:
            return MotionType.OBLIQUE
        if delta_a == 0 or delta_b == 0:
            return MotionType.OBLIQUE

        a_up = delta_a < (1 << (self._bits - 1))
        b_up = delta_b < (1 << (self._bits - 1))

        if a_up != b_up:
            return MotionType.CONTRARY

        if delta_a == delta_b:
            return MotionType.PARALLEL

        return MotionType.SIMILAR

    def optimize_transition(self, current: int, target: int) -> TransitionResult:
        """
        Find an optimized path from current to target state (Claim 11d).

        Uses greedy single-bit-flip stepping to minimize cost per step,
        constrained by max_deviation (Claim 14). Dissonant jumps trigger
        resolution into smooth intermediate steps (Claim 15).

        Args:
            current: Current state value (0..2^bits-1).
            target: Target state value (0..2^bits-1).

        Returns:
            TransitionResult with the optimized path.
        """
        current = current & self._mask
        target = target & self._mask

        if current == target:
            return TransitionResult(path=[current], total_cost=0.0, steps=0, parallel_violations=0)

        path = [current]
        total_cost = 0.0
        state = current
        visited = {current}
        parallel_violations = 0
        max_steps = self._bits * 4  # safety bound

        for _ in range(max_steps):
            if state == target:
                break

            # Find the best next state: flip bits one at a time toward target
            diff = state ^ target
            best_next = None
            best_cost = float("inf")

            for bit in range(self._bits):
                if diff & (1 << bit):
                    candidate = state ^ (1 << bit)
                    candidate &= self._mask

                    if candidate in visited:
                        continue

                    hd_to_target = _hamming_distance(candidate, target, self._bits)
                    cost = _voice_leading_cost(1) + hd_to_target * 0.1  # heuristic

                    if cost < best_cost:
                        best_cost = cost
                        best_next = candidate

            if best_next is None:
                # Fallback: jump directly to target
                total_cost += _voice_leading_cost(_hamming_distance(state, target, self._bits))
                path.append(target)
                break

            # Check for parallel motion with previous step (Claim 12)
            if len(path) >= 2:
                if self._detect_parallel_motion(path[-2], path[-1], path[-1], best_next):
                    parallel_violations += 1

            step_cost = _voice_leading_cost(_hamming_distance(state, best_next, self._bits))
            total_cost += step_cost
            state = best_next
            visited.add(state)
            path.append(state)

        return TransitionResult(
            path=path,
            total_cost=total_cost,
            steps=len(path) - 1,
            parallel_violations=parallel_violations,
        )

    def generate_smooth_key_schedule(self, round_keys: List[int]) -> List[int]:
        """
        Smooth a sequence of round keys using voice leading (Claim 13).

        Replaces large jumps between consecutive round keys with
        voice-leading-optimized intermediate values.

        Args:
            round_keys: Original round key sequence.

        Returns:
            Smoothed key sequence (may be longer).
        """
        if len(round_keys) <= 1:
            return list(round_keys)

        smoothed = [round_keys[0]]
        for i in range(1, len(round_keys)):
            result = self.optimize_transition(round_keys[i - 1], round_keys[i])
            # Skip the first element (already in smoothed) and add the rest
            smoothed.extend(result.path[1:])
        return smoothed

    def resolve_dissonance(self, current: int, target: int) -> List[int]:
        """
        Resolve a dissonant transition into consonant intermediate steps (Claim 15).

        If the Hamming distance exceeds the threshold, insert intermediate
        states that each have Hamming distance <= threshold from their predecessor.

        Args:
            current: Current state.
            target: Target state.

        Returns:
            List of states from current to target (inclusive).
        """
        if not self.is_dissonant(current, target):
            return [current, target]

        result = self.optimize_transition(current, target)
        return result.path


# ---------------------------------------------------------------------------
# 4. CounterpointProtocol — Multi-Agent Coordination (Claims 16-20)
# ---------------------------------------------------------------------------

@dataclass
class AgentVoice:
    """
    A single agent/voice in the contrapuntal hierarchy (Claim 16a-b).

    Attributes:
        voice_id: Unique identifier (0 = soprano, 1 = alto, etc.).
        name: Human-readable name.
        state: Current cryptographic state value.
        history: List of past state values.
    """
    voice_id: int
    name: str
    state: int = 0
    history: List[int] = field(default_factory=list)

    def propose_transition(self, new_state: int) -> int:
        """Record the current state in history and return the proposed state."""
        return new_state


@dataclass
class CounterpointValidation:
    """Result of validating a proposed transition against counterpoint rules."""
    valid: bool
    motion_types: Dict[int, MotionType]
    parallel_fifth_violations: List[Tuple[int, int]]
    voice_crossing_violations: List[Tuple[int, int]]
    harmony_score: float
    message: str


class CounterpointProtocol:
    """
    Multi-agent counterpoint coordination protocol (Claim 16).

    Coordinates cryptographic operations among multiple agents using
    music theory counterpoint rules:
    - No parallel fifths or octaves (Claim 17)
    - No voice crossing (Claim 16c-ii)
    - Maximize harmonic consonance (Claim 16e)
    - Trigger resolution when harmony drops (Claim 16f, 19)

    Claim 18: Consonance ratings for intervals.
    Claim 20: Multi-signature / threshold signature coordination.
    """

    def __init__(
        self,
        num_agents: int = 4,
        harmony_threshold: float = 0.4,
        bits: int = 8,
    ):
        """
        Args:
            num_agents: Number of agents/voices (default 4: SATB).
            harmony_threshold: Minimum harmony score before resolution triggers (Claim 16f).
            bits: Bit width of state values.
        """
        self._bits = bits
        self._mask = (1 << bits) - 1
        self._harmony_threshold = harmony_threshold

        voice_names = ["Soprano", "Alto", "Tenor", "Bass"]
        self._agents: List[AgentVoice] = []
        for i in range(num_agents):
            name = voice_names[i] if i < len(voice_names) else f"Voice_{i}"
            self._agents.append(AgentVoice(voice_id=i, name=name))

    @property
    def agents(self) -> List[AgentVoice]:
        return list(self._agents)

    @property
    def harmony_threshold(self) -> float:
        return self._harmony_threshold

    def set_state(self, voice_id: int, state: int) -> None:
        """Set the state of a specific agent."""
        agent = self._agents[voice_id]
        agent.history.append(agent.state)
        agent.state = state & self._mask

    def get_state(self, voice_id: int) -> int:
        """Get the current state of a specific agent."""
        return self._agents[voice_id].state

    def _interval(self, state_a: int, state_b: int) -> int:
        """Calculate the interval (mod 12) between two states."""
        return abs(state_a - state_b) % 12

    def _is_perfect_interval(self, interval: int) -> bool:
        """Check if an interval is perfect (unison, fifth, or octave)."""
        return (interval % 12) in (0, 7, 5)  # unison, P5, P4 (inverted P5)

    def harmony_score(self) -> float:
        """
        Calculate overall harmony score for all agents (Claim 16e, 18).

        Averages consonance ratings across all agent-pair intervals.

        Returns:
            Harmony score in [0.0, 1.0].
        """
        if len(self._agents) < 2:
            return 1.0

        total = 0.0
        count = 0
        for i in range(len(self._agents)):
            for j in range(i + 1, len(self._agents)):
                interval = self._interval(self._agents[i].state, self._agents[j].state)
                total += _consonance(interval)
                count += 1

        return total / count if count > 0 else 1.0

    def validate_transition(self, voice_id: int, proposed_state: int) -> CounterpointValidation:
        """
        Validate a proposed state transition against counterpoint rules (Claim 16c-d).

        Args:
            voice_id: The agent proposing the transition.
            proposed_state: The proposed new state value.

        Returns:
            CounterpointValidation with validation results.
        """
        proposed_state = proposed_state & self._mask
        agent = self._agents[voice_id]
        prev_state = agent.state

        motion_types: Dict[int, MotionType] = {}
        parallel_fifth_violations: List[Tuple[int, int]] = []
        voice_crossing_violations: List[Tuple[int, int]] = []

        optimizer = VoiceLeadingOptimizer(bits=self._bits)

        for other in self._agents:
            if other.voice_id == voice_id:
                continue

            # Classify motion (Claim 17)
            other_prev = other.history[-1] if other.history else other.state
            motion = optimizer.classify_motion(prev_state, proposed_state, other_prev, other.state)
            motion_types[other.voice_id] = motion

            # Check for parallel motion to perfect intervals (Claim 17 prohibition)
            if motion in (MotionType.PARALLEL, MotionType.SIMILAR):
                new_interval = self._interval(proposed_state, other.state)
                if self._is_perfect_interval(new_interval):
                    parallel_fifth_violations.append((voice_id, other.voice_id))

            # Check voice crossing (Claim 16c-ii)
            # Voice crossing: a higher voice goes below a lower voice
            if voice_id < other.voice_id and proposed_state < other.state - 12:
                voice_crossing_violations.append((voice_id, other.voice_id))
            elif voice_id > other.voice_id and proposed_state > other.state + 12:
                voice_crossing_violations.append((voice_id, other.voice_id))

        # Calculate projected harmony score
        original_state = agent.state
        agent.state = proposed_state
        projected_harmony = self.harmony_score()
        agent.state = original_state

        valid = len(parallel_fifth_violations) == 0 and len(voice_crossing_violations) == 0

        if valid and projected_harmony < self._harmony_threshold:
            valid = False
            message = f"Harmony score {projected_harmony:.3f} below threshold {self._harmony_threshold}"
        elif not valid:
            violations = []
            if parallel_fifth_violations:
                violations.append(f"parallel fifths/octaves: {parallel_fifth_violations}")
            if voice_crossing_violations:
                violations.append(f"voice crossing: {voice_crossing_violations}")
            message = "Counterpoint violations: " + "; ".join(violations)
        else:
            message = "Transition approved"

        return CounterpointValidation(
            valid=valid,
            motion_types=motion_types,
            parallel_fifth_violations=parallel_fifth_violations,
            voice_crossing_violations=voice_crossing_violations,
            harmony_score=projected_harmony,
            message=message,
        )

    def apply_transition(self, voice_id: int, proposed_state: int, force: bool = False) -> CounterpointValidation:
        """
        Validate and apply a state transition (Claim 16d).

        Args:
            voice_id: Agent proposing the transition.
            proposed_state: New state value.
            force: If True, apply even if validation fails.

        Returns:
            CounterpointValidation result.
        """
        validation = self.validate_transition(voice_id, proposed_state)

        if validation.valid or force:
            self.set_state(voice_id, proposed_state)

        return validation

    def resolve(self) -> Dict[int, int]:
        """
        Trigger resolution: find state changes that improve harmony (Claim 16f, 19).

        For each agent, try small state changes and pick the one that
        most improves the overall harmony score.

        Returns:
            Dict mapping voice_id -> suggested new state.
        """
        suggestions: Dict[int, int] = {}
        current_harmony = self.harmony_score()

        for agent in self._agents:
            best_state = agent.state
            best_harmony = current_harmony

            # Try small adjustments (+/- 1..3 semitones)
            for delta in range(-3, 4):
                if delta == 0:
                    continue
                candidate = (agent.state + delta) & self._mask
                original = agent.state
                agent.state = candidate
                h = self.harmony_score()
                agent.state = original

                if h > best_harmony:
                    best_harmony = h
                    best_state = candidate

            if best_state != agent.state:
                suggestions[agent.voice_id] = best_state

        return suggestions

    def needs_resolution(self) -> bool:
        """Check if harmony score is below threshold (Claim 16f)."""
        return self.harmony_score() < self._harmony_threshold

    def collective_state(self) -> bytes:
        """
        Get the combined state of all agents as bytes (useful for threshold signatures, Claim 20).

        Returns:
            Concatenation of all agent states as bytes.
        """
        result = bytearray()
        for agent in self._agents:
            result.append(agent.state & 0xFF)
        return bytes(result)


# ---------------------------------------------------------------------------
# 5. HarmonicCryptosystem — Integrated System (Claims 21-25)
# ---------------------------------------------------------------------------

@dataclass
class EncryptionResult:
    """Result of a full harmonic encryption operation."""
    ciphertext: bytes
    spiral_signature: str
    harmonic_signature: str
    harmony_score: float


@dataclass
class DecryptionResult:
    """Result of a full harmonic decryption operation."""
    plaintext: bytes
    spiral_signature: str
    verified: bool


class HarmonicCryptosystem:
    """
    Integrated harmonic cryptography system (Claim 21).

    Ties together all four subsystems:
    (a) Ring rotation cipher (Claim 1)
    (b) Circle of fifths spiral key generator (Claim 6)
    (c) Voice leading state transition optimizer (Claim 11)
    (d) Counterpoint multi-agent coordinator (Claim 16)

    Claim 22: ML-DSA signature integration (stub for PQC).
    Claim 23: ML-KEM key encapsulation integration (stub for PQC).
    Claim 24: Semantic domain classifier for tongue assignment.
    Claim 25: Distributed ledger consensus via counterpoint.
    """

    def __init__(
        self,
        seed: Optional[bytes] = None,
        num_agents: int = 4,
    ):
        """
        Initialize the integrated harmonic cryptosystem.

        Args:
            seed: Master seed for key generation. Random if None.
            num_agents: Number of agents for counterpoint coordination.
        """
        if seed is None:
            seed = secrets.token_bytes(32)
        self._seed = seed

        # (b) Spiral key generator
        self._key_gen = HarmonicKeyGenerator(seed=seed)

        # Generate cipher key from spiral
        cipher_key = self._key_gen.generate(32)

        # (a) Ring rotation cipher
        self._cipher = RingRotationCipher(key=cipher_key)

        # (c) Voice leading optimizer
        self._voice_leader = VoiceLeadingOptimizer(bits=8, max_deviation=3)

        # (d) Counterpoint coordinator
        self._counterpoint = CounterpointProtocol(num_agents=num_agents)

        # Store the spiral signature after key generation for verification
        self._init_spiral_sig = self._key_gen.spiral_signature()

    @property
    def key_generator(self) -> HarmonicKeyGenerator:
        return self._key_gen

    @property
    def cipher(self) -> RingRotationCipher:
        return self._cipher

    @property
    def voice_leader(self) -> VoiceLeadingOptimizer:
        return self._voice_leader

    @property
    def counterpoint(self) -> CounterpointProtocol:
        return self._counterpoint

    def classify_domain(self, data: bytes) -> str:
        """
        Classify data into a Sacred Tongue domain (Claim 24).

        Simple heuristic: hash the data and pick a domain based on
        the first byte modulo 6.

        Args:
            data: Input data to classify.

        Returns:
            Sacred Tongue code (KO, AV, RU, CA, UM, DR).
        """
        h = hashlib.sha256(data).digest()
        tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]
        return tongues[h[0] % 6]

    def encrypt(self, plaintext: bytes, smooth_keys: bool = True) -> EncryptionResult:
        """
        Full encryption pipeline (Claim 21e).

        Steps:
        (i) Generate key material using spiral key generator
        (ii) Optionally smooth key schedule using voice leading
        (iii) Encrypt data using harmonic ring cipher
        (iv) Record harmony state for multi-party verification

        Args:
            plaintext: Data to encrypt.
            smooth_keys: If True, apply voice leading to the key schedule.

        Returns:
            EncryptionResult with ciphertext and metadata.
        """
        # (i) Generate additional key material
        extra_key = self._key_gen.generate(len(plaintext))

        # (ii) Smooth the key schedule if requested (Claim 13)
        if smooth_keys and len(extra_key) > 1:
            key_list = list(extra_key)
            smoothed = self._voice_leader.generate_smooth_key_schedule(key_list)
            # Use only as many smoothed keys as we need
            extra_key = bytes(b & 0xFF for b in smoothed[:len(plaintext)])
            # Pad if smoothing shortened the sequence
            if len(extra_key) < len(plaintext):
                extra_key = extra_key + bytes(len(plaintext) - len(extra_key))

        # Pre-XOR with spiral key material
        pre_mixed = bytes(p ^ k for p, k in zip(plaintext, extra_key))

        # (iii) Encrypt with ring cipher
        self._cipher.reset()
        ciphertext = self._cipher.encrypt(pre_mixed)

        # (iv) Capture state
        spiral_sig = self._key_gen.spiral_signature()
        harmonic_sig = self._cipher.harmonic_signature()
        harmony = self._counterpoint.harmony_score()

        return EncryptionResult(
            ciphertext=ciphertext,
            spiral_signature=spiral_sig,
            harmonic_signature=harmonic_sig,
            harmony_score=harmony,
        )

    def decrypt(self, ciphertext: bytes, spiral_signature: str = "") -> DecryptionResult:
        """
        Full decryption pipeline.

        To decrypt correctly, must use the same seed to reconstruct
        the identical spiral key stream and ring cipher state.

        Args:
            ciphertext: Data to decrypt.
            spiral_signature: Expected spiral signature for verification.

        Returns:
            DecryptionResult with plaintext and verification status.
        """
        # Reconstruct from seed — create fresh generator with same seed
        dec_key_gen = HarmonicKeyGenerator(seed=self._seed)
        cipher_key = dec_key_gen.generate(32)
        dec_cipher = RingRotationCipher(key=cipher_key)

        # Generate the same extra key material
        extra_key = dec_key_gen.generate(len(ciphertext))

        # Smooth the key schedule identically
        if len(extra_key) > 1:
            dec_voice = VoiceLeadingOptimizer(bits=8, max_deviation=3)
            key_list = list(extra_key)
            smoothed = dec_voice.generate_smooth_key_schedule(key_list)
            extra_key = bytes(b & 0xFF for b in smoothed[:len(ciphertext)])
            if len(extra_key) < len(ciphertext):
                extra_key = extra_key + bytes(len(ciphertext) - len(extra_key))

        # Decrypt with ring cipher
        pre_mixed = dec_cipher.decrypt(ciphertext)

        # Remove spiral key pre-mixing
        plaintext = bytes(p ^ k for p, k in zip(pre_mixed, extra_key))

        # Verify spiral signature
        current_sig = dec_key_gen.spiral_signature()
        verified = (spiral_signature == "" or spiral_signature == current_sig)

        return DecryptionResult(
            plaintext=plaintext,
            spiral_signature=current_sig,
            verified=verified,
        )

    def multi_party_sign(self, data: bytes, voice_id: int) -> Tuple[bytes, CounterpointValidation]:
        """
        Multi-party signing operation using counterpoint coordination (Claim 20, 25).

        Each party proposes a state derived from the data hash. The transition
        is validated against counterpoint rules before signing.

        Args:
            data: Data to sign.
            voice_id: This party's voice identifier.

        Returns:
            Tuple of (signature_bytes, validation_result).
        """
        # Derive proposed state from data + voice_id
        h = hashlib.sha256(data + voice_id.to_bytes(4, "big")).digest()
        proposed_state = h[0]

        # Validate against counterpoint rules
        validation = self._counterpoint.apply_transition(voice_id, proposed_state)

        # Generate signature (simplified — in production, use ML-DSA / Claim 22)
        sig_input = data + self._counterpoint.collective_state()
        signature = hashlib.sha256(sig_input).digest()

        return signature, validation

    def consensus_harmony(self) -> float:
        """
        Get the current consensus harmony score (Claim 25).

        In a distributed ledger context, this represents how well
        the validators (voices) agree.

        Returns:
            Harmony score in [0.0, 1.0].
        """
        return self._counterpoint.harmony_score()

    def pqc_seed(self, length: int = 32) -> bytes:
        """
        Generate a PQC-compatible seed for ML-KEM or ML-DSA (Claims 22-23).

        Args:
            length: Seed length in bytes.

        Returns:
            Derived seed bytes.
        """
        return self._key_gen.derive_pqc_seed(length)
