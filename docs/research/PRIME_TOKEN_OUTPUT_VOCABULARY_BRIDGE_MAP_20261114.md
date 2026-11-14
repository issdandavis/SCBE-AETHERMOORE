# Prime-token pre-label output vocabulary bridge map

Status: `REUSE_FOUND_WAITING_FOR_ADMISSIBLE_LANE_AUTHORITIES`; no labels,
weights, optimizer, or model output opened
Date: 2026-11-14

## Required seam

The next material-data edge must freeze the output vocabulary before an
independent reviewer labels any query. Its categories are not learned from the
labels:

```text
verified catalog family IDs x preregistered review strata
    -> one bounded output token per pair
    -> ordinary/retention family-overlap audit
    -> immutable evaluator receipt
```

This receipt is evaluator metadata only. It cannot admit training data, score
a model, execute an action, merge a child, promote a result, or unfreeze a
parameter.

## Existing implementation to reuse

The E92 worktree already implements this contract in
`python/scbe/prime_token_material_cases.py` at commit
`dfc0de2239050fff5c39ab11888a39dc49d4255c`. Commit
`5d4c8a0f04a5f8eb33166de1dec5c44a8154ced7` independently rebuilds replay
targets from pinned sources instead of trusting producer target arrays.

`frozen_output_vocabulary` uses the verified
`scbe.prime-token-source-family-audit.v1` family list and the keys of
`EXPLICIT_ROUTE_SCOPE_COUNTS`. The fixed strata are:

- `five_w`
- `publication`
- `tongue_braid`
- `source_research`

The current v3 family audit has three manifest-bound families. The resulting
Cartesian vocabulary therefore contains exactly `3 * 4 = 12` rows. Under the
existing E92 byte assignment it occupies token IDs `224..235`; it remains
inside the 256-byte bound and does not inspect review labels. A direct replay
against the real v3 audit produced vocabulary SHA-256
`58b7feb4f2b176f6e052083ca27720c16bcf18a319363f213133e055ab6fee31`.

The implementation receipt is
`C:\dev\clay-training-runs\prime-token-catalog-20261106\successor-training-release-20261111\MATERIAL_CASE_BUILDER_IMPLEMENTATION_TEST_RECEIPT_V1.json`
with SHA-256
`338bd1561b2a29c90837e919800d21fe5360f9427a8a02455ce58533ef485dcf`.
It is explicitly mechanics-only evidence and records no material-data import
or training authority.

## Current exact inputs

The catalog-family authority is `SOURCE_FAMILY_AUDIT_V3.json`, SHA-256
`ef3f99b08d4ea1ee71c61010579012ddc515b592b44379a134a73f5fde9d9c30`.
It reports schema `scbe.prime-token-source-family-audit.v1`, status
`VERIFIED_SOURCE_FAMILY_BOUNDARY_WAITING`, zero errors, three family IDs, and
36 canonical source rows.

The newest bounded ordinary/retention bundle inspected is the frozen action
candidate bundle, not a prime-token material bundle:

- `SOURCE_AUTHORITIES.candidate.json`, SHA-256
  `fb21ddfb3d0e4f9ffe9510be067e206309df891dd5db75ab4e088a6d05b300b7`;
- 55 ordinary rows from `python-cpython-documentation`;
- 52 retention rows from `rust-lang-book`;
- `review_status = NOT_REVIEWED` and `training_authorized = false`;
- build receipt SHA-256
  `223e11cb84513bb209b7f7137136440eaf4c399c1ec3e3909799cc3513f84fc3`,
  status `COMPLETE_NOT_ADMITTED`.

Those lane rows carry `source_id`; their `source_family` mapping lives in the
separate candidate authority file. The bundle is intentionally rejected by
the campaign loader. It is useful discovery evidence, but it cannot be
silently reclassified as the prime-token ordinary/retention authority.

## Integration decision

Do not copy the candidate lane family names into the prime-token vocabulary and
do not infer equivalence between human-readable action-family names and the
hash-derived catalog family IDs. No authoritative crosswalk was found. A
literal string comparison would report no overlap while failing to prove that
both sides use the same family namespace.

Do not broad-cherry-pick the E92 material commits. The active branch and E92
branch each contain 29 commits beyond merge base
`abd1ba5962ea488d208b7b1b36a37fd47cc2d62b`; the E92 feature commit changes 15
files and more than 2,300 lines. The active query-session/family watcher must
remain intact.

The next valid build is a small extraction of the already tested
`frozen_output_vocabulary` contract after a prime-token-specific ordinary and
retention registry exists with:

1. one shared source-family namespace;
2. exact source locator and content hash per row;
3. separate ordinary and retention families;
4. a reviewed/admitted status distinct from candidate construction; and
5. an immutable hash binding the registry to the family audit and vocabulary.

Until then, status remains `WAITING`, labels stay unopened, and no scoring or
training-intake authority is created.

## Inventory receipt

The bounded active/E92 inventory is
`SYSTEM_INVENTORY_20261114_PRIME_OUTPUT_VOCABULARY.json`, SHA-256
`40491152465e716ce42aea9cd314431fe76bf4d0200f2c5238bd6d0c23c03524`.
It is discovery evidence only.
