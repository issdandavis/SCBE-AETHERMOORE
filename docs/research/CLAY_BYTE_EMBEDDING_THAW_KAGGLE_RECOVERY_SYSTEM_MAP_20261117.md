# Clay byte-embedding thaw Kaggle recovery — system map

Status: `SEALED_PRIVATE_OFFLINE_PACKET_LOCAL_REPLAY_PASSED_NOT_UPLOADED`

## Boundary

This recovery closes one failed terminal edge only: the nine byte-thaw horses
already completed `162,000` total training steps, but producer aggregation
overflowed while converting a very large exact paired-test integer to a float.
The committed `Fraction` implementation fixes that arithmetic path.  The
recovery does **not** train, resume, alter, merge, select, promote, upload, or
submit any weight.

The original campaign stays at:

`C:\dev\clay-training-runs\byte-embedding-thaw-20261115-v1`

No `RESULT.json`, replay ledger, model, checkpoint, pointer, status, or watcher
file is written there.  Aggregation and replay operate in a separately named
writable view.

## Exact flow

```text
source run (read-only)
  RUN_MANIFEST + 9 horse RESULT/MODEL
  + 9 latest pointers + 18 slot-a/slot-b checkpoints
               |
baseline authorities (read-only)
  manifest/result/replay/watch
  + 3 parents and both parent checkpoint slots
  + 3 frozen-multiview control models
               |
exact action source + deterministic dataset manifest
               v
self-hashed content packet
               v
writable hardlink/symlink/copy view
               |
aggregate terminal JSON only
               v
independent dataset rebuild + model inference replay
               v
receipt (training/merge/promotion/upload = NONE)
```

## Immutable authorities

| Authority | SHA-256 |
|---|---|
| byte-thaw `RUN_MANIFEST.json` | `6bb0fd276c1d2d9c309dc9e04ea9fb4d9aaf84aab62b2060c166059c1da492cc` |
| config | `583f4362158068a056e52ea8894163989fe810378d60b858e60c4e9a70c0e0d6` |
| dataset manifest | `7460665cbb718097438227c452f1915e88bdc5a10ac643122b17908b505d0041` |
| campaign runner | `41ae605fe8a72df2bc24c6a55a43eb30a7a93e324838dd3b731cf1f8b5a4d956` |
| thaw module | `1404b980af543e1a9dcb032f1807dca225eee57e80cb776c34f39831917c0577` |
| preregistration | `86ae011264baec865f9391aa123a4a5535bf345bb1a512168befd38015ab7f1b` |

Every packet input also has its own byte length and SHA-256 in
`PACKET_MANIFEST.json`.  The manifest is self-bound by hashing canonical JSON
with only its seal fields omitted.  A duplicate path, unsafe path, byte-count
change, file-hash change, descriptor change, or manifest-body change fails
before aggregation.

## Content-addressed release

Packet identity:

`f20ea9183bdef402abe8f317e3cf9eb6fc981b98f953714597e412dd05681a99`

Release root:

`C:\dev\clay-training-runs\byte-embedding-thaw-kaggle-recovery-20261117\clay-byte-thaw-aggregation-replay-f20ea9183bdef402`

The private offline archive is `128,987,702` bytes with SHA-256
`a95ce3768c5ecac5dae57385fd69551e2d3a4145dc56a5f02f2839c34e6236c8`.
Its uncompressed, hash-listed payload is `162,346,430` bytes across `126`
files.  This is `1,896,302` bytes below the previously documented
`130,884,004`-byte Clay Kaggle compatibility archive.  Kaggle metadata declares
CPU, internet off, GPU off, and private visibility.  Nothing was uploaded or
launched remotely.

The packet has no machine-specific absolute path in its entry point.  The
local release directory is only the build output location.  Inside Kaggle the
script discovers the single `.packet` below the mounted input root, extracts
and stages under `/tmp`, and publishes only the four evidence files below
`/kaggle/working/clay-byte-thaw-aggregation-replay`.

## Path neutrality

The exact source manifest is not rewritten.  `PATH_MAP.json` binds each Windows
authority to a packet-relative location:

- campaign run -> `payload/run`;
- frozen baseline -> `payload/baseline`;
- action source ->
  `payload/loom_root/experiments/clay_action_compiler_20261109`;
- action-source dependencies -> `payload/loom_root`;
- runtime source -> `runtime/scbe_repo`.

On Kaggle/Linux, the entry point makes one-component symbolic aliases whose
names are the unchanged Windows strings, then runs from that alias directory.
On Windows, it verifies every native mapped byte against the packet before
using the existing exact authorities.  The staged campaign tree uses hardlinks
when possible, then symlinks, then hash-verified copies.  Output files are
written only to the separately supplied working directory.

## Executable surfaces

- Builder:
  `scripts/research/build_clay_byte_embedding_thaw_kaggle_recovery.py`
- Offline/Kaggle entry point:
  `scripts/research/run_clay_byte_embedding_thaw_kaggle_recovery.py`
- Focused tests:
  `tests/governance/test_clay_byte_embedding_thaw_kaggle_recovery.py`

The entry point exposes only `aggregate` and `all` (aggregate plus independent
replay).  It has no steps, learning rate, optimizer, resume, merge, promotion,
or upload argument.

The release also contains:

- `dataset/dataset-metadata.json`, private dataset metadata;
- `kernel/kernel-metadata.json`, private CPU/internet-off kernel metadata;
- `PRIVATE_KAGGLE_LAUNCH_PLAN.json`, exact create/version/push commands and
  expected atomic outputs.

Those commands require a separate human-authorized action.  The build receipt
records upload and Kaggle-run authority as `NONE`.

## Verification

Focused recovery, thaw, adapter, exact-p, and independent-replay fixtures:

```text
31 passed in 14.79s
Ruff: passed
Flake8: passed
```

These tests cover packet self-hash/tamper rejection, deterministic immutable
run staging, terminal-result-only aggregation, exact paired inference beyond
the float integer range, and bounded independent inference mechanics.  The
full packaged replay receipt is hash-bound in the recovery result document.

The packaged entry point was then executed locally from the private dataset
and kernel bytes, with two CPU threads and `--mode all`:

| Evidence | Result |
|---|---|
| recovery receipt | `PASS_AGGREGATION_AND_INDEPENDENT_REPLAY_NO_TRAINING` |
| independent replay | `PASS_RECOVERY_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION` |
| models independently inferred | `15` |
| prediction mismatches | `0` |
| maximum metric delta | `0.0` |
| aggregate comparison delta | `0.0` |
| aggregate paired delta | `0.0` |
| prediction-ledger rows / unique keys | `22,500 / 22,500` |
| recovered producer gate | `NOT_MET` |
| aggregate `RESULT.json` SHA-256 | `bc807f0dd82dcdf68dc2ba8cc76cef95fee2dc8cb302c72589656b8965062339` |
| independent replay SHA-256 | `6961dc3508f3a0d7011ca11470720fe534512461893d00e54dfed02f15a860cd` |
| ledger SHA-256 | `9dc6fc82d36040ad6de7d97d241f44048ff470d1a750b60446c5dce92ae7a705` |
| published files | `4` |
| published checkpoint/model files | `0` |

The unqualified historical verifier reports four provenance errors, and the
recovery receipt preserves those raw errors.  One is the expected verifier
source-hash change caused by the committed exact-`Fraction` overflow repair;
the packet includes the historical verifier bytes with the exact hash bound by
the closed baseline receipt.  The other three compare a parent
`no_intervention` result document to an aggregate row with a different schema;
the recovery qualification requires exact seed, predictions, metrics,
counting accuracy, and explicit zero-new-parameter semantics.  These
qualifications do not waive any inference, metric, aggregate, or ledger
comparison.  Any such mismatch remains a hard failure.

## Build note

An initial preflight packet correctly failed before replay because its reduced
Python package omitted dependencies loaded by the action compiler.  The sealed
packet above uses the already-proven Loom compatibility dependency list and a
small explicit SCBE import closure.  A later preflight exposed the two
historical/schema provenance comparisons described above.  No model,
checkpoint, prediction, metric, or campaign evidence was changed while
correcting either packaging surface.
