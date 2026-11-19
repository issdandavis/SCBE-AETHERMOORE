# Stable CE efficacy campaign map

Status date: 2026-11-19

## Question and controls

Measure whether `stable_log1p` improves the frozen-multiview adapter over both
the unchanged `standard` hard-target cross entropy and the immutable
no-intervention parent. This is a bounded measurement only; it cannot promote
or overwrite weights.

- Seeds: `20261134`, `20261135`, `20261136`
- Trained arms: `standard`, `stable_log1p`
- No-intervention arm: pinned parent predictions from the existing baseline
- Matched budget: 2,000 steps, batch 128, checkpoint every 250 steps, CPU
- Only intervention: hard-target cross-entropy mode
- Decision gate: `stable_log1p` must beat both controls by more than two times
  pooled standard deviation on source-disjoint accuracy and macro F1

## Exact lineage

- Stable-CE base: `4acc1e6ff1545662b7f1dc9803adf81e597a06e2`
- Campaign source: `dfc51da6f658038b3b383e76bec8cc96365fb369`
- Baseline manifest SHA-256:
  `7f2516af8ae5a122f357565afad60ab412fdf54e76a3018cd8f1ddbfdb702a97`
- Baseline result SHA-256:
  `c5261ada862a2851db0b1dd7e53835b5ddef22299660921527a249a866361482`
- Dataset manifest SHA-256:
  `7460665cbb718097438227c452f1915e88bdc5a10ac643122b17908b505d0041`
- Packet archive SHA-256:
  `64dd23bacb92a162d34c1b48946f804e0a8579bfdaa13e6384876afd22b3d7af`
- Packet descriptor SHA-256:
  `e1eca31313be90bda53fc77770df2ec02393bee0826c7d91822ad3c4300f3a47`
- Packet manifest SHA-256:
  `9d2cd300d8508a888edf9f7b09171dd87829ece99768f79815a5f7cc9600e887`

## Execution route

Local admission remained closed: live free space was 11.93 GiB against the
unchanged 25 GiB minimum. The existing byte-thaw campaign and watcher were not
modified. The controlled segment was therefore routed to the already
authorized private Kaggle CPU lane:

- Dataset: `issacizrealdavis/clay-stable-ce-efficacy-input-20261119`, version 2
- Kernel: `issacizrealdavis/clay-stable-ce-efficacy-20261119`, version 2
- Visibility: private
- Internet: disabled
- GPU: disabled
- Runtime entry: the Kaggle interpreter via
  `sys.executable -m python.scbe.clay_stable_ce_efficacy_campaign`

Version 1 failed closed before training because the launcher invoked the module
as a file and Python could not resolve the top-level `python` package. No
optimizer step or measurement occurred. Version 2 uses module execution and
passed packet-relative import replay before launch.

## Runtime and recovery gates

The campaign writes atomic checkpoint pointers, `PROGRESS.json`, `STATUS.json`,
and `RESULT.json`. Every checkpoint records its loss mode and refuses a
mismatched resume. Frozen-state identity, finite loss, baseline/source/data
hashes, and the 25 GiB runtime storage minimum are fail-closed. Cloud output is
accepted only after the recovery inventory, result hash, checkpoint hashes, and
model hashes verify.

Two increasing checkpoint counters from one arm were observed through Kaggle's
authenticated live-log stream:

- `standard`, seed `20261134`, step 250, generation 0, checkpoint
  `9d136016d120c68d343cba5a28bb380b3b92d39c69831680792e5f2160aa1381`
- `standard`, seed `20261134`, step 500, generation 1, checkpoint
  `5d9866130973cc2e64a59e553a25d89744d9c754cb9046ed208f14fd94fcc9fd`

This proved that the controlled run was advancing. The kernel subsequently
completed all six trained arms and terminated with Kaggle status `COMPLETE`.

## Independently verified result

The downloaded output is preserved at
`C:\dev\_kaggle_stage\clay-stable-ce-kernel-output-v2-verified`. Independent
replay verified 37 recovery-listed files (68,804,044 bytes), all six model
hashes, both retained checkpoint slots per arm, checkpoint loss-mode identity,
all three pinned parent hashes, and bit-identical frozen cores.

- Campaign result SHA-256:
  `84f17c09c86b098203da01863350174586d2e29632a7bda190b30873c91e2da2`
- Recovery manifest SHA-256:
  `e2e4053acaf337c097d38c3e1fa56ebe4582f101d4f4f70aa053c38d15e517a4`
- Independent verification receipt SHA-256:
  `6e088608ba3af3840be8a5fa9ce7f32bdfb214ae46781d67989059be11cccf7d`

| Loss | Seed | Accuracy | Macro F1 | Final loss | Model SHA-256 prefix |
| --- | ---: | ---: | ---: | ---: | --- |
| standard | 20261134 | 0.214000 | 0.199390 | 0.784998 | `210d00d6` |
| standard | 20261135 | 0.220000 | 0.219126 | 0.400433 | `4dda9764` |
| standard | 20261136 | 0.204667 | 0.199884 | 0.531575 | `84f42ec1` |
| stable_log1p | 20261134 | 0.209333 | 0.201991 | 0.782836 | `c6aed6a4` |
| stable_log1p | 20261135 | 0.215333 | 0.214829 | 0.428444 | `4fe08fa7` |
| stable_log1p | 20261136 | 0.210000 | 0.207293 | 0.519706 | `6a547128` |

Against unchanged standard cross entropy, `stable_log1p` had:

- Accuracy mean 0.211556 versus 0.212889; delta -0.001333 versus a required
  +0.011876 (two pooled SD). Gate: false.
- Macro-F1 mean 0.208037 versus 0.206133; delta +0.001904 versus a required
  +0.018346 (two pooled SD). Gate: false.
- Paired held-out outcomes: 304 wins, 310 losses, 3,886 ties; exact two-sided
  p = 0.840107. Finite-uncertainty gate: false.

Both trained arms beat the immutable no-intervention parent, whose adapter
accuracy and macro F1 were zero. That confirms learning occurred, but it does
not distinguish the loss functions. The preregistered producer gate is
`NOT_MET`; promotion remains `NOT_AUTHORIZED`.

## Separate numerical-fidelity result

The independent FP32-versus-FP64 audit used 4,096 examples, 257 classes, and
margins from 0 through 80. Standard cross entropy rounded 3,172 losses and
target gradients to zero; `stable_log1p` rounded none. Mean absolute target
gradient error was `3.130154e-8` for standard and `2.193952e-9` for stable.
This proves improved numerical fidelity only, not improved training efficacy.

- Reproducer SHA-256:
  `943f211b4d2a4f5047830511b22e763cd6a9c5d8ca6f3d14a372146bd85043c4`
- Numerical receipt SHA-256:
  `5edc10616cb38ac3c4f18c5ce273826559d6c70b68a21b78a2e9195ae906f87d`
