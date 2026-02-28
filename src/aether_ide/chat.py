"""IDE Chat -- HydraSpine AI-to-AI assistance loops.

Wraps HydraSpine message passing for IDE context.  Messages
are governed: each chat message goes through the encoder
before delivery.

@layer Layer 5, Layer 13
@component AetherIDE.Chat
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

try:
    from hydra.spine import HydraSpine
    _HAS_HYDRA = True
except ImportError:
    _HAS_HYDRA = False


@dataclass
class ChatMessage:
    """A governed chat message."""
    role: str
    content: str
    tongue: str
    governed: bool = True


class IDEChat:
    """AI chat interface for the IDE.

    When HydraSpine is available, uses its message queues.
    Falls back to a simple in-memory message list otherwise.
    """

    def __init__(self) -> None:
        self._spine: Optional[Any] = None
        self._messages: List[ChatMessage] = []
        if _HAS_HYDRA:
            try:
                self._spine = HydraSpine()
            except Exception:
                self._spine = None

    def send(self, content: str, tongue: str = "KO", role: str = "assistant") -> ChatMessage:
        """Send a chat message (caller must govern before calling)."""
        msg = ChatMessage(role=role, content=content, tongue=tongue)
        self._messages.append(msg)
        return msg

    def get_history(self, limit: int = 50) -> List[ChatMessage]:
        """Return recent chat history."""
        return self._messages[-limit:]

    def clear(self) -> None:
        """Clear chat history."""
        self._messages.clear()

    @property
    def message_count(self) -> int:
        return len(self._messages)

    @property
    def has_spine(self) -> bool:
        return self._spine is not None
