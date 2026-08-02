# Langues Weighting System: Corrected Mathematical Contract

Status: profile-aware correction; the implementations are real, but they are
not yet one numerically identical cross-language runtime.

This document replaces the ambiguous phrase "the LWS formula" with named,
testable profiles. It does not change the patent record and does not assert
that a patent-facing claim is valid merely because related code exists.

The machine-readable registry is
[`langues_weighting_system_profiles.json`](langues_weighting_system_profiles.json).

## 1. General cost family

For six coordinates indexed by \(l=0,\ldots,5\), define the unclamped cost

\[
C(x,t)=\sum_{l=0}^{5}
\nu_l(t) w_l
\exp\left(\beta_l\left[d_l(x)+a\sin(\omega_l t+\varphi_l)\right]\right).
\]

The parameters are:

- \(w_l>0\): coordinate weight;
- \(\beta_l>0\): exponential sensitivity;
- \(d_l(x)\ge 0\): a deviation supplied by the caller or computed from an
  ideal point;
- \(a\): temporal phase amplitude;
- \(\omega_l\): angular mode;
- \(\varphi_l=2\pi l/6\): six-fold phase offset;
- \(0\le\nu_l(t)\le1\): optional fractional participation.

Some implementations return
\(\min(C(x,t),C_{\max})\). That saturation changes strict monotonicity to
nondecreasing behavior once the clamp is reached.

The scalar \(C\) is a **cost functional**, not a mathematical metric: it takes
one state plus time, is generally nonzero at the ideal state, and does not
itself provide symmetry or the triangle inequality. The separate
`langues_distance` function is a weighted Euclidean metric.

## 2. The four cost profiles actually on disk

| Profile            | Weights                 | Sensitivity                  | Frequencies               | Phase amplitude | Deviation                  |
| ------------------ | ----------------------- | ---------------------------- | ------------------------- | --------------: | -------------------------- |
| `kernel-v1`        | \(w_l=\phi^l\)          | \(\beta_0\phi^{l/2}\)        | \(\omega_0(l+1)\)         |               1 | caller-supplied            |
| `spacetor-v1`      | rounded just intonation | explicit, normally 1         | \(1,2,3,4,5,6\)           |               1 | \(\lvert x_l-\mu_l\rvert\) |
| `python-axiom-v1`  | \(w_l=\phi^l\)          | \(\beta_0+0.1\cos\varphi_l\) | \(1,9/8,5/4,4/3,3/2,5/3\) |             0.1 | \(\lvert x_l-\mu_l\rvert\) |
| `notebook-2026-01` | rounded just intonation | explicit, normally 1         | \(1,2,3,4,5,6\)           |               1 | \(\lvert x_l-\mu_l\rvert\) |

`kernel-v1` is canonical for the exported harmonic kernel API.
`spacetor-v1` is the live SpaceTor trust runtime. `python-axiom-v1` is the
Python governance implementation, and `notebook-2026-01` preserves the
historical executable example. They must not be silently presented as
numerically equivalent.

The SpaceTor and notebook weights

\[
(1,\;1.125,\;1.25,\;1.333,\;1.5,\;1.667)
\]

approximate

\[
(1/1,\;9/8,\;5/4,\;4/3,\;3/2,\;5/3).
\]

They are a just-intonation sequence. They are not an attenuated golden-ratio
sequence: \(\phi^5\approx11.0902\), not \(1.667\).

## 3. Properties that hold, with their conditions

### Positivity

Every term is nonnegative when \(\nu_l\ge0\), \(w_l>0\), and the parameters are
finite. Therefore \(C\ge0\). Strict positivity requires at least one active
coordinate \(\nu_l>0\); a fully collapsed flux vector gives \(C=0\).

### Monotonicity and convexity in deviation

Before clamping, for an active coordinate,

\[
\frac{\partial C}{\partial d_l}
=\nu_lw_l\beta_l e^{\beta_l[d_l+a\sin(\omega_lt+\varphi_l)]}>0,
\]

\[
\frac{\partial^2 C}{\partial d_l^2}
=\nu_lw_l\beta_l^2 e^{\beta_l[d_l+a\sin(\omega_lt+\varphi_l)]}>0.
\]

Thus the cost is strictly increasing and strictly convex in an active
deviation. A collapsed coordinate has both derivatives equal to zero. A
clamped implementation is only nondecreasing after saturation.

### Temporal bounds

Because \(-1\le\sin(\cdot)\le1\),

\[
\sum_l\nu_lw_le^{\beta_l(d_l-|a|)}
\le C(x,t)\le
\sum_l\nu_lw_le^{\beta_l(d_l+|a|)}.
\]

The Python profile uses \(|a|=0.1\); the kernel, SpaceTor, and notebook
profiles use \(|a|=1\).

### Smoothness

The cost is \(C^\infty\) as a function of the independent deviations \(d_l\).
It is **not** \(C^\infty\) as a function of \(x\) when
\(d_l(x)=|x_l-\mu_l|\). At \(x_l=\mu_l\), the left and right derivatives have
equal magnitude and opposite signs. The Python runtime now returns the valid
zero subgradient at that exact cusp instead of labeling a one-sided derivative
as the gradient.

Using \(d_l=(x_l-\mu_l)^2\) would produce a smooth alternative, but it is a
different cost surface and therefore requires a versioned profile rather than
a silent substitution.

### Conditional normalization

The SpaceTor and notebook formulas divide by

\[
C_{\max}=\sum_l w_l e^{2\beta_l},
\]

which assumes \(d_l\le1\) and \(a=1\). SpaceTor validates \(x_l\in[0,1]\),
and the `spacetor-v1` default \(\mu_l\) is also in that interval, so its
quotient lies in \((0,1]\). A custom SpaceTor parameter set must enforce the
same bound itself. The standalone formula does not enforce that domain and can
exceed one for larger deviations. The quotient is not a probability and
cannot generally be described as a percentage deviation.

## 4. Reproducible notebook receipts

For

```text
x     = [0.8, 0.6, 0.4, 0.2, 0.1, 0.9]
mu    = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
w     = [1.0, 1.125, 1.25, 1.333, 1.5, 1.667]
beta  = [1, 1, 1, 1, 1, 1]
omega = [1, 2, 3, 4, 5, 6]
phase = [0, pi/3, 2pi/3, pi, 4pi/3, 5pi/3]
t     = 1
```

the six positive terms are approximately

```text
[3.1313711785, 1.3662066310, 0.5461972502,
 3.8352496731, 2.8271484441, 0.9415630123]
```

and their sum is

\[
C(x,1)=12.647736189185094.
\]

The executable notebook output rounds this to `12.6477`; a worked example
claiming approximately `13.1` does not follow from the printed parameters.

The Monte Carlo receipt is also fully specified:

- seed: NumPy `default_rng(0)`;
- samples: 10,000 independent \(x\sim U([0,1]^6)\);
- fixed \(\mu=(0.5,\ldots,0.5)\) and \(t=1\);
- profile: `notebook-2026-01`;
- comparison variable: \(\sum_l |x_l-\mu_l|\).

It yields:

```text
mean(C)              = 12.216702536450999
population std(C)    = 0.8258778652654358
corr(C, sum(abs d))  = 0.8769837617359362
```

These numbers do not reproduce `7.2 +/- 2.5` or correlation `0.97`.
Correlation is descriptive here; coordinatewise monotonicity follows from the
derivative above, not from Monte Carlo.

## 5. Cycle average

For a single phase sampled uniformly over a full cycle,

\[
\frac{1}{2\pi}\int_0^{2\pi}e^{\beta a\sin\theta}\,d\theta
=I_0(\beta a),
\]

so a term's phase average is

\[
\nu_lw_le^{\beta_ld_l}I_0(\beta_la).
\]

The sum formula is valid when averaging each phase uniformly, or over a common
period for commensurate modes. This Bessel identity is verified numerically in
the regression suite.

## 6. Gradient-flow limitation

A fixed-time descent step can use a gradient or subgradient of \(C\). For the
time-varying cost, however,

\[
\frac{dC}{dt}=\nabla_xC\cdot\dot{x}+\frac{\partial C}{\partial t}.
\]

Choosing \(\dot{x}=-\eta\nabla_xC\) controls the first term but does not make
the explicit phase term nonpositive. A global Lyapunov claim therefore needs
either fixed \(t\), an augmented state, or an explicit bound on
\(\partial C/\partial t\).

## 7. Polytonic appendix: what is and is not established

For quadratic companion blocks

\[
M_l=\begin{pmatrix}0&1\\-c_l&-b_l\end{pmatrix},
\qquad M_{\mathrm{poly}}=\bigoplus_l M_l,
\]

the eigenvalue expression is valid when the discriminant is negative. The
following stronger statements need additional hypotheses:

- a direct sum of quadratic field extensions is generally a direct-product
  algebra, not itself a field;
- pairwise coprime block polynomials can make the minimal polynomial their
  product, but do not imply rational independence of the modal frequencies;
- maximal commutativity requires a centralizer argument, not just block
  diagonality;
- \(e^{iM_{\mathrm{poly}}t}\) is unitary only when the generator is
  self-adjoint in the selected inner product;
- dense or ergodic torus motion needs rationally independent frequencies and
  suitable initial support.

Neither runtime profile satisfies the proposed rational-independence
condition: integer modes and just-intonation ratios are both rationally
dependent. The maximal-polytonic construction is therefore recorded as
research, not as a production LWS property.

## 8. Evidence map

| Claim surface                                     | State              | Evidence                                                                       |
| ------------------------------------------------- | ------------------ | ------------------------------------------------------------------------------ |
| Public kernel cost and fractional flux            | implemented/tested | `packages/kernel/src/languesMetric.ts`, `tests/harmonic/languesMetric.test.ts` |
| SpaceTor trust cost and receipt labels            | implemented/tested | `src/spaceTor/trust-manager.ts`, `tests/spaceTor/trust-manager.test.ts`        |
| Python ideal-state cost and fractional flux       | implemented/tested | `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/langues_metric.py`        |
| Historical worked example                         | executable/audited | `notebooks/scbe_langues_metric_colab.ipynb`                                    |
| Weight/profile distinction and numerical receipts | tested             | `tests/specs/test_langues_weighting_system_spec.py`                            |
| Maximal-polytonic LWS runtime                     | unmapped           | no focused production implementation or test found                             |

Any future unification should receive a new profile identifier and must beat
or preserve the current decision behavior under multi-seed, held-out tests.
Renaming one profile as another is not a migration.
