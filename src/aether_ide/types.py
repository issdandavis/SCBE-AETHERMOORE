"""Shared types for AetherIDE.

@layer Layer 13
@component AetherIDE.Types
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

ActionKind = Literal[
    "edit", "save", "run", "test", "search", "chat",
    "commit", "deploy", "refactor", "review",
]


@dataclass
class IDEAction:
    """An IDE action to be governed."""
    kind: ActionKind
    content: str
    file_path: Optional[str] = None
    tongue_hint: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IDEEvent:
    """Record of a governed IDE event."""
    action: IDEAction
    decision: str  # ALLOW / QUARANTINE / DENY
    encoder_result: Any
    timestamp: float = 0.0
    session_id: str = ""


@dataclass
class IDEConfig:
    """Configuration for an AetherIDE session."""
    initial_mode: str = "ENGINEERING"
    initial_zone: str = "HOT"
    chemistry_threat_level: int = 3
    auto_improve: bool = True
    coherence_threshold: float = 0.55
    n8n_bridge_url: str = "http://127.0.0.1:8001"
    pad_store_path: str = "artifacts/aether_ide/pads.db"


@dataclass
class SessionState:
    """Snapshot of IDE session state."""
    session_id: str
    mode: str
    zone: str
    coherence: float
    encode_count: int
    event_count: int
    deny_count: int
    quarantine_count: int
    allow_count: int
    active_spins: int
    improvement_tasks_pending: int
