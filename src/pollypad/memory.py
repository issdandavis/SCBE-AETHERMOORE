"""
Persistent Memory — The Octopus Nervous System
================================================

Memory lives WHERE it's used. Not centralized. Distributed.
Every memory cell has a 6D address:

  [tongue, weight, context, time, intent, instruction]

You already know 2 coordinates by design (tongue + weight).
Context/time/intent/instructions resolve the other 4 immediately.
That's not search — that's addressing. O(1) amortized.

Every interaction creates a memory cell.
Every memory cell is a potential training pair.
Memory persists across sessions via JSONL files.

@patent USPTO #63/961,403
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# Sacred Tongue weights (phi-scaled)
PHI = 1.618033988749895
TONGUE_WEIGHTS = {
    "KO": 1.0,
    "AV": PHI,
    "RU": PHI ** 2,
    "CA": PHI ** 3,
    "UM": PHI ** 4,
    "DR": PHI ** 5,
}

# Context categories
CONTEXTS = [
    "conversation", "code", "research", "creative",
    "commerce", "governance", "planning", "debug",
]

# Intent categories
INTENTS = [
    "ask", "tell", "create", "modify", "delete",
    "search", "analyze", "decide", "play", "learn",
]


# ---------------------------------------------------------------------------
#  6D Address
# ---------------------------------------------------------------------------

@dataclass
class SixDAddress:
    """
    6-dimensional address in the semantic storage space.

    Dimensions:
      1. tongue:      Sacred Tongue (KO/AV/RU/CA/UM/DR) — KNOWN BY DESIGN
      2. weight:      Phi-scaled tongue weight — KNOWN BY DESIGN
      3. context:     What domain is this? (code, research, etc.)
      4. time_bucket: When? (quantized to session/hour/day)
      5. intent:      What's the user trying to do?
      6. instruction: Specific directive hash (first 8 chars)

    First 2 coords are known from the encoding.
    Next 4 are derived from the interaction context.
    This means retrieval is addressing, not searching.
    """
    tongue: str
    weight: float
    context: str
    time_bucket: str
    intent: str
    instruction_hash: str

    @classmethod
    def from_interaction(
        cls,
        text: str,
        context: str = "conversation",
        intent: str = "tell",
    ) -> "SixDAddress":
        """
        Build a 6D address from an interaction.
        Tongue is classified from content. Weight is automatic.
        """
        tongue = cls._classify_tongue(text)
        weight = TONGUE_WEIGHTS[tongue]
        time_bucket = time.strftime("%Y-%m-%d-%H")
        instruction_hash = hashlib.sha256(text.encode()).hexdigest()[:8]

        return cls(
            tongue=tongue,
            weight=weight,
            context=context,
            time_bucket=time_bucket,
            intent=intent,
            instruction_hash=instruction_hash,
        )

    @staticmethod
    def _classify_tongue(text: str) -> str:
        """Quick tongue classification from text content."""
        t = text.lower()
        # KO = authority/command, AV = creative/vision, RU = logic/structure,
        # CA = computation/math, UM = emotion/intuition, DR = meta/governance
        scores = {
            "KO": sum(1 for w in ["do", "run", "execute", "build", "make", "create", "start"] if w in t),
            "AV": sum(1 for w in ["imagine", "design", "story", "visual", "art", "color", "feel"] if w in t),
            "RU": sum(1 for w in ["analyze", "structure", "logic", "reason", "plan", "organize"] if w in t),
            "CA": sum(1 for w in ["calculate", "compute", "math", "number", "algorithm", "code"] if w in t),
            "UM": sum(1 for w in ["think", "wonder", "maybe", "could", "sense", "vibe", "mood"] if w in t),
            "DR": sum(1 for w in ["govern", "rule", "law", "policy", "meta", "system", "guard"] if w in t),
        }
        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return "KO"  # Default to authority tongue
        return best

    def to_tuple(self) -> Tuple:
        return (self.tongue, self.weight, self.context,
                self.time_bucket, self.intent, self.instruction_hash)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tongue": self.tongue,
            "weight": self.weight,
            "context": self.context,
            "time_bucket": self.time_bucket,
            "intent": self.intent,
            "instruction_hash": self.instruction_hash,
        }

    def distance_to(self, other: "SixDAddress") -> float:
        """6D distance — weighted by dimension importance."""
        d = 0.0
        # Dim 1: tongue match (0 or 1)
        d += 0.0 if self.tongue == other.tongue else 2.0
        # Dim 2: weight distance (normalized by max weight)
        d += abs(self.weight - other.weight) / TONGUE_WEIGHTS["DR"]
        # Dim 3: context match
        d += 0.0 if self.context == other.context else 1.0
        # Dim 4: time proximity (same bucket = 0, otherwise scaled)
        d += 0.0 if self.time_bucket == other.time_bucket else 0.5
        # Dim 5: intent match
        d += 0.0 if self.intent == other.intent else 0.8
        # Dim 6: instruction similarity (hash comparison)
        common = sum(a == b for a, b in zip(self.instruction_hash, other.instruction_hash))
        d += (8 - common) / 8.0
        return d


# ---------------------------------------------------------------------------
#  Memory Cell
# ---------------------------------------------------------------------------

@dataclass
class MemoryCell:
    """
    One unit of persistent memory — one thing Polly remembers.

    Each cell has a 6D address (for retrieval) and content.
    Cells can be conversation turns, code snippets, decisions,
    observations, reflections — anything.
    """
    address: SixDAddress
    content: str
    role: str = "user"         # user, assistant, system, observation
    cell_type: str = "message" # message, code, decision, fact, reflection
    importance: float = 0.5    # 0.0 to 1.0 — how important is this memory?
    created_at: float = field(default_factory=time.time)
    accessed_count: int = 0
    last_accessed: Optional[float] = None
    cell_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.cell_id:
            raw = f"{self.content[:50]}:{self.created_at}"
            self.cell_id = hashlib.sha256(raw.encode()).hexdigest()[:16]

    def access(self) -> str:
        """Read this memory — updates access tracking."""
        self.accessed_count += 1
        self.last_accessed = time.time()
        return self.content

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "address": self.address.to_dict(),
            "content": self.content,
            "role": self.role,
            "cell_type": self.cell_type,
            "importance": self.importance,
            "created_at": self.created_at,
            "accessed_count": self.accessed_count,
            "metadata": self.metadata,
        }

    def to_jsonl(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MemoryCell":
        addr = SixDAddress(**d["address"])
        return cls(
            address=addr,
            content=d["content"],
            role=d.get("role", "user"),
            cell_type=d.get("cell_type", "message"),
            importance=d.get("importance", 0.5),
            created_at=d.get("created_at", time.time()),
            accessed_count=d.get("accessed_count", 0),
            cell_id=d.get("cell_id", ""),
            metadata=d.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
#  Memory Query
# ---------------------------------------------------------------------------

@dataclass
class MemoryQuery:
    """Query for retrieving memories from the 6D space."""
    tongue: Optional[str] = None
    context: Optional[str] = None
    intent: Optional[str] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    keyword: Optional[str] = None
    cell_type: Optional[str] = None
    max_results: int = 10
    min_importance: float = 0.0


# ---------------------------------------------------------------------------
#  Persistent Memory
# ---------------------------------------------------------------------------

class PersistentMemory:
    """
    The distributed nervous system — persistent memory across sessions.

    Stores memories as MemoryCells with 6D addresses.
    Retrieval uses addressing (not search): 2 coords known by design,
    4 derived from context. Finding a memory = resolving its address.

    Persistence: JSONL files organized by tongue and time bucket.
    This means the file structure IS the first 2 coordinates of the index.
    """

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "artifacts", "pollypad", "memory"
        )
        self.cells: List[MemoryCell] = []
        self._index: Dict[str, List[int]] = {}  # tongue → list of cell indices

    def remember(self, cell: MemoryCell) -> MemoryCell:
        """Store a memory. Returns the stored cell."""
        idx = len(self.cells)
        self.cells.append(cell)

        # Index by tongue (first coordinate — known by design)
        tongue = cell.address.tongue
        if tongue not in self._index:
            self._index[tongue] = []
        self._index[tongue].append(idx)

        return cell

    def remember_text(
        self, text: str, role: str = "user",
        context: str = "conversation", intent: str = "tell",
        importance: float = 0.5, cell_type: str = "message",
    ) -> MemoryCell:
        """Convenience: create and store a memory from raw text."""
        address = SixDAddress.from_interaction(text, context, intent)
        cell = MemoryCell(
            address=address,
            content=text,
            role=role,
            cell_type=cell_type,
            importance=importance,
        )
        return self.remember(cell)

    def recall(self, query: MemoryQuery) -> List[MemoryCell]:
        """
        Recall memories matching a query.

        Uses 6D addressing: start with tongue index (O(1)),
        then filter by remaining coordinates.
        """
        # Start with tongue index if specified (O(1) lookup)
        if query.tongue and query.tongue in self._index:
            candidates = [self.cells[i] for i in self._index[query.tongue]]
        else:
            candidates = self.cells

        results = []
        for cell in candidates:
            # Filter by context
            if query.context and cell.address.context != query.context:
                continue
            # Filter by intent
            if query.intent and cell.address.intent != query.intent:
                continue
            # Filter by time range
            if query.time_start and cell.address.time_bucket < query.time_start:
                continue
            if query.time_end and cell.address.time_bucket > query.time_end:
                continue
            # Filter by keyword
            if query.keyword and query.keyword.lower() not in cell.content.lower():
                continue
            # Filter by type
            if query.cell_type and cell.cell_type != query.cell_type:
                continue
            # Filter by importance
            if cell.importance < query.min_importance:
                continue

            results.append(cell)

        # Sort by importance (descending), then recency
        results.sort(key=lambda c: (-c.importance, -c.created_at))
        return results[:query.max_results]

    def recall_nearest(self, address: SixDAddress, k: int = 5) -> List[Tuple[float, MemoryCell]]:
        """
        Find k nearest memories in 6D space.
        This IS the O(1)-amortized retrieval the user described:
        tongue+weight narrow to a small subset, then 4D scan.
        """
        # Start with tongue match (known by design)
        if address.tongue in self._index:
            candidates = [self.cells[i] for i in self._index[address.tongue]]
        else:
            candidates = self.cells

        # Compute distances and sort
        distances = []
        for cell in candidates:
            d = address.distance_to(cell.address)
            distances.append((d, cell))

        distances.sort(key=lambda x: x[0])
        return distances[:k]

    def conversation_window(self, n: int = 20) -> List[MemoryCell]:
        """Get the last N messages (for conversation context)."""
        messages = [c for c in self.cells if c.cell_type == "message"]
        return messages[-n:]

    # -------------------------------------------------------------------
    #  Persistence
    # -------------------------------------------------------------------

    def save(self) -> str:
        """
        Save all memories to disk.
        File structure mirrors the 6D address: tongue/time_bucket.jsonl
        This means the filesystem IS the first 2 coordinates of the index.
        """
        os.makedirs(self.data_dir, exist_ok=True)

        # Group by tongue
        by_tongue: Dict[str, List[MemoryCell]] = {}
        for cell in self.cells:
            t = cell.address.tongue
            if t not in by_tongue:
                by_tongue[t] = []
            by_tongue[t].append(cell)

        files_written = 0
        for tongue, cells in by_tongue.items():
            tongue_dir = os.path.join(self.data_dir, tongue)
            os.makedirs(tongue_dir, exist_ok=True)

            # Group by time bucket within tongue
            by_time: Dict[str, List[MemoryCell]] = {}
            for cell in cells:
                tb = cell.address.time_bucket
                if tb not in by_time:
                    by_time[tb] = []
                by_time[tb].append(cell)

            for time_bucket, bucket_cells in by_time.items():
                path = os.path.join(tongue_dir, f"{time_bucket}.jsonl")
                with open(path, "w") as f:
                    for cell in bucket_cells:
                        f.write(cell.to_jsonl() + "\n")
                files_written += 1

        return self.data_dir

    def load(self) -> int:
        """Load memories from disk. Returns count loaded."""
        if not os.path.exists(self.data_dir):
            return 0

        loaded = 0
        for tongue_name in os.listdir(self.data_dir):
            tongue_dir = os.path.join(self.data_dir, tongue_name)
            if not os.path.isdir(tongue_dir):
                continue
            for filename in os.listdir(tongue_dir):
                if not filename.endswith(".jsonl"):
                    continue
                path = os.path.join(tongue_dir, filename)
                with open(path) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        d = json.loads(line)
                        cell = MemoryCell.from_dict(d)
                        self.remember(cell)
                        loaded += 1

        return loaded

    # -------------------------------------------------------------------
    #  Stats
    # -------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        tongue_counts = {}
        for tongue, indices in self._index.items():
            tongue_counts[tongue] = len(indices)

        return {
            "total_memories": len(self.cells),
            "by_tongue": tongue_counts,
            "unique_contexts": len(set(c.address.context for c in self.cells)),
            "unique_intents": len(set(c.address.intent for c in self.cells)),
            "avg_importance": sum(c.importance for c in self.cells) / max(len(self.cells), 1),
        }
