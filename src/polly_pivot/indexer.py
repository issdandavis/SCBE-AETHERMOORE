"""
PollyPivot Indexer — Builds FAISS + BM25 indices from documents
===============================================================

Indexes text documents from multiple sources:
  - Obsidian vault markdown files
  - Training JSONL files
  - Python/TypeScript source code
  - Plain text files

Uses sentence-transformers (all-MiniLM-L6-v2, 384-dim) for semantic
embeddings and rank_bm25 for keyword search.

@layer L3
@component PollyPivot.Indexer
"""

from __future__ import annotations

import json
import hashlib
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import faiss
except ImportError:
    faiss = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None


MODEL_NAME = "all-MiniLM-L6-v2"
EMBED_DIM = 384
MAX_CHUNK_CHARS = 1500
OVERLAP_CHARS = 200


@dataclass
class Document:
    """A single indexed document chunk."""
    doc_id: str
    source_path: str
    title: str
    text: str
    tongue: str = ""        # Sacred Tongue affinity (if known)
    doc_type: str = "text"  # text, code, training, markdown
    chunk_index: int = 0
    metadata: Dict = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None

    def content_hash(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS, overlap: int = OVERLAP_CHARS) -> List[str]:
    """Split text into overlapping chunks."""
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks


def _detect_tongue(text: str) -> str:
    """Simple Sacred Tongue classification from keywords."""
    text_lower = text.lower()
    scores = {
        "KO": sum(1 for w in ["authority", "control", "command", "enforce", "govern", "rule"] if w in text_lower),
        "AV": sum(1 for w in ["transport", "message", "route", "deliver", "send", "connect"] if w in text_lower),
        "RU": sum(1 for w in ["policy", "constraint", "rule", "law", "limit", "boundary"] if w in text_lower),
        "CA": sum(1 for w in ["compute", "encrypt", "cipher", "algorithm", "hash", "key"] if w in text_lower),
        "UM": sum(1 for w in ["security", "secret", "hidden", "stealth", "shadow", "protect"] if w in text_lower),
        "DR": sum(1 for w in ["schema", "auth", "identity", "verify", "credential", "sign"] if w in text_lower),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else ""


class KnowledgeIndexer:
    """Builds and manages FAISS + BM25 indices for hybrid search.

    Usage:
        indexer = KnowledgeIndexer()
        indexer.add_directory("/path/to/obsidian/vault", doc_type="markdown")
        indexer.add_jsonl("/path/to/training.jsonl")
        indexer.build()  # builds FAISS index + BM25

        # Now use with HybridSearcher
    """

    def __init__(self, model_name: str = MODEL_NAME, embed_dim: int = EMBED_DIM):
        self.model_name = model_name
        self.embed_dim = embed_dim
        self._model: Optional[object] = None
        self.documents: List[Document] = []
        self.faiss_index: Optional[object] = None
        self.bm25_index: Optional[object] = None
        self._embeddings: Optional[np.ndarray] = None
        self._built = False

    @property
    def model(self):
        """Lazy-load sentence transformer model."""
        if self._model is None:
            if SentenceTransformer is None:
                raise ImportError("sentence-transformers not installed")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def add_document(self, doc: Document) -> None:
        """Add a single pre-built document."""
        self.documents.append(doc)
        self._built = False

    def add_text(
        self,
        text: str,
        source_path: str = "",
        title: str = "",
        doc_type: str = "text",
        metadata: Optional[Dict] = None,
    ) -> int:
        """Add a text string, auto-chunking if needed.

        Returns:
            Number of document chunks created.
        """
        chunks = _chunk_text(text)
        tongue = _detect_tongue(text)
        count = 0
        for i, chunk in enumerate(chunks):
            doc = Document(
                doc_id=f"{hashlib.md5(source_path.encode()).hexdigest()[:8]}_{i}",
                source_path=source_path,
                title=title or os.path.basename(source_path),
                text=chunk,
                tongue=tongue,
                doc_type=doc_type,
                chunk_index=i,
                metadata=metadata or {},
            )
            self.documents.append(doc)
            count += 1
        self._built = False
        return count

    def add_file(self, path: str, doc_type: Optional[str] = None) -> int:
        """Add a single file. Auto-detects type from extension.

        Returns:
            Number of chunks created.
        """
        p = Path(path)
        if not p.exists() or not p.is_file():
            return 0

        ext = p.suffix.lower()
        if doc_type is None:
            if ext in (".md", ".markdown"):
                doc_type = "markdown"
            elif ext in (".py", ".ts", ".js", ".tsx", ".jsx"):
                doc_type = "code"
            elif ext in (".jsonl",):
                return self.add_jsonl(path)
            else:
                doc_type = "text"

        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return 0

        if not text.strip():
            return 0

        return self.add_text(
            text=text,
            source_path=str(p),
            title=p.stem,
            doc_type=doc_type,
        )

    def add_directory(
        self,
        directory: str,
        extensions: Optional[List[str]] = None,
        doc_type: Optional[str] = None,
        recursive: bool = True,
    ) -> int:
        """Add all matching files from a directory.

        Args:
            directory: Path to directory.
            extensions: File extensions to include (default: .md, .txt, .py, .ts).
            doc_type: Override document type for all files.
            recursive: Whether to recurse into subdirectories.

        Returns:
            Total number of chunks created.
        """
        if extensions is None:
            extensions = [".md", ".txt", ".py", ".ts", ".jsonl"]

        directory = Path(directory)
        if not directory.is_dir():
            return 0

        total = 0
        pattern = "**/*" if recursive else "*"
        for p in directory.glob(pattern):
            if p.is_file() and p.suffix.lower() in extensions:
                total += self.add_file(str(p), doc_type=doc_type)

        self._built = False
        return total

    def add_jsonl(self, path: str) -> int:
        """Add documents from a JSONL file (training data format).

        Expected fields: instruction, response (SFT format).

        Returns:
            Number of chunks created.
        """
        p = Path(path)
        if not p.exists():
            return 0

        count = 0
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                for line_num, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # SFT format: instruction + response
                    text_parts = []
                    if "instruction" in record:
                        text_parts.append(record["instruction"])
                    if "response" in record:
                        text_parts.append(record["response"])
                    if "text" in record:
                        text_parts.append(record["text"])
                    if "content" in record:
                        text_parts.append(record["content"])

                    text = "\n".join(text_parts)
                    if not text.strip():
                        continue

                    count += self.add_text(
                        text=text,
                        source_path=str(p),
                        title=f"{p.stem}_L{line_num}",
                        doc_type="training",
                        metadata={"line": line_num},
                    )
        except Exception:
            pass

        return count

    def build(self) -> None:
        """Build FAISS and BM25 indices from all added documents.

        This computes embeddings for all documents and builds the
        FAISS L2 index and BM25 token index.
        """
        if not self.documents:
            self._built = True
            return

        # Compute embeddings
        texts = [d.text for d in self.documents]
        embeddings = self.model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        self._embeddings = np.asarray(embeddings, dtype=np.float32)

        for i, doc in enumerate(self.documents):
            doc.embedding = self._embeddings[i]

        # Build FAISS index (inner product since embeddings are normalized)
        if faiss is not None:
            self.faiss_index = faiss.IndexFlatIP(self.embed_dim)
            self.faiss_index.add(self._embeddings)

        # Build BM25 index
        if BM25Okapi is not None:
            tokenized = [text.lower().split() for text in texts]
            self.bm25_index = BM25Okapi(tokenized)

        self._built = True

    @property
    def is_built(self) -> bool:
        return self._built

    @property
    def doc_count(self) -> int:
        return len(self.documents)

    def stats(self) -> Dict:
        """Return index statistics."""
        type_counts = {}
        tongue_counts = {}
        for doc in self.documents:
            type_counts[doc.doc_type] = type_counts.get(doc.doc_type, 0) + 1
            if doc.tongue:
                tongue_counts[doc.tongue] = tongue_counts.get(doc.tongue, 0) + 1

        return {
            "total_documents": len(self.documents),
            "built": self._built,
            "has_faiss": self.faiss_index is not None,
            "has_bm25": self.bm25_index is not None,
            "by_type": type_counts,
            "by_tongue": tongue_counts,
            "model": self.model_name,
            "embed_dim": self.embed_dim,
        }
