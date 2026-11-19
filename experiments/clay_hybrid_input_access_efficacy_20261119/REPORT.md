# Clay hybrid input-access packet

Date: 2026-11-19

Status: staged locally for independent breaker review. Nothing was uploaded,
launched, published, merged, or promoted.

## Executable architecture

The candidate keeps a 49,379-scalar downstream adapter and adds a 38,173-scalar
causal reader over the 269 action-input IDs that actually occur. The unchanged
53,268-scalar action head makes the total exactly 140,820, matching the ordinary
downstream-only control.

The raw residual projection and downstream adapter projection start at zero.
All three pinned parents therefore produced bit-identical candidate/control
action logits at initialization. On regenerated, hash-pinned training rows,
both arms had 140,820/140,820 gradient-reachable and 140,820/140,820
deterministically changeable scalars for every seed. Action IDs 3, 10-14, and 18
are absent from the training alphabet and fail closed in the candidate action
path; the frozen counting path bypasses this remap.

## Storage and recovery

Training is staged for a scratch root whose exact filesystem must have at least
26 GiB free at launch. The wrapper checks a hard 25 GiB runtime floor at every
checkpoint event. Durable output is measured separately and must have at least
1 GiB free before a copy. Checkpoint slots are hash-copied before `latest.json`,
and recovery validates exact byte counts, hashes, file counts, and inventories.

The wrapper defaults to scratch under `/tmp` and durable output under
`/kaggle/working`, but neither path is trusted by name: their actual existing
filesystem anchors and free bytes are measured before execution.

## Sealed packet

- Source commit: `20e9d8f498c468f327ff38050e13094be674d973`
- Archive: `69c0da60...9fc8` (8,717,346 bytes)
- Descriptor: `ed344dfe...8218`
- Packet manifest: `6c612a40...4b32`
- Campaign: `ed0d1f29...e4c`
- Preregistration: `b5de5a9c...656b`
- Rendered runner: `26133f46...838e`
- Inventory: 327 files

Two independent neutral-suffix extractions reverified the same manifest and all
327 files. Extracted-packet code regenerated dataset `7460665c...0041`, vocab
276, compact alphabet 269, all parent lineages, all parameter/effective-capacity
counts, and the bit-identical initial probes across all three seeds.

Focused evidence: 26 pytest cases passed and Ruff passed. The exact external
packet is at
`C:\dev\_kaggle_stage\clay-hybrid-input-access-efficacy-20261119-v1`.

## Gate

Upload and execution remain closed until MainLane independently audits the exact
packet bytes and reports a breaker pass. Even a completed cloud result would be
measurement-only: promotion still requires both preregistered controls, both
metrics over 2 pooled standard deviations, all four finite paired gates,
retention, exact-capacity checks, and independent replay.
