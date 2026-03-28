"""
Message Router
==============

Routes agent messages through channels with governance checks.
Integrates with the SCBE governance pipeline for authorization.

@module agent_comms/router
"""

import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from .channel import Channel
from .message import AgentMessage
from .registry import AgentRegistry


@dataclass
class RouteResult:
    """Result of a routing attempt."""

    delivered: bool
    channel_id: Optional[str] = None
    error: Optional[str] = None
    governance_decision: Optional[str] = None
    hop_count: int = 0


class MessageRouter:
    """
    Routes messages between agents through governed channels.

    The router:
    1. Validates sender/recipient exist
    2. Checks governance authorization
    3. Selects appropriate channel
    4. Delivers message (or queues for async delivery)
    """

    def __init__(self, registry: Optional[AgentRegistry] = None):
        self.registry = registry or AgentRegistry()
        self._channels: Dict[str, Channel] = {}
        self._agent_channels: Dict[str, List[str]] = {}  # agent_id -> channel_ids
        self._governance_hook: Optional[Callable] = None
        # Stats
        self.messages_routed: int = 0
        self.messages_failed: int = 0
        self.messages_governed: int = 0

    def create_channel(
        self,
        channel_id: str,
        owner_id: str,
        participants: Optional[List[str]] = None,
        required_tongue: Optional[str] = None,
        bidirectional: bool = True,
    ) -> Channel:
        """Create a new communication channel."""
        channel = Channel(
            channel_id=channel_id,
            owner_id=owner_id,
            participants=participants or [],
            required_tongue=required_tongue,
            bidirectional=bidirectional,
        )

        # Register governance hook if available
        if self._governance_hook:
            channel.on_governance_check(self._governance_hook)

        self._channels[channel_id] = channel

        # Index channels by participant
        for participant in (participants or []) + [owner_id]:
            if participant not in self._agent_channels:
                self._agent_channels[participant] = []
            self._agent_channels[participant].append(channel_id)

        return channel

    def get_channel(self, channel_id: str) -> Optional[Channel]:
        """Get a channel by ID."""
        return self._channels.get(channel_id)

    def close_channel(self, channel_id: str) -> bool:
        """Close and remove a channel."""
        channel = self._channels.pop(channel_id, None)
        if not channel:
            return False
        channel.close()

        # Clean up agent-channel index
        for agent_id, channels in self._agent_channels.items():
            if channel_id in channels:
                channels.remove(channel_id)

        return True

    def set_governance_hook(self, hook: Callable):
        """
        Set a governance check function.

        The hook receives (message, channel) and returns True/False.
        Used to integrate with the SCBE governance pipeline.
        """
        self._governance_hook = hook

        # Apply to existing channels
        for channel in self._channels.values():
            channel.on_governance_check(hook)

    def route(self, message: AgentMessage) -> RouteResult:
        """
        Route a message to its destination.

        Routing process:
        1. Validate sender exists and is online
        2. For targeted messages, validate recipient
        3. Check governance authorization
        4. Select channel (explicit or auto-select)
        5. Deliver through channel
        """
        # Validate sender
        sender = self.registry.get(message.sender_id)
        if not sender:
            self.messages_failed += 1
            return RouteResult(delivered=False, error="Unknown sender")

        # Check message expiry
        if message.is_expired():
            self.messages_failed += 1
            return RouteResult(delivered=False, error="Message expired")

        # Check hop count
        if not message.increment_hop():
            self.messages_failed += 1
            return RouteResult(delivered=False, error="Max hops exceeded")

        # Handle broadcast
        if message.is_broadcast():
            return self._route_broadcast(message)

        # Validate recipient
        recipient = self.registry.get(message.recipient_id)
        if not recipient:
            self.messages_failed += 1
            return RouteResult(delivered=False, error="Unknown recipient")

        # Select channel
        channel = self._select_channel(message)
        if not channel:
            # Create ad-hoc channel
            channel = self.create_channel(
                channel_id=f"adhoc_{message.sender_id}_{message.recipient_id}_{int(time.time())}",
                owner_id=message.sender_id,
                participants=[message.sender_id, message.recipient_id],
            )

        # Deliver
        success = channel.send(message)
        if success:
            self.messages_routed += 1
            return RouteResult(
                delivered=True,
                channel_id=channel.channel_id,
                hop_count=message.hop_count,
            )
        else:
            self.messages_failed += 1
            return RouteResult(
                delivered=False,
                channel_id=channel.channel_id,
                error="Channel rejected message",
            )

    def _route_broadcast(self, message: AgentMessage) -> RouteResult:
        """Route a broadcast message to all relevant channels."""
        delivered = False
        for channel_id, channel in self._channels.items():
            if channel.is_participant(message.sender_id) and channel.is_open():
                if channel.send(message):
                    delivered = True

        if delivered:
            self.messages_routed += 1
            return RouteResult(delivered=True)
        else:
            self.messages_failed += 1
            return RouteResult(delivered=False, error="No channels accepted broadcast")

    def _select_channel(self, message: AgentMessage) -> Optional[Channel]:
        """Select the best channel for a message."""
        # If message specifies a channel, use it
        if message.channel_id:
            channel = self._channels.get(message.channel_id)
            if channel and channel.is_open():
                return channel

        # Find shared channels between sender and recipient
        sender_channels = set(self._agent_channels.get(message.sender_id, []))
        recipient_channels = set(self._agent_channels.get(message.recipient_id, []))
        shared = sender_channels & recipient_channels

        if not shared:
            return None

        # Prefer channels matching the message tongue
        for ch_id in shared:
            channel = self._channels[ch_id]
            if channel.is_open() and (
                not channel.required_tongue or channel.required_tongue == message.tongue
            ):
                return channel

        # Fall back to any open shared channel
        for ch_id in shared:
            channel = self._channels[ch_id]
            if channel.is_open():
                return channel

        return None

    def get_agent_channels(self, agent_id: str) -> List[Channel]:
        """Get all channels an agent participates in."""
        channel_ids = self._agent_channels.get(agent_id, [])
        return [self._channels[cid] for cid in channel_ids if cid in self._channels]

    def poll(self, agent_id: str) -> List[AgentMessage]:
        """Poll all channels for messages addressed to an agent."""
        messages = []
        for channel in self.get_agent_channels(agent_id):
            while True:
                msg = channel.receive(agent_id)
                if not msg:
                    break
                messages.append(msg)
        return messages

    def stats(self) -> Dict:
        """Get router statistics."""
        return {
            "channels": len(self._channels),
            "open_channels": sum(1 for c in self._channels.values() if c.is_open()),
            "messages_routed": self.messages_routed,
            "messages_failed": self.messages_failed,
            "messages_governed": self.messages_governed,
            "agents_registered": self.registry.agent_count,
            "agents_online": self.registry.online_count,
        }
