"""
Nodal Context Storage for Agentic Workers
==========================================

LLM context storage using 6D Cymatic Voxels + Sacred Tongue domains.
Better than flat vector stores - context is geometrically organized.

Key concepts:
- Nodal Bunches: Clusters of related context nodes
- Phase-aligned access: Agents can only read context matching their phase
- 6D positioning: [embed_x, embed_y, embed_z, time, priority, security]
- Harmonic retrieval: Closer context = lower cost

Layer 10: Cymatic Voxel Storage (from 13-layer stack)

Patent: USPTO #63/961,403
Author: Issac Davis
"""

import numpy as np
import hashlib
import time
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set
from enum import Enum
import secrets


# =============================================================================
# Constants
# =============================================================================

PHI = 1.6180339887498948482
R_FIFTH = 1.5  # Perfect fifth harmonic ratio
EMBEDDING_DIM = 3  # Reduced from full embedding for efficiency


# =============================================================================
# Core Types
# =============================================================================

class ContextType(Enum):
    """Types of context nodes."""
    MEMORY = "memory"       # Long-term memory
    THOUGHT = "thought"     # Reasoning step
    FACT = "fact"           # Retrieved fact
    TOOL = "tool"           # Tool output
    QUERY = "query"         # User query
    RESPONSE = "response"   # Agent response
    INSTRUCTION = "instruction"  # System instruction


class SacredTongue(Enum):
    """6 Sacred Tongues for domain separation."""
    KO = ("Korah", 0, "Control")
    AV = ("Aelin", 60, "Transport")
    RU = ("Runis", 120, "Policy")
    CA = ("Caelis", 180, "Compute")
    UM = ("Umbral", 240, "Security")
    DR = ("Dru", 300, "Schema")

    def __init__(self, full_name: str, phase_deg: int, role: str):
        self.full_name = full_name
        self.phase_deg = phase_deg
        self.phase_rad = np.radians(phase_deg)
        self.role = role


@dataclass
class ContextNode:
    """
    A node in the context storage system.

    Stored at a 6D position with phase alignment for access control.
    """
    id: str
    content: str
    context_type: ContextType
    position: np.ndarray  # 6D position
    phase: float          # Phase angle (rad) - must match agent to access
    tongue: SacredTongue  # Domain assignment
    embedding: Optional[np.ndarray] = None  # Raw embedding vector
    metadata: Dict[str, Any] = field(default_factory=dict)
    created: float = field(default_factory=time.time)
    checksum: str = ""

    def __post_init__(self):
        if not self.checksum:
            self.checksum = hashlib.sha256(self.content.encode()).hexdigest()[:16]

    def verify(self) -> bool:
        """Verify content integrity."""
        return hashlib.sha256(self.content.encode()).hexdigest()[:16] == self.checksum

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "type": self.context_type.value,
            "position": self.position.tolist(),
            "phase": self.phase,
            "tongue": self.tongue.name,
            "created": self.created,
            "checksum": self.checksum,
        }


@dataclass
class NodalBunch:
    """
    A cluster of related context nodes.

    Agents access bunches as coherent units - more efficient than
    individual node retrieval.
    """
    id: str
    name: str
    nodes: List[ContextNode] = field(default_factory=list)
    centroid: Optional[np.ndarray] = None  # 6D centroid
    phase: float = 0.0  # Bunch phase (average of nodes)
    tongue: SacredTongue = SacredTongue.KO
    created: float = field(default_factory=time.time)

    def add_node(self, node: ContextNode):
        """Add a node and update centroid."""
        self.nodes.append(node)
        self._update_centroid()

    def _update_centroid(self):
        if not self.nodes:
            self.centroid = None
            return
        positions = np.array([n.position for n in self.nodes])
        self.centroid = np.mean(positions, axis=0)
        self.phase = np.mean([n.phase for n in self.nodes])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "node_count": len(self.nodes),
            "centroid": self.centroid.tolist() if self.centroid is not None else None,
            "phase": self.phase,
            "tongue": self.tongue.name,
        }


# =============================================================================
# 6D KD-Tree for Efficient Retrieval
# =============================================================================

class KDNode6D:
    """Node in 6D KD-Tree."""
    def __init__(self, context_node: ContextNode, split_dim: int = 0):
        self.context_node = context_node
        self.point = context_node.position
        self.split_dim = split_dim
        self.left: Optional['KDNode6D'] = None
        self.right: Optional['KDNode6D'] = None


class KDTree6D:
    """
    6D KD-Tree for O(log n) nearest neighbor queries.

    Uses harmonic distance metric from AETHERMOORE spec.
    """

    def __init__(self, R: float = R_FIFTH):
        self.root: Optional[KDNode6D] = None
        self.R = R
        self.size = 0
        # Harmonic metric weights: [1, 1, 1, R, R², R³]
        self.weights = np.array([1.0, 1.0, 1.0, R, R**2, R**3])

    def harmonic_distance(self, u: np.ndarray, v: np.ndarray) -> float:
        """Compute weighted harmonic distance."""
        diff = u - v
        return np.sqrt(np.sum(self.weights * diff**2))

    def insert(self, node: ContextNode):
        """Insert a context node."""
        kd_node = KDNode6D(node)

        if self.root is None:
            self.root = kd_node
            self.size = 1
            return

        self._insert_recursive(self.root, kd_node, 0)
        self.size += 1

    def _insert_recursive(self, current: KDNode6D, new_node: KDNode6D, depth: int):
        dim = depth % 6

        if new_node.point[dim] < current.point[dim]:
            if current.left is None:
                current.left = new_node
                new_node.split_dim = (depth + 1) % 6
            else:
                self._insert_recursive(current.left, new_node, depth + 1)
        else:
            if current.right is None:
                current.right = new_node
                new_node.split_dim = (depth + 1) % 6
            else:
                self._insert_recursive(current.right, new_node, depth + 1)

    def nearest_k(self, point: np.ndarray, k: int = 5,
                  phase_filter: Optional[float] = None,
                  phase_tolerance: float = np.pi/6) -> List[Tuple[ContextNode, float]]:
        """
        Find k nearest nodes with optional phase filtering.

        Args:
            point: Query point (6D)
            k: Number of neighbors
            phase_filter: Required phase angle (None = no filter)
            phase_tolerance: Allowed phase deviation

        Returns:
            List of (node, distance) tuples sorted by distance
        """
        if self.root is None:
            return []

        # Collect all candidates (can optimize with heap)
        candidates = []
        self._collect_candidates(self.root, point, candidates, phase_filter, phase_tolerance)

        # Sort by distance and return top k
        candidates.sort(key=lambda x: x[1])
        return candidates[:k]

    def _collect_candidates(self, node: Optional[KDNode6D], target: np.ndarray,
                           results: List, phase_filter: Optional[float],
                           phase_tolerance: float):
        if node is None:
            return

        # Check phase filter
        if phase_filter is not None:
            phase_diff = abs(node.context_node.phase - phase_filter)
            phase_diff = min(phase_diff, 2*np.pi - phase_diff)
            if phase_diff > phase_tolerance:
                # Phase mismatch - skip but continue searching children
                self._collect_candidates(node.left, target, results, phase_filter, phase_tolerance)
                self._collect_candidates(node.right, target, results, phase_filter, phase_tolerance)
                return

        # Compute distance
        dist = self.harmonic_distance(target, node.point)
        results.append((node.context_node, dist))

        # Search children
        self._collect_candidates(node.left, target, results, phase_filter, phase_tolerance)
        self._collect_candidates(node.right, target, results, phase_filter, phase_tolerance)

    def range_query(self, center: np.ndarray, radius: float) -> List[ContextNode]:
        """Find all nodes within harmonic distance radius."""
        results = []
        self._range_recursive(self.root, center, radius, results)
        return results

    def _range_recursive(self, node: Optional[KDNode6D], center: np.ndarray,
                        radius: float, results: List):
        if node is None:
            return

        dist = self.harmonic_distance(center, node.point)
        if dist <= radius:
            results.append(node.context_node)

        self._range_recursive(node.left, center, radius, results)
        self._range_recursive(node.right, center, radius, results)


# =============================================================================
# Nodal Context Store
# =============================================================================

class NodalContextStore:
    """
    Main context storage system for agentic workers.

    Features:
    - 6D positioning with harmonic distance
    - Phase-aligned access control
    - Nodal bunches for coherent context clusters
    - Sacred Tongue domain separation
    - Fail-to-noise on unauthorized access
    """

    def __init__(self, store_id: str = "default"):
        self.id = store_id
        self.tree = KDTree6D()
        self.nodes: Dict[str, ContextNode] = {}
        self.bunches: Dict[str, NodalBunch] = {}
        self.tongue_indices: Dict[str, Set[str]] = {t.name: set() for t in SacredTongue}
        self._created = time.time()

    # =========================================================================
    # Position Generation
    # =========================================================================

    def _generate_position(self, content: str, embedding: Optional[np.ndarray],
                          context_type: ContextType, priority: float = 0.5,
                          security: float = 0.5) -> np.ndarray:
        """
        Generate 6D position for a context node.

        Dimensions:
        - [0-2]: Embedding-derived spatial position
        - [3]: Time (normalized)
        - [4]: Priority (0-1)
        - [5]: Security level (0-1)
        """
        if embedding is not None and len(embedding) >= 3:
            # Project embedding to 3D
            spatial = embedding[:3] / (np.linalg.norm(embedding[:3]) + 1e-8)
            spatial = spatial * 0.8  # Keep inside unit ball
        else:
            # Hash content to get deterministic position
            h = hashlib.sha256(content.encode()).digest()
            spatial = np.array([
                (h[0] / 255.0) * 2 - 1,
                (h[1] / 255.0) * 2 - 1,
                (h[2] / 255.0) * 2 - 1,
            ]) * 0.8

        # Time dimension (normalized to [0, 1] over 24 hours)
        time_val = (time.time() % 86400) / 86400

        return np.array([
            spatial[0], spatial[1], spatial[2],
            time_val, priority, security
        ])

    def _assign_tongue(self, content: str, context_type: ContextType) -> SacredTongue:
        """Assign Sacred Tongue based on content/type."""
        content_lower = content.lower()

        # Security content -> UM
        if any(w in content_lower for w in ['security', 'password', 'key', 'secret', 'auth']):
            return SacredTongue.UM

        # Schema/structure -> DR
        if any(w in content_lower for w in ['schema', 'structure', 'format', 'database']):
            return SacredTongue.DR

        # Policy -> RU
        if any(w in content_lower for w in ['policy', 'rule', 'permission', 'constraint']):
            return SacredTongue.RU

        # Compute -> CA
        if any(w in content_lower for w in ['compute', 'calculate', 'process', 'transform']):
            return SacredTongue.CA

        # Transport -> AV
        if any(w in content_lower for w in ['send', 'receive', 'fetch', 'transfer', 'api']):
            return SacredTongue.AV

        # Default -> KO (Control)
        return SacredTongue.KO

    # =========================================================================
    # Node Operations
    # =========================================================================

    def add_context(self, content: str, context_type: ContextType = ContextType.MEMORY,
                   embedding: Optional[np.ndarray] = None,
                   priority: float = 0.5, security: float = 0.5,
                   metadata: Optional[Dict] = None) -> ContextNode:
        """
        Add a context node to the store.

        Args:
            content: Text content
            context_type: Type of context
            embedding: Optional embedding vector
            priority: Priority level (0-1)
            security: Security level (0-1)
            metadata: Additional metadata

        Returns:
            Created ContextNode
        """
        node_id = hashlib.sha256(
            f"{content}{time.time()}{secrets.token_hex(4)}".encode()
        ).hexdigest()[:16]

        position = self._generate_position(content, embedding, context_type, priority, security)
        tongue = self._assign_tongue(content, context_type)
        phase = tongue.phase_rad

        node = ContextNode(
            id=node_id,
            content=content,
            context_type=context_type,
            position=position,
            phase=phase,
            tongue=tongue,
            embedding=embedding,
            metadata=metadata or {},
        )

        self.nodes[node_id] = node
        self.tree.insert(node)
        self.tongue_indices[tongue.name].add(node_id)

        return node

    def get_context(self, node_id: str, agent_phase: Optional[float] = None) -> Optional[str]:
        """
        Retrieve context by ID with phase-based access control.

        Args:
            node_id: Node identifier
            agent_phase: Agent's phase angle (None = bypass check)

        Returns:
            Content if authorized, None otherwise
        """
        node = self.nodes.get(node_id)
        if not node:
            return None

        # Phase check
        if agent_phase is not None:
            phase_diff = abs(node.phase - agent_phase)
            phase_diff = min(phase_diff, 2*np.pi - phase_diff)
            if phase_diff > np.pi/6:  # 30° tolerance
                return None  # Access denied (would return noise in production)

        return node.content

    def query_context(self, query: str, k: int = 5,
                     agent_phase: Optional[float] = None,
                     tongue_filter: Optional[SacredTongue] = None,
                     query_embedding: Optional[np.ndarray] = None) -> List[Tuple[ContextNode, float]]:
        """
        Query for relevant context.

        Args:
            query: Query text
            k: Number of results
            agent_phase: Agent's phase for access control
            tongue_filter: Restrict to specific tongue
            query_embedding: Pre-computed query embedding

        Returns:
            List of (node, distance) tuples
        """
        # Generate query position
        position = self._generate_position(query, query_embedding, ContextType.QUERY)

        # Get candidates
        candidates = self.tree.nearest_k(position, k * 2, agent_phase)

        # Filter by tongue if specified
        if tongue_filter:
            candidates = [(n, d) for n, d in candidates if n.tongue == tongue_filter]

        return candidates[:k]

    # =========================================================================
    # Bunch Operations
    # =========================================================================

    def create_bunch(self, name: str, node_ids: List[str] = None) -> NodalBunch:
        """Create a new nodal bunch."""
        bunch_id = hashlib.sha256(f"{name}{time.time()}".encode()).hexdigest()[:12]

        bunch = NodalBunch(
            id=bunch_id,
            name=name,
            nodes=[],
        )

        if node_ids:
            for nid in node_ids:
                if nid in self.nodes:
                    bunch.add_node(self.nodes[nid])

        self.bunches[bunch_id] = bunch
        return bunch

    def add_to_bunch(self, bunch_id: str, node_id: str) -> bool:
        """Add a node to a bunch."""
        if bunch_id not in self.bunches or node_id not in self.nodes:
            return False

        self.bunches[bunch_id].add_node(self.nodes[node_id])
        return True

    def get_bunch(self, bunch_id: str, agent_phase: Optional[float] = None) -> Optional[List[str]]:
        """
        Get all content from a bunch.

        Args:
            bunch_id: Bunch identifier
            agent_phase: Agent's phase for access control

        Returns:
            List of content strings if authorized
        """
        bunch = self.bunches.get(bunch_id)
        if not bunch:
            return None

        # Phase check against bunch phase
        if agent_phase is not None:
            phase_diff = abs(bunch.phase - agent_phase)
            phase_diff = min(phase_diff, 2*np.pi - phase_diff)
            if phase_diff > np.pi/4:  # 45° tolerance for bunches
                return None

        return [n.content for n in bunch.nodes]

    def auto_bunch(self, radius: float = 0.5) -> List[NodalBunch]:
        """
        Automatically create bunches from clustered nodes.

        Uses spatial clustering based on harmonic distance.
        """
        # Simple greedy clustering
        assigned = set()
        new_bunches = []

        for node_id, node in self.nodes.items():
            if node_id in assigned:
                continue

            # Find nearby nodes
            nearby = self.tree.range_query(node.position, radius)

            if len(nearby) > 1:
                bunch = NodalBunch(
                    id=f"auto_{len(new_bunches)}",
                    name=f"Cluster around {node.content[:20]}...",
                    tongue=node.tongue,
                )

                for n in nearby:
                    if n.id not in assigned:
                        bunch.add_node(n)
                        assigned.add(n.id)

                if len(bunch.nodes) > 1:
                    self.bunches[bunch.id] = bunch
                    new_bunches.append(bunch)

        return new_bunches

    # =========================================================================
    # Agent Integration
    # =========================================================================

    def get_agent_context(self, agent_tongue: SacredTongue, k: int = 10) -> List[str]:
        """
        Get all accessible context for an agent based on their tongue.

        Agents can access their own tongue + adjacent tongues (±60°).
        """
        agent_phase = agent_tongue.phase_rad
        accessible = []

        # Adjacent tongues (±1 step = ±60°)
        adjacent_phases = [
            agent_phase,
            (agent_phase + np.pi/3) % (2*np.pi),
            (agent_phase - np.pi/3) % (2*np.pi),
        ]

        for node in self.nodes.values():
            for adj_phase in adjacent_phases:
                phase_diff = abs(node.phase - adj_phase)
                phase_diff = min(phase_diff, 2*np.pi - phase_diff)
                if phase_diff < np.pi/6:
                    accessible.append((node, self.tree.harmonic_distance(
                        np.zeros(6), node.position
                    )))
                    break

        # Sort by distance (closest first) and return top k
        accessible.sort(key=lambda x: x[1])
        return [n.content for n, _ in accessible[:k]]

    # =========================================================================
    # Stats
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return {
            "id": self.id,
            "total_nodes": len(self.nodes),
            "total_bunches": len(self.bunches),
            "nodes_by_tongue": {t: len(ids) for t, ids in self.tongue_indices.items()},
            "nodes_by_type": {
                ct.value: sum(1 for n in self.nodes.values() if n.context_type == ct)
                for ct in ContextType
            },
            "created": self._created,
        }


# =============================================================================
# GeoSeal Integration
# =============================================================================

class GeoSealContextBridge:
    """
    Bridge between NodalContextStore and GeoSeal.

    Provides unified context management for agentic workers with
    geometric access control.
    """

    def __init__(self, store: NodalContextStore):
        self.store = store
        self._geoseal = None

    def connect_geoseal(self, geoseal):
        """Connect to a GeoSeal instance."""
        self._geoseal = geoseal

    def add_intent_context(self, intent: str, response: str,
                          decision: str, metadata: Dict = None) -> ContextNode:
        """
        Store an intent-response pair as context.

        Useful for building agent memory of past interactions.
        """
        content = f"Intent: {intent}\nResponse: {response}\nDecision: {decision}"

        # Higher security for denied intents
        security = 0.8 if decision == "DENY" else 0.3

        node = self.store.add_context(
            content=content,
            context_type=ContextType.MEMORY,
            priority=0.6,
            security=security,
            metadata={"intent": intent, "decision": decision, **(metadata or {})}
        )

        return node

    def get_relevant_history(self, current_intent: str, k: int = 5,
                            agent_tongue_name: str = "KO") -> List[str]:
        """
        Get relevant past interactions for an agent.

        Args:
            current_intent: Current query/intent
            k: Number of history items
            agent_tongue_name: Agent's assigned tongue

        Returns:
            List of relevant historical context
        """
        tongue = SacredTongue[agent_tongue_name]
        agent_phase = tongue.phase_rad

        results = self.store.query_context(
            current_intent, k=k,
            agent_phase=agent_phase
        )

        return [node.content for node, _ in results]

    def evaluate_with_context(self, intent: str, agent_tongue_name: str = "KO") -> Dict:
        """
        Evaluate an intent using both GeoSeal and historical context.

        Combines geometric access control with contextual memory.
        """
        if self._geoseal is None:
            return {"error": "GeoSeal not connected"}

        # Get GeoSeal evaluation
        geo_result = self._geoseal.evaluate_intent(intent)

        # Get relevant historical context
        history = self.get_relevant_history(intent, k=3, agent_tongue_name=agent_tongue_name)

        # Store this interaction
        self.add_intent_context(
            intent=intent,
            response="[pending]",
            decision=geo_result.get("decision", "UNKNOWN"),
            metadata={"geoseal_result": geo_result}
        )

        return {
            "geoseal": geo_result,
            "context": history,
            "context_count": len(history),
            "agent_tongue": agent_tongue_name,
        }


def create_context_store_for_geoseal(geoseal=None) -> Tuple[NodalContextStore, GeoSealContextBridge]:
    """
    Factory function to create a context store with GeoSeal bridge.

    Usage:
        store, bridge = create_context_store_for_geoseal(my_geoseal)
        result = bridge.evaluate_with_context("What is 2+2?")
    """
    store = NodalContextStore("geoseal_context")
    bridge = GeoSealContextBridge(store)

    if geoseal:
        bridge.connect_geoseal(geoseal)

    return store, bridge


# =============================================================================
# Demo
# =============================================================================

def demo():
    """Demonstrate Nodal Context Storage."""
    print("=" * 70)
    print("Nodal Context Storage for Agentic Workers")
    print("=" * 70)

    store = NodalContextStore("demo")

    # Add some context
    print("\n--- Adding Context Nodes ---")

    contexts = [
        ("The capital of France is Paris.", ContextType.FACT),
        ("User prefers dark mode.", ContextType.MEMORY),
        ("Calculate the sum of 1 to 100.", ContextType.THOUGHT),
        ("API returned status 200.", ContextType.TOOL),
        ("Never reveal passwords or secrets.", ContextType.INSTRUCTION),
        ("Encrypt all data at rest.", ContextType.INSTRUCTION),
        ("The meeting is at 3pm.", ContextType.FACT),
        ("Temperature in NYC is 72°F.", ContextType.FACT),
    ]

    for content, ctype in contexts:
        node = store.add_context(content, ctype)
        print(f"  Added: [{node.tongue.name}] {content[:40]}...")

    # Query context
    print("\n--- Querying Context ---")

    query = "What is the capital of France?"
    results = store.query_context(query, k=3)

    print(f"  Query: '{query}'")
    print(f"  Results:")
    for node, dist in results:
        print(f"    [{dist:.3f}] {node.content}")

    # Create a bunch
    print("\n--- Creating Nodal Bunch ---")

    fact_ids = [n.id for n in store.nodes.values() if n.context_type == ContextType.FACT]
    bunch = store.create_bunch("Facts Bundle", fact_ids)
    print(f"  Created bunch '{bunch.name}' with {len(bunch.nodes)} nodes")

    # Agent context by tongue
    print("\n--- Agent Context by Tongue ---")

    for tongue in [SacredTongue.KO, SacredTongue.UM]:
        context = store.get_agent_context(tongue, k=3)
        print(f"  {tongue.name} ({tongue.role}) can access:")
        for c in context:
            print(f"    - {c[:50]}...")

    # Stats
    print("\n--- Statistics ---")
    stats = store.get_stats()
    print(f"  Total nodes: {stats['total_nodes']}")
    print(f"  By tongue: {stats['nodes_by_tongue']}")
    print(f"  By type: {stats['nodes_by_type']}")

    print("\n" + "=" * 70)
    print("Nodal Context Storage Demo Complete")


if __name__ == "__main__":
    demo()
