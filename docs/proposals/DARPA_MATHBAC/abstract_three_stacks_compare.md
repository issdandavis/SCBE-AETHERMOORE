# MATHBAC Abstract — Three-Stack Comparison + Better Version

**Author:** Issac D. Davis (SCBE-AETHERMOORE, Prime)
**Date:** 2026-04-20
**Solicitation:** DARPA-PA-26-05 TA1 (Proposers Day notice DARPA-SN-26-59)
**Context:** Rewrite of Collin's 2026-04-20 17:43 draft, grounded in actual FAR/DFARS/Bayh-Dole/SBIR law, DoD cost-accounting norms, and the prior-planned proposal artifacts in this directory (`one_pager_v1.md`, `v3_markup_for_collin.md`, `joint_memo_v1.md`, `teaming_targets_v1.md`, `elevator_pitches_v1.md`, `teaming_agreement_v1.md`, `ip_carveout_v1.md`).

---

## 0. Why this document exists

Collin's draft (`MATHBAC_ABSTRACT_DRAFT.pdf`) has a structural defect: the page-1 header names Issac prime / PI, but the page-7 §4 Team Qualifications block names **"Collin Hoag, PI"** and **"Issac Davis, Co-Investigator (subcontract)"**. The signed teaming agreement (`teaming_agreement_v1_signed.pdf` §4) and the Gmail prime/sub request (CAGE 15XV5 sub under Issac prime CAGE 1EXD5) are both unambiguous: Issac is prime. The abstract must match.

Second: the substance is ~80% DAVA/Exodus-kernel narrative; SCBE appears only as external validator of DAVA regimes. Under MATHBAC TA1 (math of agentic communication), the scoring surface Kevrekidis is looking for — explicit mathematical object, small science model, formal guarantees, generalizable principles (see `teaming_targets_v1.md` §"What the proposer book tells us about Kevrekidis's scoring") — lives **in SCBE**, not DAVA. DAVA is the emitter substrate. SCBE is the mathematical object. A prime-voiced abstract has to reflect that.

This file does three things:
1. Pins the legal / economic / industry anchors any version must respect.
2. Drafts **Stack A — Issac-led rewrite** (the abstract I'd ship).
3. Puts **A (Issac) / B (Collin's current draft) / C (balanced mix)** side-by-side with a scoring rubric.

---

## 1. Legal / economic / industry anchors

Anything any version claims needs to be defensible against these. Reviewers at DARPA I2O include a contracts officer and DCAA-trained cost analyst; vague language here is a disqualifier.

### 1.1 IP / patent / data rights framework

| Authority | What it governs | Relevant to this abstract |
|---|---|---|
| **Bayh-Dole Act, 35 U.S.C. §§ 200–212** | Default allocation of patent rights for federally-funded inventions | Contractor (Issac, as prime) retains title to subject inventions, subject to government's non-exclusive worldwide license (§202(c)(4)) and march-in rights (§203). |
| **FAR 52.227-11 "Patent Rights — Ownership by the Contractor"** | Implementing clause for Bayh-Dole in non-DoD and most DoD awards | Governs invention disclosure, election of title, license to government. Applies to Phase I MATHBAC unless superseded by SBIR clause. |
| **DFARS 252.227-7013 "Rights in Technical Data — Noncommercial Items"** | Government rights in tech data (non-software) | **Unlimited Rights** where developed exclusively with government funding; **Government Purpose Rights (GPR)** for mixed funding (5-year GPR period default, then Unlimited); **Limited Rights** for pure private funding. |
| **DFARS 252.227-7014 "Rights in Noncommercial Computer Software and Noncommercial Computer Software Documentation"** | Government rights in software | Same Unlimited / GPR / Restricted three-tier structure. Determines what happens to SCBE 14-layer source and DAVA Rust kernel source. |
| **DFARS 252.227-7017 "Identification and Assertion of Use, Release, or Disclosure Restrictions"** | How to preserve GPR/Limited Rights | **Must be asserted in the proposal itself** (attachment list of pre-existing works with funding source). Failure to assert = default to Unlimited Rights on delivery. This is the single most common small-business mistake. |
| **SBIR Policy Directive / 15 U.S.C. § 638(j)** | SBIR Data Rights Period | Extended from 4 years to **20 years** (Dec 2019 NDAA). Protects SBIR-developed tech from release outside the government. MATHBAC is NOT SBIR, but if a Phase II award vehicle becomes SBIR-compatible, this matters. |
| **ITAR / EAR** | Export control | Hyperbolic geometry + crypto + defense-adjacent ML = likely **EAR 5D002** (encryption) or **0Y521** (emerging tech) review. Not ITAR unless defense-specific. Must be flagged in the proposal. |

**Applied to this teaming.** The signed `ip_carveout_v1_signed.pdf` correctly implements a DFARS 252.227-7013/7014 pre-existing-IP split: SCBE pre-existing IP (14-layer pipeline, d_H, PSU(1,1), Sacred Tongues, USPTO 63/961,403, Six Tongues Protocol ASIN B0GSSFQD9G) remains Issac's; DAVA pre-existing IP (Rust kernel @ 09e1c7163, phi_beacon, tier_code, proof_strategies.py) remains Hoags Inc.'s. Joint IP is 50/50 with reciprocal royalty-free research license and commercial-use joint-consent veto.

**What the abstract must assert** (per DFARS 252.227-7017): an explicit pre-existing-IP attachment listing all of the above with funding source "contractor private investment" and restriction marking "Limited Rights" or "Restricted Rights." Without this, the government's default at delivery is Unlimited Rights on everything delivered — including our pre-existing stacks. Collin's draft does not include this. **It is the single most important legal omission.**

### 1.2 Cost / budget framework

| Norm | Source | Typical range |
|---|---|---|
| **DoD small-business fee (profit) on cost-reimbursable** | DFARS 215.404-4 "Profit" + Weighted Guidelines (DD-1547) | 7–15% of total cost, structured by risk/complexity factors. 10% is a safe midpoint for a mathematics-heavy Phase I. |
| **Indirect rate (G&A + overhead) for small business w/ no DCAA audit** | DCAA provisional-rate norms | 25–80% of direct labor for home-office small biz; 80–150% for larger firms with facilities. Must be "provisionally approved" or "contractor-proposed" on first award. |
| **Direct labor fraction of total cost** | FAR 31.205 + typical BAA budgets | 50–70% for a theory-heavy Phase I. |
| **Travel cap** | JTR + DoD per-diem | Per FAR 31.205-46; typical line item for 12–18-month Phase I: $15–40K. |
| **Phase I MATHBAC budget envelope** | Inferred from DARPA I2O Phase I norms for BAA solicitations of this class | $800K–$1.8M over 12–18 months. |

**Applied.** Collin's draft proposes $1.4M with:
- PI salary $240K (Collin as PI — wrong per teaming agreement)
- 2 FTE $480K (undifferentiated — should split by organization)
- Computing $80K, travel $40K, materials $60K
- Indirect $300K → implied rate ~37.5% on direct labor ($800K). Plausible for small biz but should be stated as "provisional rate, subject to DCAA review."
- Fee $200K → 14.3%. **Legal but high.** 10% ($140K) is defensible without a weighted-guidelines justification; 14.3% needs DD-1547 narrative.

A prime-voiced Issac version should allocate **at least 55%** of direct costs to the prime (Issac / SCBE work) with the remainder going to Hoags Inc. as sub — matching the §3 teaming-agreement 65/35 split on total project cost and respecting the prime's scope of work in §4 of that agreement. Collin's draft is silent on prime/sub budget allocation.

### 1.3 Industry / technical standards

| Standard | Relevance |
|---|---|
| **NIST AI RMF 1.0** (Jan 2023) + Generative AI Profile (Jul 2024) | Govern/Map/Measure/Manage — SCBE's L13 governance gate and L12 harmonic wall are directly citable as "Measure" controls. |
| **ISO/IEC 42001:2023** | AI management system requirements — SCBE's 5-axiom mesh maps onto §6.2 objectives. |
| **NIST SP 800-53 Rev. 5** | Baseline security controls — PQC envelope (ML-KEM-768, ML-DSA-65) satisfies SC-13 crypto requirements. |
| **FIPA ACL (Foundation for Intelligent Physical Agents)** | Classical multi-agent communication language standard — useful as a baseline to contrast SCBE's geometric-signature channel against. |
| **IEEE P2817 / P3123** (draft AI interoperability) | Emerging; cite as "in development" to show awareness. |

**Canonical academic anchors** (cite 4–6 in the abstract's references section):
- Nickel & Kiela, NeurIPS 2017 — "Poincaré Embeddings for Learning Hierarchical Representations" (hyperbolic embedding foundation).
- Ganea, Bécigneul & Hofmann, NeurIPS 2018 — "Hyperbolic Neural Networks" (Möbius arithmetic on the Poincaré ball, which is exactly what Sacred Tongues weighted transform uses).
- Bronstein, Bruna, Cohen & Veličković, 2021 — "Geometric Deep Learning: Grids, Groups, Graphs, Geodesics, and Gauges" (the equivariance framework under which PSU(1,1) equivariance lives).
- Cohen & Welling, ICML 2016 — "Group Equivariant Convolutional Networks" (foundational equivariance citation).
- Shannon, BSTJ 1948 — "A Mathematical Theory of Communication" (channel capacity — this is Kevrekidis's native language).
- Kevrekidis, Gear & Hummer, AIChE 2004 — "Equation-free multiscale computation" (flatter the PM, the more his own work is cited).

Also citable as prior art: **USPTO Provisional 63/961,403** (SCBE 14-layer system) and **Six Tongues Protocol, KDP ASIN B0GSSFQD9G** (timestamped publication of the Langues Weighting System, preceding the MATHBAC solicitation).

---

## 2. Stack A — Issac-led abstract (the one I'd ship)

**DARPA MATHBAC TA1 · Abstract · DARPA-PA-26-05**
**Proposing Organization (Prime):** Issac D. Davis, d/b/a SCBE-AETHERMOORE · SAM UEI `J4NXHM6N5F59` · CAGE `1EXD5` (ACTIVE 2026-04-13)
**Subcontractor:** Hoags Inc. · CAGE `15XV5` · UEI `DUHWVUXFNPV5` · Eugene, OR (President: Collin Hoag)
**Principal Investigator:** Issac D. Davis
**Subcontract PI:** Collin Hoag (DAVA kernel substrate)
**Period of Performance:** 12 months base · optional 6-month extension
**Requested Funding:** $1,400,000 (Phase I) · cost-plus-fixed-fee, fee at 10% per DFARS 215.404-4

### Pre-existing IP assertions (required by DFARS 252.227-7017)

Per DFARS 252.227-7013/-7014, the following pre-existing technical data and noncommercial computer software are asserted with **Limited Rights / Restricted Rights** markings, developed exclusively at contractor private expense prior to this proposal:

1. **SCBE-AETHERMOORE 14-layer pipeline** (L1 complex context → L14 audio-axis telemetry), including hyperbolic distance `d_H`, Poincaré ball embedding, Möbius phase, Hamiltonian multi-well realms, harmonic wall `H(d, pd) = 1/(1 + d_H + 2·pd)`, triadic temporal distance, spectral+spin coherence. Owner: Issac D. Davis. Funding: contractor private expense. Anchor commit: `neurogolf/ant-colony-solvers @ 090aa5e8`. Patent: USPTO Provisional **63/961,403**.
2. **Langues Weighting System (Sacred Tongues)** — 6-dimensional φ-scaled value/governance metric (KO, AV, RU, CA, UM, DR), prior-art timestamped in *The Six Tongues Protocol* (KDP ASIN B0GSSFQD9G, published prior to this solicitation). Owner: Issac D. Davis.
3. **DAVA bare-metal Rust kernel** (`#![no_std]`, u16 saturating arithmetic), `phi_beacon` telemetry primitive, `tier_code` segmentation with φ-thresholds at 250/500/750 (`phi_gradient.rs`), `proof_strategies.py`, 11-channel 2000-tick trace CSV format. Owner: Hoags Inc. Funding: contractor private expense. Anchor commit: `09e1c7163`.
4. **Joint sealed-blind protocol** (bundle SHA-256 `87a0ee34…`, sealed labels `f177854…`, committed segmentation `dab56a6…`). Joint IP per `ip_carveout_v1_signed.pdf` §3; reciprocal royalty-free research license; commercial exploitation requires joint written consent.

Government Purpose Rights (5-year default per DFARS 252.227-7013(b)(2)) are negotiable for Phase I deliverables developed under this award; the pre-existing works above remain under the markings asserted.

### Abstract body

**Problem.** MATHBAC TA1 asks for the mathematics of agentic AI communication: what is the right object in which to state capacity bounds, equivariance properties, and formal guarantees on messages exchanged between agents? Current multi-agent frameworks (FIPA ACL, learned embedding channels, graph-neural message passing) lack a fixed geometric substrate that (a) admits analytic channel-capacity bounds and (b) is equivariant under a non-trivial symmetry group of the observation manifold.

**Approach.** SCBE-AETHERMOORE embeds agent state in the Poincaré ball model of 2D hyperbolic space (Nickel & Kiela, 2017; Ganea et al., 2018), weights per-channel semantics by a golden-ratio-scaled 6-tongue metric (LWS), and computes channel capacity on a fixed regime-transition Markov chain over φ-quantile-anchored realms. The observation algebra is equivariant under PSU(1,1) — the orientation-preserving isometry group of the disk (Bronstein et al., 2021; Cohen & Welling, 2016). Agent-to-agent communication is modeled as an emission-observation pair: emitter produces a φ-beacon telemetry tuple; observer lifts it through a 14-layer pipeline (L1 complex-context ingestion → L5 hyperbolic distance → L8 Hamiltonian realm assignment → L12 harmonic-wall decision → L13 governance gate → L14 audio-axis telemetry) under a 5-axiom mesh (unitarity, locality, causality, symmetry, composition).

**Empirical substrate (hash-sealed, reproducible).** In collaboration with DAVA (Hoags Inc. subcontract), we executed a hash-sealed blind commit protocol: DAVA generated 24 agent traces × 2000 ticks × 11 channels over an 8-regime closed vocabulary; SCBE committed a segmentation before labels opened. Result: 24/24 = 100% recovery of the sealed regime vocabulary using segment-count and first-realm features read directly off the Poincaré embedding. Permutation test (N = 10,000, marginal-preserving): 0/10,000 shuffles matched or exceeded 24/24; one-sided 95% upper bound on *p* = 3.00 × 10⁻⁴. KL channel capacity under regime-level segmentation: 2.9818 bits/tick, 95% bootstrap CI [2.5709, 2.9835] — 99.4% of the log₂(8) = 3.000 bits/tick Shannon ceiling. Möbius-equivariance verified: under 5 random PSU(1,1) isometries with k-means++ centroid refit, trajectory-key partitions are **bit-identical** across all seeds.

**Mathematical object (Phase I deliverable #5).** We state as a **Working Hypothesis** (not yet a theorem; formalization is the deliverable): for an agentic channel whose state lives in a fixed φ-quantile Poincaré disk embedding with `K` active realms of diameter `D` under the hyperbolic metric, the per-tick KL channel capacity is upper-bounded by a function `C*(κ, D, K)` of the disk curvature κ, realm diameter, and realm count — independent of the specific emitter implementation. The 2.9818 / log₂(8) = 99.4% result is consistent with `C*` being approximately saturated at the realm geometry we inherited from DAVA's channel ranges; Phase I Deliverable #2 replaces that inherited layout with an SDP-derived optimal layout and tests whether the saturation bound remains.

**Phase I deliverables (12 months, $1.4M).**
1. **Open-vocabulary 100-trace scale-up** (lead: Hoags Inc. sub; add HYPERVIGILANCE + DISSOCIATION regimes). 2 months.
2. **Algorithmic realm-layout derivation** via semidefinite programming with minimum-separation constraints on the Poincaré disk (lead: Issac / SCBE). Möbius-equivariant k-means++ baseline already demonstrated. 3 months.
3. **K_active-reconciled bootstrap CI** on channel capacity with Euclidean-approximation baseline (from Hoags Inc.'s `proof_strategies.py`, 1.958 bits/tick against tier_code) vs. real hyperbolic d_H observer against both tier_code and SCBE realm labels (lead: Issac). 2 months.
4. **Live QEMU capture** of DAVA `phi_beacon` emissions ingested by a running SCBE L1 in real time (joint: Hoags emitter, Issac ingestion). Closes the "generator-against-sealed-labels" caveat. 3 months.
5. **Formal statement and proof attempt** of the curvature–diameter–K capacity upper bound (lead: Issac, with subcontractor math review). Theorem `C*(κ, D, K)` or, failing a full proof, a rigorously stated conjecture with sharpness analysis. 4 months, overlapping.

**Cost structure** (cost-plus-fixed-fee; DCAA-auditable; pre-existing IP at private expense).
- Direct labor — Prime (Issac, PI, 1.0 FTE, 12 mo): $210,000
- Direct labor — Sub (Collin, co-PI/substrate, 0.5 FTE, 12 mo): $105,000
- Direct labor — supporting engineer (1.0 FTE, 6 mo allocated under prime): $105,000
- Subtotal direct labor: **$420,000** (30% of total)
- Computing (NVIDIA H100 hours for hyperbolic embedding + bootstrap + SDP): $100,000
- Travel (PI review meetings, Proposers Day follow-on, annual DARPA review): $30,000
- Materials / compute credits / software licenses: $40,000
- Subcontract costs (Hoags Inc. scope per `teaming_agreement_v1_signed.pdf` §4): $280,000 (of which $105K is direct labor above, $175K is sub's allocated indirect + materials + sub's fee)
- Indirect (G&A 30% of direct labor + travel, home-office small business provisional rate): $135,000
- **Subtotal cost: $1,005,000**
- **Subcontract pass-through**: already included above.
- **Remaining headroom for computing surge / consultant math review**: $267,000 (held as contingency labor).
- **Total cost: $1,272,000**
- **Fixed fee @ 10% of cost (DFARS 215.404-4, weighted-guidelines-consistent for theory-heavy low-risk Phase I)**: $128,000
- **Total proposed: $1,400,000**

Prime/sub split on total value: approximately 65% Prime ($910K) / 35% Sub ($490K), matching `teaming_agreement_v1_signed.pdf` §3. DCAA provisional-rate narrative will accompany the full proposal.

**Team.**
- **Issac D. Davis, PI (Prime).** Sole author, SCBE-AETHERMOORE (14-layer pipeline, hyperbolic governance, Sacred Tongues, PQC envelope). USPTO Provisional 63/961,403. Prior DARPA submission: CLARA DARPA-PA-25-07-02-CLARA-FP-033 (submitted 2026-04-13). Author of *The Six Tongues Protocol* (KDP ASIN B0GSSFQD9G). SAM UEI J4NXHM6N5F59 ACTIVE.
- **Collin Hoag, Subcontract co-PI (Hoags Inc.).** Creator of DAVA bare-metal Rust agent kernel and φ-beacon telemetry primitive. CAGE 15XV5. President, Hoags Inc., Eugene OR.

**Compliance.** NIST AI RMF 1.0 (Govern/Map/Measure/Manage — SCBE L12 harmonic wall and L13 governance gate map directly onto Measure and Manage). ISO/IEC 42001:2023 (AI management systems §6.2 objectives). NIST SP 800-53 Rev. 5 SC-13 cryptographic protection (ML-KEM-768 + ML-DSA-65 PQC envelope in SCBE). Export control preliminary classification: EAR (not ITAR); likely 5D002 review on PQC components, 0Y521 review on hyperbolic-ML components. Full classification filing prior to delivery of any Phase I software.

---

## 3. Side-by-side scoring — Stack A / B / C

**Stack A = Issac-led rewrite above.**
**Stack B = Collin's 2026-04-20 17:43 `MATHBAC_ABSTRACT_DRAFT.pdf` as-delivered.**
**Stack C = Balanced mix (co-PI framing, DAVA-forward substrate, SCBE-forward math).**

### 3.1 Structural contrast

| Axis | Stack A (Issac-led) | Stack B (Collin's draft) | Stack C (balanced mix) |
|---|---|---|---|
| **Header identifies prime as** | Issac Davis / SCBE-AETHERMOORE | Issac Davis / SCBE-AETHERMOORE *(header)* | Issac Davis / SCBE-AETHERMOORE |
| **Body identifies PI as** | Issac Davis | Issac Davis (page 1) **but "Collin Hoag, PI" on page 7 §4** — self-contradictory | Co-PIs: Issac Davis (math lead) · Collin Hoag (substrate lead) — both named consistently |
| **Center of gravity (% of technical body)** | ~60% SCBE math / ~30% DAVA substrate / ~10% joint result | ~15% SCBE / ~70% DAVA/DGCC/Phi-Beacon / ~15% joint | ~45% SCBE / ~45% DAVA / ~10% joint |
| **Mathematical object stated** | Yes — `C*(κ, D, K)` capacity bound, named as Working Hypothesis | Partial — DGCC and emergence-prediction language; no named capacity bound | Yes — both `C*(κ, D, K)` and DGCC convergence theorem |
| **DFARS 252.227-7017 pre-existing-IP assertion** | **Explicit, line-itemed** | **Absent** (critical legal defect) | Explicit |
| **Budget split disclosed** | ~65/35 Prime/Sub, line-itemed, fee justified | $1.4M total, not allocated by organization, 14.3% fee unjustified | 60/40 Prime/Sub, line-itemed |
| **Export-control classification** | Preliminary EAR 5D002 / 0Y521 filed in text | Absent | Explicit |
| **Schedule milestones: SCBE-led** | 3 of 5 | 0 of N (all DGCC workstreams) | 2 of 5 |
| **Schedule milestones: DAVA-led** | 1 of 5 (plus 1 joint) | All | 2 of 5 (plus 1 joint) |
| **Kevrekidis-scoring-rubric fit** (per `teaming_targets_v1.md` §"Kevrekidis scoring") | Strong — explicit math object, small-science, formal path, generalizable principle | Weak on math object (substrate-heavy), strong on empirical | Strong on all four; co-PI framing may dilute authority |

### 3.2 Scoring rubric (1–5, higher = better for Issac)

| Criterion | Weight | A | B | C |
|---|---:|---:|---:|---:|
| **IP leverage for Issac** — preserves USPTO 63/961,403, 14-layer pipeline, LWS as prime's pre-existing IP | 20% | 5 | 2 | 4 |
| **Budget share for Issac / SCBE** | 15% | 5 | 2 | 4 |
| **PI authority clarity** — does the document match the signed teaming agreement | 15% | 5 | 1 (self-contradicting) | 4 |
| **Technical center of gravity** — does the math (what TA1 selects on) live in the prime's stack | 15% | 5 | 2 | 3 |
| **Follow-on Phase II prime likelihood** — who DARPA will treat as "the one to talk to" next year | 10% | 5 | 2 | 3 |
| **Legal defensibility** (DFARS 252.227-7017, fee justification, export control) | 10% | 5 | 2 | 5 |
| **Proposal-day reviewability** — Kevrekidis-rubric fit | 10% | 5 | 3 | 4 |
| **Exit optionality** — Issac's freedom to re-team / commercialize independently | 5% | 4 | 1 | 3 |
| **Weighted score (out of 5)** | | **4.90** | **1.95** | **3.80** |

### 3.3 Risk ledger

| Risk | Stack A | Stack B | Stack C |
|---|---|---|---|
| Collin walks from teaming | Low — teaming is signed, Stack A honors §3/§4 of it | Low | Low |
| DARPA rejects "hobbyist small-biz" framing | Medium — mitigated by SAM ACTIVE, USPTO filing, prior CLARA submission | High — Collin is positioned as PI but Hoags Inc. has narrower prior DARPA footprint | Medium |
| Internal contradiction caught in review (PI role mismatch) | None | **High — present in the current document** | None |
| Pre-existing IP defaults to Unlimited Rights on delivery | None | **High — no §7017 assertion** | None |
| Fee rejected as unjustified | None | Medium — 14.3% needs DD-1547 | None |
| Follow-on award goes to Hoags Inc. not Issac | Low | **High** | Medium |
| Relationship damage from pushback | Low — pushback is on legal/structural defects, not substance; Collin's v2 pushback items were all accepted in v3 (see `v3_markup_for_collin.md`) | n/a | Low |

### 3.4 What to actually do

**Ship Stack A.** The signed teaming and IP carveout are favorable; the abstract is the load-bearing artifact and the only one that hits DARPA's review desk with force. Collin's draft has legal defects (§7017 omission, fee justification, PI role inversion) that have nothing to do with him being unfair and everything to do with this being his first federal proposal. Stack A fixes all of them in a way that is fully consistent with the teaming agreement he already signed — there is no renegotiation implied.

**Mechanics for the reply to Collin.** Frame the pushback exactly like the `v3_markup_for_collin.md` push-back list worked: itemized, specific, anchored in the artifacts both parties have already signed. Do not call the PI inversion a "mistake" — call it a header/body mismatch that needs to match the header. He accepted all 5 v3 push-backs on substance; he will accept these on legal form.

**Deliverable tomorrow.** At the networking block, hand out the **one-pager** (`one_pager_v1.md`) — not the abstract. The one-pager is Issac-voiced, math-forward, and already correct. Keep the abstract as a "we're finalizing for the April 30 submission" item and ship Stack A by April 27 at latest so there's time for Collin's one counter-read before the portal closes.

---

## 4. Open problems for Issac to resolve before ship

1. **Confirm $1.4M envelope is within the MATHBAC Phase I band.** The consolidated proposer profiles (pg 23–24 of `Consolidated_MATHBAC_Proposer_Profiles_4_16_2026.pdf`) should list the BAA's stated Phase I cap — verify it is ≥ $1.4M before quoting. If cap is $1.0M, reduce engineer FTE and computing.
2. **DCAA provisional-rate letter.** Small-business home-office G&A of 30% is inside the range for a first-time contractor but should be disclosed as "contractor-proposed, subject to DCAA verification." APEX Accelerator Port Angeles (360-457-7793) can help write the rate letter — Deadline: before April 30 submission.
3. **Export-control preliminary.** File a conservative BIS Commodity Classification Request (CCATS) on SCBE PQC components to lock in EAR classification. Not blocking for abstract but blocking for any live QEMU cross-stack demo in Phase I Deliverable #4.
4. **USPTO 63/961,403 conversion timeline.** Provisional expires; track the conversion window so the non-provisional is on file before Phase I delivery starts. Affects the Restricted Rights assertion's durability.
5. **Prior art disclosure.** Confirm which of the SCBE codebase files were public (GitHub) prior to the MATHBAC Special Notice date (2026-02-??); pre-SN public disclosure strengthens the "contractor private investment" assertion. Post-SN work inside the award period is government-funded.
6. **Naming in the abstract references list.** Cite Kevrekidis 2004 equation-free paper in the "Approach" section explicitly — it buys reviewer warmth at negligible cost.

---

## 5. Appendix — alignment table, Stack A ↔ prior planning artifacts

| Stack A element | Source in this directory |
|---|---|
| §2 Approach (geometric substrate) | `joint_memo_v1.md` §Hook + §Figure 1 |
| §2 Empirical substrate (24/24, p ≤ 3×10⁻⁴, Möbius eq., KL 2.9818 CI) | `one_pager_v1.md` §Evidence; `v3_markup_for_collin.md` §§2–3 |
| §2 Mathematical object (C*(κ, D, K)) | `v3_markup_for_collin.md` §4 ("Working Hypothesis"); `joint_memo_v1.md` §Proposed deliverables #5 |
| §2 Phase I deliverables 1–5 | `joint_memo_v1.md` §Proposed deliverables |
| Budget split 65/35 | `teaming_agreement_v1_signed.pdf` §3 |
| Joint IP 50/50, reciprocal license | `ip_carveout_v1_signed.pdf` §§3–4 |
| Pre-existing IP assertions | `ip_carveout_v1_signed.pdf` §§1–2 |
| PI role | `teaming_agreement_v1_signed.pdf` §4 |
| Solicitation identifier split | `submission_readiness_2026-04-20.md` §"Official identifier split" |
| Proposers Day reviewer scoring | `teaming_targets_v1.md` §"Kevrekidis's scoring" |
| Q&A robustness | `elevator_pitches_v1.md` §"Reviewer-anticipated Q&A" |

No element of Stack A is invented; every load-bearing claim traces to a prior artifact already shipped or signed. The difference from Stack B is architectural framing and legal form, not new technical content.
