# Unified Math Spine v2 — adapted & status-honest (2026-07-11)

Supersedes the old "Unified Math Spine" (SCBE/PHDM/GeoSeal/HYDRA/VECRO/Spin) and folds in the
**MAHSS Search-Space Optimization** results (2026-05-05) + this session's corrections. Every claim
now carries a status: **VERIFIED** (measured, robust) · **SIMULATED** (toy/one-seed only) ·
**REFUTED** (measured to fail) · **OPEN** (untested). Nothing is asserted as proven that isn't.

The headline: MAHSS is the empirical spine. The geometry the older docs *describe* (polyhedral
state, "shapes define valid regions") is exactly what MAHSS *measures* — and one polyhedral search
primitive survives a real audit, while several elegant ideas are locked as negative results.

---

## 0. What changed from v1 (the corrections)

| Old-doc claim | v2 status | Why |
|---|---|---|
| §1.3 wall `H(d,R) = R^(d²)`, "super-exponential" | **REFUTED as the canonical wall** | adversarial-cost bench measured attacker cost **LINEAR**, not exponential. Canonical L12 is now the **bounded** score `H_score(d*,pd) = 1/(1+d*+2·pd)` ∈ (0,1]. `R^(d²)` survives only as a *work-factor shape*, never as a hardness proof. |
| §2 PHDM "99% ROP vs 70% label-CFI" | **SIMULATED** | toy `complete_graph(14)`-scale, not real binaries. Structure is sound; the number is not measured. |
| 21D "brain" AUC 1.000 | **REFUTED (artifact)** | test-design artifact; ~0.61 on a fair adaptive baseline. Do not anchor. |
| GeoSeal "geometry catches intent" via hyperbolic distance | **REFUTED for distance** | hyperbolic `d_H` loses to cosine (origin-crowding) — confirmed by our GeoSeal run *and* the 2024–26 hyperbolic-LLM literature. Hyperbolic is for *representing hierarchy*, not for distance/NN. |

---

## 1. SCBE core (context → deviation → gate) — VERIFIED as pipeline, corrected wall

1. Encode `(m, c) → x ∈ ℝ^d`; maintain allowed region `𝓜`.
2. Deviation `Δ = d(x, 𝓜)` (or `‖x−μ‖`). **VERIFIED** (it's just a metric).
3. Gate score — **canonical, bounded**: `H_score(d*, pd) = 1/(1 + d* + 2·pd)`, scale 1e6, bit-identical in
   `governanceAbacus.ts`. **VERIFIED** as the current runtime formula. The old `R^(d²)` "wall" is a
   penalty *shape* only.
4. L13 tiers: ALLOW ≥ .65 · QUARANTINE ≥ .45 · ESCALATE ≥ .25 · DENY < .25.

## 2. PHDM — the polyhedral state manifold (the "brain thing with shapes")

- `G=(V,E)` with polyhedral semantics: interior = legal computation, boundary faces = the alarm.
  Euler χ = V−E+F; curvature κ(t) = deviation. Energy view `E(π)=E_task+αE_risk+βE_drift`.
- **Status:** structure **VERIFIED as geometry** (it is the polytope-lens / linear-region idea —
  real, published: *Interpreting Neural Networks through the Polytope Lens*, arXiv 2211.12312).
  Performance **SIMULATED** only. The one build that makes it real is **CFG → lift → principal-curve
  → deviation detector on a REAL control-flow graph** (not the toy complete graph). **OPEN.**

## 3. MAHSS — the empirical search spine (this is the verified core)

The polyhedral search MAHSS measured *is* PHDM's traversal, benchmarked honestly.

- **VERIFIED WIN:** `polyhedral_edge_k20_w4` (sign-facet hypercube walk). **100% recall on 50/50 seeds**
  at n=80, **2.88× faster than Tang**, cost near-constant as n grows 4× (123→150 evals). At large n
  (500–1000) a small recall hole appears (~92%); `polyhedral_edge_k20_w10` is the 100%-reliable
  conservative variant (~1.03× Tang). **For governance-critical use: w=10.**
- **NEGATIVE, locked in tests:** Platonic-solid walks (tetra→dodeca) recall **0/4** under full-rank
  random-orthogonal coupling — the 3D compass is too coarse. `constructive_oscillation` was a
  lucky seed-19 demo: **38% → 0%** recall across seeds/scale; pulled from the winner list.
- **COST-HONEST:** the disagreement probe ("double-negative → positive") is a legitimate reranker but
  **does NOT beat the cheapest single full-recall method on total cost** once both source selectors are
  charged. The schema (`total_evaluations`, `cost_accounting`) makes the misleading framing untellable.
  This is the model of honesty the rest of the spine should match.

### 3.1 The real law (VERIFIED)

> **A polyhedral lattice recovers solutions iff its resolution exceeds the solution-subspace rank.**
> Below it, no polyhedron walk works; above it, the cheapest sufficient lattice wins.

And the cryptographic-strength hinge: **effective key strength = rank of the *solution subspace*, not
rank(M).** SVD-truncating the coupling matrix to the answer-rank suffices (`r16`→full recall at rank-4
answers). Security from a high-dim key collapses to a low-dim guarantee whenever the *answer set* is low-dim.

## 4. GeoSeal / HYDRA / tokenizer — status

- **GeoSeal:** envelope + context-binding threshold `Δ(c, c_expected) ≤ τ` is **VERIFIED** (it's a gate).
  The "hyperbolic geometry catches intent" claim is **REFUTED for distance** (§0). Keep GeoSeal as a
  bounded-deviation gate, not a hyperbolic-distance oracle.
- **HYDRA quorum:** `Σ vᵢ ≥ q(R)` with lineage-diversity `|lineages(S)| ≥ L(R)` — **VERIFIED as design**;
  the anti-collusion via *differentiation* matches [[squad-differentiation-triangulation]] (clones can't
  triangulate). Diversity is load-bearing, not decorative.
- **Six-Tongues tokenizer:** byte↔nibble↔token bijection is **VERIFIED** (bijective by construction);
  its *value* is the constraint/attestation, not computation (a bijection computes nothing).

## 5. The live vulnerability MAHSS surfaces (act on this)

**L13 governance outcomes are rank-4** (ALLOW/QUARANTINE/ESCALATE/DENY). By the law in §3.1, a rank-4
*outcome* subspace is searchable by a **tetrahedron-grade compass regardless of the coupling matrix the
pipeline deploys** — the *outcome* rank is small even when the *evidence* rank is large. So an attacker
who targets the outcome subspace can recover decisions cheaply without knowing M. **This is a real
attack surface, not a strength.** Open experiment: demonstrate rank-4 outcome recovery via a
tetrahedron compass without M. Mitigation is not "bigger key" (§3.1 says that doesn't help) — it must
raise the *outcome-subspace* rank or add a cost-honest freshness/nonce term the compass can't precompute.

## 6. VECRO / spin — still OPEN (honest placeholder)

No canonical VECRO/spin equations are loaded. `ψ=(x, ω)` with `x_{t+1}=f(x_t,u_t,ω_t)` is a *shape*,
not a spec. **Do not cite spin results until the evolution equation and a measured test exist.**

## 7. One-picture flow (corrected)

Encode `(m,c)→x` → deviation `Δ` → **bounded** gate score (not `R^(d²)`) → GeoSeal threshold + crypto →
HYDRA quorum (differentiated) → PHDM constrained path (verified search = polyhedral edge-walk, w=10 for
governance) → audit with `total_evaluations` + `cost_accounting`.

---

*Adapted from the v1 Math Spine + MAHSS (2026-05-05) + the 2026-07-11 corrections. The durable, verified
pieces are: the bounded L12 gate, the polyhedral-edge-walk search, the solution-subspace-rank law, and
MAHSS's cost-honest schema. The refuted pieces (R^(d²) hardness, brain AUC 1.000, hyperbolic distance)
are marked so they stop being quoted. PHDM's real-graph detector and the L13 outcome-probe are the two
open builds that would move the most.*
