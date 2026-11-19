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

This proves that the controlled run is advancing. Three completed seeds and
both controls are still required before any efficacy statement.
