---
tags: [prime-fog, residue-wheel, alignment-ledger, axis-gate, falsification]
updated_at: 2026-06-05
---

# Residue Wheel Axis

Status: FALSIFIED as a standalone search lane.

This was the cheap exact-arithmetic frontier after the smooth/log/residue-rank families died.

## Axis

Implemented in `scripts/research/prime_alignment_ledger.py`:

`residue_wheel_frequency`

Definition:

```text
score(row) = frequency of scan_prime mod 210 among candidate rows in the same board
```

It is label-free:

- uses `scan_prime`,
- uses no `future_anchor`,
- uses no `first_anchor_*`,
- uses no tuned anchor residue list.

Artifact:

`artifacts/prime_alignment_ledger_residue_wheel/gate_demo.json`

Run:

```powershell
python scripts\research\prime_alignment_ledger.py --rings K,L,M,N --gate-demo --gate-seeds 120 --axes frozen,residue_wheel_frequency --out-dir artifacts\prime_alignment_ledger_residue_wheel
```

## Result

| Ring | Precision | Null p95 | Count error | Verdict |
| --- | ---: | ---: | ---: | --- |
| K | 0.342 | 0.367 | +263 | FAIL precision, FAIL count |
| L | 0.338 | 0.351 | +222 | FAIL precision, FAIL count |
| M | 0.387 | 0.402 | +232 | FAIL precision, FAIL count |
| N | 0.354 | 0.367 | +207 | FAIL precision, FAIL count |

Verdict: rejected. This axis is below its own random.shuffle precision null and severely over-predicts clusters.

## Index-Primality Caveat

The exact `pi(p)` / `is_superprime` ledger field is valid as truth metadata, but not automatically valid as a search-axis score.

Using `first_anchor_prime`, `first_anchor_idx`, or the ledger's known anchor `prime_index` to score candidate rows would leak the target.

`scan_idx` is also not `pi(scan_prime)`; in the field scanner it is the event index in the superprime-event stream. So `is_prime(scan_idx)` is not a clean superprime-index axis.

The safe status is:

- exact index-primality is already landed as ledger truth with `--with-index`,
- no non-leaking index-primality row score is currently wired,
- do not promote index-primality as a lane until the score can be computed from visible row state only.
