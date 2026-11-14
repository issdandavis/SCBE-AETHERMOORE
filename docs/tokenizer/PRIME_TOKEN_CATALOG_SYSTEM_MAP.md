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
It also verifies each retained query's timezone-aware authored timestamp is
strictly after that bound catalog freeze (`f592123e7`).

## Prospective Codex Collector Design — 2026-11-07

The next bounded component connects newly closed local Codex sessions to the
already frozen prospective-review gate. It is collection infrastructure, not a
retrieval result or training-data path.

```text
local Codex rollout JSONL files
  -> mtime prefilter only
  -> Loom's exact user.text parser + internal-context rejection + secret scrub
  -> immutable post-freeze direct-speech JSONL + source/hash receipt
  -> SCBE harvest_prime_token_queries.py
  -> v6-manifest-bound review queue
  -> human hash-bound relevance labels (only after >=30 accepted requests)
  -> existing source-disjoint evaluator + lexical/null/shuffled/ablation controls
```

The canonical value is one exact scrubbed user turn, identified by source-file
path hash, source line, authored timestamp, and exact query SHA-256. File mtime
only avoids rescanning known-old multi-gigabyte logs; it never establishes
prospective authorship. Every admitted row must carry a timezone-aware record
timestamp strictly after the catalog manifest's frozen generation time, and the
SCBE queue independently enforces the same boundary.

Reused nodes are the Loom direct-speech extractor at
`experiments/clay_codex_session_harvest_20261107/harvest_codex_session.py`, the
v6 `MANIFEST.json`, and the existing SCBE query harvester and evaluator. The
only new node is a multi-session, immutable collector around the Loom parser.
Raw session text never enters Git, the catalog, model weights, the probability
table, or the shared context ledger.

The downstream risk is accidentally treating system/tool transcript material
or pre-freeze requests as independent evidence. The collector must therefore
fail closed on a changed source, unknown manifest schema, missing timezone,
non-user metadata, internal markers, output reuse, or scrubber-source drift.
An empty or under-30 queue is retained as `INSUFFICIENT_PROSPECTIVE_QUERIES`;
the minimum is not relaxed and no labels or scores are synthesized.

The first bounded scan is CPU-only, reads only files whose modification time is
after the v6 freeze, writes under
`C:/dev/clay-training-runs/prime-token-catalog-20261106/prospective-collector-20261107/`,
and is expected to use less than 100 MiB additional disk. The pre-build
inventory is SHA-256
`2eb0df1a2c9baef7e3c4a392d130a7f3d34f39e4fe185b1c5560037af05df434`.
Rollback is path-bounded deletion or quarantine of that new runtime output;
source logs, catalog files, checkpoints, tokenizer, and serving pointers remain
untouched.

Implementation landed in the isolated Loom worktree at `3db063a`; commit
`10a0483` then made scrubber-source drift fail closed. Six focused
scrubber/collector tests pass. The current immutable scan at
`prospective-collector-20261107/scan-002/` discovered nine rollout files and
skipped all nine by the prefilter because their modification times predate the
v6 freeze. The collector verified the pinned scrubber hash before scanning. No
source body was opened, no direct-speech row was emitted, and the
empty dataset has the standard SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

SCBE independently converted that dataset into a v6-manifest-bound queue with
zero candidates. The queue content hash is
`f16e3cef0c4e0387b12feba30bb8182e49a1afc8db65ebb6a25a9eb24d013185`;
the collection report file hash is
`b7df9b1081e39a19afbdbf5e083b17196de6023e978d84a466023f03c9c451f6`.
Status remains `INSUFFICIENT_PROSPECTIVE_QUERIES`. No labels, retrieval scores,
probability updates, catalog changes, or weight writes occurred.

## Prospective watcher implementation update — 2026-11-07

Loom commit `f830b6f` adds the bounded headless watcher and strengthens the
collector with a Windows exclusive-open close gate. The watcher is a control
edge around the existing collector, not a new evidence source:

```text
rollout metadata
  -> post-v6 mtime prefilter
  -> exclusive-open closed-session gate
  -> pinned Loom collector
  -> immutable dataset/receipt
  -> pinned SCBE manifest-bound queue harvester
  -> stop at 30 candidates for human hash-bound review

open rollout ---------------------------- wait; body unopened
labels / retrieval scoring -------------- not authorized
catalog / probability table / weights --- no write edge
```

The watcher inventory is
`C:/dev/clay-training-runs/prime-token-catalog-20261106/prospective-watcher-20261107/SYSTEM_INVENTORY.json`
with SHA-256
`6a3af9e6621e22b7aab1a28a353267124722be597c3db6cd10a2b036a018be3b`.
Its pin receipt has SHA-256
`ad74d3b12fce33456b372426949948a2b23954628f8463f3af0f70debd676848`.
The observed runtime is waiting for a closed post-freeze source; it has not
emitted a third scan, labels, scores, probability events, or weight changes.

## Six-view structure audit — 2026-11-08

The reusable `audit-views` command now distinguishes complete view coverage
from independent evidence. It opens the catalog read-only, hashes exact
section/view feature signatures, reports collisions and feature cardinality,
and verifies the catalog hash before and after. The full v6 run passed all
integrity checks: every one of 9,750 sections has every declared view, with no
unknown or orphan rows and no catalog mutation.

The audit records lexical as the canonical anchor; speech and atomic as
deterministic lexical annotations; five-W as a deterministic section
aggregation; prime as a deterministic ordinal/role routing view; and source as
external metadata. Thus complete six-view coverage is not six independent
semantic observations. The prime signature is unique for all 9,750 sections,
which makes it a high-cardinality positional identity channel rather than
standalone semantic evidence.

The immutable receipt is
`S:/ClayRuns/prime-token-view-audit-20261108/VIEW_STRUCTURE_AUDIT.json`, SHA-256
`2d93aa24a4b14164254d639b1787c968268d214dc32f5cdc07b818785b501b6d`.
The detailed result is in
`docs/tokenizer/PRIME_TOKEN_VIEW_STRUCTURE_AUDIT_20261108.md`. This is a
structural result only. E92's prospective source-disjoint gate, lexical
baseline, route-null control, shuffled bindings, and no-promotion boundary are
unchanged.

## Live prospective-chain audit — 2026-11-08

The reusable `verify_prime_token_watch_chain.py` command now independently
checks the complete pre-score runtime edge: source-session-disjoint watcher pin,
collector and harvester hashes, frozen catalog identity, unreviewed-packet
preparer pin, candidate floor, live no-authority statuses, complete packet
writes, and absence of `BENCHMARK.json`, `RESULT.json`, or `RUN_RECEIPT.json`
from the collection/preparation directory. It never opens session bodies,
selects labels, or executes retrieval.

The post-commit live audit reports `VERIFIED_WAITING_NO_SCORING` with zero errors
and audit SHA-256
`069fca05d619d95416d84d3da9f0d95b7b993701e615c42b3fbeed2019014bb6`.
The frozen v6 catalog remains unchanged, the 30-candidate floor remains intact,
one post-freeze session is still open, and no scoring or training artifact is
present. The runtime receipt is
`C:/dev/clay-training-runs/prime-token-catalog-20261106/source-disjoint-audit-20261108/LIVE_CHAIN_AUDIT.json`.

Implementation lives in `python/scbe/prime_token_watch_audit.py` with the CLI
wrapper under `scripts/tokenizer/`. Four mutation/boundary tests cover source
hash drift, authority drift, forbidden scoring output, partial packet writes,
and the valid waiting/packet-ready states. The broader focused evidence is 32
catalog/evaluator tests plus 17 collector/preparer/watcher tests passing.

## Continuation audit — 2026-11-09

The live watcher and preparer were re-audited without opening the active session
or running retrieval. The fresh receipt again reports
`VERIFIED_WAITING_NO_SCORING` with zero errors, zero closed post-freeze sources,
one open source, zero candidates, and no benchmark, result, run, review-packet,
serving, merge, training-intake, or promotion artifact. The catalog SHA-256 is
still `1839d609bc8e7263263e4c83d1bac2c3645285a9a664abfc6e9f292cc0b2fba0`.

Receipt:
`C:/dev/clay-training-runs/prime-token-catalog-20261106/source-disjoint-audit-20261108/LIVE_CHAIN_AUDIT_20261109T0724Z.json`;
canonical audit SHA-256
`b5fb8843a4709b8ecbd93614fb729dd827906ae2d2d463d88f0e8cf3ad89427c`;
file SHA-256
`76afedd2f1b58ed6eadd2eefecbd42260b2b154b7bd675cb40cc21aefb47c515`.
The focused catalog, prospective evaluator, query-harvest, and watch-audit suite
passes 36/36. This remains a verified wait and does not authorize scoring the
open session or changing tokenizer probabilities or model weights.

## Second continuation audit — 2026-11-09 07:46 UTC

The exact pinned watcher/preparer chain was independently re-run while both
headless workers remained live. The receipt again reports
`VERIFIED_WAITING_NO_SCORING` with zero errors, zero closed post-freeze sources,
one open source, zero candidates, and no benchmark, result, run, packet,
serving, merge, training-intake, or promotion artifact. The frozen catalog
SHA-256 remains
`1839d609bc8e7263263e4c83d1bac2c3645285a9a664abfc6e9f292cc0b2fba0`.

Receipt:
`C:/dev/clay-training-runs/prime-token-catalog-20261106/source-disjoint-audit-20261108/LIVE_CHAIN_AUDIT_20261109T0746Z.json`;
canonical audit SHA-256
`f230e1332695916cccf93115b368ac516ce76aad77d63dcc83cd80000397bfa8`;
file SHA-256
`4a4b50f8379f8032f3150d80908894d090ff691b16b987d680af32d430692139`.
This is collection-only evidence. The active session remains excluded from
prospective scoring until it closes and the 30-candidate floor is met.

## Third continuation audit — 2026-11-09 08:38 UTC

The same pinned watcher/preparer chain was audited again while both headless
workers remained live and continued updating their status receipts. The result
is `VERIFIED_WAITING_NO_SCORING` with zero errors, zero closed post-freeze
sources, one open source, zero candidates, and no benchmark, result, run,
review-packet, serving, merge, training-intake, or promotion artifact. The
frozen catalog SHA-256 remains
`1839d609bc8e7263263e4c83d1bac2c3645285a9a664abfc6e9f292cc0b2fba0`.

Receipt:
`C:/dev/clay-training-runs/prime-token-catalog-20261106/source-disjoint-audit-20261108/LIVE_CHAIN_AUDIT_20261109T0838Z.json`;
canonical audit SHA-256
`5c6780c41d8571dd4a8b896c33ba848607465a9e4bd37c219f8fa0916117d323`;
file SHA-256
`5507001e1bf117588ef4e5ffbae924878c876702ea7543ce24939a4ddb707dee`.
The source-session gate remains authoritative: this open session cannot enter
prospective scoring, training intake, or probability updates.

## Closed-snapshot v3 audit — 2026-11-10 17:55 UTC

The watcher advanced from the v2 source-disjoint pin to the v3 closed-source
snapshot pin. The first continuation audit correctly failed because the SCBE
auditor still admitted only v2; that immutable failure receipt is
`LIVE_CHAIN_AUDIT_20261110T1752Z.json` and reports only `watcher pin schema
mismatch`. The verifier was then extended with explicit v3 checks rather than
accepting arbitrary future schemas.

For v3, the verifier now requires the closed-snapshot gate, open-source
deferral, a source-session-disjoint deferred-open status, the bound snapshot
file, the exact canonical source-list fingerprint, matching source count,
unique source-session IDs, unchanged source size and modification time, and a
collection report bound to the same snapshot path, file hash, and count. It
still does not open active session bodies, label requests, run retrieval, or
authorize scoring or training.

The corrected live audit reports `VERIFIED_WAITING_NO_SCORING` with zero
errors. It verifies 9 closed post-freeze sources, 1 deferred open source, and 1
candidate against the unchanged minimum of 30. The frozen catalog remains
SHA-256
`1839d609bc8e7263263e4c83d1bac2c3645285a9a664abfc6e9f292cc0b2fba0`.
No review packet or forbidden scoring artifact exists.

Receipt:
`C:/dev/clay-training-runs/prime-token-catalog-20261106/source-disjoint-audit-20261108/LIVE_CHAIN_AUDIT_20261110T1758Z.json`;
canonical audit SHA-256
`ce5cff8d5a61ca8efb40026f3d210e861d61f7d5b9d6e5ddf60b483558c3b0e1`;
file SHA-256
`256d132772e12b276b507753beff080eb67ffd9b82a41b64d4a62ab0a808c8e8`.

The focused watch-audit, query-harvest, and prospective-evaluator suite passes
25/25; the v3 audit unit suite passes 6/6 after formatting and lint checks.
The gate remains closed and promotion remains unauthorized.

## Finite-evaluation and matched-route control hardening — 2026-11-10

The evaluator's candidate gates now require both the existing `2x` pooled-SD
margin and an exact one-sided paired sign test at alpha `0.05`. The receipt keeps
the raw win, loss, tie, non-tie and exact p-value counts. This prevents a small
deterministic sample with zero within-arm variance from passing only because its
pooled-SD threshold is zero.

The explicit-route and late-output-fusion receipts also prove that every
route-null query uses the same number of auxiliary views as its candidate. Both
arms declare zero trainable parameters, so this is the deterministic retrieval
equivalent of an equal-width/equal-parameter control. Candidate passage now
requires that structural contract in addition to lexical, no-intervention,
route-null, shuffled-binding, source-diversity and finite-sample gates.

This changes only evaluation strictness. It does not score the waiting v7
successor, open an active session, update a probability table, alter a tokenizer,
train a model, merge a child, or authorize promotion.

The independent E92 verifier reconstructs the exact sign statistics and matched
route-width contract from raw per-query outcomes; it does not trust those result
fields. A targeted tamper test proves that changing the recorded null width is
rejected. The combined catalog, prospective, query-harvest and watch-audit suite
passes 65/65 after Black and Ruff checks.

## Staged case and grammar address adapter — 2026-11-10

`python/scbe/token_surface_routes.py` now joins existing mechanics without
creating a seventh catalog view or changing the frozen catalog. Reversible
one-code-point upper/lower choices form a binary case address. An explicitly
observed S, V, or O role is separately transported through the six authoritative
tongue orders (KO/SOV, AV/SVO, RU/VSO, CA/OVS, UM/VOS, and DR/OSV). The combined
address is

`address = case_index * 6 + tongue_index`.

This makes every case/order possibility directly selectable without allocating
the full `2^cased_characters * 6` table. Exact surface bytes remain the
occurrence identity, normalized spelling remains the canonical word identity,
and role identity remains distinct from its tongue-specific presentation slot.
If a role was not parsed or receipted, no grammar route may be fabricated.

The adapter emits an eight-lane bounded numeric projection consumed directly by
the existing algebraic radial token table: four case-shape coordinates, three
S/V/O carrier lanes, and one centered slot coordinate. Those lanes are correlated
deterministic views, not new information or eight independent observations.
Likewise, the prior case-direction embedding probe remains inconclusive; exact
case encoding does not establish that a trained model has learned one global
uppercase direction.

This adapter is staged mechanics only. It does not alter the waiting v7 successor,
score prospective examples, train a model, authorize partial unfreezing, or
authorize promotion. Before catalog integration, compare it against a lexical
baseline, equal-width random features, shuffled case binding, shuffled
role-to-slot binding, case/grammar ablations, and the source-session-disjoint
holdout under the existing multi-seed gates.

## V7 source-readiness accounting — 2026-11-14

The live v7 chain is operational but still lacks enough admissible independent
queries. A stable count-only snapshot accounts for all 195 collector-eligible
turns across 16 closed sessions and one open session. The frozen selector accepts
4 closed-session candidates and 10 deferred open-session candidates; closing the
open source unchanged would yield 14, still 16 below the immutable floor of 30.
The remaining 181 turns are fully explained by 143 topic rejections and 38 length
rejections, with no selector-accounting gap or invalid JSON. This is classified
as `FIXED_SELECTOR_CANDIDATE_SCARCITY`, not pipeline failure.

A fresh independent pre-score audit reports `VERIFIED_WAITING_NO_SCORING` with
zero errors and verifies the frozen v7 catalog, closed-source snapshot,
collector/preparer pins, absent scoring artifacts, and disabled training and
promotion authority. Receipt paths, hashes, and the `20 / 20` focused test result
are recorded in
`docs/research/PRIME_TOKEN_SOURCE_DISJOINT_READINESS_20261113.md`.

The valid next edge is therefore additional independently authored,
selector-matching source sessions. Lowering the selector, reusing consumed
queries, admitting the open source early, or manufacturing rows remains outside
the frozen evaluation contract.

## Query-session/target-family component gate — 2026-11-14

The next evaluator seam is now implemented but deliberately unactivated. The
existing v7 scope caps one candidate per source session inside each stratum, and
the E92 family audit collapses line fragments to canonical source families.
Neither alone guarantees that one query session or one selected target family
cannot cross later train/holdout-style partitions.

`python/scbe/prime_token_query_family_components.py` joins accepted query hashes
to hashed query-session IDs and reviewer-selected manifest family IDs, constructs
their bipartite connected components, and assigns whole components to neutral
fold names. It never emits query text or raw session IDs, and target metadata
remains evaluator-only. Fewer than three components, an oversized component,
an empty fold, any session/family overlap, an incomplete review, an unknown
suffix, or a broken source/catalog binding fails or reports `UNDERPOWERED`
without splitting a component or lowering the 30-query floor.

The audit and CLI are covered by five adversarial tests; the full tokenizer
suite passes `315 / 315`. This establishes mechanics only. The active v7 chain
still has 4 closed candidates and no labels, so no component receipt, scoring,
training intake, promotion, or partial unfreeze exists yet. Detailed contracts
and hashes are in
`docs/research/PRIME_TOKEN_QUERY_SESSION_FAMILY_COMPONENT_MAP_20261114.md`.

The component gate now also has a fail-closed dormant watcher at
`scripts/tokenizer/watch_prime_query_family_components.py`. It waits for both
the prepared packet and exact-selection audit before resolving the queue,
inventory or labels; hash-pins the component CLI and source-family audit; runs
once through an exclusive pending path; independently replays the input,
component and report hashes; and preserves verified, underpowered and invalid
reports as distinct terminal states. It never maps neutral folds to semantic
train/holdout roles and grants no downstream authority. Nine watcher tests and
the complete `324 / 324` tokenizer suite pass. A real v7 one-shot smoke remained
at `WAITING_FOR_PREPARATION_PACKET` with four candidates and labels unopened;
the committed persistent worker is now active in that same fail-closed waiting
state. Two advancing poll receipts prove liveness only. No labels, component
report, score, training intake, promotion or partial unfreeze has been produced.
