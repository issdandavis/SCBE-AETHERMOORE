"""Triangulated PHDM Lattice — 21D polyhedral graph with governance vertices.

Architecture:
  - 21 nodes from PHDM (6 tongue + 6 phase + 9 telemetry)
  - Edges = Sacred Tongue tokenizer channels
  - Squares triangulated into rigid triangles
  - Each triangle: 2 tokenizer corners + 1 governance corner
  - Governance corners carry compression weights, NOT semantics
  - Barycentric interpolation inside each triangle

Key property: governance is structurally independent from semantics.
  - Can't be prompt-injected (not in semantic channel)
  - Can't be fine-tuned away (not a weight, it's a vertex)
  - Adjustable without touching tokenizer channels

Patent relevant: extends USPTO #63/961,403
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


PHI = (1 + math.sqrt(5)) / 2

# 21 PHDM dimensions
TONGUE_DIMS = ["KO", "AV", "RU", "CA", "UM", "DR"]
PHASE_DIMS = ["KO_phase", "AV_phase", "RU_phase", "CA_phase", "UM_phase", "DR_phase"]
TELEMETRY_DIMS = ["pressure", "tension", "curvature", "entropy", "temperature",
                  "coherence", "drift", "fidelity", "stability"]
ALL_DIMS = TONGUE_DIMS + PHASE_DIMS + TELEMETRY_DIMS  # 21 total

TONGUE_WEIGHTS = [PHI ** i for i in range(6)]


@dataclass
class LatticeNode:
    """A node in the 21D polyhedral graph."""
    id: int
    name: str
    dim_type: str  # "tongue", "phase", "telemetry"
    value: float = 0.0
    is_governance: bool = False  # True for stitch-point governance vertices


@dataclass
class TokenizerEdge:
    """An edge connecting two nodes via a Sacred Tongue tokenizer channel."""
    source: int
    target: int
    tongue: str  # Which tongue encodes this channel
    weight: float = 1.0


@dataclass
class Triangle:
    """A triangulated face with 2 tokenizer corners + 1 governance corner."""
    corner_a: int  # tokenizer node
    corner_b: int  # tokenizer node
    corner_c: int  # governance node (compression weight)
    governance_weight: float = 1.0  # compression parameter

    def interpolate(self, w1: float, w2: float, w3: float,
                    val_a: float, val_b: float) -> float:
        """Barycentric interpolation with governance compression.

        w1, w2 blend the two tokenizer values.
        w3 * governance_weight compresses/expands the result.
        """
        assert abs(w1 + w2 + w3 - 1.0) < 1e-6, "Barycentric coords must sum to 1"
        semantic_blend = w1 * val_a + w2 * val_b
        governance_factor = 1.0 + (w3 * (self.governance_weight - 1.0))
        return semantic_blend * governance_factor


class TriangulatedPHDMLattice:
    """21D polyhedral lattice with triangulated governance mesh.

    Construction:
    1. Build 21-node graph from PHDM dimensions
    2. Connect nodes via polyhedral adjacency (tongue->phase, phase->telemetry, etc.)
    3. Each edge is a tokenizer channel
    4. Triangulate quadrilateral faces by adding diagonal stitches
    5. Add governance vertices at stitch points
    6. Governance vertices carry independent compression weights
    """

    def __init__(self, governance_default: float = 1.0):
        self.nodes: List[LatticeNode] = []
        self.edges: List[TokenizerEdge] = []
        self.triangles: List[Triangle] = []
        self.governance_vertices: List[LatticeNode] = []
        self._governance_default = governance_default
        self._next_id = 0

        self._build_nodes()
        self._build_edges()
        self._triangulate()

    def _build_nodes(self):
        """Create 21 PHDM nodes."""
        for name in TONGUE_DIMS:
            self.nodes.append(LatticeNode(id=self._next_id, name=name, dim_type="tongue"))
            self._next_id += 1
        for name in PHASE_DIMS:
            self.nodes.append(LatticeNode(id=self._next_id, name=name, dim_type="phase"))
            self._next_id += 1
        for name in TELEMETRY_DIMS:
            self.nodes.append(LatticeNode(id=self._next_id, name=name, dim_type="telemetry"))
            self._next_id += 1

    def _build_edges(self):
        """Connect nodes via polyhedral adjacency with tongue-specific channels."""
        # Tongue <-> Phase connections (each tongue connects to its phase)
        for i in range(6):
            self.edges.append(TokenizerEdge(
                source=i, target=6 + i,
                tongue=TONGUE_DIMS[i],
                weight=TONGUE_WEIGHTS[i],
            ))

        # Phase <-> Telemetry connections (distribute across telemetry)
        for i in range(6):
            for j in range(9):
                if (i + j) % 3 == 0:  # Selective connectivity (polyhedral face rule)
                    self.edges.append(TokenizerEdge(
                        source=6 + i, target=12 + j,
                        tongue=TONGUE_DIMS[i],
                        weight=TONGUE_WEIGHTS[i] * 0.5,
                    ))

        # Cross-tongue connections (60-degree phase neighbors)
        for i in range(6):
            next_i = (i + 1) % 6
            self.edges.append(TokenizerEdge(
                source=i, target=next_i,
                tongue=TONGUE_DIMS[i],
                weight=(TONGUE_WEIGHTS[i] + TONGUE_WEIGHTS[next_i]) / 2,
            ))

    def _triangulate(self):
        """Triangulate faces and add governance vertices at stitch points."""
        # For each pair of adjacent edges sharing a common node,
        # create a triangle with a governance vertex
        processed = set()
        for e1 in self.edges:
            for e2 in self.edges:
                if e1 is e2:
                    continue
                # Find shared vertex
                shared = None
                other1 = None
                other2 = None
                if e1.target == e2.source:
                    shared = e1.target
                    other1 = e1.source
                    other2 = e2.target
                elif e1.source == e2.target:
                    shared = e1.source
                    other1 = e1.target
                    other2 = e2.source

                if shared is not None and other1 != other2:
                    key = tuple(sorted([other1, shared, other2]))
                    if key in processed:
                        continue
                    processed.add(key)

                    # Create governance vertex at the stitch point
                    gov_node = LatticeNode(
                        id=self._next_id,
                        name=f"gov_{other1}_{shared}_{other2}",
                        dim_type="governance",
                        value=self._governance_default,
                        is_governance=True,
                    )
                    self._next_id += 1
                    self.governance_vertices.append(gov_node)

                    # Create triangle: two tokenizer corners + governance corner
                    tri = Triangle(
                        corner_a=other1,
                        corner_b=other2,
                        corner_c=gov_node.id,
                        governance_weight=self._governance_default,
                    )
                    self.triangles.append(tri)

                    if len(self.triangles) >= 200:  # Cap for performance
                        return

    def set_node_values(self, values: np.ndarray):
        """Set the 21 PHDM node values from a state vector."""
        assert len(values) >= 21, "Need at least 21 values"
        for i in range(21):
            self.nodes[i].value = float(values[i])

    def set_governance(self, triangle_id: int, weight: float):
        """Adjust a governance vertex weight without touching tokenizers."""
        if 0 <= triangle_id < len(self.triangles):
            self.triangles[triangle_id].governance_weight = weight

    def set_all_governance(self, weight: float):
        """Set all governance weights uniformly."""
        for tri in self.triangles:
            tri.governance_weight = weight

    def evaluate(self, state: np.ndarray) -> dict:
        """Evaluate the full lattice for a given 21D state.

        Returns governance-compressed semantic values for each triangle.
        """
        self.set_node_values(state)

        results = []
        for tri in self.triangles:
            # Get tokenizer values from the two semantic corners
            val_a = self._get_node_value(tri.corner_a)
            val_b = self._get_node_value(tri.corner_b)

            # Equal blend by default (can be parameterized)
            blended = tri.interpolate(0.4, 0.4, 0.2, val_a, val_b)
            results.append({
                "triangle_id": len(results),
                "corner_a": tri.corner_a,
                "corner_b": tri.corner_b,
                "val_a": val_a,
                "val_b": val_b,
                "governance_weight": tri.governance_weight,
                "blended": blended,
            })

        # Aggregate
        if results:
            total_blend = sum(r["blended"] for r in results) / len(results)
            max_governance = max(r["governance_weight"] for r in results)
            min_governance = min(r["governance_weight"] for r in results)
        else:
            total_blend = 0
            max_governance = min_governance = self._governance_default

        return {
            "total_triangles": len(self.triangles),
            "total_governance_vertices": len(self.governance_vertices),
            "total_edges": len(self.edges),
            "average_blend": total_blend,
            "governance_range": (min_governance, max_governance),
            "triangle_results": results[:10],  # First 10 for inspection
        }

    def _get_node_value(self, node_id: int) -> float:
        """Get value for a node (PHDM or governance)."""
        for n in self.nodes:
            if n.id == node_id:
                return n.value
        for n in self.governance_vertices:
            if n.id == node_id:
                return n.value
        return 0.0

    def summary(self) -> str:
        """Human-readable summary."""
        return (
            f"TriangulatedPHDMLattice:\n"
            f"  PHDM nodes: {len(self.nodes)}\n"
            f"  Tokenizer edges: {len(self.edges)}\n"
            f"  Triangulated faces: {len(self.triangles)}\n"
            f"  Governance vertices: {len(self.governance_vertices)}\n"
            f"  Tongue dims: {TONGUE_DIMS}\n"
            f"  Phase dims: {PHASE_DIMS}\n"
            f"  Telemetry dims: {TELEMETRY_DIMS[:3]}...\n"
        )
