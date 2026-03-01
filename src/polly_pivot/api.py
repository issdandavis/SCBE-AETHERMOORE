"""
PollyPivot API — FastAPI endpoint on port 8400
===============================================

Provides REST API for knowledge search and indexing.

Endpoints:
  GET  /health          — Health check
  POST /index           — Add documents to the index
  POST /build           — Build/rebuild the search index
  POST /search          — Hybrid search
  POST /search/semantic — Pure semantic search
  POST /search/keyword  — Pure keyword search
  GET  /stats           — Index statistics

@layer L3, L5
@component PollyPivot.API
"""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .indexer import KnowledgeIndexer
from .searcher import HybridSearcher, SearchResult

# Module-level indexer (singleton for the API)
_indexer: Optional[KnowledgeIndexer] = None
_searcher: Optional[HybridSearcher] = None


class AddTextRequest(BaseModel):
    text: str
    source_path: str = ""
    title: str = ""
    doc_type: str = "text"


class AddDirectoryRequest(BaseModel):
    directory: str
    extensions: Optional[List[str]] = None
    doc_type: Optional[str] = None
    recursive: bool = True


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    tongue_filter: Optional[str] = None
    doc_type_filter: Optional[str] = None


class SearchResultResponse(BaseModel):
    doc_id: str
    title: str
    source_path: str
    text: str
    tongue: str
    doc_type: str
    score: float
    semantic_score: float
    keyword_score: float
    rank: int


def _result_to_response(r: SearchResult) -> SearchResultResponse:
    return SearchResultResponse(
        doc_id=r.document.doc_id,
        title=r.document.title,
        source_path=r.document.source_path,
        text=r.document.text[:500],  # truncate for API response
        tongue=r.document.tongue,
        doc_type=r.document.doc_type,
        score=r.score,
        semantic_score=r.semantic_score,
        keyword_score=r.keyword_score,
        rank=r.rank,
    )


def create_app(indexer: Optional[KnowledgeIndexer] = None) -> FastAPI:
    """Create the PollyPivot FastAPI application.

    Args:
        indexer: Optional pre-built indexer. If None, creates a new one.

    Returns:
        FastAPI application.
    """
    global _indexer, _searcher

    app = FastAPI(
        title="PollyPivot Knowledge Router",
        description="Hybrid semantic + keyword search for SCBE knowledge bases",
        version="1.0.0",
    )

    _indexer = indexer or KnowledgeIndexer()
    if _indexer.is_built:
        _searcher = HybridSearcher(_indexer)

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "service": "polly_pivot",
            "port": 8400,
            "indexed": _indexer.doc_count if _indexer else 0,
            "built": _indexer.is_built if _indexer else False,
        }

    @app.post("/index/text")
    async def add_text(req: AddTextRequest):
        if _indexer is None:
            raise HTTPException(500, "Indexer not initialized")
        count = _indexer.add_text(
            text=req.text,
            source_path=req.source_path,
            title=req.title,
            doc_type=req.doc_type,
        )
        return {"chunks_added": count, "total_documents": _indexer.doc_count}

    @app.post("/index/directory")
    async def add_directory(req: AddDirectoryRequest):
        if _indexer is None:
            raise HTTPException(500, "Indexer not initialized")
        count = _indexer.add_directory(
            directory=req.directory,
            extensions=req.extensions,
            doc_type=req.doc_type,
            recursive=req.recursive,
        )
        return {"chunks_added": count, "total_documents": _indexer.doc_count}

    @app.post("/build")
    async def build_index():
        global _searcher
        if _indexer is None:
            raise HTTPException(500, "Indexer not initialized")
        _indexer.build()
        _searcher = HybridSearcher(_indexer)
        return {"status": "built", "documents": _indexer.doc_count}

    @app.post("/search", response_model=List[SearchResultResponse])
    async def search(req: SearchRequest):
        if _searcher is None:
            raise HTTPException(400, "Index not built. Call POST /build first.")
        results = _searcher.search(
            query=req.query,
            top_k=req.top_k,
            tongue_filter=req.tongue_filter,
            doc_type_filter=req.doc_type_filter,
        )
        return [_result_to_response(r) for r in results]

    @app.post("/search/semantic", response_model=List[SearchResultResponse])
    async def search_semantic(req: SearchRequest):
        if _searcher is None:
            raise HTTPException(400, "Index not built. Call POST /build first.")
        sem_results = _searcher.search_semantic(req.query, req.top_k)
        results = []
        for rank, (idx, score) in enumerate(sem_results):
            doc = _indexer.documents[idx]
            results.append(SearchResultResponse(
                doc_id=doc.doc_id,
                title=doc.title,
                source_path=doc.source_path,
                text=doc.text[:500],
                tongue=doc.tongue,
                doc_type=doc.doc_type,
                score=score,
                semantic_score=score,
                keyword_score=0.0,
                rank=rank,
            ))
        return results

    @app.post("/search/keyword", response_model=List[SearchResultResponse])
    async def search_keyword(req: SearchRequest):
        if _searcher is None:
            raise HTTPException(400, "Index not built. Call POST /build first.")
        kw_results = _searcher.search_keyword(req.query, req.top_k)
        results = []
        for rank, (idx, score) in enumerate(kw_results):
            doc = _indexer.documents[idx]
            results.append(SearchResultResponse(
                doc_id=doc.doc_id,
                title=doc.title,
                source_path=doc.source_path,
                text=doc.text[:500],
                tongue=doc.tongue,
                doc_type=doc.doc_type,
                score=score,
                semantic_score=0.0,
                keyword_score=score,
                rank=rank,
            ))
        return results

    @app.get("/stats")
    async def stats():
        if _indexer is None:
            raise HTTPException(500, "Indexer not initialized")
        return _indexer.stats()

    return app


def cli_main():
    """CLI entry point for the PollyPivot server."""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="PollyPivot Knowledge Router")
    parser.add_argument("--port", type=int, default=8400)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--index-dir", type=str, help="Directory to pre-index")
    args = parser.parse_args()

    indexer = KnowledgeIndexer()
    if args.index_dir:
        print(f"Pre-indexing {args.index_dir}...")
        count = indexer.add_directory(args.index_dir)
        print(f"Added {count} document chunks")
        print("Building index...")
        indexer.build()
        print(f"Index built with {indexer.doc_count} documents")

    app = create_app(indexer)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    cli_main()
