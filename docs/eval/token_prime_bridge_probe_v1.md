# Token-Prime Bridge Probe v1

Date: 2026-06-05

## Question

Do prime-specific sidecar features carry measurable structure beyond an equally
rich monotone-index sidecar?

This implements the gate in `docs/eval/token_prime_bridge_probe_v1_gate_spec.md`
using real consecutive primes and a bucketed next-gap target.

## Setup

Dataset:

```text
first 4000 real consecutive primes, skipping p1=2 for previous-prime access
target = gap_next_bucket
classes = small / normal / large vs 0.75x and 1.5x log(p)
```

Feature arms:

- `prime_structure`: residue phases, `gap_prev`, `gap_prev/log(p)`,
  past-only local composite fraction, and small-factor pressure of `p-1` and
  `p+1`.
- `monotone_index`: equal-width smooth index/log/power/sin-cos features with no
  prime lookup.

Important implementation hardening:

- The local phase feature is **past-only** (`[p-radius, p-1]`), not centered on
  `[p-radius, p+radius]`, to avoid seeing the future gap being classified.
- Prime and monotone feature widths are asserted equal.
- The target name is absent from feature names.
- The monotone sidecar is audited for no prime-derived columns.
- Score is balanced accuracy, not retrieval rank.

Command:

```bash
python scripts/eval/token_prime_bridge_probe_v1.py
```

## Result

```text
PRIME_STRUCTURE_ADDS_SIGNAL
N=4000 train=2600 test=1400 nulls=400
class_distribution={'small': 1881, 'normal': 1309, 'large': 810}
prime_structure: bal_acc=0.4151 raw_acc=0.4593 null95=0.3747 p=0.0025
monotone_index: bal_acc=0.3463 raw_acc=0.3757 null95=0.3578
majority_floor: bal_acc=0.3333 raw_acc=0.4771
delta_prime_minus_monotone=0.0688 null_noise_margin=0.0253
```

Artifact:

```text
artifacts/eval/token_prime_bridge_probe_v1.json
```

## Interpretation

This is the first controlled token-prime bridge result where the prime-specific
sidecar beats:

- its shuffled-label null,
- the majority-class balanced-accuracy floor,
- and an equally rich monotone-index sidecar by more than null-noise.

So the v1 answer is not "prime is decorative" for this narrow target. Prime
residue / prior-gap / neighbor-pressure features carry measurable structure for
the real-prime `gap_next_bucket` task.

Follow-up: `docs/eval/token_prime_bridge_probe_v2_residual.md` splits this
signal against a residue-admissibility baseline. That stricter gate finds the
v1 lift is explained by known wheel geometry, not by a new residual structure.

## Projection Framing

This is also the concrete form of the "prime wall / slope over edge" transform:

```text
raw prime line     p_n
accumulated wall   W(n) = sum(log(p_k))
local slope        r_n = gap_next / log(p_n)
edge crossing      gap_next_bucket = small / normal / large
```

The model is not chasing the next prime in raw value-space. It rotates the
sequence into a density-normalized slope coordinate and asks whether known
prime-specific structure predicts which edge the next gap crosses. The answer
here is modest but positive: residue / prior-gap / neighbor-pressure features
predict that edge better than an equally rich monotone-index coordinate.

This framing is interpretive, not a new input leak: `gap_next/log(p)` defines
the target bucket, while the inputs remain past-only or current-prime features.

## Claim Discipline

This still does **not** prove a tokenizer or LLM improves. It proves a
prime-specific sidecar can beat a monotone index control on a real arithmetic
classification target.

The next downstream test remains:

```text
baseline router/retriever
vs
baseline + sidecar coordinates
```

measured on a real retrieval, routing, attention-stability, or audit task.
