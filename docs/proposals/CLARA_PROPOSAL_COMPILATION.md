# DARPA CLARA (DARPA-PA-25-07-02) — Proposal Compilation System

**Solicitation**: DARPA-PA-25-07-02 (Disruption Opportunity under DARPA-PA-25-07 Disruptioneering)
**Program**: Compositional Learning-And-Reasoning for AI Complex Systems Engineering (CLARA)
**Technical Area**: TA1 (primary research track)
**Deadline**: April 17, 2026, 4:00 PM ET
**Target Award**: June 16, 2026
**Program Start**: June 22, 2026
**PM**: Benjamin Grosof, DARPA/DSO
**Contact**: CLARA@darpa.mil
**Submission Portal**: https://baa.darpa.mil
**Format**: Single .zip file, ≤100 MB, unclassified only

---

## 0. Prerequisites & Blockers

| Item | Status | Notes |
|------|--------|-------|
| SAM.gov UEI | J4NXHM6N5F59 | Submitted 2026-04-03, activation pending |
| CAGE Code | PENDING | Required for OT agreements; triggered by SAM registration |
| DARPA BAA Portal Account | NOT VERIFIED | https://baa.darpa.mil — need to register/verify access |
| Parent PA DARPA-PA-25-07 | RETRIEVAL IN PROGRESS | Need Section 5 (format) and Section 6 (evaluation) |
| Model OT Agreement | NOT YET REVIEWED | Attachment to DARPA-PA-25-07; need to review terms |
| Task Description Document Template | NOT YET OBTAINED | From DARPA-PA-25-07 attachments |

---

## 1. SOP-to-Tools Mapping

### Proposal Volumes (per Section 5 of DARPA-PA-25-07 — details TBD)

| Volume | Content | Tool/System | Status |
|--------|---------|-------------|--------|
| **Vol 1: Technical** | Technical approach, management, schedule, risks | Claude + codebase research | SCAFFOLD BELOW |
| **Vol 2: Price** | Cost buildup workbook + narrative | Excel workbook (TA1) + cost narrative | WORKBOOK AVAILABLE |
| **Vol 3: Admin/IP** | Data rights, OCI, certifications | Templates from parent PA | TEMPLATES NEEDED |

### Section-by-Section Execution Plan

| Section | Source Material | Tool | Action Needed |
|---------|----------------|------|---------------|
| Cover page | Proposer info, UEI, CAGE | Manual | Fill after CAGE arrives |
| Executive summary | Heilmeier + tech approach | Claude synthesis | Draft after tech sections done |
| Technical approach | SCBE codebase + AR/ML theory | Claude + codebase research | CRITICAL — see Section 3 |
| AR-ML composition | Formal methods + ML integration | Claude + academic research | Identify AR kind + ML kind |
| Theoretical analysis | Proofs of verifiability | Claude + math derivations | Need formal proof sketches |
| Application domain | Unclassified use case + SOA | Web research + benchmarks | SELECT DOMAIN |
| Explainability properties | Hierarchical proofs ≤10 unfolding | Technical writing | Map to SCBE axiom system |
| Tractability analysis | Polynomial complexity proof | Mathematical analysis | Prove or bound complexity |
| Risk identification | Technical + programmatic risks | Domain expertise | Enumerate and mitigate |
| Software substantiation | SCBE repo + dependencies | Codebase analysis | Show existing + planned |
| Management plan | Team, roles, schedule | Org planning | Define team structure |
| Schedule/milestones | 7 Phase 1 + 4 Phase 2 milestones | Workbook template | Pre-filled in workbook |
| Cost narrative | Rate justification | Cost analysis | Justify all rates |
| Cost workbook | Labor, travel, ODC, subs | Excel (TA1 workbook) | FILL IN |
| Data rights | IP assertions | Template from PA | Fill template |
| OCI plan | Conflict analysis | Legal/admin | Likely N/A (no advisory role) |
| Model OT edits | Terms review | Legal review | Review and accept or redline |

---

## 2. Program Parameters (Extracted from Solicitation)

### Phases & Budget

| Phase | Duration | Max Award | Period |
|-------|----------|-----------|--------|
| Phase 1 (Base) | 15 months | $1,350,000 | Jun 2026 – Sep 2027 |
| Phase 2 (Option) | 9 months | $850,000 | Sep 2027 – Jun 2028 |
| **Total** | **24 months** | **$2,000,000** | |

- Up to $100K may shift between phases
- Hackathon incentive: $30K/phase ($60K total) — only top TA1 team
- Non-hackathon milestone costs: ≤ $1,940,000

### Metrics (Figure 1 from Solicitation)

| Metric | Phase 1 Target | Phase 2 Target |
|--------|---------------|---------------|
| Verifiability (no perf loss) | Fully verifiable; Error ≤ SOA | Fully verifiable; Error ≤ SOA |
| AI Kinds in Composition (intra) | ≥1 ML + ≥1 AR | ≥2 ML + ≥1 AR |
| AI Kinds in Composition (inter) | Hackathons | Hackathons |
| Polynomial Time Complexity | Inferencing | Inferencing + Training |
| Composed Task Reliability | > SOA (AUROC) | > SOA (AUROC) |
| Sample Complexity | N/A | < SOA |

### Milestones (TA1)

| # | Month | Deliverable | Payment Notes |
|---|-------|-------------|---------------|
| 1 | 1 | Kickoff meeting; personnel assigned | Payable |
| 2 | 3 | SOA baselines; data sources; approach modifications; ACAs in place | Payable |
| 3 | 6 | Initial AR-ML demo; progress report vs metrics | Payable |
| 4 | 9 | AR-ML demo; metric progress; SW/docs to IV&V for hackathon prep | Payable |
| 5 | 12 | First-place hackathon performance | $30K incentive (winner only) |
| 6 | 12 | AR-ML demo; hackathon report; inter-performer compositions | Payable |
| 7 | 15 | Phase 1 final: demo on selected use-case; final report; all SW/docs | Payable |
| 8 | 18 | Additional AI kinds; SW/docs to IV&V for Phase 2 hackathon | Payable |
| 9 | 21 | AR-ML demo; metric progress report | Payable |
| 10 | 22 | First-place Phase 2 hackathon performance | $30K incentive (winner only) |
| 11 | 24 | Phase 2 final: demo; final report; all SW/docs; hackathon participation | Payable |

### Travel Budget (Required)

| Trip Type | Count | Location | People | Duration |
|-----------|-------|----------|--------|----------|
| DC meetings | 4 | Washington DC area | 2 essential | 2 days each |
| SF meetings | 4 | San Francisco area | 2 essential | 2 days each |
| Phase transition event | 1 | Washington DC area | 2 essential | 1 week |
| **Total trips** | **9** | | | |

### Deliverables

- Quarterly technical reports (within 10 days of quarter end)
- Phase completion reports (within 30 days of phase end)
- Software (open source, preferably Apache 2.0)
- Documentation and training materials
- Data management plan

### AR Kinds (must select ≥1)

- Logic Programs (incl. Bayesian-LP / Probabilistic-LP)
- Classical Logic (incl. Propositional Classical)
- Answer Set Programs
- May extend with Constraints / Fuzzy Logic

### ML Kinds (must select ≥1 Phase 1, ≥2 Phase 2)

- Bayesian (Bayes Nets, HMM, Decision Trees, SRL, EM, Markov Logic)
- Inductive Logic Programs / Meta-Interpretive Learning
- Neural Networks (RNN, CNN, MLP, Transformer, GAN, Neural Additive Models)
- Reinforcement Learning
- "Arithmetic" (Regression, SVM, GAM)

---

## 3. Technical Approach — Bullet Point Compilation

### 3.1 Proposed AR-ML Composition Approach

**AR Kind Selection**: [TBD — awaiting technical mapping]
- [ ] Logic Programs (strongest candidate — SCBE axiom system is rule-based)
- [ ] Classical Logic
- [ ] Answer Set Programs

**ML Kind Selection (Phase 1 — ≥1)**: [TBD]
- [ ] Neural Networks (Transformer-based — LLM governance)
- [ ] Bayesian (probabilistic safety scoring)
- [ ] Reinforcement Learning (agent behavior optimization)

**ML Kind Selection (Phase 2 — add ≥1 more)**: [TBD]

**Composition Approach Bullet Points**:
- [ ] How AR and ML are tightly coupled (not just pipeline — must be compositional)
- [ ] Theoretical analysis of why composition preserves verifiability
- [ ] What logical explainability properties the composition provides
- [ ] How composition extends to additional kinds
- [ ] Software-to-software connection analysis

### 3.2 Verifiability & Explainability

**Bullet Points**:
- [ ] Automatic proof mechanism (what proves soundness/completeness?)
- [ ] How proofs are hierarchical with ≤10 unfolding expansion
- [ ] Natural deduction style explanation
- [ ] Fine-grained decomposition of decisions
- [ ] Error rate comparison methodology vs SOA

### 3.3 Tractability / Polynomial Complexity

**Bullet Points**:
- [ ] Complexity class of inferencing (prove polynomial or show practical scaling)
- [ ] Phase 2: complexity of training
- [ ] Scaling experiments plan (millions of clauses)
- [ ] Theory + empirical demonstration approach

### 3.4 Application Domain & SOA Benchmarks

**Candidate Domains** (must be unclassified, DARPA-relevant):
- [ ] Course of Action planning/evaluation
- [ ] Multi-condition medical guidance
- [ ] Supply chain / logistics
- [ ] Cybersecurity / threat assessment (closest to SCBE's existing domain)
- [ ] AI safety governance (novel — is this too meta?)

**SOA Requirements**:
- [ ] Identified pair of existing ML + AR models for benchmark
- [ ] Associated sample complexity
- [ ] Train/test corpus
- [ ] AUROC or similar performance metric

### 3.5 Risk Identification & Mitigation

**Bullet Points**:
- [ ] Technical risk: AR-ML integration complexity
- [ ] Technical risk: Achieving polynomial tractability with sufficient expressiveness
- [ ] Programmatic risk: Team scale (sole proprietor — see mitigation)
- [ ] Mitigation: Early prototype, iterative development
- [ ] Mitigation: Leverage existing SCBE infrastructure

### 3.6 Software Substantiation

**Existing Software**:
- [ ] SCBE-AETHERMOORE repo (TypeScript + Python, Apache 2.0 compatible?)
- [ ] 14-layer pipeline implementation
- [ ] Axiom verification system
- [ ] Sacred Tongues tokenizer
- [ ] GeoSeal CLI
- [ ] HYDRA multi-agent orchestrator

**Planned Development**:
- [ ] AR-ML composition layer
- [ ] Formal proof generation
- [ ] Benchmark evaluation harness

### 3.7 Management Plan

**Team Structure**:
- PI: Issac Davis (sole proprietor)
- [ ] Subcontractors/collaborators? (would strengthen proposal significantly)
- [ ] Academic partners? (university affiliation for credibility)
- [ ] Consultants?

**Key Risk**: Sole proprietor with no employees — DARPA typically expects teams.

---

## 4. Cost Volume — Structure

### Labor Categories Needed (from workbook Constants sheet)

For Small Business:
- Project Management: PI (Issac Davis)
- Science and Engineering: [Roles TBD]
- Software Development: [Roles TBD]
- Consultant: [If any]
- Support: [If any]

### Cost Estimation Framework

| Category | Phase 1 (15mo) | Phase 2 (9mo) | Total |
|----------|---------------|---------------|-------|
| Direct Labor | | | |
| Fringe Benefits | | | |
| Labor Overhead | | | |
| Subcontracts | | | |
| Consultants | | | |
| Travel | ~$25K est. | ~$15K est. | ~$40K |
| Equipment | | | |
| Other ODC | | | |
| Material Handling | | | |
| G&A | | | |
| Cost of Money | | | |
| Fee/Profit | | | |
| **Subtotal** | **≤ $1,350K** | **≤ $850K** | **≤ $2,000K** |

### Travel Estimate Detail

| Trip | Destination | People | Days | Est. Cost |
|------|-------------|--------|------|-----------|
| Kickoff (Phase 1) | Washington DC | 2 | 2 | ~$3,500 |
| Meeting 2 | San Francisco | 2 | 2 | ~$4,000 |
| Meeting 3 | Washington DC | 2 | 2 | ~$3,500 |
| Meeting 4 | San Francisco | 2 | 2 | ~$4,000 |
| Phase transition week | Washington DC | 2 | 5 | ~$8,000 |
| Meeting 6 | San Francisco | 2 | 2 | ~$4,000 |
| Meeting 7 | Washington DC | 2 | 2 | ~$3,500 |
| Meeting 8 | San Francisco | 2 | 2 | ~$4,000 |
| Contingency | — | — | — | ~$5,500 |
| **Total Travel** | | | | **~$40,000** |

---

## 5. Evaluation Criteria

Per Section 6 of DARPA-PA-25-07 — **AWAITING RETRIEVAL**

Typical DARPA Disruptioneering evaluation factors (expected):
1. Technical Merit / Innovation
2. Potential for Disruption
3. Team Qualifications / Management
4. Cost Realism
5. Schedule Feasibility

[UPDATE THIS SECTION when parent PA is retrieved]

---

## 6. Submission Checklist

- [ ] CAGE code received (SAM.gov activation)
- [ ] DARPA BAA Portal account created and verified
- [ ] Parent PA DARPA-PA-25-07 reviewed (all sections)
- [ ] Model OT agreement reviewed
- [ ] Task Description Document template obtained and filled
- [ ] Volume 1: Technical proposal (format per Section 5)
- [ ] Volume 2: Cost workbook (TA1 Excel) + cost narrative
- [ ] Volume 3: Admin volume (data rights, certifications)
- [ ] All volumes assembled into single .zip (≤100 MB)
- [ ] Submission uploaded to https://baa.darpa.mil
- [ ] Confirmation email received (within 2 business days)
- [ ] If no confirmation: contact CLARA@darpa.mil

---

## 7. Key Contacts

- **PM**: Benjamin Grosof, DARPA/DSO
- **Email**: CLARA@darpa.mil
- **Tech Support**: BAAT_Support@darpa.mil (cc CLARA@darpa.mil)
- **APEX Accelerator (local)**: 338 W First St, Port Angeles, (360) 457-7793, APEX@clallam.org

---

## 8. Critical Decisions Needed

1. **AR Kind**: Which automated reasoning approach to propose?
2. **ML Kind(s)**: Which ML systems to compose with AR?
3. **Application Domain**: What unclassified task domain to demonstrate on?
4. **Team Composition**: Solo or with subcontractors/partners?
5. **License**: Apache 2.0 for SCBE open-source release?
6. **Cost Share**: Required for non-traditional defense contractors? (Check Section 4 of parent PA)
