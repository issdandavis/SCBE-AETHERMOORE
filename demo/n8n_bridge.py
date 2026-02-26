#!/usr/bin/env python3
"""
AetherNet Bridge — n8n <-> Aethermoor Game
==========================================

The AetherNet is a pseudo-internet for AI agents inside the game world.
n8n workflows are the "network protocols" — NPC communication, training
data routing, world events, and TV broadcasts all flow through here.

Outbound: Game events -> n8n webhook URLs (async via background thread)
Inbound:  n8n actions -> game action queue (polled each frame)

In-game lore: The AetherNet is the crystalline data lattice connecting
Aethermoor's floating islands. Polly monitors it from the Wingscroll
Archive. All traffic is filtered through the Six Sacred Tongues.

Toggle: F9 in-game, or set N8N_WEBHOOK_URLS env var.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger("aethernet")


# ---------------------------------------------------------------------------
# Event Types (outbound: game -> n8n)
# ---------------------------------------------------------------------------
class GameEventType(str, Enum):
    BATTLE_WON = "battle_won"
    BATTLE_LOST = "battle_lost"
    EVOLUTION = "evolution"
    GACHA_PULL = "gacha_pull"
    SCENE_TRANSITION = "scene_transition"
    CHOICE_MADE = "choice_made"
    LEVEL_UP = "level_up"
    DEATH = "death"
    QUEST_COMPLETE = "quest_complete"
    NPC_DIALOGUE = "npc_dialogue"
    DUNGEON_ENTERED = "dungeon_entered"
    OVERWORLD_ENTERED = "overworld_entered"
    TRAINING_BATCH = "training_batch"       # SFT/DPO pairs ready
    TV_BROADCAST = "tv_broadcast"           # Custom TV show event
    WORLD_BUILD = "world_build"             # Player-created world content
    TONGUE_MASTERED = "tongue_mastered"     # Sacred Tongue proficiency milestone
    DUNGEON_FLOOR_CLEARED = "dungeon_floor_cleared"  # Tower floor completed
    BOSS_DEFEATED = "boss_defeated"         # Boss encounter won
    NPC_DIALOGUE_COMPLETE = "npc_dialogue_complete"  # Finished talking to NPC
    COMPANION_EVOLVED = "companion_evolved" # Party member evolved stage
    QUEST_PROGRESS = "quest_progress"       # Quest objective advanced


@dataclass
class GameEvent:
    """A game event to dispatch to n8n (AetherNet packet)."""
    event_type: str
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "source": "aethernet",
            **self.data,
        }


# ---------------------------------------------------------------------------
# Action Types (inbound: n8n -> game)
# ---------------------------------------------------------------------------
class GameActionType(str, Enum):
    SPAWN_ENEMY = "spawn_enemy"
    GIVE_ITEM = "give_item"
    TRIGGER_SCENE = "trigger_scene"
    SEND_DIALOGUE = "send_dialogue"
    MODIFY_STAT = "modify_stat"
    TV_SHOW = "tv_show"                 # Push a TV broadcast into the game
    TRAINING_RESULT = "training_result"  # HF training metrics back to game
    WORLD_EVENT = "world_event"         # n8n-generated world event
    FORCE_GACHA = "force_gacha"         # Trigger a gacha pull for the player
    BUFF_PARTY = "buff_party"           # Apply temporary buff to entire party
    ANNOUNCE = "announce"               # Show an AetherNet announcement overlay
    DUNGEON_MODIFIER = "dungeon_modifier"  # Modify dungeon difficulty/theme


@dataclass
class GameAction:
    """An action received from n8n to apply in the game."""
    action_type: str
    action_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    received_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# GameEventBus (AetherNet Core)
# ---------------------------------------------------------------------------
class GameEventBus:
    """
    Non-blocking bridge between Pygame game loop and n8n webhooks.

    Outbound dispatch uses a background daemon thread with urllib.
    Inbound actions are queued via put_action() (called from FastAPI)
    and drained each frame via drain_actions().

    Lore: This is the AetherNet relay node. Each webhook URL is an
    island endpoint on the crystalline lattice.
    """

    def __init__(
        self,
        webhook_urls: Optional[List[str]] = None,
        enabled: bool = False,
        dispatch_timeout: float = 5.0,
        max_queue_size: int = 256,
    ):
        self.webhook_urls: List[str] = webhook_urls or []
        self.enabled: bool = enabled
        self.dispatch_timeout: float = dispatch_timeout

        # Outbound: background thread drains and POSTs
        self._outbound: queue.Queue[GameEvent] = queue.Queue(maxsize=max_queue_size)
        self._dispatch_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Inbound: FastAPI pushes here, game loop drains
        self._inbound: queue.Queue[GameAction] = queue.Queue(maxsize=max_queue_size)

        # TV broadcast buffer (most recent broadcasts for in-game display)
        self.tv_buffer: List[Dict[str, Any]] = []
        self.tv_max_buffer: int = 10

        # Stats
        self.events_sent: int = 0
        self.events_failed: int = 0
        self.actions_received: int = 0
        self.actions_processed: int = 0
        self.packets_total: int = 0  # lore: total AetherNet packets

    # -- Lifecycle --

    def start(self) -> None:
        """Start the background dispatch thread (AetherNet goes online)."""
        if self._dispatch_thread and self._dispatch_thread.is_alive():
            return
        self._stop_event.clear()
        self._dispatch_thread = threading.Thread(
            target=self._dispatch_loop, daemon=True, name="aethernet-relay"
        )
        self._dispatch_thread.start()
        logger.info("AetherNet online (endpoints=%d)", len(self.webhook_urls))

    def stop(self) -> None:
        """Shut down the AetherNet relay."""
        self._stop_event.set()
        if self._dispatch_thread:
            self._dispatch_thread.join(timeout=3.0)
        logger.info(
            "AetherNet offline (sent=%d, failed=%d, actions=%d)",
            self.events_sent, self.events_failed, self.actions_processed,
        )

    def toggle(self) -> bool:
        """Toggle AetherNet. Returns new state."""
        self.enabled = not self.enabled
        if self.enabled and (not self._dispatch_thread or not self._dispatch_thread.is_alive()):
            self.start()
        return self.enabled

    # -- Outbound: game -> n8n --

    def emit(self, event_type: str, **data: Any) -> None:
        """Queue a game event for dispatch. Non-blocking; drops if full."""
        if not self.enabled:
            return
        self.packets_total += 1
        if not self.webhook_urls:
            return
        event = GameEvent(event_type=event_type, data=data)
        try:
            self._outbound.put_nowait(event)
        except queue.Full:
            logger.warning("AetherNet outbound full, dropping %s", event_type)

    def _dispatch_loop(self) -> None:
        """Background thread: drain outbound queue and POST to webhooks."""
        while not self._stop_event.is_set():
            try:
                event = self._outbound.get(timeout=0.5)
            except queue.Empty:
                continue
            self._send_to_webhooks(event)

    def _send_to_webhooks(self, event: GameEvent) -> None:
        """POST event JSON to all registered webhook URLs."""
        payload = json.dumps(event.to_dict()).encode("utf-8")
        for url in self.webhook_urls:
            try:
                req = Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urlopen(req, timeout=self.dispatch_timeout)
                self.events_sent += 1
            except (URLError, OSError) as exc:
                self.events_failed += 1
                logger.debug("AetherNet dispatch failed to %s: %s", url[:60], exc)

    # -- Inbound: n8n -> game --

    def put_action(self, action: GameAction) -> bool:
        """Enqueue an inbound action from n8n. Returns False if full."""
        try:
            self._inbound.put_nowait(action)
            self.actions_received += 1
            return True
        except queue.Full:
            return False

    def drain_actions(self) -> List[GameAction]:
        """Drain all pending inbound actions. Called once per game frame."""
        actions: List[GameAction] = []
        while True:
            try:
                actions.append(self._inbound.get_nowait())
            except queue.Empty:
                break
        self.actions_processed += len(actions)
        return actions

    # -- TV Broadcast System --

    def push_tv(self, show_name: str, content: str, channel: str = "AetherTV") -> None:
        """Add a TV broadcast to the buffer (displayed in-game)."""
        broadcast = {
            "show": show_name,
            "content": content,
            "channel": channel,
            "time": time.time(),
        }
        self.tv_buffer.append(broadcast)
        if len(self.tv_buffer) > self.tv_max_buffer:
            self.tv_buffer.pop(0)

    def latest_tv(self) -> Optional[Dict[str, Any]]:
        """Get the most recent TV broadcast."""
        return self.tv_buffer[-1] if self.tv_buffer else None

    # -- Config --

    def add_webhook(self, url: str) -> None:
        if url not in self.webhook_urls:
            self.webhook_urls.append(url)

    def remove_webhook(self, url: str) -> None:
        self.webhook_urls = [u for u in self.webhook_urls if u != url]

    def status(self) -> Dict[str, Any]:
        """AetherNet status (for dashboard and API)."""
        return {
            "online": self.enabled,
            "endpoints": len(self.webhook_urls),
            "packets_total": self.packets_total,
            "events_sent": self.events_sent,
            "events_failed": self.events_failed,
            "actions_received": self.actions_received,
            "actions_processed": self.actions_processed,
            "outbound_pending": self._outbound.qsize(),
            "inbound_pending": self._inbound.qsize(),
            "tv_broadcasts": len(self.tv_buffer),
        }


# ---------------------------------------------------------------------------
# Module-level singleton for cross-process sharing (game + API)
# ---------------------------------------------------------------------------
_SHARED_BUS: Optional[GameEventBus] = None


def get_shared_bus() -> Optional[GameEventBus]:
    """Get the shared AetherNet bus (None if game not running)."""
    return _SHARED_BUS


def set_shared_bus(bus: GameEventBus) -> None:
    """Set the shared AetherNet bus (called by the game on startup)."""
    global _SHARED_BUS
    _SHARED_BUS = bus


def create_bus_from_env() -> GameEventBus:
    """Create an AetherNet bus from environment variables."""
    urls_raw = os.environ.get("N8N_WEBHOOK_URLS", "")
    urls = [u.strip() for u in urls_raw.split(",") if u.strip()]
    bus = GameEventBus(webhook_urls=urls, enabled=bool(urls))
    set_shared_bus(bus)
    return bus


# ---------------------------------------------------------------------------
# Inbound HTTP server (n8n -> game)
# ---------------------------------------------------------------------------
_inbound_thread: Optional[threading.Thread] = None


def _run_inbound_server(port: int) -> None:
    """Minimal HTTP server so n8n can POST actions into the game."""
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # silence default logs
            logger.debug(fmt, *args)

        def do_GET(self):
            if self.path == "/health":
                bus = get_shared_bus()
                body = json.dumps(bus.status() if bus else {"online": False})
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body.encode())
            else:
                self.send_error(404)

        def do_POST(self):
            if self.path != "/action":
                self.send_error(404)
                return
            bus = get_shared_bus()
            if not bus:
                self.send_error(503, "Game not running")
                return
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                self.send_error(400, "Invalid JSON")
                return
            action = GameAction(
                action_type=data.get("action_type", ""),
                action_id=data.get("action_id", uuid.uuid4().hex[:12]),
                data=data.get("data", {}),
            )
            ok = bus.put_action(action)
            resp = json.dumps({"queued": ok, "action_id": action.action_id})
            self.send_response(200 if ok else 429)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp.encode())

    server = HTTPServer(("127.0.0.1", port), Handler)
    logger.info("AetherNet inbound server on http://127.0.0.1:%d", port)
    server.serve_forever()


def start_inbound_server(port: int = 9800) -> None:
    """Start the inbound HTTP server in a daemon thread.

    n8n can POST to http://127.0.0.1:9800/action with::

        {"action_type": "spawn_enemy", "data": {"name": "Glitch", "tongue": "DR", "hp": 80}}
        {"action_type": "announce", "data": {"text": "A rift opens..."}}
        {"action_type": "give_item", "data": {"item": "Gold", "amount": 50}}
        {"action_type": "buff_party", "data": {"stat": "attack", "delta": 5, "turns": 3}}

    GET http://127.0.0.1:9800/health returns bus status.
    """
    global _inbound_thread
    if _inbound_thread and _inbound_thread.is_alive():
        return
    port = int(os.environ.get("AETHERNET_PORT", str(port)))
    _inbound_thread = threading.Thread(
        target=_run_inbound_server, args=(port,), daemon=True, name="aethernet-inbound"
    )
    _inbound_thread.start()
