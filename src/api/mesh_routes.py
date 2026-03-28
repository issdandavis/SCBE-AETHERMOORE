"""Semantic Mesh HTTP Routes — REST API for the SCBE Knowledge Graph.

Exposes the SemanticMesh (embryonic intake, tongue-space search,
governed writes) over HTTP for GKE/Cloud Run deployment.

Endpoints:
    POST /mesh/ingest      — Ingest a concept (binary → ternary → node)
    POST /mesh/query       — Semantic search by tongue-space similarity
    GET  /mesh/context/{id} — Subgraph around a node
    POST /mesh/connect     — Create semantic link between nodes
    POST /mesh/path        — Shortest path between concepts
    GET  /mesh/stats       — Mesh health statistics
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("mesh-routes")

# ── Lazy-init SemanticMesh ──────────────────────────────────────────
_mesh = None


def _get_mesh():
    """Lazy-initialize the SemanticMesh singleton."""
    global _mesh
    if _mesh is None:
        from src.mcp_server.semantic_mesh import SemanticMesh

        db_path = os.environ.get("SEMANTIC_MESH_DB_PATH", "data/semantic_mesh.db")
        # Ensure parent directory exists
        import pathlib

        pathlib.Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _mesh = SemanticMesh(db_path)
        logger.info("Semantic mesh initialized: %s", db_path)
    return _mesh


# ── Pydantic Models ─────────────────────────────────────────────────


class IngestRequest(BaseModel):
    content: str = Field(..., description="The concept/knowledge to ingest")
    label: Optional[str] = Field(
        None, description="Short label (defaults to first 100 chars)"
    )
    node_type: str = Field(
        "CONCEPT", description="EMOTION|LITERARY|PROVERB|CONCEPT|SOURCE|TONGUE"
    )
    connect_to: Optional[List[str]] = Field(None, description="Node IDs to connect to")


class QueryRequest(BaseModel):
    text: str = Field(..., description="Search text (matched by semantic similarity)")
    limit: int = Field(10, ge=1, le=100)
    tongue_filter: Optional[str] = Field(None, description="KO|AV|RU|CA|UM|DR")
    node_type: Optional[str] = Field(None)


class ConnectRequest(BaseModel):
    source_id: str
    target_id: str
    edge_type: str = Field("MAPS_TO")
    weight: float = Field(1.0, ge=0.0, le=10.0)


class PathRequest(BaseModel):
    start_id: str
    end_id: str


# ── Router ──────────────────────────────────────────────────────────

mesh_router = APIRouter(prefix="/mesh", tags=["Semantic Mesh"])


@mesh_router.post("/ingest")
async def ingest(req: IngestRequest) -> Dict[str, Any]:
    """Ingest a concept through the embryonic pipeline.

    Raw text → tongue classification → 6D embedding → ternary quantization
    → manifold assignment (M+/M0/M-) → breathing pulse → governed node.
    """
    mesh = _get_mesh()
    try:
        result = mesh.ingest(
            content=req.content,
            label=req.label,
            node_type=req.node_type,
            connect_to=req.connect_to,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@mesh_router.post("/query")
async def query(req: QueryRequest) -> List[Dict[str, Any]]:
    """Search by tongue-space cosine similarity."""
    mesh = _get_mesh()
    try:
        return mesh.query(
            text=req.text,
            limit=req.limit,
            tongue_filter=req.tongue_filter,
            node_type=req.node_type,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@mesh_router.get("/context/{node_id}")
async def context(node_id: str, depth: int = 2) -> Dict[str, Any]:
    """Get subgraph around a node (N-hop neighborhood)."""
    mesh = _get_mesh()
    try:
        return mesh.get_context(node_id, depth=min(depth, 5))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@mesh_router.post("/connect")
async def connect(req: ConnectRequest) -> Dict[str, Any]:
    """Create a semantic link between two concepts."""
    mesh = _get_mesh()
    try:
        return mesh.connect(
            source_id=req.source_id,
            target_id=req.target_id,
            edge_type=req.edge_type,
            weight=req.weight,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@mesh_router.post("/path")
async def path(req: PathRequest) -> Dict[str, Any]:
    """Find shortest semantic path between two concepts."""
    mesh = _get_mesh()
    try:
        return mesh.path(start_id=req.start_id, end_id=req.end_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@mesh_router.get("/stats")
async def stats() -> Dict[str, Any]:
    """Mesh health statistics."""
    mesh = _get_mesh()
    try:
        return mesh.stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
