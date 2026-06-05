---
tags: [prime-fog, cascade, hypothesis, blind-next]
updated_at: 2026-06-04
---

# cascade v3 hypothesis

The v3 hypothesis adds a fourth split after the G failure.

```text
if cen_std < 0.97974:
    magnitude
elif frz_skew > 0.4495 and frz_mean > 0.15 and frz_std < 0.95:
    compressed frozen
elif frz_skew > 0.4495:
    frozen coherent
else:
    dominant
```

## Why

[[Board G - 400M-450M]] has very high [[frz_skew]], but its frozen distribution is shifted and compressed:

```text
F: frz_skew=0.5135, frz_mean=0.0904, frz_std=1.0002
G: frz_skew=0.7379, frz_mean=0.2152, frz_std=0.9241
```

That means [[frz_skew]] alone detects frozen structure, but it does not say whether to preserve frozen or suppress it.

## Validation Boundary

This is retrodictive from G. The next valid test is [[Board H - 450M-500M]].

