# Explicit-Intent Auxiliary Route Preregistration

Status: design frozen before non-sieve holdout review or candidate scoring; no promotion authority.

## Question

The full six-view ranker regressed against lexical retrieval, while exact-tie and
fixed-band cascades were inert on independent holdouts. The next candidate tests
a narrower claim: an explicit query intent may select one or two relevant
auxiliary views, while lexical retrieval remains the authoritative route.

This is a deterministic external retrieval sidecar. It is not a tokenizer
change, learned gate, neural activation, model-weight update, or serving default.

## Frozen candidate

Lexical retrieval always runs. The query router may add at most two auxiliary
views from `five_w`, `speech`, `atomic`, `prime`, and `source`. A view is eligible
only when the normalized query contains one of its explicit intent markers:

| View | Intent markers |
|---|---|
| `five_w` | `who`, `what`, `when`, `where`, `why`, `how`, `5w`, `five w` |
| `speech` | `grammar`, `syntax`, `noun`, `verb`, `pronoun`, `tense`, `speech function` |
| `atomic` | `atomic`, `tongue`, `braid`, `trit`, `semantic element`, `sacred tongue` |
| `prime` | `prime`, `sieve`, `factor`, `composite`, `eratosthenes`, `modulus`, `residue` |
| `source` | `source`, `file`, `code`, `paper`, `research`, `documentation`, `publish`, `book` |

Markers use case-folded Unicode word boundaries; phrases use collapsed
whitespace. Count distinct matched markers per view. Select the two views with
the highest positive counts, breaking ties in the table order above. With no
match, select no auxiliary view. The router does not inspect catalog results,
relevance labels, source paths, or model output.

Source-kind evidence is inferred only from explicit source markers: `code`
selects catalog kind `code`; `paper` or `research` selects `academic`; and
`documentation`, `publish`, or `book` selects `documentation`. The generic
markers `source` and `file` select the view but add no guessed source kind.

Run lexical-only and a routed search over the same complete section set. The
routed search ablates every non-selected auxiliary view. Partition lexical order
into contiguous bands anchored to each band's strongest lexical score using the
already-frozen width `0.005`. Reorder only within a band by routed-search score,
then stable section ID. Emit the lexical score unchanged.

The implementation revision will be `six-view-explicit-route-v1`. Marker lists,
view cap, precedence, band width, topology steps (`2`), and result limit (`20`)
are frozen by this document and may not be tuned on the holdout.

## Controls

Evaluate the candidate against all of the following on identical queries:

1. lexical-only retrieval;
2. no-intervention retrieval;
3. the rejected full six-view field as a diagnostic reference;
4. the rejected ungated lexical-band field at width `0.005` as a diagnostic
   reference;
5. a size-matched route-null control that rotates every selected auxiliary view
   by one position through the five-view table while preserving route count and
   leaving source-kind inference unchanged;
6. one-to-one shuffled feature binding with seeds `11`, `29`, and `47` while
   preserving the candidate's selected views.

The route-null control separates explicit view identity from the mere act of
using fewer views. Shuffled binding separates valid feature membership from
route selection. Neither control may change lexical order or the band partition.

## Sealed multi-source holdout protocol

Use the existing canonical direct-speech review queue bound by SHA-256
`30c84e28a807e6df06c158cbcde044032ee850781e15c2a91f7deb4f73ecd91d`.
Exclude every query hash consumed by the mechanics, independent-request,
lexical-first, or sieve-stratum holdouts.

Before reading candidate text, create one deterministic review scope:

- one exclusive `five_w` candidate per hashed source session, ordered by query
  SHA-256;
- the first 20 exclusive `publication` candidates by query SHA-256;
- the first 17 exclusive `tongue_braid` candidates by query SHA-256;
- the first 20 exclusive `source_research` candidates by query SHA-256.

Keep at most one candidate per hashed source session within each stratum. If a
collision occurs, take the next query by SHA-256. Review every selected candidate
and record accept/reject plus exactly one catalog source suffix for each accepted
query. Do not run retrieval during selection or review.

Hash-only structural audit amendment: no consumed-query overlap was found in any
stratum, but the exclusive candidates have capacities of 3 unique sessions for
`five_w`, 20 for `publication`, 17 for `tongue_braid`, and 74 for
`source_research`. No query text or retrieval result was opened during that
audit. Preserve the session cap, take the lower query hash on collisions, and
use counts 3, 20, 17, and 20 respectively, yielding 60 total scoped candidates.
Do not weaken source-session independence merely to retain the original counts.

The benchmark is admissible only with at least 30 accepted queries, at least
three topic strata, at least six distinct relevant catalog sources, and no one
relevant source exceeding 40 percent of accepted labels. Otherwise stop with
`INSUFFICIENT_CROSS_SOURCE_HOLDOUT` and do not score.

Private query text, source-session hashes, and labels stay in the timestamped
runtime directory. Git may contain only code, tests, this protocol, aggregate
counts, and content hashes.

## Success gate

Recompute reciprocal rank per query and report both micro MRR and macro MRR over
relevant catalog sources. The candidate must exceed lexical-only,
no-intervention, route-null, and every shuffled-binding seed by more than two
pooled sample standard deviations on micro reciprocal rank. It must also exceed
lexical-only on macro-source MRR, improve at least three relevant sources, and
harm no relevant source by more than `0.05` mean reciprocal rank.

Anything else is `NO_GAIN` or `UNDERPOWERED`. A pass authorizes only another
controlled experiment; it cannot modify a tokenizer, probability lookup,
serving pointer, package default, deployment, or neural checkpoint.

## Budget and stop conditions

- CPU-only, less than 100 MiB new runtime output, and no network fetch.
- Refuse catalog, queue-binding, implementation, or benchmark hash drift.
- Refuse output paths that already exist or labels not bound to the exact review
  scope.
- Stop on query-hash overlap, catalog-source leakage, fewer than three shuffled
  seeds, failed width-zero parity, or any attempt to write model weights.

The failed and inert candidates remain preserved as evidence. This experiment
adds a thinner routed atmosphere above lexical retrieval; it does not discard or
overwrite earlier catalog views.
