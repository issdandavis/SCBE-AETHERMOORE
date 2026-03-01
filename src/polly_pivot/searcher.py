"""
PollyPivot Searcher — Hybrid FAISS + BM25 search
=================================================

Combines semantic search (FAISS inner product) with keyword search
(BM25Okapi) using reciprocal rank fusion for result merging.

@layer L5
@component PollyPivot.Searcher
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .indexer import KnowledgeIndexer, Document

try:
    import faiss
except ImportError:
    faiss = None

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None


@dataclass(frozen=True)
class SearchResult:
    """A single search result with relevance scoring."""
    document: Document
    score: float           # combined relevance score
    semantic_score: float  # FAISS cosine similarity
    keyword_score: float   # BM25 score
    rank: int              # position in results (0-based)


class HybridSearcher:
    """Hybrid search combining FAISS semantic search with BM25 keyword search.

    Uses Reciprocal Rank Fusion (RRF) to merge results from both indices:
        RRF(d) = sum(1 / (k + rank_i(d))) for each ranker i

    Args:
        indexer: Built KnowledgeIndexer with FAISS and BM25 indices.
        rrf_k: Reciprocal rank fusion constant (default 60).
        semantic_weight: Weight for semantic results in fusion (default 0.7).
        keyword_weight: Weight for keyword results in fusion (default 0.3).
    """

    def __init__(
        self,
        indexer: KnowledgeIndexer,
        rrf_k: int = 60,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ):
        if not indexer.is_built:
            raise ValueError("Indexer must be built before creating searcher")
        self.indexer = indexer
        self.rrf_k = rrf_k
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight

    def search_semantic(
        self,
        query: str,
        top_k: int = 10,
    ) -> List[Tuple[int, float]]:
        """Pure semantic search using FAISS.

        Returns:
            List of (doc_index, similarity_score) tuples.
        """
        if self.indexer.faiss_index is None or faiss is None:
            return []

        query_embedding = self.indexer.model.encode(
            [query], normalize_embeddings=True
        ).astype(np.float32)

        n_docs = self.indexer.doc_count
        k = min(top_k, n_docs)
        if k == 0:
            return []

        scores, indices = self.indexer.faiss_index.search(query_embedding, k)
        results = []
        for i in range(k):
            idx = int(indices[0][i])
            if idx >= 0:
                results.append((idx, float(scores[0][i])))
        return results

    def search_keyword(
        self,
        query: str,
        top_k: int = 10,
    ) -> List[Tuple[int, float]]:
        """Pure keyword search using BM25.

        Returns:
            List of (doc_index, bm25_score) tuples.
        """
        if self.indexer.bm25_index is None or BM25Okapi is None:
            return []

        tokens = query.lower().split()
        if not tokens:
            return []

        scores = self.indexer.bm25_index.get_scores(tokens)
        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            s = float(scores[idx])
            if s > 0:
                results.append((int(idx), s))
        return results

    def search(
        self,
        query: str,
        top_k: int = 10,
        tongue_filter: Optional[str] = None,
        doc_type_filter: Optional[str] = None,
    ) -> List[SearchResult]:
        """Hybrid search combining semantic and keyword results.

        Uses Reciprocal Rank Fusion (RRF) to merge results.

        Args:
            query: Search query string.
            top_k: Maximum number of results.
            tongue_filter: Only return results matching this Sacred Tongue.
            doc_type_filter: Only return results of this document type.

        Returns:
            List of SearchResult sorted by combined relevance.
        """
        # Get results from both indices (fetch more to account for filtering)
        fetch_k = top_k * 3
        semantic_results = self.search_semantic(query, fetch_k)
        keyword_results = self.search_keyword(query, fetch_k)

        # Build RRF scores
        rrf_scores: Dict[int, float] = {}
        semantic_scores: Dict[int, float] = {}
        keyword_scores_map: Dict[int, float] = {}

        for rank, (idx, score) in enumerate(semantic_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + self.semantic_weight / (self.rrf_k + rank)
            semantic_scores[idx] = score

        for rank, (idx, score) in enumerate(keyword_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + self.keyword_weight / (self.rrf_k + rank)
            keyword_scores_map[idx] = score

        # Sort by RRF score
        sorted_indices = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)

        # Build SearchResult list with filtering
        results = []
        for idx in sorted_indices:
            if len(results) >= top_k:
                break

            doc = self.indexer.documents[idx]

            # Apply filters
            if tongue_filter and doc.tongue != tongue_filter:
                continue
            if doc_type_filter and doc.doc_type != doc_type_filter:
                continue

            results.append(SearchResult(
                document=doc,
                score=rrf_scores[idx],
                semantic_score=semantic_scores.get(idx, 0.0),
                keyword_score=keyword_scores_map.get(idx, 0.0),
                rank=len(results),
            ))

        return results

    def search_by_tongue(
        self,
        query: str,
        tongue: str,
        top_k: int = 10,
    ) -> List[SearchResult]:
        """Search filtered by Sacred Tongue affinity.

        Args:
            query: Search query.
            tongue: Sacred Tongue to filter by (KO/AV/RU/CA/UM/DR).
            top_k: Maximum results.

        Returns:
            Filtered search results.
        """
        return self.search(query, top_k=top_k, tongue_filter=tongue)

    def find_similar(
        self,
        doc_index: int,
        top_k: int = 5,
    ) -> List[SearchResult]:
        """Find documents similar to a given document (by embedding).

        Args:
            doc_index: Index of the source document.
            top_k: Number of similar documents to return.

        Returns:
            List of similar documents (excluding the source).
        """
        if self.indexer._embeddings is None or self.indexer.faiss_index is None:
            return []

        query_embedding = self.indexer._embeddings[doc_index:doc_index + 1]
        n_docs = self.indexer.doc_count
        k = min(top_k + 1, n_docs)

        scores, indices = self.indexer.faiss_index.search(query_embedding, k)
        results = []
        for i in range(k):
            idx = int(indices[0][i])
            if idx == doc_index or idx < 0:
                continue
            if len(results) >= top_k:
                break
            results.append(SearchResult(
                document=self.indexer.documents[idx],
                score=float(scores[0][i]),
                semantic_score=float(scores[0][i]),
                keyword_score=0.0,
                rank=len(results),
            ))
        return results
