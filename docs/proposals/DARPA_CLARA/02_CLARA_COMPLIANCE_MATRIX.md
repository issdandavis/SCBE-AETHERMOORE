# CLARA Proposal Compliance Matrix

**Solicitation**: DARPA-PA-25-07-02
**Program**: CLARA (Compositional Learning-And-Reasoning for AI Complex Systems Engineering)
**Office**: Defense Sciences Office (DSO)
**PM**: Benjamin Grosof
**Deadline**: April 17, 2026, 4:00 PM ET

---

## Solicitation Structure (from FAQ Analysis)

### Task Areas
| TA | Focus | Who |
|----|-------|-----|
| **TA1** | Performer teams — develop compositional ML+AR approaches | **This is us** |
| **TA2** | Integration library — pluggable composition framework | Separate performer |
| **IV&V** | Independent Verification & Validation — Hackathon scenarios | Government-selected |

**SCBE applies to TA1.**

### Phases
| Phase | Duration | Focus | Metrics |
|-------|----------|-------|---------|
| **Phase 1** (Base) | ~12 months | Feasibility Study | Inferencing only |
| **Phase 2** (Option) | ~12 months | Proof of Concept | Inferencing + Training |

### Funding
- Total cap: $2,000,000 per performer (Phase 1 + Phase 2 combined)
- Hackathon incentive: ~$60K reserved (non-Hackathon costs should total no more than $1,940,000)
- Compute resources are part of performer's budget (DARPA does not provide)
- Cost sharing may be required for OT agreements (10 U.S.C. 4022)

---

## Proposal Volume Structure (Standard DARPA PA Format)

### Volume 1: Technical & Management
| Section | Content | Notes |
|---------|---------|-------|
| Cover page | Standard DoD cover page | Program name, solicitation #, performer name, date |
| Table of contents | | |
| Executive Summary | 1-2 pages | Problem, approach, expected outcomes |
| Technical Approach | Core of proposal | Map to CLARA metrics and TA1 requirements |
| Application Task Domain | Performer-proposed domain | AI security governance (our domain) |
| SOA Benchmarks | Explicit state-of-the-art comparison | DeBERTa, Llama Guard, SCBE (before/after semantic projector) |
| Train/Test Corpuses | Identified datasets | 470+ SFT pairs, synthetic benchmark (240 attacks + 20 benign) |
| Milestone Schedule | Phase 1 + Phase 2 milestones | Include Hackathon attendance milestones |
| Management Plan | Team structure, roles, facilities | Sole proprietor + subcontractor plan |
| Key Personnel | PI resume/bio | Issac Daniel Davis |
| Prior work | Relevant past performance | SCBE-AETHERMOORE development history, patent |

### Volume 2: Cost
| Section | Content | Notes |
|---------|---------|-------|
| Cost summary | Total by phase | Phase 1 + Phase 2 under $2M |
| Direct labor | Hours x rates by person | PI rate + any subcontractor |
| Travel | Workshops + Hackathons | DARPA typically holds in-person events |
| Equipment / compute | GPU cloud costs | Document Colab/AWS/GCP estimates |
| Other direct costs | Software licenses, publication | |
| Indirect costs | Overhead rate | Sole proprietor: negotiate rate or use de minimis 10% |
| Subcontractor costs | If applicable | University partner? |

### Volume 3: Administrative
| Item | Required |
|------|----------|
| UEI / CAGE code | Yes (from SAM.gov) |
| Representations and Certifications | Via SAM.gov |
| OCI (Organizational Conflict of Interest) statement | If applicable |
| IP/Patent disclosure | Disclose USPTO #63/961,403 |
| Security classification | CLARA appears unclassified |
| Human subjects / animal use | N/A for AI security |

---

## CLARA's 6 Metrics (from Solicitation Section I.E)

These are what DARPA evaluates performers on:

| # | Metric | What DARPA Measures | SCBE Mapping |
|---|--------|--------------------|----|
| 1 | **Multiplicity of AI Kinds in Composition** | Number of distinct ML and AR kinds used in combination | 3 ML (embeddings, tokenizer, FFT) + 3 AR (axiom logic, governance rules, BFT consensus) = 6 kinds |
| 2 | **Composed Task Reliability of ML+AR System** | Task performance on performer-proposed domain | Detection rate, F1 (0.813), FPR on adversarial benchmark |
| 3 | **Verifiability without Loss of Performance** | AR provides proofs without degrading ML performance | 5 axiom verifiers check invariants; detection holds with axiom enforcement |
| 4 | **Scalability** | Performance maintained as complexity grows | 14 layers scale independently; tongue projection is O(1) per query |
| 5 | **Computational Tractability** | Runs in reasonable time/resources | Semantic projection: ~3ms/query. Full pipeline: <100ms |
| 6 | **Hackathon Performance** | Competitive composition against other TA1 teams | Modular pipeline allows rapid adaptation to IV&V scenarios |

---

## Key FAQ Insights for Our Proposal

### What DARPA explicitly wants:
1. **AR in the guts of ML** — not bolted on. Our harmonic wall operates INSIDE the inference pipeline.
2. **Open-source software** — SCBE is already MIT-licensed on GitHub.
3. **Open, non-proprietary data** — our synthetic benchmark + SFT pairs can be published.
4. **Performer-proposed application domain** — AI security governance, with explicit SOA benchmarks.
5. **New kinds of ML or AR are acceptable** — if they contribute to CLARA objectives.

### What DARPA explicitly does NOT provide:
1. No foundation models (performers build their own)
2. No compute resources (part of performer budget)
3. No scenario data during proposal period
4. No preferred scenarios for Phase 1

### Teaming rules:
- Performers can be on multiple proposals (with mitigation plan)
- Subawardees can participate on multiple teams
- Prime must be identified at abstract submission (abstract deadline passed)
- Teaming arrangements don't need to be final at abstract time

---

## Formatting Requirements (Standard DARPA PA)

| Requirement | Standard |
|-------------|----------|
| Font | Times New Roman, 12pt minimum |
| Margins | 1 inch all sides |
| Line spacing | Single-spaced |
| Page size | 8.5" x 11" |
| File format | PDF |
| Page numbers | Required |
| Classification | UNCLASSIFIED |

**Note**: Check the actual solicitation on SAM.gov for exact page limits. Standard DARPA PAs vary (typically 15-25 pages for Volume 1).

---

## Submission Checklist

- [ ] Volume 1: Technical & Management (PDF)
- [ ] Volume 2: Cost Proposal (PDF or Excel)
- [ ] Volume 3: Administrative (PDF)
- [ ] Cover page with solicitation number (DARPA-PA-25-07-02)
- [ ] UEI and CAGE code on cover page
- [ ] Key Personnel resume (Issac Daniel Davis)
- [ ] IP/Patent disclosure (USPTO #63/961,403)
- [ ] OCI statement (if applicable)
- [ ] Verify submission portal and upload format
- [ ] Submit by April 16 (1 day early for safety margin)
