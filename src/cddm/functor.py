"""
Functor — categorical composition, domain graphs, and graph isomorphism.

Provides:
  - CompositionChain: chain multiple morphisms A->B->C->...
  - DomainGraph: a directed graph of domains connected by morphisms
  - GraphIsomorphism: check if two domain graphs have the same structure
  - compose(): shorthand for chaining two morphisms
  - identity_morphism(): id: A -> A

Pure stdlib. No networkx dependency — we implement adjacency-list graphs
and VF2-lite isomorphism directly.

@module cddm/functor
@version 1.0.0
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from .domain import Domain
from .morphism import Morphism, MorphismError


# ═══════════════════════════════════════════════════════════════
# Composition Utilities
# ═══════════════════════════════════════════════════════════════


def identity_morphism(domain: Domain) -> Morphism:
    """Create an identity morphism id: D -> D."""
    return Morphism(
        src=domain,
        dst=domain,
        func=lambda x: x,
        name=f"id({domain.name})",
        inverse_func=lambda x: x,
    )


def compose(f: Morphism, g: Morphism) -> Morphism:
    """Compose f then g: (g ∘ f)(x) = g(f(x))."""
    return f.compose_with(g)


class CompositionChain:
    """Chain of morphisms A -> B -> C -> ... with automatic composition.

    Useful for building multi-step cross-domain pipelines:
        chain = CompositionChain()
        chain.add(energy_to_motivation)
        chain.add(motivation_to_incentive)
        result = chain.apply(500_000)  # Energy -> Motivation -> Incentive
    """

    def __init__(self):
        self.steps: List[Morphism] = []

    def add(self, morphism: Morphism) -> "CompositionChain":
        """Append a morphism to the chain."""
        if self.steps:
            last = self.steps[-1]
            if last.dst.name != morphism.src.name:
                raise MorphismError(f"Chain break: last dst={last.dst.name} " f"!= new src={morphism.src.name}")
        self.steps.append(morphism)
        return self

    def apply(self, x: float) -> float:
        """Apply the full chain to a value."""
        v = x
        for step in self.steps:
            v = step(v)
        return v

    def apply_traced(self, x: float) -> List[Tuple[str, float]]:
        """Apply chain with trace: returns [(domain_name, value), ...]."""
        trace = [(self.steps[0].src.name, x)]
        v = x
        for step in self.steps:
            v = step(v)
            trace.append((step.dst.name, v))
        return trace

    def compose_all(self) -> Morphism:
        """Flatten chain into a single composite morphism."""
        if not self.steps:
            raise MorphismError("Cannot compose empty chain")
        result = self.steps[0]
        for step in self.steps[1:]:
            result = result.compose_with(step)
        return result

    @property
    def src(self) -> Optional[Domain]:
        return self.steps[0].src if self.steps else None

    @property
    def dst(self) -> Optional[Domain]:
        return self.steps[-1].dst if self.steps else None

    @property
    def invertible(self) -> bool:
        return all(s.invertible for s in self.steps)

    def invert(self) -> "CompositionChain":
        """Return the reverse chain (if all steps are invertible)."""
        if not self.invertible:
            raise MorphismError("Chain contains non-invertible morphisms")
        inv = CompositionChain()
        for step in reversed(self.steps):
            inv.add(step.invert())
        return inv

    def __len__(self) -> int:
        return len(self.steps)

    def __repr__(self) -> str:
        if not self.steps:
            return "CompositionChain(empty)"
        path = " -> ".join([self.steps[0].src.name] + [s.dst.name for s in self.steps])
        return f"CompositionChain({path})"


# ═══════════════════════════════════════════════════════════════
# Domain Graph — Directed Graph of Domains + Morphisms
# ═══════════════════════════════════════════════════════════════


class DomainGraph:
    """Directed graph where nodes are Domains and edges are Morphisms.

    Used for:
      - Finding paths between domains (BFS)
      - Checking structural equivalence (graph isomorphism)
      - Enumerating all possible cross-domain mappings
    """

    def __init__(self):
        self.nodes: Dict[str, Domain] = {}
        self.edges: Dict[str, List[Tuple[str, Morphism]]] = {}  # src_name -> [(dst_name, morphism)]

    def add_domain(self, domain: Domain) -> None:
        self.nodes[domain.name] = domain
        if domain.name not in self.edges:
            self.edges[domain.name] = []

    def add_morphism(self, morphism: Morphism) -> None:
        """Add a morphism (and its domains if not already present)."""
        self.add_domain(morphism.src)
        self.add_domain(morphism.dst)
        self.edges[morphism.src.name].append((morphism.dst.name, morphism))

    def neighbors(self, domain_name: str) -> List[Tuple[str, Morphism]]:
        """Get outgoing edges from a domain."""
        return self.edges.get(domain_name, [])

    def find_path(self, src_name: str, dst_name: str) -> Optional[List[Morphism]]:
        """BFS to find a morphism path from src to dst."""
        if src_name not in self.nodes or dst_name not in self.nodes:
            return None
        if src_name == dst_name:
            return []

        visited: Set[str] = {src_name}
        queue: List[Tuple[str, List[Morphism]]] = [(src_name, [])]

        while queue:
            current, path = queue.pop(0)
            for neighbor, morph in self.neighbors(current):
                if neighbor == dst_name:
                    return path + [morph]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [morph]))
        return None

    def build_chain(self, src_name: str, dst_name: str) -> Optional[CompositionChain]:
        """Build a CompositionChain for the shortest path between domains."""
        path = self.find_path(src_name, dst_name)
        if path is None:
            return None
        chain = CompositionChain()
        for morph in path:
            chain.add(morph)
        return chain

    def adjacency_matrix(self) -> Tuple[List[str], List[List[int]]]:
        """Return (node_names, adjacency_matrix) for isomorphism checks."""
        names = sorted(self.nodes.keys())
        idx = {n: i for i, n in enumerate(names)}
        n = len(names)
        mat = [[0] * n for _ in range(n)]
        for src_name, edges in self.edges.items():
            for dst_name, _ in edges:
                mat[idx[src_name]][idx[dst_name]] = 1
        return names, mat

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(e) for e in self.edges.values())

    def __repr__(self) -> str:
        return f"DomainGraph(nodes={self.node_count}, edges={self.edge_count})"


# ═══════════════════════════════════════════════════════════════
# Graph Isomorphism — VF2-lite for small domain graphs
# ═══════════════════════════════════════════════════════════════


class GraphIsomorphism:
    """Check structural equivalence of two DomainGraphs.

    Uses degree-sequence filtering + backtracking (VF2-lite) for small graphs.
    Designed for domain graphs with <100 nodes (typical: 6-20).
    """

    @staticmethod
    def degree_sequence(adj: List[List[int]]) -> List[Tuple[int, int]]:
        """Compute sorted (in_degree, out_degree) sequence."""
        n = len(adj)
        out_deg = [sum(row) for row in adj]
        in_deg = [sum(adj[r][c] for r in range(n)) for c in range(n)]
        return sorted(zip(in_deg, out_deg))

    @staticmethod
    def is_isomorphic(g1: DomainGraph, g2: DomainGraph) -> bool:
        """Check if two domain graphs are structurally isomorphic."""
        if g1.node_count != g2.node_count or g1.edge_count != g2.edge_count:
            return False

        _, adj1 = g1.adjacency_matrix()
        _, adj2 = g2.adjacency_matrix()

        # Quick filter: degree sequences must match
        ds1 = GraphIsomorphism.degree_sequence(adj1)
        ds2 = GraphIsomorphism.degree_sequence(adj2)
        if ds1 != ds2:
            return False

        # Backtracking search for valid mapping
        n = len(adj1)
        if n == 0:
            return True
        return GraphIsomorphism._backtrack(adj1, adj2, {}, set(), n)

    @staticmethod
    def find_mapping(g1: DomainGraph, g2: DomainGraph) -> Optional[Dict[str, str]]:
        """Find a node mapping if graphs are isomorphic, else None."""
        if g1.node_count != g2.node_count or g1.edge_count != g2.edge_count:
            return None

        names1, adj1 = g1.adjacency_matrix()
        names2, adj2 = g2.adjacency_matrix()

        ds1 = GraphIsomorphism.degree_sequence(adj1)
        ds2 = GraphIsomorphism.degree_sequence(adj2)
        if ds1 != ds2:
            return None

        n = len(adj1)
        if n == 0:
            return {}

        mapping = GraphIsomorphism._find_mapping(adj1, adj2, {}, set(), n)
        if mapping is None:
            return None

        return {names1[k]: names2[v] for k, v in mapping.items()}

    @staticmethod
    def _backtrack(
        adj1: List[List[int]],
        adj2: List[List[int]],
        mapping: Dict[int, int],
        used: Set[int],
        n: int,
    ) -> bool:
        """Recursive backtracking isomorphism check."""
        if len(mapping) == n:
            return True

        u = len(mapping)  # Next node in g1 to map
        for v in range(n):
            if v in used:
                continue
            if GraphIsomorphism._consistent(adj1, adj2, mapping, u, v):
                mapping[u] = v
                used.add(v)
                if GraphIsomorphism._backtrack(adj1, adj2, mapping, used, n):
                    return True
                del mapping[u]
                used.discard(v)
        return False

    @staticmethod
    def _find_mapping(
        adj1: List[List[int]],
        adj2: List[List[int]],
        mapping: Dict[int, int],
        used: Set[int],
        n: int,
    ) -> Optional[Dict[int, int]]:
        """Recursive backtracking returning the mapping."""
        if len(mapping) == n:
            return dict(mapping)

        u = len(mapping)
        for v in range(n):
            if v in used:
                continue
            if GraphIsomorphism._consistent(adj1, adj2, mapping, u, v):
                mapping[u] = v
                used.add(v)
                result = GraphIsomorphism._find_mapping(adj1, adj2, mapping, used, n)
                if result is not None:
                    return result
                del mapping[u]
                used.discard(v)
        return None

    @staticmethod
    def _consistent(
        adj1: List[List[int]],
        adj2: List[List[int]],
        mapping: Dict[int, int],
        u: int,
        v: int,
    ) -> bool:
        """Check if mapping u->v is consistent with existing partial mapping."""
        for u2, v2 in mapping.items():
            # Forward edge consistency
            if adj1[u][u2] != adj2[v][v2]:
                return False
            # Backward edge consistency
            if adj1[u2][u] != adj2[v2][v]:
                return False
        return True
