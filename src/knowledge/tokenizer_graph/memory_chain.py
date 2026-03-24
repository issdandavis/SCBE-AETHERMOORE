"""
6D DNA Blockchain Memory — Sacred Tongue Tokenizer Graph

Each knowledge chunk gets a 6D coordinate from the Sacred Tongues:
    KO (0) = Control/orchestration     weight: phi^0 = 1.00
    AV (1) = Transport/initialization  weight: phi^1 = 1.62
    RU (2) = Policy/authorization      weight: phi^2 = 2.62
    CA (3) = Encryption/compute        weight: phi^3 = 4.24
    UM (4) = Redaction/privacy         weight: phi^4 = 6.85
    DR (5) = Authentication/integrity  weight: phi^5 = 11.09

Chunks link via semantic hypercords (edges weighted by tongue-distance).
The graph IS the memory. Traversal = recall. Proximity = relevance.

Memory Scenes: clusters of related chunks form "scenes" — like DNA codons
that encode a concept. Multiple scenes chain together via governance hashes.
"""

import math
import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

PHI = (1 + math.sqrt(5)) / 2
TONGUE_WEIGHTS = [PHI**i for i in range(6)]  # [1.0, 1.618, 2.618, 4.236, 6.854, 11.09]
TONGUE_NAMES = ["KO", "AV", "RU", "CA", "UM", "DR"]

# Category -> dominant tongue mapping
CATEGORY_TONGUE_MAP = {
    # KO-dominant (control/orchestration)
    "governance": [0.8, 0.1, 0.3, 0.1, 0.1, 0.2],
    "architecture": [0.7, 0.2, 0.2, 0.3, 0.1, 0.1],
    "hydra": [0.6, 0.3, 0.2, 0.2, 0.1, 0.2],
    "swarm": [0.6, 0.3, 0.1, 0.2, 0.1, 0.3],
    # AV-dominant (transport/initialization)
    "deployment": [0.2, 0.7, 0.1, 0.3, 0.1, 0.2],
    "demo": [0.3, 0.6, 0.1, 0.2, 0.1, 0.1],
    # RU-dominant (policy/authorization)
    "patent": [0.2, 0.1, 0.8, 0.1, 0.2, 0.2],
    "axioms": [0.3, 0.1, 0.7, 0.2, 0.1, 0.2],
    "theorems": [0.2, 0.1, 0.7, 0.3, 0.1, 0.1],
    # CA-dominant (encryption/compute)
    "security": [0.2, 0.1, 0.2, 0.8, 0.2, 0.3],
    "math": [0.1, 0.1, 0.3, 0.7, 0.1, 0.1],
    "quantum": [0.1, 0.1, 0.2, 0.8, 0.1, 0.2],
    "geometry": [0.2, 0.1, 0.2, 0.7, 0.1, 0.1],
    # UM-dominant (redaction/privacy)
    "sacred-eggs": [0.2, 0.2, 0.2, 0.2, 0.7, 0.3],
    "geoseal": [0.2, 0.1, 0.3, 0.3, 0.6, 0.3],
    # DR-dominant (authentication/integrity)
    "tongues": [0.2, 0.2, 0.2, 0.2, 0.2, 0.8],
    "geoseed": [0.2, 0.2, 0.1, 0.3, 0.2, 0.7],
    "lore": [0.1, 0.3, 0.1, 0.1, 0.2, 0.7],
    # Mixed
    "ai": [0.3, 0.2, 0.2, 0.4, 0.1, 0.2],
    "nlp": [0.2, 0.3, 0.1, 0.4, 0.1, 0.3],
    "research": [0.2, 0.2, 0.2, 0.4, 0.1, 0.3],
    "machine-learning": [0.2, 0.2, 0.1, 0.5, 0.1, 0.2],
    "browser": [0.4, 0.3, 0.2, 0.2, 0.2, 0.1],
    "marketing": [0.3, 0.4, 0.1, 0.1, 0.1, 0.2],
    "phdm": [0.3, 0.1, 0.2, 0.5, 0.2, 0.3],
    "scbe-general": [0.3, 0.2, 0.2, 0.3, 0.2, 0.2],
}


@dataclass
class MemoryNode:
    """A node in the 6D memory graph."""

    chunk_id: str
    coords: list  # 6D Sacred Tongue coordinates
    chain_hash: str
    parent_hash: str
    title: str
    source: str
    category: str
    edges: list = field(default_factory=list)  # [(target_id, weight, tongue)]
    scene_id: Optional[str] = None


@dataclass
class HyperCord:
    """An edge in the memory graph — a semantic link between chunks."""

    source_id: str
    target_id: str
    weight: float
    dominant_tongue: str  # Which tongue dimension is strongest
    governance_hash: str = ""


@dataclass
class MemoryScene:
    """A cluster of related memory nodes — like a DNA codon."""

    scene_id: str
    node_ids: list
    centroid: list  # 6D centroid
    dominant_tongue: str
    governance_hash: str


class TokenizerGraph:
    """
    6D DNA Blockchain Memory Graph.

    Nodes = KnowledgeChunks with 6D coordinates.
    Edges = HyperCords weighted by tongue-distance.
    Scenes = Clusters of related nodes (DNA codons).
    """

    def __init__(self):
        self.nodes: dict[str, MemoryNode] = {}
        self.cords: list[HyperCord] = []
        self.scenes: dict[str, MemoryScene] = {}

    def compute_tongue_coords(self, category: str, content: str = "") -> list[float]:
        """Compute 6D Sacred Tongue coordinates for a chunk."""
        base = CATEGORY_TONGUE_MAP.get(category, [0.2] * 6)
        coords = [b * w for b, w in zip(base, TONGUE_WEIGHTS)]

        # Content-based adjustment: keyword boosting
        content_lower = content.lower()[:2000]
        keyword_boosts = {
            0: ["control", "orchestrat", "workflow", "command", "coordinate"],
            1: ["transport", "deploy", "initialize", "network", "send"],
            2: ["policy", "authorize", "rule", "govern", "law", "patent"],
            3: ["encrypt", "compute", "math", "algorithm", "cipher", "hash"],
            4: ["secret", "redact", "privacy", "hide", "egg", "ritual"],
            5: ["authentic", "verify", "integrity", "tongue", "token", "sign"],
        }
        for dim, keywords in keyword_boosts.items():
            for kw in keywords:
                if kw in content_lower:
                    coords[dim] += TONGUE_WEIGHTS[dim] * 0.1

        # Normalize to unit ball (Poincare constraint)
        norm = math.sqrt(sum(c**2 for c in coords))
        if norm > 0:
            coords = [c / norm * 0.95 for c in coords]  # Stay inside ball

        return coords

    def add_chunk(
        self, chunk_id: str, title: str, category: str, content: str, source: str, chain_hash: str, parent_hash: str
    ) -> MemoryNode:
        """Add a knowledge chunk to the graph."""
        coords = self.compute_tongue_coords(category, content)

        node = MemoryNode(
            chunk_id=chunk_id,
            coords=coords,
            chain_hash=chain_hash,
            parent_hash=parent_hash,
            title=title,
            source=source,
            category=category,
        )
        self.nodes[chunk_id] = node

        # Auto-link to nearby nodes
        self._auto_link(node)

        return node

    def _auto_link(self, node: MemoryNode, max_links: int = 5, threshold: float = 0.3):
        """Automatically create HyperCords to nearby nodes."""
        distances = []
        for other_id, other in self.nodes.items():
            if other_id == node.chunk_id:
                continue
            dist = self._tongue_distance(node.coords, other.coords)
            if dist < threshold:
                distances.append((other_id, dist))

        distances.sort(key=lambda x: x[1])
        for target_id, dist in distances[:max_links]:
            weight = 1.0 - dist  # Closer = stronger
            dominant = self._dominant_tongue(node.coords, self.nodes[target_id].coords)

            cord = HyperCord(
                source_id=node.chunk_id,
                target_id=target_id,
                weight=weight,
                dominant_tongue=dominant,
                governance_hash=hashlib.sha256(
                    f"{node.chain_hash}:{self.nodes[target_id].chain_hash}".encode()
                ).hexdigest()[:16],
            )
            self.cords.append(cord)
            node.edges.append((target_id, weight, dominant))

    def _tongue_distance(self, a: list, b: list) -> float:
        """Weighted distance in 6D tongue space."""
        return math.sqrt(sum((ai - bi) ** 2 * TONGUE_WEIGHTS[i] for i, (ai, bi) in enumerate(zip(a, b)))) / sum(
            TONGUE_WEIGHTS
        )

    def _dominant_tongue(self, a: list, b: list) -> str:
        """Find which tongue dimension has the strongest connection."""
        diffs = [abs(ai - bi) * TONGUE_WEIGHTS[i] for i, (ai, bi) in enumerate(zip(a, b))]
        min_idx = diffs.index(min(diffs))
        return TONGUE_NAMES[min_idx]

    def recall(self, query_coords: list, top_k: int = 10) -> list[tuple[str, float]]:
        """Recall memory nodes by proximity to query coordinates."""
        distances = []
        for node_id, node in self.nodes.items():
            dist = self._tongue_distance(query_coords, node.coords)
            distances.append((node_id, dist))
        distances.sort(key=lambda x: x[1])
        return distances[:top_k]

    def traverse(self, start_id: str, depth: int = 3) -> list[str]:
        """Traverse the graph from a starting node, following HyperCords."""
        visited = set()
        queue = [(start_id, 0)]
        path = []

        while queue:
            node_id, d = queue.pop(0)
            if node_id in visited or d > depth:
                continue
            visited.add(node_id)
            path.append(node_id)

            node = self.nodes.get(node_id)
            if node:
                for target_id, weight, _ in node.edges:
                    if target_id not in visited:
                        queue.append((target_id, d + 1))

        return path

    def export_graph(self, output_path: str) -> str:
        """Export the graph as JSON for visualization or HF upload."""
        data = {
            "nodes": {
                nid: {
                    "coords": n.coords,
                    "title": n.title,
                    "source": n.source,
                    "category": n.category,
                    "chain_hash": n.chain_hash,
                    "edges": n.edges,
                    "scene_id": n.scene_id,
                }
                for nid, n in self.nodes.items()
            },
            "cords": [
                {
                    "source": c.source_id,
                    "target": c.target_id,
                    "weight": c.weight,
                    "tongue": c.dominant_tongue,
                }
                for c in self.cords
            ],
            "stats": {
                "total_nodes": len(self.nodes),
                "total_cords": len(self.cords),
                "total_scenes": len(self.scenes),
            },
        }
        Path(output_path).write_text(json.dumps(data, indent=2))
        return output_path
