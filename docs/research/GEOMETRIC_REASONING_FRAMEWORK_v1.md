# Geometric Reasoning Framework v1 (2026-07-11)

One addressable capture of the framework Issac built across a long ideation thread. It is a
**method for hard-to-conceptualize problems**: use theoretical-math structures as a candidate-
representation library, prune by the task, assign values/labels/factors inside each candidate, and
let cross-face agreement pick the survivor. Every structure below is grounded in real math with the
honest boundary of where it applies. Companion to `UNIFIED_MATH_SPINE_v2`.

**The discipline that makes it a method and not hype:** a borrowed structure is a *model* only when it
**verifiably reproduces** the problem's behavior; otherwise it is a *metaphor*. Measure before trusting.
([[honesty-firewall-in-code]], [[see-inputs-not-reviews]], [[multi-representation-route-dont-blend]].)

---

## 0. The method (representation-as-jamming-and-gömböc)

Given a hard problem: generate candidate representations from the structure library (§below), then let
the problem's *terms/needs* prune the infinite field. This narrowing is itself the framework applied to
representations: the representation space is **floppy** (infinite, unconstrained) → the task's
requirements are **constraints that jam it** to a workable rigid set → the **correct** representation is
the **gömböc-stable resting point** reasoning rolls to. You cannot and need not enumerate the infinite
(no-free-lunch: a selection bias is mandatory; relevance realization: cognition samples the relevant).

Grounding: Newell & Simon / Pólya (representation *is* the problem); frame problem / relevance
realization (Vervaeke); no-free-lunch (a bias is required); category-theoretic structure-mapping (why one
structure recurs across domains).

## 1. The dimensional ladder — what each dimension ADDS

| Dim | Adds | Load-bearing consequence |
|---|---|---|
| 0D point | presence/absence, identity | the bare yes/no |
| 1D line | order, magnitude, one graded value (slope/gradient/hue) | a path is only forward/back; *rotation does not exist yet* |
| 2D plane | rotation SO(2), depth/distance, the *relation* between axes, area, curves | **the coin trap** — Four-Vertex Theorem forces ≥2 stable states; a binary gate lives here |
| 3D volume | the gömböc (self-righting), non-commutative SO(3), chirality, knots/linking, volume, cross product | **minimum for a clean gate**; PHDM's polyhedron lives here |
| nD | more independent relations, polytope tessellation (linear regions), hyperbolic capacity, **curse of dimensionality** | tokens/weights live here; octrees fail (2^D children) |

Honest correction: rotation is a *2D* phenomenon; a 1D value's "rotation between vertical/horizontal" is
its *embedding direction* in 2D. Each dimension unlocks a specific capacity, not "more of the same."

## 2. The gömböc gate — the resting structure

A verification gate = a **Morse potential on a sphere of answer-orientations**; state rolls down
`ẋ = −∇E` to a stable minimum. Poincaré–Hopf on S²: **S − H + U = 2** (stable − saddle + unstable).
- **You cannot delete "no":** `S=1, U=0` needs `H=−1` — forbidden. ≥1 unstable equilibrium is mandatory.
- **Minimized:** `S=1` forces `U = 1+H ≥ 1`; the floor is the **gömböc {1,1}** (one stable "solved," one
  unstable "no," zero saddles). "Make no the smallest, unstable option" = the topological optimum.
- **False-accepts are expensive:** a second stable "accepted" state forces `H = S+U−2 ≥ 1` — a detectable saddle.
- **Harvesting emitters = basin-merging** (min–saddle Morse cancellations) collapsing the landscape toward {1,1}.

Sources: Várkonyi & Domokos, *Static Equilibria… Poincaré–Hopf*, J. Nonlinear Sci. 16 (2006); Domokos &
Várkonyi, *Mono-monostatic bodies* (2006); Domokos–Papadopoulos–Ruina (1994, 2D {1,1} empty ⇔ Four-Vertex);
abrasion flows (Bloore 1977, Firey 1974, Domokos–Gibbons 2012); MercuryDPM gömböc sim (arXiv:2310.05027).

**Four hard constraints (make it real, not metaphor):**
1. **Must be genuinely multi-axis (≥3D)** or it's a coin (2D → ≥2 stable → intrinsic false-accept). This is
   the rigorous reason for the **cube (many faces)** and **HYDRA (diverse quorum)** — multi-face isn't decoration.
2. **Answer-space must be compact/closed** (a sphere) for the bound to bite; on an open loss surface a lone
   min is legal. Arc-gen's finite pair-set is a valid closure.
3. **Gömböc self-corrects, it doesn't reject:** {1,1} gives one stable (correct) state, no reject-bin; a wrong
   answer sits on the measure-zero unstable knife-edge **until perturbed** — needs **active verification
   pressure** (re-execution, arc-gen probing) to tip it off.
4. **It's fragile** (gömböc is ~0.1% from a sphere; near-degenerate). Use **S − H + U = 2 as a live
   self-consistency check** — a violation means a missed or spurious basin (a hidden false-accept).

## 3. Pathfinding — the dynamics on the landscape

A path is a 1D object threading nD space (graded by the gradient, turning in 2D, knotting in 3D). The
gömböc's self-righting **is** pathfinding: the gradient flow to the single solved minimum is the path.
"Walk the legal maze" ([[navigation-coding-tool]]) and "roll to the stable pose" are one act. Collective
form: ant-colony optimization (stigmergy) finds shortest paths without a plan.

## 4. Scaffolding — the sub-rigid regime (below the gömböc)

Before a stable state exists (floppy / sub-isostatic, no solve), you **scaffold** to rigidity. Grounded in
the **Maxwell/jamming transition**: rigidity needs coordination `z ≥ z_iso = 2D` (constraints ≥ DOF); below
it there are floppy modes and no resting pose; adding constraints reaches **isostaticity** (marginally
rigid), then the **stressed-rigid** phase (robust). Biological realization: **army-ant living bridges** (Reid
& Garnier et al., PNAS 2015) — ants self-assemble their bodies across a gap (each ant = a tiny-rock
constraint), **cost-optimize** the bridge, hold it while the colony crosses, then dissolve it.

Maps exactly to the pipeline: a task with no solve is *floppy* → **fallback** = the tiny-rock scaffold →
**agent composes DSL primitives** = reaches isostatic (it reproduces) → **harvest into a clean-room emitter**
= the permanent stressed-rigid brick. task347/task257 (fallback → agent-fold → emitter) *is* this.

Sources: Maxwell constraint counting / isostatic jamming (Nagel 2010 review; arXiv:1306.4639;
cond-mat/0201366); army-ant living bridges (Reid, Garnier et al., PNAS 2015).

## 5. The system in one line

**Dimensions** set what a representation *can* encode (≥3 for a clean gate). **The gömböc** sets the
resting structure (one stable "solved," "no" the lone unstable repeller, floor S−H+U=2). **Pathfinding**
is the motion down-gradient to the sink. **Scaffolding** is what you do when no path exists yet —
self-assemble constraints across the gap, then harvest the bridge into a road. **The method** applies all
of this to *choosing the representation itself*: jam the infinite field to a workable set, roll to the
stable framing, and keep only structures that verifiably reproduce the problem.

*Self-right where you can, bridge where you can't, harvest the bridge into a road — and trust only what reproduces.*
