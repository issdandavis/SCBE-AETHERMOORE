# Prime-token component-gate release integration map

Date: 2026-11-14

Status: `IMPLEMENTED_TESTED_AWAITING_LIVE_STATE_BIND_NO_TRAINING_NO_PROMOTION`

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
| Release auditor | `scripts/tokenizer/audit_prime_token_training_release.py` / `scbe.prime-token-frozen-input-access-release-audit.v1` | Hash-checks evidence and returns only waiting, invalid, or manual-review-ready | Reused unchanged unless tests expose a generic evidence defect; SHA-256 `d7eee04968d8cbcd978fadc06a24447f4c78fcaf5d309e5e951ed378103a7d6b` |
| Component algebra | `python/scbe/prime_token_query_family_components.py` / `scbe.prime-token-query-session-family-components.v1` | Builds bipartite connected components and neutral fold assignment from reviewed hashes | Cherry-picked from the isolated component branch; SHA-256 `c3750f9dfe37603660a3363e24285e5e0a6c310cf8c9e1e75fd96d6fe7e0a2cd` |
| Component watcher | `scripts/tokenizer/watch_prime_query_family_components.py` / `scbe.prime-token-query-session-family-component-watcher.v1` | Waits for prepared/selection evidence, then runs the pinned component audit once | Live external watcher is fail-closed at `WAITING_FOR_PREPARATION_PACKET`; source SHA-256 `fc842e6bd660561e36d0823ff9ee7ca44531837d333da42302685b363fee1454` |
| Live watcher receipt | `C:/dev/clay-training-runs/prime-token-catalog-20261106/prospective-query-session-family-component-watcher-v7-20261114/QUERY_SESSION_FAMILY_COMPONENT_WATCHER_STATUS.json` | Dynamic evidence consumed only after its terminal verified status | 10 candidates; labels not opened; scoring/training/promotion unauthorized; observed SHA-256 `6f46f80366010a36724ce628d485d93ee9783f943f666080e20973d251dcb36d` |
| Current release state | `C:/dev/clay-training-runs/prime-token-catalog-20261106/successor-training-release-20261111/CURRENT_RELEASE_STATE.json` / `scbe.prime-token-frozen-input-access-release-state.v1` | Binds dynamic and immutable evidence into one audit input | Missing the component watcher entry; current SHA-256 `c7d03688bd1ba52f69c84ee98d926d6f800281f3117cdf7a7d0826dab7c7e021` |
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

The seam is sufficiently mapped for a bounded code-and-contract integration.
Updating the live release-state JSON is a separate post-test operation; it may
only add the waiting component watcher as another blocker and must regenerate
the audit without opening labels or starting training.

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
25 focused release/component tests passed
141 prime-token/watcher regression tests passed
Black check passed
Ruff check passed
```

The first wide run in the sparse worktree failed only because
`lexicons/function_primitives.json` had not been checked out. Adding the
existing `lexicons` cone made the same tests pass without a code change. This
was an environment-coverage failure, not a product regression.

No optimizer, label file, model state, adapter checkpoint, parent tensor, or
tool dispatcher was opened or changed. The live release state remains
deliberately unmodified until this branch is committed and its fail-closed
audit can be regenerated against the exact committed contract.
