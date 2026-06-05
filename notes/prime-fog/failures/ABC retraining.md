---
tags: [prime-fog, failure, lesson]
updated_at: 2026-06-04
---

# ABC retraining

Retrained [[centroid_a]] on A+B+C combined, then tested on F.

## Result

```text
cen_abc pure centroid on F: 4/231
cen_a pure centroid on F: 12/231
```

Retraining on more ranges made the model WORSE.

## Why

Mixing A/B/C averages anchor populations from 3 ranges with different local field structures. The centroid weights either flip sign or zero out across ranges — discriminative features cancel. A single-range model (trained on A) generalizes better because it learned clean signal from one consistent anchor population.

## Lesson

More training data is not always better when the distributions are heterogeneous. The [[cen_std]] anomaly on D is an example of this: D's anchor population is structurally different from A/B/C, and averaging them together destroys the signal.

## Related

- [[centroid_a]] — the model that works
- [[frz_skew]] — heterogeneous boards also have different frz_skew; mixing loses this signal
