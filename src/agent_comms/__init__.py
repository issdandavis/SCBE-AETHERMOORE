"""
SCBE-AETHERMOORE Agent Communications
=====================================

Secure AI-to-AI communication primitives.

This module provides:
- Secure channel establishment between agents
- Message encryption with PQC (simulated)
- Trust-based routing decisions
- Replay protection
- Fail-to-noise on errors

Future: Integrate with Space Tor for 3D mesh routing.
"""

from .channel import SecureChannel, ChannelConfig
from .message import AgentMessage, MessageType
from .registry import AgentRegistry
from .router import MessageRouter

__all__ = [
    "SecureChannel",
    "ChannelConfig",
    "AgentMessage",
    "MessageType",
    "AgentRegistry",
    "MessageRouter",
]
