"""
AetherSearch REST API Routes
==============================
FastAPI router for governed geometric search.

Endpoints:
  POST /search/query    — Search with tongue-aware ranking + governance filtering
  POST /search/index    — Index documents with SCBE enrichment
  POST /search/enrich   — Enrich documents without indexing (preview)
  GET  /search/stats    — Index statistics
  GET  /search/health   — Meilisearch health check

Requires Meilisearch running locally (default: http://127.0.0.1:7700).
Set MEILI_URL and MEILI_MASTER_KEY env vars to override.
"""

import os
import time
import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.search_enrichment import (
    enrich_document,
    enrich_batch,
    compute_tongue_profile,
    tongue_boost_score,
    TONGUE_ORDER,
    TONGUE_WEIGHTS,
    EnrichedDocument,
)

logger = logging.getLogger("scbe.search")

# ---------------------------------------------------------------------------
# Meilisearch client (lazy init)
# ---------------------------------------------------------------------------

MEILI_URL = os.getenv("MEILI_URL", "http://127.0.0.1:7700")
MEILI_MASTER_KEY = os.getenv("MEILI_MASTER_KEY", "")
MEILI_INDEX = os.getenv("MEILI_INDEX", "aethersearch")

_meili_client = None


def _get_meili():
    """Lazy-init Meilisearch client."""
    global _meili_client
    if _meili_client is not None:
        return _meili_client
    try:
        import meilisearch

        _meili_client = meilisearch.Client(MEILI_URL, MEILI_MASTER_KEY or None)
        # Ensure index exists with searchable/filterable attributes
        try:
            _meili_client.create_index(MEILI_INDEX, {"primaryKey": "id"})
        except Exception:
            pass  # Index may already exist

        index = _meili_client.index(MEILI_INDEX)
        index.update_filterable_attributes(
            ["dominant_tongue", "governance_tier", "source"]
        )
        index.update_sortable_attributes(
            ["harmonic_distance", "friction_magnitude", "phi_weight", "indexed_at"]
        )
        index.update_searchable_attributes(["title", "content"])

        return _meili_client
    except ImportError:
        logger.warning("meilisearch package not installed — search will use in-memory fallback")
        return None
    except Exception as e:
        logger.warning(f"Meilisearch connection failed: {e} — using in-memory fallback")
        return None


# ---------------------------------------------------------------------------
# In-memory fallback index (when Meilisearch is unavailable)
# ---------------------------------------------------------------------------

_memory_index: Dict[str, Dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class SearchQuery(BaseModel):
    query: str = Field(..., description="Search query text")
    tongue_filter: Optional[str] = Field(
        None, description="Filter by dominant tongue (KO/AV/RU/CA/UM/DR)"
    )
    governance_filter: Optional[List[str]] = Field(
        None, description="Allowed governance tiers (default: ALLOW only)"
    )
    limit: int = Field(20, ge=1, le=100, description="Max results")
    tongue_boost: float = Field(
        0.3, ge=0.0, le=1.0,
        description="Weight of tongue-affinity boost in ranking (0=off, 1=dominant)"
    )


class IndexRequest(BaseModel):
    documents: List[Dict[str, str]] = Field(
        ..., description="List of {title, content, url?, source?, id?} documents"
    )


class EnrichRequest(BaseModel):
    title: str
    content: str
    url: str = ""
    source: str = "manual"


class SearchResult(BaseModel):
    id: str
    title: str
    content_preview: str
    url: str
    dominant_tongue: str
    governance_tier: str
    harmonic_distance: float
    tongue_score: float
    combined_score: float


class SearchResponse(BaseModel):
    query: str
    query_tongue: str
    results: List[SearchResult]
    total_hits: int
    search_time_ms: float


class IndexResponse(BaseModel):
    indexed: int
    enriched: int
    governance_breakdown: Dict[str, int]


class StatsResponse(BaseModel):
    total_documents: int
    tongue_distribution: Dict[str, int]
    governance_distribution: Dict[str, int]
    index_backend: str


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

search_router = APIRouter(prefix="/search", tags=["AetherSearch"])


@search_router.post("/query", response_model=SearchResponse)
async def search_query(req: SearchQuery):
    """Search with tongue-aware ranking and governance filtering.

    Flow:
      1. Classify query into tongue profile
      2. Search Meilisearch (or memory fallback)
      3. Apply governance filter (default: ALLOW only)
      4. Re-rank by tongue affinity boost
      5. Return sorted results
    """
    start = time.time()

    # Classify query tongue
    query_profile = compute_tongue_profile(req.query)
    query_tongue_idx = query_profile.index(max(query_profile))
    query_tongue = TONGUE_ORDER[query_tongue_idx]

    # Governance filter defaults to ALLOW only
    allowed_tiers = req.governance_filter or ["ALLOW"]

    meili = _get_meili()
    raw_hits = []

    if meili is not None:
        # Meilisearch search
        index = meili.index(MEILI_INDEX)
        filters = []
        if req.tongue_filter:
            filters.append(f'dominant_tongue = "{req.tongue_filter}"')
        tier_filter = " OR ".join(f'governance_tier = "{t}"' for t in allowed_tiers)
        if tier_filter:
            filters.append(f"({tier_filter})")

        filter_str = " AND ".join(filters) if filters else None
        search_params = {"limit": req.limit * 2}  # Over-fetch for re-ranking
        if filter_str:
            search_params["filter"] = filter_str

        try:
            result = index.search(req.query, search_params)
            raw_hits = result.get("hits", [])
        except Exception as e:
            logger.error(f"Meilisearch search failed: {e}")
            raw_hits = []
    else:
        # In-memory fallback — simple substring match
        query_lower = req.query.lower()
        for doc_id, doc in _memory_index.items():
            if doc.get("governance_tier") not in allowed_tiers:
                continue
            if req.tongue_filter and doc.get("dominant_tongue") != req.tongue_filter:
                continue
            text = f"{doc.get('title', '')} {doc.get('content', '')}".lower()
            if query_lower in text or any(w in text for w in query_lower.split()):
                raw_hits.append(doc)

    # Re-rank with tongue affinity boost
    scored_results = []
    for hit in raw_hits:
        doc_profile = hit.get("tongue_profile", [0.05] * 6)
        t_score = tongue_boost_score(query_profile, doc_profile)

        # Combined score: text relevance (position) + tongue boost
        position_score = 1.0  # Meilisearch already ranked by relevance
        combined = (1 - req.tongue_boost) * position_score + req.tongue_boost * t_score

        content = hit.get("content", "")
        scored_results.append(
            SearchResult(
                id=hit.get("id", ""),
                title=hit.get("title", ""),
                content_preview=content[:300] + ("..." if len(content) > 300 else ""),
                url=hit.get("url", ""),
                dominant_tongue=hit.get("dominant_tongue", "CA"),
                governance_tier=hit.get("governance_tier", "ALLOW"),
                harmonic_distance=hit.get("harmonic_distance", 0.0),
                tongue_score=round(t_score, 4),
                combined_score=round(combined, 4),
            )
        )

    # Sort by combined score descending, take top N
    scored_results.sort(key=lambda r: r.combined_score, reverse=True)
    scored_results = scored_results[: req.limit]

    elapsed_ms = (time.time() - start) * 1000

    return SearchResponse(
        query=req.query,
        query_tongue=query_tongue,
        results=scored_results,
        total_hits=len(scored_results),
        search_time_ms=round(elapsed_ms, 2),
    )


@search_router.post("/index", response_model=IndexResponse)
async def index_documents(req: IndexRequest):
    """Index documents with SCBE enrichment.

    Each document passes through the enrichment pipeline:
      raw text -> tongue profile -> Poincare embedding -> harmonic wall -> governance tier

    Then gets indexed into Meilisearch (or memory fallback).
    """
    enriched = enrich_batch(req.documents)

    governance_counts: Dict[str, int] = {}
    meili_docs = []

    for doc in enriched:
        tier = doc.governance_tier
        governance_counts[tier] = governance_counts.get(tier, 0) + 1
        meili_docs.append(doc.to_meili_doc())

    meili = _get_meili()
    if meili is not None:
        try:
            index = meili.index(MEILI_INDEX)
            index.add_documents(meili_docs)
        except Exception as e:
            logger.error(f"Meilisearch indexing failed: {e}")
            # Fall through to memory index
            for doc in meili_docs:
                _memory_index[doc["id"]] = doc
    else:
        for doc in meili_docs:
            _memory_index[doc["id"]] = doc

    return IndexResponse(
        indexed=len(meili_docs),
        enriched=len(enriched),
        governance_breakdown=governance_counts,
    )


@search_router.post("/enrich")
async def enrich_preview(req: EnrichRequest):
    """Enrich a single document without indexing — preview the geometric metadata."""
    doc = enrich_document(
        title=req.title,
        content=req.content,
        url=req.url,
        source=req.source,
    )
    return doc.to_meili_doc()


@search_router.get("/stats", response_model=StatsResponse)
async def search_stats():
    """Index statistics: document count, tongue distribution, governance tiers."""
    meili = _get_meili()

    if meili is not None:
        try:
            index = meili.index(MEILI_INDEX)
            stats = index.get_stats()
            total = stats.get("numberOfDocuments", 0)

            # Get distributions via facets
            tongue_dist = {}
            gov_dist = {}
            for tongue in TONGUE_ORDER:
                try:
                    r = index.search("", {"filter": f'dominant_tongue = "{tongue}"', "limit": 0})
                    tongue_dist[tongue] = r.get("estimatedTotalHits", 0)
                except Exception:
                    tongue_dist[tongue] = 0

            for tier in ["ALLOW", "QUARANTINE", "ESCALATE", "DENY"]:
                try:
                    r = index.search("", {"filter": f'governance_tier = "{tier}"', "limit": 0})
                    gov_dist[tier] = r.get("estimatedTotalHits", 0)
                except Exception:
                    gov_dist[tier] = 0

            return StatsResponse(
                total_documents=total,
                tongue_distribution=tongue_dist,
                governance_distribution=gov_dist,
                index_backend="meilisearch",
            )
        except Exception as e:
            logger.warning(f"Stats from Meilisearch failed: {e}")

    # Memory fallback stats
    tongue_dist = {t: 0 for t in TONGUE_ORDER}
    gov_dist = {"ALLOW": 0, "QUARANTINE": 0, "ESCALATE": 0, "DENY": 0}
    for doc in _memory_index.values():
        t = doc.get("dominant_tongue", "CA")
        tongue_dist[t] = tongue_dist.get(t, 0) + 1
        g = doc.get("governance_tier", "ALLOW")
        gov_dist[g] = gov_dist.get(g, 0) + 1

    return StatsResponse(
        total_documents=len(_memory_index),
        tongue_distribution=tongue_dist,
        governance_distribution=gov_dist,
        index_backend="memory",
    )


@search_router.get("/health")
async def search_health():
    """Health check for AetherSearch backend."""
    meili = _get_meili()
    if meili is not None:
        try:
            health = meili.health()
            return {
                "status": "healthy",
                "backend": "meilisearch",
                "meili_url": MEILI_URL,
                "meili_status": health.get("status", "unknown"),
                "index": MEILI_INDEX,
            }
        except Exception as e:
            return {
                "status": "degraded",
                "backend": "memory_fallback",
                "meili_error": str(e),
                "memory_docs": len(_memory_index),
            }

    return {
        "status": "degraded",
        "backend": "memory_fallback",
        "reason": "meilisearch package not installed or not reachable",
        "memory_docs": len(_memory_index),
    }
