# Prime-token query-session/family component gate — system map

Status: `IMPLEMENTED_NOT_ACTIVATED`; audit-only; not connected to the active v7 workers
Date: 2026-11-14

## Capability boundary

The existing prospective chain already freezes the catalog before query
authorship, hash-binds every review decision, caps one candidate per session
inside each review stratum, and audits canonical catalog-source families. It
does not yet prove that query sessions and reviewer-selected target families
remain disjoint when rows are partitioned for a later learned experiment.

The new capability is a deterministic bipartite-component audit:

```text
frozen review queue --query hash--> reviewed decision
        |                                  |
        +-- query session                  +-- selected catalog suffix
                                                   |
source inventory --suffix--> canonical source --family audit--> family ID

query-session nodes <---- accepted query edges ----> target-family nodes
        -> connected components
        -> indivisible deterministic folds
        -> overlap/coverage receipt only
```

No query text, target family, reward, or label is added to a model input. The
component assignment is evaluator metadata only. It grants no scoring,
training-intake, execution, merge, promotion, or partial-unfreeze authority.

## Existing nodes reused

| Node | Exact surface | Role / invariant |
| --- | --- | --- |
| Frozen queue | `scbe.prime-token-independent-review-queue.v1` | Candidate ID, query SHA-256 and source session; queue content hash must replay exactly. |
| Review labels | `scbe.prime-token-independent-review-labels.v1` | Complete hash-bound accept/reject decisions; targets remain evaluator-only. |
| Source inventory | `clay.prime-token-catalog-source-suffixes.v1` | Maps each unique reviewed suffix to one catalog source URI. |
| Family audit | `scbe.prime-token-source-family-audit.v1` | Collapses catalog rows/line fragments to canonical files and conservative family IDs. |
| Current family gate | E92 branch `scripts/tokenizer/audit_e92_source_family_gate.py` | Measures canonical-source/family diversity but does not construct session-family components. |
| Active v7 chain | `C:\dev\clay-training-runs\prime-token-catalog-20261106` | Hash-pinned collector/preparer/auditors; remains untouched. |

The E92 worktree and the current frozen-adapter worktree have broad divergent
histories. A branch merge would remove current frozen-training files, so this
addition must be a small standalone module on the current integration branch,
not a broad merge or cherry-pick.

## New node and exact contract

Implemented module: `python/scbe/prime_token_query_family_components.py`
Proposed CLI: `scripts/tokenizer/audit_prime_query_family_components.py`

Inputs are the four immutable JSON files above. For every accepted query, the
audit joins:

```text
(query_sha256, query_session, review_stratum,
 relevant_source_suffix, canonical_source, target_family)
```

It then unions the query-session and target-family vertices. Every resulting
connected component is assigned as one indivisible unit to a named fold using
a deterministic largest-first load balancer. Input row order must not change
component IDs or fold assignments.

The output must contain hashes/counts and never query text. It records component
IDs, hashed session IDs, target-family IDs, query hashes, strata counts, fold
loads, overlap counts, thresholds, failures, and a canonical report hash.

## Pre-build gates and controls

- Minimum accepted queries remains 30; this audit cannot lower the active gate.
- At least three source sessions, two manifest-bound target families and three
  connected components are required for a three-fold receipt.
- No component may exceed the declared maximum query share (default `0.8`).
- Query sessions and target families must each have zero cross-fold overlap.
- Invalid schemas, hashes, incomplete decisions, unknown suffixes, catalog
  mismatches, duplicate identities, or non-hex query hashes fail closed.
- One test permutes all input row orders and requires an identical component and
  fold digest.
- One test makes a session target two families; those families must collapse
  into one component rather than leak across folds.
- One test uses one giant component and must return `UNDERPOWERED`, not pass by
  splitting the component or lowering a threshold.
- The current source-family-only audit is the baseline. The no-intervention
  comparison is its lack of a session-family split. Equal-width/random-feature
  controls are not applicable because this node has no model or parameters;
  shuffled binding is represented by the cross-family-session collapse test.

## Budget, persistence and stop conditions

The audit is `O(Q alpha(V))` union-find work over tens of reviewed rows, needs no
GPU/network call, and should consume well under one MiB of output. The CLI must
refuse to overwrite an existing receipt. Rollback is deletion of only the new
unactivated code/docs commit; active v7 artifacts and workers are unchanged.

Stop before any scoring or training when the report is invalid or underpowered.
Only a later, separately preregistered consumer may assign semantic roles such
as train/holdout/retention to the neutral fold names.

## Inventory receipt

The bounded two-worktree inventory used for this map is
`SYSTEM_INVENTORY_20261114_PRIME_QUERY_SESSION_GATE.json`. It is discovery
evidence, not a capability result.

## Implementation receipt — 2026-11-14

Implemented paths:

- `python/scbe/prime_token_query_family_components.py`
  (`8e65188f93fef41635daf301481de33f929f8c0d87ec70d3c2980def8ee643f2`)
- `scripts/tokenizer/audit_prime_query_family_components.py`
  (`1ebcecd69b473c472739c4e02e12092a34320312c657a804b875a41b5b749a18`)
- `tests/tokenizer/test_prime_token_query_family_components.py`
  (`aa9a53b9d4941a8e297755313ddf8ebb892b5b9dc639aa0bbd54352cb46f8d70`)
- `docs/research/SYSTEM_INVENTORY_20261114_PRIME_QUERY_SESSION_GATE.json`
  (`0276f7af90bd80c0c27c430694c6973850519148c84d3e4bab7205917e2c3215`)

The focused query-harvest/prospective/component suite passed `26 / 26`; the
entire current tokenizer suite passed `315 / 315`. Tests prove deterministic
folds under input permutation, zero raw query/session text in the report,
cross-family session collapse, giant-component underpowering, unknown-source
rejection, and preservation of existing prospective behavior.

The active v7 chain remains unchanged and underpowered at 4 closed candidates.
Its one unstable open session presently contains 10 selector matches; even a
clean close would yield only 14, below 30. Therefore no real component receipt,
labels, score, model update, promotion, or unfreeze has been produced.
