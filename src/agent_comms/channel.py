"""
Agent Communication Channels
=============================

Channels provide isolated communication paths between agents.
Each channel has state, capacity limits, and governance integration.

@module agent_comms/channel
"""

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

from .message import AgentMessage


class ChannelState(Enum):
    """Channel lifecycle states."""
    OPEN = "open"
    PAUSED = "paused"
    THROTTLED = "throttled"
    CLOSED = "closed"


@dataclass
class Channel:
    """
    A communication channel between agents.

    Channels are directional by default but can be made bidirectional.
    They support message queuing, priority ordering, and governance hooks.
    """
    channel_id: str
    owner_id: str
    # Allowed participants
    participants: List[str] = field(default_factory=list)
    # Channel configuration
    state: ChannelState = ChannelState.OPEN
    bidirectional: bool = True
    max_queue_size: int = 1000
    default_ttl: int = 300  # seconds
    # Tongue binding
    required_tongue: Optional[str] = None  # If set, only this tongue allowed
    # Message queue (priority ordered)
    _queue: deque = field(default_factory=deque, repr=False)
    # Message history
    _history: List[AgentMessage] = field(default_factory=list, repr=False)
    max_history: int = 500
    # Statistics
    messages_sent: int = 0
    messages_received: int = 0
    messages_dropped: int = 0
    created_at: float = field(default_factory=time.time)
    last_activity: float = 0.0
    # Hooks
    _on_message: Optional[Callable] = field(default=None, repr=False)
    _on_governance_check: Optional[Callable] = field(default=None, repr=False)

    def is_open(self) -> bool:
        """Check if channel accepts messages."""
        return self.state == ChannelState.OPEN

    def is_participant(self, agent_id: str) -> bool:
        """Check if an agent is allowed on this channel."""
        if not self.participants:
            return True  # Open channel
        return agent_id in self.participants or agent_id == self.owner_id

    def send(self, message: AgentMessage) -> bool:
        """
        Send a message through this channel.

        Returns True if message was accepted, False if rejected.
        """
        # Check channel state
        if self.state == ChannelState.CLOSED:
            return False

        if self.state == ChannelState.PAUSED:
            return False

        # Check participant permissions
        if not self.is_participant(message.sender_id):
            return False

        if message.recipient_id and not self.is_participant(message.recipient_id):
            return False

        # Check tongue binding
        if self.required_tongue and message.tongue != self.required_tongue:
            return False

        # Check queue capacity
        if len(self._queue) >= self.max_queue_size:
            self.messages_dropped += 1
            return False

        # Governance check hook
        if self._on_governance_check:
            allowed = self._on_governance_check(message, self)
            if not allowed:
                return False

        # Set channel context
        message.channel_id = self.channel_id
        if not message.ttl_seconds:
            message.ttl_seconds = self.default_ttl

        # Add to queue (priority ordered)
        self._queue.append(message)
        self.messages_sent += 1
        self.last_activity = time.time()

        # Notify hook
        if self._on_message:
            self._on_message(message, self)

        return True

    def receive(self, agent_id: Optional[str] = None) -> Optional[AgentMessage]:
        """
        Receive next message from the channel.

        If agent_id is specified, only returns messages for that agent.
        """
        if not self._queue:
            return None

        if agent_id:
            # Find first message for this agent
            for i, msg in enumerate(self._queue):
                if msg.recipient_id == agent_id or msg.is_broadcast():
                    self._queue.remove(msg)
                    self._record_history(msg)
                    self.messages_received += 1
                    return msg
            return None
        else:
            msg = self._queue.popleft()
            self._record_history(msg)
            self.messages_received += 1
            return msg

    def peek(self, count: int = 1) -> List[AgentMessage]:
        """Peek at next N messages without removing them."""
        return list(self._queue)[:count]

    def drain(self) -> List[AgentMessage]:
        """Remove and return all messages."""
        messages = list(self._queue)
        self._queue.clear()
        self.messages_received += len(messages)
        for msg in messages:
            self._record_history(msg)
        return messages

    def purge_expired(self) -> int:
        """Remove expired messages from queue. Returns count removed."""
        before = len(self._queue)
        self._queue = deque(msg for msg in self._queue if not msg.is_expired())
        removed = before - len(self._queue)
        self.messages_dropped += removed
        return removed

    def _record_history(self, message: AgentMessage):
        """Record message in history."""
        self._history.append(message)
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]

    def get_history(self, limit: int = 50) -> List[AgentMessage]:
        """Get recent message history."""
        return self._history[-limit:]

    def add_participant(self, agent_id: str):
        """Add an agent to this channel."""
        if agent_id not in self.participants:
            self.participants.append(agent_id)

    def remove_participant(self, agent_id: str):
        """Remove an agent from this channel."""
        if agent_id in self.participants:
            self.participants.remove(agent_id)

    def pause(self):
        """Pause the channel (no new messages accepted)."""
        self.state = ChannelState.PAUSED

    def resume(self):
        """Resume a paused channel."""
        if self.state == ChannelState.PAUSED:
            self.state = ChannelState.OPEN

    def close(self):
        """Close the channel permanently."""
        self.state = ChannelState.CLOSED
        self._queue.clear()

    def on_message(self, callback: Callable):
        """Register a message callback."""
        self._on_message = callback

    def on_governance_check(self, callback: Callable):
        """Register a governance check callback."""
        self._on_governance_check = callback

    @property
    def queue_depth(self) -> int:
        """Current queue depth."""
        return len(self._queue)

    def stats(self) -> Dict:
        """Get channel statistics."""
        return {
            "channel_id": self.channel_id,
            "state": self.state.value,
            "participants": len(self.participants),
            "queue_depth": self.queue_depth,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "messages_dropped": self.messages_dropped,
            "last_activity": self.last_activity,
            "uptime_seconds": time.time() - self.created_at,
        }
