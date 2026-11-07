# Prime Token Catalog System Map

Status: BOUNDED LOCAL IMPLEMENTATION VERIFIED; CAPABILITY GAIN UNESTABLISHED
Date: 2026-11-06

## Capability

Build a streaming, source-aware word catalog that preserves exact input identity,
attaches Clay's frozen tokenizer IDs, labels sections with explicit 5W evidence,
adds SCBE atomic and speech-function views, routes occurrences through prime and
non-prime lanes, and exposes a sparse pre-vector retrieval index.

The catalog is an external deterministic tool. It is not a model layer, learned
semantic capability, training result, or replacement tokenizer.

## Current Node Map

```text
local/downloaded sources
  -> source records + content hashes
  -> canonical UTF-8 bytes and word spans
  -> frozen BPE-4096 word-span view + exact byte-ID view
  -> atomic semantic evidence + function-word candidate senses
  -> section 5W evidence -> derived color
  -> Loom Eratosthenes sieve -> prime/composite/edge occurrence lanes
  -> bounded relationship memberships + sparse section features
  -> SQLite catalog + JSONL streams + HTML preview + immutable manifest
  -> lexical baseline / feature ablations / shuffled-binding control
  -> optional compact read-only packet for a detached tablet context surface
```

## Reused Authorities

| Node | Path | Role | Authority/status |
|---|---|---|---|
| Active Clay token identity | `C:/dev/tongue-compiler/artifacts/token_flow_infrastructure_20261015/TOKEN_FLOW_INFRASTRUCTURE_BLUEPRINT.md` | Current Clay consumes UTF-8 byte IDs 0..255 | Active architecture map; bytes remain canonical |
| Frozen BPE tokenizer | `C:/dev/clay_home/tokenizers/clay_open_core_bpe_v1/tokenizer.json` | Optional historical BPE-4096 view for word spans | Frozen; SHA-256 `6c14a5cd26188678f920273cff49483f535e340caa98e3a7eb4d3285286c37c6` |
| Atomic analyzer | `python/scbe/atomic_tokenization.py` | Evidence-bearing semantic class, element, trits and lexical domains | Active deterministic tool; unresolved stays explicit |
| Speech-function registry | `python/scbe/function_lexicon.py` | Candidate function/content senses, UPOS, family and perspective roles | Authored deterministic registry; SHA-256 `a95236d9e95ecac4def40860069313bfb1ae0f2bbe3148e42f4373872b60dee4` |
| 5W precedent | `C:/dev/loom/wall_5w.py` | Structured who/what/when/where/why records | Reused contract shape; its route-wall semantics are not reused |
| Prime sieve | `C:/dev/loom/clay_sieve.py` through `python/scbe/chemistry_sieve_spectrum.py` | Exact prime/composite/edge classification and factors | Existing tested Eratosthenes implementation |
| Pre-build inventory | `C:/dev/clay-training-runs/prime-token-catalog-20261106/INVENTORY.json` | Immutable three-root inventory | SHA-256 `f9a011f5d2b36d73bff62014d461a0cff4f9d60ff56eec552f511452cb574668` |

## New Nodes

1. A streaming source reader for plain text, Markdown, code and downloaded JSONL.
2. A stable source/section/word occurrence identity contract.
3. Evidence-scored 5W section labels and a versioned 5W-to-color mapping.
4. Prime routing over the one-based global occurrence ordinal. The ordinal is a
   routing address, not a semantic measurement.
5. Bounded inverted relationship memberships instead of quadratic occurrence
   pairs.
6. A sparse section-feature index and deterministic search before neural vectors.
7. A manifest containing source, tokenizer, mapping and output hashes.

The laptop catalog remains canonical. A detached tablet may receive a compact,
hash-addressed search packet containing source IDs, section IDs, previews and
evidence paths. It must return IDs or annotations rather than editing the catalog,
probability sidecar or model checkpoint. No tablet transfer was performed in this
build.

## Six-View Retrieval Field

The search field has six typed views of the same canonical occurrence:

1. lexical identity and exact byte/BPE spans;
2. 5W goal/section evidence and its derived color;
3. speech-function candidates, UPOS and grammar constraints;
4. atomic semantic evidence and tongue-trit view;
5. prime lane, factors, modulus, residue and range;
6. source kind, source identity and evidence provenance.

Each view receives a bounded normalized contribution so the high-cardinality
lexical view cannot drown out the others. Shared feature memberships form a
sparse hypergraph. Goal search seeds matching sections, propagates bounded score
mass across shared memberships, and competitively normalizes each step so
supported relationships rise while unsupported candidates fall. The output is
a goal-to-section-to-token evidence path, not a generated answer.

Grammar is secondary. Content/idea/evidence tokens drive retrieval. Function
words, UPOS candidates, negation and causal markers are returned as constraints
and scaffolding for a later generator; they do not become independent evidence
or dominate the idea score.

## Probability Lookup and Weight Anchor

Goal search may update an external token-probability lookup table. Every update
is append-only and records the goal, old/new probability, six-view evidence,
algorithm revision and model/checkpoint anchor hash. This modifies retrieval
probabilities, not neural tensors. A later neural attachment must consume the
table through a zero/identity-initialized input sidecar and pass source-disjoint,
shuffled-binding, equal-width and retention controls before any weight promotion.

## Edge Contracts

- `source -> section`: source ID, source kind, URI/path, content SHA-256,
  section ordinal, exact character range and section SHA-256.
- `section -> word`: occurrence ID, exact surface, normalized word, exact UTF-8
  bytes, section offsets and one-based global ordinal.
- `word -> tokenizer view`: tokenizer SHA-256 and overlapping BPE IDs/offsets.
  BPE IDs never replace byte IDs and are never compared to current byte-model IDs.
- `word -> speech views`: atomic evidence and every compatible function-lexicon
  candidate. Candidate senses are not silently disambiguated.
- `section -> 5W/color`: raw per-role scores, evidence tokens, primary role,
  palette mapping ID and color. Color is a derived display/routing view.
- `occurrence -> sieve lane`: ordinal, prime/composite/edge state, exact prime
  factors, role-prime modulus, residue and bounded range bucket.
- `occurrence -> relationships`: typed relation key memberships. No all-pairs
  graph is materialized.
- `goal -> retrieval field`: six separately normalized view scores, bounded
  topology propagation, explicit ablation/control mode, catalog hash, stable
  search ID and evidence path.
- `retrieval -> probability table`: append-only probability delta anchored to a
  caller-supplied model/checkpoint hash; no direct weight write is permitted.

## Invariants

1. Canonical source bytes and their hashes are unchanged.
2. Every derived view carries its mapping or authority hash.
3. Missing evidence is `UNRESOLVED`/`ABSENT`, never a meaningful zero.
4. One occurrence belongs to one source, section and canonical word span.
5. Color, BPE, atomic, tongue and prime views of one occurrence are correlated
   views, not additional observations.
6. Internet content enters only as a downloaded/source-attributed record; the
   core catalog performs no network fetches.
7. Output directories are immutable: an existing non-empty output is refused.
8. Relationship growth is linear in occurrences times a fixed membership cap.

## Controls and Success Gate

- Baseline: lexical/frequency-only retrieval.
- No-intervention control: canonical word catalog without 5W, source and prime
  features.
- Size-matched control: the same sparse feature count with 5W labels permuted
  one-to-one across sections.
- Ablations: remove 5W/color, source kind, atomic/function, or prime features.
- Holdout: split by source content hash, never by derived occurrence rows.
- Structural success: exact deterministic rebuild, tokenizer hash match, complete
  occurrence accounting, sieve parity, bounded memberships and search receipts.
- Capability success: only a source-disjoint retrieval benchmark that beats the
  lexical baseline and size-matched shuffled control across multiple seeds may
  claim an advantage. This build does not promote a weight or retrieval claim.

## Budget and Stop Conditions

- First implementation: CPU-only, under 1 GiB additional disk, bounded local
  source sample, and no model/checkpoint writes.
- Commit SQLite transactions in batches; avoid retaining the full corpus in RAM.
- Stop if the tokenizer hash differs, the sieve authority is unavailable, any
  source cannot be attributed, occurrence counts diverge, membership growth
  exceeds the declared cap, output exists, or free disk falls below 5 GiB.

## Saves and Rollback

Runtime outputs go to a new timestamped directory under
`C:/dev/clay-training-runs/prime-token-catalog-20261106/`. Source code lives in
SCBE-AETHERMOORE and is reverted by its Git commit. No Clay weights, tokenizer,
serving pointer or active training checkpoint are modified.

## Downstream Problem Created

The catalog can make deterministic routing metadata look semantically powerful.
Consumers must therefore keep lexical evidence, derived encodings, source
provenance and learned scores separate. A later trainer must group every view of
the same source record into one split and use the controls above before attaching
this catalog as an input layer.

## Implementation Update — 2026-11-06

Implemented in `python/scbe/prime_token_catalog.py` with the command surface in
`scripts/tokenizer/build_prime_token_catalog.py` and focused coverage in
`tests/tokenizer/test_prime_token_catalog.py`.

The final bounded pilot is
`C:/dev/clay-training-runs/prime-token-catalog-20261106/local-pilot-v3/`:

- 11 sources, 364 sections, 10,220 occurrences and 20,923 bounded relationship
  memberships;
- immutable catalog SHA-256
  `0c051ab5c27da8f70fd0d77830994e03bf55cda0224c696d06ac3cedf404b403`;
- 256 probability events in a separate sidecar, summing to 1.0 and anchored to
  weight SHA-256
  `003c7b846f59aa67fe6cefb04647bd93d94b896ad2617ad79384f1ac8246fd1f`;
- aligned top score 1.031711 on the sieve-routing implementation versus 0.898709
  for the shuffled-binding control's unrelated packaging result;
- 5W ablation top score 1.032159, effectively unchanged for this one query.

The pilot therefore proves the mechanics, audit trail, bounded storage and
separation of immutable evidence from mutable lookup probabilities. It does not
establish retrieval improvement: the sample is small, the aligned/shuffled result
is one query, and this query shows no independent 5W contribution. A later claim
requires source-disjoint evaluation across multiple queries/seeds against both
the lexical baseline and size-matched shuffled control.

Verification: Black and Flake8 passed; 48 focused and adjacent regression tests
passed. Runtime outputs are not committed. The incomplete first storage-heavy
attempt is held reversibly at
`C:/Users/issda/.quarantine/held-deletions/20261107T004424184Z-7a13dc21/local-pilot`.

## Benchmark Update — 2026-11-07

The source-record-disjoint evaluator is implemented in
`python/scbe/prime_token_benchmark.py`, exposed by
`scripts/tokenizer/evaluate_prime_token_catalog.py`, and uses the committed query
manifest at `research/tokenizer/prime_token_catalog_benchmark_v1.json`.

Seeded one-to-one shuffled controls now record their permutation offset under
algorithm revision `six-view-topology-v3`. Query source IDs and relevance labels
remain evaluator-only and are rejected if a query source appears in the catalog.

The first 11-query result is `UNDERPOWERED` and negative for the candidate:
full MRR 0.5329, lexical-only 0.6617, and no-intervention 0.5872. Three shuffled
controls averaged 0.2040. Prime and atomic ablations improved MRR but did not beat
lexical-only; speech ablation regressed. No two-pooled-SD gate passed. Details and
the next independent-query gate are in
`docs/tokenizer/PRIME_TOKEN_CATALOG_BENCHMARK_RESULT_20261107.md`.
