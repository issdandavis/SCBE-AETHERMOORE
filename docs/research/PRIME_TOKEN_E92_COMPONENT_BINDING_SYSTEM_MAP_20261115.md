# Prime-token E92 component-binding system map

Date: 2026-11-15  
Branch: `research/e92-component-binding-20261115`  
Scope: mechanics only; no labels, model weights, scoring, training, serving, merge, promotion, or partial unfreeze are authorized.

## Objective

Make the E92 prospective scorer fail closed until the existing
query-session/target-family component watcher has produced a verified,
hash-bound split. A query session or selected target family must remain an
indivisible evaluation unit before any labels can reach the E92 scoring path.

## Existing capabilities to reuse

- `scripts/tokenizer/watch_prime_query_family_components.py` waits for the
  prepared queue and exact selection audit, opens labels only through its pinned
  auditor, and emits a terminal component-gate status.
- `python/scbe/prime_token_query_family_components.py` builds the bipartite
  query-session/target-family graph, assigns whole connected components to
  neutral folds, and seals the split and report digests.
- `scripts/tokenizer/watch_run_e92_prospective.py` currently gates E92 on the
  collector, preparation packet, selection replay, and labels.
- `python/scbe/prime_token_prospective.py` builds the source-chain bundle and
  executes the existing controlled E92 evaluator.
- `python/scbe/prime_token_prospective_verify.py` independently reconstructs
  the benchmark and control evidence from bundled source artifacts.

## Missing edge

The component watcher and E92 watcher currently run beside one another. E92 can
observe labels and score before the component watcher has certified an
indivisible split. This is a race at the evaluator boundary, not a missing
clustering algorithm or model feature.

## Planned dataflow

```text
collector -> preparer -> exact selection audit
                         |
                         v
                 pinned component watcher
                 opens independent labels once
                         |
             VERIFIED component status + report
                         |
                         v
                    E92 watcher
                         |
             pinned E92 runner + source bundle
                         |
                         v
              independent E92 verification
```

E92 must stop before reading labels or launching the scorer when the component
status is missing, waiting, underpowered, invalid, hash-drifted, or bound to a
different queue, labels file, source inventory, or source-family audit.

## Interfaces and artifacts

Inputs added to the E92 watcher:

- component watcher status path;
- terminal status schema and exact `QUERY_SESSION_FAMILY_COMPONENT_GATE_VERIFIED`
  state;
- report path, file SHA-256, split SHA-256, and fail-closed authority fields.

Inputs added to the E92 runner:

- verified component report path.

Outputs added to the E92 bundle:

- `SOURCE_QUERY_SESSION_FAMILY_COMPONENTS.json` as a fixed source-chain role;
- `SOURCE_FAMILY_AUDIT.json` so independent replay can reconstruct each selected
  source suffix's canonical target family instead of trusting family IDs copied
  into the component report;
- receipt fields for its source-file hash and component split hash;
- a new run schema revision so v4 bundles cannot be mistaken for component-gated
  bundles.

No raw query text or raw session ID may be introduced by the component report.
Existing hashed query identities and hashed session identities remain evaluator
metadata only.

## Verification and controls

The producer must validate the component report before scoring. The independent
verifier must separately check:

- report schema, terminal status, zero errors, and exact no-authority contract;
- queue, labels, inventory, and source-family input hashes;
- canonical report and component-split digests;
- whole-component fold assignment, nonempty folds, and zero session/family
  overlap;
- accepted query identities agree with the independently reconstructed labels;
- no forbidden raw `query` or `session_id` keys occur in the report.

Required adversarial tests:

1. waiting, underpowered, and invalid component states cannot launch E92;
2. report path or file-hash drift fails before the runner;
3. split-digest, authority, overlap, or source-input tampering is rejected;
4. recomputing outer bundle hashes cannot hide a mutated component report;
5. the existing lexical, no-intervention, route-null, shuffled-binding, and
   random-fusion controls remain unchanged.

## Budgets, save boundary, and rollback

- Compute/storage: JSON validation only; no additional model parameters or
  training run.
- Save boundary: this isolated worktree and branch only. Active pinned watchers
  and their hashes remain untouched.
- Rollback: discard this branch/worktree; the authoritative v4 watcher chain is
  unchanged.
- Activation boundary: do not replace or relaunch the live E92/component
  watchers until focused and full tokenizer tests pass and a new pinned launch
  contract is explicitly reviewed.

## Stop conditions

Stop without scoring on any missing report, non-verified gate, underpowered
split, malformed/forbidden field, digest mismatch, source-binding mismatch,
authority drift, label-order violation, session overlap, family overlap, or
unexpected implementation hash. Promotion remains manual and outside this
change even after an independently verified E92 result.
