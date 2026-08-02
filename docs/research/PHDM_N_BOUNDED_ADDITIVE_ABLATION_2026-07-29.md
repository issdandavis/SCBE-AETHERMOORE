# PHDM n-bounded additive ablation

Date: 2026-07-29

## Verdict

Keep the `n_bounded` projection as an additive alternative after the
fail-closed corrections in `python/scbe/phdm_embedding.py`.

The result is narrower than the original claim:

- The radius map preserves caller-supplied structural depth in representable
  float64 ranges.
- It improves structural-address retrieval on real SCBE Python ASTs.
- It does not change the default `PHDMEmbedder.encode()` path.
- It has produced no Clay language-model gain and no GitHub-governance gain.
- The legacy `r**196` helper becomes depth-sensitive but remains bounded by
  one. It is not the registered unbounded Harmonic Wall.

## Primary-path conservation

The executable body of `PoincareBall.embed()` remains identical to `HEAD`.
An exact comparison over 6,004 vectors produced 6,004 identical outputs.
An end-to-end comparison over 1,003 fixed-context text encodings produced
1,003 identical 21D embeddings.

The out-of-ball primary result remains:

```text
[2, 0, 0, 0, 0, 0] -> [0.99999, 0, 0, 0, 0, 0]
```

Therefore the new results are opt-in and additive. Existing callers do not
receive them accidentally.

## Correct radius measurements

For the unit ball:

```text
r(n) = tanh(n / 2)
d_H(0, r) = 2 * atanh(r)
```

Measured in float64:

```text
depth   radius                  recovered d_H        absolute error
1       0.46211715726000974     0.9999999999999999   1.1e-16
2       0.76159415595576485     1.9999999999999998   2.2e-16
3       0.90514825364486651     3.0000000000000009   8.9e-16
4       0.96402758007581690     4.0000000000000009   8.9e-16
10      0.99990920426259511     9.999999999999746    2.5e-13
20      0.99999999587769273    19.999999991040749    9.0e-09
```

“Exact integer” is display-level, not bit-exact. Float64 rounds
`tanh(depth/2)` onto the boundary at integer depth 38. The alternative now
rejects depths that cannot remain inside the open ball instead of returning a
false depth. Float32 and float16 are not used for this projection because they
collapse much earlier.

## Legacy radial gate correction

The local helper computes:

```text
gate(r) = r ** 196
```

Measured:

```text
depth 1    1.956186e-66
depth 4    7.612616e-04
depth 10   9.823607e-01
clamp      9.980419e-01
```

Depth 1 through 10 spans 65.7009 decimal orders, not 62. The 62.5901-order
span is depth 1 through 4.

This is a steep bounded radial gate. It is convex as a function of radius, but
as a function of depth it inflects near depth 5.9713 and saturates toward one.
It must not be cited as the registered `QUADRATIC_EXP_COST`, whose base is
greater than one and whose distance is the exponent input.

## Real-code structural-address experiment

Script:

```text
scripts/eval/phdm_ast_parent_ablation.py
```

Task:

- Deterministic corpus: the first 20 `python/scbe/*.py` files used by the
  existing encoder benchmark.
- Bounded prefix: at most 256 AST nodes per file.
- Honest depth: Python AST traversal depth.
- Direction features: node-type one-hot, six face trits, and eight bytes from a
  token SHA-256 digest.
- Excluded from direction: depth, parent, path, location, child index, and
  source index.
- Common seeded projection: 80 features to the six PHDM hyperbolic dimensions.
- Target: rank the true parent against every other node in the same file.
- Metrics: parent mean reciprocal rank, Recall@1, and Recall@5.
- Gate: gain must exceed two pooled sample standard deviations.

Arms:

```text
flat Euclidean
untouched primary clamp with Poincare distance
n-bounded with Poincare distance
n-bounded coordinates with Euclidean distance
linear depth with Euclidean distance
n-bounded with depth shuffled within each file
```

### Independent seed band A

Seeds 0 through 19:

```text
arm                         MRR       Recall@1   Recall@5
n-bounded hyperbolic        0.06193   0.01472    0.08590
linear-depth Euclidean      0.04882   0.00754    0.05988
primary clamp               0.02735   0.00364    0.02541
shuffled depth              0.02713   0.00401    0.02347
random rank expectation     0.03267   0.00626    0.03131
```

Against the primary clamp, all three gains passed:

```text
metric       gain       2 * pooled SD
MRR          0.03458    0.00992
Recall@1     0.01108    0.00580
Recall@5     0.06049    0.01923
```

Against the size-matched linear-depth control:

```text
metric       gain       2 * pooled SD
MRR          0.01311    0.01179
Recall@1     0.00719    0.00689
Recall@5     0.02603    0.02457
```

All three passed, but the Recall@5 margin was narrow.

### Independent seed band B

Seeds 1000 through 1019:

```text
arm                         MRR       Recall@1   Recall@5
n-bounded hyperbolic        0.06125   0.01530    0.08317
linear-depth Euclidean      0.04777   0.00788    0.05780
primary clamp               0.02657   0.00343    0.02358
shuffled depth              0.02613   0.00317    0.02250
random rank expectation     0.03267   0.00626    0.03131
```

Against the primary clamp, all three gains passed:

```text
metric       gain       2 * pooled SD
MRR          0.03468    0.00877
Recall@1     0.01188    0.00570
Recall@5     0.05959    0.02013
```

Against the size-matched linear-depth control:

```text
metric       gain       2 * pooled SD
MRR          0.01348    0.01047
Recall@1     0.00742    0.00677
Recall@5     0.02537    0.02510
```

All three passed again. Recall@5 cleared the gate by only 0.00027, so it is the
weakest reproduced result.

### Effect size and absolute boundary

Across the two independent bands, n-bounded hyperbolic was approximately:

```text
versus primary clamp
MRR          2.26x to 2.31x
Recall@1     4.04x to 4.47x
Recall@5     3.38x to 3.53x

versus random ranking
MRR          1.88x to 1.90x
Recall@1     2.35x to 2.44x
Recall@5     2.66x to 2.74x
```

The absolute result remains modest: roughly 1.5% Recall@1 and 8.3% to 8.6%
Recall@5. This is a useful additive structural signal, not a standalone parent
resolver.

Noise-scale checks at 0, 0.005, and 0.02 retained the MRR and Recall@5 gain
against the linear-depth control. Recall@1 was underpowered at noise 0.005 by
0.0000014, so the incremental Recall@1 claim is less stable than MRR.

## Synthetic mechanism control

Script:

```text
scripts/eval/phdm_n_bounded_ablation.py
```

On a complete depth-four binary tree at the real PHDM width of six dimensions,
two independent 100-seed bands reproduced:

```text
candidate tree-distance Spearman     0.9282 / 0.9250
primary clamp Spearman               0.7138 / 0.7070
candidate normalized stress          0.1527 / 0.1535
primary clamp stress                 0.3443 / 0.3447
```

The candidate beat the primary and matched fixed-radius controls on global
tree distortion. Against linear Euclidean depth coding, stress passed but
Spearman remained underpowered. Parent and same-depth sibling top-1 accuracy
were identical to the linear control. The mechanism improves global distance
organization; the synthetic test does not show a local retrieval gain.

## Implementation hardening

The additive path now:

- rejects negative, missing, NaN, and infinite depths;
- rejects NaN and infinite direction vectors;
- accepts a zero direction only at depth zero;
- emits float64 coordinates;
- rejects depths that round onto the Poincare boundary;
- returns JSON-serializable decision records;
- states that provenance exists when callers use `project()`, not universally;
- labels the local `r**196` output as an unregistered legacy radial profile;
- keeps the primary clamp body unchanged.

Focused verification:

```text
44 passed
```

This includes the new strategy, receipt, synthetic-ablation, AST-ablation,
legacy PHDM suite, and inverse-embedding tests.

## Operational boundary and next gain test

`PHDMEmbedder.encode()` still selects the primary clamp. The only production
caller found, `api/github_app/scoring.py`, uses that unchanged method. Current
runtime and Clay gain are therefore exactly zero.

Do not derive governance depth from risk hits, privileged-file counts, or the
expected decision; that would leak the target.

The next additive training experiment should use an honest structural lane,
such as AST depth in Clay's coding corpus:

1. untouched parent model;
2. n-bounded structural side channel;
3. same-parameter linear-depth side channel;
4. shuffled-depth side channel;
5. at least three seeds;
6. next-token/coding metric, protected-skill regression, and runtime;
7. promotion only if n-bounded beats the parent and both matched controls by
   more than two pooled standard deviations.

No production caller, model weight, or governance threshold was changed by
this experiment.
