# Nature's Ruler — a universal ratio-measuring device

A single instrument: point it at any set of quantities, get their relationships
back as **interpretable ratios** (3:2, not 1.4983), with a built-in **level** that
says which ratios are *real* and which are just a decimal it had to round.

Not tied to any other system — it stands alone. You can hand it lengths,
densities, angles, frequencies, intervals, anything measurable.

## The idea

- **One line, fixed length.** Everything is read as a ratio off a chosen **seed**
  (the "one"). On a log line, products become sums of lengths and ratios become
  differences — so the line is also a slide rule.
- **Read as a ratio, not a decimal.** The readout snaps to the simplest rational
  a/b (a "gear"), so a measurement comes back as something you can reason about.
- **The level (the honest part).** A physical ratio is usually irrational, so the
  snap is an approximation. The level glows only when the quantity *really* sits on
  that ratio — tighter than a random number would land on a simple ratio by chance
  (a pre-fixed density null). φ (the worst-approximable number) never glows; it can
  only be cornered by Fibonacci ratios (34:21) and the device says "don't trust it."
- **Measure before you measure.** Lay the ruler beside a measured trajectory, fit
  the part you have, and the marks past your data predict the rest. Verify by the
  gap — like eyeballing a ruler against an edge.
- **Calibrate on hard knowns.** Fine-tune the device against exact, verifiable
  references (primes are ideal — exact, an infinite ladder), validating on a
  **held-out** set so it's calibration not overfit. It then carries a *certified
  tolerance*: any unknown it measures is reported within that bound.
- **Reframe across axes.** In a hyperbolic (Poincaré) ball you can angle/skew the
  line through many frames; the right (congruent) measurement reads the **same at
  every angle**. An alignment that survives all angles is real; one that appears at
  only one skew is an artifact. Invariance-across-frames is the level for curved space.

## Files

| file | what it is |
|---|---|
| `nature_ruler_tool.py` | **THE device.** `NatureRuler.read / between / ahead`. Self-contained. |
| `nature_ruler.py` | Visual ruler + glowing-bubble level (SVG); constants etched by log. |
| `ratio_caliper.py` | The fluid use-case (Galileo's sector) — read densities as ratios. |
| `calibrate_ruler.py` | Calibrate on known primes, held-out, emit a certified tolerance. |
| `hyperbolic_ruler.py` | Reframe across angles; congruence-invariance (Möbius) = the level, curved. |
| `prime_ruler.py` | Three gearings of one line (multiply / ratio / sieve), as SVG. |
| `nth_prime_baseline_gate.py` | The prime engine that etches the marks (exact, self-verifying). |

## Use

```python
from nature_ruler_tool import NatureRuler
r = NatureRuler()
card = r.read([1.0, 1.5, 2.0, 5/3], names=["A", "B", "C", "D"])
print(card.card())          # A=seed, B=3:2 ✦, C=2:1 ✦, D=5:3 ✦
pred, _ = r.ahead([(i, float(i*i)) for i in range(1, 7)], 10)   # -> ~100
```

Verified demo: 8 fluids → trusts 3:2, 2:1, 5:3, 7:4; refuses φ, π/2, and a 0.2%-off
near-miss. Calibration drops prime-prediction error 4.5%→1.1% on held-out (±2.4%
certified). Hyperbolic reframe: d_H invariant to 1e-15 across 6 angles.

## The one rule that keeps it honest

Every readout ships with its trust. The device measures *and* tells you whether to
believe the measurement — a snapped ratio without its residual/level is just a
decimal in disguise. Calibrate before you trust; report within tolerance; an
alignment is only real if it holds across frames.
