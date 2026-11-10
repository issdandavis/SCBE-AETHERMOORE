# Layer-14A Predictive Audio Probe — Controlled Result

Date: 2026-11-10

## Outcome

The source-disjoint campaign completed all 120 preregistered horses: three held-source folds, eight arms, and five seeds. The predictive-trit representation preserved useful causal audio information, but it did not beat every stronger representation and ablation control. Therefore this experiment authorizes neither promotion nor partial unfreezing.

Producer status: `NO_PROMOTION_GATE_FAILED_OR_UNDERPOWERED`.

## Held-source results

| Held source | Predictive-trit balanced accuracy | Cross entropy | Controls beaten | Controls not beaten |
| --- | ---: | ---: | --- | --- |
| tracing code | 0.513694 | 0.947710 | random features, shuffled binding, zero features | no adaptation, no omission, raw current, raw lags |
| tracing lists | 0.557155 | 0.935084 | random features, raw current, shuffled binding, zero features | no adaptation, no omission, raw lags |
| tracing nested loops | 0.514063 | 0.954288 | random features, shuffled binding, zero features | no adaptation, no omission, raw current, raw lags |

Future-perturbation mismatches were zero in all three folds. Existing model, tokenizer, and parent weights were not modified.

## Independent replay

The read-only replay independently reconstructed window scores, arm features, train-only thresholds, normalized inputs, and checkpoint inference for all 120 horses.

- probability mismatches: 0
- substantive prediction mismatches: 0
- metric mismatches: 0
- threshold mismatches: 0
- CPU/GPU argmax tie variances: 11,411, all within the declared probability tolerance
- status: `PASS_READ_ONLY_INFERENCE_REPLAY_NO_PROMOTION`

The tie count is retained instead of hidden. It is concentrated in control outputs whose top classes are equal or numerically indistinguishable. The replay treats a different class index as equivalent only when the saved class is also within `2e-6` of the replay maximum; probability-vector equality remains mandatory.

## Hardware execution

The controlled campaign ran on the local NVIDIA GeForce GTX 1660 Ti with CUDA. The independent replay ran on CPU to provide an implementation and device boundary. This is why numerical argmax ties are recorded separately from probability mismatches.

## Evidence

- Campaign matrix: `C:\dev\clay-training-runs\l14a-predictive-audio-20261110\full-v1\MATRIX_RESULT.json`
  - SHA-256: `2f3a72b5f4a904ab6c20261b3655b1aa094de2834f2636ba572a14959e5d3db6`
- Independent replay: `C:\dev\clay-training-runs\l14a-predictive-audio-20261110\full-v1-independent-replay-v2\REPLAY_RESULT.json`
  - file SHA-256: `a567d3ff86a320e3f5208ca734c88ab708f242aafbb77738d752ec45190e5766`
  - canonical result SHA-256: `d021967c0b418405f83c9531f149a7071aa3213f75da31762dc0ec10ea093c12`

## Decision

This result supports a narrow claim: the Layer-14A predictive-trit sidecar carries more next-window direction information than random, shuffled-binding, and zero-feature controls. It does not establish an advantage over ordinary causal lag features or prove that adaptation and omission channels add value. Do not integrate, promote, or partially unfreeze from this campaign. A future confirmation must use fresh source families and a revised mechanism preregistered before looking at their outcomes.
