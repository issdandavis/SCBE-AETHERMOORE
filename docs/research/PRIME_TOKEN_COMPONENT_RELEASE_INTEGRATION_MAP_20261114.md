# Prime-token component-gate release integration map

Date: 2026-11-14

Status: `IMPLEMENTED_TESTED_LIVE_STATE_AND_REPORT_BOUND_FAIL_CLOSED_NO_TRAINING_NO_PROMOTION`

## Capability boundary

Add one fail-closed release prerequisite: the frozen six-view prime-token
experiment must not become eligible for manual launch review until the live
query-session/target-family connected-component watcher reports
`QUERY_SESSION_FAMILY_COMPONENT_GATE_VERIFIED`.

This integration does not collect queries, open labels, launch an optimizer,
alter a checkpoint, authorize training, or promote weights. It closes a
governance gap in which the existing release contract could theoretically pass
without proving that query-session and target-family components remain
indivisible across later folds.

## Bounded system

The repository inventory helper named by the system-mapping skill is absent
from both connected worktrees, so this map uses exact Git state, targeted file
inspection, runtime receipts, and SHA-256 values instead.

| Node | Path / schema | Role | Current status |
| --- | --- | --- | --- |
| Frozen release contract | `config/training/prime_token_frozen_input_access_release_v1.json` / `scbe.prime-token-frozen-input-access-release-contract.v1` | Declares counts, arms, metrics, and required evidence | Now requires the component gate; SHA-256 `ccebfb4a646c80dc61b129316b176321c2bae20249f746cf10f4cf79d909f83b` |
| Release auditor | `scripts/tokenizer/audit_prime_token_training_release.py` / `scbe.prime-token-frozen-input-access-release-audit.v1` | Hash-checks evidence and returns only waiting, invalid, or manual-review-ready | Now independently replays the dynamic component watcher, colocated report hash, split digest, report digest, all component gates, and fail-closed authority before accepting the verified status |
| Component algebra | `python/scbe/prime_token_query_family_components.py` / `scbe.prime-token-query-session-family-components.v1` | Builds bipartite connected components and neutral fold assignment from reviewed hashes | Cherry-picked from the isolated component branch; SHA-256 `c3750f9dfe37603660a3363e24285e5e0a6c310cf8c9e1e75fd96d6fe7e0a2cd` |
| Component watcher | `scripts/tokenizer/watch_prime_query_family_components.py` / `scbe.prime-token-query-session-family-component-watcher.v1` | Waits for prepared/selection evidence, then runs the pinned component audit once | Live external watcher is fail-closed at `WAITING_FOR_PREPARATION_PACKET`; source SHA-256 `fc842e6bd660561e36d0823ff9ee7ca44531837d333da42302685b363fee1454` |
| Live watcher receipt | `C:/dev/clay-training-runs/prime-token-catalog-20261106/prospective-query-session-family-component-watcher-v7-20261114/QUERY_SESSION_FAMILY_COMPONENT_WATCHER_STATUS.json` | Dynamic evidence consumed only after its terminal verified status | 10 candidates; labels not opened; scoring/training/promotion unauthorized; observed SHA-256 `6f46f80366010a36724ce628d485d93ee9783f943f666080e20973d251dcb36d` |
| Current release state | `C:/dev/clay-training-runs/prime-token-catalog-20261106/successor-training-release-20261111/CURRENT_RELEASE_STATE.json` / `scbe.prime-token-frozen-input-access-release-state.v1` | Binds dynamic and immutable evidence into one audit input | Now includes the dynamic component watcher without changing authority; SHA-256 `3ecdeeede2d6b72044924d53ed0ecf87eb839dd53d46feb92b40bd356e3c7a99` |
| Frozen model campaign | `C:/dev/clay-training-runs/frozen-multiview-adapter-replication-20261114-v1` | Separate three-seed frozen-core replication | Live and untouched; no edge from this code-only change into its process or checkpoints |

## Edges and invariants

```text
closed reviewed queries + manifest-bound target families
  -> component auditor
  -> component watcher status (dynamic, fail-closed)
  -> current release state evidence entry
  -> frozen release contract requirement
  -> generic release auditor
  -> at most READY_FOR_MANUAL_TRAINING_RELEASE_REVIEW
```

- The component watcher transfers only its status artifact path and derived
  status. It does not transfer query text, raw session IDs, labels, weights, or
  predictions into the release auditor.
- The release state must use `read_status_from_artifact: true`; copied stale
  status text cannot satisfy the gate.
- A terminal verified status is insufficient by itself. The release auditor
  requires the watcher schema and fail-closed authority, resolves a colocated
  component report, matches its file hash, recomputes its split and report
  digests, and requires every component gate to be true.
- The contract accepts exactly
  `QUERY_SESSION_FAMILY_COMPONENT_GATE_VERIFIED`. Waiting, underpowered,
  invalid, missing, unreadable, or hash-drifted states remain blockers/errors.
- Existing six arms, three-or-more fresh seeds, source-family split, shuffled
  binding, random-fixed, single-frame, no-intervention, and independent replay
  requirements remain unchanged.
- A passing machine audit still grants no training, merge, serving, promotion,
  tool-dispatch, or partial-unfreeze authority.

## Controls and verification

The focused release tests must prove:

1. a fixture with a terminal verified component watcher can reach only manual
   review readiness;
2. missing component evidence is a blocker;
3. waiting, underpowered, and invalid component statuses cannot pass;
4. dynamic artifact status overrides stale copied state;
5. existing immutable-hash and authority-drift tests still pass; and
6. component algebra/watcher tests still pass after branch integration.

No model baseline or size-matched neural control is run here because this is a
release-governance integration, not a learning claim. Those controls remain in
the downstream six-arm material experiment.

## Resource and rollback gate

- Expected compute: focused CPU tests only; no GPU and no optimizer.
- Expected disk: under 100 MiB for a sparse worktree and test caches.
- Measured free C: space before checkout: `23,988,084,736` bytes. The active
  trainer's 25 GiB restart floor is not lowered. Two existing guarded cloud
  offloads remain independent and must not be interrupted.
- Stop conditions: any conflict outside documentation, a failing component or
  release test, authority widening, live-process disturbance, or substantial
  disk growth.
- Rollback: discard this isolated worktree/branch or revert its integration
  commit. The live watcher, live trainer, current release state, and weights are
  outside the worktree and remain unchanged until a separately verified state
  refresh is intentionally performed.

## Build decision

The bounded code-and-contract integration passed. The post-commit live-state
update added only the waiting component watcher and regenerated a separate
fail-closed audit without opening labels or starting training.

## Implementation evidence

Changed integration paths:

- `config/training/prime_token_frozen_input_access_release_v1.json` adds the
  exact terminal component-watcher status to `required_evidence`;
- `tests/tokenizer/test_prime_token_training_release.py` makes the component
  evidence dynamic, checks the shipped contract, requires the evidence entry,
  and rejects waiting, underpowered, and invalid watcher states; and
- this scoped map records the pre-build and post-build boundary.

Verification:

```text
23 focused release/watcher tests passed
406 tokenizer regression tests passed
Black check passed
Ruff check passed
```

The first wide run in the sparse worktree failed only because
`lexicons/function_primitives.json` had not been checked out. Adding the
existing `lexicons` cone made the same tests pass without a code change. This
was an environment-coverage failure, not a product regression.

No optimizer, label file, model state, adapter checkpoint, parent tensor, or
tool dispatcher was opened or changed. After commit `c3ba86a00`, the live
release state gained the dynamic component-watcher entry. The regenerated
audit is
`C:/dev/clay-training-runs/prime-token-catalog-20261106/successor-training-release-20261111/RELEASE_AUDIT_COMPONENT_BOUND_20261114.json`.
It reports `WAITING_FOR_RELEASE_REQUIREMENTS`, zero errors, ten blockers, and
report SHA-256
`99e170700f5874adbaa64c743989e8f83de4148fc047579a9edf0e76b5e3d82b`.
The new blocker is exactly
`query_session_family_component_gate status is WAITING_FOR_PREPARATION_PACKET`;
all no-training/no-promotion authority fields remain unchanged.

## Dynamic-report replay hardening

A follow-up audit found that the first integration consumed the live watcher
status dynamically but did not itself reopen the component report. That left a
manual-edit trust gap between the watcher and release review. The release
auditor now treats the watcher as a structured dynamic receipt rather than a
status string. Tests reject a missing report binding, report-file hash drift,
component split drift, report digest drift, watcher authority drift, and a
missing dynamic-read declaration.

The hardened auditor was run against the unchanged live waiting state and
wrote
`C:/dev/clay-training-runs/prime-token-catalog-20261106/successor-training-release-20261111/RELEASE_AUDIT_COMPONENT_REPORT_BOUND_20261114.json`.
It correctly exited `2` with `WAITING_FOR_RELEASE_REQUIREMENTS`, zero errors,
ten blockers, promotion `NOT_AUTHORIZED`, and partial unfreeze `NONE`. Its
canonical report SHA-256 is
`672e8b6ddbe62fca761d67cce8207c12fbdb2fe0ef066180b5a38c3f221072d3`;
the serialized file SHA-256 is
`0b80346308139e2f39704b39594276fb6b4245c10c054f6a60e5f2cd1c469c15`.

## Information-rich review states

Waiting, missing-label, pending-report, underpowered, invalid, and verified
watcher receipts now include a non-sensitive `review_packet`. The component
gate remains fail-closed, but it reports:

- a review-only disposition and reason code;
- safe aggregate observations and explicit deficits;
- which measurements remain unavailable until independent review;
- failed component gates after the pinned auditor runs; and
- the next safe action without granting training, scoring, promotion, serving,
  merge, execution, or partial-unfreeze authority.

The packet never copies query text, raw session identifiers, labels, model
outputs, or weights. Its pre-review candidate deficit is intentionally a lower
bound: independent review may reject candidates, so reaching the candidate
floor does not imply reaching the accepted-query floor.

A separate one-shot receipt was generated from the live waiting inputs without
restarting or replacing the authoritative watcher:

`C:/dev/clay-training-runs/prime-token-catalog-20261106/prospective-query-session-family-review-v1-20261115/QUERY_SESSION_FAMILY_COMPONENT_WATCHER_STATUS.json`

It reports 10 prospective candidates, a minimum additional-candidate deficit
of 20 before 30 acceptances are even possible, labels `NOT_OPENED`, disposition
`REVIEW_REQUIRED_NO_AUTOMATIC_TRANSITION`, and all execution/training/promotion
authority disabled. The receipt file SHA-256 is
`1bbbf3a1387a605dd14eb88445baa0a0723b33f12f827cdf5552ea25cfa524e1`;
the watcher source SHA-256 is
`f0e80f9a6e4191a43de445db26d2619c929ad2105b5fea2eb9b86ad69fed21bf`.

Verification after the review-packet change:

```text
28 focused component/release tests passed
406 tokenizer regression tests passed
Ruff passed
Black passed
```

## Exact candidate-scarcity diagnosis

The hash-pinned selector was also run once in telemetry-only mode over the
current closed and open Codex sources. It emitted counts and rejection classes,
not query text or identities:

`C:/dev/clay-training-runs/prime-token-catalog-20261106/prospective-open-readiness-v2-20261115/OPEN_SOURCE_READINESS.json`

Observed state:

- 31 closed source sessions, so the three-session minimum is already met;
- 10 closed review-query candidates;
- 14 additional review-query candidates in the current open source;
- 24 projected candidates after that source closes, leaving a deficit of 6;
- 232 selector-accounted turns with an accounting gap of 0;
- source health `HEALTHY`; and
- shortfall classification `FIXED_SELECTOR_CANDIDATE_SCARCITY`, with `topic`
  as the dominant rejection reason.

This rules out storage pressure, missing sessions, or selector-accounting drift
as the present blocker. The safe path is to let normal, genuinely independent
post-freeze review requests accumulate. The threshold and selector remain
unchanged, and no rejected turn is relabeled merely to fill the quota. Receipt
SHA-256:
`b01c6a01ed929dd9d337dfdc28432f00aa94e534f13f9f0e5a40de107fe8e647`.
