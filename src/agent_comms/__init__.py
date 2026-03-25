"""
Agent Communications Module
============================

AI-to-AI agent communication system using Sacred Tongues encoding
and SCBE governance for message routing and authorization.

Components:
- Message: Structured agent messages with tongue encoding
- Channel: Communication channels between agents
- Registry: Agent discovery and registration
- Router: Message routing with governance checks

@module agent_comms
@layer L13 (Risk decision), L14 (Telemetry)
"""

from .message import AgentMessage, MessagePriority, MessageType
from .channel import Channel, ChannelState
from .registry import AgentRegistry, AgentInfo
from .router import MessageRouter

__all__ = [
    "AgentMessage",
    "MessagePriority",
    "MessageType",
    "Channel",
    "ChannelState",
    "AgentRegistry",
    "AgentInfo",
    "MessageRouter",
]
