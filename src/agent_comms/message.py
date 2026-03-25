"""
Agent Message Protocol
======================

Structured messages for AI-to-AI communication.
Each message is encoded in a Sacred Tongue and carries
governance metadata for routing decisions.

@module agent_comms/message
"""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MessageType(Enum):
    """Types of agent messages."""
    REQUEST = "request"       # Agent requesting action
    RESPONSE = "response"     # Response to a request
    BROADCAST = "broadcast"   # Message to all agents
    HANDOFF = "handoff"       # Task handoff between agents
    HEARTBEAT = "heartbeat"   # Keep-alive signal
    GOVERNANCE = "governance"  # Governance decision notification
    ALERT = "alert"           # Security alert


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3
    EMERGENCY = 4


@dataclass
class AgentMessage:
    """
    A structured message between AI agents.

    Messages are signed with HMAC to prevent tampering
    and include governance metadata for routing.
    """
    # Core fields
    message_id: str = ""
    sender_id: str = ""
    recipient_id: str = ""  # Empty for broadcast
    message_type: MessageType = MessageType.REQUEST
    priority: MessagePriority = MessagePriority.NORMAL

    # Payload
    action: str = ""
    target: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    # Tongue encoding
    tongue: str = "KO"  # Primary tongue for this message

    # Routing
    channel_id: str = ""
    correlation_id: str = ""  # Links request/response pairs
    hop_count: int = 0
    max_hops: int = 10

    # Timestamps
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0  # 0 = no expiry
    ttl_seconds: int = 300  # Default 5 minutes

    # Security
    signature: str = ""
    nonce: str = ""

    def __post_init__(self):
        if not self.message_id:
            self.message_id = hashlib.sha256(
                f"{self.sender_id}:{time.time()}:{id(self)}".encode()
            ).hexdigest()[:16]
        if not self.nonce:
            import os
            self.nonce = os.urandom(16).hex()
        if self.expires_at == 0.0 and self.ttl_seconds > 0:
            self.expires_at = self.created_at + self.ttl_seconds

    def sign(self, key: bytes) -> str:
        """Sign the message with HMAC-SHA256."""
        canonical = self._canonical_form()
        self.signature = hmac.new(key, canonical.encode(), hashlib.sha256).hexdigest()
        return self.signature

    def verify(self, key: bytes) -> bool:
        """Verify message signature."""
        if not self.signature:
            return False
        canonical = self._canonical_form()
        expected = hmac.new(key, canonical.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.signature, expected)

    def _canonical_form(self) -> str:
        """Canonical string representation for signing."""
        return json.dumps({
            "id": self.message_id,
            "sender": self.sender_id,
            "recipient": self.recipient_id,
            "type": self.message_type.value,
            "action": self.action,
            "target": self.target,
            "payload": self.payload,
            "tongue": self.tongue,
            "nonce": self.nonce,
            "created_at": self.created_at,
        }, sort_keys=True, separators=(",", ":"))

    def is_expired(self) -> bool:
        """Check if message has expired."""
        if self.expires_at <= 0:
            return False
        return time.time() > self.expires_at

    def is_broadcast(self) -> bool:
        """Check if this is a broadcast message."""
        return self.message_type == MessageType.BROADCAST or not self.recipient_id

    def increment_hop(self) -> bool:
        """Increment hop count. Returns False if max hops exceeded."""
        self.hop_count += 1
        return self.hop_count <= self.max_hops

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "message_type": self.message_type.value,
            "priority": self.priority.value,
            "action": self.action,
            "target": self.target,
            "payload": self.payload,
            "tongue": self.tongue,
            "channel_id": self.channel_id,
            "correlation_id": self.correlation_id,
            "hop_count": self.hop_count,
            "max_hops": self.max_hops,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "signature": self.signature,
            "nonce": self.nonce,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        """Deserialize from dictionary."""
        msg = cls(
            message_id=data.get("message_id", ""),
            sender_id=data.get("sender_id", ""),
            recipient_id=data.get("recipient_id", ""),
            message_type=MessageType(data.get("message_type", "request")),
            priority=MessagePriority(data.get("priority", 1)),
            action=data.get("action", ""),
            target=data.get("target", ""),
            payload=data.get("payload", {}),
            tongue=data.get("tongue", "KO"),
            channel_id=data.get("channel_id", ""),
            correlation_id=data.get("correlation_id", ""),
            hop_count=data.get("hop_count", 0),
            max_hops=data.get("max_hops", 10),
            created_at=data.get("created_at", time.time()),
            expires_at=data.get("expires_at", 0.0),
            signature=data.get("signature", ""),
            nonce=data.get("nonce", ""),
        )
        return msg

    def create_response(
        self, payload: Dict[str, Any], tongue: Optional[str] = None
    ) -> "AgentMessage":
        """Create a response message to this message."""
        return AgentMessage(
            sender_id=self.recipient_id,
            recipient_id=self.sender_id,
            message_type=MessageType.RESPONSE,
            priority=self.priority,
            action=self.action,
            target=self.target,
            payload=payload,
            tongue=tongue or self.tongue,
            channel_id=self.channel_id,
            correlation_id=self.message_id,
        )
