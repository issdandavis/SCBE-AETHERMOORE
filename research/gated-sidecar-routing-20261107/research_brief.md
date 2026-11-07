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

The current confirmatory run is separate and unpromoted. Its first provisional
full-fine-tune arm scored coding `0.622727` while counting fell from `0.111111`
to `0.037037`. The aggregate replication and independent verifier are not yet
complete, so that single-seed observation is not a conclusion.

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
  local discovery result.
- Medium: the recommendation to prefer deterministic dispatch plus late fusion;
  it is an inference from the literature, local hardware, and Clay's controls.
- Unproven: broad language usefulness, v6 retrieval gain, commercial demand,
  and any promotion candidate from the running confirmatory experiment.
