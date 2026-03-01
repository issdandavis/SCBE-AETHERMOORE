"""
PollyPivot — Knowledge Router with FAISS + BM25 Hybrid Search
==============================================================

Indexes Obsidian vaults, training JSONL, and codebase docs using
sentence-transformers (all-MiniLM-L6-v2, 384-dim) + FAISS for
semantic search and rank_bm25 for keyword fallback.

FastAPI endpoint on port 8400.

@layer L3, L5
@component PollyPivot.KnowledgeRouter
"""

from .indexer import KnowledgeIndexer, Document
from .searcher import HybridSearcher, SearchResult
from .api import create_app
from .quick_pivot import QuickPivot, PivotCard, ThoughtAccumulator

__all__ = [
    "KnowledgeIndexer",
    "Document",
    "HybridSearcher",
    "SearchResult",
    "QuickPivot",
    "PivotCard",
    "ThoughtAccumulator",
    "create_app",
]
