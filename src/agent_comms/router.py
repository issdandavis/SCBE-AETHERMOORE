"""
Message Router
==============

Routes messages between agents based on trust and topology.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Callable

from .message import AgentMessage, MessageType
from .channel import SecureChannel, ChannelState
from .registry import AgentRegistry, AgentInfo, TrustLevel


class RouteType(Enum):
    """Types of routing strategies."""
    DIRECT = auto()       # Direct to recipient
    RELAY = auto()        # Via single relay
    ONION = auto()        # Multi-hop onion routing (future: Space Tor)
    BROADCAST = auto()    # To all trusted agents


@dataclass
class RouteInfo:
    """Information about a route."""
    route_type: RouteType
    hops: List[str]  # Agent IDs in order
    total_trust: float
    estimated_latency_ms: int
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))


class MessageRouter:
    """
    Routes messages between agents.

    Features:
    - Trust-based routing decisions
    - Multi-hop relay support
    - Automatic failover
    - Route caching

    Future: Integrate with Space Tor for 3D mesh routing.
    """

    def __init__(
        self,
        local_id: str,
        registry: AgentRegistry,
        min_relay_trust: TrustLevel = TrustLevel.TRUSTED,
    ):
        self.local_id = local_id
        self.registry = registry
        self.min_relay_trust = min_relay_trust

        # Active channels
        self._channels: Dict[str, SecureChannel] = {}

        # Route cache
        self._route_cache: Dict[str, RouteInfo] = {}
        self._route_cache_ttl_ms = 60000

        # Delivery callbacks
        self._on_receive: Optional[Callable[[AgentMessage, Dict], None]] = None

    def set_receive_handler(self, handler: Callable[[AgentMessage, Dict], None]) -> None:
        """Set callback for received messages."""
        self._on_receive = handler

    def get_or_create_channel(
        self,
        remote_id: str,
        shared_secret: bytes,
    ) -> SecureChannel:
        """Get existing channel or create new one."""

        if remote_id in self._channels:
            channel = self._channels[remote_id]
            if channel.is_healthy():
                return channel

        # Create new channel
        channel = SecureChannel(
            local_id=self.local_id,
            remote_id=remote_id,
            shared_secret=shared_secret,
        )

        self._channels[remote_id] = channel
        return channel

    def find_route(
        self,
        destination_id: str,
        route_type: RouteType = RouteType.DIRECT,
    ) -> Optional[RouteInfo]:
        """
        Find a route to destination.

        For DIRECT: Returns direct path if destination is trusted enough.
        For RELAY: Finds a trusted relay.
        For ONION: Builds multi-hop path (placeholder for Space Tor).
        """

        # Check cache
        cache_key = f"{destination_id}:{route_type.name}"
        if cache_key in self._route_cache:
            cached = self._route_cache[cache_key]
            now_ms = int(time.time() * 1000)
            if now_ms - cached.created_at < self._route_cache_ttl_ms:
                return cached

        dest_agent = self.registry.get(destination_id)
        if dest_agent is None:
            return None

        if route_type == RouteType.DIRECT:
            # Direct route
            route = RouteInfo(
                route_type=RouteType.DIRECT,
                hops=[destination_id],
                total_trust=dest_agent.trust_score,
                estimated_latency_ms=50,  # Placeholder
            )

        elif route_type == RouteType.RELAY:
            # Find best relay
            local_agent = self.registry.get(self.local_id)
            if local_agent is None:
                return None

            # Get trusted agents as relay candidates
            relays = self.registry.list_trusted(self.min_relay_trust)
            relays = [r for r in relays if r.agent_id not in (self.local_id, destination_id)]

            if not relays:
                # Fall back to direct
                return self.find_route(destination_id, RouteType.DIRECT)

            # Pick relay with best trust
            best_relay = max(relays, key=lambda r: r.trust_score)

            route = RouteInfo(
                route_type=RouteType.RELAY,
                hops=[best_relay.agent_id, destination_id],
                total_trust=min(best_relay.trust_score, dest_agent.trust_score),
                estimated_latency_ms=100,
            )

        elif route_type == RouteType.ONION:
            # Multi-hop onion routing (placeholder for Space Tor integration)
            # For now, use 3-hop path through trusted relays

            relays = self.registry.list_trusted(self.min_relay_trust)
            relays = [r for r in relays if r.agent_id not in (self.local_id, destination_id)]

            if len(relays) < 2:
                return self.find_route(destination_id, RouteType.RELAY)

            # Sort by trust and pick top 2 as intermediate hops
            relays.sort(key=lambda r: r.trust_score, reverse=True)
            hop1, hop2 = relays[0], relays[1]

            route = RouteInfo(
                route_type=RouteType.ONION,
                hops=[hop1.agent_id, hop2.agent_id, destination_id],
                total_trust=min(hop1.trust_score, hop2.trust_score, dest_agent.trust_score),
                estimated_latency_ms=150,
            )

        elif route_type == RouteType.BROADCAST:
            # Broadcast to all trusted agents
            trusted = self.registry.list_trusted(TrustLevel.TRUSTED)
            trusted = [t for t in trusted if t.agent_id != self.local_id]

            if not trusted:
                return None

            route = RouteInfo(
                route_type=RouteType.BROADCAST,
                hops=[t.agent_id for t in trusted],
                total_trust=min(t.trust_score for t in trusted) if trusted else 0.0,
                estimated_latency_ms=200,
            )

        else:
            return None

        # Cache route
        self._route_cache[cache_key] = route
        return route

    def send(
        self,
        destination_id: str,
        msg_type: MessageType,
        payload: Dict,
        route_type: RouteType = RouteType.DIRECT,
        shared_secret: Optional[bytes] = None,
    ) -> Optional[AgentMessage]:
        """
        Send a message to destination.

        Returns the message to transmit (caller handles actual network send).
        """

        # Find route
        route = self.find_route(destination_id, route_type)
        if route is None:
            return None

        # Get or create channel to first hop
        first_hop = route.hops[0]

        if shared_secret is None:
            # Try to derive from registry (placeholder)
            dest_agent = self.registry.get(first_hop)
            if dest_agent and dest_agent.public_key:
                shared_secret = hashlib.sha256(dest_agent.public_key).digest()
            else:
                return None

        channel = self.get_or_create_channel(first_hop, shared_secret)

        # Establish channel if needed
        if channel.state == ChannelState.INIT:
            # Return handshake message (caller should handle handshake flow)
            return channel.initiate_handshake()

        if channel.state != ChannelState.ESTABLISHED:
            return None

        # Build payload with routing info (for relay/onion)
        if route_type in (RouteType.RELAY, RouteType.ONION) and len(route.hops) > 1:
            # Wrap payload with routing instructions
            wrapped_payload = {
                "final_dest": destination_id,
                "remaining_hops": route.hops[1:],
                "inner_payload": payload,
            }
            return channel.send(msg_type, wrapped_payload)

        # Direct send
        return channel.send(msg_type, payload)

    def receive(
        self,
        msg: AgentMessage,
        shared_secret: Optional[bytes] = None,
    ) -> Optional[Dict]:
        """
        Receive and process a message.

        Handles:
        - Direct messages for us
        - Relay messages to forward
        - Handshake messages

        Returns decrypted payload for messages addressed to us.
        """

        sender_id = msg.sender_id

        # Get or create channel
        if shared_secret is None:
            sender_agent = self.registry.get(sender_id)
            if sender_agent and sender_agent.public_key:
                shared_secret = hashlib.sha256(sender_agent.public_key).digest()
            else:
                return None

        channel = self.get_or_create_channel(sender_id, shared_secret)

        # Handle handshake
        if msg.msg_type == MessageType.HANDSHAKE:
            response = channel.handle_handshake(msg)
            # Caller should send response if not None
            return {"_handshake_response": response} if response else None

        # Decrypt
        payload = channel.receive(msg)
        if payload is None:
            # Update trust on failure
            sender_agent = self.registry.get(sender_id)
            if sender_agent:
                sender_agent.update_trust(False)
            return None

        # Update trust on success
        sender_agent = self.registry.get(sender_id)
        if sender_agent:
            sender_agent.update_trust(True)

        # Check if this is a relay message
        if "remaining_hops" in payload and payload["remaining_hops"]:
            # Forward to next hop (not implemented - caller handles)
            return {"_relay": True, **payload}

        # Call receive handler
        if self._on_receive:
            self._on_receive(msg, payload)

        return payload

    def close_channel(self, remote_id: str) -> Optional[AgentMessage]:
        """Close channel to remote agent."""
        channel = self._channels.get(remote_id)
        if channel:
            return channel.close()
        return None

    def close_all(self) -> List[AgentMessage]:
        """Close all channels."""
        messages = []
        for channel in self._channels.values():
            msg = channel.close()
            if msg:
                messages.append(msg)
        self._channels.clear()
        return messages

    def stats(self) -> Dict:
        """Get router statistics."""
        return {
            "channels": len(self._channels),
            "healthy_channels": sum(1 for c in self._channels.values() if c.is_healthy()),
            "cached_routes": len(self._route_cache),
        }
