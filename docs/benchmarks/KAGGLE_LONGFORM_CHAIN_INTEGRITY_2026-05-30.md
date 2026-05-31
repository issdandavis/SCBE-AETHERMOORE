# Kaggle Longform Chain Integrity Benchmark - 2026-05-30

Status: completed on Kaggle.

Kernel:
https://www.kaggle.com/code/issacizrealdavis/scbe-longform-chain-integrity-benchmark

## Result

| Metric | Value |
|---|---:|
| Score | 105 / 105 |
| Percent | 100.0% |
| Attack classes | 8 / 8 |
| Cold-start resume | Pass |
| Kaggle kernel version | 3 |

## What Was Tested

The benchmark tests the SCBE Longform Bridge ledger and landing semantics:

- A1 payload byte-flip
- A2 event hash field flip
- A3 event insertion without recompute
- A4 event deletion
- A5 adjacent event swap
- A6 hash-field substitution
- A7 full recompute after payload mutation
- A8 anchored-prefix truncation
- R1 cold-start resume verification in a subprocess

The important result is A7/A8: `verify_chain()` intentionally accepts a
fully-recomputed internally consistent chain, but `ContextLanding.verify_semantic()`
detects the payload mutation or anchored-prefix truncation because the landing
seals `event_count` and `semantic_anchor`.

## Kaggle Output

Downloaded evidence:

- `artifacts/kaggle/scbe-longform-chain-integrity/remote-output-v3/longform_chain_integrity_latest.json`
- `artifacts/kaggle/scbe-longform-chain-integrity/remote-output-v3/longform_chain_integrity_latest.md`
- `artifacts/kaggle/scbe-longform-chain-integrity/remote-output-v3/scbe-longform-chain-integrity-benchmark.log`

Summary from Kaggle log:

```json
{
  "score_percent": 100.0,
  "earned": 105,
  "max": 105,
  "all_passed": true,
  "a7_semantic_detected": true,
  "a8_semantic_detected": true
}
```

Performance table from Kaggle:

| Events | `verify_chain()` ms |
|---:|---:|
| 50 | 2.088 |
| 100 | 4.647 |
| 250 | 5.926 |
| 500 | 11.297 |

## Local Reproduction

```powershell
python scripts/benchmark/longform_chain_integrity.py --out-dir artifacts/benchmarks
```

Local pre-push validation also scored `105 / 105`.

## Claim Boundary

This benchmark supports the narrow claim that the current Longform Bridge
implementation detects the listed ledger mutation classes under the benchmark
model. It does not prove general security against all filesystem compromise or
all adversaries. The result is evidence for the semantic landing anchor closing
the two previously identified write-access drift cases within this test harness.
