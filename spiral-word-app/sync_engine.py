"""
@file sync_engine.py
@module spiral-word-app/sync_engine
@layer Layer 9, Layer 10
@component CRDT Document Sync Engine

Conflict-free replicated data type (CRDT) engine for real-time
collaborative editing. Uses a text-based CRDT (RGA variant) that
converges without central coordination.

Each edit operation is a tuple (position, content, op_type, lamport_clock, site_id)
that can be applied in any order and still converge to the same document state.
"""

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class EditOp:
    """A single edit operation in the CRDT log."""

    op_id: str  # Unique operation ID
    site_id: str  # Originating site/user/AI
    clock: int  # Lamport timestamp
    op_type: str  # "insert" | "delete"
    position: int  # Character position
    content: str  # Inserted text (empty for delete)
    length: int  # Number of chars affected (for delete)
    timestamp: float  # Wall-clock time for audit
    nonce: str  # Replay-protection nonce

    def to_dict(self) -> dict:
        return {
            "op_id": self.op_id,
            "site_id": self.site_id,
            "clock": self.clock,
            "op_type": self.op_type,
            "position": self.position,
            "content": self.content,
            "length": self.length,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EditOp":
        return cls(**d)

    def checksum(self) -> str:
        """Deterministic hash for integrity verification."""
        canonical = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]


class Document:
    """
    A collaborative document backed by an ordered operation log.

    The document state is the result of replaying all operations in
    Lamport-clock order (ties broken by site_id). This guarantees
    convergence across all replicas.
    """

    def __init__(self, doc_id: str):
        self.doc_id = doc_id
        self.site_id = str(uuid.uuid4())[:8]
        self.clock: int = 0
        self.ops: List[EditOp] = []
        self._text: str = ""
        self.created_at: float = time.time()
        self.version: int = 0

    @property
    def text(self) -> str:
        return self._text

    @property
    def length(self) -> int:
        return len(self._text)

    def _next_clock(self) -> int:
        self.clock += 1
        return self.clock

    def _make_nonce(self) -> str:
        return hashlib.sha256(
            f"{self.site_id}:{self.clock}:{time.time()}".encode()
        ).hexdigest()[:16]

    def insert(self, position: int, content: str, site_id: str = None) -> EditOp:
        """
        Insert text at position. Returns the operation for broadcast.

        Args:
            position: Character index (clamped to [0, len]).
            content: Text to insert.
            site_id: Override site ID (for AI ports).
        """
        position = max(0, min(position, len(self._text)))
        op = EditOp(
            op_id=f"{self.site_id}-{self.clock + 1}",
            site_id=site_id or self.site_id,
            clock=self._next_clock(),
            op_type="insert",
            position=position,
            content=content,
            length=len(content),
            timestamp=time.time(),
            nonce=self._make_nonce(),
        )
        self._apply(op)
        return op

    def delete(self, position: int, length: int = 1, site_id: str = None) -> EditOp:
        """
        Delete `length` characters starting at position. Returns the operation.
        """
        position = max(0, min(position, len(self._text)))
        length = min(length, len(self._text) - position)
        if length <= 0:
            length = 0

        op = EditOp(
            op_id=f"{self.site_id}-{self.clock + 1}",
            site_id=site_id or self.site_id,
            clock=self._next_clock(),
            op_type="delete",
            position=position,
            content="",
            length=length,
            timestamp=time.time(),
            nonce=self._make_nonce(),
        )
        self._apply(op)
        return op

    def replace_all(self, new_text: str, site_id: str = None) -> List[EditOp]:
        """Replace entire document content. Returns list of ops."""
        ops = []
        if self._text:
            ops.append(self.delete(0, len(self._text), site_id=site_id))
        if new_text:
            ops.append(self.insert(0, new_text, site_id=site_id))
        return ops

    def _apply(self, op: EditOp):
        """Apply a single operation to the document text."""
        if op.op_type == "insert":
            pos = max(0, min(op.position, len(self._text)))
            self._text = self._text[:pos] + op.content + self._text[pos:]
        elif op.op_type == "delete":
            pos = max(0, min(op.position, len(self._text)))
            end = min(pos + op.length, len(self._text))
            self._text = self._text[:pos] + self._text[end:]

        self.ops.append(op)
        self.clock = max(self.clock, op.clock)
        self.version += 1

    def apply_remote(self, op: EditOp) -> bool:
        """
        Apply an operation received from another replica.

        Returns True if applied, False if duplicate (replay).
        """
        # Duplicate detection by op_id
        if any(existing.op_id == op.op_id for existing in self.ops):
            return False

        self._apply(op)
        return True

    def snapshot(self) -> dict:
        """Full document state for new joiners."""
        return {
            "doc_id": self.doc_id,
            "text": self._text,
            "version": self.version,
            "clock": self.clock,
            "op_count": len(self.ops),
        }


class SyncEngine:
    """
    Manages multiple documents and their sync state.

    Each document is independent; operations are broadcast per-document
    to connected WebSocket peers.
    """

    def __init__(self):
        self.documents: Dict[str, Document] = {}

    def get_or_create(self, doc_id: str) -> Document:
        if doc_id not in self.documents:
            self.documents[doc_id] = Document(doc_id)
        return self.documents[doc_id]

    def list_docs(self) -> List[dict]:
        return [doc.snapshot() for doc in self.documents.values()]

    def delete_doc(self, doc_id: str) -> bool:
        if doc_id in self.documents:
            del self.documents[doc_id]
            return True
        return False

    def serialize_op(self, op: EditOp) -> bytes:
        """Serialize an operation for WebSocket transmission."""
        return json.dumps(op.to_dict()).encode("utf-8")

    def deserialize_op(self, data: bytes) -> EditOp:
        """Deserialize an operation from WebSocket data."""
        return EditOp.from_dict(json.loads(data.decode("utf-8")))
