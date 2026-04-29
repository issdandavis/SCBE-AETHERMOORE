# EML / T-cell empirical verification — follow-up note

> Companion document to [`docs/research/t_cell_analog_schematic.md`](./t_cell_analog_schematic.md).
> Distills the empirical findings from session `local_8347d241-a3c1-4aae-87ac-71c04e8c9ee6`
> (EML/T simulator) and re-runs the load-bearing math at 50-digit precision so the claims
> in this note carry their own receipts.
>
> **TL;DR.** The binary `EML(x,y) = exp(x) − ln(y)` paper is real, the canonical log
> identity that has been circulating on socials is **wrong by one outer wrap**, and the
> follow-up "ternary T-cell" speculation does not survive an algebraic shake-down. The
> useful kernel here is the binary EML+1 result; nothing in this note supports the
> TENG-memristor / HYDRA / atomic-tokenizer extensions.

---

## 1. The source paper is real

* **Citation.** Andrzej Odrzywołek (Jagiellonian University), *All elementary functions
  from a single binary operator*, **arXiv:2603.21852** [cs.SC], v1 23 Mar 2026,
  v2 4 Apr 2026.
  * Abstract: <https://arxiv.org/abs/2603.21852v2>
  * PDF:      <https://arxiv.org/pdf/2603.21852>
  * HTML:     <https://arxiv.org/html/2603.21852v2>
  * DOI:      <https://doi.org/10.48550/arXiv.2603.21852>
  * Code (Zenodo): <https://zenodo.org/records/19183008>
  * Subjects: Symbolic Computation (cs.SC); Machine Learning (cs.LG)
  * MSC: 26A09 (primary), 08A40, 68W30. ACM: I.1.1, F.1.1.

* **Claim of the paper.** The single binary operator
  `eml(x, y) := exp(x) − ln(y)`, together with the constant `1`, generates
  the entire scientific-calculator basis: `e`, `π`, `i`; addition, subtraction,
  multiplication, division, exponentiation; and the standard transcendental and
  algebraic functions. The grammar reduces to `S → 1 | eml(S, S)`, i.e. a binary
  tree of identical nodes. The paper also reports gradient-based symbolic regression
  (Adam) recovering closed-form elementary functions from numerical data at tree
  depths up to 4.

This is a serious, properly-archived result. Treat it as the load-bearing piece of
this whole line of work; everything else summarised below either trims overstated
claims about it or refutes downstream extrapolations.

---

## 2. The popular log identity is wrong by one outer `eml(1, ·)` wrap

A version that has been floating around in derivative summaries and chat threads
(including in some early SCBE-AETHERMOORE notes) reads:

```
log x  =  EML(EML(1, x), 1)        -- POPULAR, INCORRECT
```

That expression evaluates to something else entirely. With `eml(a, b) = exp(a) − ln(b)`:

```
EML(1, x)            =  e − ln x
EML(EML(1, x), 1)    =  exp(e − ln x) − ln 1
                     =  exp(e) · exp(−ln x)
                     =  e^e / x
```

So the popular form is `e^e / x`, not `log x`. Numerical check at 50 dps
(`/tmp/scbe/verify_eml.py`):

```
x=2.0   eml(eml(1,x),1) = 7.5771311207...      |LHS - e^e/x| = 0          |LHS - log x| = 6.884
x=7.3   eml(eml(1,x),1) = 2.0759263344...      |LHS - e^e/x| = 0          |LHS - log x| = 0.0881
x=0.41  eml(eml(1,x),1) = 36.961615223...      |LHS - e^e/x| = 0          |LHS - log x| = 37.853
```

The **paper's actual** identity has one more outer `eml(1, ·)`:

```
log x  =  eml(1,  eml(eml(1, x), 1))           -- PAPER (verbatim from abstract)
```

Algebraically:

```
eml(1, eml(eml(1, x), 1))
  = e − ln( eml(eml(1, x), 1) )
  = e − ln( e^e / x )
  = e − ( e − ln x )
  = ln x        ✓
```

Numerical residuals at 60-digit working precision (60 dps) reported at 50 dps:

| `x`        | `|residual|` |
|------------|-------------:|
| 0.5        | 1.34 × 10⁻⁵¹ |
| 2          | 1.34 × 10⁻⁵¹ |
| 100        | 0            |
| 1234.5     | 0            |
| 1 × 10⁻²⁰  | 0            |
| 1 × 10²⁰   | 0            |
| 1 + 1 i    | 2.00 × 10⁻⁵¹ |
| 5 − 2 i    | 6.68 × 10⁻⁵² |
| 0.1 + 3 i  | 0            |
| 100 − 100 i| 0            |

**Correction to the session-`8347d241` write-up.** That earlier write-up claimed the
identity "misses by exactly 2π at x = −1 due to the principal branch cut." That is
not what the numbers show. Stepping `x = −2 ± εi` across the negative real axis
(`/tmp/scbe/verify_eml2.py`):

```
x = −2 + 1e−10 i :  log x = (0.6931... + 3.1415...i)
                    LHS   = (0.6931... + 3.1415...i)
                    LHS − log x = (−2.67e−51 + 0 i)

x = −2 − 1e−10 i :  log x = (0.6931... − 3.1415...i)
                    LHS   = (0.6931... − 3.1415...i)
                    LHS − log x = (−2.67e−51 + 0 i)
```

The identity holds **across** the cut as well, because we apply the principal log
twice in the same expression: the side-of-the-cut choice cancels. So the corrected
claim is the stronger one — the paper identity is good to ≤ 3 × 10⁻⁵¹ on the entire
domain we sampled, including either side of the negative real axis. No 2π wrap miss.

---

## 3. EML identities that survive 50-digit verification

All of the following pass with residual `0` (or rounding noise ≪ 10⁻⁵⁰) at `mp.dps =
60`. Source: `/tmp/scbe/verify_eml.py` (mirror in repo would belong at
`research/eml_simulator/verify_eml_identities.py`).

### 3.1  `eml(x, 1) = exp x`

```
eml(x, 1) = exp(x) − ln(1) = exp(x) − 0 = exp(x)
```

Residuals:

| `x`         | `|residual|` |
|-------------|-------------:|
| 0.5         | 0 |
| −3          | 0 |
| 17.25       | 0 |
| 1.2 + 0.7 i | 0 |

### 3.2  `eml(1, 1) = e`

```
eml(1, 1) = exp(1) − ln(1) = e
```

Residual: 0.

### 3.3  `eml(x, exp y) = exp(x) − y`

```
eml(x, exp y) = exp(x) − ln(exp y) = exp(x) − y
```

Residuals:

| `(x, y)`                          | `|residual|` |
|-----------------------------------|-------------:|
| (0.7, −2.4)                       | 0 |
| (1 + 0.3 i, −0.5 + 1.2 i)         | 0 |

### 3.4  `sin(x) = (eml(i x, 1) − eml(−i x, 1)) / (2 i)`

Substituting (3.1):

```
(exp(i x) − exp(−i x)) / (2 i) = sin(x)
```

Residuals at `x = 0.3, 1.7, −2.5`: all 0.

### 3.5  `cos(x) = (eml(i x, 1) + eml(−i x, 1)) / 2`

```
(exp(i x) + exp(−i x)) / 2 = cos(x)
```

Residuals at `x = 0.3, 1.7, −2.5`: all 0.

### 3.6  `π = −Im( eml(0, −1) )`

```
eml(0, −1) = exp(0) − ln(−1) = 1 − iπ        (principal branch)
−Im(1 − iπ) = π
```

Residual: 0.

### 3.7  Recap of the corrected log identity (from §2)

```
log x = eml(1, eml(eml(1, x), 1))
```

Worst residual on the test grid (real and complex sample points): 2 × 10⁻⁵¹.

These seven identities are the load-bearing primitives. Every other elementary
function in the paper's grammar reduces to compositions of them; the paper's
construction is constructive and shallow.

---

## 4. The ternary "T-cell" claim does not survive scrutiny

Define

```
T(x, y, z)  :=  (e^x / ln x) · (ln z / e^y)
```

The promotional framing was that `T` is a **single-input, constant-free Sheffer**
operator for elementary functions: feed `T` one variable and recover the entire
scientific-calculator basis without needing the EML seed `1`. That framing fails
on three independent grounds.

### 4.1  `T(x, x, x) = 1` is the trivial diagonal — and not useful

Algebraically:

```
T(x, x, x) = (e^x / ln x) · (ln x / e^x) = 1
```

Numerically (60 dps; `/tmp/scbe/verify_t.py`):

| `x`         | `T(x,x,x)`            | residual |
|-------------|-----------------------|----------|
| 2           | 1                     | 0 |
| 3.7         | 1                     | 7.78 × 10⁻⁶² |
| 0.4         | 1                     | 0 |
| 17          | 1                     | 0 |
| 1.2 + 0.5 i | 1 + 1.32 × 10⁻⁶² i    | 7.89 × 10⁻⁶² |

So yes, `T(x, x, x) = 1` to within floating-point noise of the working precision.
This is also where the "constant-free" pitch wants to live: `1` falls out of `T`
applied to a single variable, so we don't need `1` as a seed. But:

### 4.2  `T(1, ·, ·)` is undefined — `T` cannot consume the EML seed

```
T(1, y, z) = (e^1 / ln 1) · (ln z / e^y) = (e / 0) · (·)
```

`ln 1 = 0`, so the first factor is singular. `T` produces `1` from a non-trivial
input, but the moment you try to feed that `1` back in as the leftmost argument
you hit a removable-only-in-limit singularity. So the round-trip
"derive `1` from `T`, then build EML on top of it" doesn't close: at the point
where you need to plug `1` back in, the operator is not defined.

### 4.3  Single-input depth-1 closure is too small to hold EML

Enumerate every depth-1 expression `T(α, β, γ)` with `α, β, γ ∈ {a, b}` (i.e. every
way of routing one or two non-trivial inputs through the three slots).
There are 2³ = 8 patterns. They reduce to four distinct algebraic forms (plus the
trivial 1):

```
T(a, a, a)  =  1                                  (and T(b,b,b)=1)
T(a, a, b)  =  (e^a / ln a) · (ln b / e^a)  =  ln b / ln a
T(b, b, a)  =  ln a / ln b
T(a, b, a)  =  (e^a / ln a) · (ln a / e^b)  =  e^{a−b}
T(b, a, b)  =  e^{b−a}
T(a, b, b)  =  (e^a / ln a) · (ln b / e^b)  =  e^{a−b} · ln b / ln a
T(b, a, a)  =  (e^b / ln b) · (ln a / e^a)  =  e^{b−a} · ln a / ln b
```

Numerical sample with `a = 2.7, b = 5.1`:

```
T(a,a,a) = 1.00000000
T(a,a,b) = 1.64030970
T(a,b,a) = 0.09071795
T(a,b,b) = 0.14880554
T(b,a,a) = 6.72017991
T(b,a,b) = 11.02317600
T(b,b,a) = 0.60964096
T(b,b,b) = 1.00000000
```

The depth-1 closure of `T` over a single non-trivial input thus collapses to:

```
{ 1,
  ln b / ln a,
  ln a / ln b,
  e^{a−b},
  e^{b−a},
  e^{a−b} · ln b / ln a,
  e^{b−a} · ln a / ln b }
```

**Outer-subtraction lemma.** Every form on that list is a product/quotient of
`exp` terms and `ln`-ratios. None of them is `e^a − ln a` (the EML value
`eml(a, a)`). That is, **a single application of `T` over its own input set
cannot place a subtraction outside an `exp`.** Subtraction can only re-appear
*inside* an exponent (as `a − b`), never at the top level of the expression.

Numerically: `eml(a, a) = e^a − ln a ≈ 13.886` for `a = 2.7`; none of the 8
depth-1 `T` outputs comes anywhere near that value (all hits would have to be
≤ 10⁻⁴⁰ off — none are).

To recover EML you need a top-level `e^A − e^B`-style structure, which `T`
cannot produce in a single application from a single variable. So `T` is **not
single-input universal** in the sense the popular summaries suggest, and in
particular **`T` cannot reconstruct `EML`** from one variable plus the trivial
`1` it spits out at the diagonal.

### 4.4  Verdict on the "constant-free Sheffer" framing

Both pieces of the framing fail:

1. *Constant-free.* You only get `1` as the diagonal, and the moment you try to
   re-use it as input to `T` you hit `ln 1 = 0` and lose definition. So the
   constant `1` is not actually consumable.
2. *Sheffer-like.* The depth-1 image of `T` is a small multiplicative orbit
   that cannot host any top-level subtraction. EML is not in the closure.

The binary `EML + 1` paper is a proper algebraic Sheffer-style result. The
ternary `T` extension is not, and there is no obvious rescue: deepening `T`
trees does not promote `a − b` from inside an exponent to outside it without
re-introducing exactly the kind of `eml`-style top-level subtraction that the
proposal was trying to dispense with.

---

## 5. Symbolic regression — "100% recovery at depth 2" doesn't reproduce

The popular write-up reports gradient-based symbolic regression over EML trees
recovering closed-form formulas with "100% recovery at depth 2" across a range
of targets. Two problems with that summary:

### 5.1  Some targets are not even *representable* at depth ≤ 2

Exhaustive enumeration over the EML grammar with leaf set `{1, x}`,
counting "depth" as the longest path of internal `eml` nodes
(`/tmp/scbe/depth2.py`):

* Depth 0 leaves:   2  (`1`, `x`).
* Depth ≤ 1 trees:  6  (the 2 leaves plus 4 binary trees `eml(L₁, L₂)`).
* Depth ≤ 2 trees:  42 raw, **38 distinct** symbolic values after `simplify`.

(The popular "144 depth-2 trees" count appears to come from a different
enumeration convention — counting ordered pairs over a richer leaf set such as
`{1, x, e, exp x, log x, exp x − log x, e − log x, …}`. Whatever the count,
the dimension of the depth-2 symbol set over `{1, x}` is exactly 38, and
the *qualitative* representability conclusion below is the same.)

Reachability at depth ≤ 2 against canonical targets:

| target              | reachable at depth ≤ 2 |
|---------------------|-----------------------|
| `exp(x)`            | ✓ |
| `exp(exp(x))`       | ✓ |
| `exp(x) − log(x)`   | ✓ |
| `log(x) + exp(x)`   | **✗** |
| `log(x)`            | **✗** |
| `1/x`               | **✗** |
| `x · x`             | **✗** |

`log(x) + exp(x)` is *not* in the depth-2 symbol set: getting `−log(x)` at the
top level requires `log(B)` with `B = 1/x`, and `1/x` itself is not at depth
≤ 1 over `{1, x}`. You need depth ≥ 3. Same story for plain `log(x)` — the
paper's identity for it sits at depth 3.

So *any* search over depth-2 trees with these targets has a hard ceiling: the
*reachable* targets can in principle hit 100%; the *unreachable* ones are
stuck at 0% no matter the optimiser.

### 5.2  SPSA recovery rates over a Gumbel-softmax depth-2 tree

Set-up (mirroring the simulator notebook in
`research/eml_simulator/notebooks/symbolic_regression.ipynb`):

* 14-weight Gumbel-softmax parameterisation of a depth-2 EML tree.
* SPSA optimiser, 10 random seeds per target, 4000 steps each, anneal
  τ = 1.0 → 0.1.
* PyTorch + Adam was the original optimiser in the paper; PyTorch was not
  installable in the sandbox, hence the SPSA fallback.

| target              | recovery rate (10 seeds) |
|---------------------|-------------------------|
| `exp(x)`            | 50 % |
| `exp(x) − log(x)`   | 50 % |
| `exp(exp(x))`       | 0 %  |
| `log(x) + exp(x)`   | 0 %  |

Two observations:

1. **In-class recovery is partial under SPSA.** `exp(x)` and `exp(x) − log(x)`
   are demonstrably reachable at depth ≤ 2, yet SPSA only finds them on
   half the seeds. That is consistent with SPSA being a noisier optimiser
   than Adam over the same Gumbel-softmax landscape; switching to PyTorch+Adam
   (as in the paper) likely lifts the in-class numbers towards the published
   100%.
2. **Out-of-class targets stay at 0% no matter what.** `log(x) + exp(x)` is not
   in the depth-2 symbol set; no choice of optimiser will pull it out of a
   depth-2 search. `exp(exp(x))` *is* in the symbol set but the SPSA basin
   for it is small enough that 10 seeds didn't hit it. (Re-running with more
   seeds, or with Adam, would likely recover it eventually.)

**Bottom line on the regression claim.** The headline "100% recovery at depth 2"
is conditional on (a) the target actually being expressible at depth ≤ 2, and
(b) the optimiser being able to navigate the discrete tree landscape. Both are
non-trivial. The depth-2 EML symbol set has structural holes (`log x`, `1/x`,
`x·x`, anything with a top-level `+` that isn't `e^A − e^B`-shaped), and any
benchmark that selects targets only from inside the reachable set can in
principle hit 100% but tells you nothing about the holes.

---

## 6. Hardware verdict

For the analog-realisability question — whether `EML` (or the broken-as-a-Sheffer
`T`) maps onto a physical device — see the companion document
[`docs/research/t_cell_analog_schematic.md`](./t_cell_analog_schematic.md).

That schematic stands or falls on `T` being algebraically sound, which §4 above
argues it is not. The binary `EML` itself maps to two well-known analog
primitives (a Type-I exponential element and a logarithmic transimpedance
stage), composed by subtraction at a summing junction — that part is plausible
and unremarkable, and the analog literature on `exp − log` cells is decades
deep. Nothing about that legitimises the TENG-memristor / HYDRA / "atomic
tokenizer" framings.

---

## 7. What's actually useful

* **The binary `EML + 1` paper is legitimate.** Odrzywołek, arXiv:2603.21852v2,
  cs.SC. A constructive single-binary-operator basis for the
  scientific-calculator subset of elementary functions, with the canonical log
  identity `log x = eml(1, eml(eml(1, x), 1))` verified to ≤ 2 × 10⁻⁵¹ on the
  full sample grid. This is a proper Sheffer-style result for elementary
  functions; treat it the way you'd treat NAND for Boolean logic.

* **The seven identities in §3** are the load-bearing primitives. Each was
  re-derived and verified at 50 dps. That's the part of the simulator output
  that should survive into any future write-up.

* **The ternary `T` extension does not survive scrutiny.** §4 spells out three
  independent failures: domain singularity at the would-be `1`-seed, depth-1
  closure that can't host top-level subtraction, and consequent inability to
  recover EML from one input. The "constant-free Sheffer" framing in the
  popular summaries is incorrect.

* **The symbolic-regression headline is conditional.** Some targets are
  unreachable at depth ≤ 2 by the EML grammar itself; reporting "100% recovery
  at depth 2" only makes sense when the target set is restricted to the
  reachable subset. The simulator's SPSA numbers (§5.2) show partial recovery
  even on reachable targets, and zero on unreachable ones.

* **The TENG-memristor / HYDRA / atomic-tokenizer extensions are unsupported.**
  None of them follow from the binary EML result, and the ternary `T`
  bridge that was meant to motivate them is broken at the algebra layer
  (see §4). They should be marked as speculative in any downstream document
  that currently treats them as established.

---

## 8. Verification artifacts

All numerical claims in this note can be re-run from the scripts referenced
inline. For convenience:

| Script (sandbox path)           | What it verifies                             |
|---------------------------------|----------------------------------------------|
| `/tmp/scbe/verify_eml.py`       | Identities §3.1–§3.6 and the wrong/right log forms in §2 |
| `/tmp/scbe/verify_eml2.py`      | Branch behaviour of the corrected log identity across the negative real axis |
| `/tmp/scbe/verify_t.py`         | `T(x,x,x)=1`, depth-1 closure of `T`, EML-unreachability |
| `/tmp/scbe/depth2.py`           | Exhaustive depth-≤2 EML enumeration over `{1, x}` and target reachability |

When this note is staged into the repo, the corresponding canonical home
for those scripts is `research/eml_simulator/` (next to the existing
simulator notebooks). The session that produced the original numbers is
`local_8347d241-a3c1-4aae-87ac-71c04e8c9ee6`.

---

## 9. Suggested edits to other docs

* **`docs/research/t_cell_analog_schematic.md`** — add a header pointer to this
  note and explicitly downgrade the algebraic claims for `T` to "speculative,
  open" until the depth-1 closure issue (§4.3) is addressed by a deeper
  construction.
* **`docs/research/eml_simulator/README.md`** (or equivalent) — replace any
  occurrence of `EML(EML(1, x), 1) = log x` with the paper-correct
  `eml(1, eml(eml(1, x), 1)) = log x`, and add the residual table from §2.
* **Any external write-up / blog post referencing "100% recovery at depth 2"** —
  qualify with the depth-2 reachability table from §5.1, and replace
  unrestricted "100%" with the in-class recovery numbers from §5.2 (or the
  Adam re-run when available).

---
*Prepared 2026-04-26.*
*Math re-derived at `mp.dps = 60` with `mpmath 1.3.0`; symbolic enumeration via
`sympy`. No PyTorch in this environment, so the regression numbers in §5.2 use
SPSA over the same Gumbel-softmax tree the simulator notebook defines.*
