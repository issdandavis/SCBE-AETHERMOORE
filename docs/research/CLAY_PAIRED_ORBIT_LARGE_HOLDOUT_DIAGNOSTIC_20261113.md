# Clay paired-orbit large-holdout diagnostic — 2026-11-13

This diagnostic was added after inspecting the completed campaign's evaluation
data. Held sector 4 contained 1,000 rows but its action counts were
`[165, 0, 827, 4, 4]`; aggregate accuracy therefore looked excellent while a
four-example supported class remained at zero.

The diagnostic does not retrain or select checkpoints. It loads the already
saved best weights and evaluates them on a new, independently seeded 10,000-row
holdout and 10,000-row anchor for each held sector. It reports supported-class
macro-F1, a stable-class view requiring at least 32 natural examples, worst
supported class, absent and sparse classes, and matched fold/seed deltas. Saved
input banks are receipt-checked and may be reused for metric-only reruns; model
checkpoints remain immutable.

Because this check was motivated by inspecting the first evaluation, it is
post-hoc evidence and cannot authorize promotion or partial unfreeze.
