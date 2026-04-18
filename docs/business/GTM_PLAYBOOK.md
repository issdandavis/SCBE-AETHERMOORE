# Go-To-Market Playbook

> Consolidated pricing, ICP, channels, and outreach sequence.
> Last Updated: April 17, 2026

---

## 1. Products and Pricing

### SCBE Gateway (SaaS/API)

| Tier | Monthly | Target | Includes |
|------|---------|--------|----------|
| Starter | $499 | Early-stage teams | Core 14-layer pipeline, basic audit logs, capped action volume |
| Growth | $2,500 | Production teams | Full pipeline, expanded controls, SIEM export, higher throughput |
| Enterprise | Custom | High-scale orgs | Dedicated deployment, custom policies, SLA, on-prem option |

**Pricing unit:** Per 1,000 decisions (authorize/deny/quarantine) + per-tenant platform floor.
**Alternative packaging:** Per-agent bundles for customers preferring predictable budgeting.

### SCBE Assurance (Compliance)

| Scope | Monthly | Includes |
|-------|---------|----------|
| Single environment | $3,000 | One AI system, quarterly reports, basic retention |
| Multi-environment | $5,000-7,000 | Multiple systems, monthly reports, extended retention |
| Enterprise | $10,000 | All environments, continuous reporting, custom frameworks, dedicated support |

### AI Red Team as a Service

| Deliverable | Format |
|-------------|--------|
| 91 adversarial prompts | Custom to target system |
| Branded PDF report | Executive summary + technical findings |
| Remediation roadmap | Prioritized fixes with difficulty ratings |
| Quarterly re-tests | Ongoing adversarial validation |

**Pricing:** Per engagement. Contact for quote.

### Packaged Products (One-Time Purchase)

| Product | Description |
|---------|-------------|
| AI Governance Toolkit | Templates, thresholds, decision records, rollout guidance |
| HYDRA Agent Templates | Agent roles, packet patterns, launch structure for governed swarms |
| n8n Workflow Pack | Governed automation building blocks, importable workflows |
| Content Spin Engine | Source-once content operations across channels |

**Buy links:** aethermoore.com/services.html

---

## 2. Ideal Customer Profile

### Primary ICP (Year 1-2)

**Mid-market and enterprise product teams deploying LLM agents into regulated workflows.**

| Segment | Pain Point | Entry Product | Expand To |
|---------|-----------|---------------|-----------|
| **Fintech / Banking** | Fraud detection, AI governance for regulators | Gateway Starter | Assurance + Red Team |
| **Insurance** | Actuarial model governance, state regulators | Assurance | Gateway + Red Team |
| **Healthcare** | HIPAA + AI governance intersection | Assurance | Gateway |
| **B2B SaaS** | Agent guardrails for customer-facing automation | Gateway Growth | Enterprise + Assurance |
| **Platform / Security teams** | Production guardrails across multiple agents | Gateway Growth | Enterprise |

### Secondary ICP (Year 2-3)

| Segment | Entry Point |
|---------|-------------|
| AI platform providers (Salesforce, Databricks, Snowflake) | Gateway Enterprise (platform integration) |
| Defense contractors (Lockheed, Booz Allen, Northrop) | Assurance + Gateway (SBIR/STTR) |
| Government / DoD (CDAO, TRADEWINDS) | Gateway Enterprise (vendor profile) |

### Buying Triggers

- Deploying AI agents to production for the first time
- Regulator or auditor asking "how do you govern your AI?"
- Incident where an AI agent went off-policy
- ISO 42001 or EU AI Act compliance deadline approaching
- Board or C-suite mandate for AI governance framework
- Hiring VP/Director of AI Governance (budget signal)

---

## 3. Channels

### Direct Outreach

| Channel | Target | Template |
|---------|--------|----------|
| Cold email | Innovation lab leads, VP/Director AI, CISOs | See PITCH_EMAIL_BANK_INNOVATION_LAB.md |
| LinkedIn connection | Security and AI governance professionals | Short request + curiosity hook |
| Conference networking | RSAC, IAPP, AI DevSummit, Databricks Summit | Demo-ready, one-pager in hand |

### Investor Pipeline

| Priority | Targets | Status |
|----------|---------|--------|
| Highest | SAIF ($100K SAFE), IQT ($11-17M), Paladin Capital | See PITCH_TARGETS_INTELLIGENCE.md |
| High | General Catalyst, a16z American Dynamism, Shield Capital | Thesis-aligned |
| Medium | Air Street Capital, Radical Ventures, Conviction | AI safety focus |

### Grant Pipeline

| Program | Amount | Deadline | Status |
|---------|--------|----------|--------|
| Schmidt Sciences Trustworthy AI | $1M-5M+ | May 17, 2026 | Prepare application |
| Open Philanthropy AI Governance | $200K-2M/yr | Rolling | Ready to submit |
| SFF Speculation Grants | Varies | Rolling (1-week turnaround) | Ready to submit |
| Foresight Institute AI Safety | $10K-100K | Rolling | Ready to submit |
| NSF SBIR/STTR | Up to $30M | Apr-May 2026 (expected) | SBIR pitch ready |
| UK AISI Challenge Fund | £50K-200K | Through Apr 2026 | Evaluate fit |

### Licensing Targets

Companies that need PQC + governance capabilities they don't have:

| Company | Gap | Licensing Value |
|---------|-----|-----------------|
| HiddenLayer ($56M, MDA SHIELD) | No PQC, no geometry | Quantum-resistant capabilities for classified deployments |
| Credo AI ($41M, Andrew Ng) | No security, no runtime | PQC + multi-agent as complement |
| Arthur AI ($63M) | No inference-time guardrails | Runtime governance module |
| Guardrails AI ($7.5M, open-source) | No PQC | Premium PQC module on open-source base |

### Defense Contractor Channels

| Contractor | Key Contact | Entry Point |
|-----------|-------------|-------------|
| Lockheed Martin | Mike Baylor (CDAO), Astris AI | Supplier portal + SBIR partnership |
| Booz Allen Hamilton | Steve Escaravage (Defense Tech) | Investment + customer + conference |
| Northrop Grumman | Vern Boyle (Adversarial AI) | Technical engagement |
| Palantir | Shyam Sankar (CTO) | Palantir-Anduril consortium |
| DoD CDAO / TRADEWINDS | Cameron Stanley | Vendor profile + pitch video |

---

## 4. Outreach Sequence

### Week 1-2: Foundation

- [ ] Update SAM.gov profile with current capabilities
- [ ] Create TRADEWINDS vendor profile + pitch video
- [ ] Submit to IQT technology submission form (no warm intro required)
- [ ] Submit to SAIF application (saif.vc/request)
- [ ] Submit Open Philanthropy AI Governance RFP

### Week 3-4: Direct Outreach (Batch 1)

- [ ] Send bank innovation lab emails (JPMorgan SAIGE team, Citi AI CoE, BNY Mellon)
- [ ] Send AI company emails (targets deploying autonomous agents)
- [ ] LinkedIn connect with 20 AI governance / CISO professionals
- [ ] Submit Schmidt Sciences Trustworthy AI application (due May 17)

### Week 5-6: Direct Outreach (Batch 2)

- [ ] Send defense contractor emails (Lockheed, Booz Allen, Northrop)
- [ ] Send licensing target emails (HiddenLayer, Credo AI, Guardrails AI)
- [ ] Follow up on Batch 1 (Day 5 follow-up template)
- [ ] Submit SFF Speculation Grant

### Week 7-8: Conference Prep

- [ ] Register for IAPP AI Governance Global (May 4-6, Toronto)
- [ ] Register for AI DevSummit (May 27-28, South San Francisco)
- [ ] Prepare demo for conference floor conversations
- [ ] Print one-pagers and battle cards

### Ongoing (Monthly)

- [ ] Follow up on all open outreach threads
- [ ] Update COMPETITIVE_INTEL with new funding/M&A announcements
- [ ] Update battle cards with new competitor information
- [ ] Track grant application statuses
- [ ] Post 2-3 LinkedIn articles on AI governance topics

---

## 5. Sales Collateral Inventory

| Document | Location | Status |
|----------|----------|--------|
| Battle cards (8 competitors) | docs/business/BATTLE_CARDS.md | Done |
| Competitive positioning | docs/business/COMPETITIVE_POSITIONING.md | Done |
| Gateway product one-pager | docs/business/PRODUCT_ONE_PAGER_GATEWAY.md | Done |
| Assurance product one-pager | docs/business/PRODUCT_ONE_PAGER_ASSURANCE.md | Done |
| GTM SKUs with pricing | docs/GO_TO_MARKET_SKUS.md | Done |
| Launch SKU + 12-week roadmap | docs/product/LAUNCH_SKU.md | Done |
| Pitch email templates (4 personas) | docs/PITCH_EMAIL_BANK_INNOVATION_LAB.md | Done |
| Investor one-pager | docs/ONE_PAGER_INVESTOR.md | Done |
| Technical pitch deck | docs/specs/INVESTOR_PITCH_TECHNICAL.md | Done |
| SBIR elevator pitch | docs/proposals/SBIR_ELEVATOR_PITCH.md | Done |
| Pitch targets intelligence | docs/business/PITCH_TARGETS_INTELLIGENCE.md | Done |
| Competitive intel Q1 2026 | docs/business/COMPETITIVE_INTEL_Q1_2026.md | Done |
| Darktrace deep-dive | docs/08-reference/archive/COMPETITIVE_ANALYSIS.md | Done |
| Full competitive analysis 2026 | docs/08-reference/archive/COMPETITIVE_ANALYSIS_2026.md | Done |
| AetherBrowser competitive goal | docs/specs/AETHERBROWSER_COMPETITIVE_GOAL.md | Done |

---

## 6. Key Numbers (Keep Updated)

| Metric | Current Value | Source |
|--------|--------------|--------|
| Codebase | 50,000+ LOC | Repo |
| Tests | 1,150+ passing | CI |
| Patent | USPTO #63/961,403 (47 claims) | Filing |
| SAM.gov UEI | J4NXHM6N5F59 | SAM.gov |
| SAM.gov CAGE | 1EXD5 | SAM.gov |
| Cost per decision | ~$0.0003 | AWS Lambda benchmark |
| TAM (AI security) | $18.6B (2026) → $78.3B (2030) | Market reports |
| TAM (AI governance) | $5.77B by 2029 (45.3% CAGR) | Market reports |
| Competitor M&A total | $1.38B (4 acquisitions) | Public filings |
| Agentic AI sec funding Q1 2026 | $392M+ | RSAC tracking |

---

_April 2026_
