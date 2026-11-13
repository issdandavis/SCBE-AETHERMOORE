# Clay hash-spread specificity launch receipt — 2026-11-13

Status: active headless optimizer training; no promotion or partial unfreeze.

## Launch

The preregistered shuffled-factor versus deterministic hash-spread campaign is
running at:

`C:\dev\clay-training-runs\paired-orbit-data-20261113\multiview-hash-specificity-v1`

- Git source: `21d614f568032e65717760cba3c712568079a4f3` (pushed).
- Headless launcher PID at start: `23000`.
- Training worker PID at start: `16292`.
- Device: NVIDIA GeForce GTX 1660 Ti with Max-Q Design; CUDA required by CLI.
- Horses: 60 (`4 arms x 5 seeds x 3 held sectors`).
- Model seeds: `419/431/443/457/461`.
- Rows per arm/fold: 30,000.
- Training draws per horse: 4,800 steps x 192 = 921,600.
- Standard learner: 37 -> 64 -> 64 -> 5, 6,917 trainable scalars.

The process was launched through `C:\dev\pc-health\run_headless.py` with
redirected streams and `CREATE_NO_WINDOW`.  Existing results and weights were
not overwritten.

## Campaign data preflight

All three locked-seed folds completed before optimizer execution.  Each built
180,000 training-only candidates and four matched 30,000-row arms.  Every fold
reported zero selected-index overlap, zero exact-feature overlap, false
holdout use, false post-outcome use, and higher conditional hash entropy for
the hash-spread arm than the shuffled-factor and random arms.

| Held sector | Selection receipt | Hash entropy | Shuffled entropy | Random entropy |
| ---: | --- | ---: | ---: | ---: |
| 1 | `6dd737048c8d24e43665f0f8249b4e153acef732ad4dbe872e841ace1d4da1b6` | 0.999987 | 0.997949 | 0.997927 |
| 4 | `1716904be6fd4a60369270fdae8c8a8f0fd12ad3e37c60bca2353826ff8332b6` | 0.999986 | 0.997961 | 0.998008 |
| 7 | `ab339a6c0d49ef466addc1c2948b028b8a2ac122c6a36305a4023ddff84f1c34` | 0.999988 | 0.997921 | 0.997851 |

An external pre-launch smoke check used seed `2038111301`, not a campaign
seed.  Its receipt
`cc6d9d794f7f8e71ff2a5f99dec2864c9875305560b17e0f31e00199f930d28b`
is retained as a mechanism check but is not training lineage.  The three rows
above are authoritative.

## First optimizer evidence

At `2026-11-13T07:23:13-08:00`, horse 3/60 was active.  The first two
`static_unique`, held-sector-1 controls completed and changed all 6,917
trainable scalars:

| Seed | Best step | Held accuracy | Stable F1 | Anchor accuracy | Result receipt |
| ---: | ---: | ---: | ---: | ---: | --- |
| 419 | 4,600 | 0.8010 | 0.8413 | 0.9844 | `bd7ea0d982f25b6ec0c56f155d56b54538d2b5ced72448906fceeb07efaa2335` |
| 431 | 3,200 | 0.7964 | 0.8271 | 0.9830 | `97cd237170134c907a82fe81fba2aac820a9377afe557688613f8718188c1883` |

These are early baseline observations, not a selection result.  Outcome claims
remain locked until all 60 horses complete, the sector gate is independently
recomputed, and the source-pinned exposure auditor reconstructs the exact row
counts.  No intermediate result authorizes model promotion, deployment,
execution authority, deletion, or partial unfreezing.

## Verification before launch

- 22 neighboring trainer, factor, hash-spread, and exposure-audit tests passed.
- Ruff passed for all changed Python files.
- A complete miniature 24-horse campaign changed weights and emitted gate and
  market receipts.
- The repository commit and upstream branch matched before launch.

