# Attachment G — Performer Fill Guide

> Open `official_templates/Attachment_G_Model_Other_Transaction_for_Research_Agreement_MATHBAC_.docx`.
> **Performer fills blue text only.** Do not touch brown/red sections — those are DARPA-fill.
> Enable Track Changes before editing if you want DARPA to see your edits clearly.

---

## Quick-fill Table

| Placeholder | Your value | Notes |
|---|---|---|
| `(INSERT PERFORMER AND ADDRESS)` | ISSAC D DAVIS / SCBE-AETHERMOORE<br>2361 E 5th Ave<br>Port Angeles, WA 98362 | Cover page + body L030 |
| `(INSERT PERFORMER NAME)` | ISSAC D DAVIS / SCBE-AETHERMOORE | Signature block L031 |
| `(INSERT RESEARCH AND DEVELOPMENT EFFORT)` | SCBE Mathematical Framework for Agentic Communication Protocols | Cover page title line |
| `(INSERT GOAL(S) OF AGREEMENT)` | See draft below | Article 3, L098 |
| `(INSERT NUMBER OF MONTHS) (xx) months` | **16 (sixteen)** months | Article 4, L103 |
| `(ENTER CAGE CODE)` | **1EXD5** | Financial Article, L172 |
| `(ENTER UEI)` | **J4NXHM6N5F59** | Financial Article, L173 |
| `(ENTER TIN)` | **[YOUR SSN OR EIN — do not record here]** | Financial Article, L174 — sole prop = SSN unless you have EIN |
| Data retention `(INSERT NUMBER OF YEARS)` (L233) | **3 (three)** | Standard DARPA minimum |
| Post-term article duration `(INSERT NUMBER OF YEARS)` (L240) | **3 (three)** | CUI/data rights article |
| Tax felony checkboxes (L410–L411) | Mark **"is not"** for both | Sole proprietor — not a corporation; mark anyway per form instructions |

---

## Goal Statement Draft (Article 3, L098)

> Fill into: `The goal of this Agreement is _____.`

**Draft text:**

> develop a mathematically rigorous framework for governing multi-agent AI communication protocols using a composed Poincaré-ball operator with five physical axioms, demonstrated on NMR spectroscopy task families, producing certified convergence bounds, a protocol coherence drift index (CDPTI), and a computational design tool for applying the framework to new scientific subdomains.

Adjust length/wording to taste — this should match the one-sentence framing from Attachment D §1.1.

---

## Attachment 3 — Schedule of Milestones and Payments

The template has a placeholder example (XXXX molecule candidate — ignore, that is from a chemistry program). Replace with SCBE milestones. Suggested structure (fill dollar amounts once Attachment F is finalized):

| Milestone | Month | Description | Payment ($) |
|---|---|---|---|
| MS-1 | 1 | Kickoff: theory/model/baseline plan and personnel assignment; SSM probe-layer calibration; φ-weighting ablation design; IV&V bundle format fixed | $84,000 |
| MS-2 | 3 | Initial successes/failures; initial mathematical framework; Lyapunov constants η, b measured; L_H(G_t) instrumented; CDPTI live | $109,000 |
| MS-3 | 6 | PI meeting; framework description; IV&V data-pipeline demo; CDPTI live demo; ≥2 NMR subtask variants; metric progress report | $151,000 |
| MS-4 | 9 | Initial software suite report; ROMs; Hammett generalization validation; IV&V challenge progress | $151,000 |
| MS-5 | 13 | PI meeting; side-by-side baseline comparison vs. Mixtral-8x7B; superior protocol set; PIS catalog v1 | $151,000 |
| MS-6 | 14 | Computational design tool demo: Lagrangian automation for new subdomains; IV&V test results | $84,000 |
| MS-7 | 16 | Final report; protocol catalog; Phase II plan; full archive | $109,000 |
| **TOTAL** | | | **$839,000** |

> Payments must be milestone-triggered, not time-triggered. Keep descriptions concise (one line per milestone). DARPA will review these for SOW consistency. Dollar amounts from Attachment F / BAAT proposed cost.

---

## DARPA-Fill Items — Do NOT Touch

These are brown/red in the template. Leave blank:

- Agreement No. `HR0011-XX-3-XXXX`
- Purchase Requisition No.
- Total Amount / Funds Obligated
- Line of Appropriation (CLIN/ACRN table)
- `(INSERT AO'S EXTENSION)` — WAWF section
- `the Service Acceptor AOR DoDAAC` — WAWF section
- `DFAS-(INSERT APPROPRIATE DFAS OFFICE)` — payment section
- `(INSERT IMAGES OF AOR APPOINTMENT MEMO HERE)` — Attachment 2
- Milestone Report example text with "XXXX molecule" — replace with your milestones but DARPA controls the numbering

---

## Subcontractor Row (Hoags Inc.)

If Hoags is formally included as a subcontractor:
- Article requiring subcontract flow-downs applies (L214, L238, L253, L270, L319)
- Their scope must match Annex A / Attachment H TDD language exactly
- Do not name them as prime or co-PI anywhere in G

---

## Checklist Before Saving

- [ ] All `(INSERT ...)` and `(ENTER ...)` replaced
- [ ] Both `(INSERT NUMBER OF YEARS)` filled (L233 and L240)
- [ ] Both tax felony checkboxes marked "is not"
- [ ] Milestone table complete — descriptions and amounts filled (from F: $839K total, see table above)
- [ ] TIN entered in the document (NOT saved to repo — fill directly in the Word file)
- [ ] Track Changes on if you are suggesting any non-administrative edits to DARPA
- [ ] Save as `Attachment_G_SCBE_FILLED.docx` — keep the original template untouched
