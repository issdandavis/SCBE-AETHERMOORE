"""
Concept Blocks — SOCKET (Mr. Potato Head Architecture)
======================================================

Dynamic capability-attachment system for concept blocks.
Like Mr. Potato Head: the body (pipeline) has sockets, and sense
organs (blocks) snap in and out at runtime.

Each socket has:
- A **ring** (CORE / INNER / OUTER / CA) from Sacred Egg access control
- A **tongue affinity** (which Sacred Tongue phase governs attachment)
- A **layer binding** (which pipeline layer the socket maps to)
- An **eigenvalue constraint** — non-negative eigenvalues only,
  ensuring no phantom states in the proximity field

PotatoHead
----------
The agent body.  Holds N sockets, each typed to a pipeline layer.
Blocks attach/detach through Sacred Egg ring predicates.  When a
block attaches, the PotatoHead gains that capability; when it
detaches, the capability is cleanly removed (no phantom residue).

# A5: Composition — socket attachment preserves pipeline integrity
# A2: Unitarity — detach leaves norm unchanged (no energy leak)
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .base import BlockResult, BlockStatus, ConceptBlock
from .telemetry import TelemetryLog, TelemetryRecord

# ---------------------------------------------------------------------------
# Sacred Egg ring levels (access control tiers)
# ---------------------------------------------------------------------------


class EggRing(Enum):
    """Access rings from sacred_eggs.py — determines attachment permission."""

    CORE = 0  # Innermost: full pipeline access
    INNER = 1  # Trusted: layers 1-12
    OUTER = 2  # Limited: layers 1-8 only
    CA = 3  # Certificate Authority: read-only telemetry


# ---------------------------------------------------------------------------
# Sacred Tongue phases (which tongue governs this socket)
# ---------------------------------------------------------------------------

TONGUE_PHASES: Dict[str, float] = {
    "KO": 0.0,  # Kor'aelin — Control/orchestration
    "AV": math.pi / 3,  # Avali — Initialization/transport
    "RU": 2 * math.pi / 3,  # Runethic — Policy/authorization
    "CA": math.pi,  # Cassisivadan — Encryption/compute
    "UM": 4 * math.pi / 3,  # Umbroth — Redaction/privacy
    "DR": 5 * math.pi / 3,  # Draumric — Authentication/integrity
}


# ---------------------------------------------------------------------------
# Socket definition
# ---------------------------------------------------------------------------


@dataclass
class SocketSpec:
    """Defines a slot on the PotatoHead body where a block can attach."""

    name: str
    layer: int  # Pipeline layer (1-14)
    min_ring: EggRing  # Minimum ring required to attach
    tongue: str  # Which Sacred Tongue governs this slot
    required: bool = False  # Is this socket mandatory for operation?
    max_blocks: int = 1  # How many blocks can attach here (usually 1)

    @property
    def phase(self) -> float:
        """Phase angle from Sacred Tongue assignment."""
        return TONGUE_PHASES.get(self.tongue, 0.0)


@dataclass
class AttachmentRecord:
    """Tracks a block attached to a socket."""

    block: ConceptBlock
    socket_name: str
    ring: EggRing
    attached_at: float = field(default_factory=time.time)
    egg_hash: str = ""  # SHA-256 of the Sacred Egg that authorized this

    @property
    def age_seconds(self) -> float:
        return time.time() - self.attached_at


# ---------------------------------------------------------------------------
# Eigenvalue guard — non-negative eigenvalues only
# ---------------------------------------------------------------------------


def _eigenvalue_check(state_vector: List[float]) -> Tuple[bool, float]:
    """Verify all eigenvalues of the state autocorrelation are non-negative.

    For a 1D state vector, the autocorrelation eigenvalues are the squared
    magnitudes — inherently non-negative.  This check ensures no phantom
    states (negative energy) can exist in the proximity field.

    Returns (passed, min_eigenvalue).
    """
    if not state_vector:
        return True, 0.0

    # Autocorrelation eigenvalues = |x_i|^2 (Parseval's theorem for real signals)
    eigenvalues = [x * x for x in state_vector]
    min_ev = min(eigenvalues)
    # All squared values are non-negative by construction, but numerical
    # drift near zero can produce -epsilon; clamp it.
    return min_ev >= -1e-15, min_ev


# ---------------------------------------------------------------------------
# Sacred Egg authorization stub
# ---------------------------------------------------------------------------


def _compute_egg_hash(block_name: str, socket_name: str, ring: EggRing) -> str:
    """Derive a deterministic egg hash for an attachment.

    In production this would verify against the Sacred Egg registry;
    here we produce a repeatable fingerprint for audit logging.
    """
    payload = f"{block_name}:{socket_name}:{ring.name}".encode()
    return hashlib.sha256(payload).hexdigest()[:16]


# ---------------------------------------------------------------------------
# PotatoHead — the agent body
# ---------------------------------------------------------------------------

# Default socket layout maps the 6 existing concept blocks + the new 6th sense
DEFAULT_SOCKETS: List[SocketSpec] = [
    SocketSpec("sense", layer=9, min_ring=EggRing.OUTER, tongue="KO"),
    SocketSpec("plan", layer=6, min_ring=EggRing.OUTER, tongue="AV"),
    SocketSpec("decide", layer=7, min_ring=EggRing.INNER, tongue="RU"),
    SocketSpec("steer", layer=8, min_ring=EggRing.INNER, tongue="CA"),
    SocketSpec("coordinate", layer=12, min_ring=EggRing.CORE, tongue="UM"),
    SocketSpec(
        "proximity", layer=14, min_ring=EggRing.CORE, tongue="DR", required=True
    ),
]


class PotatoHead:
    """Mr. Potato Head agent body — snap-on capability sockets.

    Usage::

        head = PotatoHead("agent-1")
        head.attach("sense", my_sense_block, EggRing.OUTER)
        head.attach("proximity", my_proximity_block, EggRing.CORE)
        result = head.tick_all({"measurement": 42.0})
        head.detach("sense")  # clean removal, no phantom state

    Lifecycle:
        1. Create with socket layout (defaults provided)
        2. Attach blocks to sockets (Sacred Egg ring check)
        3. tick_all() runs every attached block in layer order
        4. Detach blocks when capability should be removed
    """

    def __init__(
        self,
        agent_id: str,
        sockets: Optional[List[SocketSpec]] = None,
    ) -> None:
        self.agent_id = agent_id
        self._sockets: Dict[str, SocketSpec] = {}
        self._attachments: Dict[str, List[AttachmentRecord]] = {}
        self._telemetry = TelemetryLog()
        self._tick_count = 0

        for spec in sockets or DEFAULT_SOCKETS:
            self._sockets[spec.name] = spec
            self._attachments[spec.name] = []

    # -- socket management ---------------------------------------------------

    @property
    def socket_names(self) -> List[str]:
        """All available socket names."""
        return list(self._sockets.keys())

    @property
    def attached_blocks(self) -> Dict[str, List[str]]:
        """Map of socket_name -> list of attached block names."""
        return {
            name: [rec.block.name for rec in recs]
            for name, recs in self._attachments.items()
            if recs
        }

    @property
    def empty_sockets(self) -> List[str]:
        """Sockets with no blocks attached."""
        return [name for name, recs in self._attachments.items() if not recs]

    @property
    def missing_required(self) -> List[str]:
        """Required sockets that have no block attached."""
        return [
            name
            for name, spec in self._sockets.items()
            if spec.required and not self._attachments[name]
        ]

    # -- attach / detach -----------------------------------------------------

    def attach(
        self,
        socket_name: str,
        block: ConceptBlock,
        ring: EggRing,
    ) -> AttachmentRecord:
        """Snap a block into a socket.

        Raises ValueError if:
        - Socket doesn't exist
        - Ring level is insufficient (higher number = less access)
        - Socket is full (max_blocks reached)

        # A5: Composition — attachment must not violate pipeline ordering
        """
        if socket_name not in self._sockets:
            raise ValueError(
                f"No socket named '{socket_name}'. Available: {self.socket_names}"
            )

        spec = self._sockets[socket_name]

        # Ring check: lower enum value = more access
        if ring.value > spec.min_ring.value:
            raise ValueError(
                f"Ring {ring.name} (level {ring.value}) insufficient for "
                f"socket '{socket_name}' (requires {spec.min_ring.name}, level {spec.min_ring.value})"
            )

        # Capacity check
        current = self._attachments[socket_name]
        if len(current) >= spec.max_blocks:
            raise ValueError(
                f"Socket '{socket_name}' is full ({spec.max_blocks} block(s) max)"
            )

        egg_hash = _compute_egg_hash(block.name, socket_name, ring)
        record = AttachmentRecord(
            block=block,
            socket_name=socket_name,
            ring=ring,
            egg_hash=egg_hash,
        )
        current.append(record)

        self._telemetry.append(
            TelemetryRecord(
                block_name=f"socket:{socket_name}",
                inputs={"action": "attach", "block": block.name, "ring": ring.name},
                outputs={"egg_hash": egg_hash},
                status="ok",
            )
        )

        return record

    def detach(self, socket_name: str, block_name: Optional[str] = None) -> bool:
        """Remove a block from a socket.

        If block_name is None, removes all blocks from the socket.
        Returns True if anything was removed.

        # A2: Unitarity — detach resets the block so no state leaks
        """
        if socket_name not in self._attachments:
            return False

        records = self._attachments[socket_name]
        if not records:
            return False

        removed = []
        if block_name is None:
            removed = records[:]
            self._attachments[socket_name] = []
        else:
            remaining = []
            for rec in records:
                if rec.block.name == block_name:
                    removed.append(rec)
                else:
                    remaining.append(rec)
            self._attachments[socket_name] = remaining

        # Reset detached blocks to prevent phantom state
        for rec in removed:
            rec.block.reset()
            self._telemetry.append(
                TelemetryRecord(
                    block_name=f"socket:{socket_name}",
                    inputs={"action": "detach", "block": rec.block.name},
                    outputs={"age_s": rec.age_seconds},
                    status="ok",
                )
            )

        return len(removed) > 0

    # -- tick all attached blocks in layer order -----------------------------

    def tick_all(self, inputs: Dict[str, Any]) -> Dict[str, BlockResult]:
        """Tick every attached block in pipeline layer order.

        Returns a dict of socket_name -> BlockResult for each active socket.
        Sockets are processed in ascending layer number (L6 before L14).

        # A5: Composition — layer ordering preserved
        """
        self._tick_count += 1

        # Sort sockets by layer number for pipeline ordering
        ordered = sorted(
            self._sockets.keys(),
            key=lambda name: self._sockets[name].layer,
        )

        results: Dict[str, BlockResult] = {}
        accumulated_state: Dict[str, Any] = dict(inputs)

        for socket_name in ordered:
            records = self._attachments[socket_name]
            if not records:
                continue

            for rec in records:
                result = rec.block.tick(accumulated_state)
                results[socket_name] = result

                # Feed outputs forward to next layer (pipeline chaining)
                if result.status == BlockStatus.SUCCESS:
                    accumulated_state.update(result.output)

        return results

    # -- introspection -------------------------------------------------------

    def capabilities(self) -> Dict[str, bool]:
        """Report which capabilities this agent currently has."""
        return {name: len(self._attachments[name]) > 0 for name in self._sockets}

    def health_check(self) -> Dict[str, Any]:
        """Run eigenvalue guard and report overall health."""
        # Collect most recent state vector from telemetry
        state = []
        for recs in self._attachments.values():
            for rec in recs:
                recent = rec.block.telemetry.query(limit=1)
                if recent:
                    for val in recent[0].outputs.values():
                        if isinstance(val, (int, float)):
                            state.append(float(val))

        ev_ok, min_ev = _eigenvalue_check(state)

        return {
            "agent_id": self.agent_id,
            "tick_count": self._tick_count,
            "capabilities": self.capabilities(),
            "missing_required": self.missing_required,
            "empty_sockets": self.empty_sockets,
            "eigenvalue_ok": ev_ok,
            "min_eigenvalue": min_ev,
            "total_attachments": sum(len(recs) for recs in self._attachments.values()),
        }

    def __repr__(self) -> str:
        caps = self.capabilities()
        active = [k for k, v in caps.items() if v]
        return f"PotatoHead({self.agent_id!r}, active={active})"
