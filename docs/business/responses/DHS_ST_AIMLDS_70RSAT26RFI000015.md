# Response to Sources Sought / RFI 70RSAT26RFI000015

**Subject:** Artificial Intelligence, Machine Learning, and Data Science (AI/ML/DS) Technical Support Services
**Issuing office:** DHS S&T — Office of Procurement Operations, Sci Tech Acq Division
**Submitted by:** SCBE-AETHERMOORE (Issac D. Davis, sole proprietor)
**Date:** 2026-05-05
**Response method:** Email to Jennifer.Koons@hq.dhs.gov, subject line "Response to 70RSAT26RFI000015 — SCBE-AETHERMOORE"
**Attached:** SCBE-AETHERMOORE Capability Statement (1 page)

---

## 1. Company Identification

| Field | Value |
|---|---|
| Legal name | Issac D. Davis (DBA SCBE-AETHERMOORE) |
| UEI | J4NXHM6N5F59 |
| CAGE Code | 1EXD5 |
| SAM status | Active (registered 2026-04-02; expires 2027-04-03) |
| SBA SBIR Control ID | SBC_002676728 |
| Business size | Small business under all listed NAICS, including 541611 |
| Socioeconomic | Sole proprietor; minority-owned |
| Address | 2361 East 5th Avenue, Port Angeles, WA 98362 |
| Phone | (360) 808-0876 |
| Email | issdandavis7795@gmail.com |
| Website | https://aethermoore.com |
| GitHub | https://github.com/issdandavis/SCBE-AETHERMOORE |

---

## 2. Capability Mapping to the RFI Statement of Need

The RFI lists six technical capability areas. Below is an honest yes / partial / no map against each, followed by evidence.

### 2.1 Conducting and providing independent evaluations of AI/ML/DS tools — **YES**

SCBE-AETHERMOORE's primary practice area is **independent, gate-based evaluation of AI/ML systems**. Our open-source repository implements:

- A multi-layer **safety pipeline** (governance, harmonic, constrained-decoding) that scores model outputs against frozen contracts.
- A **double-blind evaluation harness** with cryptographic commit-reveal mapping receipts, so candidate identity is hidden from the scoring stage and tampering is mathematically detectable.
- An **executable promotion gate** that blocks model promotion when frozen-holdout benchmarks fail — no metric-only "passes."

These are exactly the tools required when an agency needs an evaluator that is not the system vendor.

### 2.2 Supporting testing, validation, and standards development — **YES**

We design test contracts shaped against:

- **NIST AI Risk Management Framework (AI RMF 1.0)** — Govern, Map, Measure, Manage functions
- **ISO/IEC 42001:2023** AI management system controls
- **EO 14110** federal AI deployment guidance

Our compliance documentation pattern is reusable across mission domains: required-token contracts, forbidden-token boundary guards, must-pass thresholds, and reproducible scoring receipts.

### 2.3 Evaluating and analyzing AI/ML and DS tools — **YES**

We perform tooling-side evaluations: comparing model behavior across base models, adapters, and decoding strategies; isolating which intervention (training vs. constrained decoding vs. prompt design) actually moves the gate metric. We have published failure-mode postmortems where SFT plateaued and constrained decoding cleared the same gate at 5/5 — a class of finding that materially changes evaluator recommendations.

### 2.4 Developing and evaluating automated image analysis software and algorithms — **PARTIAL**

This is not our primary practice area. We have not built production image-analysis pipelines for X-ray or CT screening data. We can credibly support the **evaluation, governance, and assurance** layer above an image-analysis tool — including bias and drift detection, threshold calibration, and adversarial robustness testing — but we would not lead the model-development side without a teaming partner who specializes in computer vision for screening.

### 2.5 Supporting development and interpretation of open architecture data and metadata standards — **YES**

We maintain machine-readable schemas and JSONL contract formats for AI evaluation, training data, and audit telemetry. Our work emphasizes deterministic, version-pinned schemas that survive model and tool churn — exactly the property an open-architecture standard needs.

### 2.6 Supporting and creating algorithm training, validation, testing and assurance tools — **YES**

We build assurance tooling end to end: training-data validation, post-training evaluation gates, tamper-resistant scoring, and audit-grade reporting. Our recent published work demonstrates the full loop on a 0.5B-parameter chemistry-verification adapter, including a **post-train gate runner** that exits non-zero on threshold miss before any model is promoted. The same harness generalizes to any required/forbidden contract — including image-analysis output validation when the relevant labels are tokenizable.

---

## 3. Key Differentiators

- **Founder-led delivery, no subcontracting layers.** Direct technical engagement; rapid iteration; cost discipline appropriate to RFIs and Phase I-scale work.
- **Open public artifact of capability.** Our governance, evaluation, and assurance code is on GitHub today (https://github.com/issdandavis/SCBE-AETHERMOORE), with a documented commit history, CI gates, and reproducible test suites. DHS S&T evaluators can inspect the actual work product before contracting.
- **Minority-owned small business.** Supports DHS small-business and socioeconomic goals; eligible for relevant set-asides under listed NAICS.
- **Active in adjacent federal AI/safety pipelines.** Submitted abstract to DARPA MATHBAC (DARPA-SN-26-59) and proposal to DARPA CLARA (DARPA-PA-25-07-02 / FP-033) — June 2026 award decisions. Demonstrates the firm's federal-research engagement is real, not aspirational.

## 4. Past Performance

SCBE-AETHERMOORE is an early-stage small business (SAM-active since 2026-04-02). We have **no prior federal contracts**. We are responding because the RFI explicitly requests insight into small-business capabilities, including emerging firms.

In lieu of contract past performance, the public technical record stands as primary evidence:

- **GitHub repository** (https://github.com/issdandavis/SCBE-AETHERMOORE) — multi-language (TypeScript, Python, Rust) implementation of an AI governance and assurance pipeline, including 14 documented architectural layers and a continuous-integration test suite.
- **Documented postmortem of an evaluation cycle** — `artifacts/cleanup_2026_04_29/POSTMORTEM_failed_adapters.md` shows the firm's discipline on negative results: failed adapters were not silently dropped; the failure modes were enumerated and a follow-on intervention (constrained decoding) was empirically validated to clear the original contract gate at 5/5.
- **Active federal proposal pipeline** — MATHBAC abstract submitted 2026-04-27; DARPA CLARA FP-033 submitted (decision 2026-06-16).

We are willing to provide additional technical demonstrations or read-only repository access on request.

## 5. Recommended Procurement Approach

We respectfully suggest DHS S&T consider the following for the eventual task order:

1. **Total small-business set-aside** under NAICS 541611 if the requirement size supports it. The RFI's stated purpose includes understanding small-business capability specifically; a set-aside aligns means with end.
2. **OASIS+ Small Business pool** as the contract vehicle, consistent with the RFI's market-research framing. SCBE-AETHERMOORE is not currently an OASIS+ holder, but we can team with an OASIS+ small-business prime to provide the AI evaluation, governance, and assurance components of the task order.
3. **Modular task structure** that separates (a) image-analysis development, (b) evaluation and assurance, and (c) standards/test-tool development. This lets DHS S&T match each task module to firms whose capabilities are actually deepest in that module.

## 6. Point of Contact

**Issac D. Davis**
Principal, SCBE-AETHERMOORE
Email: issdandavis7795@gmail.com
Phone: (360) 808-0876
Address: 2361 East 5th Avenue, Port Angeles, WA 98362

---

## 7. Statement of Compliance

This response is submitted in compliance with the RFI:

- This response is **not a proposal** and does not constitute a binding offer.
- No proprietary or restricted information is included; the entire response is releasable.
- SCBE-AETHERMOORE acknowledges that the Government will not reimburse any costs incurred in preparing this response.
- All factual claims (UEI, CAGE, SAM status, business size) are verifiable in SAM.gov as of the response date.
