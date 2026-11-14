# Clay frozen multi-view adapter system map — 2026-11-13

## Goal/input/output review

```text
counting rows
  -> embedding + 2-layer GRU + counting head
  -> frozen parent deed (one per fresh seed)

read-only Clay action state (37 float32 values)
  -> exact 148-byte serialization
  -> bijective 256-byte token plane
  -> equal-row support arm
       static view 0 --------------------------+
       three legal views ----------------------+--> frozen core
       three views + constant hidden carrier --+    -> matched adapter/head
       no update ------------------------------+    -> held action predictions
                                                     -> no execution authority

held diagonal source family
  -> fixed prediction ledger
  -> accuracy + macro-F1 + worst-action + per-sector outputs
  -> paired sign tests + 2 pooled-SD controls
  -> independent checkpoint replay
```

## Reused components

| Component | Role | Mutation |
| --- | --- | --- |
| `clay_paired_orbit_training.ClaySourceAdapter` | Pins and reads the existing 37-field state/action generator | read-only |
| `concept_exposure_ledger.py` v2 | Seals concept, operation, view, source, and presentation coordinates | training audit only |
| Frozen counting architecture | Preserves the previously validated input-adapter intervention | new parents; frozen after counting |
| Deterministic Clay label | Evaluation target and future compiler fallback | never learned or overridden |
| Two-slot checkpoint protocol | Resume-safe optimizer, sampler, RNG, model, and exposure state | new output only |

## New executable surfaces

- `python/scbe/clay_frozen_multiview_data.py`: exact byte-token data bridge.
- `python/scbe/clay_frozen_multiview_adapter.py`: controlled producer.
- `python/scbe/clay_frozen_multiview_replay.py`: separately declared model and
  separately implemented byte serialization, row balancing, manifest
  reconstruction, inference replay, and metric/gate comparison. It does not
  import the producer model, producer metrics, or producer data bridge.
- `scripts/research/run_clay_frozen_multiview_adapter.py`: CLI entry point.
- `scripts/research/verify_clay_frozen_multiview_adapter.py`: independent replay
  CLI. `--partial-completed` audits only atomic terminal artifacts and emits
  `PARTIAL_INDEPENDENT_REPLAY.json` without calculating a campaign verdict.
- `scripts/research/watch_clay_frozen_multiview_replay.py`: final-only watcher.
  It polls for the producer's atomic campaign `RESULT.json` without opening
  checkpoints, runs the independent replay once after training terminates,
  preserves stale/unbound receipts for review, and exits with no promotion or
  partial-unfreeze authority.
- `tests/governance/test_clay_frozen_multiview_data.py`: byte and split receipts.
- `tests/governance/test_clay_frozen_multiview_adapter.py`: frozen-surface and
  output-accounting tests.
- `tests/governance/test_clay_frozen_multiview_replay.py`: producer/replay state
  compatibility and independent metric-accounting tests.

## Boundaries

- Byte views are deterministic representations, not extra Shannon information.
- The learned adapter emits a measured proposal only.  It cannot call a tool or
  alter deterministic compiler authority.
- No selector, geometry view, or partial-unfreeze claim is under test.
- No result can promote a checkpoint under this experiment's authority.
- Partial replay is an early corruption/evaluator-drift check only. Missing
  horses remain pending, aggregate comparisons are absent, promotion is
  `NONE`, and partial unfreeze remains false.

## Earlier independent receipt during the first multi-view horse — 2026-11-13

At campaign step 15,000/18,000 for the first multi-view horse, the partial
replay independently reconstructed the exact dataset manifest and vocabulary,
then reopened the completed parent and static-adapter artifacts:

- status: `PASS_PARTIAL_INDEPENDENT_REPLAY_NO_VERDICT`
- terminal artifacts checked: `2 / 12`
- dataset/source/vocabulary receipts: exact match
- prediction mismatches: `0` for both artifacts
- metric and counting deltas: `0.0`
- frozen core: bit-identical for both artifacts
- static held result: accuracy `0.2166666667`, macro-F1 `0.2105417755`

This verifies artifact integrity and evaluator agreement. It does not say the
multi-view intervention wins; ten terminal artifacts and all preregistered
matched-control gates are still outstanding.

## First multi-view terminal output audit — 2026-11-13

The first multi-view horse (`seed=20261131`) is terminal and independently
replayed. The partial receipt now covers `3 / 12` terminal artifacts with zero
prediction, metric, counting, source, vocabulary, or frozen-core mismatches.
The hardened replay receipt at this boundary has SHA-256
`666d90e61f1028f7040645b44d08499813d7ade3b2c02c5620866352852cc6c6`.
Its validator rejects fractional action IDs, correctness flags that disagree
with the actual target/prediction pair, and duplicate held-example keys rather
than truncating or overwriting them.

| Held output | Static | Multi-view | Difference |
| --- | ---: | ---: | ---: |
| Accuracy | 0.216667 | 0.214000 | -0.002667 |
| Macro-F1 | 0.210542 | 0.213184 | +0.002642 |
| Worst-action accuracy | 0.116667 | 0.163333 | +0.046667 |
| Valid action-ID rate | 0.999333 | 1.000000 | +0.000667 |

Multi-view changed `1,155 / 1,500` predictions, but those changes produced 230
fixes and 234 regressions. The exact paired two-sided p-value is `0.889255`, so
the finite-evaluation gate is false. Only 91 examples were correct under both
arms; 254 were wrong with the same output and 691 were wrong with different
outputs. This is a redistribution of behavior, not evidence of a net win.

The redistribution is still diagnostically useful. Static predictions were
concentrated on `push_y_positive` (483 outputs), while multi-view outputs were
more balanced across the five actions (`310, 314, 242, 331, 303`). Multi-view
fixed more than it regressed for `push_x_positive` and `push_y_negative`, but
regressed more for `push_x_negative` and `push_y_positive`. It improved sectors
0 and 6 while losing most heavily in sectors 3 and 4. Full confusion matrices,
per-sector distributions, and error flows are stored in
`PARTIAL_INDEPENDENT_REPLAY.json` rather than inferred from averages.

## First-seed trainable-weight audit — 2026-11-13

The independent replay now reconstructs the parent and candidate trainable
states without the producer's flattening helper. It hashes the named tensors,
measures each adapter group, and compares scalar counts and norms with the
producer receipt. All comparisons passed. The frozen embedding, GRU, and
counting head remain excluded from these numbers and separately bit-identical.

| Trainable movement | Static | Multi-view |
| --- | ---: | ---: |
| Changed scalars | 140,820 / 140,820 | 140,820 / 140,820 |
| Aggregate delta L2 | 109.2001 | 90.5166 |
| Aggregate max absolute delta | 3.5135 | 2.1894 |
| Mean absolute delta | 0.19184 | 0.15078 |
| Delta / initial L2 | 7.7212 | 6.4001 |
| Initial/final cosine | 0.15184 | 0.18307 |

Multi-view moved about 17.1% less in aggregate. Its largest movement remained
the zero-initialized `adapter.up` bridge (`72.7266` versus static `85.6336`).
The clearest reduction was in `adapter_head` (`28.8784` versus `47.9529`, about
39.8% less). This is compatible with the observed redistribution toward more
balanced action outputs, but it does not establish efficiency or a capability
gain: every trainable scalar moved, held accuracy did not improve, and only one
seed is terminal. The remaining seeds and matched null arm decide whether this
pattern is stable.

## Six-artifact replay and first null control — 2026-11-13

After the first null arm and the second seed's parent/static pair became
terminal, independent replay expanded to `6 / 12` expected artifacts. It
reconstructed inference for every terminal model and reported zero prediction,
metric, counting, frozen-core, source, vocabulary, or producer weight-receipt
mismatches. Status remains `PASS_PARTIAL_INDEPENDENT_REPLAY_NO_VERDICT`; the
partial receipt's internal replay SHA-256 is
`ff97b3fd66802b197f6c3adf756e429a16bec6ef638431e96b7ea0645d5e2374`.

The first null control is diagnostically sharp but not a competitive learned
model. All `140,820` trainable scalars changed, with aggregate delta L2
`151.5694`, yet all `1,500 / 1,500` held decodes were invalid action IDs. Most
movement concentrated in `adapter_head` (delta L2 `149.4215`). Multi-view
therefore beats null with 321 paired wins, zero losses, and exact two-sided
`p=4.68e-97`; however, that only proves the real byte input carries usable
action information. It does not establish a multi-view advantage because the
matched static arm remains the relevant non-degenerate control, and seed one
was 230 wins versus 234 losses against static (`p=0.8893`).

The second-seed static arm independently replayed at accuracy `0.217333` and
macro-F1 `0.217502`, close to seed one's `0.216667` and `0.210542`. Its parent
counting accuracy was `0.629630`, versus `0.740741` for seed one, confirming why
the preregistered multi-seed analysis must finish before any inference about
stability. No promotion or partial unfreeze is authorized.

### Cross-experiment location of the current bottleneck

The low held score here does not show that the legal geometry views contain no
learnable action signal. The earlier matched raw-state study used an ordinary
`37 -> 64 -> 64 -> 5` MLP and the same three legal view families. Its
independent-view arm reached held accuracy `0.8923` versus `0.8251` for unique
static data, with positive accuracy and stable-F1 deltas in every one of the
`15 / 15` matched seed/fold comparisons. Those results remain
variance-qualified `NO_SELECTION`, but they establish that a small learner with
direct access to the 37-value state can use the additional view support.

The present partial frozen-descendant evidence is sharply different. The first
multi-view horse reached final training loss `2.64e-5` while held accuracy stayed
at `0.2140`; the second static horse reached final training loss `8.73e-7` while
held accuracy stayed at `0.2173`. The trainable adapter is downstream of the
frozen byte embedding and two-layer GRU, so it can only reorganize distinctions
that survive that recurrence. At this boundary, more optimization can fit the
training source nearly exactly without recovering held-diagonal action
structure.

This is a location diagnosis, not a final causal verdict: only one multi-view
seed is terminal, and the preregistered campaign must finish. If the remaining
seeds repeat the pattern, the supported next seam is the already implemented
causal input-access point before block 0, with the frozen downstream adapter
retained as a matched control. Adding downstream width or relabelling this as a
geometry failure would not follow from the evidence.

The final-only independent replay watcher is committed at `90ac8e73c` and runs
headlessly with launcher PID `24116` and worker PID `3396` (launch identities,
not durable authorities). While the campaign is active it performs only atomic
result-file polling. Once the aggregate result exists, it runs the independent
replay once, seals `INDEPENDENT_REPLAY.json`, and exits. Its immutable launch
receipt is `FINAL_REPLAY_WATCH_LAUNCH_RECEIPT.json` in the run directory.

## What performed the reasoning

The action target is created by the deterministic developmental sandbox sieve:
all five bounded motor actions are executed one step and the highest
action-credit reward wins. That sieve is teacher/label authority only.

The learned inference path is:

```text
37-value state
  -> exact 148-byte token deed
  -> frozen embedding
  -> frozen two-layer GRU
  -> trainable adapter + action head
  -> greedy integer action-ID decode
```

The byte deed is exact at the model boundary: all byte values `0..255` are
reserved as `U+E100 + byte`, all 256 carrier symbols occupy contiguous model
token IDs, and each 148-byte feature deed enters as exactly 148 embedding
tokens. This is a logical one-token-per-byte mapping. It is not a claim that the
intermediate Unicode string is one physical storage byte per token: each
private-use carrier occupies three bytes when encoded as UTF-8. B256 and the
six tongue spellings remain reversible names/views over the same canonical byte
identity and are not silently mixed into this controlled campaign.
The independently reconstructed live table spans model IDs `20..275`, has no
missing byte values, and has table SHA-256
`00f5567f26c8d0c946eea62052100f3bc43f363c8703a5eb2f8fafd8d69cfc3c`.

It does not call a route sieve, centroid index, topology operator, tool, beam,
vote, or triangulation pass at inference. Sector is an evaluation coordinate,
not an input route. Therefore this campaign isolates whether three legal input
views teach the downstream adapter a better boundary; it does not test the
user's answer-space vacuum/triangulation proposal.

## Existing sieve components and the next seam

The connected action worktree already contains the pieces that should be
reused after this campaign rather than rebuilt:

- `centroid_trit_vector_sieve.py`: prime-radial trit/Hydra candidate index;
  mechanics work, but three-candidate winner recall fell to 81.48% on one seed,
  so speed and model benefit remain unproven.
- `topology_sector_action_ab.py`: fixed reflection/push/pull topology; the
  controlled 72-run study changed trajectories but failed the primary held
  accuracy/F1 gate.
- `compiled_action_input_access.py` and `full_system_action_input_access.py`:
  the verified before-block-0 causal seam into the frozen 14-layer byte model;
  material source-disjoint training remains gated.

### Pre-block-0 successor readiness map — 2026-11-14

The successor was mapped rather than rebuilt. The bounded three-root inventory
is `SYSTEM_INVENTORY_20261114_FROZEN_ACTION_SUCCESSOR.json`, SHA-256
`89733ad1d4fbd292bb151ec2bca722aa8d11ec758892b933e11f4ae08744d853`.
It covers this clean research worktree, the existing action-compiler experiment,
and the live frozen-multiview run. The action experiment already contains the
required before-block-0 reader, full-system bridge, exact compiler fallback,
source-authority admission contract, two-slot exact-resume mechanics, and the
no-circuit, authority-row, equal-shape random-fixed, and one-to-one
shuffled-binding controls. Its action reader is the only trainable component;
the recovered 14-layer parent remains frozen.

The current implementation surface was rechecked without writing pytest caches
or bytecode:

```text
python -X utf8 -B -m pytest -q \
  test_compiled_action_input_access.py \
  test_full_system_action_input_access.py \
  test_full_system_action_campaign.py -p no:cacheprovider
```

Observed result: `37 passed in 18.53s`. This verifies mechanics and admission
guards, not model benefit. The experiment worktree has `134` pre-existing
status entries and remains deliberately untouched; successor evidence is being
recorded only in this clean worktree.

The recorded parent path currently points to an unavailable `S:` drive, but the
parent is not lost or silently substituted. Kaggle reports
`issacizrealdavis/clay-full-system-best-recovery-20261029/1` complete and lists
`checkpoint_A.pt`; the prior recovery watcher independently verified that file
at step `13,400` with SHA-256
`f3988a328cd18a082e3e058827c65cc9f0947b6695abc757fcd3e1ee11181b2e`.
The canonical `FullSystemLM` source remains locally available under
`C:\dev\tongue-compiler\artifacts\kaggle_full_system_recovery_20261026`.
Any material child must restore the exact remote checkpoint and rehash it before
use; an arbitrary local checkpoint is not an acceptable replacement.

The course-source `S:` ledger and derived transcripts are also not mounted.
However, all three original videos remain locally accessible and their freshly
measured hashes exactly match the sealed audit:

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| Tracing Code | 40,211,741 | `d663332be980169f296890e31ffab4c0b20887cac4e71a9c99edf560e3d0d4a4` |
| Tracing Lists | 30,226,656 | `42bc9a3eb2d10a6d212120ef240c15eb674023134becc25440e6f8a1aceb58cb` |
| Tracing Nested Loops | 40,587,138 | `0ee8da1342d532e251fadabee11868932eafbb3579368c50b0a8f0d66ec60634` |

This preserves a verified recovery route, but it does not satisfy the material
data gate: the 279 indexed transcript spans remain unreviewed and ineligible,
and no disjoint holdout, ordinary, or retention source family has been admitted.
Current local capacity is healthy at about `27.6 GiB` free, while the exact
successor peak-write reserve has not yet been measured. The live campaign and
its final independent replay must close first. Therefore successor launch,
promotion, partial unfreeze, and tool dispatch all remain unauthorized.

The next model-level sieve trial must remain a separately preregistered child of
the completed campaign. It should attach a fixed-width centroid/trit summary at
the existing causal input-access seam and compare ordinary/no-intervention,
equal-width random-fixed, one-to-one shuffled binding, means-only, and full
sieve arms across fresh seeds. It must preserve the exact byte/token deed,
retain the frozen parent, keep labels/rewards out of the packet, and judge
source-disjoint action, reasoning/coding transfer, retention, false action
calls, throughput, and independent replay. No such child is authorized yet.

