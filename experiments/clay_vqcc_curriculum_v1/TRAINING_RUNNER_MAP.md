# Clay VQCC training-runner map

This is the smallest evidence-backed path from the sealed intake to a real
controlled Clay experiment. It is a build contract, not training authority.

## Reuse, do not replace

- Parent dataset: `issacizrealdavis/clay-input-access-efficacy-input-20261119`.
- Parent seeds/checkpoints:
  - campaign seed `1618033` -> parent seed `20261134` (`e719ca23...b910`)
  - campaign seed `2718281` -> parent seed `20261135` (`bb4d912d...8438`)
  - campaign seed `3141592` -> parent seed `20261136` (`820f0ed1...6729`)
- Reuse the 140,820-trainable-parameter `InputAccessActionModel` and the
  existing `TwoSlotCheckpoint` model/optimizer/sampler/RNG restore mechanics.
- Standard cross-entropy stays the controlled default. Stable cross-entropy
  recovered arithmetic gradients but did not show a measured efficacy win.

The old input-access and hybrid campaigns both failed their efficacy gates.
Reusing their mechanics does not claim their architectures are better. The new
hypothesis is the source-disjoint VQCC material plus exact controls.

## Required 15 evaluations

For each of three aligned seeds:

1. `candidate`: intact VQCC finding-binding and gate-count material.
2. `equal_parameter`: identical model, initialization, update count, and a
   token/length/task-mixture-matched ordinary control.
3. `shuffled_binding`: identical prompt/occurrence pool with a dataset-wide,
   one-to-one, separately receipted binding permutation.
4. `zero_update`: identical input-access model and initialization, zero updates.
5. `no_intervention`: immutable frozen parent, no sidecar and zero updates.

Only the first three train, so this is nine optimizer runs and fifteen aligned
evaluations, not fifteen unrelated training runs.

## Tokenizer correction implemented

The fixed parent vocabulary has 276 tokens and a complete private-use byte
block at `U+E100..U+E1FF`. It does not contain literal VQCC prose or literal
`A/B/T` targets. `clay_vqcc_byte_codec.py` now maps all prompt/target UTF-8 bytes
into that existing block without expanding the embedding table. Findings allow
only `A/B`; gate count allows `A/B/T`. Literal labels are rejected.

Actual checkpoint vocabulary readback and hash equality remain a release gate;
the local model-load gate is closed by RAM pressure, so this was not faked with
a local checkpoint load.

## Still required before training

1. Execute and independently verify the full mounted-corpus intake.
2. Persist or deterministically reconstruct the exact task comparisons, not
   only their ID hashes.
3. Build the comparison-level findings shuffle and matched ordinary control.
4. Seal task mixing, batch size, learning rate, fixed steps, checkpoint cadence,
   thread/device settings, runtime cap, and all 15 identities after a loader and
   fixed-step runtime smoke.
5. Prove actual trainable name/shape/dtype/byte equality and initial-logit
   equality on real byte-compiled VQCC rows.
6. Add interrupted-vs-continuous bit-exact checkpoint replay.
7. Add strict one-byte generation coverage, task-restricted log-score metrics,
   retention, finite-evaluation bounds, and an independent replay that does not
   trust producer predictions.
8. Obtain separate one-use training authorization. Promotion stays separately
   gated.
