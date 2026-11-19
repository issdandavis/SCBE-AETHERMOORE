# Clay input-access efficacy campaign

Date: 2026-11-19

Cloud kernel: `issacizrealdavis/clay-input-access-efficacy-20261119`

Cloud dataset: `issacizrealdavis/clay-input-access-efficacy-input-20261119`

Authority: private, offline, CPU-only measurement; no promotion or overwrite.

## Outcome

The six trained arms completed, and the recovered model bytes, parent lineage,
holdout predictions, metrics, checkpoint pointers, and decision gates replayed.
The input-access candidate did **not** beat the same-size downstream adapter:

| metric | input access | downstream only | delta | 2x pooled SD | seed wins |
| --- | ---: | ---: | ---: | ---: | ---: |
| accuracy | 0.194444 | 0.218667 | -0.024222 | 0.022457 | 0/3 |
| macro-F1 | 0.189444 | 0.211516 | -0.022072 | 0.025806 | 0/3 |

The paired accuracy comparison had 639 candidate wins, 748 losses, and 3,113
ties across 4,500 matched predictions (`p=0.003717`, wrong direction). The
paired macro-F1 bootstrap estimated `-0.022072`, with one-sided lower bound
`-0.040165`. The candidate and downstream control both beat the immutable
no-intervention action baseline, whose action accuracy and macro-F1 are zero.

Retention passed. Variance, finite-evaluation, and producer gates failed.
Promotion is `NOT_AUTHORIZED`.

## Per-seed measurements

| arm | seed | final loss | accuracy | macro-F1 | counting accuracy | changed / selected |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| downstream | 20261134 | 0.806115 | 0.217333 | 0.200267 | 0.703704 | 140,820 / 140,820 |
| input access | 20261134 | 0.364054 | 0.180667 | 0.180232 | 0.703704 | 138,923 / 140,820 |
| downstream | 20261135 | 0.407126 | 0.226000 | 0.224831 | 0.370370 | 140,820 / 140,820 |
| input access | 20261135 | 0.491379 | 0.209333 | 0.204787 | 0.370370 | 138,923 / 140,820 |
| downstream | 20261136 | 0.498709 | 0.212667 | 0.209451 | 0.407407 | 140,820 / 140,820 |
| input access | 20261136 | 0.462840 | 0.193333 | 0.183313 | 0.407407 | 138,923 / 140,820 |

All six models retained the parent counting score exactly. Frozen-core and all
non-selected tensors were byte-identical. Each arm retained valid two-slot
checkpoints at steps 1,750 and 2,000.

## Admission defect

This run is useful negative evidence, but it is **not a preregistration-compliant
promotion trial**. The 25 GiB disk gate inspected Linux `/` rather than the
filesystem containing `/kaggle/working`:

- campaign manifest recorded 2,514.58 GiB from `/`;
- cloud environment recorded 20,916,408,320 bytes, or 19.4799 GiB, on the
  actual output filesystem;
- required free space was 26,843,545,600 bytes, or 25 GiB.

The run completed without storage loss, but the admission condition was false.
The campaign and wrapper now fail closed on the closest existing output path and
the output filesystem itself. Focused tests include mutation coverage for the
wrong-filesystem case.

## Effective-capacity defect

Both arms selected 140,820 trainable scalars, but the candidate changed only
138,923. The exact 1,897-scalar difference is seven unused embedding rows times
271 dimensions. The action-training inputs never contain shared-vocabulary IDs
for EOS, digits 5-9, or `C`; token zero is activated only by the sidecar anchor.
The structural gradient witness covered every vocabulary ID, but the real
action-training distribution did not. Therefore selected parameter parity did
not become effective parameter parity in this run.

This is a second reason not to use the result for promotion. It is also a design
constraint for the next campaign: size matching must be proven on the actual
training rows, not only on a synthetic all-token witness.

## Error structure and next testable architecture

The raw-input path was not uniformly useless. Its mean accuracy delta versus
the downstream control by target action was:

| target | mean delta | paired wins | paired losses |
| ---: | ---: | ---: | ---: |
| 0 | +0.035556 | 157 | 125 |
| 1 | -0.008889 | 138 | 146 |
| 2 | +0.004444 | 143 | 139 |
| 3 | -0.063333 | 82 | 139 |
| 4 | -0.088889 | 119 | 199 |

This suggests a narrower hypothesis than "replace the downstream adapter with
input access": preserve downstream nonlinear capacity and add raw input as a
zero-gated residual. A mechanically exact 140,820-scalar candidate is:

- action-only compact alphabet: 269 rows, containing every token that occurs in
  the real action-training inputs, including the token-zero anchor;
- compact embedding: `269 x 80`;
- causal GRU: `80 -> 31`;
- zero-initialized input projection: `31 -> 192`;
- retained downstream adapter with bottleneck 101;
- unchanged `192 -> 276` action head.

The budget is exact: 49,379 downstream-adapter scalars + 38,173 input-access
scalars + 53,268 head scalars = 140,820. Both residual projections begin at
zero, so initial logits remain identical to the control. Before any cloud run,
the next preregistration must prove every selected scalar receives gradient on
the actual action-training rows and must use the repaired output-filesystem
storage gate. This is a proposal from observed errors, not a measured gain.

## Provenance

- Kaggle API status: `KernelWorkerStatus.COMPLETE`; dataset status: `ready`.
- Kernel metadata: private, internet disabled, GPU disabled.
- Packet: 326 files; archive SHA-256 `21ee4359...0ef7`.
- Campaign result SHA-256: `a1c4c436...1f688`.
- Recovery manifest SHA-256: `bfdcc771...4f440`.
- Recovery inventory: 40 listed files, 71,995,115 bytes; all hashes verified.
- Independent receipt: `CLOUD_RESULT_VERIFICATION.json`.
- Post-run repair suite: 37 focused tests passed; Ruff passed.

Cross-PyTorch GRU floating-point bytes differ between cloud PyTorch 2.11 and
the local replay runtime. Within each environment, candidate and control
initial logits are bit-identical. Final predictions, metrics, and trainable
state hashes replayed; the input-arm initial-to-final weight-effect hash is
therefore recorded as cloud-origin rather than claimed cross-version exact.
