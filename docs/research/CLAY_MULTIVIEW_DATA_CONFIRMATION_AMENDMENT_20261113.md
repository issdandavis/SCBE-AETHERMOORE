# Clay multi-view data confirmation amendment — 2026-11-13

## Pre-training control correction

The first `multiview-confirm-v1` preparation process was stopped before any
optimizer horse started. Inspection of its generated labels showed that the
`static_repeated` source states were inherited from the complete paired-orbit
builder. Those states had to remain outside the held sector in all three views,
while `static_unique` states only had to remain outside it in the canonical
view. That extra eligibility filter changed the action distribution and made
the arm an invalid pure repetition control.

The correction samples the repeated arm independently from the canonical view
under the same held-sector rule as `static_unique`, then copies each selected
row exactly three times. The paired orbit remains available only as a common
gradient-coherence probe. The primary arm, controls, seeds, row counts, held
sectors, steps, stable-support threshold, and promotion gate do not change.

The partial v1 inputs are retained at:

`C:\dev\clay-training-runs\paired-orbit-data-20261113\multiview-confirm-v1`

Its abort receipt is `ABORTED_PRETRAIN.json`, state
`ABORTED_PRETRAIN_DATA_CONTROL_FIX`, with zero optimizer horses and no weights.
The corrected run uses a new `multiview-confirm-v2` directory and a new campaign
receipt. No v1 result may be used as evidence.
