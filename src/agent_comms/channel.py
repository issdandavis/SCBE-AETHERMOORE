"""
Secure Channel for Agent Communication
======================================

Establishes encrypted channels between AI agents.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Callable, Any

from .message import AgentMessage, MessageType


class ChannelState(Enum):
    """Channel lifecycle states."""
    INIT = auto()
    HANDSHAKING = auto()
    ESTABLISHED = auto()
    DEGRADED = auto()
    CLOSED = auto()


@dataclass
class ChannelConfig:
    """Configuration for a secure channel."""

    # Timing
    handshake_timeout_ms: int = 5000
    heartbeat_interval_ms: int = 10000
    message_ttl_ms: int = 60000

    # Security
    require_mutual_auth: bool = True
    max_failed_auth: int = 3
    replay_window_ms: int = 60000

    # Reliability
    max_retries: int = 3
    retry_backoff_ms: int = 1000


@dataclass
class SecureChannel:
    """
    A secure communication channel between two agents.

    Features:
    - Mutual authentication
    - Session key derivation
    - Replay protection (nonce cache)
    - Automatic heartbeats
    - Graceful degradation
    """

    local_id: str
    remote_id: str
    shared_secret: bytes  # Pre-shared or derived from key exchange
    config: ChannelConfig = field(default_factory=ChannelConfig)

    # State
    state: ChannelState = ChannelState.INIT
    session_key: Optional[bytes] = None
    established_at: Optional[int] = None
    last_activity: Optional[int] = None

    # Replay protection
    _seen_nonces: Dict[str, int] = field(default_factory=dict)
    _failed_auth_count: int = 0

    # Message handlers
    _handlers: Dict[MessageType, Callable] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize channel."""
        self._seen_nonces = {}
        self._handlers = {}

    def derive_session_key(self, nonce_local: bytes, nonce_remote: bytes) -> bytes:
        """
        Derive session key from shared secret and nonces.

        Uses HKDF-like construction for key derivation.
        """
        # Combine nonces deterministically (sorted to ensure same result on both sides)
        combined = b"".join(sorted([nonce_local, nonce_remote]))

        # Derive session key
        prk = hmac.new(self.shared_secret, combined, hashlib.sha256).digest()
        session_key = hmac.new(
            prk,
            b"session_key|" + self.local_id.encode() + b"|" + self.remote_id.encode(),
            hashlib.sha256
        ).digest()

        return session_key

    def initiate_handshake(self) -> AgentMessage:
        """
        Start handshake (caller is initiator).

        Returns HANDSHAKE message to send.
        """
        self.state = ChannelState.HANDSHAKING

        nonce_local = os.urandom(32)

        msg = AgentMessage.create(
            msg_type=MessageType.HANDSHAKE,
            sender_id=self.local_id,
            recipient_id=self.remote_id,
            payload={"nonce": nonce_local.hex(), "version": "1.0"},
            key=self.shared_secret,
            priority=10,  # High priority for handshake
        )

        # Store our nonce for session key derivation
        self._local_nonce = nonce_local

        return msg

    def handle_handshake(self, msg: AgentMessage) -> Optional[AgentMessage]:
        """
        Handle incoming handshake message.

        Returns response message (or None if invalid).
        """
        # Verify and decrypt
        payload = msg.verify_and_decrypt(self.shared_secret)
        if payload is None:
            self._failed_auth_count += 1
            if self._failed_auth_count >= self.config.max_failed_auth:
                self.state = ChannelState.CLOSED
            return None

        nonce_remote = bytes.fromhex(payload["nonce"])

        if self.state == ChannelState.INIT:
            # We're responder - generate our nonce and respond
            self.state = ChannelState.HANDSHAKING
            nonce_local = os.urandom(32)
            self._local_nonce = nonce_local

            # Derive session key
            self.session_key = self.derive_session_key(nonce_local, nonce_remote)
            self._remote_nonce = nonce_remote

            # Send response with our nonce
            response = AgentMessage.create(
                msg_type=MessageType.HANDSHAKE,
                sender_id=self.local_id,
                recipient_id=self.remote_id,
                payload={"nonce": nonce_local.hex(), "version": "1.0", "ack": True},
                key=self.shared_secret,
                priority=10,
            )

            return response

        elif self.state == ChannelState.HANDSHAKING:
            # We're initiator, got response - complete handshake
            self._remote_nonce = nonce_remote
            self.session_key = self.derive_session_key(self._local_nonce, nonce_remote)

            # Channel established
            self.state = ChannelState.ESTABLISHED
            self.established_at = int(time.time() * 1000)
            self.last_activity = self.established_at

            return None  # Handshake complete

        return None

    def send(self, msg_type: MessageType, payload: Dict[str, Any]) -> Optional[AgentMessage]:
        """
        Send a message on this channel.

        Returns the message to transmit (caller handles actual transmission).
        """
        if self.state != ChannelState.ESTABLISHED:
            return None

        if self.session_key is None:
            return None

        msg = AgentMessage.create(
            msg_type=msg_type,
            sender_id=self.local_id,
            recipient_id=self.remote_id,
            payload=payload,
            key=self.session_key,
        )

        self.last_activity = int(time.time() * 1000)

        return msg

    def receive(self, msg: AgentMessage) -> Optional[Dict[str, Any]]:
        """
        Receive and process a message.

        Returns decrypted payload on success, None on failure.
        """
        if self.state != ChannelState.ESTABLISHED:
            # Allow handshake messages through
            if msg.msg_type == MessageType.HANDSHAKE:
                self.handle_handshake(msg)
                return None
            return None

        if self.session_key is None:
            return None

        # Check replay
        nonce_hex = msg.nonce.hex()
        now_ms = int(time.time() * 1000)

        if nonce_hex in self._seen_nonces:
            return None  # Replay attack

        # Prune old nonces
        cutoff = now_ms - self.config.replay_window_ms
        self._seen_nonces = {
            n: t for n, t in self._seen_nonces.items()
            if t > cutoff
        }

        # Verify and decrypt
        payload = msg.verify_and_decrypt(self.session_key, self.config.message_ttl_ms)
        if payload is None:
            self._failed_auth_count += 1
            if self._failed_auth_count >= self.config.max_failed_auth:
                self.state = ChannelState.DEGRADED
            return None

        # Mark nonce as seen
        self._seen_nonces[nonce_hex] = now_ms
        self.last_activity = now_ms
        self._failed_auth_count = 0  # Reset on success

        # Handle system messages
        if msg.msg_type == MessageType.HEARTBEAT:
            # Auto-respond to heartbeats
            pass
        elif msg.msg_type == MessageType.DISCONNECT:
            self.state = ChannelState.CLOSED

        return payload

    def close(self) -> Optional[AgentMessage]:
        """
        Gracefully close the channel.

        Returns DISCONNECT message to send.
        """
        if self.state == ChannelState.CLOSED:
            return None

        msg = self.send(MessageType.DISCONNECT, {"reason": "normal"})
        self.state = ChannelState.CLOSED

        return msg

    def is_healthy(self) -> bool:
        """Check if channel is healthy."""
        if self.state not in (ChannelState.ESTABLISHED, ChannelState.DEGRADED):
            return False

        if self.last_activity is None:
            return False

        now_ms = int(time.time() * 1000)
        stale_threshold = self.config.heartbeat_interval_ms * 3

        return (now_ms - self.last_activity) < stale_threshold

    def register_handler(self, msg_type: MessageType, handler: Callable) -> None:
        """Register a handler for a message type."""
        self._handlers[msg_type] = handler
