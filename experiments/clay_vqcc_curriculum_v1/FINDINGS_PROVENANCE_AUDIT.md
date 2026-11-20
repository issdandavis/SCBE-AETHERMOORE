# Findings provenance audit

Read-only recomputation on the exact pinned `ledger.csv` (SHA-256
`8f2ff6980a8de0321e861dde67f54cb1e9b5cc3ab59511088ee28634fd6fa490`)
found 145 eligible public findings among 309 rows.

The safe family graph connects findings only through exact nonempty `link`,
exact nonempty `family_target`, or direct `supersedes` item references. Shared
`related_cards` are citations, not identity: including them collapsed 90 of
145 eligible findings into one component and left the four-task holdout unable
to form valid different-family comparisons.

With citation edges excluded, the ledger yields 107 eligible components. The
sealed 20% split produces 117 train rows and 28 holdout rows. Both roles retain
`all`, `chemistry`, `dqi`, and `invsqrt`, and the real comparison builder emits
96 train comparisons and 14 holdout comparisons. Perfect predictions pass the
strict all-four-task scoring gate in both roles.

This proves that the proposed provenance boundary is mechanically feasible. It
does not prove learning, promotion, semantic circuit equivalence, or Kaggle
score gain. Full details are sealed in `FINDINGS_PROVENANCE_AUDIT.json`.
