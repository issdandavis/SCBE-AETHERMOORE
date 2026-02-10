"""
HYDRA WebSocket Manager - Real-Time Agent Coordination
======================================================

WebSocket-based real-time communication layer for the HYDRA system.
Enables coordinated multi-agent operations with governance-first design.

Phase 1 Q2 2026 Expansion Feature.

Features:
- WebSocket client connection management
- Subscription-based message routing
- All messages governed through spine.execute()
- Broadcast capability for state changes
- Clean disconnect with resource cleanup

Architecture:
    Client A ----ws----> WebSocketManager -----> HydraSpine
    Client B ----ws----> WebSocketManager -----> (Governance)
    Client C ----ws----> WebSocketManager -----> Limbs/Heads

Research Validation:
- RFC 6455 WebSocket Protocol compliance
- SentinelAgent (2025) - Real-time anomaly detection
- SwarmRaft (2025) - Byzantine consensus via WS channels
"""

import asyncio
import json
import weakref
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import uuid

# Type hints for WebSocket - supports both websockets and aiohttp
try:
    from websockets import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = Any

try:
    from aiohttp import web
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from .ledger import Ledger, LedgerEntry, EntryType


class SubscriptionChannel(str, Enum):
    """Available subscription channels for real-time updates."""
    ACTIONS = "actions"           # All action executions
    DECISIONS = "decisions"       # Governance decisions (ALLOW/DENY/ESCALATE/QUARANTINE)
    HEADS = "heads"               # Head connect/disconnect events
    LIMBS = "limbs"               # Limb activation events
    WORKFLOWS = "workflows"       # Workflow state changes
    CONSENSUS = "consensus"       # Byzantine consensus votes
    SPECTRAL = "spectral"         # Spectral anomaly detections
    BROADCAST = "broadcast"       # General broadcast channel
    ALL = "all"                   # Subscribe to everything


class ClientState(str, Enum):
    """WebSocket client connection states."""
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    IDLE = "idle"
    BUSY = "busy"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class WebSocketClient:
    """
    Represents a connected WebSocket client.

    Each client can subscribe to multiple channels and optionally
    associate with a HydraHead for AI-to-AI messaging.
    """
    client_id: str
    websocket: Any  # WebSocket connection object
    state: ClientState = ClientState.CONNECTING
    subscriptions: Set[str] = field(default_factory=set)
    head_id: Optional[str] = None  # Associated HYDRA head
    metadata: Dict[str, Any] = field(default_factory=dict)
    connected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_message_at: Optional[str] = None
    message_count: int = 0
    error_count: int = 0

    def is_subscribed(self, channel: str) -> bool:
        """Check if client is subscribed to a channel."""
        return (
            SubscriptionChannel.ALL.value in self.subscriptions or
            channel in self.subscriptions
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize client info (without websocket reference)."""
        return {
            "client_id": self.client_id,
            "state": self.state.value,
            "subscriptions": list(self.subscriptions),
            "head_id": self.head_id,
            "connected_at": self.connected_at,
            "last_message_at": self.last_message_at,
            "message_count": self.message_count,
            "error_count": self.error_count,
            "metadata": self.metadata
        }


class WebSocketManager:
    """
    WebSocket connection manager for HYDRA real-time coordination.

    All messages are routed through spine.execute() to ensure
    governance checks before any action is taken.

    Usage:
        spine = HydraSpine()
        ws_manager = WebSocketManager(spine)

        # Start WebSocket server
        await ws_manager.start(host="0.0.0.0", port=8765)

        # Or use with aiohttp
        app = web.Application()
        ws_manager.setup_aiohttp(app)
    """

    def __init__(
        self,
        spine: 'HydraSpine',
        auth_required: bool = True,
        heartbeat_interval: float = 30.0,
        max_clients: int = 100,
        max_message_size: int = 1024 * 1024  # 1MB
    ):
        self._spine = spine
        self._auth_required = auth_required
        self._heartbeat_interval = heartbeat_interval
        self._max_clients = max_clients
        self._max_message_size = max_message_size

        # Connected clients: client_id -> WebSocketClient
        self._clients: Dict[str, WebSocketClient] = {}

        # Subscription index: channel -> set of client_ids
        self._subscriptions: Dict[str, Set[str]] = {
            channel.value: set() for channel in SubscriptionChannel
        }

        # Event handlers for extensibility
        self._handlers: Dict[str, List[Callable]] = {}

        # Server state
        self._server = None
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Use spine's ledger for logging
        self._ledger = spine.ledger

    @property
    def client_count(self) -> int:
        """Number of connected clients."""
        return len(self._clients)

    @property
    def is_running(self) -> bool:
        """Check if WebSocket server is running."""
        return self._running

    # =========================================================================
    # Server Lifecycle
    # =========================================================================

    async def start(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        """
        Start standalone WebSocket server using websockets library.

        Args:
            host: Bind address (default 0.0.0.0 for all interfaces)
            port: Listen port (default 8765)
        """
        if not WEBSOCKETS_AVAILABLE:
            raise RuntimeError("websockets library not available. Install with: pip install websockets")

        import websockets

        self._running = True

        # Start heartbeat task
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # Log server start
        self._log_entry(
            EntryType.CHECKPOINT,
            "ws_server_start",
            f"{host}:{port}",
            {"max_clients": self._max_clients, "auth_required": self._auth_required}
        )

        print(f"""
========================================================
  HYDRA WebSocket Server
========================================================
  Address:    ws://{host}:{port}
  Max Clients: {self._max_clients}
  Auth:       {'Required' if self._auth_required else 'Optional'}
  Heartbeat:  {self._heartbeat_interval}s
========================================================
        """)

        # Start server
        self._server = await websockets.serve(
            self._handle_connection,
            host,
            port,
            max_size=self._max_message_size,
            ping_interval=self._heartbeat_interval,
            ping_timeout=10.0
        )

        # Keep running until stopped
        await self._server.wait_closed()

    async def stop(self) -> None:
        """Stop WebSocket server and disconnect all clients."""
        self._running = False

        # Cancel heartbeat
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Disconnect all clients
        disconnect_tasks = []
        for client_id in list(self._clients.keys()):
            disconnect_tasks.append(self.disconnect_client(client_id, "Server shutting down"))

        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)

        # Close server
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        self._log_entry(
            EntryType.CHECKPOINT,
            "ws_server_stop",
            "system",
            {"clients_disconnected": len(disconnect_tasks)}
        )

        print("[WS] Server stopped")

    def setup_aiohttp(self, app: 'web.Application', path: str = "/ws") -> None:
        """
        Set up WebSocket handler for aiohttp application.

        Args:
            app: aiohttp Application instance
            path: WebSocket endpoint path (default /ws)
        """
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp library not available. Install with: pip install aiohttp")

        app.router.add_get(path, self._aiohttp_handler)

        # Store reference for cleanup
        app.on_startup.append(self._on_aiohttp_startup)
        app.on_cleanup.append(self._on_aiohttp_cleanup)

        print(f"[WS] Configured aiohttp handler at {path}")

    async def _on_aiohttp_startup(self, app: 'web.Application') -> None:
        """aiohttp startup hook."""
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _on_aiohttp_cleanup(self, app: 'web.Application') -> None:
        """aiohttp cleanup hook."""
        await self.stop()

    async def _aiohttp_handler(self, request: 'web.Request') -> 'web.WebSocketResponse':
        """aiohttp WebSocket request handler."""
        ws = web.WebSocketResponse(
            max_msg_size=self._max_message_size,
            heartbeat=self._heartbeat_interval
        )
        await ws.prepare(request)

        # Create client
        client_id = f"ws-{uuid.uuid4().hex[:8]}"
        client = WebSocketClient(
            client_id=client_id,
            websocket=ws,
            metadata={"remote": str(request.remote), "path": str(request.path)}
        )

        await self._register_client(client)

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    await self._handle_message(client, msg.data)
                elif msg.type == web.WSMsgType.ERROR:
                    print(f"[WS] Connection error: {ws.exception()}")
                    break
        finally:
            await self._unregister_client(client_id)

        return ws

    # =========================================================================
    # Connection Handling
    # =========================================================================

    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str = "/") -> None:
        """Handle incoming websockets library connection."""
        # Check client limit
        if len(self._clients) >= self._max_clients:
            await websocket.close(1013, "Server at capacity")
            return

        # Create client
        client_id = f"ws-{uuid.uuid4().hex[:8]}"
        client = WebSocketClient(
            client_id=client_id,
            websocket=websocket,
            metadata={"remote": str(websocket.remote_address), "path": path}
        )

        await self._register_client(client)

        try:
            async for message in websocket:
                await self._handle_message(client, message)
        except Exception as e:
            client.state = ClientState.ERROR
            client.error_count += 1
            print(f"[WS] Client {client_id} error: {e}")
        finally:
            await self._unregister_client(client_id)

    async def _register_client(self, client: WebSocketClient) -> None:
        """Register a new client connection."""
        self._clients[client.client_id] = client
        client.state = ClientState.CONNECTED

        # Log connection
        self._log_entry(
            EntryType.CHECKPOINT,
            "ws_connect",
            client.client_id,
            {"metadata": client.metadata}
        )

        # Send welcome message
        await self._send_to_client(client.client_id, {
            "type": "welcome",
            "client_id": client.client_id,
            "server_time": datetime.now(timezone.utc).isoformat(),
            "channels": [c.value for c in SubscriptionChannel]
        })

        # Trigger handlers
        await self._emit("connect", client)

        print(f"[WS] Client connected: {client.client_id}")

    async def _unregister_client(self, client_id: str) -> None:
        """Unregister and cleanup client connection."""
        if client_id not in self._clients:
            return

        client = self._clients[client_id]
        client.state = ClientState.DISCONNECTED

        # Remove from all subscriptions
        for channel in self._subscriptions.values():
            channel.discard(client_id)

        # Remove from clients
        del self._clients[client_id]

        # Log disconnection
        self._log_entry(
            EntryType.CHECKPOINT,
            "ws_disconnect",
            client_id,
            {
                "message_count": client.message_count,
                "error_count": client.error_count,
                "duration_connected": client.connected_at
            }
        )

        # Trigger handlers
        await self._emit("disconnect", client)

        print(f"[WS] Client disconnected: {client_id}")

    async def disconnect_client(self, client_id: str, reason: str = "Disconnected by server") -> bool:
        """
        Forcefully disconnect a client.

        Args:
            client_id: Client to disconnect
            reason: Reason message to send before closing

        Returns:
            True if client was disconnected
        """
        if client_id not in self._clients:
            return False

        client = self._clients[client_id]
        client.state = ClientState.DISCONNECTING

        # Send disconnect notice
        try:
            await self._send_to_client(client_id, {
                "type": "disconnect",
                "reason": reason
            })

            # Close WebSocket
            if hasattr(client.websocket, 'close'):
                await client.websocket.close(1000, reason)
        except Exception:
            pass  # Connection may already be closed

        await self._unregister_client(client_id)
        return True

    # =========================================================================
    # Message Handling - All Routed Through Spine
    # =========================================================================

    async def _handle_message(self, client: WebSocketClient, raw_message: str) -> None:
        """
        Handle incoming message from client.

        CRITICAL: All action messages are routed through spine.execute()
        for governance checks before processing.
        """
        client.message_count += 1
        client.last_message_at = datetime.now(timezone.utc).isoformat()

        try:
            message = json.loads(raw_message)
        except json.JSONDecodeError:
            await self._send_error(client.client_id, "Invalid JSON")
            return

        msg_type = message.get("type", "unknown")
        msg_id = message.get("id", f"msg-{uuid.uuid4().hex[:8]}")

        # Handle different message types
        if msg_type == "ping":
            await self._send_to_client(client.client_id, {
                "type": "pong",
                "id": msg_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        elif msg_type == "subscribe":
            await self._handle_subscribe(client, message, msg_id)

        elif msg_type == "unsubscribe":
            await self._handle_unsubscribe(client, message, msg_id)

        elif msg_type == "execute":
            # GOVERNANCE: Route through spine.execute()
            await self._handle_execute(client, message, msg_id)

        elif msg_type == "associate_head":
            await self._handle_associate_head(client, message, msg_id)

        elif msg_type == "status":
            await self._handle_status(client, msg_id)

        else:
            await self._send_error(client.client_id, f"Unknown message type: {msg_type}", msg_id)

    async def _handle_subscribe(self, client: WebSocketClient, message: Dict, msg_id: str) -> None:
        """Handle subscription request."""
        channels = message.get("channels", [])
        if isinstance(channels, str):
            channels = [channels]

        subscribed = []
        for channel in channels:
            if channel in [c.value for c in SubscriptionChannel]:
                client.subscriptions.add(channel)
                self._subscriptions[channel].add(client.client_id)
                subscribed.append(channel)

        await self._send_to_client(client.client_id, {
            "type": "subscribed",
            "id": msg_id,
            "channels": subscribed,
            "all_subscriptions": list(client.subscriptions)
        })

        self._log_entry(
            EntryType.ACTION,
            "ws_subscribe",
            client.client_id,
            {"channels": subscribed}
        )

    async def _handle_unsubscribe(self, client: WebSocketClient, message: Dict, msg_id: str) -> None:
        """Handle unsubscribe request."""
        channels = message.get("channels", [])
        if isinstance(channels, str):
            channels = [channels]

        unsubscribed = []
        for channel in channels:
            if channel in client.subscriptions:
                client.subscriptions.discard(channel)
                self._subscriptions.get(channel, set()).discard(client.client_id)
                unsubscribed.append(channel)

        await self._send_to_client(client.client_id, {
            "type": "unsubscribed",
            "id": msg_id,
            "channels": unsubscribed,
            "all_subscriptions": list(client.subscriptions)
        })

    async def _handle_execute(self, client: WebSocketClient, message: Dict, msg_id: str) -> None:
        """
        Handle execute request - ROUTES THROUGH SPINE FOR GOVERNANCE.

        This is the critical integration point. Every action from a
        WebSocket client must pass through spine.execute() which applies:
        - Dual lattice governance (Kyber/Dilithium + Sacred Tongues)
        - Sensitivity-based authorization
        - Full audit trail in ledger
        """
        command = message.get("command", {})

        # Ensure command has proper structure
        if not isinstance(command, dict):
            await self._send_error(client.client_id, "Command must be an object", msg_id)
            return

        # Add client context
        command["ws_client_id"] = client.client_id
        if client.head_id:
            command["head_id"] = client.head_id

        client.state = ClientState.BUSY

        try:
            # GOVERNANCE CHECK: Route through spine
            result = await self._spine.execute(command)

            # Send result back to client
            await self._send_to_client(client.client_id, {
                "type": "execute_result",
                "id": msg_id,
                "result": result
            })

            # Broadcast to relevant channels
            decision = result.get("decision", "ALLOW")
            await self._broadcast_to_channel(
                SubscriptionChannel.ACTIONS.value,
                {
                    "type": "action",
                    "client_id": client.client_id,
                    "action": command.get("action"),
                    "target": command.get("target", "")[:50],  # Truncate for broadcast
                    "decision": decision,
                    "success": result.get("success", False)
                },
                exclude_client=client.client_id  # Don't double-send to originator
            )

            if decision in ["DENY", "ESCALATE", "QUARANTINE"]:
                await self._broadcast_to_channel(
                    SubscriptionChannel.DECISIONS.value,
                    {
                        "type": "governance_decision",
                        "client_id": client.client_id,
                        "action": command.get("action"),
                        "decision": decision,
                        "trust_score": result.get("trust_score")
                    }
                )

        except Exception as e:
            await self._send_error(client.client_id, f"Execution failed: {str(e)}", msg_id)
            client.error_count += 1

        finally:
            client.state = ClientState.CONNECTED

    async def _handle_associate_head(self, client: WebSocketClient, message: Dict, msg_id: str) -> None:
        """Associate this WebSocket client with a HYDRA head."""
        head_id = message.get("head_id")

        if not head_id:
            await self._send_error(client.client_id, "head_id required", msg_id)
            return

        # Verify head exists in spine
        if head_id not in self._spine.heads:
            await self._send_error(client.client_id, f"Head {head_id} not found", msg_id)
            return

        client.head_id = head_id

        await self._send_to_client(client.client_id, {
            "type": "head_associated",
            "id": msg_id,
            "head_id": head_id,
            "head_info": {
                "ai_type": self._spine.heads[head_id].ai_type,
                "model": self._spine.heads[head_id].model,
                "callsign": self._spine.heads[head_id].callsign
            }
        })

        self._log_entry(
            EntryType.ACTION,
            "ws_associate_head",
            client.client_id,
            {"head_id": head_id}
        )

    async def _handle_status(self, client: WebSocketClient, msg_id: str) -> None:
        """Return server and client status."""
        await self._send_to_client(client.client_id, {
            "type": "status",
            "id": msg_id,
            "server": {
                "clients_connected": len(self._clients),
                "max_clients": self._max_clients,
                "active_heads": len(self._spine.heads),
                "active_limbs": len(self._spine.limbs),
                "running": self._running
            },
            "client": client.to_dict()
        })

    # =========================================================================
    # Broadcasting
    # =========================================================================

    async def broadcast(self, message: Dict[str, Any], channel: str = None) -> int:
        """
        Broadcast message to all clients or specific channel subscribers.

        Args:
            message: Message to broadcast
            channel: Optional channel to target (None = all connected clients)

        Returns:
            Number of clients message was sent to
        """
        if channel:
            return await self._broadcast_to_channel(channel, message)
        else:
            return await self._broadcast_all(message)

    async def _broadcast_all(self, message: Dict[str, Any]) -> int:
        """Broadcast to all connected clients."""
        sent = 0
        for client_id in list(self._clients.keys()):
            if await self._send_to_client(client_id, message):
                sent += 1
        return sent

    async def _broadcast_to_channel(
        self,
        channel: str,
        message: Dict[str, Any],
        exclude_client: str = None
    ) -> int:
        """Broadcast to all subscribers of a channel."""
        message["channel"] = channel
        message["timestamp"] = datetime.now(timezone.utc).isoformat()

        sent = 0
        subscribers = self._subscriptions.get(channel, set())

        # Also include "all" subscribers
        all_subscribers = self._subscriptions.get(SubscriptionChannel.ALL.value, set())
        target_clients = subscribers | all_subscribers

        for client_id in target_clients:
            if client_id != exclude_client:
                if await self._send_to_client(client_id, message):
                    sent += 1

        return sent

    async def broadcast_state_change(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        data: Dict[str, Any]
    ) -> int:
        """
        Broadcast a state change event to appropriate channels.

        Args:
            event_type: Type of event (e.g., "connected", "disconnected", "updated")
            entity_type: Type of entity (e.g., "head", "limb", "workflow")
            entity_id: ID of the entity
            data: Additional event data

        Returns:
            Number of clients notified
        """
        # Map entity types to channels
        channel_map = {
            "head": SubscriptionChannel.HEADS.value,
            "limb": SubscriptionChannel.LIMBS.value,
            "workflow": SubscriptionChannel.WORKFLOWS.value,
            "consensus": SubscriptionChannel.CONSENSUS.value,
            "spectral": SubscriptionChannel.SPECTRAL.value
        }

        channel = channel_map.get(entity_type, SubscriptionChannel.BROADCAST.value)

        message = {
            "type": "state_change",
            "event": event_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "data": data
        }

        return await self._broadcast_to_channel(channel, message)

    # =========================================================================
    # Client Communication
    # =========================================================================

    async def _send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Send message to specific client."""
        if client_id not in self._clients:
            return False

        client = self._clients[client_id]

        try:
            payload = json.dumps(message)

            if hasattr(client.websocket, 'send'):
                # websockets library
                await client.websocket.send(payload)
            elif hasattr(client.websocket, 'send_str'):
                # aiohttp
                await client.websocket.send_str(payload)
            else:
                return False

            return True

        except Exception as e:
            client.error_count += 1
            print(f"[WS] Send error to {client_id}: {e}")
            return False

    async def _send_error(self, client_id: str, error: str, msg_id: str = None) -> None:
        """Send error message to client."""
        await self._send_to_client(client_id, {
            "type": "error",
            "id": msg_id,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    # =========================================================================
    # Heartbeat & Maintenance
    # =========================================================================

    async def _heartbeat_loop(self) -> None:
        """Background task for client health checks."""
        while self._running:
            try:
                await asyncio.sleep(self._heartbeat_interval)

                # Check for stale clients
                now = datetime.now(timezone.utc)
                stale_threshold = self._heartbeat_interval * 3

                for client_id, client in list(self._clients.items()):
                    if client.last_message_at:
                        last_msg = datetime.fromisoformat(client.last_message_at.replace('Z', '+00:00'))
                        if (now - last_msg).total_seconds() > stale_threshold:
                            # Client hasn't responded, consider stale
                            client.state = ClientState.IDLE

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[WS] Heartbeat error: {e}")

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def on(self, event: str, handler: Callable) -> None:
        """
        Register event handler.

        Events:
        - connect: Client connected (client: WebSocketClient)
        - disconnect: Client disconnected (client: WebSocketClient)
        - message: Any message received (client, message)
        """
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    async def _emit(self, event: str, *args) -> None:
        """Emit event to registered handlers."""
        if event in self._handlers:
            for handler in self._handlers[event]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(*args)
                    else:
                        handler(*args)
                except Exception as e:
                    print(f"[WS] Handler error for {event}: {e}")

    # =========================================================================
    # Status & Info
    # =========================================================================

    def get_clients(self) -> List[Dict[str, Any]]:
        """Get list of all connected clients."""
        return [client.to_dict() for client in self._clients.values()]

    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get info for specific client."""
        if client_id in self._clients:
            return self._clients[client_id].to_dict()
        return None

    def get_channel_subscribers(self, channel: str) -> List[str]:
        """Get list of client IDs subscribed to a channel."""
        return list(self._subscriptions.get(channel, set()))

    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics."""
        return {
            "running": self._running,
            "total_clients": len(self._clients),
            "max_clients": self._max_clients,
            "subscriptions": {
                channel: len(clients)
                for channel, clients in self._subscriptions.items()
                if clients
            },
            "clients_by_state": {
                state.value: sum(1 for c in self._clients.values() if c.state == state)
                for state in ClientState
            }
        }

    # =========================================================================
    # Helpers
    # =========================================================================

    def _log_entry(
        self,
        entry_type: EntryType,
        action: str,
        target: str,
        payload: Dict[str, Any],
        decision: str = None,
        score: float = None
    ) -> str:
        """Log entry to ledger."""
        entry = LedgerEntry(
            id=f"ws-{uuid.uuid4().hex[:8]}",
            entry_type=entry_type.value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            head_id=None,
            limb_id=None,
            action=action,
            target=target,
            payload=payload,
            decision=decision,
            score=score
        )
        return self._ledger.write(entry)


# =============================================================================
# Factory Functions
# =============================================================================

def create_websocket_manager(
    spine: 'HydraSpine',
    **kwargs
) -> WebSocketManager:
    """
    Create a WebSocket manager for a HYDRA spine.

    Args:
        spine: HydraSpine instance to integrate with
        **kwargs: Additional WebSocketManager configuration

    Returns:
        Configured WebSocketManager instance
    """
    return WebSocketManager(spine, **kwargs)


# =============================================================================
# Standalone Server Entry Point
# =============================================================================

async def run_websocket_server(
    host: str = "0.0.0.0",
    port: int = 8765,
    scbe_url: str = "http://127.0.0.1:8080"
) -> None:
    """
    Run standalone WebSocket server with a new HydraSpine.

    For development/testing purposes.
    """
    from .spine import HydraSpine

    spine = HydraSpine(scbe_url=scbe_url)
    ws_manager = WebSocketManager(spine)

    try:
        await ws_manager.start(host, port)
    except KeyboardInterrupt:
        print("\n[WS] Interrupted")
    finally:
        await ws_manager.stop()


if __name__ == "__main__":
    asyncio.run(run_websocket_server())
