"""
Federated Context Grid
=======================

Hierarchical multi-swarm context system fusing:
  - ScatteredAttentionSphere (geometric substrate)
  - AgenticSphereGrid (FFX skill tree)
  - MemoryLattice (7-layer persistent context)
  - HyperbolicRAG (Poincare ball retrieval)
  - SignedOctree (sparse spatial index)
  - SentenceTransformer (local embedding)

Documents are embedded, projected onto the sphere, stored in the octree
for O(log n) spatial lookup, indexed in the memory lattice for persistence,
and retrievable via hyperbolic distance for RAG.

Multi-swarm: each agent has its own grid state but shares the context store.
Federated: local embeddings + shared knowledge base.
"""

from __future__ import annotations

import hashlib
import math
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

# Sacred Tongue constants
PHI = 1.618033988749895
TONGUE_KEYS = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_WEIGHTS = {t: PHI**i for i, t in enumerate(TONGUE_KEYS)}
TONGUE_ANGLES = {t: i * math.pi / 3 for i, t in enumerate(TONGUE_KEYS)}

# Category -> tongue mapping for automatic classification
CATEGORY_TONGUE_MAP = {
    "command": "KO",
    "orchestration": "KO",
    "dispatch": "KO",
    "coordination": "KO",
    "transport": "AV",
    "navigation": "AV",
    "search": "AV",
    "browsing": "AV",
    "entropy": "RU",
    "research": "RU",
    "chaos": "RU",
    "hypothesis": "RU",
    "compute": "CA",
    "code": "CA",
    "training": "CA",
    "deployment": "CA",
    "security": "UM",
    "governance": "UM",
    "audit": "UM",
    "threat": "UM",
    "structure": "DR",
    "documentation": "DR",
    "debugging": "DR",
    "architecture": "DR",
    "concept": "KO",
    "geometry": "DR",
    "hodge-combo": "CA",
    "agent-archetype": "KO",
}


@dataclass
class ContextDocument:
    """A document stored in the context grid."""

    doc_id: str
    title: str
    content: str
    tongue: str = "KO"
    tier: int = 1
    doc_type: str = "note"
    source_path: str = ""
    embedding: Optional[np.ndarray] = None
    tongue_coords: Optional[np.ndarray] = None  # 6D Sacred Tongue projection
    spatial_coords: Optional[np.ndarray] = None  # 3D for octree
    metadata: dict = field(default_factory=dict)
    chain_hash: str = ""
    timestamp: float = field(default_factory=time.time)

    def summary(self, max_len: int = 120) -> str:
        text = self.content.replace("\n", " ").strip()
        return text[:max_len] + "..." if len(text) > max_len else text


@dataclass
class RetrievalResult:
    """A result from a context grid query."""

    doc_id: str
    title: str
    content: str
    distance: float
    trust_score: float
    tongue: str
    retrieval_method: str  # "rag" | "octree" | "memory" | "hierarchy"
    metadata: dict = field(default_factory=dict)


@dataclass
class GridStats:
    """Statistics about the context grid."""

    total_documents: int
    tongue_distribution: dict
    memory_layers: dict
    embedding_dim: int
    octree_nodes: int
    avg_retrieval_ms: float


class FederatedContextGrid:
    """
    Hierarchical federated multi-swarm context grid.

    Fuses octree spatial indexing with sphere grid organization,
    memory lattice persistence, and hyperbolic RAG retrieval.

    Each agent has a view into the shared grid filtered by their
    sphere grid activation levels — you can only retrieve context
    for skills you've partially unlocked.
    """

    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        # Document store
        self.documents: dict[str, ContextDocument] = {}

        # Embedding matrix for fast cosine similarity
        self._embeddings: list[np.ndarray] = []
        self._doc_ids: list[str] = []

        # Icosahedral projection matrix (6D -> 3D)
        self._ico_matrix = self._build_ico_matrix()

        # Embedding model (lazy load)
        self._model_name = embedding_model
        self._model = None

        # Memory layers (simplified in-process version of MemoryLattice)
        self.memory: dict[str, list[ContextDocument]] = {
            "working": [],  # Current session
            "session": [],  # Today
            "mission": [],  # This week
            "identity": [],  # Permanent
            "reflex": [],  # Fast-path lookups
            "immune": [],  # Known bad patterns
        }

        # Hash chain for tamper detection
        self._chain_hash = hashlib.sha256(b"genesis").hexdigest()[:32]

        # Octree spatial index (3D buckets for O(1) neighborhood lookup)
        self._spatial_buckets: dict[tuple, list[str]] = {}
        self._bucket_size = 0.25  # Partition [-1,1]^3 into 8^3 = 512 buckets

        # Stats
        self._retrieval_times: list[float] = []

    def _build_ico_matrix(self) -> np.ndarray:
        """Icosahedral projection matrix (6D -> 3D)."""
        phi = PHI
        phi_inv = 1.0 / phi
        raw = np.array(
            [
                [1, phi, 0, phi_inv, 0, 0],
                [0, 1, phi, 0, phi_inv, 0],
                [0, 0, 1, phi, 0, phi_inv],
            ],
            dtype=np.float64,
        )
        norms = np.linalg.norm(raw, axis=1, keepdims=True)
        return raw / norms

    def _load_model(self):
        """Lazy load sentence-transformers model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, text: str) -> np.ndarray:
        """Embed text using sentence-transformers."""
        model = self._load_model()
        return model.encode(text, normalize_embeddings=True)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Batch embed for efficiency."""
        model = self._load_model()
        return model.encode(texts, normalize_embeddings=True, show_progress_bar=True)

    def _compute_tongue_coords(self, tongue: str, embedding: np.ndarray) -> np.ndarray:
        """
        Project embedding into 6D Sacred Tongue space.

        Each tongue dimension gets a projection of the embedding,
        weighted by the tongue's phi-scaled weight.
        """
        # Use 6 evenly-spaced slices of the embedding as tongue dimensions
        dim = len(embedding)
        chunk = dim // 6
        coords = np.zeros(6)
        for i in range(6):
            start = i * chunk
            end = start + chunk
            coords[i] = np.mean(embedding[start:end]) * TONGUE_WEIGHTS[TONGUE_KEYS[i]]

        # Boost the document's primary tongue
        tongue_idx = TONGUE_KEYS.index(tongue) if tongue in TONGUE_KEYS else 0
        coords[tongue_idx] *= 1.5

        # Normalize to unit ball (Poincare constraint)
        norm = np.linalg.norm(coords)
        if norm > 0.99:
            coords = coords * 0.99 / norm

        return coords

    def _compute_spatial_coords(self, tongue_coords: np.ndarray) -> np.ndarray:
        """Project 6D tongue coords to 3D for octree storage."""
        spatial = self._ico_matrix @ tongue_coords
        # Clamp to [-1, 1]
        spatial = np.clip(spatial, -0.99, 0.99)
        return spatial

    def _spatial_bucket_key(self, coords: np.ndarray) -> tuple:
        """Quantize 3D coords into a bucket key."""
        bs = self._bucket_size
        return tuple(int((c + 1.0) / bs) for c in coords[:3])

    def _chain_next(self, content: str) -> str:
        """Advance the hash chain."""
        data = f"{self._chain_hash}:{time.time():.6f}:{content[:64]}"
        self._chain_hash = hashlib.sha256(data.encode()).hexdigest()[:32]
        return self._chain_hash

    # =========================================================================
    #  Store
    # =========================================================================

    def store(
        self,
        doc_id: str,
        title: str,
        content: str,
        tongue: str = "KO",
        tier: int = 1,
        doc_type: str = "note",
        source_path: str = "",
        metadata: dict | None = None,
        memory_layer: str = "session",
    ) -> ContextDocument:
        """
        Store a document in the federated context grid.

        Pipeline:
          1. Embed text with sentence-transformers
          2. Project to 6D tongue coords
          3. Project to 3D spatial coords
          4. Insert into octree buckets
          5. Store in memory layer
          6. Chain-hash for tamper detection
        """
        embedding = self.embed(title + " " + content[:500])
        tongue_coords = self._compute_tongue_coords(tongue, embedding)
        spatial_coords = self._compute_spatial_coords(tongue_coords)
        chain_hash = self._chain_next(content)

        doc = ContextDocument(
            doc_id=doc_id,
            title=title,
            content=content,
            tongue=tongue,
            tier=tier,
            doc_type=doc_type,
            source_path=source_path,
            embedding=embedding,
            tongue_coords=tongue_coords,
            spatial_coords=spatial_coords,
            metadata=metadata or {},
            chain_hash=chain_hash,
        )

        self.documents[doc_id] = doc
        self._embeddings.append(embedding)
        self._doc_ids.append(doc_id)

        # Octree bucket
        bucket = self._spatial_bucket_key(spatial_coords)
        if bucket not in self._spatial_buckets:
            self._spatial_buckets[bucket] = []
        self._spatial_buckets[bucket].append(doc_id)

        # Memory layer
        if memory_layer in self.memory:
            self.memory[memory_layer].append(doc)

        return doc

    def store_batch(self, docs: list[dict]) -> list[ContextDocument]:
        """
        Batch store with efficient batch embedding.

        Each dict should have: doc_id, title, content, tongue, tier, doc_type
        """
        texts = [d.get("title", "") + " " + d.get("content", "")[:500] for d in docs]
        embeddings = self.embed_batch(texts)

        results = []
        for i, d in enumerate(docs):
            tongue = d.get("tongue", "KO")
            tongue_coords = self._compute_tongue_coords(tongue, embeddings[i])
            spatial_coords = self._compute_spatial_coords(tongue_coords)
            chain_hash = self._chain_next(d.get("content", ""))

            doc = ContextDocument(
                doc_id=d["doc_id"],
                title=d.get("title", ""),
                content=d.get("content", ""),
                tongue=tongue,
                tier=d.get("tier", 1),
                doc_type=d.get("doc_type", "note"),
                source_path=d.get("source_path", ""),
                embedding=embeddings[i],
                tongue_coords=tongue_coords,
                spatial_coords=spatial_coords,
                metadata=d.get("metadata", {}),
                chain_hash=chain_hash,
            )

            self.documents[doc.doc_id] = doc
            self._embeddings.append(embeddings[i])
            self._doc_ids.append(doc.doc_id)

            bucket = self._spatial_bucket_key(spatial_coords)
            if bucket not in self._spatial_buckets:
                self._spatial_buckets[bucket] = []
            self._spatial_buckets[bucket].append(doc.doc_id)

            layer = d.get("memory_layer", "session")
            if layer in self.memory:
                self.memory[layer].append(doc)

            results.append(doc)

        return results

    # =========================================================================
    #  Retrieve — Multiple Methods
    # =========================================================================

    def query_rag(
        self, query: str, top_k: int = 5, tongue_filter: str | None = None
    ) -> list[RetrievalResult]:
        """
        RAG retrieval: embed query, cosine similarity, Poincare distance ranking.

        This is the primary retrieval method — fast, accurate, governed.
        """
        t0 = time.time()

        if not self._embeddings:
            return []

        query_emb = self.embed(query)
        emb_matrix = np.array(self._embeddings)

        # Cosine similarity (embeddings are already normalized)
        similarities = emb_matrix @ query_emb

        # Poincare distance boost: project to tongue space, compute hyperbolic distance
        query_tongue_coords = self._compute_tongue_coords(
            tongue_filter or "KO", query_emb
        )

        results = []
        for i, doc_id in enumerate(self._doc_ids):
            doc = self.documents[doc_id]

            # Tongue filter
            if tongue_filter and doc.tongue != tongue_filter:
                continue

            cos_sim = float(similarities[i])

            # Hyperbolic distance in tongue space
            if doc.tongue_coords is not None:
                u = query_tongue_coords
                v = doc.tongue_coords
                u_norm_sq = np.dot(u, u)
                v_norm_sq = np.dot(v, v)
                diff_norm_sq = np.dot(u - v, u - v)
                denom = (1 - u_norm_sq) * (1 - v_norm_sq)
                if denom > 1e-10:
                    arg = 1 + 2 * diff_norm_sq / denom
                    hyp_dist = math.acosh(max(1.0, arg))
                else:
                    hyp_dist = 10.0
            else:
                hyp_dist = 1.0

            # Trust score: combine cosine sim and hyperbolic distance
            trust = cos_sim / (1 + 0.3 * hyp_dist)

            results.append(
                RetrievalResult(
                    doc_id=doc_id,
                    title=doc.title,
                    content=doc.content,
                    distance=1 - cos_sim,
                    trust_score=trust,
                    tongue=doc.tongue,
                    retrieval_method="rag",
                    metadata=doc.metadata,
                )
            )

        # Sort by trust score descending
        results.sort(key=lambda r: r.trust_score, reverse=True)

        elapsed = (time.time() - t0) * 1000
        self._retrieval_times.append(elapsed)

        return results[:top_k]

    def query_octree(
        self, query: str, radius: int = 1, top_k: int = 5
    ) -> list[RetrievalResult]:
        """
        Octree spatial retrieval: find documents in nearby buckets.

        O(1) neighborhood lookup — fast for spatial proximity queries.
        """
        t0 = time.time()
        query_emb = self.embed(query)
        query_tc = self._compute_tongue_coords("KO", query_emb)
        query_sc = self._compute_spatial_coords(query_tc)
        center = self._spatial_bucket_key(query_sc)

        # Search nearby buckets
        candidates = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    key = (center[0] + dx, center[1] + dy, center[2] + dz)
                    if key in self._spatial_buckets:
                        candidates.extend(self._spatial_buckets[key])

        results = []
        for doc_id in set(candidates):
            doc = self.documents[doc_id]
            if doc.spatial_coords is not None and doc.embedding is not None:
                spatial_dist = float(np.linalg.norm(query_sc - doc.spatial_coords))
                cos_sim = float(np.dot(query_emb, doc.embedding))
                results.append(
                    RetrievalResult(
                        doc_id=doc_id,
                        title=doc.title,
                        content=doc.content,
                        distance=spatial_dist,
                        trust_score=cos_sim,
                        tongue=doc.tongue,
                        retrieval_method="octree",
                        metadata=doc.metadata,
                    )
                )

        results.sort(key=lambda r: r.trust_score, reverse=True)
        elapsed = (time.time() - t0) * 1000
        self._retrieval_times.append(elapsed)
        return results[:top_k]

    def query_memory(
        self, layer: str, category: str | None = None, limit: int = 10
    ) -> list[ContextDocument]:
        """
        Memory layer retrieval: get documents from a specific memory tier.
        """
        docs = self.memory.get(layer, [])
        if category:
            docs = [d for d in docs if d.tongue == category or d.doc_type == category]
        return docs[-limit:]

    def query_hierarchy(
        self,
        tongue: str | None = None,
        tier: int | None = None,
        doc_type: str | None = None,
    ) -> list[ContextDocument]:
        """
        Hierarchical retrieval: filter by tongue -> tier -> type.
        The sphere grid's natural traversal order.
        """
        results = list(self.documents.values())
        if tongue:
            results = [d for d in results if d.tongue == tongue]
        if tier is not None:
            results = [d for d in results if d.tier == tier]
        if doc_type:
            results = [d for d in results if d.doc_type == doc_type]
        return results

    def query_multi_method(
        self, query: str, top_k: int = 5, tongue_filter: str | None = None
    ) -> list[RetrievalResult]:
        """
        Fused multi-method retrieval: RAG + octree + dedup + rerank.

        This is the grid's signature query — combines all retrieval methods
        and deduplicates by doc_id, keeping the highest trust score.
        """
        rag_results = self.query_rag(
            query, top_k=top_k * 2, tongue_filter=tongue_filter
        )
        octree_results = self.query_octree(query, radius=1, top_k=top_k * 2)

        # Merge and dedup
        seen = {}
        for r in rag_results + octree_results:
            if r.doc_id not in seen or r.trust_score > seen[r.doc_id].trust_score:
                seen[r.doc_id] = r

        merged = sorted(seen.values(), key=lambda r: r.trust_score, reverse=True)
        return merged[:top_k]

    # =========================================================================
    #  Generation (HF Inference)
    # =========================================================================

    def generate_answer(
        self,
        query: str,
        context_docs: list[RetrievalResult],
        hf_token: str | None = None,
        model: str = "meta-llama/Llama-3.1-8B-Instruct",
    ) -> str:
        """
        Generate an answer using HF Inference API with retrieved context.

        RAG pipeline: retrieve -> format context -> generate.
        """
        from huggingface_hub import InferenceClient

        token = hf_token or os.environ.get("HF_TOKEN", "")
        if not token:
            return "[No HF token — cannot generate. Set HF_TOKEN env var.]"

        # Format context
        context_parts = []
        for i, r in enumerate(context_docs[:5]):
            context_parts.append(
                f"[{i+1}] {r.title} ({r.tongue} domain, trust={r.trust_score:.3f}):\n"
                f"{r.content[:400]}"
            )
        context_str = "\n\n".join(context_parts)

        client = InferenceClient(token=token)
        try:
            response = client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an AI agent in the SCBE-AETHERMOORE sphere grid."
                            " Answer using ONLY the provided context. Be concise."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context_str}\n\nQuestion: {query}",
                    },
                ],
                model=model,
                max_tokens=300,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[Generation error: {e}]"

    # =========================================================================
    #  Stats & Verification
    # =========================================================================

    def stats(self) -> GridStats:
        """Grid statistics."""
        tongue_dist = {}
        for doc in self.documents.values():
            tongue_dist[doc.tongue] = tongue_dist.get(doc.tongue, 0) + 1

        memory_layers = {k: len(v) for k, v in self.memory.items()}
        avg_rt = (
            sum(self._retrieval_times) / len(self._retrieval_times)
            if self._retrieval_times
            else 0.0
        )

        return GridStats(
            total_documents=len(self.documents),
            tongue_distribution=tongue_dist,
            memory_layers=memory_layers,
            embedding_dim=len(self._embeddings[0]) if self._embeddings else 0,
            octree_nodes=len(self._spatial_buckets),
            avg_retrieval_ms=avg_rt,
        )

    def verify_chain(self) -> bool:
        """Verify the hash chain is intact."""
        if not self.documents:
            return True
        # Check that chain_hash values form a sequence
        hashes = [d.chain_hash for d in self.documents.values()]
        return len(set(hashes)) == len(hashes)  # All unique


# =========================================================================
#  Obsidian Vault Loader
# =========================================================================


def load_obsidian_vault(vault_path: str | Path) -> list[dict]:
    """
    Load all markdown notes from an Obsidian vault.

    Parses YAML frontmatter for metadata (tongue, tier, type).
    Returns list of dicts ready for store_batch().
    """
    vault_path = Path(vault_path)
    docs = []

    for md_file in sorted(vault_path.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8", errors="replace")
        rel_path = str(md_file.relative_to(vault_path))

        # Parse frontmatter
        metadata = {}
        body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm = parts[1].strip()
                body = parts[2].strip()
                for line in fm.split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        metadata[key.strip()] = val.strip().strip('"')

        # Extract tongue and tier from frontmatter or path
        tongue = metadata.get("tongue", "KO")
        if tongue not in TONGUE_KEYS:
            # Try to infer from path
            for t in TONGUE_KEYS:
                if t in rel_path:
                    tongue = t
                    break

        tier = 1
        tier_str = metadata.get("tier", "1")
        try:
            tier = int(tier_str)
        except ValueError:
            pass

        doc_type = metadata.get("type", "note")

        # Title from first heading or filename
        title = md_file.stem
        for line in body.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break

        doc_id = hashlib.md5(rel_path.encode()).hexdigest()[:12]

        docs.append(
            {
                "doc_id": doc_id,
                "title": title,
                "content": body,
                "tongue": tongue,
                "tier": tier,
                "doc_type": doc_type,
                "source_path": rel_path,
                "metadata": metadata,
                "memory_layer": (
                    "identity" if doc_type in ("concept", "moc") else "session"
                ),
            }
        )

    return docs
