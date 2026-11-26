# Clay byte-embedding thaw independent replay — system map

Status: `IMPLEMENTED_TESTED_HEADLESS_WATCHER_WAITING_FOR_ATOMIC_RESULT`

Date: 2026-11-15

## Capability boundary

Add an independent, final-only inference replay for the running
`byte-embedding-thaw-20261115-v1` measurement. The replay must reconstruct the
source-disjoint data and shuffled-byte control without importing the thaw
producer/model modules, reopen only terminal model artifacts read-only, and
recompute predictions, metrics, retention, frozen-tensor identity, changed
byte rows, and the producer gate. It grants no execution, merge, promotion, or
partial-unfreeze authority.

The current producer remains the sole checkpoint writer. The new watcher must
not open partial checkpoints or launch another trainer.

## Inventory receipt

- Immutable inventory:
  `docs/research/CLAY_BYTE_EMBEDDING_THAW_REPLAY_SYSTEM_INVENTORY_20261115.json`
- SHA-256:
  `ff21d060aaa7d17864b264f15972b2f92eafc314c2d520112aa354da6075af60`
- Roots: source worktree, sealed frozen baseline run, active thaw run.

## Existing nodes

| node | exact authority | status | output / consumer |
| --- | --- | --- | --- |
| Frozen campaign manifest | `C:\dev\clay-training-runs\frozen-multiview-adapter-replication-20261114-v1\RUN_MANIFEST.json` | sealed | parent identities, config, source hashes, dataset manifest |
| Frozen atomic result | same run, `RESULT.json`, SHA `c5261ada862a2851db0b1dd7e53835b5ddef22299660921527a249a866361482` | complete; producer gate `NOT_MET` | imported baseline/control rows |
| Frozen independent replay | same run, `INDEPENDENT_REPLAY.json`, SHA `f434e8cdfc49c43079997a4bc665c0029f0fa300129d9483f41ca7ce4b7c4bcf` | exact PASS, no promotion | mandatory predecessor authority |
| Thaw producer | `python/scbe/clay_byte_embedding_thaw_campaign.py`, SHA `41ae605fe8a72df2bc24c6a55a43eb30a7a93e324838dd3b731cf1f8b5a4d956` | active writer | nine terminal `MODEL.pt` artifacts, per-horse results, atomic aggregate |
| Thaw model | `python/scbe/clay_byte_embedding_thaw.py`, SHA `1404b980af543e1a9dcb032f1807dca225eee57e80cb776c34f39831917c0577` | producer implementation only | action-only shadow rows and deterministic sample-local shuffle |
| Thaw manifest | `C:\dev\clay-training-runs\byte-embedding-thaw-20261115-v1\RUN_MANIFEST.json`, SHA `6bb0fd276c1d2d9c309dc9e04ea9fb4d9aaf84aab62b2060c166059c1da492cc` | sealed at launch | pins source, parents, dataset, config, producer and preregistration |
| Active thaw lineage | same run, `horses/byte_thaw_multiview-seed-20261134/checkpoints/latest.json` | advancing; partial | producer resume only; forbidden to replay watcher |
| Frozen replay template | `python/scbe/clay_frozen_multiview_replay.py`, SHA `48c2c171c315e8354ed13018885285a73d65ac65948282dce10795e45b781ec1` | reusable arithmetic pattern | independent dataset/model/metric code |
| Final-only watcher template | `python/scbe/clay_frozen_multiview_replay_watch.py`, SHA `a7d021e0d29c934a76c44e9154b7aa10c9af42ee47f0590d60b7c3affc249c3b` | reusable state machine | existence-only wait, one-shot replay, stale receipt review |

## Required data flow

```text
sealed action authorities + frozen manifest
  -> independent source-disjoint dataset reconstruction
  -> independently reconstructed static/multiview/holdout rows
  -> deterministic sample-local shuffled rows (seed 20261115)
  -> separate ReplayByteThawModel
  -> terminal thaw MODEL.pt files opened read-only
  -> per-example predictions + canonical replay ledger
  -> independent metrics/comparisons/gate + tensor audits
  -> atomic INDEPENDENT_REPLAY.json
  -> final-only watcher status
```

The model-input edge carries prompt/token data only. Labels remain evaluator
targets. The shuffled view preserves each sample's byte marginal through a
bijective permutation but breaks stable byte identity; it is a matched binding
control, not an independent source family.

## New nodes

1. `python/scbe/clay_byte_embedding_thaw_replay.py`
   - schema: `clay.byte-embedding-thaw-independent-replay.v1`;
   - must not import `clay_byte_embedding_thaw` or
     `clay_byte_embedding_thaw_campaign`;
   - validates baseline manifest/result/replay and thaw manifest/result bindings;
   - rebuilds data through the independent frozen-replay authority path;
   - defines its own byte-thaw model and shuffle implementation;
   - writes `INDEPENDENT_REPLAY_LEDGER.jsonl` before the final receipt;
   - returns `promotion=NONE` and `partial_unfreeze_authorized=false` always.

2. `python/scbe/clay_byte_embedding_thaw_replay_watch.py`
   - schema: `clay.byte-embedding-thaw-replay-watch.v1`;
   - polls only for the atomic thaw `RESULT.json`;
   - never enumerates or opens partial horse checkpoints;
   - runs replay once, binds verifier/result/ledger hashes, and preserves stale
     receipts for review.

3. Focused tests for independent-model parity, source/import separation,
   shuffled-prompt determinism, tensor tampering, ledger uniqueness, result
   binding, stale receipts, and watcher one-shot behavior.

4. Successor-gate regression:
   - baseline result absent -> `WAITING_FOR_FROZEN_BASELINE`;
   - baseline result present but replay absent/unbound/failing ->
     `WAITING_FOR_BASELINE_INDEPENDENT_REPLAY` or fail-closed review;
   - storage must satisfy `floor + peak_write_reserve + recovery_margin`;
   - exact threshold opens; one byte below stays closed.

## Invariants and schemas

- Three seeds and three learned arms are fixed by the thaw manifest.
- Imported controls are `frozen_adapter_multiview` and
  `no_intervention_adapter` from the sealed baseline.
- Candidate state keys equal parent keys plus `thawed_byte_rows` only.
- `e.*`, `g.*`, and `count_head.*` are bit-identical to each seed's parent.
- Trainable-vector order is adapter, adapter head, then thaw rows.
- Every terminal model hash must match its horse result before load.
- Ledger key is `(arm, seed, sample_id)` and must be unique and canonically
  sorted. Rows bind prompt, payload, target, prediction, correctness, sector,
  operation, view, and source family.
- Replay success requires zero prediction/metric/gate/hash/tensor mismatches.
- A passing replay is evidence only; it cannot repair the predecessor's
  `partial_unfreeze=NONE` decision or deploy the shadow rows.

## Controls and evaluator

- No intervention: imported `no_intervention_adapter`.
- Frozen learned baseline: imported `frozen_adapter_multiview`.
- Parameter-matched binding control: `byte_thaw_sample_shuffled`.
- View ablation: `byte_thaw_static`.
- Primary: `byte_thaw_multiview`.
- Metrics: held-diagonal accuracy, macro-F1, paired exact sign test, per-action
  and per-sector accuracy, counting retention, changed-row count, and frozen
  tensor identity.

## Resource and rollback envelope

- Replay is local CPU, read-only over model artifacts, with one atomic JSONL
  ledger and one atomic JSON receipt.
- The producer owns all checkpoints; replay owns only its ledger, replay
  receipt, and watcher status.
- A failed or stale replay is preserved for review and never overwritten.
- Rollback is omission of the new watcher; no producer state or model bytes
  are mutated.

## Stop conditions

- Any source, manifest, producer, parent, model, vocabulary, or replay hash is
  absent or mismatched.
- Baseline independent replay is missing, failing, stale, or unbound.
- Dataset or deterministic shuffle reconstruction differs.
- A model contains unexpected trainable/state keys or a frozen tensor differs.
- Per-example ledger keys duplicate or canonical ordering fails.
- Producer/replay predictions, metrics, comparisons, or gate differ beyond
  the declared tolerance.

## Pre-build decision

The map identifies one missing capability, reuses the existing independent
dataset/evaluator patterns, defines the new schemas and consumers, and keeps
producer/replay/watcher ownership separate. The build may proceed. It must not
launch or read the active run before atomic `RESULT.json` appears.

## Post-build evidence

The independent replay and final-only watcher are implemented and active only
at the file-existence boundary:

- replay verifier: `python/scbe/clay_byte_embedding_thaw_replay.py`, SHA-256
  `9b3bc0310e1d011d68a87f2bc3101a9bddc0dd7121822e38809f1f7d24585de8`;
- watcher: `python/scbe/clay_byte_embedding_thaw_replay_watch.py`, SHA-256
  `f0c62912a1aabb809822bceab51f54c9451462566b8c505a31365a81e1dd46b2`;
- replay tests: SHA-256
  `030da7607d9d33e71eff0c9c785034212b5d7d532834e1cfb001b6f2bec36be2`;
- watcher tests: SHA-256
  `d7d8abcde92f7b80a9dd2f59bb979cc547430d92899052842bd3a1e0a7dc3689`;
- 38 focused and integration tests passed; Ruff and `py_compile` passed;
- the real frozen watcher receipt schema is covered, including producer-result,
  replay-receipt, verifier-contract, source-adapter, stable-contract, and
  authority-boundary bindings;
- the long-lived watcher requires the exact replay-verifier SHA-256 and exits
  for review if that source drifts.

The verified hidden launch is recorded at
`C:\dev\clay-training-runs\byte-embedding-thaw-20261115-v1\INDEPENDENT_REPLAY_WATCH_LAUNCH_RECEIPT.json`,
SHA-256
`f5352a30fbabdaa54f4f742e1c90df68b5d7c9e3149b79b303b5200d92af01c1`.
Its headless config SHA-256 is
`ff3bcaa89ed231f6c3061e0282eb1c95673043b612e9b6c39024c5b55ace8f3a`.
The live state is `WAITING_FOR_ATOMIC_CAMPAIGN_RESULT`; no thaw result, replay,
or replay ledger exists yet. The initial direct-file launch failed before a
watch state because the package import contract requires module execution. The
corrected module launch is live, and neither attempt opened a partial result or
changed the trainer.

The successor gate was also repaired for future campaigns. It now requires a
bound passing baseline replay and storage equal to the floor plus explicit peak
write reserve and recovery margin. The current active campaign retains its
sealed launch manifest and is not retroactively mutated. Successor-gate source
SHA-256 is
`db2d80cfbe4ca76a4dca4ccc0e92a35e2389a65f347e8670a2abc623e20a9cd4`;
its regression-test SHA-256 is
`69c1c0ec63c3c43ef0d19d8ae789c05cbd176e92918de88b71341a854bf4bdc1`.

## Active boundary

The producer remains the only training writer. Until its atomic `RESULT.json`
appears, the watcher may update only its wait status. After the result appears,
it may write the independent ledger, replay receipt, and final watch status.
Every training, execution, merge, promotion, and partial-unfreeze authority
remains `NONE`.

