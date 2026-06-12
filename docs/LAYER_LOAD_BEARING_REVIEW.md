# 14-Layer Pipeline — Load-Bearing Review

**Generated:** 2026-06-10
**Question asked:** Review each of the 14 layers independently (what does it actually do for *security*?), then review them as a composition. Hypothesis under test: *a narrow slice already works for security; the full stack is more than needed.*
**Method:** Read the real implementations (`packages/kernel/src/pipeline14.ts`, `hyperbolic.ts`, `hamiltonianCFI.ts`, `harmonicScaling.ts`, `audioAxis.ts`, `src/spectral/`, `src/governance/runtime_gate.py`, `axiom_grouped/causality_axiom.py`) and cross-checked against the repo's own benchmark/ablation JSONs.
**Verdict up front:** The hypothesis is **correct, and your own data proves it.** Security comes from **2 layers** (L13 decision gate + L8 control-flow integrity). The other 12 are coordinate plumbing or telemetry. They earn their keep only as a *governance/receipt* system — not as the detector.

---

## Part 1 — Each layer, independently, as a *security* component

Graded on one axis only: **does this layer, on its own, provide a security property?**

| Layer | What it actually computes | Independent security value |
|---|---|---|
| **L1** Complex state | `c = amp · e^{i·phase}` → `{real, imag}` | **None — plumbing.** Input formatting. |
| **L2** Realification | concat → `ℝ²ᴰ`, isometric | **None — plumbing.** Distance-preserving reshape. |
| **L3** φ-weighted transform | diagonal `√φ^k` scaling | **None — plumbing.** *And your data says it's worse than nothing:* char-TF-IDF beats `scbe_full` by **13.3%** in-domain; `scbe_nophi` ≈ `scbe_full`, so φ adds variance, not signal. |
| **L4** Poincaré embed | `tanh(α‖x‖)·x/‖x‖`, clamp to ball | **None — prerequisite** for L5's metric to be defined. |
| **L5** Hyperbolic distance | `arcosh(1 + 2‖u−v‖²/((1−‖u‖²)(1−‖v‖²)))` | **None — and it hurts.** Helix benchmark: recall **0.529 flat → 0.283 Poincaré → 0.20 helix**. Better separation, worse detection. |
| **L6** Breathing transform | `tanh(‖p‖ + A·sin ωt)·p/‖p‖` | **None — telemetry.** Deterministic time-oscillation. |
| **L7** Möbius phase | Givens rotation (isometry) | **None — plumbing.** Preserves all distances; pure navigation. |
| **L8** Hamiltonian CFI / wells | golden-path check → `VALID/DEVIATION/ATTACK/OBSTRUCTION`; `V(p)=Σ wᵢ e^{−‖p−cᵢ‖²/2σ²}` | **YES — real, separable detector.** Control-flow-integrity: does execution follow the sanctioned Hamiltonian path? This is the one *upstream* layer with standalone security value. |
| **L9** Spectral coherence | `E_low/(E_low+E_high)` (FFT) | **None — telemetry.** Phase-invariant stability score. |
| **L10** Spin coherence | mean phasor length `‖Σe^{iφ}‖/N` | **None — telemetry.** Circular-statistics alignment metric. |
| **L11** Triadic temporal | `√(d_H² + Δτ² + Δη² + (1−F_q))` | **None — telemetry.** A distance that feeds L13; decides nothing. |
| **L12** Harmonic wall | `H = 1/(1+d+2·pd)` ∈ (0,1] | **Decorative as documented.** The canonical formula lives in TS, but `runtime_gate.py` does **not** use it — the real gate uses an exponential cost `π^(φ·d*)`. The "wall" you advertise isn't the wall that runs. |
| **L13** Risk decision gate | `cost = π^(φ·weighted_drift_from_centroid)`; threshold vs budget; spin/veto overlays → `ALLOW/QUARANTINE/REVIEW/DENY` | **YES — this is the security.** The only layer that makes the allow/deny call. Everything else exists to feed it coordinates. |
| **L14** Audio axis | FFT energy/centroid/flux/HF-ratio; `risk += 0.1·(1−stability)` | **None — telemetry.** A 10% nudge on a risk number; never decides. |

**Independent-review conclusion:** Security-bearing layers = **{L8, L13}**. Plumbing = {L1–L7 except L8, plus L12 as-documented}. Telemetry = {L9, L10, L11, L14}.

A "narrow slice that works" is concretely: **a cheap feature (centroid-drift or TF-IDF) → L13 gate with thresholds**, optionally **+ L8 CFI** for execution integrity. That is 1–2 layers, and the benchmarks below show it matches or beats all 14.

---

## Part 2 — Your own benchmark evidence (this is the strong part)

| File | Finding | Implication |
|---|---|---|
| `experiments/honest_injection_results.json` | **char_tfidf AUC 0.9833** vs scbe_full 0.817 (in-domain); 0.8988 vs 0.8723 (cross-domain) | The whole pipeline is **beaten by character TF-IDF + a classifier.** |
| `experiments/semantic_vs_stub_comparison.json` | stub char-count **0.8022** vs semantic 6D cross-talk **0.6703** | The richer the semantics, the **worse** — over-parameterized. |
| `artifacts/benchmark/hyperbolic_helix_test.json` | recall **flat 0.529 > Poincaré 0.283 > helix 0.20** | Hyperbolic geometry **trades detection for tightness.** Net negative for the security job. |
| `experiments/null_space_ablation.json` | null-space +14.29% detection; **helix adds 0** on top | Only **one** added component (null-space) ever showed reproducible gain — and it cost FP rate. Helix decorative. |
| `experiments/fixed_anchor_wall_results.json` | fixed-anchor **AUC 0.9986** | A single fixed-anchor wall ≈ the whole stack's lab performance. |
| `benchmarks/.../scbe_benchmark_local_*.json` | full pipeline 1.0 acc — but file admits *"weights hand-tuned, not learned"*, *"pd simulated"*, *"regex misses semantic attacks"* | Lab-perfect, but the perfection is hand-tuning, not the geometry. |

**The narrow slice isn't a compromise — on measured detection it's the *better* product.**

---

## Part 3 — The composition: what (if anything) the full stack buys

If 2 layers detect better, why keep the other 12? Honest answer: **not for detection.** They only justify themselves as three non-detection properties — and only if you actually use them:

1. **An interpretable governance coordinate system.** The 6 tongues are a *basis you can name a reason in* ("DR/oath axis tripped"), and on a home-turf governance corpus they hit **0.91 (2× random, 92% of the learned ceiling)** — so they're a genuinely well-chosen *governance* basis even though they look random off-domain. This is what turns a yes/no classifier into a **receipt with a reason**.
2. **Escalate-only, multi-veto defense-in-depth.** L8 (CFI), L10 (spin), L11 (temporal), classifier/council overlays each sit in the *same* coordinate space and can only *raise* risk, never lower it. Independent vetoes that can't cancel each other is a real safety property a single classifier doesn't have.
3. **Session-stateful cost accumulation.** L13 carries cumulative drift across a session; a stateless TF-IDF classifier judges each prompt fresh and can be walked there one safe step at a time. The accumulator is the answer to slow-boil attacks.

**Compositional verdict:** The stack's value is **governance, interpretability, and stateful veto-stacking — i.e. the *receipt* — not the detection.** If a layer can't be tied to one of those three, it's decorative and should be demoted to optional telemetry or cut. By that test: **keep L8, L13, the tongue basis (L3 as *labels* not as weights), and the cumulative accumulator. Make L5/L6/L7/L9/L10/L11/L12/L14 opt-in telemetry, off the hot path.**

---

## Part 4 — The reframe that ties this to the CLI

A receipt is only worth printing if the work it certifies **succeeded**. The 12 telemetry/plumbing layers have been carrying the *story* of rigor while the 2 real layers do the gating — but **gating is not getting work done.** A gate that says DENY is, in your words, *proof of failure.*

So the priority inversion is:
- **Detection** is solved by a 2-layer slice — stop spending engineering there.
- **The 12 layers' real job is to produce the receipt** — keep only the parts that make the receipt *interpretable and trustworthy* (tongue labels, multi-veto, accumulator).
- **The actual product gap is execution + recovery:** the CLI must *do the work as well as competitors*, attach the receipt as a side-effect, and on failure **reroute/retry/heal** (the self-healing orchestrator already models RETRY/FALLBACK/CIRCUIT_BREAK/ESCALATE) so the receipt ends in *success*, not a documented dead-stop.

That's the next build: make the gate an **enabler with a recovery path**, not a wall with a certificate.
