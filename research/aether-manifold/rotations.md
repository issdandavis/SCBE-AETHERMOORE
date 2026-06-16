# Rotations, hyperbolic rotations, and the n-cube — the algebra of a "twist"

**Status:** research grounding for the `code-cube --target manifold` output. The point:
a cube **twist** is not a metaphor — it is a group element. This file says *which group*,
how Euclidean and hyperbolic twists differ, and how the cube generalizes to n dimensions.
Honest discipline kept: real math is marked real; analogies are marked analogies.

> *"When coding becomes shapes, you're folding paper cranes."* — exactly. A twist is a
> fold; a program is a crease pattern; the finished form is the crane. The math below is
> the fold algebra. (Origami note at the end is literal, not decoration.)

---

## 1. Rotations happen in 2-planes (the real core)

In any dimension n, an elementary rotation is a **Givens rotation** G(i, j, θ): it rotates
the (eᵢ, eⱼ) plane by θ and leaves every other axis fixed. Its only nontrivial part is a
2×2 block:

```
[ cos θ   -sin θ ]
[ sin θ    cos θ ]
```

- The group of all rotations in n-D is **SO(n)**.
- Its dimension is **C(n, 2) = n(n−1)/2** — one generator per coordinate 2-plane.
- Any rotation factors into Givens rotations (this is how QR decomposition works).

So "rotate the cube" = "pick a 2-plane, pick an angle." A **90° face turn** is
G(i, j, π/2): cos = 0, sin = 1 — it *swaps* two axes (with a sign). That makes a face turn
a **signed axis permutation**, which is the bridge to the next section.

For our cube, n = 6 faces → **SO(6)**, dimension **15**. There are 15 distinct 2-planes a
twist can act in. That is the continuous "twist budget."

---

## 2. The n-cube's own symmetry: the hyperoctahedral group (real)

The discrete symmetries of an n-cube (the moves that map the cube onto itself) form the
**hyperoctahedral group Bₙ** = signed permutations of n axes:

```
Bₙ = (Z/2)ⁿ ⋊ Sₙ        order = 2ⁿ · n!
```

- The orientation-preserving (rotation-only) subgroup has order **2ⁿ⁻¹ · n!**.
- **n = 3** (ordinary cube): order 48; 24 rotations — *exactly the whole-cube rotations of
  a Rubik's cube* (the octahedral rotation group).
- **n = 4** (tesseract / 4-cube): order 384; 192 rotations.
- **n = 6** (our six-face cube): order **2⁶ · 6! = 46,080**; rotation subgroup **23,040**.

This is the "n^cube or higher" structure, made precise: as you add dimensions the symmetry
group grows like 2ⁿ·n! — fast, but finite and enumerable. A discrete twist (a face turn)
is one element of Bₙ; a continuous twist is an element of SO(n). Bₙ ⊂ SO(n) ⋊ reflections —
the 90° Givens rotations are the lattice elements of Bₙ.

**"Cube of cubes" / higher towers.** Stacking cubes (an array of m cubes, each itself
n-dimensional) gives a **wreath product** Bₙ ≀ Sₘ — the inner symmetry of each cube times
the permutations of the cubes. Order (2ⁿ·n!)ᵐ · m!. This is the honest meaning of "n^cube
or higher": you compose the per-cube group with an outer arrangement group. It does not
add new *kinds* of move; it multiplies the move count.

---

## 3. Hyperbolic rotations = boosts (the SCBE-native part)

SCBE already lives in hyperbolic space (Poincaré ball, dH distance, Möbius phase). The
"rotations" of hyperbolic n-space are not all ordinary rotations — the ones that move you
*through* the space are **hyperbolic rotations**, a.k.a. **boosts**.

A boost in the (e₀, eᵢ) plane (e₀ = the radial / "depth" axis) uses **cosh/sinh** instead
of cos/sin, with a **rapidity** φ:

```
[ cosh φ   sinh φ ]
[ sinh φ   cosh φ ]
```

- The isometry group of hyperbolic n-space is **SO⁺(n, 1)** (Lorentz-type, signature
  n positive + 1 negative). Boosts are its non-compact generators.
- On the Poincaré ball these are **Möbius / gyro-translations** — they slide the whole ball.
- **Rapidity is additive along one axis:** φ_total = φ₁ + φ₂. Composing boosts in *different*
  planes is non-commutative and produces a residual ordinary rotation — the **Thomas–Wigner
  rotation**. (Real, well-known. It means twist *order matters* in the hyperbolic layer.)

### Why this matters for the cube
- A **Euclidean twist** (ordinary face turn) reshapes the cube *in place* — Givens, angle
  π/2, costs nothing in "depth." Use for: frontend/backend/data/tests bindings.
- A **hyperbolic twist** (boost) moves the cube *deeper into the governance manifold* — it
  costs rapidity. Use for: security/deploy moves, where SCBE's tongue weights already say
  "this is expensive."

We tie rapidity to SCBE's tongue weights (KO 1.00, AV 1.62, RU 2.62, CA 4.24, UM 6.85,
DR 11.09):

```
φ_face = ln(tongue_weight)
```

So a `security.deploy` twist (UM→DR, weights 6.85 → 11.09) is a boost with
φ = ln(6.85) + ln(11.09) = ln(75.96) ≈ 4.33 — large rapidity, deep move, high governance
cost. A `tests.backend` twist (KO→CA, 1.00 → 4.24) is φ = ln(4.24) ≈ 1.44 — shallow. The
geometry now *prices* the twist, which is exactly the geometric-router idea, in one number.

---

## 4. The twist taxonomy (what `--target manifold` emits)

| Twist kind | Group | Block | Angle/param | Cube meaning |
|---|---|---|---|---|
| Face turn | Bₙ ⊂ SO(n) | Givens | θ = π/2 | swap two face-axes (signed) |
| Free rotation | SO(n) | Givens | θ ∈ ℝ | partial blend of two faces |
| Governance move | SO⁺(n,1) | boost | rapidity φ = ln(weight) | push deeper into safety manifold |
| Whole-cube reorient | Bₙ | signed perm | — | relabel which face is "up" |

Each emitted twist therefore carries: the **plane (i, j)** it acts in, its **type**
(givens_euclidean | boost_hyperbolic), the **2×2 block** (cos/sin or cosh/sinh), and the
resulting **signed permutation** on the six faces.

---

## 5. The manifold packet (spec for the CLI output)

`geoseal code-cube "<intent>" --target manifold --json` adds a `manifold_plan` key:

```
ambient_dim            n = 6 (faces as axes)
rotation_group         SO(6), dim 15  |  Bₙ order 46080, rotations 23040
face_axes[]            face -> axis index, tongue, weight, TRIT state {-1,0,+1}
trit_word              the six face trits = the cube token's 6 channels
coprime_address        CRT residues mod {7,11,13} (+ redundant 17 for RRNS lane recovery)
pressure_interlock     geoseal tier -> fail-closed pressure threshold (UM tongue, in metal)
twist_schedule[]       each selected twist as a rotation operator (plane, type, block, perm)
note                   control schedule + algebra, NOT a hardware claim
```

This makes the software cube and the physical Aether Manifold **one artifact with two
output faces**: the file plan (software) and the valve/rotation schedule (physical), over
the same center IR.

---

## 6. Origami, literally

Origami is not a flourish here — it is the same math:
- A **flat-foldable crease pattern** must satisfy **Kawasaki's theorem** (alternating angles
  around a vertex sum to 180°) and **Maekawa's theorem** (|mountain − valley| folds = 2).
  These are *linear constraints* — the same flavor as "rotations live in 2-planes."
- A **fold** is a reflection across a crease line = a rotation by π about that line in the
  embedding space. A folding *sequence* is a product of such rotations — a path in the
  rotation group, just like a twist schedule.
- The finished **crane** is the orbit endpoint: the center sheet (IR) carried by a specific
  product of folds (twists) into a target form (the app, or the valve configuration).

So "coding becomes shapes, you're folding paper cranes" is exact: the center IR is the
sheet, `twists` are the creases, and the emitted artifact — software files or valve schedule
— is the crane. The `manifold_plan` is the crease pattern written down.
