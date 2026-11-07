# Lexical-Band Auxiliary Cascade Discovery Protocol

Status: preregistered before implementation or scoring; no promotion authority.

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
