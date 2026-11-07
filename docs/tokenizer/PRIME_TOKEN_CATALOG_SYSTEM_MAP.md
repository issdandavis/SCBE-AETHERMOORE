# Prime Token Catalog System Map

Status: BOUNDED LOCAL IMPLEMENTATION VERIFIED; CAPABILITY GAIN UNESTABLISHED
Date: 2026-11-07

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

## Lexical-Band Discovery Map — 2026-11-07

The post-benchmark inventory receipt is
`C:/dev/clay-training-runs/prime-token-catalog-20261106/SYSTEM_INVENTORY_20261107.json`,
SHA-256 `41cf010c205079ed84f68c93baa770ad4822a46efa2c8f3aae0126a01b65227e`.
It covers the clean SCBE and isolated Loom worktrees and does not replace the
earlier three-root implementation inventory.

The next bounded node reuses both existing child searches:

```text
query -> lexical-only scores -----------+
                                         -> anchored lexical score bands
query -> aligned/shuffled six-view scores+   -> auxiliary ordering inside a band
                                             -> unchanged lexical score output
                                             -> controlled evaluator + receipt
```

The new capability under test is restricted auxiliary routing when lexical
evidence is close, not a new tokenizer or learned semantic layer. Inputs are the
existing catalog path, goal text, control seed, result limit, and fixed band
width. Outputs preserve the search receipt schema and add the band width,
band-anchor score, lexical score, auxiliary score, and stable child search IDs.

The first independent 31-request set is development-only. The already-observed
lexical-first holdout is also consumed and cannot validate this candidate. The
predeclared discovery grid, controls, selection rule, third-holdout requirement,
compute budget, rollback boundary, and stop conditions are frozen in
`docs/tokenizer/PRIME_TOKEN_LEXICAL_BAND_DISCOVERY_20261107.md`.

The committed implementation revision is `six-view-lexical-band-v1` at commit
`d1c935b2c`. The development grid selected width `0.005` by its predeclared
smallest-width tie rule. Its MRR advantage over lexical-only was only `0.001707`,
so the candidate remains unproven and requires a third hash-disjoint holdout.

Third-holdout collection stopped before scoring: the corrected pre-November
Codex queue has seven authentic requests and the available Claude sessions add
one, below the 30-query floor. Parser commit `c4ed93cda` rejects retained-source
and tool-transcript artifacts that an initial invalid queue admitted. The
selected width remains development-only until enough authentic, independently
authored, query-hash-disjoint requests exist.

An expanded pre-design audit subsequently found the August 2026 scrubbed direct-
speech corpus, which retains hashed source-session and turn provenance for 6,085
user-authored rows. The existing fixed topic policy yielded 320 candidates. A
complete review of its 48-request prime-sieve stratum accepted 34 and rejected
14; the sealed private benchmark has unique query-source records, zero overlap
with both consumed 31-query sets, and passes catalog source-disjoint validation.
Labels now bind the exact canonical review queue rather than only the source
dataset hash. The candidate remains development-only until this sealed holdout
is scored once against all preregistered controls.

The one-shot score at commit `f8cb2bff9` returned `NO_GAIN`. Lexical-band,
lexical-only, no-intervention, and every shuffled-binding seed all scored MRR
1.0; all 34 query outcomes were unchanged and all declared gates failed. The
full six-view reference scored MRR 0.985294 after moving one query from rank 1
to rank 2. Because the complete accepted stratum maps to one sieve source, this
is an authentic source-record-disjoint ceiling test, not cross-source evidence.
The result is retained without changing any probability table, tokenizer,
serving pointer, or model weight.

The next candidate is preregistered in
`docs/tokenizer/PRIME_TOKEN_EXPLICIT_ROUTE_PREREGISTRATION_20261107.md`.
It keeps lexical retrieval authoritative and permits at most two explicit
intent-matched auxiliary views inside the frozen `0.005` lexical band. Its
balanced private holdout requires at least three strata, six relevant catalog
sources, and a 40-percent per-source cap before scoring. Route-null and shuffled
controls must both fail before view identity can receive credit. No holdout text
was reviewed and no candidate result was observed when this design was frozen.

The subsequent balanced collection stopped with
`INSUFFICIENT_CROSS_SOURCE_HOLDOUT`: complete review accepted only 16 of 60
session-capped candidates, below the frozen 30-query floor. No benchmark file or
retrieval score was produced. The routed implementation and negative collection
receipt remain preserved; creating a real cross-source gate now requires a
broader attributed catalog or a new independent request pool, not relaxed labels.

The first rights-bound development expansion is recorded in
`docs/tokenizer/PRIME_TOKEN_CATALOG_EXPANSION_20261107.md`. Its strict input
manifest binds 33 local sources to content hashes, source kinds, licenses, and
rights bases. The resulting catalog remains unscored and unpromoted. The prior
60-query review set is development-consumed; only a newly authored independent
pool may evaluate the expanded catalog.

The expanded catalog passes the structural source gate at commit `d4a7f82ea`:
manifest and catalog hashes agree, all 33 sources expose all six views, three
source kinds are present, no license is unknown, and the largest source holds
17.175 percent of sections. This proves catalog readiness only. Retrieval
capability remains unmeasured until a new independent query pool exists.

The current development candidate is the 35-source v5 rights-bound catalog. It
restores Loom's exact five-W and prime-sieve implementation files through a
separate local, hash-bound, internal-research authorization; those two files are
not represented as MIT or redistributable. V5 also passes the structural gate,
but remains unscored and cannot replace an independent retrieval holdout.

Prospective holdout harvesting now requires a timezone-aware authored timestamp
strictly after the frozen catalog cutoff (`3d4ee3d1e`). The old voice corpus lacks
that evidence and is rejected without writing a queue. Only newly exported,
scrubbed user-authored requests may satisfy the next source-disjoint gate.

The current internal development candidate is v6. It adds 2,119 verified,
scrubbed, timestamped user-authored records from an inactive Codex session log
to the 35-source v5 boundary, yielding 2,154 sources, 9,750 sections, 339,637
occurrences, and 315,594 bounded relationship memberships. Internal conversation
records remain owner-authorized research data and are not relabeled as MIT or
redistributable. The catalog SHA-256 is
`1839d609bc8e7263263e4c83d1bac2c3645285a9a664abfc6e9f292cc0b2fba0`.

V6 passes the same structural source gate with five source kinds, complete
six-view coverage, zero unknown rights labels, and a largest-source section
share of `0.06708`. Every retained conversation predates the v6 freeze, so the
layer is eligible only for development or a separately controlled training
experiment. It is not prospective holdout evidence and has not been scored,
attached to a probability table, or written into model weights.

The v6 pre-score gate at commit `c0b4ee810` also compares query identity against
source and section byte hashes plus normalized token-stream hashes. It found
both prior 31-query private-session benchmarks entirely inside v6 and blocks
them before retrieval. The remaining historical sets are either underpowered or
development-consumed. Consequently, the only valid next capability path is a
new post-freeze prospective pool; no historical result may be relabeled as a v6
holdout.

Prospective collection at commit `713195820` derives its cutoff from the exact
catalog manifest and carries the manifest/catalog hashes through review into the
benchmark. The evaluator checks that binding before retrieval, preventing a
valid pool for one catalog version from silently becoming evidence for another.
