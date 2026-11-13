# Clay frozen multi-view adapter preregistration — 2026-11-13

Status: frozen before outcome-generating training  
Authority: measurement only; no execution, promotion, merge, or partial unfreeze

## Question

Does three-view action-state support improve a real input-visible adapter over
one static view when both sit downstream of the same frozen counting core?

This is not another selector race.  The completed action-data campaigns already
established the narrower distinction that legal multi-view support beats one
static sheet, while random, shuffled, and semantic selectors did not separate.
The present test carries only that supported input distinction into the frozen
adapter that previously showed a small reproducible input-access effect.

## Frozen data design

The read-only Clay authority is
`C:\dev\_wt_clay_action_byte_confirm_20261110\experiments\clay_action_compiler_20261109`.
Its four source files are SHA-256 pinned in the run manifest.

- Three existing training sandboxes are the legal training views.
- The existing diagonal sandbox is the source-disjoint holdout family.
- Every 37-value state is serialized as 148 canonical big-endian float32 bytes.
- Each byte maps bijectively to one token in a fixed 256-token private-use range.
  There is no decimal rendering, learned tokenizer, rounding, or lossy text
  conversion between the state tensor and model input.
- Static and multi-view arms each receive 3,000 unique rows.  Static receives
  all rows from view 0; multi-view receives 1,000 rows from each legal view.
- The held diagonal contains 1,500 unique rows and is never sampled for updates.
- Each train and holdout bank is exactly balanced across the five deterministic
  action labels.  Payload hashes must be disjoint across all banks.
- The exposure ledger records the explicit tensor
  `sector concept x action operation x view x source family x presentations`.

The labels come from Clay's deterministic policy/compiler surface.  The learned
model predicts labels for measurement only; it cannot execute or authorize them.

## Frozen model design

Fresh parent seeds: `20261131`, `20261132`, `20261133`.  A bounded search before
freezing this document found no prior experiment use of those seeds.

Each seed first trains the ordinary two-layer, 192-wide counting core for 28,000
updates.  The embedding, recurrent core, and counting head are then frozen.  All
trained arms use 18,000 updates, batch size 128, Adam at 0.002, deterministic CPU
execution with two threads, and hash-checked two-slot checkpoints.

The four paired arms are:

1. `no_intervention_adapter`: untouched parent adapter path;
2. `frozen_adapter_static`: real hidden stream, static-view rows;
3. `frozen_adapter_multiview`: real hidden stream, three-view rows;
4. `frozen_adapter_null`: same three-view rows and trainable surface, but a
   constant all-ones carrier replaces the token-dependent hidden stream.

The three trained arms begin from the exact same parent adapter weights.  They
have equal trainable parameter counts, update counts, optimizer settings, and
positional sampling schedules.  Only data support or real-versus-null input
differs.

## Preregistered gates

The primary arm is `frozen_adapter_multiview`.  It must beat **all three**
controls.  For each comparison:

- mean held accuracy delta must exceed `2 * pooled SD`;
- mean held macro-F1 delta must exceed `2 * pooled SD`;
- pooled fixed-example predictions must have more paired wins than losses and
  a two-sided exact sign-test `p <= 0.05`.

Additionally:

- all trained arms must have identical trainable parameter counts;
- each trained arm must preserve its parent's counting score exactly;
- every frozen tensor must remain bit-identical;
- every action, sector, and view report remains visible so aggregate accuracy
  cannot hide a zero class or sector;
- exposure manifests and actual presentation counts must replay;
- an independent inference implementation must regenerate the data from pinned
  sources, reopen every checkpoint, and agree before the producer result is
  considered closed.

A producer pass is reported `MET_PENDING_INDEPENDENT_REPLAY`, never promoted.
Failure of any effect-size gate is `NOT_MET`; it is not rewritten as a geometry
or selector win after outcomes are visible.

## Storage and execution boundary

The admission floor remains 25 GiB on the selected output volume.  It may not be
lowered to force a launch.  The local C: lifecycle and cloud archives remain
separate from training authority.  Existing parent weights and prior experiment
trees are never overwritten.

