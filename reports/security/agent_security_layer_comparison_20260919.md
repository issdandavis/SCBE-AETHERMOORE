# Agent Security Layer Comparison

Cases: 36 (18 deny / 18 allow).

| Arm | Attack detection | False positives | Benign allowed | Balanced accuracy |
|---|---:|---:|---:|---:|
| no_guard | 0.0% | 0.0% | 100.0% | 50.0% |
| lexical_baseline | 0.0% | 11.1% | 88.9% | 44.4% |
| scbe_custom | 50.0% | 11.1% | 88.9% | 69.4% |
| combined | 55.6% | 22.2% | 77.8% | 66.7% |

## Runtime

Full detector median: 5210.7 µs; p95: 5974.7 µs across 108 evaluations.

## Interpretation

Research claim status: **UNDERPOWERED**. The three runs permute one fixed holdout and are not independent samples; there is no size-matched implementation control. Treat this as engineering evidence.

The JSON report contains per-seed confusion matrices and case IDs for incremental catches and false positives. It intentionally excludes prompt text.
