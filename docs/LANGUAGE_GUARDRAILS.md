# Language Guardrails

Last updated: February 19, 2026
Scope: patent-safe, technical-safe, experiment-safe writing.

## Register model

### 1) Patent register
Use claim-bounded language tied to mechanism and evidence scope.

### 2) Technical register
Use implementation language tied to module paths and measured behavior.

### 3) Experimental register
Use hypothesis language with explicit pass/fail criteria and limits.

## Forbidden phrase table (12)

| Avoid | Replace with |
|---|---|
| unbreakable | achieves N-bit target under stated threat model |
| mathematically impossible | denied by current threshold and policy constraints |
| perfect security | no failures observed in current test scope |
| guaranteed safe | reduced risk under measured conditions |
| production-ready (without SLO evidence) | prototype implemented |
| no prior art | prior art review pending |
| proven novelty | integration novelty under active validation |
| geometric firewall (hardness sense) | geometric risk-scoring layer |
| 518,400x security | weighted policy multiplier |
| full BFT (if majority vote only) | quorum majority consensus |
| constant-time | timing behavior not constant-time verified |
| impossible to bypass | no bypass found in tested attack suite |

## Status labels
- `[PROVEN]`
- `[PROVEN_PARTIAL]`
- `[CODE_EXISTS_UNTESTED]`
- `[THEORETICAL_ONLY]`
- `[REFRAMED]`

## Formula regime tags
- `[WALL_ENFORCEMENT]`
- `[PATROL_MONITORING]`
- `[BOUNDED_SCORING]`
- `[EXPERIMENTAL]`

Any use of `H(...)` must include one regime tag and formula ID.

## Citation format

### Experiment citation
`Metric=value (artifact_path, date, dataset_id, seed_set)`

Example:
`AUC=0.9942 (experiments/three_mechanism_results.json, 2026-02-06, ds_v1, seeds_01)`

### Prior art citation
`[Author Year] venue/link + one-line distinction`

### Code citation
`path:line` pointing to implementation used for the claim.

## Review checklist for docs PRs
- Claim statement includes status label.
- Claim statement includes formula regime tag where applicable.
- Every numeric claim has artifact citation.
- Baseline comparison present for performance claims.
- Limitation statement present.
- Language does not use forbidden phrases.
