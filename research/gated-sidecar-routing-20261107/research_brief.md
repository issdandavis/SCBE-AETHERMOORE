# Gated sidecar junctions for preserved-skill growth

Date: 2026-11-07  
Scope: foundational through 2024 primary literature; global, architecture-level
research.  
Authority: design research only; no model promotion or serving change.

## Research question

Which activation and routing mechanisms best implement a frozen main highway,
specialist exits, optional re-entry, and a parallel underpass while preserving
existing Clay weights and keeping commercial behavior auditable?

## Evidence-backed findings

1. **Carry/transform gates are the closest literal highway junction.** Highway
   Networks combine an identity/carry path with a learned transformed path and
   were designed to preserve information flow through depth. The follow-up
   experiments trained networks hundreds of layers deep. This supports a
   default-carry junction, but it does not by itself prove skill retention in
   Clay. [Highway Networks (2015)](https://arxiv.org/abs/1505.00387),
   [Training Very Deep Networks (2015)](https://arxiv.org/abs/1507.06228).

2. **Frozen adapters are the strongest literature match for keeping old weights.**
   Houlsby et al. freeze the original network and add small, near-identity
   task-specific modules. AdapterFusion separately learns task adapters and then
   composes their outputs without destructively retraining the backbone.
   [Parameter-Efficient Transfer Learning for NLP (2019)](https://proceedings.mlr.press/v97/houlsby19a.html),
   [AdapterFusion (2021)](https://aclanthology.org/2021.eacl-main.39/).

3. **Sparse expert routing adds capacity, but creates load and stability
   problems.** The original sparsely gated MoE uses a learned gate to activate a
   small expert subset. Switch simplifies this to top-1 routing; ST-MoE focuses
   explicitly on instability and transfer. Expert Choice reverses assignment so
   experts select fixed-capacity token buckets, improving load balance but
   allowing a token to receive a variable number of experts. These are useful
   patterns, not evidence that a laptop-scale Clay MoE is commercially ready.
   [Sparsely-Gated MoE (2017)](https://arxiv.org/abs/1701.06538),
   [Switch Transformer (2022)](https://www.jmlr.org/papers/v23/21-0998.html),
   [ST-MoE (2022)](https://arxiv.org/abs/2202.08906),
   [Expert Choice Routing (2022)](https://arxiv.org/abs/2202.09368).

4. **Hard routing can be learned, but the relaxation is an approximation.**
   Gumbel-Softmax and the Concrete distribution replace a non-differentiable
   categorical decision with a temperature-controlled continuous relaxation.
   This makes exit selection trainable with backpropagation, but introduces
   temperature, stochasticity, and train/deploy mismatch that a commercial gate
   must measure. [Gumbel-Softmax (2017)](https://openreview.net/forum?id=rkE3y85ee),
   [Concrete distribution (2017)](https://arxiv.org/abs/1611.00712).

5. **Dynamic depth is a separate decision from expert identity.** Adaptive
   Computation Time learns how long to process an input. Mixture-of-Depths uses
   top-k token selection with a fixed total compute budget, making aggregate
   cost predictable while token identities vary. LayerSkip trains intermediate
   exits and can verify an early draft with later layers. These mechanisms map
   to “continue on the highway” versus “exit now,” but they do not supply a new
   specialist skill. [ACT (2016)](https://arxiv.org/abs/1603.08983),
   [Mixture-of-Depths (2024)](https://arxiv.org/abs/2404.02258),
   [LayerSkip (2024)](https://arxiv.org/abs/2404.16710).

6. **Activation gating and route gating should not be conflated.** GLU variants
   multiply one projection by an activated second projection inside a block;
   they improve feature flow but do not choose an independently governed
   specialist. A SwiGLU-like block can live inside a sidecar, while the junction
   still needs an explicit route contract. [GLU Variants Improve Transformer
   (2020)](https://arxiv.org/abs/2002.05202).

7. **Recursive module routing is expressive but operationally complex.** Routing
   Networks repeatedly choose among function blocks and include a pass action.
   Their multi-agent reinforcement-learning router demonstrates dynamic
   composition, but adds a moving policy and delayed-credit problem. It is a
   research option, not the first commercial lane.
   [Routing Networks (ICLR 2018)](https://openreview.net/forum?id=ry8dvM-R).

## Local measured evidence

Clay's independently verified three-seed discovery run is more directly relevant
than paper analogy:

- direct-input sidecar coding mean `0.231818`;
- size-matched constant-input null mean `0.039394`;
- no-intervention sidecar mean `0.001515`;
- the direct-input sidecar cleared both strict `2x pooled SD` gates and preserved
  counting exactly for every seed;
- full fine-tuning learned more coding (`0.562121` mean) but did not preserve
  counting.

The separate confirmatory seeds `20261113..20261115` are now independently
verified. The direct-input sidecar mean was again `0.231818`, versus `0.028788`
for the size-matched null and `0.000000` for no intervention. Its mean deltas
of `+0.203030` and `+0.231818` exceeded the corresponding strict `2x pooled SD`
thresholds of `0.117363` and `0.116952`. It preserved each parent counting
coordinate exactly (`0.111111`, `0.240741`, `0.537037`).

The frozen adapter also replicated a smaller but controlled coding shift:
`0.040909`, `0.031818`, and `0.022727` versus three zero baselines, for mean
delta `+0.031818` against threshold `0.012856`, again with exact counting
retention. Full fine-tuning moved farther toward coding (`0.462121` mean) while
the shared counting coordinate shifted from the three parent values to
`0.037037`, `0.074074`, and `0.018519`. This is capability redistribution in a
mutable shared weight state, not deletion: every parent and descendant remains
separately preserved and hash-addressed.

The independent assessor reports `POSITIVE_REPLICATION` without pooling the
discovery and confirmatory seeds. No checkpoint was promoted, merged, averaged,
installed, or served.

### Source-disjoint six-view attachment sequence

Three later Clay diagnostics now bound the hidden-state six-view question on a
36/36 balanced train/development proxy with disjoint works, source IDs, and
sentence hashes. Every arm used three seeds; the frozen parent was preserved;
the sealed test was unavailable; and nothing was promoted.

- **E89 flat attachment:** aligned mean `0.3056` versus activation-only
  `0.5833`. Flat concatenation of 1,536 catalog coordinates overwhelmed the
  useful 512-wide layer-0 signal.
- **E90 default-closed learned gate:** aligned `0.2778` versus activation-only
  `0.6019`. A negative initial gate bias was not a durable safety boundary: the
  source gate reopened to mean `0.5774`, and the routed residual again displaced
  useful carry behavior.
- **E91 staged pressure limit:** aligned, its frozen carry snapshot,
  activation-only, and binding-shuffled all scored `0.5926`. Every capped route
  had zero pressure violations and all activation-only logits were bit-identical
  to their carry snapshots. The equal-budget uncapped arm fell to `0.2685`.

E91 therefore proves a narrower engineering point: a hard residual-norm ceiling
plus frozen-readout fidelity can prevent dislodgement. It does **not** prove that
the six views add capability; aligned and binding-shuffled equality shows no
measured binding benefit on this proxy. The source-type task is not the frozen
prospective v6 retrieval benchmark. That benchmark remains unopened until 30
post-freeze candidates exist, so retrieval and commercial-use claims remain
unproven.

Authoritative Clay receipts:

- E89 matrix `a4754ea1152b81393ab5fdd8ca527d464f12f6dc2be9cf01764747d180e5b76a`;
- E90 matrix `59092f91be91e733d203816790b2b629e0623ab42435eb024f119b9b3bb41a8b`;
- E91 matrix `8274651596b3f5c9bfcc23cfc96ace2607a451659d912db71dbd43b9f8339d45`.

### Frozen false-route development contract

Before implementing any learned gate, the research lane now freezes 54 authored
contract cases in `false_route_benchmark_v1.json`: 30 ordinary prompts with
lexical traps, 12 malformed explicit specialist requests, and 12 valid typed
requests. The zero-parameter evaluator uses trusted envelope fields only; it
does not inspect prompt text. It produced:

- false specialist activation `0/42` on non-specialist cases;
- valid specialist route recall `12/12`;
- exact route decision `54/54`.

This result verifies only that the declared deterministic contract is
implemented consistently. The cases are development-consumed, author-written,
and not a source-disjoint estimate of natural request classification. They may
not be used as training intake or promotion evidence. Exact benchmark and
evaluator hashes are frozen in `FALSE_ROUTE_BENCHMARK_PIN.json`.

## Recommended junction architecture

Use a **frozen highway plus a direct-input underpass**, with default-closed
routing and late fusion. Do not write sidecar activations back into the frozen
recurrent state in the first commercial implementation.

```text
token IDs ---------------------------> frozen core -----------------> core output
    |                                      |
    +--> direct-input sidecar              +--> read-only context tap
             |                                      |
             +--> specialist output <---------------+
                         |
goal/source/provenance --> deterministic gate --> abstain | specialist | late fuse
                                                      |
                                                receipt + metrics
```

The road semantics are explicit:

| Road action | Neural/runtime contract |
|---|---|
| Stay on highway | Use the frozen core output unchanged. |
| Exit to town | Dispatch to one frozen-core specialist with direct token access. |
| Exit and rejoin | Combine at final logits/output only; never mutate core hidden state. |
| Cross over | Project a typed sidecar result into another specialist's declared input schema. |
| Under the bridge | Run retrieval/tool/evidence work in parallel and return an evidence packet, not an activation write. |
| Continue past junction | Gate emits `PASS`; compute and output remain on the core path. |
| Road closed | Gate abstains when provenance, confidence, capacity, or schema checks fail. |

### Gate order

1. **Deterministic eligibility gate:** source kind, prompt grammar, required
   evidence, schema, and specialist availability. This is the commercial safety
   boundary and has zero learned parameters.
2. **Optional calibrated score gate:** a small sigmoid score may rank eligible
   routes, initialized toward carry/closed. It cannot override an ineligible
   route.
3. **Capacity gate:** fixed per-request and per-specialist limits prevent MoE-like
   overload and make latency predictable.
4. **Output gate:** choose core, specialist, or late fusion. Preserve both raw
   outputs in the receipt; never hide a fallback.

For a hidden-state experiment, the bounded highway equation is:

`y = carry * h + route * P(sidecar(tokens, stop_gradient(h)))`

with `carry = 1 - route`, a negative route bias, frozen `h`, and a near-zero or
near-identity projection `P`. This is an experiment only. The first product
surface should dispatch or late-fuse outputs because that leaves the core state
bit-for-bit untouched.

## The “thin atmosphere” for non-promoted weights

Do not discard failed or underpowered runs, and do not average them into the
core. Store each as an addressable specialist candidate with:

- parent and child hashes;
- architecture and tokenizer hashes;
- exact data/split authority;
- capability, retention, false-route, latency, and calibration results;
- gate eligibility contract;
- status `candidate`, `refuted`, `underpowered`, or `promoted`;
- immutable path to weights and receipts.

This is the thin atmosphere: inactive adapters can contribute metadata and route
priors, like a weak static field, while only controlled winners receive traffic.
Their tensors remain separate. Evidence can raise or lower route eligibility;
it cannot silently alter backbone weights.

## Commercial recommendation

Build the first product as a **small governed adapter registry**, not a general
learned MoE:

- one frozen backbone;
- one immutable specialist artifact per capability;
- a zero-parameter eligibility gate with abstention;
- optional top-1 selection among already eligible specialists;
- late output fusion only where a control proves it helps;
- hash-bound receipts, latency budgets, and rollback by specialist ID;
- no automatic promotion, averaging, or deletion.

This gives predictable compute, testable failure boundaries, and sellable
capability packages. A learned router is justified only if it beats the fixed
gate on held-out route accuracy and false activation while preserving every
protected capability.

## Required controlled experiment

Use at least three fixed seeds and keep the current no-promotion authority.

| Arm | Purpose |
|---|---|
| Core/no intervention | Existing behavior and latency baseline. |
| Direct-input sidecar + fixed gate | Recommended candidate. |
| Size-matched constant-input sidecar | Proves input identity matters. |
| Shuffled source/view binding | Proves six-view binding matters. |
| Learned sigmoid gate | Tests whether a learned soft route beats the fixed gate. |
| Hard/Gumbel route | Tests discrete dispatch only if soft routing clears first. |
| Full fine-tune | Dislodgement reference, never the default growth path. |

Success requires capability improvement over both no intervention and the
size-matched null by more than `2x pooled SD`, exact protected-skill retention,
source-disjoint holdout, lower false-route rate than the declared commercial
ceiling, and measured latency/memory within budget. A learned gate must also beat
the fixed zero-parameter gate. The six-view v6 catalog cannot enter this test
until its prospective pool reaches the frozen 30-query minimum.

## Confidence

- High: descriptions of the cited mechanisms and the independently verified
  local discovery plus exact confirmatory replication.
- Medium: the recommendation to prefer deterministic dispatch plus late fusion;
  it is an inference from the literature, local hardware, and Clay's controls.
- Unproven: broad language usefulness, v6 retrieval gain, commercial demand,
  and any production promotion candidate.
