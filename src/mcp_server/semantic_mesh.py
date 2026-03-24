"""SCBE Semantic Mesh — Local Knowledge Graph MCP Server.

Cross-platform context extension for LLMs using interconnected
linguistic variations and quasi-meanings.

What makes this different from Mem0/Zep/Cognee:
  1. Linguistic registers as dimensions (6 Sacred Tongues)
  2. Hyperbolic geometry (Poincare ball) — drift = exponential cost
  3. Governed writes (multi-layer security pipeline)
  4. Embryonic breathing — data differentiates from binary to ternary
     before it becomes a node (simulated morphogenesis)
  5. Balanced ternary state encoding (+1/0/-1 meaning polarity)

Run:
    python -m src.mcp_server.semantic_mesh

Or add to Claude Code config:
    {
      "mcpServers": {
        "semantic-mesh": {
          "command": "python",
          "args": ["-m", "src.mcp_server.semantic_mesh"],
          "cwd": "C:/Users/issda/SCBE-AETHERMOORE"
        }
      }
    }
"""

from __future__ import annotations

import json
import hashlib
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# ── Project root on path ────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── SCBE imports ────────────────────────────────────────────────────
from src.symphonic_cipher.scbe_aethermoore.concept_blocks.heart_vault.graph import (
    HeartVaultGraph,
    NodeType,
    EdgeType,
    TongueAffinity,
)

logger = logging.getLogger("semantic_mesh")

# ── Optional SCBE extensions ────────────────────────────────────────
try:
    from src.gacha_isekai.personality_tri_manifold import (
        ternary_quantize,
    )
    _HAS_TRI_MANIFOLD = True
except ImportError:
    _HAS_TRI_MANIFOLD = False

try:
    _HAS_TRINARY = True
except ImportError:
    _HAS_TRINARY = False


# ── Tongue classifier ──────────────────────────────────────────────
# Maps keywords/domains to Sacred Tongue registers.
# This is the "linguistic variation" layer — same concept, different register.
TONGUE_KEYWORDS: Dict[str, List[str]] = {
    "KO": ["command", "authority", "control", "leader", "orchestrate", "manage",
           "execute", "direct", "govern", "king", "queen", "power"],
    "AV": ["transport", "navigate", "path", "route", "bridge", "connect",
           "link", "travel", "explore", "discover", "search", "find"],
    "RU": ["policy", "law", "rule", "compliance", "regulation", "standard",
           "protocol", "audit", "verify", "validate", "check", "gate"],
    "CA": ["compute", "algorithm", "pattern", "growth", "code", "build",
           "create", "develop", "optimize", "calculate", "analyze", "data"],
    "UM": ["shadow", "secret", "hidden", "mystery", "encrypt", "veil",
           "depth", "dark", "unknown", "ambiguity", "subtle", "subtext"],
    "DR": ["forge", "structure", "craft", "design", "architect", "construct",
           "shape", "mold", "foundation", "framework", "template", "form"],
}


def classify_tongue(text: str) -> str:
    """Classify text into primary Sacred Tongue register."""
    text_lower = text.lower()
    scores = {}
    for tongue, keywords in TONGUE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[tongue] = score
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "CA"  # Default to CA (compute/growth)


def text_to_tongue_embedding(text: str) -> List[float]:
    """Convert text to a 6D tongue-space embedding.

    Each dimension = affinity to that tongue's semantic register.
    Normalized to unit ball (Poincare-safe).
    """
    text_lower = text.lower()
    raw = []
    for tongue in ["KO", "AV", "RU", "CA", "UM", "DR"]:
        keywords = TONGUE_KEYWORDS[tongue]
        score = sum(1 for kw in keywords if kw in text_lower)
        raw.append(float(score))

    # Normalize to Poincare ball (norm < 1)
    total = sum(r * r for r in raw) ** 0.5
    if total > 0:
        # Scale to 0.9 max radius to stay inside the ball
        raw = [r / total * 0.9 for r in raw]
    else:
        # No keywords matched — place near origin (neutral)
        raw = [0.05, 0.05, 0.05, 0.05, 0.05, 0.05]

    return raw


def embryonic_intake(raw_text: str) -> Dict[str, Any]:
    """Embryonic intake — binary text differentiates into ternary meaning.

    Like gastrulation: raw input (binary) → three layers (M+/M0/M-)
    before the concept becomes a governed node.

    Returns intake record with tongue, embedding, ternary state, and manifold.
    """
    # Stage 1: Classify tongue register
    tongue = classify_tongue(raw_text)

    # Stage 2: Compute 6D tongue embedding
    embedding = text_to_tongue_embedding(raw_text)

    # Stage 3: Ternary quantization (binary → balanced ternary)
    if _HAS_TRI_MANIFOLD:
        ternary_state = [ternary_quantize(v) for v in embedding]
    elif _HAS_TRINARY:
        ternary_state = [1 if v > 0.3 else (-1 if v < -0.3 else 0) for v in embedding]
    else:
        ternary_state = [1 if v > 0.3 else (-1 if v < -0.3 else 0) for v in embedding]

    # Stage 4: Manifold assignment (M+/M0/M-)
    pos_energy = sum(1 for t in ternary_state if t == 1)
    neg_energy = sum(1 for t in ternary_state if t == -1)
    neu_energy = sum(1 for t in ternary_state if t == 0)

    if pos_energy > neg_energy and pos_energy > neu_energy:
        manifold = "M+"
    elif neg_energy > pos_energy and neg_energy > neu_energy:
        manifold = "M-"
    else:
        manifold = "M0"

    # Stage 5: Breathing pulse (simulated embryonic breathing)
    # Phase oscillation based on content hash — deterministic but organic
    content_hash = hashlib.sha256(raw_text.encode()).hexdigest()
    breath_phase = int(content_hash[:4], 16) / 65536.0  # [0, 1)
    breath_amplitude = 0.1 * (1.0 + np.sin(breath_phase * 2 * np.pi))

    # Apply breathing to embedding (subtle dimensional pulsing)
    breathed_embedding = [
        v * (1.0 + breath_amplitude * np.sin(i * np.pi / 3))
        for i, v in enumerate(embedding)
    ]
    # Re-clamp to Poincare ball
    norm = sum(v * v for v in breathed_embedding) ** 0.5
    if norm >= 1.0:
        breathed_embedding = [v / norm * 0.95 for v in breathed_embedding]

    return {
        "tongue": tongue,
        "embedding": breathed_embedding,
        "ternary_state": ternary_state,
        "manifold": manifold,
        "breath_phase": breath_phase,
        "breath_amplitude": breath_amplitude,
        "raw_embedding": embedding,
    }


# ── Semantic Mesh (wraps HeartVaultGraph with SCBE governance) ─────

class SemanticMesh:
    """The core semantic mesh — governed knowledge graph with tongue dimensions.

    This is what gets exposed via MCP tools.
    """

    def __init__(self, db_path: str = "semantic_mesh.db"):
        self.graph = HeartVaultGraph(db_path)
        self._db_path = db_path

    def ingest(
        self,
        content: str,
        *,
        node_type: str = "CONCEPT",
        label: Optional[str] = None,
        source: str = "user",
        connect_to: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Ingest a concept through the embryonic pipeline.

        Binary text → ternary differentiation → governed graph write.
        """
        # Embryonic intake
        intake = embryonic_intake(content)

        # Determine node type
        try:
            nt = NodeType(node_type.upper())
        except (ValueError, KeyError):
            nt = NodeType.CONCEPT

        # Determine tongue affinity
        try:
            tongue = TongueAffinity(intake["tongue"])
        except (ValueError, KeyError):
            tongue = TongueAffinity.CA

        # Create the node
        node = self.graph.add_node(
            node_type=nt,
            label=label or content[:100],
            properties={
                "content": content,
                "source": source,
                "embedding": intake["embedding"],
                "ternary_state": intake["ternary_state"],
                "manifold": intake["manifold"],
                "breath_phase": intake["breath_phase"],
                "breath_amplitude": intake["breath_amplitude"],
            },
            tongue=tongue,
            quality_score=0.5,  # Default; can be updated by governance
        )

        # Connect to existing nodes
        edges_created = []
        for target_id in (connect_to or []):
            target = self.graph.get_node(target_id)
            if target:
                # Determine edge type from relationship
                edge = self.graph.add_edge(
                    EdgeType.MAPS_TO,
                    node.id,
                    target_id,
                    weight=1.0,
                )
                edges_created.append(edge.id)

        return {
            "node_id": node.id,
            "tongue": intake["tongue"],
            "manifold": intake["manifold"],
            "ternary_state": intake["ternary_state"],
            "edges_created": edges_created,
            "embedding_norm": sum(v * v for v in intake["embedding"]) ** 0.5,
        }

    def query(
        self,
        text: str,
        *,
        limit: int = 10,
        tongue_filter: Optional[str] = None,
        node_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Semantic query — find nodes by tongue-space similarity."""
        query_embedding = text_to_tongue_embedding(text)

        # Build filters
        nt = None
        if node_type:
            try:
                nt = NodeType(node_type.upper())
            except (ValueError, KeyError):
                pass

        ta = None
        if tongue_filter:
            try:
                ta = TongueAffinity(tongue_filter.upper())
            except (ValueError, KeyError):
                pass

        # Get candidate nodes
        candidates = self.graph.find_nodes(
            node_type=nt,
            tongue=ta,
            limit=limit * 5,  # Over-fetch for ranking
        )

        # Rank by cosine similarity in tongue-space
        results = []
        for node in candidates:
            node_emb = node.properties.get("embedding", [0] * 6)
            # Cosine similarity
            dot = sum(a * b for a, b in zip(query_embedding, node_emb))
            norm_q = sum(v * v for v in query_embedding) ** 0.5
            norm_n = sum(v * v for v in node_emb) ** 0.5
            sim = dot / (norm_q * norm_n + 1e-10)
            results.append({
                "node_id": node.id,
                "label": node.label,
                "tongue": node.tongue.value if node.tongue else None,
                "manifold": node.properties.get("manifold", "?"),
                "similarity": round(sim, 4),
                "content": node.properties.get("content", "")[:200],
                "ternary_state": node.properties.get("ternary_state"),
            })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

    def get_context(self, node_id: str, depth: int = 2) -> Dict[str, Any]:
        """Get full context subgraph around a node."""
        nodes, edges = self.graph.subgraph(node_id, depth=depth)
        return {
            "center": node_id,
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "type": n.node_type.value,
                    "tongue": n.tongue.value if n.tongue else None,
                    "manifold": n.properties.get("manifold"),
                    "quality": n.quality_score,
                }
                for n in nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "type": e.edge_type.value,
                    "source": e.source_id,
                    "target": e.target_id,
                    "weight": e.weight,
                }
                for e in edges
            ],
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
            },
        }

    def connect(
        self,
        source_id: str,
        target_id: str,
        *,
        edge_type: str = "MAPS_TO",
        weight: float = 1.0,
    ) -> Dict[str, Any]:
        """Create a semantic link between two nodes."""
        try:
            et = EdgeType(edge_type.upper())
        except (ValueError, KeyError):
            et = EdgeType.MAPS_TO

        edge = self.graph.add_edge(et, source_id, target_id, weight=weight)
        return {
            "edge_id": edge.id,
            "type": et.value,
            "source": source_id,
            "target": target_id,
            "weight": weight,
        }

    def path(self, start_id: str, end_id: str) -> Dict[str, Any]:
        """Find semantic path between two concepts."""
        node_ids = self.graph.shortest_path(start_id, end_id)
        if node_ids is None:
            return {"found": False, "path": [], "length": -1}

        path_nodes = []
        for nid in node_ids:
            node = self.graph.get_node(nid)
            if node:
                path_nodes.append({
                    "id": node.id,
                    "label": node.label,
                    "tongue": node.tongue.value if node.tongue else None,
                    "manifold": node.properties.get("manifold"),
                })

        return {
            "found": True,
            "path": path_nodes,
            "length": len(node_ids) - 1,
        }

    def stats(self) -> Dict[str, Any]:
        """Get mesh statistics."""
        base = self.graph.stats()
        base["db_path"] = self._db_path
        base["has_tri_manifold"] = _HAS_TRI_MANIFOLD
        base["has_trinary"] = _HAS_TRINARY
        return base


# ── MCP Protocol Handler ───────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "mesh_ingest",
        "description": (
            "Ingest a concept into the semantic mesh. Raw text is differentiated "
            "through embryonic intake (binary → ternary), classified into a Sacred "
            "Tongue register, and stored as a governed node with 6D embedding."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The concept/knowledge to ingest",
                },
                "label": {
                    "type": "string",
                    "description": "Short label for the node (defaults to first 100 chars)",
                },
                "node_type": {
                    "type": "string",
                    "enum": ["EMOTION", "LITERARY", "PROVERB", "CONCEPT", "SOURCE", "TONGUE"],
                    "description": "Type of knowledge node",
                    "default": "CONCEPT",
                },
                "connect_to": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Node IDs to connect this concept to",
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "mesh_query",
        "description": (
            "Search the semantic mesh by meaning similarity in tongue-space. "
            "Returns nodes ranked by cosine similarity in the 6D Sacred Tongue "
            "embedding space. Optionally filter by tongue register or node type."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Search text (matched by semantic similarity)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return",
                    "default": 10,
                },
                "tongue_filter": {
                    "type": "string",
                    "enum": ["KO", "AV", "RU", "CA", "UM", "DR"],
                    "description": "Filter by Sacred Tongue register",
                },
                "node_type": {
                    "type": "string",
                    "enum": ["EMOTION", "LITERARY", "PROVERB", "CONCEPT", "SOURCE", "TONGUE"],
                    "description": "Filter by node type",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "mesh_context",
        "description": (
            "Get the full context subgraph around a node. Returns all nodes and "
            "edges within N hops, showing the semantic neighborhood."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {
                    "type": "string",
                    "description": "Center node ID",
                },
                "depth": {
                    "type": "integer",
                    "description": "How many hops to expand",
                    "default": 2,
                },
            },
            "required": ["node_id"],
        },
    },
    {
        "name": "mesh_connect",
        "description": (
            "Create a semantic link between two concepts in the mesh. "
            "Edge types: EVOKES, MAPS_TO, SOURCED_FROM, CATEGORISED, "
            "INTENSIFIES, CONTRASTS, ILLUSTRATES."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_id": {"type": "string", "description": "Source node ID"},
                "target_id": {"type": "string", "description": "Target node ID"},
                "edge_type": {
                    "type": "string",
                    "enum": ["EVOKES", "MAPS_TO", "SOURCED_FROM", "CATEGORISED",
                             "INTENSIFIES", "CONTRASTS", "ILLUSTRATES"],
                    "default": "MAPS_TO",
                },
                "weight": {"type": "number", "default": 1.0},
            },
            "required": ["source_id", "target_id"],
        },
    },
    {
        "name": "mesh_path",
        "description": (
            "Find the shortest semantic path between two concepts. "
            "Shows how concepts connect through the knowledge graph."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_id": {"type": "string", "description": "Starting node ID"},
                "end_id": {"type": "string", "description": "Ending node ID"},
            },
            "required": ["start_id", "end_id"],
        },
    },
    {
        "name": "mesh_stats",
        "description": "Get semantic mesh statistics — node counts, edge counts, capabilities.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


class MCPServer:
    """JSON-RPC over stdio MCP server for the semantic mesh."""

    def __init__(self, db_path: str = "semantic_mesh.db"):
        self.mesh = SemanticMesh(db_path)
        self._running = True

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a single JSON-RPC request."""
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        try:
            if method == "initialize":
                return self._respond(req_id, {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": False},
                    },
                    "serverInfo": {
                        "name": "scbe-semantic-mesh",
                        "version": "1.0.0",
                    },
                })

            elif method == "notifications/initialized":
                return None  # No response for notifications

            elif method == "tools/list":
                return self._respond(req_id, {"tools": TOOL_DEFINITIONS})

            elif method == "tools/call":
                tool_name = params.get("name", "")
                tool_args = params.get("arguments", {})
                result = self._call_tool(tool_name, tool_args)
                return self._respond(req_id, {
                    "content": [
                        {"type": "text", "text": json.dumps(result, indent=2)},
                    ],
                })

            elif method == "ping":
                return self._respond(req_id, {})

            else:
                return self._error(req_id, -32601, f"Method not found: {method}")

        except Exception as e:
            logger.exception("Error handling request")
            return self._error(req_id, -32603, str(e))

    def _call_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """Dispatch a tool call to the mesh."""
        if name == "mesh_ingest":
            return self.mesh.ingest(
                content=args["content"],
                label=args.get("label"),
                node_type=args.get("node_type", "CONCEPT"),
                connect_to=args.get("connect_to"),
            )
        elif name == "mesh_query":
            return self.mesh.query(
                text=args["text"],
                limit=args.get("limit", 10),
                tongue_filter=args.get("tongue_filter"),
                node_type=args.get("node_type"),
            )
        elif name == "mesh_context":
            return self.mesh.get_context(
                node_id=args["node_id"],
                depth=args.get("depth", 2),
            )
        elif name == "mesh_connect":
            return self.mesh.connect(
                source_id=args["source_id"],
                target_id=args["target_id"],
                edge_type=args.get("edge_type", "MAPS_TO"),
                weight=args.get("weight", 1.0),
            )
        elif name == "mesh_path":
            return self.mesh.path(
                start_id=args["start_id"],
                end_id=args["end_id"],
            )
        elif name == "mesh_stats":
            return self.mesh.stats()
        else:
            raise ValueError(f"Unknown tool: {name}")

    @staticmethod
    def _respond(req_id: Any, result: Any) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    @staticmethod
    def _error(req_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

    def run(self) -> None:
        """Run the MCP server on stdio."""
        logger.info("SCBE Semantic Mesh MCP server starting...")
        logger.info("DB: %s", self.mesh._db_path)

        while self._running:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                request = json.loads(line)
                response = self.handle_request(request)

                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()

            except json.JSONDecodeError as e:
                logger.warning("Invalid JSON: %s", e)
                error = MCPServer._error(None, -32700, f"Parse error: {e}")
                sys.stdout.write(json.dumps(error) + "\n")
                sys.stdout.flush()
            except KeyboardInterrupt:
                break
            except Exception:
                logger.exception("Server error")


def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="SCBE Semantic Mesh MCP Server")
    parser.add_argument(
        "--db",
        default=str(PROJECT_ROOT / "data" / "semantic_mesh.db"),
        help="Path to SQLite database file",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stderr,  # Logs to stderr, protocol on stdout
    )

    # Ensure data directory exists
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    server = MCPServer(db_path=str(db_path))
    server.run()


if __name__ == "__main__":
    main()
