# DARPA-PA-26-05 (MATHBAC) — Compliance Checklist

Source: `artifacts/mathbac/sam_pa_26_05_attachments/DARPA-PA-26-05.{pdf,txt}` (1057 lines, posted 2026-04-07).
Generated: 2026-04-29 (autonomous-loop pivot per `project_constrained_decoding_result.md`).

**Status legend**
- HAVE — already covered by existing SCBE artifact / submission
- NEED — not yet drafted; required before 2026-06-16 full proposal upload
- BLOCKED — requires user auth (BAAT account, advisor outreach, DARPA Q&A submission)
- N/A — does not apply to TA1-only submission (we are TA1)

Track corresponds to: **TA1 — The Mathematics of Agentic Communication Protocols (LOCKED).**

---

## Section 0 — Dates & Hard Deadlines (lines 17–24)

| Clause | Date | Status |
|---|---|---|
| Posting | 2026-04-07 | HAVE (received) |
| Proposers Day | 2026-04-21 | HAVE (attended; see `proposers_day_playbook.md`) |
| Abstract due | 2026-04-30 16:00 ET | HAVE (SUBMITTED 2026-04-27 05:02 ET — `project_mathbac_abstract_v1`) |
| Question submittal close | 2026-06-04 16:00 ET | NEED (FAQ questions list — item #12 BLOCKED on user) |
| **Full proposal due** | **2026-06-16 16:00 ET** | **NEED** (full Vol I + II + attachments) |
| Anticipated PoP start | 2026-09-15 | informational |

---

## Section I — Funding Opportunity Description (lines 42–254)

### 1.0 Domain framing (lines 42–78)

| # | Clause | Required action | Status |
|---|---|---|---|
| 1.1 | Proposal must "promote revolutionary advances" — *incremental* improvements **excluded** (line 47–49) | Frame SCBE as new mathematical framework, not iteration on transformers | NEED in Vol I §1 |
| 1.2 | Phase I scope is fixed pre-trained agents, no fine-tuning (lines 187–191) | TA1 SOW must explicitly say agents held static | NEED in Vol I §2 |
| 1.3 | Communication substrates limited to natural language + floating-point numbers (lines 242–243) | Must NOT propose new domain language in Phase I | NEED — confirm SCBE's tongue layer is *analytical*, not new substrate |

### 2.0 Program Description and Scope (lines 255–354)

| # | Clause | Required action | Status |
|---|---|---|---|
| 2.1 | Proposals **must address TA1 OR TA2** in Phase I; not both in single proposal (lines 282–287) | One proposal, TA1 only | HAVE (decided TA1) |
| 2.2 | **Must briefly describe Phase II SOW** showing how TA1+TA2 capabilities orchestrate (lines 282–286) | Vol I §3 — Phase II draft SOW, TA1+TA2 integration | NEED |
| 2.3 | Non-conforming proposals (no Phase II description) **removed from consideration** (line 285–286) | hard requirement | NEED — gate before submit |
| 2.4 | TA1/TA2 proposers must identify selected science subdomain(s) (line 299) | pick subdomain | HAVE for draft — NMR spectroscopy selected by Decision Box A silence rule; see `vol_i_section_4_technical_approach_skeleton.md` |
| 2.5 | Must identify two families of scientific tasks in chosen subdomain (line 300) | name 2 task families | HAVE for draft — 1H NMR structure prediction + mixture-spectrum deconvolution; final datasets still NEED |
| 2.6 | TA2 only: identify ≥1 well-established principle/law/correlation to rediscover, with corpus that does NOT contain it (lines 304–308) | N/A | N/A |
| 2.7 | **Must specify baseline performance with current methods** (line 308–310) | numbers from SCBE on chosen subdomain | NEED — requires §2.4 first |
| 2.8 | Must identify additional metrics; for each provide 6 fields (lines 308–319): description, calculation method, how it measures progress, how it supplements current metrics, why adopt, literature sources | this is the 8-field metric spec from punch list item #6 | **HAVE v1 draft** — `proposer_added_metrics_v1.md` (4 metrics: MEE, ACV, CDPTI, PIS; 6 PA fields each + 2 header fields; awaiting fold into Attachment X) |
| 2.9 | Must identify other scientific subdomains where approach generalizes (lines 320–321) | generalization paragraph in Vol I | NEED |
| 2.10 | TA1 Phase I baseline = SOA model (e.g., Mixture of Experts) (line 322) | name comparison model | HAVE for draft — Mixtral-8x7B selected by Decision Box C; baseline numbers still NEED |
| 2.11 | Phase I performers expected to "Evolution Team" for Phase II (lines 332–336) | one performer cannot be in >1 Evolution Team | informational; affects Collin teaming |
| 2.12 | **Phase I proposed price ≤ $2,000,000** (line 344) | hard cap | NEED — Vol II Cost workbook |
| 2.13 | Provide Phase II ROM cost (line 343) | Vol I §3 + Cost workbook tab | NEED |

### 3.0 Phase II preview (lines 358–399) — must justify Phase I supports Phase II

| # | Clause | Required action | Status |
|---|---|---|---|
| 3.1 | Proposers **must identify rewards** they anticipate leveraging in Phase II and why (line 376–377) | Vol I §3.2 — reward design rationale | NEED |
| 3.2 | Proposals **must describe** for Phase II: (a) methods to identify evolutionary pressures, (b) create directed-evolution mechanisms, (c) measure agent knowledge/latent space, (d) evolve agent language; (2) baseline experiments; (3) oracle implementation; (4) how TA1+TA2 extend; (5) how approach achieves Phase II Table 1 outcomes (lines 383–392) | Vol I §3 — full Phase II description | NEED |
| 3.3 | **Must include grounded example** in chosen subdomain showing Phase II expected capabilities (lines 391–393) | Vol I §3 — worked example | NEED — depends on §2.4 |

---

## Section I.3 — Program Structure (lines 401–800) — TA1 specifics

### 3.1 TA1 mandatory description elements (lines 421–462)

Every numbered item below is a *must-state* in Vol I.

| # | Clause | Status |
|---|---|---|
| TA1-(1)(a) | Methods to evaluate and schedule interactions between heterogeneous agents | NEED |
| TA1-(1)(b) | Methods to enable more efficient agent interactions: (b1) without latent-space access, (b2) with access, (b3) mixed-access | NEED — phi-weighted Sacred Tongue metric maps here |
| TA1-(1)(c) | Methods to characterize/quantify communication-dynamics progress through campaign | NEED |
| TA1-(1)(d) | Methods to optimize communication protocols | NEED |
| TA1-(2) | Experiments + handcrafted baseline protocol(s) for comparison | NEED |
| TA1-(3) | Which "small science" foundation models will be used (must have accessible latent spaces); how latent spaces accessed and used | HAVE for draft — ChemBERTa-77M primary SSM + Qwen2.5-Coder-0.5B-Instruct orchestrator; latent-access details still NEED |
| TA1-(4) | Method for capturing/processing agentic-communication-stream + latent-space data; how shared with IV&V | NEED — telemetry pipeline spec |
| TA1-(5) | How approach achieves/exceeds TA1 metrics (Table 1) | NEED |
| TA1-doc-example | Clearly documented example in chosen subdomain showing expected capabilities | NEED |
| TA1-task-families | Two families of scientific tasks in chosen subdomain | NEED |
| TA1-generalization | Other subdomains where approach generalizes (rationale) | NEED |

### 3.2 TA1 mathematical-challenges to address (lines 463–486)

Vol I must state how each is addressed:

| # | Challenge | SCBE primitive that maps | Status |
|---|---|---|---|
| TA1-MC-1 | Agents as Operators/Systems (system-id, ROM, input-output) | 14-layer pipeline as composed operator; LWS as preconditioner | **HAVE v1 mapping** — `ta1_mathematical_challenges_v1.md` §MC-1 |
| TA1-MC-2 | Communication Protocols in Operator Networks (graph-theory, hierarchical spectral augmentation) | Hamiltonian CFI multi-well + Mobius phase | **HAVE v1 mapping** — `ta1_mathematical_challenges_v1.md` §MC-2 |
| TA1-MC-3 | Performance Prediction (discrete math models for combinations/permutations) | Phi-weighted convergence + harmonic wall H | **HAVE v1 mapping** — `ta1_mathematical_challenges_v1.md` §MC-3 |
| TA1-MC-4 | Protocol Optimization (discrete/continuous optimization with cost functions) | Risk-decision tier minimization + L13 governance | **HAVE v1 mapping** — `ta1_mathematical_challenges_v1.md` §MC-4 |
| TA1-MC-5 | Construction of an Oracle (semantic-communication confirmation) | Symphonic Cipher trust score | **HAVE v1 mapping** — `ta1_mathematical_challenges_v1.md` §MC-5 |

### 3.3 TA1 Deliverables (lines 488–498)

| Month | Deliverable | Status |
|---|---|---|
| 12 | Quantitative Mathematical Framework (theory) | NEED in milestones |
| 14 | Computational Design Tool (software suite) | NEED in milestones |
| 16 | Catalog of Protocol Design Principles + Domain-Specific Optimal Protocols | NEED in milestones |

### 3.4 TA1 Fixed Payable Milestones (lines 685–733) — verbatim required

Vol I + Attachment F (Cost Workbook "Schedule of Milestones and Payments" tab) **must** include at minimum:

| Month | Required milestone | Status |
|---|---|---|
| M1 | Kickoff: present chosen math/info/systems theory + rationale + foundation models + latent-space access plan + baseline protocol + initial TA1 rubric quantitative analysis on chosen tasks; all named personnel assigned | NEED — milestone schedule |
| M3 | Report initial successes/failures + initial mathematical-framework description; confirm all personnel at planned LoE | NEED |
| M6 | PI meeting: thorough framework description + Phase I metric progress + demonstrate capabilities w/ IV&V + capture/process agentic-comm + latent-space data + share w/ IV&V | NEED |
| M9 | Initial software-suite report (math framework in chosen subdomain) + IV&V challenge-problem progress + ROMs for selected agents predicting outputs at specified fidelity | NEED |
| M13 | PI meeting: thorough software-suite description + Phase I metric progress + IV&V challenge-problem progress + initial superior-protocols set; **side-by-side baseline comparison** in IV&V rubric, mathematically explained | NEED |
| M14 | Demonstrate computational-design-tool capabilities + test results w/ IV&V | NEED |
| M16 | Final report: math/info/systems theory developments + implementations + Phase II plans | NEED |

### 3.5 IV&V interface (lines 559–581, 615–628)

| # | Clause | Status |
|---|---|---|
| IVV-1 | IV&V designs bespoke challenge problems by M7 (informational) | informational |
| IVV-2 | "Living metric" — IV&V uses best/most-recent SOA platform at time of comparison (lines 562–564) | NEED — Vol I §5 must commit to living-metric methodology |
| IVV-3 | Performers **must explain why approach worked or didn't** (lines 626–628) | embed in every milestone deliverable |
| IVV-4 | IV&V rubric shared with performers by M4 (informational) | informational |
| IVV-5 | TA1 rubric: % success rate ↑, speedup, adaptability/generalizability (lines 572–590) | NEED — performance projections |

### 3.6 Phase I baselines (lines 617–625)

| Window | Baseline | Status |
|---|---|---|
| M0–M4 | TA1 uses own data, agentic platform, task families | NEED — Vol I §6 must list these |
| M5–M7 | TA1 must hit IV&V rubric on own data/platform/tasks | NEED — projection |
| M8–end | Compare to IV&V living metric (data, platform, tasks, rubric) on bespoke challenge | NEED — projection |

---

## Section I.4 — Meeting / Travel / Reporting (lines 800–831)

| # | Clause | Status |
|---|---|---|
| MTR-1 | Budget for **3 three-day meetings over 16 months**: 2× DC-area, 1× SF Bay-area | NEED — Vol II Cost: $X travel line |
| MTR-2 | Regular teleconferences w/ Govt for progress reporting | informational |
| MTR-3 | At least one PM site visit per phase | informational |
| MTR-4 | **Quarterly technical reports** within 10 days of quarter-end | NEED — listed as deliverable in TDD |
| MTR-5 | **Phase completion report** within 30 days of phase end | NEED — listed in TDD |
| MTR-6 | Other negotiated deliverables: registered reports, protocols, corpora, demos, prompts, publications, software libraries, small science models, code, APIs, docs/manuals | NEED — anticipate in TDD |
| MTR-7 | **Working system** capable of T&E evaluation in Phase I | NEED — Vol I commitment |
| MTR-8 | Brief DARPA on each evaluation; written summary within 2 weeks | informational |
| MTR-9 | **Identify (1) compute used in Phase I broken out by month, (2) resources at organization, (3) additional resources requested** (lines 821–824) | NEED — Vol II compute table |
| MTR-10 | **Encouraged**: noncommercial software/docs/data delivered with ≥ Government Purpose Rights (GPR) (lines 825–831) | NEED — IP statement (cross-ref `ip_carveout_v1.md`) |

---

## Section II — Evaluation Criteria (lines 834–866)

Listed in **descending order of importance**:

| # | Criterion | Vol I coverage required |
|---|---|---|
| EC-1 | **Overall Scientific and Technical Merit** — innovative, feasible, complete, detailed technical rationale, logically sequenced tasks, deliverables defined, risks + mitigations identified | Vol I §1 + §4 + §7 (risk register) — NEED |
| EC-2 | **Potential Contribution and Relevance to DARPA Mission** — bolster national security tech base, "pivotal early technology investments that create or prevent technological surprise" | Vol I §1 (mission alignment paragraph) — NEED |
| EC-3 | **Price** — proposed price represents practical understanding, efficient, sufficiently detailed; burden on proposer; unreasonable price → not selected | Vol II Cost workbook — NEED |
| EC-4 | **Proposer's Capabilities or Related Experience** — evidence team can realize the effort, specifically (1) agentic AI, (2) small science models, (3) the proposed math/info/systems/data-science theory | Vol I §6 (team) — NEED — leverages SCBE github + HF + commits |

---

## Section III — Submission Guidelines (lines 869–930)

### 3.1 Award instrument (lines 870–881)

| # | Clause | Status |
|---|---|---|
| SUB-1 | Award type: **OT for Research only** (10 U.S.C. §4021) (line 870) | informational |
| SUB-2 | **Must complete and submit Model Research OT (Attachment G)** — edit blue text, redline to negotiation position | NEED — Attachment G fill |
| SUB-3 | Must review Proposer Instructions: General Terms and Conditions (URL line 879) | NEED — reference review |
| SUB-4 | Must review Other Transaction Agreements (URL line 880–881) | NEED — reference review |

### 3.2 Abstract (lines 882–893)

| # | Clause | Status |
|---|---|---|
| SUB-5 | Abstract strongly encouraged but not required | informational |
| SUB-6 | DARPA attempts reply within 30 days | informational |
| SUB-7 | Abstract due 2026-04-30 16:00 ET | HAVE (SUBMITTED 2026-04-27) |
| SUB-8 | Use Attachment A (slide) + Attachment B (template) | HAVE — both submitted |

### 3.3 Full proposal mandatory attachments (lines 894–930)

**Attachments A through I + X constitute a full proposal submission** (line 895).

| Attachment | Required? | Status |
|---|---|---|
| A — Abstract Summary Slide Template | required *if* submitting abstract | HAVE |
| B — Abstract Instructions and Template | required *if* submitting abstract | HAVE |
| C — Proposal Summary Slide Template | **required** (full proposal) | NEED |
| D — Proposal Instructions and Volume I Template (Technical & Management) | **required** | NEED — biggest doc |
| E — Proposal Instructions and Volume II Template (Price) | **required** | NEED |
| F — Streamlined Cost Buildup Workbook (Excel) | **required** | NEED |
| G — Model Other Transaction for Research | **required** | NEED |
| H — Task Description Document (TDD) Template | **required** | NEED |
| I — Other Transaction Certification Template | **required** | NEED |
| X — Proposal Overview & Proposed Metrics | **required** | NEED — vehicle for the 4 proposer-added metrics |

### 3.4 Milestones requirement (lines 900–905)

| # | Clause | Status |
|---|---|---|
| SUB-9 | Fixed payable milestones — payments triggered by completed observable technical events | NEED — Cost workbook tab + TDD |
| SUB-10 | May suggest modifications to Schedule of Milestones and Payments (DARPA may not accept) | informational |

### 3.5 Reps & Certs (lines 906–910)

| # | Clause | Status |
|---|---|---|
| SUB-11 | **Must submit DARPA-specific reps and certs for Research OT awards (Attachment I)** to be eligible | NEED — fill Attachment I |

### 3.6 Q&A channel (lines 913–918)

| # | Clause | Status |
|---|---|---|
| SUB-12 | All questions emailed to MATHBAC@darpa.mil; emails to PM directly may be delayed | NEED — questions list (item #12 BLOCKED on user) |
| SUB-13 | DARPA will post FAQ document, updated until close | informational — monitor weekly |

---

## Section IV — Special Considerations (lines 933–1057)

| # | Clause | Status |
|---|---|---|
| SC-1 | All responsible sources may submit (US + non-US) (lines 937–946) | informational |
| SC-2 | HBCUs/SBs/SDBs/MIs encouraged but **no set-aside** | informational — SCBE = sole-prop minority-owned |
| SC-3 | Non-US participants must comply with NDAs, security regs, export controls (lines 944–946) | informational — applies if Collin/DAVA on team |
| SC-4 | All proposal submissions **anticipated to be unclassified** (line 947) | informational |
| SC-5 | **FFRDCs, UARCs, Government Entities (incl. Nat'l Labs) NOT eligible** (lines 949–951) | informational — PNNL Sequim cannot prime; can sub via partnership? Verify before approach |
| SC-6 | **OCI**: organization cannot simultaneously provide SETA/A&AS to DARPA AND be a performer (lines 952–959) | informational — confirm none of our team has DARPA SETA |
| SC-7 | Fundamental research framework — DoW policy publishes results (NSDD 189, lines 960–981) | NEED — Vol I §1.4 declare *fundamental* |
| SC-8 | **Government has sole discretion** to determine fundamental vs not (lines 998–1005) | informational |
| SC-9 | **FRRBS**: Fundamental Research Risk-Based Security Review — risk assessments of all proposed senior/key personnel (lines 982–992) | NEED — submit FRRBS forms after notification of negotiation |
| SC-10 | **Must complete Common Disclosure Forms, biosketch, current/pending support** (lines 993–997) | NEED — fill NSF common forms |
| SC-11 | Proposers should indicate fundamental vs not in proposal (lines 998–1005) | NEED — Vol I §1.4 |

---

## Section V — Phase I Mandatory Phase II Description Cross-Check

A proposal is **non-conforming** (rejected) if it lacks Phase II SOW description (per §2.3 above). Cross-check before submit:

- [ ] Vol I §3 contains *Phase II Statement of Work draft*
- [ ] Vol I §3 contains *how TA1 + TA2 capabilities orchestrate* (must address even though we are TA1-only)
- [ ] Vol I §3 contains *grounded subdomain example* showing Phase II expected capabilities
- [ ] Vol I §3 identifies *anticipated rewards* for Phase II self-evolution
- [ ] Cost workbook tab includes Phase II *ROM cost*

---

## Section VI — DECISIONS A-D (resolved for Vol I draft by 2026-05-06 silence rule)

### Decision Box A — Science subdomain (blocks §2.4 → cascade to §2.5/2.7/2.10/3.1/3.3/Vol I §6)
Candidates given SCBE corpus + tongue alignment:
- **Cheminformatics / reaction prediction** — has clear baselines (RXN, Reaxys), large public corpora (USPTO), aligns with Kevrekidis chemistry examples in PA
- **NMR spectroscopy / structure elucidation** — explicitly named in PA line 305 (Karplus equation), strong SOA gap
- **Materials discovery (perovskite/MoF subset)** — SparksMatter referenced in PA line 91; broader symbol corpus
- **Mathematical theorem-proving (Lean/Mathlib)** — cleanest "principle" rediscovery test, but PA emphasizes physical-science domains

Selected for Vol I draft: **NMR structure elucidation** — lowest cost-to-baseline, named in PA, bounded data, IV&V can construct tractable challenges, and SCBE's spectral coherence layer (L9–L10) maps directly.
Resolution basis: `decision_boxes_a_d_prep.md` silence rule after 2026-05-06.

### Decision Box B — Small Science Model selection (blocks TA1-(3))
Must have accessible latent spaces. Candidates:
- ChemBERTa-77M (HF, latent space accessible)
- Qwen2.5-Coder-0.5B-Instruct (already running locally; not science-tuned)
- MolT5 (translation between molecules and natural language)
- Mistral-Small instruction-tuned + chemistry SFT layer

Selected for Vol I draft: **ChemBERTa-77M as primary SSM + Qwen2.5-Coder-0.5B as orchestrator**. Both fit under HF Pro plan limits, both latent-space accessible.
Resolution basis: `decision_boxes_a_d_prep.md` silence rule after 2026-05-06.

### Decision Box C — TA1 baseline protocol model (blocks §2.10)
PA suggests "Mixture of Experts." Lightweight options that fit OT scope:
- Mixtral-8x7B (open MoE, latent-space accessible)
- DBRX-Instruct
- Switch-Transformer-base

Selected for Vol I draft: **Mixtral-8x7B** — open weights, well-published baseline, accessible via HF.
Resolution basis: `decision_boxes_a_d_prep.md` silence rule after 2026-05-06.

### Decision Box D — Two task families in chosen subdomain (blocks §2.5)
If subdomain = NMR:
- (i) 1H NMR → structure prediction
- (ii) Mixture-spectrum deconvolution
Selected for Vol I draft: **(i) 1H NMR to structure prediction + (ii) mixture-spectrum deconvolution**.
Resolution basis: `decision_boxes_a_d_prep.md` silence rule after 2026-05-06.

---

## Section VII — Punch-list cross-reference

This checklist closes punch-list item **#7** (`project_mathbac_proposal_spine_2026_04_21.md` line 76). Remaining punch-list items in dependency order:

| # | Item | Blocked by |
|---|---|---|
| #4 | SAM.gov amendment download (Attachments C/D/E/F/G/H/I/X latest) | user (manual SAM.gov download) |
| #5 | BAAT account setup | user (attended MFA) |
| #6 | 8-field metric specs for MEE/ACV/CDPTI/PIS | DONE — `proposer_added_metrics_v1.md` (2026-04-29) |
| #7 | This compliance checklist | DONE |
| #8 | Vol I Technical & Management draft | STARTED — Section 4 skeleton at `vol_i_section_4_technical_approach_skeleton.md`; full Vol I still NEED |
| #9 | Vol II Price (Cost workbook + travel + compute table) | Decision Boxes + Vol I scope |
| #10 | Advisor outreach (Kevrekidis, Bertsekas, Sakana, etc.) | user |
| #11 | TDD draft (Attachment H) | Vol I milestones + deliverables |
| #12 | FAQ question submission to MATHBAC@darpa.mil | user (deadline 2026-06-04) |
| #13 | Final BAAT upload | user (deadline 2026-06-16) |

---

## Section VIII — Bare-minimum-to-submit list (a.k.a. "what we need by 2026-06-16")

If everything else slips, these are the irreducible artifacts:

1. **Attachment C** — Proposal summary slide
2. **Attachment D** — Vol I (Technical & Management) — TA1, full
3. **Attachment E** — Vol II (Price)
4. **Attachment F** — Streamlined Cost Buildup workbook (with milestone-payment tab + Phase II ROM tab)
5. **Attachment G** — Model OT for Research, blue-text edited
6. **Attachment H** — TDD
7. **Attachment I** — Reps & Certs
8. **Attachment X** — Proposal Overview & Proposed Metrics (the 4 proposer-added metrics live here)
9. **Common Disclosure Forms** — biosketch + current/pending support (NSF format) for every senior/key personnel
10. **FRRBS materials** — risk-review forms for senior/key personnel (after notification of negotiation, but plan now)

All ten items must be uploaded via **BAAT** by 2026-06-16 16:00 ET.
