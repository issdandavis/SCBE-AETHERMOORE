---
tags: [prime-fog, failure, cascade]
updated_at: 2026-06-04
---

# frozen_dominant overfit

Ring M falsified the frozen_dominant rule. Ring N confirmed the failure was not
a one-board noise point.

## Failed Rule

```text
if frz_mean > 0.45 AND frz_skew > 1.0:
    use raw frozen gate
```

The trigger fired at Ring M:

- `frz_mean = 0.60596`
- `frz_skew = 1.16726`

But raw frozen came last.

| Method | Ring M hits |
| --- | ---: |
| frozen baseline | 4/202 |
| dominant | 7/202 |
| magnitude | 6/202 |
| frozen_coherent | 9/202 |

Ring N then fired the same trigger again:

- `frz_mean = 0.62379`
- `frz_skew = 1.07750`

and raw frozen lost again:

| Method | Ring N hits |
| --- | ---: |
| frozen baseline | 10/180 |
| dominant | 9/180 |
| magnitude | 10/180 |
| frozen_coherent | 13/180 |

## Lesson

The rule was committed from too little evidence. K was only a +1 frozen win and L was a strong +8 frozen win. That made the rule depend mostly on one favorable board.

Rings M and N show `frz_skew > 1.0` is not enough to prove raw frozen is optimal. At very high `frz_mean`, the frozen spike can overconcentrate and lose diversity.

## Candidate Discriminator

`corr_frz_cen` is the candidate exit variable, but it is only one confirmed point so far:

| Ring | corr_frz_cen | Raw frozen result |
| --- | ---: | --- |
| K | -0.226 | wins +1 |
| L | -0.221 | wins +8 |
| M | -0.159 | loses -5 |

Initial M-only hypothesis:

```text
if frz_skew > 1.0 AND corr_frz_cen > -0.19:
    route to frozen_coherent
```

Ring N rejects the corr-only split: `corr_frz_cen = -0.2022`, but
frozen_coherent still wins.

Better hypothesis, still uncommitted:

```text
if frz_skew > 1.0 AND frz_mean > ~0.57:
    route to frozen_coherent
```

or use the turn signal:

```text
frz_skew falling while frz_mean remains high
frz_p90 falling while frz_mean remains high
```

Do not commit this as cascade v7 until more than two rings verify it.

## Related

- [[Ring M]]
- [[Ring N]]
- [[cascade v6]]
- [[frozen_dominant]]
- [[frozen coherent]]
- [[corr_frz_cen]]
