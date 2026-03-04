"""
Heart Vault — SQLite Knowledge Graph
======================================

The Heart Vault stores cultural, emotional, and literary knowledge as a
directed property graph backed by SQLite.  This gives the SCBE fleet
*qualitative* intelligence — metaphors, proverbs, emotional arcs, and
cultural idioms — to complement the quantitative governance layers.

Node types:
    EMOTION       — A named emotion with valence/arousal coordinates
    LITERARY      — A literary device (metaphor, simile, personification …)
    PROVERB       — A cultural proverb or idiom
    CONCEPT       — An abstract concept (time, death, love, justice …)
    SOURCE        — A data source (ATOMIC2020, Gutenberg, Wikiquote …)
    TONGUE        — A Sacred Tongue affinity marker

Edge types:
    EVOKES        — Literary device → Emotion  (this metaphor evokes …)
    MAPS_TO       — Concept → Concept          (metaphorical mapping)
    SOURCED_FROM  — Node → Source               (provenance)
    CATEGORISED   — Node → Tongue               (Sacred Tongue affinity)
    INTENSIFIES   — Emotion → Emotion           (escalation path)
    CONTRASTS     — Emotion → Emotion           (dialectic opposition)
    ILLUSTRATES   — Proverb → Concept           (what the proverb teaches)

Each node and edge can carry arbitrary JSON properties.

Integrates with:
    - SCBE Layer 1–2  (Complex Context: emotion/literary metadata)
    - SCBE Layer 3–4  (Poincaré Ball: valence/arousal → hyperbolic coords)
    - SCBE Layer 5    (Governance Mesh: Runethic quality gates)
    - MMCCL           (Heart Credits for contribution/consumption)
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
#  Enums
# ---------------------------------------------------------------------------

class NodeType(str, Enum):
    EMOTION = "EMOTION"
    LITERARY = "LITERARY"
    PROVERB = "PROVERB"
    CONCEPT = "CONCEPT"
    SOURCE = "SOURCE"
    TONGUE = "TONGUE"


class EdgeType(str, Enum):
    EVOKES = "EVOKES"
    MAPS_TO = "MAPS_TO"
    SOURCED_FROM = "SOURCED_FROM"
    CATEGORISED = "CATEGORISED"
    INTENSIFIES = "INTENSIFIES"
    CONTRASTS = "CONTRASTS"
    ILLUSTRATES = "ILLUSTRATES"


class TongueAffinity(str, Enum):
    """Which Sacred Tongue governs the ingestion/use of this data."""
    KO = "KO"  # Kor'aelin — Control: orchestrates ingestion
    AV = "AV"  # Avali     — I/O: manages API connections
    RU = "RU"  # Runethic  — Policy: quality gates on wisdom data
    CA = "CA"  # Cassisivadan — Bitcraft: structural analysis
    UM = "UM"  # Umbroth   — Veil: ambiguity & mystery handling
    DR = "DR"  # Draumric  — Structure: ordering & taxonomy


# ---------------------------------------------------------------------------
#  Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Node:
    """A node in the Heart Vault graph."""
    id: str
    node_type: NodeType
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)
    tongue: Optional[TongueAffinity] = None
    quality_score: float = 0.0    # Runethic gate score [0.0, 1.0]
    created_at: float = 0.0
    updated_at: float = 0.0

    def content_hash(self) -> str:
        """Deterministic hash for deduplication and chain integrity."""
        blob = json.dumps({
            "type": self.node_type.value,
            "label": self.label,
            "properties": self.properties,
        }, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()


@dataclass
class Edge:
    """A directed edge in the Heart Vault graph."""
    id: str
    edge_type: EdgeType
    source_id: str
    target_id: str
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0


# ---------------------------------------------------------------------------
#  Heart Vault Graph (SQLite-backed)
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS hv_nodes (
    id          TEXT PRIMARY KEY,
    node_type   TEXT NOT NULL,
    label       TEXT NOT NULL,
    properties  TEXT NOT NULL DEFAULT '{}',
    tongue      TEXT,
    quality_score REAL NOT NULL DEFAULT 0.0,
    content_hash TEXT,
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS hv_edges (
    id          TEXT PRIMARY KEY,
    edge_type   TEXT NOT NULL,
    source_id   TEXT NOT NULL REFERENCES hv_nodes(id),
    target_id   TEXT NOT NULL REFERENCES hv_nodes(id),
    weight      REAL NOT NULL DEFAULT 1.0,
    properties  TEXT NOT NULL DEFAULT '{}',
    created_at  REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_hv_nodes_type ON hv_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_hv_nodes_tongue ON hv_nodes(tongue);
CREATE INDEX IF NOT EXISTS idx_hv_nodes_label ON hv_nodes(label);
CREATE INDEX IF NOT EXISTS idx_hv_nodes_hash ON hv_nodes(content_hash);
CREATE INDEX IF NOT EXISTS idx_hv_edges_type ON hv_edges(edge_type);
CREATE INDEX IF NOT EXISTS idx_hv_edges_source ON hv_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_hv_edges_target ON hv_edges(target_id);

CREATE TABLE IF NOT EXISTS hv_heart_credits (
    id          TEXT PRIMARY KEY,
    agent_id    TEXT NOT NULL,
    action      TEXT NOT NULL,
    node_id     TEXT REFERENCES hv_nodes(id),
    amount      REAL NOT NULL,
    denomination TEXT NOT NULL DEFAULT 'KO',
    timestamp   REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_hv_credits_agent ON hv_heart_credits(agent_id);
"""


class HeartVaultGraph:
    """
    SQLite-backed cultural knowledge graph.

    Usage::

        vault = HeartVaultGraph("heart_vault.db")

        # Add emotion nodes
        joy = vault.add_node(NodeType.EMOTION, "joy",
            properties={"valence": 0.8, "arousal": 0.6},
            tongue=TongueAffinity.KO)

        # Add literary device
        metaphor = vault.add_node(NodeType.LITERARY, "Time is a thief",
            properties={"device": "metaphor", "vehicle": "thief", "tenor": "time"},
            tongue=TongueAffinity.CA)

        # Connect: metaphor evokes loss
        loss = vault.add_node(NodeType.EMOTION, "loss",
            properties={"valence": -0.7, "arousal": 0.5})
        vault.add_edge(EdgeType.EVOKES, metaphor.id, loss.id, weight=0.9)

        # Query: what emotions does "Time is a thief" evoke?
        evoked = vault.neighbors(metaphor.id, edge_type=EdgeType.EVOKES)
    """

    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    @contextmanager
    def _tx(self) -> Generator[sqlite3.Cursor, None, None]:
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    # -- Nodes ---------------------------------------------------------------

    def add_node(
        self,
        node_type: NodeType,
        label: str,
        *,
        properties: Optional[Dict[str, Any]] = None,
        tongue: Optional[TongueAffinity] = None,
        quality_score: float = 0.0,
        node_id: Optional[str] = None,
    ) -> Node:
        """Insert a node. Returns the new Node (with generated id if not given)."""
        now = time.time()
        props = properties or {}
        node = Node(
            id=node_id or uuid.uuid4().hex[:16],
            node_type=node_type,
            label=label,
            properties=props,
            tongue=tongue,
            quality_score=quality_score,
            created_at=now,
            updated_at=now,
        )
        with self._tx() as cur:
            cur.execute(
                """INSERT INTO hv_nodes
                   (id, node_type, label, properties, tongue,
                    quality_score, content_hash, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    node.id,
                    node.node_type.value,
                    node.label,
                    json.dumps(node.properties, sort_keys=True),
                    node.tongue.value if node.tongue else None,
                    node.quality_score,
                    node.content_hash(),
                    node.created_at,
                    node.updated_at,
                ),
            )
        return node

    def get_node(self, node_id: str) -> Optional[Node]:
        """Retrieve a node by ID."""
        cur = self._conn.execute(
            "SELECT id, node_type, label, properties, tongue, "
            "quality_score, created_at, updated_at FROM hv_nodes WHERE id=?",
            (node_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return Node(
            id=row[0],
            node_type=NodeType(row[1]),
            label=row[2],
            properties=json.loads(row[3]),
            tongue=TongueAffinity(row[4]) if row[4] else None,
            quality_score=row[5],
            created_at=row[6],
            updated_at=row[7],
        )

    def find_nodes(
        self,
        *,
        node_type: Optional[NodeType] = None,
        tongue: Optional[TongueAffinity] = None,
        label_contains: Optional[str] = None,
        min_quality: float = 0.0,
        limit: int = 100,
    ) -> List[Node]:
        """Search nodes with optional filters."""
        clauses: List[str] = ["quality_score >= ?"]
        params: List[Any] = [min_quality]
        if node_type:
            clauses.append("node_type = ?")
            params.append(node_type.value)
        if tongue:
            clauses.append("tongue = ?")
            params.append(tongue.value)
        if label_contains:
            clauses.append("label LIKE ?")
            params.append(f"%{label_contains}%")
        params.append(limit)

        sql = (
            "SELECT id, node_type, label, properties, tongue, "
            "quality_score, created_at, updated_at FROM hv_nodes "
            f"WHERE {' AND '.join(clauses)} "
            "ORDER BY quality_score DESC LIMIT ?"
        )
        rows = self._conn.execute(sql, params).fetchall()
        return [
            Node(
                id=r[0],
                node_type=NodeType(r[1]),
                label=r[2],
                properties=json.loads(r[3]),
                tongue=TongueAffinity(r[4]) if r[4] else None,
                quality_score=r[5],
                created_at=r[6],
                updated_at=r[7],
            )
            for r in rows
        ]

    def update_node(
        self,
        node_id: str,
        *,
        label: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        quality_score: Optional[float] = None,
        tongue: Optional[TongueAffinity] = None,
    ) -> bool:
        """Update a node's mutable fields. Returns True if the node existed."""
        node = self.get_node(node_id)
        if not node:
            return False
        now = time.time()
        new_label = label if label is not None else node.label
        new_props = properties if properties is not None else node.properties
        new_quality = quality_score if quality_score is not None else node.quality_score
        new_tongue = tongue if tongue is not None else node.tongue

        updated_node = Node(
            id=node.id, node_type=node.node_type, label=new_label,
            properties=new_props, tongue=new_tongue, quality_score=new_quality,
            created_at=node.created_at, updated_at=now,
        )
        with self._tx() as cur:
            cur.execute(
                """UPDATE hv_nodes
                   SET label=?, properties=?, tongue=?, quality_score=?,
                       content_hash=?, updated_at=?
                   WHERE id=?""",
                (
                    new_label,
                    json.dumps(new_props, sort_keys=True),
                    new_tongue.value if new_tongue else None,
                    new_quality,
                    updated_node.content_hash(),
                    now,
                    node_id,
                ),
            )
        return True

    def delete_node(self, node_id: str) -> bool:
        """Delete a node and all its edges."""
        with self._tx() as cur:
            cur.execute("DELETE FROM hv_edges WHERE source_id=? OR target_id=?",
                        (node_id, node_id))
            cur.execute("DELETE FROM hv_nodes WHERE id=?", (node_id,))
            return cur.rowcount > 0

    def node_count(self, node_type: Optional[NodeType] = None) -> int:
        if node_type:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM hv_nodes WHERE node_type=?",
                (node_type.value,),
            ).fetchone()
        else:
            row = self._conn.execute("SELECT COUNT(*) FROM hv_nodes").fetchone()
        return row[0] if row else 0

    # -- Edges ---------------------------------------------------------------

    def add_edge(
        self,
        edge_type: EdgeType,
        source_id: str,
        target_id: str,
        *,
        weight: float = 1.0,
        properties: Optional[Dict[str, Any]] = None,
        edge_id: Optional[str] = None,
    ) -> Edge:
        """Insert a directed edge. Both endpoints must exist."""
        now = time.time()
        props = properties or {}
        edge = Edge(
            id=edge_id or uuid.uuid4().hex[:16],
            edge_type=edge_type,
            source_id=source_id,
            target_id=target_id,
            weight=weight,
            properties=props,
            created_at=now,
        )
        with self._tx() as cur:
            cur.execute(
                """INSERT INTO hv_edges
                   (id, edge_type, source_id, target_id, weight, properties, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    edge.id,
                    edge.edge_type.value,
                    edge.source_id,
                    edge.target_id,
                    edge.weight,
                    json.dumps(edge.properties, sort_keys=True),
                    edge.created_at,
                ),
            )
        return edge

    def get_edges(
        self,
        *,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        edge_type: Optional[EdgeType] = None,
    ) -> List[Edge]:
        """Query edges with optional filters."""
        clauses: List[str] = []
        params: List[Any] = []
        if source_id:
            clauses.append("source_id = ?")
            params.append(source_id)
        if target_id:
            clauses.append("target_id = ?")
            params.append(target_id)
        if edge_type:
            clauses.append("edge_type = ?")
            params.append(edge_type.value)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"SELECT id, edge_type, source_id, target_id, weight, "
            f"properties, created_at FROM hv_edges {where}",
            params,
        ).fetchall()
        return [
            Edge(
                id=r[0],
                edge_type=EdgeType(r[1]),
                source_id=r[2],
                target_id=r[3],
                weight=r[4],
                properties=json.loads(r[5]),
                created_at=r[6],
            )
            for r in rows
        ]

    def neighbors(
        self,
        node_id: str,
        *,
        edge_type: Optional[EdgeType] = None,
        direction: str = "outgoing",
    ) -> List[Tuple[Edge, Node]]:
        """
        Get neighboring nodes connected by edges.

        Args:
            direction: "outgoing" (source→target), "incoming", or "both"
        """
        results: List[Tuple[Edge, Node]] = []
        if direction in ("outgoing", "both"):
            edges = self.get_edges(source_id=node_id, edge_type=edge_type)
            for e in edges:
                n = self.get_node(e.target_id)
                if n:
                    results.append((e, n))
        if direction in ("incoming", "both"):
            edges = self.get_edges(target_id=node_id, edge_type=edge_type)
            for e in edges:
                n = self.get_node(e.source_id)
                if n:
                    results.append((e, n))
        return results

    def edge_count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM hv_edges").fetchone()
        return row[0] if row else 0

    # -- Graph queries -------------------------------------------------------

    def shortest_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 10,
    ) -> Optional[List[str]]:
        """BFS shortest path between two nodes. Returns list of node IDs or None."""
        if start_id == end_id:
            return [start_id]

        visited = {start_id}
        queue: List[List[str]] = [[start_id]]

        for _ in range(max_depth):
            next_queue: List[List[str]] = []
            for path in queue:
                current = path[-1]
                edges = self.get_edges(source_id=current)
                for edge in edges:
                    if edge.target_id == end_id:
                        return path + [end_id]
                    if edge.target_id not in visited:
                        visited.add(edge.target_id)
                        next_queue.append(path + [edge.target_id])
            queue = next_queue
            if not queue:
                break

        return None

    def subgraph(
        self,
        center_id: str,
        depth: int = 2,
    ) -> Tuple[List[Node], List[Edge]]:
        """Extract a subgraph around a center node up to `depth` hops."""
        visited_nodes: Dict[str, Node] = {}
        collected_edges: List[Edge] = []
        frontier = {center_id}

        for _ in range(depth + 1):
            next_frontier: set = set()
            for nid in frontier:
                if nid in visited_nodes:
                    continue
                node = self.get_node(nid)
                if not node:
                    continue
                visited_nodes[nid] = node
                for edge, neighbor in self.neighbors(nid, direction="both"):
                    collected_edges.append(edge)
                    if neighbor.id not in visited_nodes:
                        next_frontier.add(neighbor.id)
            frontier = next_frontier
            if not frontier:
                break

        # Only keep nodes within `depth` hops — trim the last expansion
        # by removing nodes that were only added in the frontier step
        # Actually the +1 loop already handles this correctly since we
        # expand center (hop 0), then neighbors (hop 1), etc.
        return list(visited_nodes.values()), collected_edges

    # -- Stats ---------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """Return summary stats for the vault."""
        type_counts = {}
        for nt in NodeType:
            type_counts[nt.value] = self.node_count(nt)
        return {
            "total_nodes": self.node_count(),
            "total_edges": self.edge_count(),
            "nodes_by_type": type_counts,
        }
