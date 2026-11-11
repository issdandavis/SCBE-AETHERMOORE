# Prime-token frozen input-access preregistration — 2026-11-11

Authority: `EXPLORATORY_NO_PROMOTION_NO_PARTIAL_UNFREEZE`

## Question

Can a small reader placed before Clay block 0 use the prime-token catalog's
canonical six-view packet better than equal-capacity nonsemantic controls while
the parent model stays frozen?

This is not a text-generation experiment and does not make the tokenizer an
execution authority. The target is bounded route/function behavior: a frozen
parent receives a typed token packet, the reader proposes a route or operation,
and an exact compiler or evaluator checks the result.

## Independent units and split boundary

The six catalog views are correlated deterministic representations of one
canonical occurrence. They count as one observation. Line fragments from one
file and records from one conversation export also remain one source family.

The material split must satisfy both boundaries:

1. catalog train, validation, and final-test lanes are disjoint by conservative
   manifest-bound source family; and
2. authored query lanes are disjoint by closed source-session identity and query
   hash.

Require at least 30 accepted final-test queries, six canonical catalog sources,
three manifest-bound catalog families, and three closed query source sessions.
The largest canonical source may supply at most 40 percent of accepted queries,
and the largest family at most 60 percent. A generated or relabelled row cannot
create another family.

## Arms

All learned arms use the same reader shape, initialization family, optimizer,
sampler, update count, checkpoint cadence, and source split.

- `no_intervention`: frozen parent and canonical lexical input, no reader;
- `lexical_only_reader`: equal-capacity reader over the lexical anchor only;
- `canonical_six_view_reader`: candidate over the canonical correlated packet;
- `random_fixed_reader`: equal-shape deterministic random-fixed packet;
- `shuffled_binding_reader`: one-to-one permutation of view-to-token bindings;
- `single_frame_reader`: equal-width packet held to one named radial/angle frame.

The candidate must beat every control. The lexical-only reader distinguishes a
gain from added trainable capacity; random-fixed and shuffled binding distinguish
semantic binding from width; the single-frame arm tests the claim that multiple
declared frames contribute rather than merely duplicate one coordinate chart.

## Seeds and persistence

Use at least three fresh seeds declared before training. Preserve the exact
parent hash, source manifests, source-session list, reader configuration,
optimizer and sampler state. Every learned `(arm, seed)` has its own two-slot
atomic checkpoint lineage and hash-checked latest pointer. A split
save/load/next-step test must match an uninterrupted path before the material
run starts. Parent and prior descendant weights remain read-only.

## Measures

Keep the raw tri-point vector rather than collapsing it into one score:

- **accuracy:** balanced held-task accuracy and exact packet/route agreement;
- **relationship:** bidirectional token/view binding and source-family transfer;
- **function:** valid operation/compiler agreement and invalid-operation rejection.

Also retain per-example outcomes, ordinary-prompt false activation, frozen-parent
retention/KL, route occupancy, reader connection strengths, sparsity, throughput,
peak memory, checkpoint bytes, and failure counts. Ternary projections do not
replace the raw values or absolute magnitudes.

## Evidence gates

For every primary coordinate, compare the candidate with the no-intervention
baseline and the strongest parameter-matched control. A claimed advantage must
exceed both two pooled seed standard deviations and a preregistered finite-sample
bound. When per-example outcomes exist, use an exact paired test or paired
bootstrap; zero seed variance does not reduce the finite-sample gate to zero.

An independent replay must reconstruct held packets and targets from pinned
sources, reopen checkpoints read-only, and recompute outputs through a separately
checked arithmetic path. Producer-written losses and hashes are consistency
evidence only.

## Release and safety boundary

Material training remains closed until the machine-readable release contract at
`config/training/prime_token_frozen_input_access_release_v1.json` passes and a
human explicitly releases the run. The evaluator may report
`READY_FOR_MANUAL_TRAINING_RELEASE_REVIEW`; it never starts a trainer or changes
authority.

The exact compiler/evaluator remains authoritative. Tool dispatch, merge,
serving, promotion, and partial unfreeze remain `NOT_AUTHORIZED`. A later sector
unfreeze requires its own preregistration, fresh seeds, matched controls,
retention gate, and independent replay. Otherwise the recorded thaw decision is
`NONE`.

## Frozen preflight state

At freeze time the catalog has 36 canonical sources across three conservative
manifest families, but the prospective chain has one open post-freeze source,
zero closed candidates, and no labels or scores. Five headless watcher/evaluator
chains are alive; no weight-update trainer is advancing. The same-shape storage
envelope is open, but data intake, scoring, training, merge, and promotion remain
closed.

