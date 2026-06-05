# Prime Fog Known-Solution Rings

Date: 2026-06-04

## Framing

The current prime-fog benchmark is a known-solution trajectory problem.

The verifier already knows the rings:

```text
anchor = future prime-gap event where abs(ratio) >= 4.0
```

The search engine does not get to use that predicate while flying. It only sees the local field before the anchor. The task is to build a trajectory rule that lines up with as many verifier rings as possible before the verifier reveals them.

In the video-game analogy:

- The hidden anchors are the rings in the sky.
- Each sensor lane is a camera, flashlight, map, or parallax layer.
- A gate/ranker is the rocket controller.
- The answer is not one ring. The answer is the path that hits ring after ring without being handed the next ring during flight.

## Known Verifier Rings

These are the known solution sets we can verify against. Counts are unique hidden anchors in each range.

| Ring board | Prime range | Known hidden anchors | Status |
| --- | ---: | ---: | --- |
| A | 100M-150M | 235 | calibration / fit and holdout source |
| B | 150M-200M | 227 | validation board |
| C | 200M-250M | 256 | validation board |
| D | 250M-300M | 220 | anomaly board |
| E | 300M-350M | 224 | transfer board |
| F | 350M-400M | 231 | consumed retrodiction board |
| G | 400M-450M | 214 | blind test board, now consumed |

Verifier artifacts and generators:

- `scripts/research/run_prime_search_engine_bench.py`
- `scripts/research/range_regime_classifier.py`
- `artifacts/prime_fog_row_cache/field_rows_l*_w36_h12_a4p0.json`
- `artifacts/range_regime_classifier/RESULTS.md`
- `artifacts/range_regime_classifier/regime_classifier_v2.json`
- `artifacts/prime_search_engine_bench_100_200_hidden_numbers/known_unknown_catalog_latest.json`

## Known Trajectory Solutions

These are not truth predicates. They are trajectory controllers learned or derived from known rings.

| Trajectory rule | Meaning | Best known use | Verified score |
| --- | --- | --- | ---: |
| `frozen_gate` | Conservative camera. Preserves stable local field structure. | baseline across boards | B 11/227, C 6/256, D 7/220, E 6/224, F 11/231, G 10/214 |
| `dominant` | Adversarial frozen plus centroid; suppress frozen and let centroid steer. | default for A/B/C/E and G | G 11/214, +1 vs frozen |
| `magnitude` | D anomaly controller: positive frozen magnitude plus centroid. | D-like tight centroid distribution | D-regime transfer to E 8/224; D in-sample 14/220 |
| `frozen_coherent` | Cooperative frozen plus centroid. Preserve frozen and add centroid. | F | F 16/231, +5 vs frozen |
| `centroid_a` | Learned centroid from A; strong independent route. | B/C/D/E/F diagnostics | B 14/227, C 12/256, D 8/220, F pure centroid 12/231 |
| `dynamic per-range optimal` | In-sample ceiling by sweeping weights on the same board. | diagnostic only | B 14/227, C 15/256, D 14/220, E 13/224, F 16/231 |
| `lambda_shadow_only` | PNT/von-Mangoldt flashlight. | orthogonal scouting lane | B 10/227 with zero frozen overlap |
| `graph_map_only` | Local landmark/road-sign graph lane. | orthogonal scouting lane | B 7/227 |
| `CMPSSZ only` | Cross-manifold phase-shifted zone lane. | fourth scout lane | B 12/227, C 8/256, D 11/220, mostly non-overlap with frozen |
| `answer_backprop_distiller` | Reverse known anchors into lane attribution. | diagnostic, not net-positive selector yet | confirms lane winners but quota selector loses frozen hits |

## Known Failed Paths

These failures are solutions too: they tell us which trajectories miss rings.

| Failed path | What it taught |
| --- | --- |
| Row-hit scoring | Overlapping windows inflate hits; unique anchor scoring is the real metric. |
| Oracle row score | Can score 17/20 rows but only 8 unique anchors; duplicate surfing is not discovery. |
| ABC retraining | Mixing heterogeneous boards cancels discriminative centroid signal; cen-ABC collapsed on F. |
| RRF ensemble | Top-k selected methods were too correlated with the same local overfit. |
| Router argmax | Z-score argmax routed too many anchor rows away from frozen because lane distributions are skewed. |
| 3-regime v2 on G | `frz_skew > 0.4495` detected high frozen skew but picked the wrong cooperative controller. |

## Regime Ring Map

The regime labels are the current best description of which controller should fly each board.

| Board | Known best regime interpretation | Key evidence |
| --- | --- | --- |
| A | dominant | default non-D/non-coherent calibration board |
| B | dominant / centroid-friendly | frozen baseline 11/227; centroid/dynamic reaches 14/227 |
| C | dominant / centroid-friendly | frozen weak at 6/256; dynamic reaches 15/256 |
| D | magnitude anomaly | `cen_std=0.9591`, below `0.97974`; D-regime weights work |
| E | dominant | D-regime transfer gives 8/224, but E in-sample ceiling is 13/224 |
| F | frozen_coherent | `frz_skew=0.5135`; cooperative reaches 16/231 |
| G | compressed_frozen / dominant-needed | `frz_skew=0.7379`, `frz_mean=0.2152`, `frz_std=0.9241`; cooperative collapses to 4/214, dominant reaches 11/214 |

## Current Cascade and Break

Current v2 cascade:

```text
if cen_std < 0.97974:
    magnitude
elif frz_skew > 0.4495:
    frozen_coherent
else:
    dominant
```

This retrodicts A-F, but G breaks it.

G has even stronger frozen skew than F, but the frozen distribution is compressed and shifted:

```text
F: frz_skew=0.5135, frz_mean=0.0904, frz_std=1.0002
G: frz_skew=0.7379, frz_mean=0.2152, frz_std=0.9241
```

So `frz_skew` is necessary but not sufficient. The next controller needs a fourth split:

```text
if cen_std < 0.97974:
    magnitude
elif frz_skew > 0.4495 and frz_mean > 0.15 and frz_std < 0.95:
    compressed_frozen
elif frz_skew > 0.4495:
    frozen_coherent
else:
    dominant
```

The proposed `compressed_frozen` label is retrodictive from G. It should not be treated as validated until tested on H or later.

## What Counts As A Real Solution

A real solution is not:

```text
find the anchor after seeing the anchor
```

A real solution is:

```text
known anchors -> reverse into visible pre-anchor rule -> freeze rule -> test on unseen board
```

Allowed during calibration:

- anchor catalog
- lane attribution against known anchors
- postmortem of missed/found anchors
- retrodictive regime labels

Forbidden during flight:

- direct anchor truth
- same-board in-sample weight search presented as blind result
- picking the regime after seeing which regime hit more anchors

## Next Ring

The next meaningful board is H, not G. G is now consumed.

Use the G failure to freeze a v3 controller, then test the trajectory on the next unseen range:

```text
H = 450M-500M
```

Success criterion:

```text
v3 predicted controller on H >= frozen baseline on H
and preferably adds new unique anchors without losing most frozen hits
```

That is the game loop: use old rings to tune the flight model, then fly through the next ring before checking the answer.
