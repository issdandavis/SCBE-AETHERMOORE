# Benchmark Verification — 2026-03-23

## Scientific method

1. Snapshot the prior artifact outputs as the baseline.
2. Rerun each benchmark script five times under the same code and corpus.
3. Record top-level metrics after every run.
4. Compare the repeated means and standard deviations against the saved baseline.
5. Run a deterministic adversarial regression suite once as a control.

- Timestamp: `2026-03-24T06:45:36.537377+00:00`
- Repeats per benchmark: `5`
- Control test: `============================== 4 passed in 0.74s ==============================`

## Reproducibility verdict

- `semantic_vs_stub`: exactly reproduced
- `hyperbolic_helix`: exactly reproduced
- `unified_triangulation`: exactly reproduced
- `null_space_ablation`: exactly reproduced

## Benchmarks

### semantic_vs_stub

| Metric | Baseline | Mean | Std | Min | Max | Delta |
|---|---:|---:|---:|---:|---:|---:|
| `semantic_detection_rate` | 0.6703 | 0.6703 | 0.0 | 0.6703 | 0.6703 | 0.0 |
| `semantic_false_positive_rate` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `semantic_ru_mean` | 0.0538 | 0.0538 | 0.0 | 0.0538 | 0.0538 | 0.0 |
| `stub_detection_rate` | 0.8022 | 0.8022 | 0.0 | 0.8022 | 0.8022 | 0.0 |
| `stub_false_positive_rate` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `stub_ru_mean` | 0.9519 | 0.9519 | 0.0 | 0.9519 | 0.9519 | 0.0 |

### hyperbolic_helix

| Metric | Baseline | Mean | Std | Min | Max | Delta |
|---|---:|---:|---:|---:|---:|---:|
| `flat_recall` | 0.5292 | 0.5292 | 0.0 | 0.5292 | 0.5292 | 0.0 |
| `flat_separation` | 1.1244 | 1.1244 | 0.0 | 1.1244 | 1.1244 | 0.0 |
| `helix_adv_radius` | 0.0849 | 0.0849 | 0.0 | 0.0849 | 0.0849 | 0.0 |
| `helix_recall` | 0.2 | 0.2 | 0.0 | 0.2 | 0.2 | 0.0 |
| `helix_separation` | 1.7618 | 1.7618 | 0.0 | 1.7618 | 1.7618 | 0.0 |
| `helix_tech_radius` | 0.055 | 0.055 | 0.0 | 0.055 | 0.055 | 0.0 |
| `poincare_recall` | 0.2833 | 0.2833 | 0.0 | 0.2833 | 0.2833 | 0.0 |
| `poincare_separation` | 1.492 | 1.492 | 0.0 | 1.492 | 1.492 | 0.0 |

### unified_triangulation

| Metric | Baseline | Mean | Std | Min | Max | Delta |
|---|---:|---:|---:|---:|---:|---:|
| `detection_rate` | 0.7582 | 0.7582 | 0.0 | 0.7582 | 0.7582 | 0.0 |
| `false_positive_rate` | 0.1333 | 0.1333 | 0.0 | 0.1333 | 0.1333 | 0.0 |

### null_space_ablation

| Metric | Baseline | Mean | Std | Min | Max | Delta |
|---|---:|---:|---:|---:|---:|---:|
| `e4_detection_rate` | 0.8571 | 0.8571 | 0.0 | 0.8571 | 0.8571 | 0.0 |
| `e4_holdout_fp_rate` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `null_detection_rate` | 1.0 | 1.0 | 0.0 | 1.0 | 1.0 | 0.0 |
| `null_helix_detection_rate` | 1.0 | 1.0 | 0.0 | 1.0 | 1.0 | 0.0 |
| `null_helix_holdout_fp_rate` | 1.0 | 1.0 | 0.0 | 1.0 | 1.0 | 0.0 |
| `null_holdout_fp_rate` | 1.0 | 1.0 | 0.0 | 1.0 | 1.0 | 0.0 |
| `null_space_fp_cost` | 1.0 | 1.0 | 0.0 | 1.0 | 1.0 | 0.0 |
| `null_space_gain` | 0.1429 | 0.1429 | 0.0 | 0.1429 | 0.1429 | 0.0 |

## Conclusions

1. All four benchmark scripts were deterministic over five reruns; the repeated outputs matched the saved baseline artifacts exactly.
2. `hyperbolic_helix_test.py` reproduced the same architecture tradeoff every time: flat retrieval wins recall, helix wins separation.
3. `semantic_vs_stub_comparison.py` reproduced the current reality that the semantic L3 path does not yet beat the stub on this exact detection logic.
4. `unified_triangulation.py` reproduced the null-space / remainder result, but it did not beat the simpler gate on detection-quality.
5. `null_space_ablation.py` reproduced the sharper finding: null space is a boost feature that can close the last 14.3% of misses, but it explodes held-out false positives when used as a universal gate.
6. The reliable claim is reproducibility of the measurements, not automatic promotion of every experimental idea.

