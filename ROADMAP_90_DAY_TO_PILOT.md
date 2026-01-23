# 90-Day Roadmap: From Ball of Code to First Paid Pilot

**Start Date:** January 20, 2026
**Target:** First paid pilot signed by April 20, 2026

---

## Phase 1: Packaging (Days 1-30)

### Week 1-2: API Wrapper
- [ ] Create REST API wrapper around core functions
  - `POST /evaluate` - Submit context, get risk score
  - `POST /envelope/sign` - Create RWP envelope
  - `POST /envelope/verify` - Verify envelope
  - `GET /health` - System status
- [ ] Deploy to AWS Lambda (serverless, pay-per-use)
- [ ] Create API documentation (OpenAPI/Swagger)

### Week 3-4: Demo Dashboard
- [ ] Simple web UI showing:
  - Real-time risk scores
  - Hyperbolic distance visualization (the "bubble")
  - Transaction history with pass/fail
  - "Why it failed" explainer
- [ ] Record 5-minute demo video
- [ ] Create interactive sandbox (try-it-yourself)

**Deliverable:** Working API + demo you can show prospects

---

## Phase 2: Proof of Value (Days 31-60)

### Week 5-6: Synthetic Fraud Dataset
- [ ] Generate 10,000 synthetic transactions
  - 9,500 legitimate (normal patterns)
  - 500 fraudulent (various attack types)
- [ ] Run through SCBE engine
- [ ] Document detection rate vs. traditional rules
- [ ] Create comparison chart (SCBE vs. linear rules vs. ML)

### Week 7-8: Benchmark Report
- [ ] Performance metrics:
  - Latency per transaction (target: <50ms)
  - Throughput (target: 10,000 tx/second)
  - False positive rate
  - Detection rate by attack type
- [ ] Write 5-page technical white paper
- [ ] Create 1-page executive summary

**Deliverable:** Proof that SCBE catches things others miss

---

## Phase 3: Sales (Days 61-90)

### Week 9-10: Target List + Outreach
- [ ] Identify 20 targets:
  - 5 banks (innovation labs)
  - 5 fintechs (fraud teams)
  - 5 AI companies (agent governance)
  - 5 defense contractors (secure comms)
- [ ] Personalize pitch for each vertical
- [ ] Send outreach emails (see template below)
- [ ] LinkedIn warm intros where possible

### Week 11-12: Pilot Negotiations
- [ ] Demo calls with interested parties
- [ ] Scope pilot terms:
  - Duration: 30-90 days
  - Data: Their sandbox or synthetic
  - Price: $10k-$50k (paid POC)
  - Success criteria: Detection rate, latency
- [ ] Draft pilot agreement (1-2 pages)
- [ ] Sign first pilot

**Deliverable:** Signed paid pilot

---

## Budget Estimate

| Item | Cost | Notes |
|------|------|-------|
| AWS (3 months) | $500 | Lambda + API Gateway |
| Domain + SSL | $50 | Professional appearance |
| Demo video editing | $200 | Fiverr/contractor |
| LinkedIn Premium | $100 | For outreach |
| Legal (pilot agreement) | $500 | Lawyer review |
| **Total** | **$1,350** | |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| API deployed | Day 14 |
| Demo working | Day 28 |
| White paper done | Day 56 |
| First demo call | Day 70 |
| Pilot signed | Day 90 |
| Pilot price | $10k-$50k |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| No responses to outreach | Warm intros via LinkedIn, conferences |
| Technical issues during demo | Practice 10x, have backup video |
| Prospect wants SOC 2 | "Pilot is for R&D/sandbox, prod comes later" |
| Price objection | Start at $10k, prove value, upsell |

---

## What You DON'T Need for Pilot

- SOC 2 (it's a sandbox pilot)
- Pen test (not production yet)
- 24/7 support (it's 90 days)
- Full PQC (nice to have, not required)
- Insurance (pilot agreement limits liability)

Focus on: **Demo that wows + proof it works + clear pilot terms**

---

## Next Action

**Tomorrow:** Set up AWS account and deploy basic API endpoint.

The 90 days starts when you take the first action.
