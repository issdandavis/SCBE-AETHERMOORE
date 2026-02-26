"""Generate knowledge graphs from cross-referenced research.

Produces:
1. Mermaid diagram syntax (embeddable in Obsidian notes)
2. Obsidian Canvas JSON format
3. Adjacency list for programmatic use

Pure stdlib. No external dependencies.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .source_adapter import IngestionResult
from .cross_reference_engine import WikiLink, LinkType


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class GraphNode:
    """A node in the knowledge graph."""

    id: str
    label: str
    node_type: str  # "result", "vault_page", "concept", "domain"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """An edge in the knowledge graph."""

    source_id: str
    target_id: str
    edge_type: LinkType
    confidence: float
    label: str = ""


# ---------------------------------------------------------------------------
# Mermaid rendering helpers
# ---------------------------------------------------------------------------

# Node shape delimiters by type
_MERMAID_NODE_SHAPES: Dict[str, Tuple[str, str]] = {
    "result": ("([", "])"),       # stadium / rounded rect
    "vault_page": ("[", "]"),     # rect
    "concept": ("((", "))"),      # circle
    "domain": ("{{", "}}"),       # hexagon
}

# Edge arrow styles by LinkType
_MERMAID_EDGE_STYLES: Dict[str, str] = {
    LinkType.KEYWORD: "-->",
    LinkType.CITATION: "==>",
    LinkType.CDDM_MORPHISM: "-.->",
    LinkType.SEMANTIC: "---",
    LinkType.MANUAL: "-->",
}

# Obsidian canvas colour palette by node type
_CANVAS_COLORS: Dict[str, str] = {
    "result": "4",       # green
    "vault_page": "1",   # red
    "concept": "6",      # purple
    "domain": "5",       # cyan
}


# ---------------------------------------------------------------------------
# Knowledge graph
# ---------------------------------------------------------------------------


class KnowledgeGraph:
    """In-memory knowledge graph built from research results and WikiLinks.

    Build the graph by calling :meth:`add_result`, :meth:`add_link`, and
    optionally :meth:`add_concept`.  Then render with :meth:`render_mermaid`,
    :meth:`render_obsidian_canvas`, or :meth:`render_adjacency_markdown`.
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []

    # ------------------------------------------------------------------ #
    # Building the graph                                                   #
    # ------------------------------------------------------------------ #

    def add_result(self, result: IngestionResult) -> str:
        """Add an IngestionResult as a ``result`` node.

        Returns the generated node ID.
        """
        node_id = self._make_id("result", result.title)
        if node_id not in self.nodes:
            source_str = (
                result.source_type.value
                if hasattr(result.source_type, "value")
                else str(result.source_type)
            )
            self.nodes[node_id] = GraphNode(
                id=node_id,
                label=result.title,
                node_type="result",
                metadata={
                    "source_type": source_str,
                    "tags": list(result.tags),
                    "url": result.url or "",
                },
            )

            # Auto-extract concept nodes from SCBE relevance keys
            if result.scbe_relevance:
                for concept, score in result.scbe_relevance.items():
                    concept_id = self.add_concept(concept)
                    self.edges.append(GraphEdge(
                        source_id=node_id,
                        target_id=concept_id,
                        edge_type=LinkType.SEMANTIC,
                        confidence=score,
                        label=f"relevance {score:.0%}",
                    ))

            # Auto-extract domain nodes from tags
            for tag in result.tags[:3]:
                if tag:
                    domain_id = self._add_domain(tag)
                    self.edges.append(GraphEdge(
                        source_id=node_id,
                        target_id=domain_id,
                        edge_type=LinkType.KEYWORD,
                        confidence=0.6,
                        label=f"tagged '{tag}'",
                    ))

        return node_id

    def add_link(self, source_title: str, link: WikiLink) -> None:
        """Add a WikiLink as an edge from *source_title* to the link target.

        Creates the source node (as ``result`` type) and target node
        (as ``vault_page`` type) if they do not already exist.
        """
        source_id = self._ensure_node(source_title, "result")
        target_id = self._ensure_node(link.target_page, "vault_page")

        self.edges.append(GraphEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=link.link_type,
            confidence=link.confidence,
            label=link.reason,
        ))

    def add_concept(self, concept: str, domain: str = "") -> str:
        """Add or retrieve a ``concept`` node. Returns its ID."""
        node_id = self._make_id("concept", concept)
        if node_id not in self.nodes:
            self.nodes[node_id] = GraphNode(
                id=node_id,
                label=concept,
                node_type="concept",
                metadata={"domain": domain} if domain else {},
            )
        # Link concept to domain if provided
        if domain:
            domain_id = self._add_domain(domain)
            already_linked = any(
                e.source_id == node_id and e.target_id == domain_id
                for e in self.edges
            )
            if not already_linked:
                self.edges.append(GraphEdge(
                    source_id=node_id,
                    target_id=domain_id,
                    edge_type=LinkType.KEYWORD,
                    confidence=0.8,
                    label=f"domain: {domain}",
                ))
        return node_id

    # ------------------------------------------------------------------ #
    # Renderers                                                            #
    # ------------------------------------------------------------------ #

    def render_mermaid(self, direction: str = "TB") -> str:
        """Render as Mermaid diagram syntax.

        Node shapes by type:
        - result: stadium ``([  ])``
        - vault_page: rect ``[  ]``
        - concept: circle ``((  ))``
        - domain: hexagon ``{{  }}``

        Edge styles by LinkType:
        - KEYWORD: solid ``-->``
        - CITATION: thick ``==>``
        - CDDM_MORPHISM: dotted ``-.->``
        - SEMANTIC: dashed ``---``
        """
        if not self.nodes:
            return "graph TB\n    empty[No data]"

        lines: List[str] = [f"graph {direction}"]

        # Emit node declarations
        for node in self.nodes.values():
            left, right = _MERMAID_NODE_SHAPES.get(
                node.node_type, ("[", "]"),
            )
            safe_label = self._mermaid_escape(node.label)
            lines.append(f"    {node.id}{left}\"{safe_label}\"{right}")

        lines.append("")

        # Emit edges
        for edge in self.edges:
            arrow = _MERMAID_EDGE_STYLES.get(edge.edge_type, "-->")
            if edge.label:
                safe_label = self._mermaid_escape(edge.label)
                # Truncate long labels for readability
                if len(safe_label) > 40:
                    safe_label = safe_label[:37] + "..."
                lines.append(
                    f"    {edge.source_id} {arrow}|{safe_label}| {edge.target_id}"
                )
            else:
                lines.append(f"    {edge.source_id} {arrow} {edge.target_id}")

        # Add style classes
        lines.append("")
        lines.append("    classDef result fill:#d4edda,stroke:#28a745,stroke-width:2px")
        lines.append("    classDef vault_page fill:#cce5ff,stroke:#004085,stroke-width:2px")
        lines.append("    classDef concept fill:#f8d7da,stroke:#721c24,stroke-width:2px")
        lines.append("    classDef domain fill:#fff3cd,stroke:#856404,stroke-width:2px")

        # Assign classes
        for node_type in ("result", "vault_page", "concept", "domain"):
            ids = [n.id for n in self.nodes.values() if n.node_type == node_type]
            if ids:
                lines.append(f"    class {','.join(ids)} {node_type}")

        return "\n".join(lines)

    def render_obsidian_canvas(
        self,
        width: int = 1200,
        height: int = 800,
    ) -> str:
        """Render as Obsidian Canvas JSON format.

        Auto-layouts nodes grouped by type in a grid arrangement.
        Returns a JSON string suitable for ``.canvas`` files.
        """
        if not self.nodes:
            return json.dumps({"nodes": [], "edges": []}, indent=2)

        canvas_nodes: List[Dict[str, Any]] = []
        canvas_edges: List[Dict[str, Any]] = []

        # Group nodes by type for spatial clustering
        groups: Dict[str, List[GraphNode]] = defaultdict(list)
        for node in self.nodes.values():
            groups[node.node_type].append(node)

        # Assign grid positions: each type gets a column
        type_order = ["result", "vault_page", "concept", "domain"]
        col_types = [t for t in type_order if t in groups]
        # Add any types not in the standard order
        for t in groups:
            if t not in col_types:
                col_types.append(t)

        num_cols = max(len(col_types), 1)
        col_width = width // num_cols
        node_w = 250
        node_h = 60

        for col_idx, ntype in enumerate(col_types):
            col_nodes = groups[ntype]
            num_rows = len(col_nodes)
            row_spacing = max(height // max(num_rows + 1, 2), node_h + 20)
            x_base = col_idx * col_width + (col_width - node_w) // 2

            for row_idx, node in enumerate(col_nodes):
                y = (row_idx + 1) * row_spacing - node_h // 2

                canvas_node: Dict[str, Any] = {
                    "id": node.id,
                    "type": "text",
                    "text": self._canvas_node_text(node),
                    "x": x_base,
                    "y": y,
                    "width": node_w,
                    "height": node_h,
                }
                color = _CANVAS_COLORS.get(node.node_type)
                if color:
                    canvas_node["color"] = color
                canvas_nodes.append(canvas_node)

        # Emit edges
        for i, edge in enumerate(self.edges):
            # Only include edges where both endpoints exist
            if edge.source_id in self.nodes and edge.target_id in self.nodes:
                canvas_edge: Dict[str, Any] = {
                    "id": f"edge_{i}",
                    "fromNode": edge.source_id,
                    "toNode": edge.target_id,
                    "fromSide": "right",
                    "toSide": "left",
                }
                if edge.label:
                    truncated = edge.label[:50] + "..." if len(edge.label) > 50 else edge.label
                    canvas_edge["label"] = truncated
                canvas_edges.append(canvas_edge)

        canvas = {"nodes": canvas_nodes, "edges": canvas_edges}
        return json.dumps(canvas, indent=2)

    def render_adjacency_markdown(self) -> str:
        """Render as a markdown adjacency list for vault notes."""
        if not self.nodes:
            return "# Knowledge Graph\n\n_No nodes in graph._\n"

        lines: List[str] = [
            "# Knowledge Graph Adjacency List\n",
            f"**Nodes:** {len(self.nodes)}  ",
            f"**Edges:** {len(self.edges)}\n",
        ]

        # Build adjacency map
        adj: Dict[str, List[Tuple[str, GraphEdge]]] = defaultdict(list)
        for edge in self.edges:
            adj[edge.source_id].append((edge.target_id, edge))

        # Group nodes by type
        by_type: Dict[str, List[GraphNode]] = defaultdict(list)
        for node in self.nodes.values():
            by_type[node.node_type].append(node)

        for ntype in ("result", "vault_page", "concept", "domain"):
            nodes = by_type.get(ntype, [])
            if not nodes:
                continue

            type_label = ntype.replace("_", " ").title()
            lines.append(f"## {type_label} Nodes\n")

            for node in sorted(nodes, key=lambda n: n.label):
                neighbours = adj.get(node.id, [])
                if neighbours:
                    lines.append(f"- **{node.label}**")
                    for target_id, edge in neighbours:
                        target = self.nodes.get(target_id)
                        target_label = target.label if target else target_id
                        arrow = self._link_type_symbol(edge.edge_type)
                        conf = f" ({edge.confidence:.0%})" if edge.confidence > 0 else ""
                        lines.append(f"  - {arrow} [[{target_label}]]{conf}")
                else:
                    lines.append(f"- **{node.label}** _(no outgoing links)_")

            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Analysis                                                             #
    # ------------------------------------------------------------------ #

    def get_central_nodes(self, top_k: int = 5) -> List[Tuple[str, int]]:
        """Return nodes with most connections (degree centrality).

        Counts both incoming and outgoing edges.  Returns a list of
        ``(node_label, degree)`` tuples sorted by degree descending.
        """
        degree: Dict[str, int] = defaultdict(int)

        for edge in self.edges:
            degree[edge.source_id] += 1
            degree[edge.target_id] += 1

        # Map IDs to labels and sort
        ranked: List[Tuple[str, int]] = []
        for node_id, deg in degree.items():
            node = self.nodes.get(node_id)
            label = node.label if node else node_id
            ranked.append((label, deg))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def get_clusters(self) -> List[List[str]]:
        """Find connected components (clusters of related research).

        Uses BFS over undirected edges.  Returns a list of clusters
        where each cluster is a list of node labels sorted alphabetically.
        """
        if not self.nodes:
            return []

        # Build undirected adjacency
        undirected: Dict[str, Set[str]] = defaultdict(set)
        for edge in self.edges:
            undirected[edge.source_id].add(edge.target_id)
            undirected[edge.target_id].add(edge.source_id)

        visited: Set[str] = set()
        clusters: List[List[str]] = []

        for node_id in self.nodes:
            if node_id in visited:
                continue

            # BFS from this node
            cluster_ids: List[str] = []
            queue: deque[str] = deque([node_id])
            visited.add(node_id)

            while queue:
                current = queue.popleft()
                cluster_ids.append(current)
                for neighbour in undirected.get(current, set()):
                    if neighbour not in visited and neighbour in self.nodes:
                        visited.add(neighbour)
                        queue.append(neighbour)

            # Map IDs to labels
            labels = []
            for cid in cluster_ids:
                node = self.nodes.get(cid)
                labels.append(node.label if node else cid)
            labels.sort()
            clusters.append(labels)

        # Sort clusters by size descending
        clusters.sort(key=len, reverse=True)
        return clusters

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _ensure_node(self, label: str, default_type: str) -> str:
        """Return the ID for a node with *label*, creating it if needed."""
        # Check existing nodes by label first
        for node in self.nodes.values():
            if node.label == label:
                return node.id

        # Create new node
        node_id = self._make_id(default_type, label)
        if node_id not in self.nodes:
            self.nodes[node_id] = GraphNode(
                id=node_id,
                label=label,
                node_type=default_type,
            )
        return node_id

    def _add_domain(self, domain: str) -> str:
        """Add or retrieve a ``domain`` node. Returns its ID."""
        node_id = self._make_id("domain", domain)
        if node_id not in self.nodes:
            self.nodes[node_id] = GraphNode(
                id=node_id,
                label=domain,
                node_type="domain",
            )
        return node_id

    @staticmethod
    def _make_id(prefix: str, text: str) -> str:
        """Generate a short, deterministic, Mermaid-safe node ID.

        Uses an 8-char hex hash to avoid collisions while keeping
        the diagram readable.
        """
        h = hashlib.md5(f"{prefix}:{text}".encode("utf-8")).hexdigest()[:8]
        return f"{prefix}_{h}"

    @staticmethod
    def _mermaid_escape(text: str) -> str:
        """Escape special characters for Mermaid labels."""
        text = text.replace('"', "'")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace("{", "&#123;")
        text = text.replace("}", "&#125;")
        return text

    @staticmethod
    def _canvas_node_text(node: GraphNode) -> str:
        """Generate markdown text for an Obsidian canvas node."""
        type_label = node.node_type.replace("_", " ").title()
        lines = [f"**{node.label}**", f"_Type: {type_label}_"]
        if node.metadata.get("source_type"):
            lines.append(f"Source: {node.metadata['source_type']}")
        if node.metadata.get("url"):
            lines.append(f"[Link]({node.metadata['url']})")
        if node.metadata.get("domain"):
            lines.append(f"Domain: {node.metadata['domain']}")
        return "\n".join(lines)

    @staticmethod
    def _link_type_symbol(link_type: LinkType) -> str:
        """Return a text symbol for a link type in the adjacency list."""
        symbols = {
            LinkType.KEYWORD: "->",
            LinkType.CITATION: "=>",
            LinkType.CDDM_MORPHISM: "~>",
            LinkType.SEMANTIC: "--",
            LinkType.MANUAL: "->",
        }
        return symbols.get(link_type, "->")
