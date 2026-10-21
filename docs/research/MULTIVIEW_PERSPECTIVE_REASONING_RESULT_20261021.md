# Six-tongue multiview reasoning result

Date: 2026-10-21
Runner: `scripts/experiments/multiview_perspective_reasoning.py`
Receipt: `artifacts/multiview_perspective_reasoning_20261021/RESULTS.json`

## What was tested

The test keeps three ideas separate:

1. a byte is conserved exactly across six bijective tongue encodings;
2. six evidence lenses can reach different partial conclusions about the same
   event; and
3. learned operations move forward, backward, branch, and roll back through a
   64-state world.

The model does not average the six forms before reading them. They remain six
nodes consumed by four attention heads. The encoder splits each form into a
shared semantic core and a lane residual:

```mermaid
flowchart LR
    B[Exact byte s] --> T[Six bijective tongue encodings E_k(s)]
    T --> N[Six separate form nodes]
    N --> ENC[Shared encoder]
    ENC --> C[Core c_s,k]
    ENC --> R[Residual r_s,k]
    R --> L[Original-lane receipt]
    C --> A[Four-head attention]
    A --> P[Invariant prototype z_s]
    P --> X[Forward / inverse transition]
    P --> Q[Branch / rollback selection]
    P --> V[Invariant truth]
    C --> LA[Lens-specific attention query]
    LA --> S[Partial stance]
    LA --> W[Disagreement reason]
```

For attention head `h`, the routing surface is the usual scaled dot-product
field:

`A_h(Q,K,V) = softmax((Q W_h^Q)(K W_h^K)^T / sqrt(d_h)) (V W_h^V)`.

The softmax values are the local slopes in the manifold analogy: they determine
which form nodes pull the readout. A later layer receives the resulting vector
and draws a new surface. The model only sees bytes, token surfaces, and binary
features that the architecture exposes; it does not automatically descend into
source code, hex, or hardware state.

## Controls and execution

Seven arms used exactly 33,937 parameters each and ran for 600 updates at seeds
11, 23, and 37. Controls included independently shuffled tongue bindings,
equal-width ordinary numeric features carrying the same byte and lane data, and
fixed random features. The run used the local GTX 1660 Ti and no paid compute.

Preflight passed 1,536 of 1,536 codec round trips. CUDA flash and
memory-efficient attention were disabled in favor of deterministic math
attention. Two same-seed preflight models had the same state hash. A separate
full 600-update replay of aligned seed 11 reproduced every metric and the full
activation snapshot exactly.

The complete 21-run matrix took 465.91 seconds. Its receipt SHA-256 is
`904cc957bb848b1760954694f7f4bcb02fb57a69257e01146f269c1c2ceaa53f`.

## Result

| Measurement, mean of three seeds | aligned + cycle | ordinary control | shuffled control |
|---|---:|---:|---:|
| Identity recovery | 1.000 | 1.000 | 0.995 |
| Reasoning floor | 0.952 | 0.959 | 0.540 |
| Held-out invariant truth | 0.667 | 0.375 | 0.271 |
| Truth on majority traps | 0.750 | 0.333 | 0.222 |
| Held-out lens stance | 0.444 | 0.406 | 0.309 |
| Held-out disagreement reason | 0.139 | 0.181 | 0.188 |
| Minority-view accuracy | 0.627 | 0.381 | 0.317 |
| Original-lane recovery | 1.000 | 1.000 | 1.000 |

The registered tokenizer-specific reasoning gate was **not established**. The
aligned form beat the shuffled binding on the reasoning floor in every seed,
but the mean effect `+0.412` did not exceed the registered `2 pooled SD =
0.477` threshold. Against the stronger ordinary exact-byte control, the mean
effect was `-0.008`. Exact reversible forms therefore helped relative to broken
bindings but did not improve path reasoning over an ordinary lossless encoding.

The cycle objective was also **not established**. The no-cycle relational arm
had a reasoning floor of 0.979 versus 0.952 with cycle training. Forward and
inverse examples already supplied enough structure at this scale; the extra
cycle loss competed with other objectives.

The split residual gate **passed**. Lane recovery was 1.000 with the residual
objective and 0.167 without it, an effect of `+0.833` in every seed. Its mean
reasoning effect was `+0.020`, inside noise, so form provenance was preserved
without a measured reasoning penalty. This is the useful collision-residue
mechanism: shared identity can converge in the core while the originating form
remains recoverable in a separate channel.

## The important failure

The model fit semantic training rows almost perfectly but did not learn the
held-out rule that explains perspective disagreement. At the final update,
aligned-cycle training losses averaged 0.0014 for truth, 0.0040 for stance, and
0.0067 for reason. Held-out disagreement-reason accuracy was 0.139, essentially
the 1/7 output-space chance rate, and all six held-out stances were jointly
correct for only 0.021 of events.

The attention heads did move. Aligned base attention had normalized entropy
0.584 and placed an average 0.598 mass on its strongest form node. Lens queries
changed those paths by mean total-variation distance 0.591. Shuffled forms had
nearly the same concentration (entropy 0.602, strongest mass 0.581), however.
Concentrated attention is therefore not evidence that a head learned the omitted
evidence rule. It can be a stable lookup path that memorizes training events.

The architecture needs a factorized semantic transition, analogous to its
successful state transition. Each lens should act on six explicit signed
evidence coordinates through a shared rule, with the omitted coordinate carried
as a typed receipt. The disagreement cause can then be derived from the
invariant and masked evaluations instead of memorized as an unrelated seven-way
label. That is the next controlled arm. It should be compared with an
equal-parameter free MLP and the same ordinary, shuffled, and random feature
controls.

## Secondary signal

The aligned arm scored 0.750 on the twelve held-out majority traps in every
seed. Its paired effects over the ordinary control were `+0.417`, `+0.333`, and
`+0.500` (mean `+0.417`, greater than `2 pooled SD = 0.118`). This metric was
recorded before the run but was not part of the registered tokenizer claim
gate, so it is a promising follow-up rather than a promoted result. A follow-up
must enlarge the trap set and preregister this comparison.

## Decision

Keep the six-form residual and activation receipts for innate traceability.
Keep ordinary exact-byte encoding as a mandatory control. Do not claim a general
reasoning gain from the tongue surfaces yet. Replace the memorized semantic
heads with a shared masked-evidence operator, enlarge the held-out trap world,
and rerun the same three-seed gate before integrating it into Clay.
