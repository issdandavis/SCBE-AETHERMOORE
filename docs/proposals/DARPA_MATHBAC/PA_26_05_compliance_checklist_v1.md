# DARPA-PA-26-05 (MATHBAC) — Compliance Checklist v1

**Source-of-truth:** `artifacts/mathbac/sam_pa_26_05_attachments/DARPA-PA-26-05.txt` (1057 lines)
**Hard deadline:** **2026-06-16 16:00:00 ET** via BAAT (Broad Agency Announcement Tool)
**Performance start (anticipated):** 2026-09-15
**Phase I cap:** $2,000,000 / award (16 mo)
**Phase II planned:** 18 mo, Evolution Teams (TA1+TA2 combined)
**Sole performer:** Issac D. Davis (UEI J4NXHM6N5F59, CAGE 1EXD5)
**TA selection (locked):** TA1 — Mathematics of Agentic Communication Protocols
**Award instrument:** Research Other Transaction (10 U.S.C. § 4021); NOT FAR/DFARS

Status legend: **DONE** / **DRAFT** / **OPEN** / **GATED-USER** (needs explicit user authorization) / **GATED-EXTERNAL** (needs Collin/DAVA or DARPA response).

---

## 0. Submission Mechanics (must / required)

| # | Requirement | Source | Status | Note |
|---|---|---|---|---|
| 0.1 | Submit via BAAT (Broad Agency Announcement Tool) | L894–899 | GATED-USER | Account creation pending (Punch-list item 5) |
| 0.2 | Must arrive no later than 2026-06-16 16:00 ET | L22, L894 | OPEN | 50 days remaining as of 2026-04-27 |
| 0.3 | Address questions ONLY to MATHBAC@darpa.mil; PM-direct emails may not be answered | L913–914 | OPEN | Standing rule |
| 0.4 | Review Proposer Instructions: General Terms and Conditions | L878–880 | OPEN | Linked from PA-26-05 §III |
| 0.5 | Single TA per proposal — TA1 OR TA2 | L282, L286–287, L405 | DONE | TA1 locked per spine doc |
| 0.6 | Both TAs require **separate proposals** | L286–287 | N/A | Sole performer = one proposal |
| 0.7 | Proposals must include Phase II description / draft SOW (non-conforming if absent) | L282–286, L405–407 | DRAFT-DONE | `phase_ii_bridge_narrative_v1.md` landed 2026-04-27; final close gated on 14.6 (Evolution Team posture) and 14.7 (price strategy) |

---

## 1. Required Attachments (full proposal)

All paths land in `docs/proposals/DARPA_MATHBAC/proposal_volume/` once drafted (directory not yet created).

| # | Attachment | Description | Source | Status |
|---|---|---|---|---|
| 1.1 | A | Abstract Summary Slide Template | L920 | DONE (submitted 2026-04-27 05:02 ET) |
| 1.2 | B | Abstract Instructions and Template | L921 | DONE (submitted 2026-04-27) |
| 1.3 | C | Proposal Summary Slide Template | L922 | OPEN |
| 1.4 | D | Volume I Template (Technical and Management) | L923–924 | OPEN |
| 1.5 | E | Volume II Template (Price) | L925 | OPEN |
| 1.6 | F | Streamlined Cost Buildup Workbook (Excel) — incl. Schedule of Milestones & Payments tab | L667, L904, L926 | OPEN |
| 1.7 | G | Model Other Transaction for Research — proposer must edit blue text / redline | L872–876, L927 | OPEN |
| 1.8 | H | Task Description Document (TDD) Template | L670, L928 | OPEN |
| 1.9 | I | Other Transaction Certification Template (Reps & Certs) | L906–910, L929 | OPEN |
| 1.10 | X | Proposal Overview & Proposed Metrics | L930 | DRAFT (proposer_metrics_specs_v1.md is the basis) |

**Solicitation precedence:** PA + attachments + websites = entire solicitation; PA wins on conflict (L934–936).

---

## 2. Eligibility (must / shall not)

| # | Rule | Source | Status |
|---|---|---|---|
| 2.1 | FFRDCs, UARCs, Government Entities, National Labs NOT eligible to propose | L949–951 | OK (sole prop, none apply) |
| 2.2 | OCI: org cannot simultaneously be SETA/A&AS to DARPA AND a performer | L952–959 | OK (sole prop, no SETA contracts) |
| 2.3 | OCI questions must be raised before time/effort spent — email PA-specific address | L955–959 | N/A |
| 2.4 | Non-U.S. orgs/individuals may participate subject to NDAs, security, export law | L943–946 | N/A (U.S. sole prop) |

---

## 3. TA1 Substantive Requirements (must state)

Drawn from PA §3 TA1 (L420–449 and forward).

| # | Requirement | Source | Status | Mapping |
|---|---|---|---|---|
| 3.1 | State methods to **(a)** evaluate and schedule interactions between heterogeneous agents | L433–435 | DRAFT | spine §A; harness Atomic Tongue observer |
| 3.2 | State methods to **(b)** understand/enable more efficient agent interactions — (b1) no latent access, (b2) transformer latent access, (b3) mixed | L436–440 | DRAFT | Living Metric handles all three; phi-toroidal cavity is latent-access-agnostic |
| 3.3 | State methods to **(c)** characterize/quantify progress of communication dynamics through the campaign | L443–444 | DRAFT | 8 proposer metrics (proposer_metrics_specs_v1.md) |
| 3.4 | State methods to **(d)** optimize communication protocols | L445 | DRAFT | 5 pressure classes |
| 3.5 | State experiments and baseline protocol(s) (handcrafted OK) used for comparison/improvement quantification | L446–447 | DRAFT | Mixture-of-Experts vs. SOA per L322 |
| 3.6 | Identify which "small science" foundation models will be used; latent spaces must be accessible | L448–449 | OPEN | Need decision: small-science model pick |
| 3.7 | Identify selected science subdomain(s) and two families of scientific tasks | L299–303 | OPEN | Decision required |
| 3.8 | Specify best performance achieved with current methods (baseline) | L308–309 | DRAFT | M0 fixture seal already pins L4/L5/L7/L12 |
| 3.9 | Identify potential additional metrics — 6-field schema each: definition, calc method, progress measurement, supplements existing, adoption argument, literature provenance | L309–319 | DONE | proposer_metrics_specs_v1.md §3 (8 metrics catalogued) |
| 3.10 | Identify other domain(s)/subdomain(s) approach can generalize to + rationale | L320–321 | OPEN | Spine doc has Carnot/Pasteur/Wright frames |
| 3.11 | Approach compared to SOA model in Phase I (e.g., Mixture of Experts) | L322 | DRAFT | TA1 ROM for Phase II + bridge narrative |
| 3.12 | Phase I = agents held static, not allowed to evolve | L412–413 | OK (architectural) |

---

## 4. Phase II Bridge (must describe in Phase I proposal)

| # | Requirement | Source | Status |
|---|---|---|---|
| 4.1 | Brief description of how Phase I capabilities orchestrate to Phase II | L282–284 | DRAFT-DONE | `phase_ii_bridge_narrative_v1.md` §1 (Darwin–Gödel–Safe orchestration) |
| 4.2 | Draft Phase II SOW + Rough Order of Magnitude (ROM) cost | L342–345 | DRAFT-DONE | `phase_ii_bridge_narrative_v1.md` §2 (P2.T1–P2.T6, ROM ~$2.00M); price line gated on 14.7 |
| 4.3 | Acknowledge Evolution Team structure: single performer OR team addressing both TA1+TA2; no performer in >1 team | L335–336 | DRAFT-DONE | `phase_ii_bridge_narrative_v1.md` §3 acknowledges; final declaration gated on 14.6 |
| 4.4 | One prime + subperformers (negotiated post-Phase I) | L346–348 | DRAFT-DONE | `phase_ii_bridge_narrative_v1.md` §4 (sole-prime default; sub negotiation reserved per L347–348) |
| 4.5 | Approaches in Phase II compared to (and expected to outperform) collective of domain experts w/ handcrafted protocols + SOA models | L337–338 | DRAFT-DONE | `phase_ii_bridge_narrative_v1.md` §5 (5-axis comparison + honest TA2-gap acknowledgement) |
| 4.6 | Phase II-only collaboration is **encouraged not required**; choice does not impact award decision | L339–341 | INFO (no action) |

---

## 5. Travel & Meetings (must include in schedule + budget)

| # | Requirement | Source | Status |
|---|---|---|---|
| 5.1 | 3 three-day meetings over 16 months: 2× Washington DC, 1× San Francisco CA | L803–804 | OPEN (cost workbook line items) |
| 5.2 | Regular teleconference meetings with Government team | L805–806 | OPEN (no cost line) |
| 5.3 | At least one PM site visit per phase to demonstrate progress | L806–808 | OPEN (acknowledge in SOW) |
| 5.4 | Phase I PI meeting toward end of Phase I (Phase II teaming facilitator) | L330–332 | INFO (no proposer action) |

---

## 6. Deliverables (minimum required)

| # | Deliverable | Source | Status |
|---|---|---|---|
| 6.1 | Comprehensive **quarterly technical reports** (within 10 days of quarter end), describing milestone progress per SOW | L810–811 | OPEN (in TDD) |
| 6.2 | **Phase completion report** within 30 days of phase end | L812–813 | OPEN (in TDD) |
| 6.3 | Negotiated deliverables: registered reports, protocols, corpora, demos, prompts, publications, software libraries, science models, code, APIs, docs, manuals | L814–817 | OPEN (TDD) |
| 6.4 | **Working system** capable of T&E evaluation in Phase I | L818 | OPEN (TDD; aligns with 14-layer pipeline + harness) |
| 6.5 | Brief DARPA on evaluation results + written summary within 2 weeks of each evaluation | L819–820 | OPEN (TDD) |
| 6.6 | Compute statement: (1) expected Phase I compute by month, (2) resources at proposer's organization, (3) additional resources requested (compute, time, models) | L821–824 | OPEN (Volume I) |
| 6.7 | Encouraged: noncommercial software, docs, technical data delivered with **Government Purpose Rights (GPR)** minimum | L825–828 | OPEN (Vol I IP section) |
| 6.8 | Required: identify any commercial software in approach + license rights description | L828–831 | OPEN (Vol I IP section; ip_carveout_v1.md is starting point) |

---

## 7. Milestones (Attachment F + TDD)

| # | Requirement | Source | Status |
|---|---|---|---|
| 7.1 | Fixed-payable milestones with observable technical events triggering payment | L900–905 | OPEN |
| 7.2 | Schedule of Milestones and Payments populated as tab in Attachment F | L903–904 | OPEN |
| 7.3 | TA1 specific milestones (mapped from PA): M12 Mathematical Framework, M14 Computational Design Tool, M16 Catalog of Protocol Design Principles | L686+ (TA1 deliverables block) | OPEN (must align with PA mandatory milestones at M1, M3, M6, M9, M13, M14, M16) |
| 7.4 | Phase I project kick-off meeting attendance (presentation describing selected approach) | L686, L751 | OPEN |
| 7.5 | Modifications/additions to Schedule of Milestones may be suggested but DARPA may reject | L901–903 | INFO |

---

## 8. Evaluation Criteria (descending order of importance)

Volume I narrative must explicitly support each criterion (L834–863).

| # | Criterion | Source | Status of supporting material |
|---|---|---|---|
| 8.1 | **Overall Scientific and Technical Merit** — innovative, feasible, achievable, complete; technical rationale; logical task sequencing; deliverables clearly defined; risks + mitigation | L838–844 | DRAFT (M0 fixture seal + 8 proposer metrics + Living Metric provide the merit substrate) |
| 8.2 | **Potential Contribution and Relevance to DARPA Mission** — bolster national security tech base; pivotal early tech investment; create/prevent technological surprise | L845–848 | DRAFT (Carnot/Pasteur/Wright frames + agentic governance ties) |
| 8.3 | **Price** — practical understanding; price reasonableness; sufficiently detailed; burden on proposer | L849–857 | OPEN (Volume II pending; Annex A basis sheet DONE 2026-04-27 at `annex_a_basis_sheet_v1.md`) |
| 8.4 | **Proposer's Capabilities or Related Experience** — evidence of (1) agentic AI, (2) small science models, (3) proposed math/info/systems/data science theory + algorithms; similar efforts described including other Govt sponsors | L858–863 | DRAFT (past-performance memo template pending) |

---

## 9. Fundamental Research / Publication / FRRBS

| # | Requirement | Source | Status |
|---|---|---|---|
| 9.1 | Indicate whether proposed scope is **fundamental research** per NSDD 189 (Volume I) | L998–1001 | OPEN — claim YES (publishable, basic+applied research) |
| 9.2 | Government has **sole discretion** to determine fundamental vs. non-fundamental and select award instrument | L1000–1002 | INFO |
| 9.3 | If non-fundamental selected: agree to publication restrictions OR work with DARPA to bring SOW back into fundamental scope | L976–981 | INFO |
| 9.4 | Award has potential publication restrictions language (Proposer Instructions: General T&Cs) for non-fundamental | L1002–1005 | INFO |
| 9.5 | Distinguish prime vs. sub fundamental status if mixed (sole prop = trivially uniform) | L1006–1012 | OK (no subs) |
| 9.6 | **FRRBS** — comply with risk assessments of all senior/key personnel; conducted separately from scientific review; adjudicated prior to award | L982–992 | OPEN — sole prop = single key person = single FRRBS profile |

---

## 10. Disclosures (NSF Common Forms — must complete)

All proposals must complete (L993–997):

| # | Form | Source | Status |
|---|---|---|---|
| 10.1 | Common Disclosure Form (NSPM-33 standard) | NSF link L995 | OPEN |
| 10.2 | Biosketch (NSF format) | NSF link L996–997 | OPEN |
| 10.3 | Current and Pending Support | NSF link L996–997 | OPEN |

---

## 11. OT Award Mechanics (Attachment G + I)

| # | Requirement | Source | Status |
|---|---|---|---|
| 11.1 | OT type **only** — no FAR/DFARS, no FAR/DFARS cost accounting standards | L870–871, L1050–1056 | OK |
| 11.2 | Complete and submit Model Research OT (Attachment G); edit blue text/redline to reflect proposer negotiation position | L871–876 | OPEN |
| 11.3 | Submit DARPA-specific reps & certs for Research OT awards (Attachment I) — required to be eligible for OT | L906–910 | OPEN |
| 11.4 | Non-fundamental award type may differ in terms; non-binding model only | L1052–1056 | INFO |

---

## 12. Abstract Phase (already discharged — reference only)

| # | Requirement | Source | Status |
|---|---|---|---|
| 12.1 | Abstracts strongly encouraged but not required; favorable response ≠ award | L882–891 | DONE (DARPA-PA-26-05-MATHBAC-PA-010 submitted 2026-04-27 05:02 ET) |
| 12.2 | DARPA reply targeted within 30 calendar days; via Tech POC + Admin POC email on coversheet | L889–891 | OPEN — watch inbox starting 2026-05-27 |
| 12.3 | Even with no abstract, full proposal allowed | L884–885 | INFO |

---

## 13. Special Considerations (FYI but tracked)

| # | Item | Source | Status |
|---|---|---|---|
| 13.1 | All proposals anticipated **unclassified** at PA publication | L947–948 | OK (architectural) |
| 13.2 | HBCUs / Small Businesses / SDB / Minority Institutions encouraged but no set-aside | L939–946 | INFO (Issac qualifies as small minority-owned sole prop) |
| 13.3 | APEX Accelerators free help available | L1013–1031 | DONE (APEX Port Angeles contact memorized) |
| 13.4 | Project Spectrum cybersecurity readiness | L1032–1042 | INFO |
| 13.5 | DARPAConnect free training resources | L1043–1046 | INFO |

---

## 14. Open Decisions (require explicit user authorization)

| # | Decision | Blocker for | Owner |
|---|---|---|---|
| 14.1 | Lock small-science model pick (3.6) | Volume I §TA1 | USER |
| 14.2 | Lock science subdomain + two task families (3.7) | Volume I §TA1 | USER |
| 14.3 | BAAT account creation (0.1) | Submission (13) | USER |
| 14.4 | Past-performance advisor outreach (8.4) | Volume I §Capabilities | USER (memo template can be drafted) |
| 14.5 | DAVA covered-individual disclosures | FRRBS (9.6) | EXTERNAL (Collin) |
| 14.6 | Phase II Evolution Team posture (4.3–4.4) — declare go-it-alone vs. seek partner | Phase II bridge (4) | USER |
| 14.7 | Volume II price strategy (basis sheet now landed — only the price-build call remains) | 8.3 | USER |

---

## 15. Self-Audit Cadence

- **Re-read this checklist after every BAAT amendment to PA-26-05.** Amendments may add or remove "must" obligations. SAM.gov amendment watch (Punch-list item 9) is **file-side discharged** as of 2026-04-27 and **end-to-end verified on the live HTTP-fetch path** as of 2026-04-28: `scripts/mathbac_amendment_watch.py` + `scripts/mathbac_amendment_watch_runner.ps1` + `config/system/mathbac_amendment_watch_task.xml` (daily 09:00 local, 15-min limit, UTF-8 encoded). End-to-end verification: **no-source** branch clean (runner-log `T025929Z`, exit 0); **offline-snapshot** branch clean (runner-log `T032157Z`, exit 0, 11/11 attachments match, pa_pdf sha256 unchanged); **live** HTTP-fetch branch clean (runner-log `T041734Z`, mode=live, runner_exit=0, python_exit=0, 11/11 attachments match against sealed baseline by `resourceId`, pa_pdf sha256 unchanged) — URL pivoted from internal-only `prod/opps/v3/opportunities/{oid}/resources` (HTTP 404 publicly) to public `https://api.sam.gov/opportunities/v2/search?noticeid=...`, with payload synthesized from `resourceLinks`; live-mode field-diff degrades to set diff (added/removed only) by design. OS-level Task Scheduler registration is GATED-USER — must be installed interactively via `Register-ScheduledTask -Xml ...` (instructions in the XML header).
- **Confirm checklist alignment** before each volume draft commit (Vol I, Vol II, Attachment X, etc.).
- **Final pass before BAAT submission:** every row above must be DONE or N/A. Any OPEN, DRAFT, or GATED-USER row = blocker.

## Provenance

Generated 2026-04-27 by reading PA-26-05 (1057 lines) in full, ctrl-F over `must` (50+ hits), `shall` (5), `should` (25+), `required` (20+), and cross-mapping to existing `docs/proposals/DARPA_MATHBAC/` artifacts (proposer_metrics_specs_v1.md, M0_fixture_seal_v1.md, submission_readiness_2026-04-26.md, ip_carveout_v1.md, frr_ot_eligibility_v1.md). Line numbers refer to `artifacts/mathbac/sam_pa_26_05_attachments/DARPA-PA-26-05.txt`.
