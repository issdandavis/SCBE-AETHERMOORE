"""
Agent Message Types and Structures
==================================

Message primitives for AI-to-AI communication.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Optional


class MessageType(Enum):
    """Types of agent-to-agent messages."""

    # Control messages
    HANDSHAKE = auto()      # Initial connection
    HEARTBEAT = auto()      # Keep-alive
    DISCONNECT = auto()     # Graceful close

    # Data messages
    QUERY = auto()          # Request information
    RESPONSE = auto()       # Response to query
    BROADCAST = auto()      # One-to-many

    # Consensus messages
    PROPOSE = auto()        # Propose action
    VOTE = auto()           # Vote on proposal
    COMMIT = auto()         # Commit decision

    # Security messages
    CHALLENGE = auto()      # Auth challenge
    PROOF = auto()          # Auth proof
    REVOKE = auto()         # Revoke access


@dataclass
class AgentMessage:
    """
    A message between AI agents.

    Structure:
    - Header: routing info, timestamps, nonces
    - Body: encrypted payload
    - Auth: signature(s) from sender
    """

    # Header
    msg_id: str
    msg_type: MessageType
    sender_id: str
    recipient_id: str
    timestamp_ms: int
    nonce: bytes

    # Body (encrypted)
    payload_encrypted: bytes

    # Auth
    signature: bytes

    # Metadata
    ttl_hops: int = 10
    priority: int = 5  # 1-10, higher = more urgent
    require_ack: bool = True

    @classmethod
    def create(
        cls,
        msg_type: MessageType,
        sender_id: str,
        recipient_id: str,
        payload: Dict[str, Any],
        key: bytes,
        priority: int = 5,
        ttl_hops: int = 10,
    ) -> "AgentMessage":
        """Create a new signed and encrypted message."""

        # Generate IDs and timestamps
        msg_id = hashlib.sha256(os.urandom(32)).hexdigest()[:16]
        timestamp_ms = int(time.time() * 1000)
        nonce = os.urandom(16)

        # Serialize and encrypt payload
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        payload_encrypted = cls._encrypt(key, nonce, payload_bytes)

        # Create signature over header + encrypted payload
        sign_data = (
            msg_id.encode() +
            msg_type.name.encode() +
            sender_id.encode() +
            recipient_id.encode() +
            timestamp_ms.to_bytes(8, "big") +
            nonce +
            payload_encrypted
        )
        signature = hmac.new(key, sign_data, hashlib.sha256).digest()

        return cls(
            msg_id=msg_id,
            msg_type=msg_type,
            sender_id=sender_id,
            recipient_id=recipient_id,
            timestamp_ms=timestamp_ms,
            nonce=nonce,
            payload_encrypted=payload_encrypted,
            signature=signature,
            ttl_hops=ttl_hops,
            priority=priority,
        )

    def verify_and_decrypt(self, key: bytes, max_age_ms: int = 60000) -> Optional[Dict[str, Any]]:
        """
        Verify signature and decrypt payload.

        Returns:
            Decrypted payload dict on success, None on failure.

        Note: Returns None (not error) to prevent oracle attacks.
        """
        # Check timestamp
        now_ms = int(time.time() * 1000)
        if abs(now_ms - self.timestamp_ms) > max_age_ms:
            return None

        # Verify signature
        sign_data = (
            self.msg_id.encode() +
            self.msg_type.name.encode() +
            self.sender_id.encode() +
            self.recipient_id.encode() +
            self.timestamp_ms.to_bytes(8, "big") +
            self.nonce +
            self.payload_encrypted
        )
        expected_sig = hmac.new(key, sign_data, hashlib.sha256).digest()

        if not hmac.compare_digest(expected_sig, self.signature):
            return None

        # Decrypt
        try:
            payload_bytes = self._decrypt(key, self.nonce, self.payload_encrypted)
            return json.loads(payload_bytes.decode("utf-8"))
        except Exception:
            return None

    @staticmethod
    def _encrypt(key: bytes, nonce: bytes, plaintext: bytes) -> bytes:
        """Simple XOR stream cipher (demo only - use AES-GCM in production)."""
        keystream = hmac.new(key, b"ENC" + nonce, hashlib.sha256).digest()
        # Extend keystream for longer messages
        while len(keystream) < len(plaintext):
            keystream += hmac.new(key, keystream[-32:], hashlib.sha256).digest()
        return bytes(p ^ keystream[i] for i, p in enumerate(plaintext))

    @staticmethod
    def _decrypt(key: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
        """Decrypt (same as encrypt for XOR)."""
        return AgentMessage._encrypt(key, nonce, ciphertext)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for transmission."""
        return {
            "msg_id": self.msg_id,
            "msg_type": self.msg_type.name,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "timestamp_ms": self.timestamp_ms,
            "nonce": self.nonce.hex(),
            "payload_encrypted": self.payload_encrypted.hex(),
            "signature": self.signature.hex(),
            "ttl_hops": self.ttl_hops,
            "priority": self.priority,
            "require_ack": self.require_ack,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        """Deserialize from transmission."""
        return cls(
            msg_id=data["msg_id"],
            msg_type=MessageType[data["msg_type"]],
            sender_id=data["sender_id"],
            recipient_id=data["recipient_id"],
            timestamp_ms=data["timestamp_ms"],
            nonce=bytes.fromhex(data["nonce"]),
            payload_encrypted=bytes.fromhex(data["payload_encrypted"]),
            signature=bytes.fromhex(data["signature"]),
            ttl_hops=data.get("ttl_hops", 10),
            priority=data.get("priority", 5),
            require_ack=data.get("require_ack", True),
        )
