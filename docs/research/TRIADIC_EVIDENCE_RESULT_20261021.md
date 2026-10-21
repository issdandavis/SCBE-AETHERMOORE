# Triadic evidence heads and exact-coordinate sidecar

Date: 2026-10-21

## Requested structure

The decision cell has three explicit roles:

- **affirm:** gathers nonnegative evidence for the candidate conclusion;
- **counter:** gathers nonnegative evidence against it; and
- **judge:** sees both sides, their signed margin, total activation, overlap,
  confidence, and ratio before choosing negative, open, or positive.

For contribution `c`, the role pair is

`affirm(c) = softplus(3c)/3`, `counter(c) = softplus(-3c)/3`.

The identity `affirm(c) - counter(c) = c` held within
`1.2e-7` in preflight. Both sides remain partly active near zero, so uncertainty
is represented as overlap instead of being erased.

## First implementation: failed coupling

The first implementation decoded the six signed evidence coordinates from the
same latent core used for identity and reversible transitions. Fifteen runs
(five equal-parameter arms, three seeds, 600 updates) showed gradient
interference:

| aligned arm | reasoning floor | truth | stance | reason | contribution sign |
|---|---:|---:|---:|---:|---:|
| role supervised | 0.699 | 0.708 | 0.580 | 0.319 | 0.753 |
| roles free | 0.995 | 0.729 | 0.549 | 0.306 | 0.618 |

The aligned supervised arm's byte-exact latent decoder averaged only 0.104. One
seed's route floor fell to 0.150. Training labels were nearly fit in the other
seeds, while held-out interpretation stayed weak. All registered gates failed.

This identifies the collision: semantic role gradients and route gradients were
rewriting the same latent coordinates.

## Repair: exact detached coordinate rail

The repair reads each low-bit coordinate directly from all six lossless form
features. Aligned tongue and ordinary exact-byte arms produce six identical
votes per coordinate. Shuffled and random controls retain their disagreement as
fractional values. This receipt is detached from autograd; semantic losses can
update the six evidence scales and judge, but cannot alter the route encoder.

The repaired 15-run matrix produced:

| arm | route floor | truth | stance | reason | minority | vector exact | sign | lane agreement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| aligned + role | 0.932 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| aligned + free | 0.932 | 0.938 | 0.899 | 0.868 | 0.905 | 0.729 | 0.889 | 1.000 |
| ordinary + role | 0.875 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| shuffled + role | 0.727 | 0.583 | 0.319 | 0.507 | 0.286 | 0.000 | 0.427 | 0.029 |
| random + role | 0.926 | 0.521 | 0.361 | 0.486 | 0.444 | 0.000 | 0.312 | 0.021 |

The pre-registered traceability gate passed in every aligned seed. Aligned beat
shuffled on interpretation by `+0.719` with `2 pooled SD = 0.012`, and on the
joint floor by `+0.652` with `2 pooled SD = 0.076`.

The role-supervision superiority gate did not pass because the free model was
perfect in two seeds and failed only one; paired interpretation effects were
`0.000, 0.000, +0.396`. The explicit role targets remove that bad seed, but
three seeds do not establish a stable mean advantage under the registered rule.

The tokenizer-specific interpretation gate also did not pass. Ordinary exact
bytes reached the same perfect semantic scores. This is the correct attribution:
the gain comes from exact coordinates plus gradient isolation. The six tongues
add exact cross-form provenance and an observable lane-consistency check.

## Relative weights

The supervised aligned runs learned evidence-scale vectors proportional to the
hidden target `(3, 2, 2, -2, -1, 1)`. Cosine similarities were 0.999439,
0.999768, and 0.999257. Their absolute scale was about one half because the
judge can absorb a common scale, but the signs and ratios were recovered.

## Architecture decision

Keep two rails:

1. a learned route rail for identity, transitions, branches, and rollback; and
2. an exact detached coordinate rail for evidence, provenance, disagreement,
   and authorization receipts.

Realm-specific reasoning should enter through a typed door, use the triadic
cell, and return to the shared route with a receipt. The next experiment repeats
one shared transition cell over a bounded spiral staircase, trains short loops,
tests longer unseen loops, and compares golden-angle, ordinary periodic, zero,
and shuffled depth schedules.
