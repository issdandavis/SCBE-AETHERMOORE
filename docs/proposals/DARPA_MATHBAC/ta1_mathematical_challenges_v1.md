# TA1 Mathematical-Challenges Technical Mapping (v1)

**Anchor:** DARPA-PA-26-05 lines 463–486 (TA1 mathematical challenges) and lines 488–498 (TA1 deliverables).
**Purpose:** For each of the five PA-stipulated TA1 mathematical challenges, map the SCBE-AETHERMOORE primitive(s) that address it, give the operator-theoretic / dynamical-systems formulation, and note the literature provenance. This document is **subdomain-agnostic feeder material for Vol I §4** (Technical Approach). It does *not* commit Decision Boxes A–D; it commits the *method* that any chosen subdomain will instantiate.
**Status:** v1 draft 2026-04-29 (closes Vol-I prep dependency that does not require Decision Box resolution).
**Written under:** PA-26-05 line 463–464 ("Proposals must state how they will address the following … mathematical challenges").

---

## 0. Composition principle (read this first)

The five PA mathematical challenges are not five independent boxes; they decompose along the SCBE 14-layer pipeline as a single composed operator

```
T = L14 ∘ L13 ∘ L12 ∘ … ∘ L1
```

with five accompanying axioms (Unitarity, Locality, Causality, Symmetry, Composition) that govern when the composition is well-posed. The mapping below is therefore not five separate proposals — it is one operator-theoretic framework whose pieces happen to land on the five PA challenges.

| TA1-MC | SCBE pipeline locus | Axiom(s) primarily exercised |
|---|---|---|
| MC-1 Agents as Operators | L1–L4 (lift), L5–L7 (hyperbolic transport) | Unitarity (L2, L4, L7), Composition (L1, L14) |
| MC-2 Communication Protocols in Operator Networks | L8 (Hamiltonian CFI), L7 (Möbius phase) | Locality (L3, L8), Symmetry (L5, L12) |
| MC-3 Performance Prediction | L11 (triadic temporal), L12 (harmonic wall) | Causality (L11, L13), Symmetry (L12) |
| MC-4 Protocol Optimization | L13 (risk decision / governance) | Causality (L13) |
| MC-5 Construction of an Oracle | L9–L10 (spectral + spin coherence), L14 (audio axis telemetry) | Symmetry (L9, L10), Composition (L14) |

This composition-table is the structural claim that PA line 488 ("a Quantitative Mathematical Framework: a theory to describe, analyze, and evaluate the design and implementation of multi-agent communication") is asking us to deliver. The five sections below populate the cells.

---

## TA1-MC-1 — Agents as Operators / Systems

### PA verbatim (lines 465–469)
> "Develop mathematical techniques, such as system identification and input-output based reduced-order modeling, to locally approximate/represent individual AI agents as (1) mathematical operators operating on token strings (or more generally, multimodal input streams) and/or (2) systems with inputs, internal states (in the agent latent space), and outputs."

### SCBE primitive
- **L1 → L4 lift:** Complex-context ingestion (L1) → realification (L2) → langues-weighted transform (L3) → Poincaré ball embedding (L4) — the composed map `Φ: tokens → Poincaré ball B^n` is the SCBE *agent operator*.
- **Reduced-order model (ROM):** Each agent is identified at the latent-space level by the triple `(Φ_i, U_i, ψ_i)` where `Φ_i` is the per-agent lift, `U_i` is a unitary preconditioner derived from the Langues Weighting System (φ-scaled tongue weights), and `ψ_i ∈ B^n` is the agent's working hyperbolic state.
- **Input-output bookkeeping:** Tokens-in = preimage of `Φ_i`; tokens-out = inverse of L14 (audio-axis decode). Internal latent state is the hyperbolic position `ψ_i` plus the breathing-transform phase (L6).

### Operator-theoretic formulation
For an agent `A_i` with token alphabet `T_i` and latent dim `n_i`,
- `Φ_i : T_i^* → B^{n_i}` is the *lift*. It is a composition `Φ_i = Ψ_α ∘ W_φ ∘ Φ_1 ∘ E_i` of an embedding `E_i : T_i^* → C^D`, the realification `Φ_1 : C^D → R^{2D}` (a *strict linear isometry*; verified in `src/symphonic_cipher/scbe_aethermoore/proofs_verification.py` Theorem 2.1, 100 random trials), the langues-weighting `W_φ : R^{2D} → R^{2D}` (SPD-weighted reparameterization under the metric `g_φ`), and the Poincaré radial map `Ψ_α : R^{2D} → B^{n_i}` (a *direction-preserving smooth radial diffeomorphism* into the open ball — not a Euclidean isometry; preserves direction and strict ball containment, see `unitarity_axiom.py` `LAYER_PROPERTIES[4].strict_isometry = False`). The composition `Φ_i` is therefore a smooth injection, not an isometry of Euclidean norm.
- The agent's *one-step operator* on the latent ball is `S_i = Phase_i ∘ Breathe_i ∘ Move_i`, where:
  - `Phase_i = R_φ ∘ ⊕_a` (Möbius translation by `a` followed by rotation `R_φ`) is a *strict isometry of the hyperbolic distance `d_H`* (Theorem 7.2 in `proofs_verification.py`; verified in `tests/industry_standard/test_hyperbolic_geometry_research.py::TestPoincareIsometries::test_rotation_preserves_distance`),
  - `Breathe_i` is a *smooth radial diffeomorphism that preserves ball containment but is **not** an isometry of `d_H`* (it modulates radial scale by design; the test `tests/industry_standard/test_hyperbolic_geometry_research.py::TestBreathingTransform::test_breathing_changes_distances` enforces this non-trivially),
  - `Move_i` is the residual learned displacement (an arbitrary smooth map of `B^{n_i}` into itself) supplied by the foundation model's hidden-state update.
- Consequently `S_i` is a *smooth diffeomorphism of `B^{n_i}`* whose Möbius factor (`Phase_i`) preserves `d_H` and whose breathing factor introduces controlled radial dilation — it is **not** itself a Möbius isometry, and the proposal does not claim it to be one.
- The *ROM* is the rank-r SVD of the Jacobian of `S_i` evaluated at the agent's working state; rank `r` is chosen by spectral-gap thresholding (see MC-3 below). System-identification is therefore Galerkin projection of `S_i` onto its dominant `r` linearised modes about the working point.

### Subdomain-independence
Φ_i is defined on token strings, not on chemistry/biology/physics tokens specifically. The choice of Decision Box A (subdomain) determines only the *foundation model* whose hidden states feed `Φ_i`; the operator-theoretic structure is invariant.

### Prior art / literature
- van Overschee & De Moor, *Subspace Identification for Linear Systems* (1996) — system-ID with input-output data.
- Brunton, Proctor & Kutz, "Discovering governing equations from data" (PNAS 2016) — sparse identification of nonlinear dynamics (SINDy).
- Mezić, "Spectral properties of dynamical systems, model reduction and decompositions" (Nonlinear Dyn. 2005) — Koopman-operator viewpoint.
- Cannon, Floyd, Kenyon & Parry, "Hyperbolic geometry" (Flavors of Geometry, MSRI 1997) — Poincaré ball foundations.
- Nickel & Kiela, "Poincaré embeddings for learning hierarchical representations" (NeurIPS 2017) — empirical hyperbolic embeddings.

### Vol I §4 placement
§4.1 "Agent operator model and reduced-order representation."

---

## TA1-MC-2 — Communication Protocols in Operator Networks

### PA verbatim (lines 470–474)
> "Adapt and extend the fidelity (e.g., via hierarchical spectral augmentation of the rank) of the identified models of the operators/systems as well as graph theory tools to analyze, evaluate the performance of, and design efficient complex networked interactions (including internal cascades and recurrences) toward the desired goals."

### SCBE primitive
- **Network = Hamiltonian CFI multi-well (L8):** Agents `{A_1, …, A_N}` are identified with wells `{W_1, …, W_N}` of a shared Hamiltonian `H` on `B^n × B^n × … × B^n`. Inter-agent edges = saddle-point trajectories between wells.
- **Möbius phase (L7) = protocol step:** Each communication act is a Möbius isometry of the joint manifold; sequences of Möbius steps are the *protocol*.
- **Hierarchical spectral augmentation:** PA-suggested term realised as recursive ROM refinement — when the rank-r ROM of `S_i` (MC-1) under-fits an inter-agent interaction, augment to rank `r+Δr` by adding the next dominant Möbius modes; refine until spectral residual `< ε`.

### Graph-theoretic formulation
Build the *protocol graph* `G_t = (V, E_t)` at campaign time `t`:
- `V = {A_1, …, A_N}` (agents).
- `E_t = {(i,j) : a non-trivial Möbius step S_{ij} occurred in window [t-w, t]}`, weighted by `‖log(S_{ij})‖` (Möbius generator norm = communication "energy").
The graph Laplacian `L(G_t)` admits spectral analysis; its algebraic connectivity `λ_2(L(G_t))` is the *coherence* of the agent network and feeds CDPTI (see `proposer_added_metrics_v1.md`, Metric 3).

**Implementation status (Phase I work-package — see open question 7):** Two Laplacian building blocks ship in code today: (a) a normalised graph Laplacian `L = I − A_row` on the static 16-node PHDM mesh in `src/m4mesh/mesh_graph.py:51` (used as a diffusion operator, not yet for spectral connectivity readout), and (b) a Tarski (lattice-valued, meet-based) Laplacian on cellular sheaves in `src/harmonic/sheafCohomology.ts:206-708` (used for consensus / global-section detection, mathematically distinct from the spectral Fiedler Laplacian invoked here). The time-windowed *protocol graph* `G_t`, the Möbius-generator edge weight `‖log(S_{ij})‖`, and the algebraic-connectivity readout `λ_2(L(G_t))` are explicit Phase I instrumentations on top of these primitives, scheduled for M3.

### Cascades and recurrences
- **Cascade detection:** A cascade is a directed acyclic subgraph of `G_t` with monotonically increasing edge weights — algorithmically, a topological sort + weight monotonicity check.
- **Recurrence detection:** A recurrence is a strongly-connected component of `G_t` of size ≥ 3 — Tarjan's algorithm.

**Implementation status (Phase I work-package — see open question 7):** Topological-sort cascade detection and Tarjan SCC recurrence detection are not yet shipped in `src/`; they are explicit M3–M6 deliverables built atop the protocol-graph instrumentation above. Existing code carries unrelated graph utilities (e.g. `src/m4mesh/scbe_graph.py` adjacency builders, `src/crypto/nodal_graph.py` flow utilities, `src/network/contact-graph.ts` DTN contact graphs) which provide adjacency + traversal infrastructure to build on, but the directed-acyclic-cascade and SCC-recurrence detectors themselves are Phase I work.

### Subdomain-independence
The Hamiltonian `H` is parameterised by langues weights `φ^k` (k = 0..5 for KO/AV/RU/CA/UM/DR), not by domain-specific potentials. Subdomain pick (Decision Box A) only affects the *initial-condition catalog* fed to `H`, not its structure.

### Prior art / literature
- Newman, *Networks: An Introduction* (Oxford, 2010) — graph spectra, community detection.
- Lovász, *Large Networks and Graph Limits* (AMS, 2012) — spectral graph limits.
- von Luxburg, "A tutorial on spectral clustering" (Stat. Comput. 2007).
- Mac Lane, *Categories for the Working Mathematician* (Springer, 1971) — composition of operators.
- Karplus & McCammon, "Molecular dynamics simulations of biomolecules" (Nat. Struct. Biol. 2002) — Hamiltonian-system framing of multi-particle dynamics (PA-cited at line 322).

### Vol I §4 placement
§4.2 "Protocol graph and Hamiltonian multi-well network."

---

## TA1-MC-3 — Performance Prediction

### PA verbatim (lines 475–478)
> "Formulate discrete mathematical models to estimate/analyze how different successive combinations/permutations of agent (operator, system) actions systematically affect the collective's efficiency, stability, and convergence over broad classes of related domain tasks."

### SCBE primitive
- **L11 triadic temporal distance:** Underlying quantity is the 3-tuple `d_tri(t) = (d_immediate(t), d_medium(t), d_long(t))` capturing collective efficiency at short/medium/long horizons. Canonical scalar aggregation used at the L11→L12 boundary is the φ-weighted linear combination `d_tri(t) = (1·d_immediate + φ·d_medium + φ²·d_long) / (1 + φ + φ²)` per `src/geosealCompass.ts:672`. Two alternative aggregations also exist in code — a φ-power mean `d_tri = (Σ_k λ_k·d_k^φ)^(1/φ)` in `src/polly_pads_runtime.py:648`, and a triangle-inequality residual `d_tri = mean_i max(0, d(p_i,p_{i+1}) + d(p_{i+1},p_{i+2}) - d(p_i,p_{i+2}))` in `src/crypto/dual_lattice_integration.py:503` — see open question 5 below for the reconciliation work-package. The scalars are *aggregations* of, not substitutes for, the 3-tuple, which is the object referenced in the convergence theorem below.
- **L12 harmonic wall:** `H(d, pd) = 1/(1 + φ·d_H + 2·pd) ∈ (0, 1]` — the canonical safety/efficiency score, monotone in hyperbolic distance `d_H` and predictive density `pd`. Code-level definition at `src/api/search_enrichment.py:250` (explicitly labelled "Canonical harmonic wall"), `src/geosealCompass.ts:383`, `src/fleet/dtn-bundle.ts:160`, and `src/symphonic_cipher/scbe_aethermoore/layers/fourteen_layer_pipeline.py:922`. The kernel back-compat path in `packages/kernel/src/harmonicScaling.ts:53` uses the un-φ-weighted variant `1/(1+d+2·pd)`; the φ-weighted form is the one used at the L12→L13 boundary in the Cauchy-Core path and is what this proposal commits to. (See open question 4 below for the formula-provenance reconciliation work-package.)
- **Lyapunov candidate:** `V(t) = -log H(d(t), pd(t))` is a candidate Lyapunov function whose monotone decrease along a protocol trajectory certifies *convergence* in the PA sense.

### Discrete-mathematical model
For a campaign of `K` protocol steps, define the *step-cost vector*
```
c_k = (c_token_k, c_time_k, c_failure_k, c_energy_k, c_compliance_k) ∈ R_+^5
```
and the *combination function*
```
C(σ) = Σ_{k ∈ σ} c_k + Λ · interactions(σ)
```
where `σ ⊆ {1, …, K}` is a subset/permutation of steps and `Λ` is a coupling matrix capturing pairwise step interactions. Combinations and permutations of the discrete `c_k` vectors give all relevant orderings; `H(d, pd)` provides the scalar performance summary the PA asks for.

### Stability + convergence theorems (to be proved in Vol I §4.3)
- **Stability:** Under the SCBE Symmetry axiom (gauge invariance of the langues metric under tongue permutation), `H` is invariant to relabeling of agents. This is the discrete analog of *exchange stability*.
- **Convergence:** If `V(t+1) ≤ (1 - η) V(t) + b` for some `η > 0`, `b ≥ 0`, the protocol converges to a sublevel set of `V` of radius `O(b/η)` — a discrete-time Lyapunov result (Khalil, *Nonlinear Systems*, Th. 4.16, adapted).

### Subdomain-independence
`d_H` and `pd` are computed from latent-space states that exist for any foundation model; the cost vector `c_k` admits subdomain-specific tokens (e.g., GPU-hours, wet-lab cost) by adding components to `c_k` without changing the convergence theorem.

### Prior art / literature
- Khalil, *Nonlinear Systems* (Prentice Hall, 3rd ed. 2002) — Lyapunov stability for discrete-time systems.
- Bertsekas, *Dynamic Programming and Optimal Control* (Athena Sci., 2017) — combination/permutation cost formalisms.
- Boyd & Vandenberghe, *Convex Optimization* (Cambridge, 2004).
- Cohen-Steiner, Edelsbrunner, Harer, "Stability of persistence diagrams" (Discrete Comput. Geom. 2007) — multi-scale temporal stability.
- Strogatz, *Nonlinear Dynamics and Chaos* (Westview, 2nd ed. 2014).

### Vol I §4 placement
§4.3 "Performance prediction via harmonic-wall scoring and Lyapunov certification."

---

## TA1-MC-4 — Protocol Optimization

### PA verbatim (lines 479–482)
> "Formulate and solve discrete/continuous optimization problems (with defined cost functions (e.g., token usage, solution time) and performance metrics) to minimize end-to-end overall campaign cost while maximizing task success frequency."

### SCBE primitive
- **L13 risk-decision tier (ALLOW / QUARANTINE / ESCALATE / DENY):** discrete action space `A = {a_0, a_1, a_2, a_3}` per step.
- **Cost-functional formulation:** Bicriteria objective
```
minimise   J(π) = E_π[ Σ_t c_t ]                 (campaign cost)
subject to Pr_π[ task_success ] ≥ τ              (success frequency lower bound)
           ACV(π) ≥ ACV_min ∈ [0,1]^5            (axiom-compliance side constraint)
```
where `π : H_t → A` is a policy mapping the histored state to a tier action, `c_t` is the per-step cost (MC-3), and `ACV` is the Axiom Compliance Vector (see `proposer_added_metrics_v1.md`, Metric 2).
- **Mixed discrete/continuous:** Tier choice is discrete (4 actions); within-tier continuous parameters (e.g., temperature, top-p, retry budget) form a continuous action subspace `Θ ⊂ R^p`. The combined action is `(a, θ) ∈ A × Θ`.

### Algorithm
- **Phase I baseline:** Solve the constrained problem via Lagrangian relaxation
```
L(π, λ, μ) = J(π) + λ · (τ - Pr_π[success]) + ⟨μ, ACV_min - ACV(π)⟩
```
with subgradient updates on `(λ, μ)` and policy-gradient or value-iteration on `π` over the discrete-continuous space.
- **Phase II direction:** "Evolution Team" partner (TA2) supplies discovered protocol *principles* as additional constraints `g_k(π) ≤ 0`, narrowing feasible region.

### Subdomain-independence
The cost vector `c_t` and the success indicator are subdomain-typed; the optimization framework is not. Decision Box A only fixes the *instantiation* of `c_t` and `success`.

### Prior art / literature
- Bertsekas, *Constrained Optimization and Lagrange Multiplier Methods* (Athena Sci., 1996).
- Sutton & Barto, *Reinforcement Learning: An Introduction* (MIT, 2nd ed. 2018) — policy iteration, constrained MDPs.
- Altman, *Constrained Markov Decision Processes* (CRC, 1999).
- Rockafellar, *Convex Analysis* (Princeton, 1970) — Lagrangian duality.
- Boyd, Parikh & Chu, "Distributed optimization and statistical learning via ADMM" (Found. Trends Mach. Learn. 2011).

### Vol I §4 placement
§4.4 "Protocol optimization as constrained MDP over tier action space."

---

## TA1-MC-5 — Construction of an Oracle

### PA verbatim (lines 485–486)
> "What information is needed, how much, what type, etc. to confirm semantic communication between agents was understood."

### SCBE primitive
- **L9 spectral coherence + L10 spin coherence:** FFT-based coherence between the latent-space trajectories of two communicating agents `A_i`, `A_j`, plus quantum-inspired spin alignment of the resulting frequency signatures.
- **L14 audio-axis telemetry:** Phase-modulated audio waveform encoding the communication act for IV&V replay and verifier scoring.
- **Symphonic-cipher trust score:** Bounded score `H_cipher ∈ (0,1]` derived from the harmonic wall, used as the per-act semantic-confirmation oracle.
- **Mathematical Evidence Emission (MEE):** independent verifier scoring of mathematical artifacts emitted in the communication (see `proposer_added_metrics_v1.md`, Metric 1) — answers PA's "what type" of information question.

### Information-theoretic formulation
Let `X_i`, `X_j` denote the latent-state random variables of agents `A_i`, `A_j` over a communication window. The oracle confirms semantic-understanding when *all three* of the following hold:
1. **Mutual information:** `I(X_i; X_j) ≥ I_min` (sufficient mutual content).
2. **Spectral coherence:** `|S_{ij}(f)|^2 / (S_{ii}(f) S_{jj}(f)) ≥ γ_min` for `f` in the protocol band (signal alignment).
3. **Verifier check:** `MEE(act) ≥ MEE_min` (the emitted mathematical artifact validates).

PA's "how much" is answered by the trio `(I_min, γ_min, MEE_min)`, calibrated per subdomain in the Phase I M3 milestone.

### Falsifiability
The oracle is *falsifiable* by design: ablate any one of the three checks and the oracle's true-positive rate must drop measurably on a held-out test set of known-confirmed and known-unconfirmed communication acts. This is the IV&V Living-Metric companion test.

### Subdomain-independence
All three quantities (`I`, `S_{ij}`, `MEE`) compute on latent-space and emitted-token streams that exist for every foundation model. Calibration thresholds are subdomain-tunable; structure is not.

### Prior art / literature
- Cover & Thomas, *Elements of Information Theory* (Wiley, 2nd ed. 2006).
- Tishby, Pereira & Bialek, "The information bottleneck method" (Allerton 1999).
- Brillinger, *Time Series: Data Analysis and Theory* (SIAM Classics, 2001) — coherence spectrum.
- Carter, "Coherence and time delay estimation" (Proc. IEEE 1987).
- Lewis, Tu, Goyal *et al.*, "Minerva: solving quantitative reasoning problems with language models" (NeurIPS 2022) — automated math-artifact verification.
- Polu & Sutskever, "Generative language modeling for automated theorem proving" (2020).

### Vol I §4 placement
§4.5 "Oracle construction via spectral+information+verifier triplet."

---

## Cross-cutting notes

### Composition with TA1 deliverables
- **Deliverable A (Quantitative Mathematical Framework, M12):** This document, expanded with proofs, *is* the framework. The composition table in §0 provides the structural skeleton.
- **Deliverable B (Computational Design Tool, M14):** Reference implementation lives in `src/harmonic/pipeline14.ts` (TS) and `src/symphonic_cipher/scbe_aethermoore/` (Py). Phase I milestone M14 packages this as a reproducible toolchain with the Vol I subdomain instantiated.
- **Deliverable C (Catalog of Protocol Design Principles, M16):** PIS (Metric 4 in `proposer_added_metrics_v1.md`) provides the principle-vector representation; the catalog is the persisted set of high-PIS-cluster centroids with human-readable annotations.

### DARPA programmatic lineage

The framework above sits in a direct lineage from prior I2O investments in trustworthy distributed multi-agent systems. **DARPA Mission-oriented Resilient Clouds (MRC)** — the I2O program that ran ~2011–2017 — established the reviewer vocabulary for "manageable taskable diversity across homogeneous hosts," mission-aware adaptive networking, and trust orchestration under adversarial conditions ([darpa.mil/research/programs/mission-oriented-resilient-clouds](https://www.darpa.mil/research/programs/mission-oriented-resilient-clouds), and JHU's Intrusion-Tolerant Clouds project as a representative MRC participant). The SCBE primitives proposed here are the post-quantum, geometrically-grounded successor to that framing:

- **L8 Hamiltonian CFI / multi-well realms** is the MRC "manageable taskable diversity" claim made operator-theoretic — wells are the discrete diversity classes, the Hamiltonian governs the cost of crossing between them.
- **L13 risk-decision governance** (ALLOW / QUARANTINE / ESCALATE / DENY) is the MRC "mission-aware adaptive response" surface made formally typable, with the harmonic wall `H = 1/(1 + φ·d_H + 2·pd)` providing the bounded scoring function MRC reviewers asked for but pre-hyperbolic embeddings could not deliver.
- **L14 audio-axis FFT telemetry** is the MRC "trust telemetry" channel made cryptographically commitable via the L7 Möbius phase signature.

This is a one-paragraph positioning note, not a citation network — Vol I §4 will fold MRC's two most-cited TA1/TA2 deliverables into the relevant prior-art lists alongside the academic anchors. The point is that MATHBAC TA1 reviewers (I2O lineage) will recognize the pedigree on first read.

### Compatibility with proposer-added metrics
| MC | Metrics that score it |
|---|---|
| MC-1 | ACV (axiom compliance of the operator), MEE (oracle artifacts) |
| MC-2 | CDPTI (network spectral transitions), ACV |
| MC-3 | Living Metric (PA-supplied), ACV, CDPTI |
| MC-4 | Living Metric (success-rate / speedup), CDPTI |
| MC-5 | MEE (semantic-content verification), PIS (principle distillation) |

The four proposer-added metrics jointly cover all five challenges; no MC is left without an instrumentation surface.

### Phase II hand-off to TA2 ("Evolution Team")
- MC-1's reduced-order operator `S_i` is exactly the input TA2 needs for joint-manifold learning of "consistent low-dimensional structures shared across multiple latent-space point clouds" (PA lines 536–542).
- MC-5's oracle output stream is the input TA2 needs for "principles, laws, or correlations" extraction (PA lines 517–518).
- The PIS metric provides the geometric/topological characterization PA asks for in TA2's second mathematical challenge (PA lines 543–546) at the protocol level.

### Honest open questions (to be resolved during Phase I)
1. **Hierarchical spectral augmentation rate:** PA hints at this (line 471) but does not specify; we will explore `Δr ∈ {1, 2, 4, 8}` with stability/cost tradeoff curves at M3.
2. **Lyapunov constant `η` (MC-3):** No published value carries over directly from RLHF convergence-rate literature to the harmonic-wall scoring used here, so we deliberately do *not* commit a numeric range in this draft. `η` is to be **measured at M3 per subdomain** under the IV&V protocol. The contraction inequality `V(t+1) ≤ (1 - η) V(t) + b` is the *form* of the convergence claim; the constants are an empirical M3 deliverable.
3. **Oracle threshold triplet `(I_min, γ_min, MEE_min)` (MC-5):** Calibration is the M3 work product; expect re-calibration after M9 ROM availability.
4. **Harmonic-wall formula provenance and reconciliation:** The codebase currently carries five `H` variants ascribed to L12 across files, with three distinct functional forms — (i) the un-φ-weighted bounded score `1/(1 + d + 2·pd)` in `packages/kernel/src/harmonicScaling.ts:53` (kernel back-compat path; replaces the deprecated `R^(d²)` per the `harmonicScaling.ts` v3.3 header note about AUC collapse); (ii) the φ-weighted bounded score `1/(1 + φ·d_H + 2·pd)` used at the L12→L13 boundary in `search_enrichment.py`, `geosealCompass.ts`, `dtn-bundle.ts`, `fourteen_layer_pipeline.py` (committed-to form for this proposal); (iii) the Cauchy-Core form `1/(1 + φ·d_H + 2·pd + κ(t)/d_H)` in `fourteen_layer_pipeline.py:918` for trajectories near the boundary; plus the legacy `R^(d²)` super-exponential cost form in `src/symphonic_cipher/core/harmonic_scaling_law.py` and the risk-amplification multiplier `H_wall = 1 + α·tanh(β·d*)` in `src/symphonic_cipher/harmonic_scaling_law.py`. Vol I §4.3 will declare form (ii) the canonical L12 wall and treat (i) as its φ→1 specialisation; (iii) is reserved for the boundary-stable extension. M3 deliverable: a single `H` glossary entry under `docs/specs/` per the strict-rigor convention, with deprecation notes on (legacy) and a one-line equivalence proof of (i) ≡ (ii)|_{φ=1}.
5. **Triadic temporal distance aggregation choice:** Three distinct scalar aggregations of the L11 3-tuple `(d_immediate, d_medium, d_long)` ship in code today — (i) the φ-weighted linear combination `(1·d_imm + φ·d_med + φ²·d_long)/(1+φ+φ²)` in `src/geosealCompass.ts:672` (canonical for the L11→L12 boundary because its component labels match `(d_imm, d_med, d_long)` directly), (ii) the φ-power mean `(λ_1·d_1^φ + λ_2·d_2^φ + λ_3·d_g^φ)^(1/φ)` in `src/polly_pads_runtime.py:648` (operates on directional traces, not timescales), (iii) the triangle-inequality residual `mean_i max(0, d(p_i,p_{i+1}) + d(p_{i+1},p_{i+2}) - d(p_i,p_{i+2}))` in `src/crypto/dual_lattice_integration.py:503` (a path-geodesic admissibility measure, distinct from the timescale aggregation). The proposal commits to (i) as the canonical L11→L12 boundary scalar; (ii) is reserved for the trace-planning subsystem and (iii) for path-admissibility gating. M3 deliverable: a single `d_tri` glossary entry under `docs/specs/` per the strict-rigor convention, with the three forms explicitly disambiguated by context-of-use and a one-line monotonicity proof of the canonical form in each component. The earlier doc-text claim of "exponentially-windowed timescales" was inaccurate — none of the three implementations uses exponential windowing — and is dropped in v1.2.
6. **Möbius-step generator norm:** L7 currently uses Frobenius norm of the generator; spectral norm may give tighter cascade-detection bounds — to be benchmarked at M6.
7. **MC-2 graph-instrumentation gap:** The MC-2 Phase-I work-package builds the time-windowed protocol graph `G_t` and four spectral / combinatorial readouts on top of it — (i) Möbius-generator edge weight `‖log(S_{ij})‖`, (ii) algebraic connectivity `λ_2(L(G_t))`, (iii) topological-sort cascade detection on monotone-weight DAG subgraphs, (iv) Tarjan strongly-connected-component recurrence detection at size ≥ 3 — none of which ship in `src/` today. What ships is two Laplacian building blocks (normalised graph Laplacian on the static PHDM mesh in `src/m4mesh/mesh_graph.py:51`; Tarski lattice Laplacian on cellular sheaves in `src/harmonic/sheafCohomology.ts:206-708`) plus adjacency / traversal scaffolding (`src/m4mesh/scbe_graph.py`, `src/crypto/nodal_graph.py`, `src/network/contact-graph.ts`). M3 deliverable: spec sheet for each of (i)–(iv) under `docs/specs/protocol_graph/`, with reference Python implementation, complexity bounds, and synthetic-graph unit tests. M6 deliverable: integration with the IV&V protocol per `proposer_added_metrics_v1.md` Metric 3 (CDPTI). This work-package is named explicitly so reviewers do not mistake the MC-2 graph-theoretic formulation for shipped instrumentation; the *primitives* (Möbius isometries, Hamiltonian wells, Laplacians as diffusion operators) are shipped, but the *graph-theoretic instrument* on top is Phase I.

---

## Status

- **v1 — 2026-04-29:** drafted.
- **v1.1 — 2026-04-29 (same day):** code-verification pass. (a) MC-1 operator-theoretic claims tightened to match shipped code: L2 strict isometry verified (`proofs_verification.py` Theorem 2.1), L4 explicitly *not* a Euclidean isometry (`unitarity_axiom.py` `LAYER_PROPERTIES[4].strict_isometry = False`), L7 phase transform strict `d_H` isometry verified (Theorem 7.2 + `test_hyperbolic_geometry_research.py::TestPoincareIsometries`), L6 breathing explicitly *not* an isometry (`TestBreathingTransform::test_breathing_changes_distances`). The composed one-step operator `S_i` is now described as a smooth diffeomorphism, not a Möbius isometry. (b) Lyapunov `η` numeric range removed; "to be measured at M3 per subdomain."
- **v1.1a — 2026-04-29 (same day):** L12 H-formula provenance audit. Five `H` variants exist in code; proposal commits to `1/(1+φ·d_H+2·pd)` as canonical L12 wall (open question 4); M3 obligation: single `docs/specs/H.md` glossary entry with deprecation notes on legacy super-exponential and risk-amplifier forms.
- **v1.2 — 2026-04-29 (same day):** L11 `d_tri` code-verification pass. Three distinct `triadic_temporal_distance` implementations exist in code: (i) linear φ-weighted sum at `src/geosealCompass.ts:672` (canonical for L11→L12 boundary), (ii) φ-power mean at `src/polly_pads_runtime.py:648` (trace-planning subsystem), (iii) triangle-inequality residual at `src/crypto/dual_lattice_integration.py:503` (path-admissibility gating). Proposal commits to (i) as canonical; (ii)/(iii) reserved for distinct subsystems. Earlier "exponentially-windowed timescales" framing in v1/v1.1 was inaccurate — none of the three implementations uses exponential windowing — and is retracted in v1.2 (line 108 + open question 5). Cycle-3 verification also confirmed clean: L1 composition matches `composition_axiom.py` LayerType signatures; L13 four-tier action space matches `src/index.ts:240-318` decision ladder; L14 audio-axis features match `packages/kernel/src/audioAxis.ts` FFT computations.
- **v1.4 — 2026-05-07:** added DARPA programmatic-lineage subsection under Cross-cutting notes positioning SCBE as the post-quantum, geometrically-grounded successor to DARPA I2O Mission-oriented Resilient Clouds (MRC, completed ~2011–2017). MRC is referenced by program-page URL and the JHU Intrusion-Tolerant Clouds participant. Three SCBE primitives (L8 Hamiltonian CFI, L13 governance, L14 audio-axis telemetry) are named as the operator-theoretic / hyperbolic-geometry successors to MRC's "manageable taskable diversity," "mission-aware adaptive networking," and "trust telemetry" framings. Vol I §4 will fold MRC TA1/TA2 deliverables into prior-art lists. Purpose: make the I2O reviewer pedigree explicit on first read; not a citation network.
- **v1.3 — 2026-04-29 (same day):** MC-2 graph-theoretic claims audited against shipped code. Finding: the protocol graph `G_t`, Möbius generator-norm edge weight `‖log(S_{ij})‖`, algebraic connectivity `λ_2(L(G_t))`, topological-sort cascade detection, and Tarjan SCC recurrence detection are **not yet shipped** in `src/`; they are explicit Phase I instrumentation built atop two existing Laplacian primitives (normalised PHDM graph Laplacian in `src/m4mesh/mesh_graph.py:51`; Tarski lattice Laplacian in `src/harmonic/sheafCohomology.ts:206-708`). MC-2 sections "Graph-theoretic formulation" and "Cascades and recurrences" now carry explicit "Implementation status (Phase I work-package)" callouts; new open question 7 catalogues the four gaps as M3/M6 deliverables under `docs/specs/protocol_graph/`. Disclosure protects the proposal from "claimed shipped, found absent" reviewer findings while preserving the technical case (primitives are shipped, instrument on top is Phase I).
- **Punch-list link:** advances Vol I §4 prep (item #8) without committing Decision Boxes A–D.
- **Subdomain coupling:** zero. Decision Box A pick narrows only foundation-model choice and cost-vector instantiation; the operator-theoretic structure above is invariant.
- **Folds into:** Vol I §4 (Technical Approach), Section 3.2 of `pa_26_05_compliance_checklist.md` (TA1 mathematical-challenges status).
- **Companion artifact:** `proposer_added_metrics_v1.md` (the four proposer-added metrics that instrument the five challenges above).
- **Next gate:** Decision Boxes A–D resolution (see `decision_boxes_a_d_prep.md`) before Vol I §4 is locked.
