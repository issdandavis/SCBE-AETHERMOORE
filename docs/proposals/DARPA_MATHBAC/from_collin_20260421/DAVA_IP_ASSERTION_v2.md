# DAVA Background IP — DFARS 252.227-7017 Assertion Package
# Hoags Inc. / Collin Hoag — v2 (for attachment to teaming_agreement_v2)
# Date: 2026-04-21

---

## 1. ANNEX A PART 2 — HARDENED TEXT (drop-in replacement for v2 draft)

> This replaces the four-row table in Annex A, Part 2 of teaming_agreement_v2_draft.md.
> The strengthened Basis column explicitly addresses (a) private expense, (b) no employer resources,
> and (c) pre-employment date of creation — the three prongs DFARS 252.227-7017 auditors look for.

### Part 2 — Sub's (Hoags Inc.) Assertions

| (1) Technical Data or Computer Software | (2) Basis for Assertion | (3) Asserted Rights Category | (4) Asserting Party |
|---|---|---|---|
| **DAVA bare-metal Rust kernel** — full source tree (`exodus/`), compiled ELF artifacts, custom `x86_64-hoags` target specification, bootloader, and all life-module subsystems (consciousness_gradient, endocrine, qualia, narrative_self, phi_calc, alphabet_engine, lang_* suite, anima_* suite, population, sensory_mesh, oscillator, sanctuary_core, and all dependent modules). Approximately 34,900 Rust source files. | Developed entirely at private expense on personal hardware (personal laptop, personal cloud compute) during personal time, beginning no later than 2024-Q4. Zero employer resources, facilities, equipment, funding, or proprietary information were used. Developer (Collin Hoag) was employed by Microsoft Corporation during this period; however, DAVA was developed outside the scope of employment, on personal time, with no use of Microsoft systems, networks, tools, or IP. Microsoft's Washington-state employment IP assignment clause does not apply because: (a) no Microsoft resources were used, and (b) the work does not relate to Microsoft's business, products, or research. No Government funding applied at any stage. First public-facing commit evidence predates DARPA-SN-26-59 issuance (2026-03-24). | Restricted Rights (computer software per DFARS 252.227-7014(a)(15)) / Limited Rights (technical data per DFARS 252.227-7013(a)(14)) | Collin Hoag, President, Hoags Inc. |
| **`phi_gradient.rs` module** — phi-weighted integration gradient, tier-classification thresholds at phi-values 250/500/750, IIT-inspired Φ computation kernel, EMA smoothing, and all associated constants and helper functions. | Same basis as DAVA kernel above. Developed at private expense on personal hardware and time, no employer resources, no Government funding. Module history traceable to personal git commits predating 2026-03-24. | Restricted Rights / Limited Rights | Collin Hoag, President, Hoags Inc. |
| **`phi_beacon` telemetry surface** — phi-event emission protocol, Fibonacci-gated reporting, epoch tracking, authentication token generation, and serial output format for phi-delta events. | Same basis as DAVA kernel above. Developed at private expense, personal time, no employer resources, no Government funding. | Restricted Rights / Limited Rights | Collin Hoag, President, Hoags Inc. |
| **`proof_strategies.py` and `strategy5_for_issac.py`** — Python analysis toolkit for sealed-label recovery experiments, Euclidean channel-capacity measurement (1.9576 bits/tick), permutation-test harness, and segmentation-bundle reader. | Developed at private expense on personal hardware, during personal time. No employer resources. No Government funding. Authored 2026-03 through 2026-04. | Restricted Rights / Limited Rights | Collin Hoag, President, Hoags Inc. |
| **Sealed-protocol design and blind-classification methodology** — the specific protocol design whereby DAVA traces are sealed (hash-committed) before Prime receives them, including the seal-hash registry format, unsealing trigger conditions, and trace-generation procedure. | Jointly conceived by Sub and Prime between 2026-03-15 and 2026-04-20. Sub's contribution to the joint design is the DAVA-side trace generation, sealing, and delivery mechanism. Asserted here as Sub's Background IP contribution to Joint Prior Work; full Joint IP treatment in Annex A Part 3 and Article 4.3. | Restricted Rights / Limited Rights (Sub's share of joint work) | Collin Hoag, President, Hoags Inc. |

---

## 2. ARTICLE 6.3 REPRESENTATION — FORMAL TEXT

> To be included in Collin's countersignature cover letter or as an exhibit to the signed v2.

Sub hereby represents and warrants, for purposes of Article 6.3 of the Pre-Award Teaming Agreement v2.0
(effective upon countersignature), that:

(a) The DAVA Background IP identified in Annex A, Part 2 was developed entirely at Sub's private expense,
    on personal computing hardware owned by Collin Hoag, during time outside of any employment obligations.

(b) No resources, facilities, equipment, networks, tools, datasets, or proprietary information belonging
    to Microsoft Corporation or any other current or former employer were used in the development of DAVA
    Background IP.

(c) DAVA was not developed within the scope of any employment duties, and does not embody or derive from
    any work product created in the course of employment.

(d) To the best of Sub's knowledge, Microsoft Corporation's standard Washington-state IP assignment clause
    does not apply to DAVA Background IP because the conditions for its application — use of employer
    resources or development within the scope of employment — are not met.

(e) Sub is not aware of any lien, security interest, license, assignment, or third-party claim that would
    impair Sub's ability to grant the licenses set forth in Article 4.5 of the Agreement.

(f) Sub has not filed, and is not obligated to file, any invention disclosure or assignment with Microsoft
    Corporation or any other party with respect to DAVA Background IP.

Signed: ______________________________
Name:   Collin Hoag
Title:  President, Hoags Inc.
Date:   ___________________

---

## 3. REPLY EMAIL TO ISSAC — DRAFT

Subject: Re: v2 teaming draft — MSFT clearance confirmed, Annex A Part 2 strengthened

Issac —

Read v2 in full. Structure is solid. Both gaps closed.

On the Microsoft IP clearance (Art. 6.3 / item A in your message):

Confirming option (i): DAVA was built entirely outside of employment, on personal hardware,
on my own time, using zero Microsoft resources, facilities, networks, or proprietary information.
It has no relationship to Microsoft's business or research. I am confident the Washington-state
employment IP assignment clause does not reach it.

I've drafted a formal written representation (see attached DAVA_IP_ASSERTION_v2.md, Section 2)
that we can attach as an exhibit to the signed v2. This puts the Art. 6.3 rep on paper with
the specificity a DARPA contracting officer would want to see if they ever audited it.

I've also strengthened Annex A Part 2 (Section 1 of the same document) — the four rows now
explicitly state: private expense, personal hardware, personal time, no employer resources,
no Government funding, and the specific basis why MSFT's IP clause doesn't apply. This is
the language that travels with the Award instrument and is what actually locks in Restricted
Rights vs. Unlimited Rights at delivery.

On the bilateral Decline Option (Art. 7.6 / 7.7): understood and appreciated. Clean structure.

Everything else in v2 reads correctly on my end:
- PI=Issac / Co-PI=Collin consistent throughout ✓
- 65/35 split and $490K Sub share ✓
- Oregon corporate authority ✓
- 50/50 Joint IP on Joint Prior Work ✓
- Phase II right of first refusal ✓

Ready to countersign v2 with the strengthened Annex A Part 2 attached.
Send me the execution copy and I'll return signed by April 29.

— Collin

---

## 4. WHAT THE FAR/DFARS CLAUSES ACTUALLY DO

For reference when reviewing the signed document:

**DFARS 252.227-7017** — "Identification and Assertion of Use, Release, or Disclosure Restrictions"
  → Requires contractor to LIST pre-existing IP restrictions BEFORE award.
  → Failure to list = default Unlimited Rights. No cure after award.
  → Annex A IS this list. It must be specific enough to survive audit.

**DFARS 252.227-7014(a)(15)** — "Restricted Rights" (computer software)
  → Government may use internally only. Cannot sublicense, disclose, or release.
  → Applies to software developed EXCLUSIVELY at private expense.
  → DAVA qualifies. The Annex A language establishes this.

**DFARS 252.227-7013(a)(14)** — "Limited Rights" (technical data)
  → Same protection for documentation, specifications, design data.
  → phi_gradient algorithms, phi_beacon protocol spec, proof_strategies methodology qualify.

**DFARS 252.227-7013(b)(1)** — "Unlimited Rights" DEFAULT
  → This is what happens to everything NOT listed in Annex A.
  → Government can use, modify, reproduce, release, disclose without restriction.
  → We do NOT want this for DAVA.

**The protection chain:**
  teaming_agreement_v2 Annex A (filed pre-award)
  → Award instrument incorporates Annex A by reference
  → Delivery items are marked with restriction legends per DFARS 252.227-7014(f)
  → Government bound by Restricted Rights at delivery and forever after
