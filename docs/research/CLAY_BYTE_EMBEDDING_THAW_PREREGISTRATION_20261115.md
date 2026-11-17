# Clay action-gated byte-embedding thaw preregistration

Status: **prepared successor; do not start until the frozen baseline is
complete and the 25 GiB storage admission gate is open**

## Prior evidence

The source-disjoint frozen-multiview campaign remains the baseline and must not
be modified in place.  A read-only transport probe regenerated its admitted
dataset (`7460665c...`) and measured the following held-diagonal accuracies:

| representation | static ridge | multiview ridge |
| --- | ---: | ---: |
| canonical 37-value state | 0.633333 | 0.836667 |
| frozen GRU terminal carrier, seed 20261134 | 0.208667 | 0.215333 |
| frozen GRU terminal carrier, seed 20261135 | 0.224000 | 0.210667 |

The raw action geometry is useful, but the frozen counting recurrence reduces
it to approximately chance before the downstream adapter receives it.  This is
an input-transport bottleneck, not evidence that a wider output adapter is
needed.

## Intervention

For action prompts only, make a trainable shadow copy of the 256 private-use
byte embedding rows and feed those rows into the otherwise frozen GRU.  The
counting path always reads the original embedding table.  The original parent,
all non-byte embeddings, both GRU layers, and the counting head remain frozen.

This is a bounded partial thaw, not a full fine-tune.  It adds 16,384
input-facing scalars and retains the existing action adapter and head.

## Arms

All learned arms use the same three parent seeds (`20261134`, `20261135`,
`20261136`), update count, batch size, optimizer, and learning rate.

1. `byte_thaw_multiview` — primary; stable byte identity and all three legal
   training views.
2. `byte_thaw_static` — same parameters, one repeated cardinal view.
3. `byte_thaw_sample_shuffled` — same parameters and multiview examples, but a
   deterministic per-sample byte permutation removes stable byte identity.
4. `frozen_adapter_multiview` — imported no-thaw baseline from the completed
   frozen campaign.
5. `no_intervention_adapter` — imported untouched-parent baseline.

The shuffled arm is the parameter-matched capacity control.  It can learn, but
the same byte does not retain one meaning across samples.

## Fixed budget and data

- exact admitted source-disjoint dataset and vocabulary from the baseline;
- 18,000 updates per learned arm;
- batch 128;
- Adam learning rate 0.002;
- checkpoint every 500 updates;
- one CPU process with two threads unless a compatible cloud runner is used;
- no e-means clustering inside this causal test.

e-means remains a later candidate for large token/weight catalog clustering.
It is not evidence for this intervention and is not part of the promotion gate.

## Required measurements

- held-diagonal accuracy and macro-F1;
- paired wins/losses and exact two-sided sign-test probability;
- per-action and per-sector accuracy;
- counting retention;
- changed thaw-row count and weight-effect receipt;
- bit-identical original embedding, GRU, and counting-head tensors;
- source, parent, dataset, checkpoint, and prediction hashes;
- independent replay from the retained model state.

## Gate

The primary arm clears only if, across all three seeds, it beats both
`frozen_adapter_multiview` and `byte_thaw_sample_shuffled` by more than two
pooled standard deviations on accuracy and macro-F1, wins the paired finite
uncertainty test, changes at least one thawed byte row, and preserves counting
exactly.  Static-view results are reported as a view-ablation and may not be
silently substituted for the primary comparison.

Failure is informative and remains `NO_PROMOTION`.  No checkpoint gains tool
execution authority from this experiment.
