"""
SCBE Antenna System — Real-time governance telemetry broadcast.

Server-Sent Events (SSE) endpoint that streams:
- Governance decisions (ALLOW/QUARANTINE/DENY) as they happen
- Pipeline layer outputs (14-layer telemetry)
- System health heartbeats
- Breathing transform state

Think of it as a radio station where the signal IS the security telemetry.
Any client can connect to /antenna/stream and watch governance in real-time.

Usage:
    curl -N http://localhost:8000/antenna/stream
    curl http://localhost:8000/antenna/status
"""

import asyncio
import json
import time
from collections import deque
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

antenna_router = APIRouter(prefix="/antenna", tags=["Antenna (Telemetry)"])

# ============================================================================
# BROADCAST BUS
# ============================================================================

# Max listeners and buffer size
MAX_LISTENERS = 100
EVENT_BUFFER_SIZE = 500
HEARTBEAT_INTERVAL_SEC = 15


class AntennaBus:
    """
    In-memory broadcast bus for SSE telemetry.

    Events are pushed by the API (seal, retrieve, governance, attack sim)
    and broadcast to all connected SSE listeners.
    """

    def __init__(self, buffer_size: int = EVENT_BUFFER_SIZE):
        self._queues: list[asyncio.Queue] = []
        self._buffer: deque = deque(maxlen=buffer_size)
        self._total_events: int = 0
        self._total_connections: int = 0
        self._start_time: float = time.time()

    @property
    def listener_count(self) -> int:
        return len(self._queues)

    @property
    def total_events(self) -> int:
        return self._total_events

    @property
    def total_connections(self) -> int:
        return self._total_connections

    def subscribe(self) -> asyncio.Queue:
        """Create a new listener queue. Returns queue to read events from."""
        if len(self._queues) >= MAX_LISTENERS:
            # Evict oldest listener
            old = self._queues.pop(0)
            old.put_nowait(None)  # Signal disconnect
        q: asyncio.Queue = asyncio.Queue(maxsize=64)
        self._queues.append(q)
        self._total_connections += 1
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        """Remove a listener queue."""
        try:
            self._queues.remove(q)
        except ValueError:
            pass

    def broadcast(self, event_type: str, data: Dict[str, Any], source: str = "api") -> None:
        """Push an event to all listeners and the replay buffer."""
        event = {
            "type": event_type,
            "data": data,
            "source": source,
            "ts": time.time(),
            "seq": self._total_events,
        }
        self._total_events += 1
        self._buffer.append(event)

        dead_queues = []
        for q in self._queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead_queues.append(q)

        for q in dead_queues:
            self.unsubscribe(q)

    def recent_events(self, n: int = 50) -> list:
        """Get last N events from the buffer."""
        return list(self._buffer)[-n:]

    def status(self) -> Dict[str, Any]:
        return {
            "listeners": self.listener_count,
            "total_events": self._total_events,
            "total_connections": self._total_connections,
            "buffer_size": len(self._buffer),
            "uptime_seconds": int(time.time() - self._start_time),
        }


# Singleton bus
antenna_bus = AntennaBus()


# ============================================================================
# BROADCAST HELPERS (called from main.py endpoints)
# ============================================================================


def broadcast_governance_decision(
    decision: str,
    risk_prime: float,
    risk_base: float,
    harmonic: float,
    d_star: float,
    agent: str = "",
    context: str = "",
    endpoint: str = "",
) -> None:
    """Broadcast a governance decision event."""
    antenna_bus.broadcast(
        "governance_decision",
        {
            "decision": decision,
            "risk_prime": round(risk_prime, 6),
            "risk_base": round(risk_base, 6),
            "harmonic": round(harmonic, 6),
            "d_star": round(d_star, 6),
            "agent": agent,
            "context": context,
            "endpoint": endpoint,
        },
        source="pipeline",
    )


def broadcast_seal_event(agent: str, topic: str, decision: str, risk_score: float) -> None:
    """Broadcast a memory seal event."""
    antenna_bus.broadcast(
        "memory_sealed",
        {
            "agent": agent,
            "topic": topic,
            "decision": decision,
            "risk_score": round(risk_score, 6),
        },
        source="seal",
    )


def broadcast_retrieve_event(agent: str, context: str, decision: str, denied: bool) -> None:
    """Broadcast a memory retrieval event."""
    antenna_bus.broadcast(
        "memory_retrieved",
        {
            "agent": agent,
            "context": context,
            "decision": decision,
            "denied": denied,
        },
        source="retrieve",
    )


def broadcast_attack_sim(decision: str, risk_prime: float, agent: str = "malicious_bot") -> None:
    """Broadcast an attack simulation event."""
    antenna_bus.broadcast(
        "attack_simulated",
        {
            "decision": decision,
            "risk_prime": round(risk_prime, 6),
            "agent": agent,
        },
        source="attack_sim",
    )


def broadcast_system_event(event_name: str, detail: str = "") -> None:
    """Broadcast a system lifecycle event."""
    antenna_bus.broadcast(
        "system",
        {"event": event_name, "detail": detail},
        source="system",
    )


# ============================================================================
# SSE STREAMING ENDPOINT
# ============================================================================


def _format_sse(event: Dict[str, Any]) -> str:
    """Format an event as SSE wire format."""
    event_type = event.get("type", "message")
    data = json.dumps(event, separators=(",", ":"), default=str)
    return f"event: {event_type}\ndata: {data}\n\n"


async def _event_generator(
    q: asyncio.Queue,
    last_event_id: Optional[int],
) -> Any:
    """Async generator that yields SSE-formatted events."""
    # Replay missed events if client provides Last-Event-ID
    if last_event_id is not None:
        for event in antenna_bus.recent_events(EVENT_BUFFER_SIZE):
            if event["seq"] > last_event_id:
                yield _format_sse(event)

    # Send initial connection event
    yield _format_sse({
        "type": "connected",
        "data": {"message": "SCBE Antenna connected", "listeners": antenna_bus.listener_count},
        "ts": time.time(),
        "seq": -1,
    })

    heartbeat_counter = 0
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=HEARTBEAT_INTERVAL_SEC)
                if event is None:
                    # Disconnected by bus (evicted)
                    yield _format_sse({
                        "type": "disconnected",
                        "data": {"reason": "evicted"},
                        "ts": time.time(),
                        "seq": -1,
                    })
                    return
                yield _format_sse(event)
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                heartbeat_counter += 1
                yield f": heartbeat {heartbeat_counter}\n\n"
    except asyncio.CancelledError:
        return
    finally:
        antenna_bus.unsubscribe(q)


@antenna_router.get("/stream")
async def antenna_stream(
    last_event_id: Optional[int] = Query(None, alias="Last-Event-ID"),
):
    """
    ## Antenna Stream (SSE)

    Real-time Server-Sent Events stream of SCBE governance telemetry.

    Connect with any SSE client:
    ```
    curl -N http://localhost:8000/antenna/stream
    ```

    Events broadcast:
    - `governance_decision` — ALLOW/QUARANTINE/DENY with risk metrics
    - `memory_sealed` — Memory seal operations
    - `memory_retrieved` — Memory retrieval with governance outcome
    - `attack_simulated` — Attack simulation results
    - `system` — System lifecycle events (startup, shutdown)
    - `connected` — Initial connection acknowledgment

    Supports `Last-Event-ID` for reconnection replay.
    """
    q = antenna_bus.subscribe()
    return StreamingResponse(
        _event_generator(q, last_event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@antenna_router.get("/status")
async def antenna_status():
    """
    ## Antenna Status

    Current antenna bus statistics — listeners, total events, buffer state.
    """
    return {"status": "ok", "data": antenna_bus.status()}


@antenna_router.get("/recent")
async def antenna_recent(n: int = Query(50, ge=1, le=500)):
    """
    ## Recent Events

    Get the last N events from the antenna buffer (no SSE, JSON response).
    Useful for dashboards that need to backfill on page load.
    """
    events = antenna_bus.recent_events(n)
    return {"status": "ok", "count": len(events), "data": events}
