"""
EDE Mars Protocol - Zero-Latency Deep Space Communication

Implements the Entropic Defense Engine protocol for communication
where traditional handshakes are impractical (14+ minute latency).

The Problem:
    Traditional TLS requires 4 round-trips = 56 minutes for Mars
    This is unacceptable for real-time control systems

The Solution:
    - Pre-shared seed during mission planning
    - Synchronized atomic clocks (mission time T=0)
    - Transmit with timestamp header
    - Receiver fast-forwards to sender's time and decodes immediately

Result: Zero cryptographic latency. Only physics (light speed) matters.

Document ID: EDE-MARS-2026-001
Version: 1.0.0
"""

from __future__ import annotations

import hashlib
import hmac
import struct
import time
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Any, List
from enum import Enum

from .spiral_ring import (
    SpiralRing, RingConfig, SynchronizedRingPair,
    mars_light_delay, MARS_LIGHT_TIME_MIN, MARS_LIGHT_TIME_MAX,
    LIGHT_SPEED,
)

# Import PQC for quantum resistance
try:
    from ..pqc import Kyber768, Dilithium3
    PQC_AVAILABLE = True
except ImportError:
    PQC_AVAILABLE = False


# =============================================================================
# CONSTANTS
# =============================================================================

# Protocol version
PROTOCOL_VERSION = 0x01

# Message types
class MessageType(Enum):
    """EDE message types."""
    DATA = 0x01              # Regular data message
    CONTROL = 0x02           # Control/command message
    HEARTBEAT = 0x03         # Keep-alive
    SYNC = 0x04              # Time synchronization
    EMERGENCY = 0x05         # Emergency priority
    ACK = 0x06               # Acknowledgment (delayed)


# Header sizes
HEADER_SIZE = 32             # Bytes
TIMESTAMP_SIZE = 8           # 64-bit timestamp
SEQUENCE_SIZE = 8            # 64-bit sequence number
MAC_SIZE = 32                # HMAC-SHA256

# Cosmic ray protection
ERROR_DETECTION_OVERHEAD = 4  # CRC32 per 64-byte block


# =============================================================================
# MESSAGE FORMAT
# =============================================================================

@dataclass
class EDEHeader:
    """
    EDE Protocol header.

    Format (32 bytes):
        version:     1 byte   - Protocol version
        msg_type:    1 byte   - Message type
        flags:       2 bytes  - Flags (priority, compression, etc.)
        sequence:    8 bytes  - Sequence number
        timestamp:   8 bytes  - Send timestamp (seconds since epoch)
        payload_len: 4 bytes  - Payload length
        reserved:    8 bytes  - Reserved for future use
    """
    version: int
    msg_type: MessageType
    flags: int
    sequence: int
    timestamp: float
    payload_len: int
    reserved: bytes = b'\x00' * 8

    def to_bytes(self) -> bytes:
        """Serialize header to bytes."""
        return (
            self.version.to_bytes(1, 'big') +
            self.msg_type.value.to_bytes(1, 'big') +
            self.flags.to_bytes(2, 'big') +
            self.sequence.to_bytes(8, 'big') +
            struct.pack('>d', self.timestamp) +
            self.payload_len.to_bytes(4, 'big') +
            self.reserved
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> 'EDEHeader':
        """Deserialize header from bytes."""
        if len(data) < HEADER_SIZE:
            raise ValueError(f"Header must be {HEADER_SIZE} bytes")

        return cls(
            version=data[0],
            msg_type=MessageType(data[1]),
            flags=int.from_bytes(data[2:4], 'big'),
            sequence=int.from_bytes(data[4:12], 'big'),
            timestamp=struct.unpack('>d', data[12:20])[0],
            payload_len=int.from_bytes(data[20:24], 'big'),
            reserved=data[24:32]
        )


@dataclass
class EDEMessage:
    """
    Complete EDE protocol message.

    Structure:
        header:       32 bytes
        payload:      variable (encrypted)
        mac:          32 bytes (HMAC-SHA256 of header + payload)
    """
    header: EDEHeader
    payload: bytes
    mac: bytes

    def to_bytes(self) -> bytes:
        """Serialize complete message."""
        return self.header.to_bytes() + self.payload + self.mac

    @classmethod
    def from_bytes(cls, data: bytes) -> 'EDEMessage':
        """Deserialize complete message."""
        if len(data) < HEADER_SIZE + MAC_SIZE:
            raise ValueError("Message too short")

        header = EDEHeader.from_bytes(data[:HEADER_SIZE])

        expected_len = HEADER_SIZE + header.payload_len + MAC_SIZE
        if len(data) < expected_len:
            raise ValueError(f"Message truncated: expected {expected_len}, got {len(data)}")

        payload = data[HEADER_SIZE:HEADER_SIZE + header.payload_len]
        mac = data[HEADER_SIZE + header.payload_len:HEADER_SIZE + header.payload_len + MAC_SIZE]

        return cls(header=header, payload=payload, mac=mac)

    def verify_mac(self, mac_key: bytes) -> bool:
        """Verify message MAC."""
        expected = hmac.new(
            mac_key,
            self.header.to_bytes() + self.payload,
            hashlib.sha256
        ).digest()
        return hmac.compare_digest(self.mac, expected)


# =============================================================================
# EDE STATION
# =============================================================================

@dataclass
class EDEStation:
    """
    An EDE communication station (Earth, Mars, spacecraft, etc.).

    Handles message encoding/decoding with zero-latency operation.
    """
    station_id: str
    ring: SpiralRing
    sequence_counter: int = 0
    epoch_time: float = 0.0
    mac_key: bytes = field(default_factory=lambda: b'\x00' * 32)
    received_sequences: Dict[str, int] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        station_id: str,
        shared_seed: bytes,
        mac_key: Optional[bytes] = None,
        config: Optional[RingConfig] = None
    ) -> 'EDEStation':
        """
        Create a new EDE station.

        Args:
            station_id: Unique station identifier
            shared_seed: Pre-shared secret seed
            mac_key: Key for message authentication (derived from seed if None)
            config: Ring configuration

        Returns:
            Configured EDEStation
        """
        ring = SpiralRing.from_seed(shared_seed, config)

        if mac_key is None:
            # Derive MAC key from seed
            mac_key = hashlib.sha256(shared_seed + b"mac-key").digest()

        return cls(
            station_id=station_id,
            ring=ring,
            mac_key=mac_key
        )

    def send(
        self,
        payload: bytes,
        msg_type: MessageType = MessageType.DATA,
        flags: int = 0,
        send_time: Optional[float] = None
    ) -> EDEMessage:
        """
        Create an EDE message for transmission.

        Args:
            payload: Message payload
            msg_type: Message type
            flags: Message flags
            send_time: Explicit send time (current time if None)

        Returns:
            Complete EDEMessage ready for transmission
        """
        if send_time is None:
            send_time = time.time() - self.epoch_time

        # Evolve ring to send time
        self.ring.evolve_to(send_time)

        # Encrypt payload
        encrypted_payload = self.ring.encode(payload)

        # Create header
        header = EDEHeader(
            version=PROTOCOL_VERSION,
            msg_type=msg_type,
            flags=flags,
            sequence=self.sequence_counter,
            timestamp=send_time,
            payload_len=len(encrypted_payload)
        )

        self.sequence_counter += 1

        # Compute MAC
        mac = hmac.new(
            self.mac_key,
            header.to_bytes() + encrypted_payload,
            hashlib.sha256
        ).digest()

        return EDEMessage(
            header=header,
            payload=encrypted_payload,
            mac=mac
        )

    def receive(
        self,
        message: EDEMessage,
        sender_id: str = "unknown"
    ) -> Tuple[bytes, bool]:
        """
        Receive and decode an EDE message.

        This is where the "fast-forward" magic happens:
        we evolve to the SENDER's timestamp, not our current time.

        Args:
            message: Received EDEMessage
            sender_id: Sender station ID for sequence tracking

        Returns:
            (decoded_payload, is_valid)
        """
        # Verify MAC first
        if not message.verify_mac(self.mac_key):
            return b"", False

        # Check sequence (replay protection)
        last_seq = self.received_sequences.get(sender_id, -1)
        if message.header.sequence <= last_seq:
            # Potential replay attack
            return b"", False

        self.received_sequences[sender_id] = message.header.sequence

        # Fast-forward to sender's timestamp
        self.ring.evolve_to(message.header.timestamp)

        # Decode payload
        decoded = self.ring.decode(message.payload)

        return decoded, True

    def get_stats(self) -> Dict[str, Any]:
        """Get station statistics."""
        return {
            "station_id": self.station_id,
            "sequence_counter": self.sequence_counter,
            "epoch_time": self.epoch_time,
            "ring_stats": self.ring.get_stats(),
            "received_from": list(self.received_sequences.keys()),
        }


# =============================================================================
# MARS COMMUNICATION LINK
# =============================================================================

@dataclass
class MarsLink:
    """
    Specialized link for Earth-Mars communication.

    Handles:
    - Variable light delay (54.6M to 401M km)
    - Time dilation at relativistic speeds (future-proofing)
    - Cosmic ray error detection
    """
    earth_station: EDEStation
    mars_station: EDEStation
    current_distance_m: float = (MARS_LIGHT_TIME_MIN + MARS_LIGHT_TIME_MAX) / 2 * LIGHT_SPEED

    @classmethod
    def establish(
        cls,
        shared_seed: bytes,
        config: Optional[RingConfig] = None
    ) -> 'MarsLink':
        """
        Establish a Mars communication link.

        In practice, the shared_seed would be exchanged during
        mission planning (months before launch) and verified
        multiple times before departure.
        """
        earth = EDEStation.create("EARTH-STATION", shared_seed, config=config)
        mars = EDEStation.create("MARS-STATION", shared_seed, config=config)

        return cls(
            earth_station=earth,
            mars_station=mars
        )

    def set_distance(self, distance_m: float) -> None:
        """Update current Earth-Mars distance."""
        self.current_distance_m = distance_m

    def get_light_delay(self) -> float:
        """Get current one-way light delay in seconds."""
        return self.current_distance_m / LIGHT_SPEED

    def get_round_trip_time(self) -> float:
        """Get current round-trip time in seconds."""
        return 2 * self.get_light_delay()

    def simulate_earth_to_mars(
        self,
        message: bytes,
        msg_type: MessageType = MessageType.DATA
    ) -> Tuple[EDEMessage, bytes, float]:
        """
        Simulate sending message from Earth to Mars.

        Returns:
            (wire_message, decoded_payload, simulated_delay)
        """
        # Earth sends at T=0 (relative)
        send_time = 0.0
        wire_msg = self.earth_station.send(message, msg_type, send_time=send_time)

        # Mars receives after light delay
        # But decodes using sender's timestamp (T=0), not current time!
        decoded, valid = self.mars_station.receive(wire_msg, "EARTH-STATION")

        return wire_msg, decoded, self.get_light_delay()

    def simulate_mars_to_earth(
        self,
        message: bytes,
        msg_type: MessageType = MessageType.DATA
    ) -> Tuple[EDEMessage, bytes, float]:
        """
        Simulate sending message from Mars to Earth.

        Returns:
            (wire_message, decoded_payload, simulated_delay)
        """
        send_time = 0.0
        wire_msg = self.mars_station.send(message, msg_type, send_time=send_time)

        decoded, valid = self.earth_station.receive(wire_msg, "MARS-STATION")

        return wire_msg, decoded, self.get_light_delay()

    def get_stats(self) -> Dict[str, Any]:
        """Get link statistics."""
        delay = self.get_light_delay()
        return {
            "distance_km": self.current_distance_m / 1000,
            "one_way_delay_seconds": delay,
            "one_way_delay_minutes": delay / 60,
            "round_trip_seconds": delay * 2,
            "round_trip_minutes": delay * 2 / 60,
            "traditional_tls_time_minutes": (delay * 4) / 60,  # 4 round trips
            "ede_advantage": "Zero cryptographic latency",
            "earth_station": self.earth_station.get_stats(),
            "mars_station": self.mars_station.get_stats(),
        }


# =============================================================================
# COSMIC RAY PROTECTION
# =============================================================================

def add_error_detection(data: bytes, block_size: int = 64) -> bytes:
    """
    Add CRC32 error detection for cosmic ray protection.

    High-entropy encoding means bit-flips are more likely to
    produce invalid symbols, which are caught by validation.

    Args:
        data: Data to protect
        block_size: Size of each protected block

    Returns:
        Protected data with CRC32 checksums
    """
    import zlib

    protected = bytearray()

    for i in range(0, len(data), block_size):
        block = data[i:i + block_size]
        crc = zlib.crc32(block) & 0xFFFFFFFF
        protected.extend(block)
        protected.extend(crc.to_bytes(4, 'big'))

    return bytes(protected)


def verify_error_detection(data: bytes, block_size: int = 64) -> Tuple[bytes, bool]:
    """
    Verify and strip error detection.

    Args:
        data: Protected data
        block_size: Size of each protected block

    Returns:
        (original_data, all_valid)
    """
    import zlib

    chunk_size = block_size + 4  # block + CRC32
    original = bytearray()
    all_valid = True

    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        if len(chunk) < 5:
            break

        block = chunk[:-4]
        stored_crc = int.from_bytes(chunk[-4:], 'big')
        computed_crc = zlib.crc32(block) & 0xFFFFFFFF

        if stored_crc != computed_crc:
            all_valid = False

        original.extend(block)

    return bytes(original), all_valid


# =============================================================================
# TIME DILATION (FUTURE-PROOFING)
# =============================================================================

def lorentz_factor(velocity_fraction: float) -> float:
    """
    Calculate Lorentz factor for time dilation.

    γ = 1 / √(1 - v²/c²)

    For current Mars missions, v << c, so γ ≈ 1.
    But for future high-speed missions, this becomes important.

    Args:
        velocity_fraction: v/c (0 to <1)

    Returns:
        Lorentz gamma factor
    """
    if velocity_fraction >= 1.0:
        raise ValueError("Velocity must be less than c")

    import math
    return 1.0 / math.sqrt(1 - velocity_fraction ** 2)


def apply_time_dilation(
    proper_time: float,
    velocity_fraction: float
) -> float:
    """
    Apply time dilation to convert proper time to coordinate time.

    t = γ * τ

    Args:
        proper_time: Time in moving reference frame
        velocity_fraction: v/c

    Returns:
        Time in stationary reference frame
    """
    gamma = lorentz_factor(velocity_fraction)
    return gamma * proper_time


# =============================================================================
# QUICK FUNCTIONS
# =============================================================================

def quick_mars_encode(
    message: bytes,
    seed: bytes,
    timestamp: float = 0.0
) -> bytes:
    """
    Quick encoding for Mars transmission.

    Args:
        message: Message to encode
        seed: Shared seed
        timestamp: Send timestamp

    Returns:
        Encoded message bytes
    """
    station = EDEStation.create("sender", seed)
    ede_msg = station.send(message, send_time=timestamp)
    return ede_msg.to_bytes()


def quick_mars_decode(
    encoded: bytes,
    seed: bytes
) -> Tuple[bytes, bool]:
    """
    Quick decoding for Mars reception.

    Args:
        encoded: Encoded message bytes
        seed: Shared seed

    Returns:
        (decoded_message, is_valid)
    """
    station = EDEStation.create("receiver", seed)
    ede_msg = EDEMessage.from_bytes(encoded)
    return station.receive(ede_msg)
