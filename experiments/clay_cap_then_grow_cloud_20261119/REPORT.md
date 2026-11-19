# Clay cloud-native cap-then-grow campaign

The preregistered arithmetic code-out experiment is running as Kaggle kernel
`issacizrealdavis/clay-cap-then-grow-codeout-20261119`, version 1. It is private,
offline, CPU-only, and has no weight-promotion or competition-submission authority.

The unchanged 25 GiB storage gate was measured inside Kaggle before any dataset or
model was loaded. `/kaggle/working` failed at 19.5024 GiB free. The separate writable
`/tmp` device passed with 2,514.5836 GiB free, so runtime extraction and checkpoints
are bound there. Only small status and final evidence files use `/kaggle/working`.

The launch is pinned to preregistration commit `a546670c7`, launch-source commit
`ff1b14bef`, dataset version 1, archive `21ee4359...`, and all three sealed parent
hashes. Local no-training validation confirmed 1,534 training rows, 1,509 held-out
rows, a 140,820-parameter adapter/head, ordinary cross-entropy, compile-clean
independent replay, and frozen-core identity after a two-update mechanics smoke.

Observed cloud progress is candidate seed 20261134 at steps 500, 1000, and 1500.
This proves active training, not efficacy. Final claims remain gated on all three
seeds, target-shuffle and zero-update controls, 2x pooled-SD plus 3/3 seed wins,
nonzero per-operation accuracy, exact counting retention, bit-identical frozen
tensors, and independent full-held-out replay.
