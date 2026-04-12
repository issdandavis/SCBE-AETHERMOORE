---
title: MemPalace SCBE Memory Augmentation
created_at: 2026-04-11
status: canonical-working-note
---

# MemPalace SCBE Memory Augmentation

## Purpose

This note defines the smallest useful integration between MemPalace-style memory and SCBE.

The goal is not to replace SCBE with another memory system and not to "beat" MemPalace. The goal is:

- keep a strong verbatim memory substrate
- use SCBE semantic tokenization and governance to rerank and filter retrieval
- measure whether that makes recall cheaper, safer, or more selective

## What MemPalace Actually Contributes

The strongest MemPalace idea is architectural, not mystical:

- store verbatim memory units
- retrieve them directly
- optionally rerank later
- do not destroy memory by summarizing too early

The repo-backed evidence for that is straightforward:

- [external_repos/mempalace/benchmarks/BENCHMARKS.md](../../../external_repos/mempalace/benchmarks/BENCHMARKS.md) reports `96.6% R@5` on LongMemEval for raw ChromaDB retrieval with no LLM in the loop.
- The same benchmark note reports `100%` for hybrid retrieval with optional LLM reranking, but it also contains its own caveats about structurally inflated settings in some LoCoMo runs.
- [external_repos/mempalace/mempalace/searcher.py](../../../external_repos/mempalace/mempalace/searcher.py) shows the core retrieval contract: query ChromaDB, return verbatim text, metadata, and distance.
- [external_repos/mempalace/mempalace/knowledge_graph.py](../../../external_repos/mempalace/mempalace/knowledge_graph.py) shows the structured sidecar graph: local SQLite, entity/triple storage, temporal validity, and links back to verbatim memory.
- [external_repos/mempalace/mempalace/README.md](../../../external_repos/mempalace/mempalace/README.md) makes the package split explicit: ChromaDB as the palace, SQLite as the knowledge graph, MCP exposing both.

The practical conclusion is:

- verbatim storage is the memory substrate
- structure is a sidecar
- reranking is optional
- memory extraction is not the first step

## What SCBE Already Has

SCBE already contains good components for a memory augmentation layer. They are just not assembled into a retrieval benchmark yet.

## Critical Tokenizer Split

There are two different tokenizer families in this repo and they should not be conflated.

### 1. Semantic atomic tokenizer

[python/scbe/atomic_tokenization.py](../../../python/scbe/atomic_tokenization.py) is a semantic projector.

It does useful work:

- classifies a raw token into a semantic class
- maps it into an atomic state
- emits a six-channel Sacred Tongue trit projection
- provides negative / dual / band / resilience / adaptivity / trust metadata

But it is not bijective. It is intentionally lossy. Multiple raw tokens can land in the same semantic class or nearby atomic signatures.

### 2. Sacred Tongues transport tokenizer

[src/crypto/sacred_tongues.py](../../../src/crypto/sacred_tongues.py) is the bijective transport tokenizer.

It does something different:

- `encode_bytes(...)` turns raw bytes into one of six tongue lexicons
- `decode_tokens(...)` reconstructs the exact original bytes
- each tongue has a 256-token byte-complete mapping

This is the correct place to talk about full bijective six-system tokenization.

### Practical consequence

The semantic tokenizer helps with meaning-bearing sidecars.

The transport tokenizer helps with reversible packetization and governed transport.

They are complementary, not interchangeable.

### 1. Semantic tokenization

[python/scbe/atomic_tokenization.py](../../../python/scbe/atomic_tokenization.py) already provides:

- semantic class assignment
- mapping from token to atomic state
- projection into the six tongue channels `KO AV RU CA UM DR`
- trust baseline and drift-scale related metadata

This is the right place to derive retrieval sidecars such as:

- tongue activation sketch
- semantic class histogram
- negative / inert / temporal flags
- compact token-state summaries

### 2. Path-dependent memory and trust

[python/scbe/history_reducer.py](../../../python/scbe/history_reducer.py) already provides:

- a `FibonacciTrustLadder`
- checkpoint memory objects
- trust-weighted reconstruction votes
- rhombic energy and score
- path-dependent reduction over token streams

This is not a storage engine, but it is a good rerank and governance surface.

### 3. Rhombic scoring

[python/scbe/rhombic_bridge.py](../../../python/scbe/rhombic_bridge.py) provides:

- `rhombic_fusion(...)`
- `rhombic_score(...)`

That is a compact scoring primitive that can sit on top of retrieval results instead of replacing retrieval.

### 4. Sacred Eggs as governed memory envelopes

[src/symphonic_cipher/scbe_aethermoore/sacred_egg_integrator.py](../../../src/symphonic_cipher/scbe_aethermoore/sacred_egg_integrator.py) and [docs/01-architecture/sacred-eggs-systems-model.md](../../../docs/01-architecture/sacred-eggs-systems-model.md) already support the right authority model:

- governed packet / envelope
- hatch conditions
- fail-to-noise behavior
- ring / context / tongue / path checks

This makes Sacred Eggs a good envelope for high-authority memory objects, not a replacement for the memory store itself.

## The Right Combined Architecture

Use MemPalace's storage pattern and SCBE's scoring/governance pattern.

### Layer A — Verbatim memory substrate

Store each memory unit in raw form:

- note chunk
- transcript turn or exchange
- Sacred Egg shell metadata
- decision packet
- training or benchmark artifact

This layer should optimize for:

- high recall
- simple indexing
- no lossy extraction up front

### Layer B — SCBE sidecar metadata

For each stored memory object, attach a sidecar derived from SCBE tokenization:

- six-tongue activation vector
- semantic class histogram
- trust baseline summary
- negative / temporal / relation flags
- optional Sacred Egg identity and hatch metadata

This layer should optimize for:

- cheap reranking
- governance-aware filtering
- auditability

### Layer C — Retrieval pipeline

1. Raw retrieval:
   - embedding search or lexical search over verbatim objects
2. SCBE rerank:
   - semantic token overlap
   - tongue coherence
   - trust weighting
   - rhombic score
   - Sacred Egg authority weighting when present
3. Optional answer synthesis:
   - only after retrieval and rerank

## Minimal Scoring Model

The first useful rerank formula does not need new geometry. It can be a weighted score:

```text
score_final
= a * score_retrieval
+ b * score_semantic_overlap
+ c * score_tongue_coherence
+ d * score_trust
+ e * score_authority
+ f * score_rhombic
```

Where:

- `score_retrieval` comes from the embedding or lexical engine
- `score_semantic_overlap` comes from atomic token state overlap
- `score_tongue_coherence` comes from six-channel similarity
- `score_trust` comes from the trust ladder or record source
- `score_authority` comes from Sacred Egg or packet authority
- `score_rhombic` comes from `rhombic_score(...)`

This is enough to test the idea before adding deeper manifold machinery.

## Current Benchmark Status

The benchmark harness lives at [scripts/system/memory_overlay_benchmark.py](../../../scripts/system/memory_overlay_benchmark.py).

As of the current run:

- smoke test: [tests/test_memory_overlay_benchmark.py](../../../tests/test_memory_overlay_benchmark.py) is green
- latest artifact: [memory_overlay_benchmark_20260411T125509Z.json](../../../artifacts/system_audit/memory_overlay_benchmark/memory_overlay_benchmark_20260411T125509Z.json)

Current seed-set metrics:

- baseline: `recall@5 = 0.8000`, `MRR = 0.8000`
- overlay: `recall@5 = 0.8000`, `MRR = 0.8000`

So the current overlay does not yet improve retrieval on the seed set.

## Why "Full Tokenization" Did Not Automatically Improve Retrieval

The short answer is: full bijective transport tokenization is not the same thing as a strong retrieval signal.

### What the harness now uses

The current rerank layer uses:

- lexical baseline score
- atomic semantic signature similarity
- aggregate six-tongue projection similarity
- Sacred Tongues transport-token overlap
- rhombic score
- small trust bonus

This is a better test than the first collapsed version because it now includes both:

- semantic atomic sidecars
- bijective Sacred Tongues transport-token counts

### Why that still stayed flat

1. The benchmark queries are natural-language semantic questions, not Sacred Tongue packet queries.
   The bijective transport tokenizer preserves exact bytes, but exact-byte preservation does not automatically create better semantic ranking for English code-and-notes retrieval.

2. The missed item is a file-identity problem, not a transport problem.
   The current failure is still the `rhombic_bridge.py` query. That is mostly a filename / path / symbol retrieval problem.

3. The harness still lacks code-aware retrieval boosts.
   It does not yet strongly score:
   - filename overlap
   - path-segment overlap
   - function/class/symbol names
   - heading/title anchors for notes

4. The semantic tokenizer is still lossy by design.
   It is useful for governance and coarse meaning, but it does not preserve raw token identity strongly enough to replace direct code-aware retrieval features.

### What this means

The flat result does not falsify the tokenizer architecture.

It means:

- the memory benchmark now tests more of the real tokenizer stack
- the transport-bijective layer alone is not enough to improve semantic retrieval
- the next missing layer is code- and note-identity features, not more abstract geometry

## Next Retrieval Upgrade

Before making a judgment on the memory-overlay thesis, the harness should add:

- filename token boosts
- path token boosts
- symbol/function/class extraction and boosts
- heading/title boosts for notes
- optional exact phrase match features

That will test the right thing:

- verbatim memory substrate
- SCBE semantic sidecars
- full bijective transport sidecars
- code-aware identity signals

Only after that is it fair to judge whether SCBE augmentation improves retrieval.

## What To Benchmark First

Do not start with end-to-end chatbot quality. Start with retrieval quality and cost.

### Baseline

MemPalace-style baseline:

- verbatim chunk storage
- embedding or lexical retrieval
- no SCBE rerank

### Augmented

SCBE-augmented retrieval:

- same verbatim chunk storage
- same first-pass retrieval
- SCBE sidecar rerank and governance filter

### Metrics

Measure:

- `recall@k`
- `MRR`
- support-hit rate for answer grounding
- retrieval latency
- token cost for rerank path
- governance false positive rate
- governance false negative rate

The first question is not "is it smarter?" The first question is:

- does SCBE reranking improve top-k quality enough to justify its cost?

## Suggested Memory Object Schema

```json
{
  "memory_id": "uuid",
  "source_type": "note|transcript|egg|packet|artifact",
  "verbatim_text": "...",
  "metadata": {
    "source_file": "...",
    "created_at": "...",
    "session_id": "...",
    "authority": "plain|governed|egg"
  },
  "scbe_sidecar": {
    "tongue_vector": [0, 1, 0, -1, 0, 1],
    "semantic_histogram": {},
    "trust_baseline": 0.0,
    "flags": {
      "negative": false,
      "temporal": true,
      "relation": false
    },
    "rhombic_hint": 0.0
  }
}
```

The important part is that `verbatim_text` remains first-class. The sidecar augments it. The sidecar does not replace it.

## Recommended Implementation Order

1. Build a small local verbatim memory store over:
   - selected Obsidian notes
   - selected SCBE transcripts
   - selected Sacred Egg metadata
2. Attach SCBE sidecars using `atomic_tokenization.py`.
3. Run a raw retrieval baseline.
4. Add SCBE rerank only.
5. Measure retrieval lift and cost.
6. Only then decide whether deeper geometry belongs in the memory path.

## What This Note Does Not Claim

- It does not claim SCBE memory already matches or beats MemPalace.
- It does not claim Sacred Eggs are already a retrieval engine.
- It does not claim geometry should replace storage.
- It does not claim benchmark results outside the cited MemPalace repo files.

## Sources

### MemPalace

- [external_repos/mempalace/benchmarks/BENCHMARKS.md](../../../external_repos/mempalace/benchmarks/BENCHMARKS.md)
- [external_repos/mempalace/mempalace/README.md](../../../external_repos/mempalace/mempalace/README.md)
- [external_repos/mempalace/mempalace/searcher.py](../../../external_repos/mempalace/mempalace/searcher.py)
- [external_repos/mempalace/mempalace/knowledge_graph.py](../../../external_repos/mempalace/mempalace/knowledge_graph.py)

### SCBE

- [docs/01-architecture/sacred-eggs-systems-model.md](../../../docs/01-architecture/sacred-eggs-systems-model.md)
- [python/scbe/atomic_tokenization.py](../../../python/scbe/atomic_tokenization.py)
- [python/scbe/history_reducer.py](../../../python/scbe/history_reducer.py)
- [python/scbe/rhombic_bridge.py](../../../python/scbe/rhombic_bridge.py)
- [src/symphonic_cipher/scbe_aethermoore/sacred_egg_integrator.py](../../../src/symphonic_cipher/scbe_aethermoore/sacred_egg_integrator.py)
