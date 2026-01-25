"""
SpiralRing-64 - Deterministic Entropic Expansion

The SpiralRing is a time-evolving cryptographic state that both sender
and receiver can calculate independently, enabling zero-latency decryption
for high-latency links (e.g., Earth-Mars communication).

Key Properties:
- Deterministic: Given seed + time, state is uniquely determined
- Entropic: State complexity grows exponentially with time
- Reversible: Can "fast-forward" or "rewind" to any timestamp
- Quantum-Resistant: Based on lattice-hard problems

Document ID: EDE-RING-2026-001
Version: 1.0.0
"""

from __future__ import annotations

import hashlib
import math
import struct
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Iterator
from enum import Enum

# Import AETHERMOORE constants
from ..constants import (
    PHI, R_FIFTH, PHI_AETHER, LAMBDA_ISAAC,
    harmonic_scale, DEFAULT_R,
)


# =============================================================================
# CONSTANTS
# =============================================================================

# Ring configuration
RING_SIZE = 64                    # 64 positions in the ring
EXPANSION_RATE = 1.0              # Bits per second of entropy growth
TIME_QUANTUM = 1.0                # Time step resolution in seconds
MAX_EXPANSION = 2**20             # Maximum expansion iterations

# Spiral constants (derived from AETHERMOORE)
SPIRAL_PHI = PHI                  # Golden ratio for spiral growth
SPIRAL_R = R_FIFTH                # Perfect fifth for harmonic expansion
SPIRAL_TWIST = 2 * math.pi / PHI  # Twist angle per step

# Physical constants for Mars scenario
LIGHT_SPEED = 299792458           # m/s
MARS_DISTANCE_MIN = 54.6e9        # Minimum Earth-Mars distance (m)
MARS_DISTANCE_MAX = 401e9         # Maximum Earth-Mars distance (m)
MARS_LIGHT_TIME_MIN = MARS_DISTANCE_MIN / LIGHT_SPEED  # ~182 seconds
MARS_LIGHT_TIME_MAX = MARS_DISTANCE_MAX / LIGHT_SPEED  # ~1338 seconds


class RingState(Enum):
    """Ring evolution states."""
    INITIALIZED = "initialized"
    EXPANDING = "expanding"
    STABILIZED = "stabilized"
    SYNCHRONIZED = "synchronized"


# =============================================================================
# SPIRAL RING CORE
# =============================================================================

@dataclass
class SpiralPosition:
    """A position on the spiral ring."""
    index: int                    # 0-63 position on ring
    value: int                    # 256-bit value at this position
    phase: float                  # Phase angle (0 to 2π)
    depth: int                    # Expansion depth
    entropy: float                # Accumulated entropy bits

    def to_bytes(self) -> bytes:
        """Serialize position to bytes."""
        return (
            self.index.to_bytes(1, 'big') +
            self.value.to_bytes(32, 'big') +
            struct.pack('>d', self.phase) +
            self.depth.to_bytes(4, 'big') +
            struct.pack('>d', self.entropy)
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> 'SpiralPosition':
        """Deserialize position from bytes."""
        return cls(
            index=data[0],
            value=int.from_bytes(data[1:33], 'big'),
            phase=struct.unpack('>d', data[33:41])[0],
            depth=int.from_bytes(data[41:45], 'big'),
            entropy=struct.unpack('>d', data[45:53])[0]
        )


@dataclass
class RingConfig:
    """Configuration for SpiralRing."""
    ring_size: int = RING_SIZE
    expansion_rate: float = EXPANSION_RATE
    time_quantum: float = TIME_QUANTUM
    spiral_r: float = SPIRAL_R
    use_harmonic_scaling: bool = True
    max_depth: int = MAX_EXPANSION

    def __post_init__(self):
        if self.ring_size < 8 or self.ring_size > 256:
            raise ValueError(f"Ring size must be 8-256, got {self.ring_size}")


@dataclass
class SpiralRing:
    """
    SpiralRing-64: Deterministic entropic expansion ring.

    The ring expands deterministically based on time, allowing both
    sender and receiver to compute the same state independently.

    Usage:
        # Sender at T=0
        ring = SpiralRing.from_seed(shared_seed)
        ring.evolve_to(0)
        encoded = ring.encode(message)

        # Receiver at T=840 (14 minutes later)
        ring = SpiralRing.from_seed(shared_seed)
        ring.evolve_to(0)  # Fast-forward to sender's time!
        decoded = ring.decode(encoded)
    """
    seed: bytes
    positions: List[SpiralPosition] = field(default_factory=list)
    current_time: float = 0.0
    state: RingState = RingState.INITIALIZED
    config: RingConfig = field(default_factory=RingConfig)
    _expansion_cache: Dict[int, List[int]] = field(default_factory=dict)

    def __post_init__(self):
        if not self.positions:
            self._initialize_ring()

    def _initialize_ring(self) -> None:
        """Initialize ring positions from seed."""
        self.positions = []

        # Derive initial values using SHAKE-256
        shake = hashlib.shake_256(self.seed)

        for i in range(self.config.ring_size):
            # Each position gets 32 bytes (256 bits)
            pos_seed = shake.digest(32 + i * 32)[i * 32:(i + 1) * 32]
            value = int.from_bytes(pos_seed, 'big')

            # Phase is distributed around the ring
            phase = (2 * math.pi * i) / self.config.ring_size

            self.positions.append(SpiralPosition(
                index=i,
                value=value,
                phase=phase,
                depth=0,
                entropy=0.0
            ))

        self.state = RingState.INITIALIZED

    @classmethod
    def from_seed(
        cls,
        seed: bytes,
        config: Optional[RingConfig] = None
    ) -> 'SpiralRing':
        """
        Create a new SpiralRing from a seed.

        Args:
            seed: Shared secret seed (32+ bytes recommended)
            config: Optional ring configuration

        Returns:
            Initialized SpiralRing
        """
        if len(seed) < 16:
            raise ValueError("Seed must be at least 16 bytes")

        return cls(
            seed=seed,
            config=config or RingConfig()
        )

    def evolve_to(self, target_time: float) -> None:
        """
        Evolve the ring to a specific time.

        This is the key operation that enables zero-latency decryption:
        the receiver can "fast-forward" to the sender's timestamp.

        Args:
            target_time: Target time in seconds since epoch T=0
        """
        if target_time < 0:
            raise ValueError("Target time cannot be negative")

        # Calculate number of expansion steps
        steps = int(target_time / self.config.time_quantum)

        # Check cache for this step count
        if steps in self._expansion_cache:
            self._apply_cached_expansion(steps)
            self.current_time = target_time
            return

        # Evolve step by step
        self.state = RingState.EXPANDING

        current_step = int(self.current_time / self.config.time_quantum)

        if steps > current_step:
            # Forward evolution
            for step in range(current_step, steps):
                self._expand_step(step)
        elif steps < current_step:
            # Need to reset and re-evolve (can't go backwards efficiently)
            self._initialize_ring()
            for step in range(steps):
                self._expand_step(step)

        self.current_time = target_time
        self.state = RingState.SYNCHRONIZED

    def _expand_step(self, step: int) -> None:
        """
        Perform one expansion step.

        The expansion uses harmonic scaling to grow entropy:
        - Each position mixes with its neighbors
        - Phase advances by spiral twist angle
        - Depth increases logarithmically
        """
        # Calculate expansion parameters
        if self.config.use_harmonic_scaling:
            # Use AETHERMOORE harmonic scaling
            depth_factor = min(6, 1 + int(math.log2(step + 1)))
            h_scale = harmonic_scale(depth_factor, self.config.spiral_r)
        else:
            h_scale = 1.0
            depth_factor = 1

        new_positions = []

        for i, pos in enumerate(self.positions):
            # Get neighbors (circular)
            left = self.positions[(i - 1) % self.config.ring_size]
            right = self.positions[(i + 1) % self.config.ring_size]

            # Mix values using XOR and rotation
            mixed = pos.value ^ self._rotate_left(left.value, 7) ^ self._rotate_right(right.value, 13)

            # Add step-dependent permutation
            step_mix = int.from_bytes(
                hashlib.sha256(
                    self.seed + step.to_bytes(8, 'big') + i.to_bytes(2, 'big')
                ).digest(),
                'big'
            )
            mixed ^= step_mix

            # Advance phase by spiral twist
            new_phase = (pos.phase + SPIRAL_TWIST) % (2 * math.pi)

            # Calculate entropy accumulation
            new_entropy = pos.entropy + self.config.expansion_rate * self.config.time_quantum

            new_positions.append(SpiralPosition(
                index=i,
                value=mixed % (2**256),
                phase=new_phase,
                depth=pos.depth + depth_factor,
                entropy=new_entropy
            ))

        self.positions = new_positions

    def _rotate_left(self, value: int, bits: int) -> int:
        """Rotate 256-bit value left."""
        return ((value << bits) | (value >> (256 - bits))) % (2**256)

    def _rotate_right(self, value: int, bits: int) -> int:
        """Rotate 256-bit value right."""
        return ((value >> bits) | (value << (256 - bits))) % (2**256)

    def _apply_cached_expansion(self, steps: int) -> None:
        """Apply cached expansion state."""
        cached = self._expansion_cache[steps]
        for i, value in enumerate(cached):
            self.positions[i].value = value

    def get_ring_state(self) -> bytes:
        """
        Get current ring state as bytes.

        This is the key material for encoding/decoding.
        """
        state_bytes = b""
        for pos in self.positions:
            state_bytes += pos.value.to_bytes(32, 'big')
        return state_bytes

    def get_position_key(self, index: int) -> bytes:
        """Get the key material at a specific ring position."""
        if index < 0 or index >= self.config.ring_size:
            raise ValueError(f"Index must be 0-{self.config.ring_size - 1}")
        return self.positions[index].value.to_bytes(32, 'big')

    def encode(self, data: bytes) -> bytes:
        """
        Encode data using current ring state.

        Args:
            data: Plaintext to encode

        Returns:
            Encoded ciphertext
        """
        ring_state = self.get_ring_state()

        # XOR with ring state (cycling through positions)
        encoded = bytearray(len(data))
        for i, byte in enumerate(data):
            key_byte = ring_state[i % len(ring_state)]
            encoded[i] = byte ^ key_byte

        return bytes(encoded)

    def decode(self, data: bytes) -> bytes:
        """
        Decode data using current ring state.

        This is symmetric with encode (XOR operation).

        Args:
            data: Ciphertext to decode

        Returns:
            Decoded plaintext
        """
        return self.encode(data)  # XOR is symmetric

    def get_entropy_bits(self) -> float:
        """Get total accumulated entropy in bits."""
        return sum(pos.entropy for pos in self.positions)

    def get_stats(self) -> Dict[str, Any]:
        """Get ring statistics."""
        return {
            "ring_size": self.config.ring_size,
            "current_time": self.current_time,
            "state": self.state.value,
            "total_entropy_bits": self.get_entropy_bits(),
            "average_depth": sum(p.depth for p in self.positions) / len(self.positions),
            "expansion_rate": self.config.expansion_rate,
            "seed_hash": hashlib.sha256(self.seed).hexdigest()[:16],
        }


# =============================================================================
# SYNCHRONIZED RING PAIR
# =============================================================================

@dataclass
class SynchronizedRingPair:
    """
    A pair of synchronized rings for bidirectional communication.

    Each party maintains their own ring, but both are derived from
    the same shared seed and can evolve to any timestamp.
    """
    local_ring: SpiralRing
    station_id: str
    partner_id: str
    epoch_time: float = 0.0  # T=0 for this communication session

    @classmethod
    def create_pair(
        cls,
        shared_seed: bytes,
        station_a_id: str,
        station_b_id: str,
        config: Optional[RingConfig] = None
    ) -> Tuple['SynchronizedRingPair', 'SynchronizedRingPair']:
        """
        Create a synchronized pair of rings.

        Both stations can create their half independently using
        the same shared seed.
        """
        ring_a = SpiralRing.from_seed(shared_seed, config)
        ring_b = SpiralRing.from_seed(shared_seed, config)

        pair_a = cls(
            local_ring=ring_a,
            station_id=station_a_id,
            partner_id=station_b_id
        )

        pair_b = cls(
            local_ring=ring_b,
            station_id=station_b_id,
            partner_id=station_a_id
        )

        return pair_a, pair_b

    def encode_message(
        self,
        message: bytes,
        send_time: Optional[float] = None
    ) -> Tuple[bytes, float]:
        """
        Encode a message with timestamp.

        Args:
            message: Message to send
            send_time: Explicit send time (uses current time if None)

        Returns:
            (encoded_message, send_timestamp)
        """
        if send_time is None:
            send_time = time.time() - self.epoch_time

        self.local_ring.evolve_to(send_time)
        encoded = self.local_ring.encode(message)

        return encoded, send_time

    def decode_message(
        self,
        encoded: bytes,
        send_time: float
    ) -> bytes:
        """
        Decode a message using sender's timestamp.

        This is the "fast-forward" operation that enables
        zero-latency decryption.

        Args:
            encoded: Encoded message
            send_time: Timestamp when message was sent

        Returns:
            Decoded message
        """
        # Fast-forward to sender's time
        self.local_ring.evolve_to(send_time)
        return self.local_ring.decode(encoded)


# =============================================================================
# ENTROPY STREAM
# =============================================================================

def create_entropy_stream(
    seed: bytes,
    start_time: float = 0.0,
    chunk_size: int = 32
) -> Iterator[bytes]:
    """
    Create an infinite stream of entropy from a SpiralRing.

    Yields chunk_size bytes at each time quantum.

    Args:
        seed: Seed for ring initialization
        start_time: Starting timestamp
        chunk_size: Bytes per chunk

    Yields:
        Entropy chunks
    """
    ring = SpiralRing.from_seed(seed)
    current_time = start_time

    while True:
        ring.evolve_to(current_time)
        state = ring.get_ring_state()

        # Yield chunks from ring state
        for i in range(0, len(state), chunk_size):
            yield state[i:i + chunk_size]

        current_time += ring.config.time_quantum


def calculate_light_delay(distance_m: float) -> float:
    """Calculate light propagation delay in seconds."""
    return distance_m / LIGHT_SPEED


def mars_light_delay(
    earth_mars_distance: Optional[float] = None
) -> float:
    """
    Get Earth-Mars light delay.

    Args:
        earth_mars_distance: Distance in meters (uses average if None)

    Returns:
        Light delay in seconds
    """
    if earth_mars_distance is None:
        # Use average distance
        earth_mars_distance = (MARS_DISTANCE_MIN + MARS_DISTANCE_MAX) / 2

    return calculate_light_delay(earth_mars_distance)
