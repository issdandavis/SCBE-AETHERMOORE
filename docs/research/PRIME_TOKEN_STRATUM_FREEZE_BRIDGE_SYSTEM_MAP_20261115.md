# Prime-token label-free stratum-freeze bridge — system map

Status: `PREBUILD_GATE_PASSED_IMPLEMENTATION_NOT_YET_ACTIVE`

## Capability and boundary

The source-disjoint prospective evaluator needs one exclusive, immutable
`review_stratum` on every queue row before an independent reviewer sees a
worksheet. The current live v7 collector correctly records every matching
`topic_groups` value, but it does not choose one. The current preparer emits a
blank reviewer-editable stratum, while the hardened v9 component auditor
requires a queue-frozen non-empty stratum and `topic_groups == [review_stratum]`.

The new capability is therefore a label-free queue transform and preparation
bridge. It does not choose a target catalog source, open labels, retrieve,
score, train, execute, merge, promote, or unfreeze weights.

## Bounded inventory

The repository inventory helper named by the mapping workflow is absent, so
this scoped map uses targeted file, process, status, Git, and SHA-256 evidence.
The active implementation worktree was clean at commit
`7aaff4c5f9a74f4cf23147bea9a09fad467bd796` before this map was added.

| Node | Exact authority | SHA-256 | Current role/status |
| --- | --- | --- | --- |
| Raw prospective collector | `C:/dev/_wt_clay_prospective_v3_20261109/experiments/clay_codex_session_harvest_20261107/harvest_prospective_codex_sessions.py` | `2bd78ac15c6c1a3099a9a64d4c13252a25135f6e65b777bf8af6863ddb23ea26` | Produces immutable post-freeze raw queue; live and waiting for a new closed source. |
| Exact-selection auditor | `C:/dev/_wt_prime_v7_selection_order_fix_20261115/experiments/clay_codex_session_harvest_20261107/audit_prime_queue_selection.py` | `86f696d6adf6d39209bcc70b8f70ca3bf5d693c43e7726ca9d53cfde703b32b6` | Replays the raw queue policy without labels or scoring. |
| Exact-selection watcher | same worktree, `watch_audit_prime_queue_selection.py` | `011e54080c0be8cb91d4ee6ce1fe3ac17e4df62b4f514efb9d514111a19b7ba7` | Live and waiting for the 30-row raw queue. |
| Legacy preparer | `C:/dev/_wt_clay_sidecar_multiseed_20261107/experiments/clay_codex_session_harvest_20261107/prepare_prospective_review.py` | `9b348e059bb6074385d5537e204af90a7b9b2171376724af9e0b4e9c46e80a58` | Emits an offline worksheet, but leaves `review_stratum` blank and reviewer-editable. |
| Legacy preparer watcher | same worktree, `watch_prepare_prospective_review.py` | `6623f8d0682709c8457c3bccfce564ce1b74d7802af3c6b1ef5c2bf7ca0d0564` | Live and waiting; must be retired only after a verified successor is active. |
| Hardened component module | `python/scbe/prime_token_query_family_components.py` | `b23a1d96e41816075b0c7c9ffabd653be88abfd74329b59cdff678aed714edbd` | Requires queue-frozen exclusive strata and label agreement. |
| Hardened component watcher | `scripts/tokenizer/watch_prime_query_family_components.py` | `3eb5b0519aaa398844c4e6004d413460123528f618ce5bbf2d1e35889bebd771` | Active v9 worker; currently waiting with labels unopened. |
| E92 watcher | `C:/dev/_wt_prime_e92_component_binding_20261115/scripts/tokenizer/watch_run_e92_prospective.py` | `77da1c43a90a53448879959911a4c77aa88b39ecd966ff137dcd99123c984311` | Active and fail-closed behind preparation/component gates. |
| Frozen catalog | `C:/dev/clay-training-runs/prime-token-catalog-20261106/catalog-v7-corrected-20261110/catalog.sqlite3` | `a720faae57ca5f64424624dd53f4a8913a7b01fdf12ae9b8e6855bd294ba751a` | Reviewer source-suffix universe. |
| Source-family audit | `C:/dev/clay-training-runs/prime-token-catalog-20261106/catalog-v7-audits-20261110/SOURCE_FAMILY_AUDIT_V3.json` | `ef3f99b08d4ea1ee71c61010579012ddc515b592b44379a134a73f5fde9d9c30` | Canonical target-family authority. |

Measured current raw queue:

- path: `prospective-collector-v7-20261110/scan-036/REVIEW_QUEUE.json`;
- file SHA-256: `136ef0d8fd0f5a369d737578ca001362fa528d0cda78dc7315dcf114ecab0c1b`;
- content SHA-256: `a139dd92e352cbf67c3e0941601af67af7c71b4334628148f6795f771bd62a2e`;
- candidates: `10`;
- exclusive-topic rows: `5`;
- multi-topic rows: `5`;
- rows with a non-empty queue-frozen stratum: `0`.

## Existing and proposed edges

```text
closed source sessions
  -> pinned raw collector
  -> immutable raw queue (zero or more topic groups per accepted row)
  -> pinned exact-selection audit (raw queue replay only)
  -> NEW label-free stratum freezer
       sort rows by query SHA-256
       choose the least-loaded eligible topic
       break ties by SHA-256(query_sha256 || topic), then topic name
       retain every row
       record source_topic_groups
       set topic_groups=[review_stratum]
       recompute queue/session/content hashes
  -> NEW scoped packet preparer
       SCOPED_REVIEW_QUEUE.json
       REVIEW_LABEL_TEMPLATE.json (UNREVIEWED, frozen strata)
       CATALOG_SOURCE_SUFFIXES.json
       REVIEW_WORKSHEET.html (stratum read-only)
       PREPARATION_RECEIPT.json
  -> independent human review
  -> hardened component auditor
  -> source-disjoint folds
  -> E92 evaluator + controls
```

Labels, source-family assignments, retrieval outputs, scores, and model outputs
have no edge into the stratum assignment. The transform operates only on the
raw query hash and its already-frozen broad topic membership.

## Proposed schemas and invariants

New implementation surfaces:

- `python/scbe/prime_token_review_scope.py` — pure transform and receipt checks;
- `scripts/tokenizer/prepare_prime_review_scope.py` — one-shot packet CLI;
- `scripts/tokenizer/watch_prepare_prime_review_scope.py` — headless one-time transition;
- focused tests under `tests/tokenizer/`.

Required invariants:

1. Raw queue schema/content hash, dataset hash, candidate count, identities,
   and exact-selection receipt must replay.
2. Candidate order cannot affect the scoped queue or assignment receipt.
3. Every scoped candidate retains its query text/hash, source session, and
   provenance fields exactly.
4. Every scoped row has one non-empty `review_stratum`, that stratum belonged
   to its raw `topic_groups`, and scoped `topic_groups` is exactly one item.
5. No candidate is added, removed, duplicated, or relabelled from target data.
6. The worksheet displays the frozen stratum but cannot edit it.
7. The unreviewed template contains every query hash exactly once and no query
   text, session identifier, target family, retrieval output, score, or weight.
8. All outputs are exclusive/atomic and hash-bound; partial output is preserved
   for review rather than overwritten.
9. Training, scoring, serving, execution, merge, promotion, tool dispatch, and
   partial unfreeze remain unauthorized.

## Controls and success gate

- No-intervention control: raw queue and current watchers remain byte-for-byte
  unchanged while the successor is developed.
- Order control: reverse/shuffle every raw input list and require identical
  scoped content/assignment hashes.
- Binding control: mutate the raw queue or selection-audit hash and require a
  fail-closed result.
- Leakage control: recursively reject query text, session IDs, target-family
  labels, retrieval outputs, scores, and weights from template/receipt metadata.
- Downstream control: the existing v9 component auditor must accept a synthetic
  correctly reviewed scoped queue and reject reviewer-side stratum mutation.
- Activation gate: focused tests, full tokenizer regressions, Ruff, exact source
  hashes, two advancing headless polls, and explicit retirement of only the
  superseded downstream preparer/component workers.

This bridge establishes evaluation integrity only. It does not establish
six-view model benefit or authorize a model successor.

## Budget, saves, rollback, and stop conditions

- CPU: metadata transform plus one catalog scan after the raw 30-row gate;
  no GPU and no model inference.
- Memory: bounded by the queue and source-suffix inventory; expected below
  `100 MiB` excluding the operating-system file cache.
- Disk: less than `10 MiB` for packet, worksheet, status, logs, and receipts.
- Immutable successor output must use a new runtime directory; no existing
  queue, packet, labels, result, checkpoint, or weight may be overwritten.
- Rollback: stop the successor watchers and quarantine only their newly named
  runtime directories; the raw collector, raw selection audit, catalog, labels,
  weights, and current v9 evidence remain intact.
- Stop before activation on source/hash drift, unstable input, any row-count or
  provenance change, editable/missing stratum, label/target leakage, partial
  output, failed regression, or inability to preserve fail-closed authority.

Next resume point: implement and fixture-test the pure stratum transform before
adding any watcher or replacing any live process.
