# Snake Pipeline Lesson Plan & Ingestion Guide

## The Problem

214K training records. 107K are pure lore. 27 are CS fundamentals. 0 are cross-language interop.
The model can recite the Spiralverse but can't route a purchase query to real products.

**Fix**: Inject real educational courseware as grounding mass. Not rules — knowledge.
When "buy" enters the geometry near 10K grounded product/CS/math records instead of
floating in 107K lore records, it routes correctly because the MASS is there.

## Data Type Map

| Type | Source | Records Needed | Tongue Affinity | Ingestion Method |
|------|--------|---------------|-----------------|------------------|
| CS Fundamentals | Context7 docs, open textbooks | 5,000+ | CA (Compute) | `context7 → auto_marker → snake` |
| Math (Linear Algebra, Calculus) | Open courseware, textbooks | 3,000+ | CA (Compute) | `context7 → auto_marker → snake` |
| Quantum Physics | Open courseware, arXiv | 2,000+ | CA+UM | `web_extract → auto_marker → snake` |
| Python Course | Context7 (stdlib, tutorials) | 3,000+ | AV (Wisdom) | `context7 → multilang_forge` |
| TypeScript Course | Context7 (TS handbook) | 3,000+ | DR (Structure) | `context7 → multilang_forge` |
| Rust Course | Context7 (Rust book) | 3,000+ | UM (Security) | `context7 → multilang_forge` |
| Cross-Language Interop | PyO3/wasm-bindgen/napi docs | 2,000+ | DR+UM+AV | `context7 → multilang_forge` |
| Real Product Q&A | Site content, support logs | 500+ | KO (Intent) | `manual + fabrication` |
| Adversarial Puzzles | Generated | 1,000+ | RU (Governance) | `adversarial_traps.py` |
| SCBE Architecture (grounded) | Docs, code comments | 2,000+ | DR (Structure) | `codebase_to_sft.py` |

**Target**: 25,000+ grounded records to counterbalance the 107K lore mass.

## Timeline: 5-Phase Curriculum

### Phase 1: Foundations (CS + Math + Physics)
**Goal**: Give the model computational bedrock.

```
Week 1: CS Fundamentals
  Day 1-2: Data structures (arrays, linked lists, trees, graphs, hash tables)
  Day 3-4: Algorithms (sorting, searching, dynamic programming, graph traversal)
  Day 5:   Complexity (Big-O, space/time tradeoffs, amortized analysis)
  
Week 2: Mathematics
  Day 1-2: Linear algebra (vectors, matrices, eigenvalues, transformations)
  Day 3-4: Calculus (derivatives, integrals, chain rule, gradient descent connection)
  Day 5:   Probability & statistics (Bayes, distributions, hypothesis testing)

Week 3: Physics → SCBE Bridge
  Day 1-2: Classical mechanics (Lagrangian, Hamiltonian, phase space)
  Day 3:   Quantum mechanics (Hilbert space, unitary operators, measurement)
  Day 4:   Hyperbolic geometry (Poincare model, geodesics, curvature)
  Day 5:   Bridge to SCBE (how physics concepts map to the 14-layer pipeline)
```

### Phase 2: Language Mastery (Python + TS + Rust)
**Goal**: Fluency in the foundation trio, including cross-language patterns.

```
Week 4: Python Deep Dive
  Day 1: Core (types, control flow, functions, classes)
  Day 2: Standard library (collections, itertools, pathlib, json)
  Day 3: Scientific (numpy, scipy, math operations)
  Day 4: ML/AI (torch, transformers, datasets, tokenizers)
  Day 5: Testing (pytest, hypothesis, property-based testing)

Week 5: TypeScript Deep Dive
  Day 1: Core (types, interfaces, generics, enums)
  Day 2: Runtime (Node.js, async/await, streams, buffers)
  Day 3: Frameworks (Express, Vitest, fast-check)
  Day 4: Advanced (type-level programming, conditional types, mapped types)
  Day 5: Build systems (npm, tsconfig, bundling, package exports)

Week 6: Rust Deep Dive
  Day 1: Ownership (borrow checker, lifetimes, moves)
  Day 2: Types (traits, generics, enums, pattern matching)
  Day 3: Concurrency (async, tokio, channels, atomics)
  Day 4: FFI (extern "C", bindgen, PyO3, wasm-bindgen)
  Day 5: Cargo (workspace, features, build scripts, publishing)
```

### Phase 3: Interop & Bridge Patterns
**Goal**: Cross-language fluency — same concept, three implementations, one build.

```
Week 7: The Polyglot Build
  Day 1: PyO3 — Rust functions callable from Python
  Day 2: wasm-bindgen — Rust functions callable from TypeScript
  Day 3: napi-rs — Rust native Node.js addons
  Day 4: Full trio build — Cargo → .so + .wasm + .whl in one pipeline
  Day 5: Integration testing across language boundaries
```

### Phase 4: SCBE-Grounded Application
**Goal**: Connect foundational knowledge to SCBE architecture with REAL grounding.

```
Week 8: SCBE Architecture as Applied Science
  Day 1: Poincare ball (the math) → Layer 4 (the code) → "why adversarial costs scale"
  Day 2: Harmonic wall formula → Layer 12 → "how safety scoring works"
  Day 3: Sacred Tongues (the CS) → Langues metric → "why phi-weighting matters"
  Day 4: Product grounding — "what the site sells" vs "what the lore describes"
  Day 5: Identity grounding — "who built this" vs "who exists in the Spiralverse"
```

### Phase 5: Adversarial & Context Awareness
**Goal**: Teach the model to detect CONTEXT, not just content.

```
Week 9: Adversarial Training
  Day 1: Context-trap puzzles (math that reveals hidden intent)
  Day 2: Lore-to-real disambiguation (same word, different grounding)
  Day 3: Purchase intent detection (customer vs lore-seeker)
  Day 4: Identity awareness (real owner vs fictional character)
  Day 5: Coach Rune governance review (NIST framework walkthroughs)
```

## Ingestion Guide by Data Type

### Type 1: Documentation → SFT (via Context7)

```
Source: Context7 library docs (Python stdlib, Rust book, TS handbook, etc.)
Tool:   mcp context7 resolve-library-id → query-docs
Flow:   raw doc → auto_marker.py → OrientedRecord → snake pipeline
Output: instruction/response pairs tagged with tongue + layer + grounding=1.0
```

Steps:
1. `resolve-library-id` for each library (python, typescript, rust, numpy, etc.)
2. `query-docs` with topic-specific queries ("binary search", "ownership model", etc.)
3. Pipe raw docs through `training/auto_marker.py` for tongue/layer/null classification
4. Run through snake pipeline stages 1-5 for geometric embedding
5. Stage 6 (multilang_forge) generates cross-language variants
6. Output: JSONL with full metadata chain

### Type 2: Executable Code → SFT (via codebase)

```
Source: SCBE-AETHERMOORE codebase (.py, .ts, .rs files)
Tool:   scripts/codebase_to_sft.py
Flow:   source file → AST parse → function extraction → instruction/response pairs
Output: code explanation + implementation pairs with tongue + layer tags
```

Each code file maps to a tongue:
- `src/harmonic/*.ts` → CA (Compute) + DR (Structure)
- `src/crypto/*.ts` → UM (Security)
- `src/fleet/*.ts` → RU (Governance)
- `src/symphonic_cipher/**/*.py` → AV (Wisdom)
- `hydra/**/*.py` → KO (Intent)

### Type 3: Cross-Language Interop → SFT (generated)

```
Source: Same algorithm implemented in Python + TypeScript + Rust
Tool:   training/snake/multilang_forge.py + sphere_grid.py
Flow:   concept → 3 implementations → bridge code → build config
Output: Polyglot build examples with interop metadata
```

Pattern: "Implement binary search" →
  - Python version (AV tongue, grounding=1.0)
  - TypeScript version (DR tongue, grounding=1.0)
  - Rust version (UM tongue, grounding=1.0)
  - PyO3 bridge (AV+UM, grounding=1.0)
  - wasm-bindgen bridge (DR+UM, grounding=1.0)

### Type 4: Real-World Q&A → SFT (manual + generated)

```
Source: Site content, product descriptions, owner identity
Tool:   Manual curation + glass_box fabrication
Flow:   real question → grounded answer → fabrication profile → tagged SFT
Output: High-grounding records (grounding >= 0.85)
```

Every record carries:
- `grounding: 1.0` (verifiable fact)
- `audience: customer` or `developer`
- `tongue: KO` (purchase) or `RU` (identity) or `DR` (navigation)
- Full fabrication structure (12D vector per point)

### Type 5: Adversarial Puzzles → DPO (generated)

```
Source: Generated context-trap puzzles
Tool:   training/snake/adversarial_traps.py
Flow:   setup → hidden context → math trap → Morse reveal → debrief
Output: DPO pairs (rejected=naive solve, chosen=context-aware)
```

## Parability (Cross-Source Compatibility)

All records share a common schema regardless of source:

```json
{
  "instruction": "...",
  "output": "...",
  "metadata": {
    "source": "context7|codebase|manual|generated|claude|grok|chatgpt",
    "tongue": "KO|AV|RU|CA|UM|DR",
    "tongue_profile": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "layer": "L0|L1|L2|L3",
    "grounding": 0.0,
    "audience": "customer|lore_seeker|developer|self",
    "category": "...",
    "language": "python|typescript|rust|mixed",
    "has_code": true,
    "fabrication_depth": 0,
    "pipeline_stages_passed": []
  }
}
```

### Merge Order (by weight)

1. **Grounded courseware** (CS/math/physics/coding) — highest priority, fills critical gaps
2. **Cross-language interop** — unique training signal, zero existing records
3. **Product/identity Q&A** — grounding anchors for Polly
4. **SCBE architecture (grounded)** — bridge between theory and code
5. **Adversarial puzzles** — context-awareness training
6. **Existing lore** — downsample to ~30% of total (from current 50%+)
7. **Existing claude/grok/chatgpt** — keep as-is, they provide conversation patterns

### Target Distribution After Rebalancing

| Category | Current | Target | Records Needed |
|----------|---------|--------|---------------|
| Lore (pure) | 107,500 (50%) | 30% | Downsample to ~75K |
| Math/Science | 52,227 (24%) | 20% | OK (rebalance away from lore-adjacent) |
| Code (executable) | 20,907 (10%) | 20% | +30K from courses |
| CS Fundamentals | 27 (0%) | 10% | +25K from courses |
| Cross-lang interop | 0 (0%) | 5% | +12K from forge |
| Product/Grounded | 226 (0%) | 5% | +12K from Q&A + site |
| Adversarial | 64 (0%) | 5% | +12K from traps |
| Conversation patterns | ~33K (15%) | 5% | OK (natural ratio) |

**Total target: ~250K balanced records**

## Execution: Context7 Ingestion Queries

### CS Fundamentals (target: 5K records)
```
Libraries to resolve:
  - python (stdlib: collections, itertools, functools)
  - algorithm-visualizer or similar
  
Queries per library:
  - "binary search implementation"
  - "hash table collision resolution"  
  - "graph traversal BFS DFS"
  - "dynamic programming memoization"
  - "sorting algorithms comparison"
  - "tree traversal in-order pre-order post-order"
  - "linked list operations"
  - "stack and queue implementations"
  - "heap priority queue"
  - "time complexity analysis"
```

### Python Course (target: 3K records)
```
Libraries to resolve:
  - python
  - numpy
  - scipy
  - pytorch
  - transformers (huggingface)
  - pytest
  - hypothesis

Queries: core syntax, standard library, scientific computing, ML pipeline
```

### TypeScript Course (target: 3K records)
```
Libraries to resolve:
  - typescript
  - node (Node.js)
  - express
  - vitest
  - fast-check

Queries: type system, generics, async patterns, testing, build config
```

### Rust Course (target: 3K records)
```
Libraries to resolve:
  - rust
  - tokio
  - serde
  - pyo3
  - wasm-bindgen

Queries: ownership, traits, async, FFI, cargo workspace
```

### Quantum/Physics (target: 2K records)
```
Libraries to resolve:
  - qiskit (quantum computing)
  - pennylane (quantum ML)
  
Additional sources:
  - arXiv papers on hyperbolic geometry in ML
  - Poincare embeddings papers
```

## Code Executables (what runs each phase)

| Phase | Script | Status | Input | Output |
|-------|--------|--------|-------|--------|
| Intake | `training/auto_marker.py` | EXISTS | raw text | OrientedRecord JSONL |
| Context7 Pull | `training/snake/context7_ingest.py` | NEEDS BUILD | library queries | raw docs |
| Snake Pipeline | `training/snake/pipeline.py` | NEEDS BUILD | OrientedRecord | full metadata JSONL |
| Multi-lang Forge | `training/snake/multilang_forge.py` | NEEDS BUILD | concept | 3+ language variants |
| Adversarial Traps | `training/snake/adversarial_traps.py` | NEEDS BUILD | domain templates | DPO pairs |
| Grounding Anchors | `training/snake/grounding_forge.py` | NEEDS BUILD | product/identity facts | high-grounding SFT |
| Merge & Balance | `training/snake/merge_balance.py` | NEEDS BUILD | all JSONL files | balanced dataset |
| HF Push | `training/snake/pipeline.py --push` | NEEDS BUILD | balanced dataset | HF dataset |

## The Thesis

> You don't teach a model by telling it rules.
> You teach it by giving it enough MASS in the right places
> that the geometry routes correctly on its own.
>
> 107K lore records = a black hole that swallows everything.
> 25K grounded course records = a counterweight that creates
> stable orbits around REAL knowledge.
>
> The model doesn't need to be told "don't answer with potions."
> It needs enough real product data that "buy" routes to products
> the same way a ball rolls downhill — because the mass is there.
