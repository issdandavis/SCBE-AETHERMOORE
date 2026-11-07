# Lexical-Band Auxiliary Cascade Discovery Protocol

Status: development selection complete; width `0.005` frozen for a new holdout;
no promotion authority.

## Problem

The full six-view field can move relevant sections, but it harmed more MRR than
it helped on the first independent 31-request set. The lexical-first cascade
then protected every non-tied lexical ordering and was inert on its separate
31-request holdout. A bounded lexical-confidence band is the next deterministic
candidate between those two extremes.

The first independent 31-request benchmark is development data. The later
lexical-first holdout has already been observed and is excluded from candidate
selection and capability claims. A selected candidate requires a third
query-hash-disjoint holdout.

## Candidate family

Run lexical-only and full six-view retrieval over the same complete section set.
Sort by lexical score, then partition the list into contiguous bands. A band is
anchored to its first and therefore strongest lexical score; it includes only
candidates whose lexical score is within the fixed absolute band width of that
anchor. Reorder candidates inside each band by full six-view score and then
stable section ID. Do not chain pairwise-near scores across a wider interval.

Discovery widths are frozen at:

`0.000`, `0.005`, `0.010`, `0.020`, and `0.050`.

Width zero reproduces exact lexical-first behavior. The score remains the
lexical score; auxiliary evidence is an ordering sidecar, not a scalar mixture.

## Development controls and selection rule

Evaluate every width on only the first independent 31-request set against:

- lexical-only retrieval;
- no-intervention retrieval;
- the rejected full six-view field as a reference;
- three one-to-one shuffled auxiliary-binding controls.

A positive-width candidate is eligible only when its development MRR exceeds
both lexical-only and no-intervention, its aligned MRR exceeds the mean shuffled
MRR, and it improves at least as many query outcomes as it harms relative to
lexical-only. Select the eligible width with the highest development MRR;
ties choose the smaller width. If no width is eligible, stop and record
`NO_DISCOVERY_GAIN` without collecting another holdout.

## Holdout gate

Freeze the implementation revision and selected width before collecting or
scoring a third set of at least 30 independently authored requests. Query hashes
must be disjoint from both earlier 31-request sets, and query sources must remain
source-record-disjoint from the catalog. The candidate must beat lexical-only,
no-intervention, and all shuffled-binding runs by more than two pooled sample
standard deviations. Anything else is `NO_GAIN` or `UNDERPOWERED`.

No result from this protocol may modify a tokenizer, probability lookup table,
serving pointer, or neural checkpoint. Runtime outputs use a new immutable
directory; existing receipts and weights are never overwritten.

## Budget and stop conditions

The discovery is CPU-only, uses the existing immutable catalog, writes less than
100 MiB, and should finish within 30 minutes. Stop on catalog-hash drift,
benchmark leakage, an existing output path, fewer than three shuffled controls,
or failure to reproduce width zero as the current lexical-first ranking.

## Development result

Implementation commit `d1c935b2c` predates every result below. All five widths
used the original 31-request independent development benchmark, catalog SHA-256
`0c051ab5c27da8f70fd0d77830994e03bf55cda0224c696d06ac3cedf404b403`,
and shuffled seeds 11, 29, and 47.

| Width | Candidate MRR | Lexical MRR | No-intervention MRR | Shuffled mean MRR | Improved / harmed | Eligible |
|---:|---:|---:|---:|---:|---:|:---:|
| 0.000 | 0.515921 | 0.514308 | 0.510546 | 0.515921 | 1 / 0 | no |
| 0.005 | 0.516015 | 0.514308 | 0.510546 | 0.514946 | 2 / 0 | yes |
| 0.010 | 0.516015 | 0.514308 | 0.510546 | 0.514377 | 2 / 0 | yes |
| 0.020 | 0.515921 | 0.514308 | 0.510546 | 0.516028 | 1 / 0 | no |
| 0.050 | 0.512719 | 0.514308 | 0.510546 | 0.517043 | 3 / 2 | no |

Widths `0.005` and `0.010` tied on candidate MRR. The preregistered tie rule
therefore selects the smaller `0.005` width. This is a discovery qualification,
not a capability pass: the gain over lexical-only is only `0.001707`, and no
two-pooled-SD gate passed. Freeze `0.005` before reviewing the third holdout.

Runtime receipts:

- width 0.000 SHA-256:
  `9503ac56c7aaa478a7d9ec651227c17bb46d1ba8471974be5732b4a101253751`;
- width 0.005 SHA-256:
  `c1a2da513daac46a635122758f587e64d96a07bf45e994901f2d028c241abccf`;
- width 0.010 SHA-256:
  `d46ca1ad332ee4ad69d2eee07622cbedf7967135af34eeeeb42999001b952769`;
- width 0.020 SHA-256:
  `b51e05900735d067fe32b14239976a401f73744f9c33e0bee1bb83e48266c05d`;
- width 0.050 SHA-256:
  `a47774e6717878e9ffbd270b6e0a1688534778504b48388933cda7064cb2d7f7`;
- directory:
  `C:/dev/clay-training-runs/prime-token-catalog-20261106/lexical-band-discovery-20261107/`.

## Third-holdout collection audit

Status: `INSUFFICIENT_AUTHENTIC_QUERIES`; no candidate scoring performed.

Seven pre-November Codex sessions were independently scrubbed after the width
was frozen. The first queue incorrectly admitted retained-source blocks and tool
transcripts as user requests. Commit `c4ed93cda` fixes that parser defect and
adds regression coverage. The invalid 86-candidate queue was not labeled or
scored.

The corrected queue contains seven authentic topic-matched requests. A separate
scan of the available pre-design local Claude sessions produced only one more.
This is below the preregistered 30-query floor, so fabricating relevance labels,
reusing either consumed 31-request set, or treating assistant/tool text as user
queries is forbidden. Width `0.005` remains a development candidate with no
holdout evidence.

Collection receipts:

- scrubbed seven-session source SHA-256:
  `32cc0290e21c8eac25c921c6088bf177d051fc42051991f2dd00f526d004e23f`;
- corrected seven-request queue SHA-256:
  `1cb7d59049d94cedadafa50671dacb41336526ae3033036d3cfaba57f379de74`;
- source runtime:
  `C:/dev/clay-training-runs/prime-token-catalog-20261106/third-holdout-source-20261107/`;
- queue runtime:
  `C:/dev/clay-training-runs/prime-token-catalog-20261106/lexical-band-holdout-20261107/REVIEW_QUEUE_V2.json`.

## Expanded pre-design source audit

Status: `PRIVATE_HOLDOUT_ASSEMBLED_NOT_SCORED`.

The eight-request stop above remains the correct result for the narrowly scanned
current Codex and Claude stores. A separate pre-design asset was then located:
the August 2026 `issac_voice.jsonl` harvest. It contains 6,085 scrubbed user
turns from 1,626 source files and preserves a hashed source-session plus turn
number for every row. It contains user-role direct speech only; assistant
reasoning is stored in a different file and was not read into this benchmark.

The fixed broad topic patterns selected 320 requests across 464 hashed sessions.
The complete 48-request `prime_sieve` stratum was reviewed to avoid selecting
only favorable examples. Thirty-four requests have `dev/loom/clay_sieve.py` as
a genuine catalog-relevant source; fourteen false positives, pasted task
context, or unsupported advanced-number-theory requests were rejected. The
accepted set clears the 30-query floor, has 34 unique query-source URIs, passes
catalog source-disjoint validation, and has zero query-hash overlap with either
consumed 31-request benchmark.

The review-label binding was strengthened before labels were sealed. Labels now
target a canonical SHA-256 of the exact queue, including dataset receipt,
selection policy, source provenance, candidate hashes, and private query text.
The evaluator rejects a mutated queue even when its underlying dataset hash is
unchanged.

Private runtime receipts:

- source dataset SHA-256:
  `d10baf665d25af3991b0cb3f362056be7fab43f098e9b72297e671cf512327bd`;
- canonical queue binding SHA-256:
  `30c84e28a807e6df06c158cbcde044032ee850781e15c2a91f7deb4f73ecd91d`;
- review queue file SHA-256:
  `ca0b1811c063c1478cb1a02adf8a2b3f6675437022b3e32f4313f15647496d80`;
- hash-only review-label file SHA-256:
  `34fc676fccbd8cf12101529e7f68a0081c6d7572ade92e1b39fd2354433719c5`;
- assembled benchmark SHA-256:
  `62ba3c31ccb898c361abf687879188c07408ffc28d46eeb05796e85764f50b6d`;
- runtime directory:
  `C:/dev/clay-training-runs/prime-token-catalog-20261106/lexical-band-holdout-voice-v2-20261107/`.

No candidate retrieval was run while collecting, reviewing, or validating this
set. Width `0.005` remains unproven until the committed evaluator is run once on
this sealed private benchmark against lexical-only, no-intervention, and all
three shuffled-binding controls.
