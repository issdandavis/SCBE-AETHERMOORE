# Clay byte-row extension boundary

Status: deferred design boundary; no training, promotion, merge, execution, or
Kaggle authority

## Decision

The active byte-embedding-thaw experiment does **not** add token rows. It tests
the narrower causal question first: can an action-gated, trainable copy of the
existing 256 byte rows carry useful action geometry through the frozen Clay
recurrence while the canonical parent and counting path remain exact?

Only after that three-seed race, its controls, and independent replay close may
a separately named experiment test parameter growth by appending rows.

## Proposed extension shape

Keep the canonical byte table immutable:

```text
B : [256, d]                       exact byte identities
E_g : [m_g, d]                     extension rows for generation g
address = (family, generation, row, lane)
```

`E_g` is a copy-on-write extension bank, not a replacement for `B`. A new row
must retain its source token, parent byte path, generation, lane, and training
receipt. Multiple deterministic wafer or quine views may initialize routing
coordinates for a row, but they remain correlated views of the same source and
do not count as additional observations or Shannon information.

The useful GPU-wafer analogy is allocation: when a declared region is full, an
extension bank adds addressable capacity without moving or renumbering the
canonical 256 rows. The implementation should share the immutable base and
store only extension values and lineage deltas.

## Required growth test

A future row-growth campaign must compare, at equal trainable parameter count:

1. lineage-addressed wafer/quine initialization;
2. random-fixed row coordinates with trainable values;
3. one-to-one shuffled token-to-row binding;
4. the no-extension byte-thaw winner; and
5. the frozen/no-intervention parent.

It must use source-disjoint train and holdout families, three or more seeds,
finite-sample uncertainty, exact counting retention, base-tensor hashes, row
occupancy and usage receipts, and an independent prediction replay. Merely
allocating distinct rows or reconstructing them exactly is capacity evidence,
not learned benefit.

## Activation order

```text
frozen baseline completes
  -> independent replay closes
  -> 256-row byte-thaw race runs
  -> thaw beats both matched controls and preserves parent behavior
  -> separate byte-row extension preregistration may open
```

If the thaw does not clear its gates, appended rows are not the next fix. The
bottleneck must be localized again before adding width.

## Kaggle boundary

The Google VQCC competition scores verified circuit cost. Byte extensions,
wafer reprints, quines, token geometry, or clustering belong in that path only
if they produce a concrete `.kmb`/`.kmx` candidate that passes the kickmix
verifier and lowers the task's measured qubit/Toffoli objective. They are not a
competition improvement by architectural analogy alone.
