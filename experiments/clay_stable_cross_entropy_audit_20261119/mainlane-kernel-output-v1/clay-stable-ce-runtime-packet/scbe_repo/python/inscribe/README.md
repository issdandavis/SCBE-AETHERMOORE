# inscribe

Compact, exact numerics for agentic code work — three small standalone tools (stdlib only).

## 1. Inscription by ratios
Represent a value as a compact **ratio** (bounded notation), and climb a continued-fraction ladder of ever-better ratios from very little information.

```python
from python.inscribe import inscribe, ladder
inscribe(3.14159265, max_denominator=1000)["ratio"]   # (355, 113), error ~3e-7
ladder(3.14159265)   # [3/1, 22/7, 333/106, 355/113, ...] each more accurate
```
Three tiny integers pin pi to ~1e-7 — few symbols, high accuracy.

## 2. Extrapolation from small information
A few exact samples of a polynomial relationship reconstruct it **exactly** (Newton divided differences over rationals); predicting far points has zero error. The bounded notation is the short coefficient list — `n` points fix a degree `< n` polynomial.

```python
from python.inscribe import extrapolate, reconstruction_error
extrapolate([(0,0),(1,1),(2,4)], 100)   # -> 10000  (x^2 from 3 points, exact)
reconstruction_error(train4pts, holdout) # -> 0.0   for cubic data
```
**Scope (honest):** this is 1-D and exact for polynomial data. The same divided-difference scheme extends to tensor-product **multi-dimensional** grids and to rational (Padé) fits for non-polynomial data — noted as the next step, **not built here** (so it isn't oversold).

## 3. Tokens as numbers (bijective numeration)
Set a token series as your "number set" and it *is* a positional number system. With `k` symbols, **bijective base-k** gives every non-negative integer exactly one finite token sequence and back — no leading-symbol ambiguity. So you `decode → operate → encode`, and the tokens carry the arithmetic.

```python
from python.inscribe import TokenNumbers
tn = TokenNumbers("KO AV RU CA UM DR".split())   # base 6
tn.decode(tn.add(tn.encode(7), tn.encode(8)))     # -> 15
tn.decode(tn.mul(tn.encode(6), tn.encode(7)))     # -> 42
```
Any ordered, unique alphabet works — a Sacred-Tongues 256-token grid becomes a bijective base-256 number system. This module stays standalone and takes the alphabet as data.
