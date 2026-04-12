---
title: "AetherSearch — SCBE-Native Search Engine Architecture"
date: 2026-04-05
tags: [architecture, search, product, mesh-foundry, aethersearch]
status: planning
tongue_profile: [CA, DR, RU]
concept_id: aethersearch
---

# AetherSearch — Governed Geometric Search

## Vision

A search engine where relevance is measured by geometric distance on a polyhedral manifold, not keyword frequency. Every query routes through the 14-layer governance pipeline. Results that are semantically adversarial cost exponentially more to surface.

## Why This Is Different

Standard search: `query string -> tokenize -> TF-IDF/BM25 -> rank by score -> return`
AetherSearch: `query string -> tongue profile -> polyhedral coordinate -> harmonic wall distance -> governance filter -> rank by friction -> return`

| Capability | Algolia / Meili / Typesense | AetherSearch |
|------------|----------------------------|--------------|
| Tokenizer | BPE / word-level NLP | Sacred Tongues (6D phi-weighted) |
| Relevance | TF-IDF / BM25 / vector cosine | Polyhedral friction (198 dimensions) |
| Ranking | Keyword match + embedding similarity | Harmonic wall: R^((phi*d*)^2) |
| Semantic depth | Flat embedding vectors | 47D complex manifold (pairs + triples + self-imaginary) |
| Governance | None (or basic rules) | 14-layer pipeline: ALLOW / QUARANTINE / ESCALATE / DENY |
| Typo tolerance | Edit distance | Tongue affinity (typos on same tongue cluster = closer) |
| Cross-modal | Text only (or basic vector) | Text + audio + color (gallery chromatics + spectrogram bridge) |
| Trust scoring | None | Hyperbolic distance from origin = safety score |

## Open Source Inspiration

### Meilisearch (Rust) — github.com/meilisearch/meilisearch
- Engine: `milli` crate (inverted index + vector index)
- Storage: LMDB (memory-mapped B-tree)
- Tokenizer: `Charabia` (multilingual)
- API: actix-web REST
- Indexing: parallel extraction pipeline from JSON/CSV/NDJSON
- **What to learn:** LMDB storage layer, parallel indexing architecture, REST API patterns

### Typesense (C++) — github.com/typesense/typesense
- Engine: Custom ADI tree (prefix-based ranking, no traditional inverted index)
- Embeddings: ONNX Runtime + sentencepiece
- Clustering: Raft consensus
- Single binary, zero runtime deps
- **What to learn:** ADI tree structure, ONNX embedding integration, Raft for distributed search

## Architecture — Three Phases

### Phase 1: Meilisearch + SCBE Enrichment (NOW)

Use Meilisearch as the runtime search engine. SCBE quantum bundle enriches every document before indexing.

```
Document (raw text)
    |
    v
[SCBE Quantum Bundle] --> tongue_profile[6], friction_vector[198],
                          color_field (24 CIELAB points),
                          harmonic_distance, governance_tier
    |
    v
[Meilisearch Index]
    - text fields (standard search)
    - tongue_profile as filterable attributes
    - friction_magnitude as sortable attribute
    - governance_tier as filterable attribute
    |
    v
[Search Query]
    - standard text search via Meilisearch
    - post-filter by tongue affinity
    - sort by geometric distance
    - exclude QUARANTINE/DENY results
```

**Install:**
```bash
# Meilisearch
curl -L https://install.meilisearch.com | sh
./meilisearch --master-key="your-key"

# Python client
pip install meilisearch
```

**Index enriched documents:**
```python
import meilisearch
from src.crypto.quantum_frequency_bundle import generate_quantum_bundle

client = meilisearch.Client('http://127.0.0.1:7700', 'your-key')
index = client.index('scbe_docs')

# Enrich and index
for doc in documents:
    bundle = generate_quantum_bundle(doc['text'])
    enriched = {
        'id': doc['id'],
        'text': doc['text'],
        'tongue_dominant': bundle.qho.dominant_tongue,
        'tongue_ko': bundle.qho.states['ko'].coefficient,
        'tongue_av': bundle.qho.states['av'].coefficient,
        'tongue_ru': bundle.qho.states['ru'].coefficient,
        'tongue_ca': bundle.qho.states['ca'].coefficient,
        'tongue_um': bundle.qho.states['um'].coefficient,
        'tongue_dr': bundle.qho.states['dr'].coefficient,
        'friction_magnitude': sum(bundle.friction_vector) if hasattr(bundle, 'friction_vector') else 0,
        'harmonic_distance': bundle.qho.mean_excitation,
        'color_coherence': bundle.color_field.cross_eye_coherence,
        'governance_tier': 'ALLOW',  # from L13 decision
    }
    index.add_documents([enriched])
```

### Phase 2: SCBE-Native Index (Rust)

Replace Meilisearch internals with SCBE-native components:

1. **Replace Charabia with Sacred Tongues tokenizer** (already exists in `src/tokenizer/`)
   - Every token gets a 6D tongue coordinate, not just a term ID
   - Indexing stores tongue vectors alongside term positions

2. **Replace BM25 with harmonic wall scoring**
   - Distance = R^((phi * d*)^2) where d* is polyhedral distance between query and document
   - Near-safe documents are cheap; adversarial documents cost exponentially more

3. **Replace flat vector search with polyhedral friction search**
   - 198-dimensional friction vectors replace 768/1536-dim embedding vectors
   - Geometric constraints naturally cluster semantically related content
   - Boundary crossings = high signal (most informative results)

4. **Add governance layer to search results**
   - Every result passes through L13 risk decision
   - QUARANTINE results shown with warning
   - DENY results excluded entirely
   - ESCALATE results flagged for human review

5. **Cross-modal search**
   - Query text, get audio parameters (via gallery sonifier)
   - Query audio, get text matches (via spectrogram bridge)
   - Color field alignment scores as relevance signal

### Phase 3: AetherSearch Product

- Mesh Foundry customers get governed search as a service
- API-compatible with Algolia/Meilisearch (drop-in replacement)
- Differentiator: search that understands INTENT (tongue routing), not just KEYWORDS
- Pricing: usage-based like Algolia, but governance is the premium feature

## Existing SCBE Components to Wire In

| Component | File | Role in AetherSearch |
|-----------|------|---------------------|
| Quantum bundle | `src/crypto/quantum_frequency_bundle.py` | Document enrichment |
| Tongue tokenizer | `src/tokenizer/` | Query + document tokenization |
| Gallery chromatics | `src/crypto/gallery_chromatics.py` | Color-based relevance |
| Spectrogram bridge | `src/audio/spectrogram_bridge.py` | Audio cross-modal search |
| Polyhedral flow | `src/symphonic_cipher/scbe_aethermoore/polyhedral_flow.py` | Friction scoring |
| Harmonic scaling | `src/symphonic_cipher/scbe_aethermoore/harmonic_scaling_law.py` | Distance cost |
| Governance | `src/governance/` | Result filtering |
| Speech render | `src/crypto/speech_render_plan.py` | Voice search results |

## Revenue Model

1. **Free tier:** 10K searches/month (matches Algolia, attracts developers)
2. **Pro:** Governed search with 14-layer pipeline, tongue analytics
3. **Enterprise:** Custom tongue training, cross-modal, dedicated infrastructure
4. **API licensing:** Other companies embed AetherSearch governance in their search

## Competition

| Player | What they lack |
|--------|---------------|
| Algolia | No governance, no geometric ranking, closed source |
| Elasticsearch | Complex ops, no governance, standard NLP |
| Meilisearch | No governance, standard tokenizer, no cross-modal |
| Typesense | No governance, no semantic geometry |
| Pinecone/Weaviate | Vector-only, no polyhedral structure, no governance |
| **AetherSearch** | Governed, geometric, cross-modal, tongue-aware |
