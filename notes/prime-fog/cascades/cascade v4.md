---
tags: [prime-fog, cascade, frozen-rule, ring-i]
updated_at: 2026-06-04
source: artifacts/range_regime_classifier/cascade_v4_spec.json
---

# cascade v4

Frozen rule update before [[Ring I]] anchor truth is checked.

## Rule

```text
if cen_std < 0.97974:
    magnitude
elif frz_skew > 0.4495 and frz_mean > 0.27 and frz_std < 0.9621:
    compressed_frozen_late -> magnitude weights
elif frz_skew > 0.4495 and frz_mean > 0.15 and frz_std < 0.9621:
    compressed_frozen_early -> dominant weights
elif frz_skew > 0.4495:
    frozen coherent
else:
    dominant
```

## Why v4 Exists

[[cascade v3]] split [[Board G - 400M-450M]] correctly but failed on [[Ring H]].

The missing variable was the late compressed-frozen phase:

```text
G: frz_mean=0.2152 -> dominant weights
H: frz_mean=0.3232 -> magnitude weights
```

Threshold:

```text
frz_mean > 0.27
```

This is the midpoint between G and H.

## Ring I Prediction

Extrapolated features:

```text
frz_skew=0.9828
frz_mean=0.4424
frz_std=0.8104
cen_std=1.0118
```

v4 prediction:

```text
compressed_frozen_late
weights = wf=+0.5, wa=2.0, wc=2.0
```

## Boundary

This is now the frozen controller for [[Ring I]]. Do not change it using Ring I anchors before scoring.

## Artifacts

- `artifacts/range_regime_classifier/cascade_v4_spec.json`
- `artifacts/range_regime_classifier/CASCADE_V4.md`
- `artifacts/inverse_bridge_map/bridge_map.json`

