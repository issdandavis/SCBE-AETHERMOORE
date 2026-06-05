# Prime Fog Gate — Dynamic Blend Weight Dynamics
**Date:** 2026-06-04  
**Ranges:** A=100M-150M, B=150M-200M, C=200M-250M, D=250M-300M, E=300M-350M  
**Metric:** unique anchor hits in TOP_N=20, abs_ratio ≥ 4.0, 36-step look-ahead  
**Scorer:** `score = w_f * frozen_z + w_a * |frozen_z| + w_c * centroid_z`

---

## What we built

A 3-parameter dynamic blend on top of the existing centroid ranker (44 features, trained on fit_a = 60% of range_a). The formula adds an **absolute value term** to the standard frozen/centroid blend:

```
score = w_f * frz_z  +  w_a * |frz_z|  +  w_c * cen_z
```

- `w_f`: direct frozen signal — negative = adversarial (penalise what frozen likes)  
- `w_a`: frozen magnitude — always positive; rewards extremes in either direction  
- `w_c`: centroid contribution  

Per-range grid search over `w_f ∈ [-1.5..+1.5]`, `w_a ∈ [0..2]`, `w_c ∈ [0.5..2]`.

---

## Results

### Frozen gate baseline

| Range | Unique hits | Total anchors |
|-------|------------:|--------------:|
| A | 8 | 235 |
| B | 11 | 227 |
| C | 6 | 256 |
| D | 7 | 220 |
| E | 6 | 224 |

### Centroid w=0.5 (balanced champion, prior session)

| Range | Hits | Delta |
|-------|-----:|------:|
| B | 12 | +1 |
| C | 12 | +6 |
| D | 12 | +5 |
| E | 7 | +1 |

### Dynamic blend — per-range optimal (in-sample)

| Range | Hits | Delta | w_f | w_a | w_c |
|-------|-----:|------:|----:|----:|----:|
| A | 14 | +6 | -1.5 | 0.0 | 1.5 |
| B | 14 | +3 | -1.0 | 0.0 | 2.0 |
| C | 15 | +9 | -1.5 | 0.0 | 1.0 |
| **D** | **14** | **+7** | **+0.5** | **2.0** | **2.0** |
| E | 13 | +7 | -1.5 | 0.0 | 1.0 |

---

## The dynamics finding

**Dominant regime (A, B, C, E):** adversarial frozen + centroid only  
- `w_f < 0`, `w_a = 0` — penalise frozen-liked rows, amplify centroid  
- No absolute value term needed  

**D anomaly (250M-300M):** frozen magnitude activates  
- `w_f = +0.5`, `w_a = 2.0`, `w_c = 2.0`  
- The only range where `|frz_z|` contributes — scores reward extreme frozen confidence in either direction, with a slight positive-frozen tilt  
- D is the only range where the frozen gate's *strength* (not direction) is informative  

**E reverts to C:** E's optimal weights are exactly C's (`wf=-1.5, wa=0.0, wc=1.0`). D did not start a new trend.

---

## Transfer test: D-regime → E

| Method | E hits | Delta |
|--------|-------:|------:|
| Frozen baseline | 6 | — |
| Centroid w=0.5 | 7 | +1 |
| D-regime transfer (wf=+0.5, wa=2.0, wc=2.0) | **8** | **+2** |
| E in-range optimal (wf=-1.5, wa=0.0, wc=1.0) | 13 | +7 |

D-regime transfer beats the balanced champion on E but falls far short of the dominant-regime ceiling. The anomaly is local to D.

---

## New anchors discovered (dynamic optimal per range)

**B** (wf=-1.0, wa=0, wc=2.0):  
`[154381351, 156270451, 159573809, 167108257, 167176297, 171804679, 173499427, 173744717, 182200267, 190247273, 192643013, 194084113, 196426591, 198397357]`

**C** (wf=-1.5, wa=0, wc=1.0):  
`[200319349, 200497183, 203086903, 213333397, 216335201, 218460953, 224697229, 227207821, 227658029, 228901927, 233064467, 233696053, 241084093, 244665229, 245843893]`

**D** (wf=+0.5, wa=2.0, wc=2.0):  
`[251552033, 252692179, 259378921, 261879529, 268649581, 271830043, 272193067, 274429567, 279987803, 280483591, 285638963, 295915273]`

**E** (wf=-1.5, wa=0, wc=1.0):  
`[304251433, 304669423, 305067979, 311697359, 312117019, 317662819, 319645813, 321055843, 323527261, 326364391, 330497897, 339392483, 341543233]`

---

## Open questions

1. **What makes D special?** The 250M-300M window is the only one where frozen gate magnitude is predictive. Is this a structural feature of prime gap distributions in that range, or an artifact of the frozen gate's training region?

2. **Can the D anomaly be predicted?** A range-regime classifier could select between the dominant regime and the D-regime before seeing the range's anchor data.

3. **In-sample vs blind gap.** All per-range optima are in-sample. The balanced champion (w=0.5, B=12/C=12/D=12) is the last confirmed blind result. The dynamic per-range ceiling (B=14/C=15/D=14/E=13) sets the target if a regime predictor can be built.

4. **Two-regime deployment.** A practical next step: train a binary range classifier on known features (frozen gate distribution moments, prime density slope, gap variance) to predict D-regime vs dominant-regime before scoring.

---

## Artifacts

- `artifacts/fill_ranker/RESULTS.md` — full comparison table  
- `artifacts/fill_ranker/fill_ranker_dynamic.json` — per-range optimal weights + dynamics map  
- `artifacts/fill_ranker/fill_ranker_a.json` — centroid_a model (champion, w=0.5)  
- Row caches: `artifacts/prime_fog_row_cache/field_rows_l*00000000_w36_h12_a4p0.json` (A through E)
