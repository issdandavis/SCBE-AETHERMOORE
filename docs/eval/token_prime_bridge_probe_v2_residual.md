# Token-Prime Bridge Probe v2 Residual Gate

Date: 2026-06-05

## Question

v1 showed that prime-specific coordinates beat an equally rich monotone-index
sidecar on the `gap_next_bucket` slope-edge target. v2 asks the stricter
question:

```text
Does any signal remain after the known wheel / residue-admissibility part is
given to the baseline?
```

This is the falsifier for the "new structure" interpretation. If the residual
arm fails here, the v1 signal is real and useful, but explained by known
residue geometry.

## Setup

Target:

```text
gap_next_bucket = small / normal / large by gap_next / log(p)
```

Feature arms:

- `monotone_index`: smooth density/index coordinates only.
- `wheel_admissibility`: monotone coordinates plus mod 6 / 30 / 210 residue
  phases and the mod-30 lane.
- `full_residual`: wheel baseline plus backward features: `gap_prev`,
  `gap_prev/log(p)`, past-only composite fraction, and small-factor pressure of
  `p-1` and `p+1`.

The arms are padded to equal feature width. The headline metric is:

```text
delta_full_minus_wheel
```

and it must beat a paired shuffled-label delta null. This avoids counting a
plain "full beats null" result as residual evidence when the wheel baseline
already explains the lift.

Command:

```bash
python scripts/eval/token_prime_bridge_probe_v2_residual.py
```

## Result

Default run:

```text
WHEEL_ADMISSIBILITY_EXPLAINS_SIGNAL
N=4000 train=2600 test=1400 nulls=400
monotone_index: bal_acc=0.3486 raw_acc=0.3914
wheel_admissibility: bal_acc=0.4002 raw_acc=0.4521
full_residual: bal_acc=0.3899 raw_acc=0.4400 null95=0.3651 p=0.0075
delta_wheel_minus_monotone=0.0516
delta_full_minus_wheel=-0.0103
paired_delta_p95=0.0181
paired_delta_p=0.7980
```

Larger check:

```text
N=6000, nulls=200
monotone_index: 0.3497
wheel_admissibility: 0.4324
full_residual: 0.4333
delta_full_minus_wheel=0.0009
paired_delta_p95=0.0171
paired_delta_p=0.4776
```

Artifacts:

```text
artifacts/eval/token_prime_bridge_probe_v2_residual.json
artifacts/eval/token_prime_bridge_probe_v2_residual_n6000.json
```

## Interpretation

The v1 result is not decorative: prime residues do predict the
density-normalized next-gap edge better than a monotone position baseline.

But the stricter v2 result says the lift is explained by known
wheel/admissibility geometry. Adding backward gap, past local phase, and
neighbor-pressure features does not beat the wheel baseline under the paired
delta null.

So the corrected claim is:

```text
The slope-edge coordinate is useful known geometry, not evidence of new
residual prime structure.
```

That is still valuable for an atlas/corridor system: it tells the map which
known boundary is load-bearing.
