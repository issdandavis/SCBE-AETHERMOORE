"""Tests for src/polly_pivot/ — PollyPivot Knowledge Router."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.polly_pivot.indexer import (
    KnowledgeIndexer,
    Document,
    _chunk_text,
    _detect_tongue,
)
from src.polly_pivot.searcher import HybridSearcher, SearchResult


# ── Text Chunking Tests ─────────────────────────────────────────────────

class TestChunking:
    def test_short_text_single_chunk(self):
        chunks = _chunk_text("Hello world", max_chars=100)
        assert len(chunks) == 1
        assert chunks[0] == "Hello world"

    def test_long_text_multiple_chunks(self):
        text = "x" * 3000
        chunks = _chunk_text(text, max_chars=1000, overlap=100)
        assert len(chunks) > 1
        # All chunks except possibly the last should be max_chars
        for chunk in chunks[:-1]:
            assert len(chunk) == 1000

    def test_overlap_preserved(self):
        text = "ABCDEFGHIJ" * 200  # 2000 chars
        chunks = _chunk_text(text, max_chars=1000, overlap=200)
        # Check that chunks overlap
        if len(chunks) >= 2:
            assert chunks[0][-200:] == chunks[1][:200]

    def test_empty_text(self):
        chunks = _chunk_text("")
        assert len(chunks) == 1
        assert chunks[0] == ""


# ── Tongue Detection Tests ──────────────────────────────────────────────

class TestTongueDetection:
    def test_ko_detection(self):
        assert _detect_tongue("The authority controls and governs all command structures") == "KO"

    def test_ca_detection(self):
        assert _detect_tongue("This algorithm uses encryption and cipher for computing hashes") == "CA"

    def test_um_detection(self):
        assert _detect_tongue("Security hidden in stealth shadow protection") == "UM"

    def test_no_tongue(self):
        result = _detect_tongue("The quick brown fox jumps over the lazy dog")
        assert result == ""  # no tongue keywords matched


# ── Document Tests ───────────────────────────────────────────────────────

class TestDocument:
    def test_content_hash(self):
        doc = Document(doc_id="1", source_path="/test", title="Test", text="Hello world")
        h = doc.content_hash()
        assert len(h) == 16
        # Same text → same hash
        doc2 = Document(doc_id="2", source_path="/other", title="Other", text="Hello world")
        assert doc.content_hash() == doc2.content_hash()

    def test_different_text_different_hash(self):
        doc1 = Document(doc_id="1", source_path="/a", title="A", text="Hello")
        doc2 = Document(doc_id="2", source_path="/b", title="B", text="World")
        assert doc1.content_hash() != doc2.content_hash()


# ── Indexer Tests ────────────────────────────────────────────────────────

class TestIndexer:
    def test_add_text(self):
        indexer = KnowledgeIndexer()
        count = indexer.add_text("Test document about security and encryption")
        assert count >= 1
        assert indexer.doc_count >= 1

    def test_add_text_with_chunking(self):
        indexer = KnowledgeIndexer()
        long_text = "Security " * 500  # ~4500 chars
        count = indexer.add_text(long_text)
        assert count > 1  # should chunk

    def test_add_file_markdown(self, tmp_path):
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test\n\nThis is about governance and control")
        indexer = KnowledgeIndexer()
        count = indexer.add_file(str(md_file))
        assert count >= 1

    def test_add_file_nonexistent(self):
        indexer = KnowledgeIndexer()
        count = indexer.add_file("/nonexistent/path.md")
        assert count == 0

    def test_add_jsonl(self, tmp_path):
        jsonl_file = tmp_path / "train.jsonl"
        records = [
            {"instruction": "What is SCBE?", "response": "A governance framework"},
            {"instruction": "What are Sacred Tongues?", "response": "Six languages"},
        ]
        with open(jsonl_file, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        indexer = KnowledgeIndexer()
        count = indexer.add_jsonl(str(jsonl_file))
        assert count >= 2

    def test_add_directory(self, tmp_path):
        # Create some files
        (tmp_path / "a.md").write_text("Authority control command")
        (tmp_path / "b.md").write_text("Security protection secrets")
        (tmp_path / "c.txt").write_text("Random text")
        (tmp_path / "d.py").write_text("def compute(): pass")

        indexer = KnowledgeIndexer()
        count = indexer.add_directory(str(tmp_path))
        assert count >= 3  # .md, .txt, .py

    def test_stats_before_build(self):
        indexer = KnowledgeIndexer()
        indexer.add_text("Test document")
        stats = indexer.stats()
        assert stats["total_documents"] >= 1
        assert stats["built"] is False

    def test_build_creates_indices(self):
        indexer = KnowledgeIndexer()
        indexer.add_text("The governance framework controls authority")
        indexer.add_text("Security encryption cipher algorithm protection")
        indexer.add_text("Transport messaging route delivery connection")
        indexer.build()
        assert indexer.is_built
        assert indexer.faiss_index is not None
        assert indexer.bm25_index is not None

    def test_stats_after_build(self):
        indexer = KnowledgeIndexer()
        indexer.add_text("Test document about governance")
        indexer.build()
        stats = indexer.stats()
        assert stats["built"] is True
        assert stats["has_faiss"] is True
        assert stats["has_bm25"] is True


# ── Searcher Tests ───────────────────────────────────────────────────────

def _build_test_indexer() -> KnowledgeIndexer:
    """Create a small test indexer with diverse documents."""
    indexer = KnowledgeIndexer()
    docs = [
        ("The governance framework enforces authority and control over all agents", "governance", "/gov"),
        ("Security encryption uses cipher algorithms for hash protection", "crypto", "/crypto"),
        ("Transport messaging routes deliver connections across networks", "network", "/net"),
        ("Schema authentication verifies identity credentials and signs tokens", "auth", "/auth"),
        ("Policy constraints define rules, laws, and boundaries for behavior", "rules", "/rules"),
        ("Hidden stealth operations protect shadow security protocols", "stealth", "/stealth"),
        ("Python programming language for data science and machine learning", "coding", "/coding"),
        ("The Sacred Tongues are KO AV RU CA UM DR in the SCBE system", "scbe", "/scbe"),
        ("Poincare ball model for hyperbolic geometry in AI safety", "math", "/math"),
        ("Training data pipeline for fine-tuning language models with SFT pairs", "training", "/train"),
    ]
    for text, title, path in docs:
        indexer.add_text(text, title=title, source_path=path)
    indexer.build()
    return indexer


class TestHybridSearcher:
    def test_search_returns_results(self):
        indexer = _build_test_indexer()
        searcher = HybridSearcher(indexer)
        results = searcher.search("governance authority")
        assert len(results) > 0
        assert isinstance(results[0], SearchResult)

    def test_search_relevance(self):
        indexer = _build_test_indexer()
        searcher = HybridSearcher(indexer)
        results = searcher.search("governance authority control")
        # Top result should be about governance
        assert "governance" in results[0].document.text.lower() or "authority" in results[0].document.text.lower()

    def test_search_top_k(self):
        indexer = _build_test_indexer()
        searcher = HybridSearcher(indexer)
        results = searcher.search("security", top_k=3)
        assert len(results) <= 3

    def test_semantic_search(self):
        indexer = _build_test_indexer()
        searcher = HybridSearcher(indexer)
        results = searcher.search_semantic("encryption and cipher")
        assert len(results) > 0

    def test_keyword_search(self):
        indexer = _build_test_indexer()
        searcher = HybridSearcher(indexer)
        results = searcher.search_keyword("governance")
        assert len(results) > 0

    def test_tongue_filter(self):
        indexer = _build_test_indexer()
        searcher = HybridSearcher(indexer)
        results = searcher.search_by_tongue("security", "UM")
        for r in results:
            assert r.document.tongue == "UM"

    def test_doc_type_filter(self):
        indexer = _build_test_indexer()
        searcher = HybridSearcher(indexer)
        results = searcher.search("test", doc_type_filter="text")
        for r in results:
            assert r.document.doc_type == "text"

    def test_find_similar(self):
        indexer = _build_test_indexer()
        searcher = HybridSearcher(indexer)
        # Find docs similar to the first one
        similar = searcher.find_similar(0, top_k=3)
        assert len(similar) > 0
        # Should return different documents (by text content)
        source_text = indexer.documents[0].text
        for r in similar:
            assert r.document.text != source_text

    def test_empty_query(self):
        indexer = _build_test_indexer()
        searcher = HybridSearcher(indexer)
        results = searcher.search("")
        # Should handle gracefully (may return empty or all docs)
        assert isinstance(results, list)

    def test_scores_are_positive(self):
        indexer = _build_test_indexer()
        searcher = HybridSearcher(indexer)
        results = searcher.search("governance security")
        for r in results:
            assert r.score > 0


# ── API Tests ────────────────────────────────────────────────────────────

class TestAPI:
    def test_create_app(self):
        from src.polly_pivot.api import create_app
        app = create_app()
        assert app is not None
        assert app.title == "PollyPivot Knowledge Router"

    def test_create_app_with_indexer(self):
        from src.polly_pivot.api import create_app
        indexer = _build_test_indexer()
        app = create_app(indexer)
        assert app is not None


# ── Integration Tests ────────────────────────────────────────────────────

class TestIntegration:
    def test_full_pipeline(self, tmp_path):
        """Full pipeline: add files → build → search → verify results."""
        # Create test files
        (tmp_path / "governance.md").write_text(
            "# Governance\n\nThe SCBE governance framework enforces authority "
            "and control over all AI agents using harmonic cost scaling."
        )
        (tmp_path / "crypto.md").write_text(
            "# Cryptography\n\nPost-quantum cryptography uses ML-KEM-768 "
            "and ML-DSA-65 for key exchange and digital signatures."
        )
        (tmp_path / "tongues.md").write_text(
            "# Sacred Tongues\n\nThe six Sacred Tongues KO AV RU CA UM DR "
            "form the basis of the Langues Metric System."
        )

        # Index
        indexer = KnowledgeIndexer()
        count = indexer.add_directory(str(tmp_path), extensions=[".md"])
        assert count >= 3

        # Build
        indexer.build()
        assert indexer.is_built

        # Search
        searcher = HybridSearcher(indexer)
        results = searcher.search("post-quantum cryptography key exchange")
        assert len(results) > 0
        # Top result should be about crypto
        assert "crypt" in results[0].document.text.lower()

    def test_jsonl_pipeline(self, tmp_path):
        """Pipeline with JSONL training data."""
        jsonl = tmp_path / "sft.jsonl"
        records = [
            {"instruction": "Explain SCBE governance", "response": "SCBE uses harmonic cost scaling"},
            {"instruction": "What is a Sacred Tongue?", "response": "One of six base languages: KO AV RU CA UM DR"},
            {"instruction": "How does drift detection work?", "response": "Using Poincare ball hyperbolic distance"},
        ]
        with open(jsonl, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        indexer = KnowledgeIndexer()
        indexer.add_jsonl(str(jsonl))
        indexer.build()

        searcher = HybridSearcher(indexer)
        results = searcher.search("Sacred Tongue language")
        assert len(results) > 0
