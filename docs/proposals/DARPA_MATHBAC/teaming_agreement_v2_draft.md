# PRE-AWARD TEAMING AGREEMENT AND INTELLECTUAL PROPERTY ASSIGNMENT

**Version:** 2.0 (supersedes `teaming_agreement_v1_signed.pdf` and `ip_carveout_v1_signed.pdf` upon mutual execution)
**Drafted:** 2026-04-20
**Deadline for execution:** 2026-04-29 (one day before DARPA-PA-26-05 submission close 2026-04-30)
**Status:** DRAFT — subject to both parties' legal review

---

## PARTIES

**Prime Contractor ("Prime"):**
Issac D. Davis, sole proprietor
SAM UEI: J4NXHM6N5F59
CAGE Code: 1EXD5 (ACTIVE through 2026-04-13 renewal cycle)
Address: Port Angeles, WA
Notices: issdandavis@proton.me (primary); issdandavis7795@gmail.com (secondary)

**Subcontractor ("Sub"):**
Hoags Inc., an Oregon corporation
SAM UEI: DUHWVUXFNPV5
CAGE Code: 15XV5
Address: Eugene, OR
Signatory: Collin Hoag, President
Notices: collinhoag@hoagsandfamily.com

(Prime and Sub each a "Party," collectively the "Parties.")

---

## RECITALS

**A.** Prime has, since prior to 2026-04-01, developed and owns the **SCBE-AETHERMOORE** platform, including but not limited to its 14-layer governance pipeline, Langues Weighting System (LWS), Sacred Tongues tokenizer, Poincaré-ball hyperbolic embedding stack, harmonic wall formula *H(d,pd) = 1/(1 + d_H + 2·pd)*, audio-axis telemetry, and associated codebases in TypeScript, Python, and Rust (collectively, **"SCBE Background IP"**).

**B.** Sub has, prior to 2026-04-01, developed and owns the **DAVA** bare-metal Rust kernel, including its phi-weighted gradient instrumentation (`phi_gradient.rs`), tier-classification thresholds at phi-values 250/500/750, `phi_beacon` telemetry surface, and the `proof_strategies.py` / `strategy5_for_issac.py` analysis toolkit (collectively, **"DAVA Background IP"**).

**C.** Between 2026-03-15 and 2026-04-20, Prime and Sub conducted a jointly designed blind-classification protocol yielding 24/24 = 100% sealed-label recovery on DAVA traces with permutation-test *p ≤ 3.00×10⁻⁴*, Euclidean channel-capacity measurement of 1.9576 bits/tick against a log₂(4) = 2.0000-bit ceiling (97.9% recovery), and companion segmentation-layer measurements at 1.5761 and 2.9818 bits/tick against alternative ground-truth labels. The protocol design, seal hashes, and result artifacts constitute **"Joint Prior Work"**.

**D.** DARPA issued Special Notice **DARPA-SN-26-59** ("MATHBAC — Mathematical Foundations of Agentic Artificial Intelligence Behaviors and Communication") on 2026-03-24, with Proposers Day 2026-04-21 and companion Program Announcement **DARPA-PA-26-05** closing 2026-04-30 for Technical Area 1 (TA1) abstracts.

**E.** The Parties desire to formalize, prior to proposal submission, their respective roles, cost shares, and intellectual-property positions for any prospective award under DARPA-PA-26-05, in a form that (i) satisfies 35 U.S.C. §§ 200–212 (Bayh-Dole), (ii) complies with FAR 52.227-11 and DFARS 252.227-7013, -7014, and -7017, (iii) aligns with NIST AI RMF 1.0 and ISO/IEC 42001:2023 governance expectations, and (iv) preserves each Party's right to decline without prejudice prior to submission.

**NOW, THEREFORE**, in consideration of the mutual covenants below, the Parties agree:

---

## ARTICLE 1 — DEFINITIONS

**1.1** "**Agreement**" means this Pre-Award Teaming Agreement and Intellectual Property Assignment, including all Annexes.

**1.2** "**Background IP**" means intellectual property, in any form, owned or controlled by a Party as of the Effective Date, including without limitation the SCBE Background IP and the DAVA Background IP.

**1.3** "**Foreground IP**" means intellectual property conceived, reduced to practice, authored, or otherwise first fixed in tangible form by either Party during the Term in the course of performance under this Agreement.

**1.4** "**Joint IP**" means Foreground IP to which both Parties contributed inventive or authorial content such that, under 35 U.S.C. § 116 (joint inventorship) or 17 U.S.C. § 101 (joint works), both Parties would be entitled to be named as co-inventors or co-authors.

**1.5** "**Government**" means the United States, acting through the Defense Advanced Research Projects Agency (DARPA) or successor funding agency.

**1.6** "**Government Rights**" means the license rights accorded to the Government by operation of law under FAR 52.227-11, DFARS 252.227-7013, DFARS 252.227-7014, DFARS 252.227-7018, and 35 U.S.C. § 202(c).

**1.7** "**Solicitation**" means DARPA-SN-26-59 and DARPA-PA-26-05 collectively, and any successor program announcement for MATHBAC TA1.

**1.8** "**Effective Date**" means the date of the last Party signature in the block below Article 12.

**1.9** "**Award**" means execution of a prime-contract instrument between Prime and the Government funding work described in the proposal submitted under the Solicitation.

**1.10** "**Statement of Work**" or "**SoW**" means the division of Phase I task responsibilities set forth in **Annex C**.

---

## ARTICLE 2 — ROLES

**2.1 Prime.** Prime shall serve as the prime contractor and principal investigator ("PI") for the proposal and any resulting Award. Prime retains sole authority over:
  (a) final proposal content and submission;
  (b) communications with the DARPA Program Manager and Contracting Officer;
  (c) technical direction of the research program, subject to Sub's SoW scope in **Annex C**;
  (d) publication decisions, subject to Article 4.6.

**2.2 Sub.** Sub shall serve as a subcontractor and Co-Principal Investigator ("Co-PI") for the tasks set forth in **Annex C**, which include:
  (a) DAVA kernel instrumentation and telemetry delivery for Phase I Deliverable #3;
  (b) reproduction of the Euclidean-approximation baseline of 1.9576 bits/tick using `strategy5_for_issac.py` against segmentation-committed bundles;
  (c) independent replication of the hyperbolic `d_H` swap measurement in Prime's pipeline;
  (d) joint authorship of any publication drawing on Joint Prior Work or Joint IP.

**2.3 No partnership.** The Parties are independent contractors. No provision of this Agreement creates a partnership, joint venture, or agency relationship between them.

---

## ARTICLE 3 — BUDGET AND COST STRUCTURE

**3.1 Headline split.** Of any Phase I Award proceeds received by Prime from the Government, Prime shall receive **sixty-five percent (65%)** and Sub shall receive **thirty-five percent (35%)**, inclusive of direct labor, indirect burdens, and fee.

**3.2 Pass-through.** Amounts payable to Sub shall be treated as a pass-through subcontract cost in Prime's accounting under FAR 31.205, without markup by Prime, consistent with DCAA Contract Audit Manual § 6-609 (provisional billing rates).

**3.3 Fee.** Each Party's fee component shall be computed per DFARS 215.404-4 weighted-guidelines methodology, targeting a combined program fee of ten percent (10%) of direct cost, consistent with the norm range of 7–15% for DoD small-business R&D awards.

**3.4 Indirect rates.** Each Party shall use its own provisional indirect rates, disclosed to Prime's contract file per DCAA guidance. Sub shall provide its then-current rate letter (or sole-proprietor indirect-rate equivalent) to Prime within fifteen (15) calendar days of Award.

**3.5 Cost envelope.** The budget contemplated by the proposal is approximately **one million four hundred thousand U.S. dollars ($1,400,000)** total for a twelve-month Phase I period of performance, itemized in **Annex F**. Prime reserves the right to adjust line items prior to submission; the 65/35 headline split shall remain fixed absent written agreement.

**3.6 Phase II.** In the event the Government invites a Phase II continuation, the Parties shall negotiate in good faith a Phase II budget. Sub shall have a right of first refusal to serve as Phase II subcontractor on tasks substantially similar to its Phase I SoW; this right expires thirty (30) days after Prime notifies Sub in writing of the Phase II opportunity.

---

## ARTICLE 4 — INTELLECTUAL PROPERTY

**4.1 Background IP retained.** Each Party retains full, exclusive ownership of its Background IP. Nothing in this Agreement transfers, assigns, or licenses Background IP except as expressly set forth in this Article.

**4.1.1** Prime's Background IP, including SCBE Background IP, is identified with specificity in **Annex A, Part 1**, and is hereby asserted as having restrictions on the Government's rights pursuant to **DFARS 252.227-7017**.

**4.1.2** Sub's Background IP, including DAVA Background IP, is identified with specificity in **Annex A, Part 2**, and is likewise asserted pursuant to **DFARS 252.227-7017**.

**4.1.3** Both Parties acknowledge that failure to properly assert pre-existing restrictions in an Award instrument may cause pre-existing IP to be delivered under default Unlimited Rights per DFARS 252.227-7013(b)(1); the specificity of Annex A is material to this Agreement.

**4.2 Foreground IP — single-Party.** Foreground IP created solely by one Party, without contribution from the other, shall be owned by the creating Party. The creating Party grants the other Party a non-exclusive, royalty-free, worldwide license to use such Foreground IP solely for performance of this Agreement and any resulting Award.

**4.3 Joint IP.** Joint IP shall be owned by the Parties as **undivided co-owners in equal shares (50/50)**, each with the right to exploit, license, assign, and enforce without accounting to the other, subject only to (a) the Government Rights accruing under law, (b) the publication review in Article 4.6, and (c) the non-compete in Article 4.8. This allocation is consistent with 35 U.S.C. § 262 (joint owners of patents) and 17 U.S.C. § 201(a) (joint authors of works).

**4.4 Government Rights.**
  (a) For Foreground IP developed exclusively with Government funds, the Government shall receive **Unlimited Rights** per DFARS 252.227-7013(b)(1) and 252.227-7014(b)(1).
  (b) For Foreground IP developed with mixed Government and private funds, the Government shall receive **Government Purpose Rights** for a period of five (5) years from execution of the funding instrument, converting to Unlimited Rights thereafter, per DFARS 252.227-7013(b)(2) and 252.227-7014(b)(2).
  (c) For Background IP delivered or accessed under an Award, the Government shall receive only **Limited Rights** per DFARS 252.227-7013(a)(14) (technical data) and **Restricted Rights** per DFARS 252.227-7014(a)(15) (computer software), as asserted in Annex A.
  (d) If, post-award, the Award is classified or redesignated as a Small Business Innovation Research (SBIR) award, the **twenty (20)-year SBIR data-rights period** under 15 U.S.C. § 638(j)(2) and DFARS 252.227-7018 shall attach to qualifying data, superseding (a) and (b) to the extent of any conflict.

**4.5 Inter-Party licenses.**
  (a) Prime grants Sub a non-exclusive, royalty-free, worldwide, revocable license to Prime's Background IP **solely** for performance of Sub's Annex C SoW and for use in Joint Prior Work publication and follow-on replication. This license terminates upon termination of this Agreement except with respect to Joint Prior Work already made public.
  (b) Sub grants Prime the reciprocal license to Sub's Background IP on identical terms.
  (c) Neither Party shall sublicense the other Party's Background IP without prior written consent.

**4.6 Publication and credit.**
  (a) Either Party may propose a publication drawing on Joint Prior Work, Joint IP, or mixed Background IP. The proposing Party shall provide the other Party with the manuscript not less than **thirty (30) calendar days** before submission for external review, publication, or preprint posting.
  (b) The reviewing Party may request redactions limited to (i) genuinely confidential Background IP, (ii) export-controlled content, and (iii) factual corrections. The reviewing Party may not withhold consent to publication except on these grounds.
  (c) Authorship order for publications drawing on Joint Prior Work or Joint IP shall list Issac D. Davis as corresponding author and first author for work led by Prime, and Collin Hoag as corresponding author and first author for work led by Sub. Joint-lead work shall use co-first-authorship convention (alphabetical by surname; "Davis, I. D.; Hoag, C." with equal-contribution footnote).
  (d) Neither Party shall issue a press release, LinkedIn post, or media communication referencing the Solicitation, the Award, or Joint Prior Work without prior written consent of the other Party, such consent not to be unreasonably withheld.

**4.7 Patent filings.** Either Party may file patent applications covering its own Background IP or single-Party Foreground IP without consent. Patent applications covering Joint IP shall be filed jointly, with costs split 65/35 and decision authority held jointly; either Party may, on thirty (30) days' notice, assume sole filing authority if the other declines to participate, in which case the declining Party retains a non-exclusive, royalty-free license but forfeits enforcement rights.

**4.8 Non-compete (narrow).** For the Term and for twelve (12) months thereafter, neither Party shall submit a competing proposal to the Solicitation or any substantially equivalent DARPA announcement under MATHBAC TA1 without the other Party's written consent. This Article 4.8 does not restrict:
  (a) proposals to DARPA announcements outside MATHBAC;
  (b) proposals to non-DARPA Government agencies;
  (c) academic publications or commercial products based on single-Party Background IP;
  (d) work under this Agreement's **Decline Option** in Article 7.6.

---

## ARTICLE 5 — EXPORT CONTROL AND COMPLIANCE

**5.1 Preliminary export classification.** The Parties preliminarily classify SCBE and DAVA technical data and software under the Export Administration Regulations (EAR) at **ECCN 5D002** (information security software) with possible **0Y521** designation for emerging technology, 15 C.F.R. Part 774. Neither Party has classified any component under the International Traffic in Arms Regulations (ITAR), 22 C.F.R. Parts 120–130.

**5.2 CCATS filing.** Within thirty (30) days of any Award, Prime shall file a Commodity Classification Automated Tracking System (CCATS) request with the Bureau of Industry and Security (BIS) for formal ECCN determination. Sub shall cooperate by providing technical descriptions of DAVA components within ten (10) business days of request.

**5.3 Foreign-national access.** Neither Party shall grant access to technical data delivered under an Award to any foreign national absent (a) BIS deemed-export license or license exception, and (b) written notice to the other Party.

**5.4 AI governance alignment.** The Parties shall maintain good-faith alignment with (i) the **NIST AI Risk Management Framework 1.0** (Govern/Map/Measure/Manage functions), (ii) **ISO/IEC 42001:2023** (AI management systems), and (iii) the cryptographic-module provisions of **NIST SP 800-53 Rev. 5, Control SC-13**.

**5.5 Section 889 compliance.** Each Party represents it does not use covered telecommunications equipment or services prohibited by Section 889 of the FY2019 NDAA, 41 U.S.C. § 3901 note, and will provide the certification required at FAR 52.204-24/-25/-26 upon request.

---

## ARTICLE 6 — REPRESENTATIONS AND WARRANTIES

Each Party represents and warrants to the other that:

**6.1** It has full power and authority to enter into this Agreement.

**6.2** Its entry into this Agreement does not conflict with any other agreement, grant, or obligation to which it is bound.

**6.3** It owns or has sufficient rights in its Background IP to grant the licenses set forth in Article 4.5, free of any lien, security interest, or third-party claim that would impair such grant.

**6.4** Its SAM registration is active and its CAGE code is current as of the Effective Date; it shall maintain both through any Term of Award.

**6.5** No person proposed to work on the project is barred, suspended, or proposed for debarment under FAR 9.4 or corresponding DoD regulations.

**6.6** To the best of its knowledge, no component of its Background IP was developed with foreign-government funding that would create undisclosed foreign IP claims.

**6.7** It has not entered into any conflicting teaming arrangement with a third party for the Solicitation.

---

## ARTICLE 7 — TERM AND TERMINATION

**7.1 Effective Date.** This Agreement takes effect on the date of last signature below.

**7.2 Pre-Award Term.** The "Pre-Award Term" runs from the Effective Date until the earlier of (a) execution of a prime-contract instrument by Prime with the Government pursuant to the Solicitation, or (b) 2026-09-30 if no Award is made, or (c) written notice from DARPA that no Award will be made.

**7.3 Post-Award Term.** Upon Award, this Agreement shall automatically convert to a Subcontract Agreement on the terms of **Annex E**, which the Parties shall execute within fifteen (15) business days of the Award date. If Annex E cannot be finalized within forty-five (45) business days of Award, either Party may terminate per Article 7.5.

**7.4 Termination for cause.** Either Party may terminate this Agreement for material breach by the other, upon thirty (30) days' written notice specifying the breach, if the breaching Party fails to cure within the notice period. Uncured material breach includes (a) failure to deliver Annex C tasks more than thirty days past a milestone, (b) breach of confidentiality in Article 8, (c) breach of Article 4 IP provisions, or (d) misrepresentation in Article 6.

**7.5 Termination for convenience.** Either Party may terminate this Agreement for convenience on sixty (60) days' written notice; in the event of such termination, the terminating Party shall pay the other Party for work performed and costs properly incurred through the termination date, pro rata to the 65/35 split for any Award proceeds already received and allocable to the terminated scope.

**7.6 DECLINE OPTION (pre-submission).** Notwithstanding any other provision, **Sub may elect not to be named in the proposal submitted under DARPA-PA-26-05 by delivering written notice to Prime not later than 23:59 Pacific Time on 2026-04-29** ("Decline Notice"). Upon timely Decline Notice:
  (a) this Agreement terminates without penalty to either Party;
  (b) Sub retains all Background IP, including DAVA Background IP, unencumbered;
  (c) Prime retains the sole right to submit the proposal without reference to Sub as a team member, provided that Prime shall not represent Joint Prior Work as sole-authored;
  (d) the publication provisions of Article 4.6 and the Joint IP provisions of Article 4.3 survive with respect to Joint Prior Work already in existence;
  (e) the non-compete in Article 4.8 does not apply;
  (f) neither Party shall make disparaging statements regarding the other's decision.

The Decline Option is offered in recognition of Sub's independent business interests and the short runway before the 2026-04-30 submission deadline.

**7.7 Prime's decline option.** Prime may similarly elect not to submit a proposal, by delivering written notice to Sub not later than 23:59 Pacific Time on 2026-04-29, with equivalent pre-termination effect and survival provisions.

**7.8 Survival.** Articles 1 (Definitions), 4 (IP), 5 (Export Control — ongoing obligations), 8 (Confidentiality), 9 (Indemnification), 10 (Dispute Resolution), and 11 (Miscellaneous) survive termination.

---

## ARTICLE 8 — CONFIDENTIALITY

**8.1 Mutual obligation.** Each Party shall hold in confidence all non-public information disclosed by the other Party that is marked as confidential or that a reasonable business person would understand to be confidential ("**Confidential Information**"), and shall use it solely for performance of this Agreement.

**8.2 Standard of care.** Each Party shall use at least the same degree of care to protect the other's Confidential Information as it uses to protect its own, but in no event less than reasonable care.

**8.3 Exceptions.** Confidential Information does not include information that:
  (a) was in the receiving Party's possession prior to disclosure, without confidentiality obligation;
  (b) is or becomes publicly available without breach of this Agreement;
  (c) is independently developed without use of the disclosing Party's Confidential Information;
  (d) is received from a third party without confidentiality obligation and without breach of any duty; or
  (e) is required to be disclosed by law, court order, or Government request, provided the receiving Party gives prompt notice to the disclosing Party and cooperates in seeking protective treatment.

**8.4 Term.** The confidentiality obligation survives for **five (5) years** following termination of this Agreement.

---

## ARTICLE 9 — INDEMNIFICATION

**9.1 Mutual indemnity.** Each Party ("**Indemnitor**") shall defend, indemnify, and hold harmless the other Party ("**Indemnitee**") from and against third-party claims, damages, and reasonable attorneys' fees to the extent arising from Indemnitor's (a) gross negligence or willful misconduct, (b) breach of Article 6 representations, or (c) infringement of third-party intellectual property by Indemnitor's Background IP.

**9.2 Procedure.** Indemnitee shall provide prompt written notice of any claim, tender control of the defense to Indemnitor (with Indemnitee's right to participate with its own counsel at its own expense), and cooperate reasonably. Indemnitor shall not settle any claim imposing non-monetary obligations on Indemnitee without Indemnitee's prior written consent.

**9.3 Cap.** Each Party's aggregate liability under this Agreement, including under Article 9, shall not exceed the total consideration actually received by that Party under any Award, except for breaches of confidentiality (Article 8), willful IP misappropriation (Article 4), or willful misconduct, which are not subject to this cap.

**9.4 No consequential damages.** Neither Party shall be liable for consequential, incidental, special, indirect, or punitive damages, excepting the carve-outs in Article 9.3.

---

## ARTICLE 10 — DISPUTE RESOLUTION

**10.1 Good-faith negotiation.** In the event of any dispute, the Parties shall first attempt resolution by good-faith negotiation between the signatories for a period of at least thirty (30) days.

**10.2 Mediation.** If negotiation fails, the Parties shall submit the dispute to non-binding mediation under the **Commercial Mediation Rules of the American Arbitration Association (AAA)**, with the mediator selected by agreement.

**10.3 Arbitration.** If mediation does not resolve the dispute within sixty (60) days of commencement, either Party may submit the dispute to binding arbitration under the **Commercial Arbitration Rules of the AAA**, seated in Seattle, Washington, before a single arbitrator. The arbitrator's award shall be final and enforceable in any court of competent jurisdiction.

**10.4 Equitable relief.** Notwithstanding Articles 10.1–10.3, either Party may seek injunctive or equitable relief in any court of competent jurisdiction to prevent or remedy breach of Article 4 (IP) or Article 8 (Confidentiality).

**10.5 Governing law.** This Agreement is governed by the substantive law of the State of Washington (as the Prime's state of business), without regard to conflict-of-laws principles, except that (a) Oregon law governs matters of Sub's internal corporate authority and (b) Federal law governs Government Rights, Bayh-Dole, DFARS assertions, and export control, as applicable.

**10.6 Attorney's fees.** In any action to enforce this Agreement, the prevailing Party shall be entitled to recover reasonable attorneys' fees and costs.

---

## ARTICLE 11 — MISCELLANEOUS

**11.1 Entire agreement.** This Agreement, including all Annexes, constitutes the entire agreement between the Parties with respect to the Solicitation and supersedes all prior or contemporaneous agreements, including the `teaming_agreement_v1_signed.pdf` and `ip_carveout_v1_signed.pdf` of 2026-04-20, which are hereby deemed superseded effective the Effective Date of this Agreement.

**11.2 Amendments.** No amendment is effective unless in writing and signed by both Parties.

**11.3 Severability.** If any provision is held unenforceable, the remainder shall continue in full force and effect; the Parties shall negotiate in good faith a substitute provision approximating the economic and legal intent of the unenforceable provision.

**11.4 Assignment.** Neither Party may assign this Agreement without the other's prior written consent, except that either Party may assign to a successor entity in a merger, acquisition, or sale of substantially all assets, provided the successor assumes all obligations in writing.

**11.5 Notices.** Notices shall be in writing and sent (a) by email to the addresses in the Parties block (with delivery receipt or follow-up confirmation), (b) by registered or certified U.S. mail, or (c) by nationally recognized courier. Notice is effective on receipt.

**11.6 Counterparts; electronic signatures.** This Agreement may be executed in counterparts and by electronic signature (including PDF-scanned manual signatures and DocuSign/Adobe Sign), each of which is an original; together they constitute one instrument, per the Electronic Signatures in Global and National Commerce Act, 15 U.S.C. § 7001 *et seq.*

**11.7 Force majeure.** Neither Party is liable for delay caused by acts of God, war, terrorism, pandemic, government action, or other causes beyond its reasonable control, provided it gives prompt notice and uses reasonable efforts to resume performance.

**11.8 No third-party beneficiaries.** Except for the Government's rights under Article 4.4, this Agreement creates no rights in any third party.

**11.9 Debarment.** Each Party represents it is not currently debarred, suspended, or proposed for debarment from Federal contracting, and shall notify the other Party within five (5) business days of any such action.

**11.10 Joint drafting.** This Agreement has been drafted jointly by the Parties with opportunity for legal review; no presumption shall be applied against either Party as the drafter.

---

## ARTICLE 12 — SIGNATURES

**IN WITNESS WHEREOF**, the Parties have executed this Agreement as of the dates below.

**PRIME:**

Signature: ______________________________
Name: Issac D. Davis
Title: Sole Proprietor
Date: _______________________

**SUBCONTRACTOR:**

Signature: ______________________________
Name: Collin Hoag
Title: President, Hoags Inc.
Date: _______________________

---

# ANNEX A — DFARS 252.227-7017 ASSERTIONS

*Per DFARS 252.227-7017, each Party identifies below the technical data and computer software for which it asserts restrictions on the Government's rights.*

## Part 1 — Prime's (Issac D. Davis) Assertions

| (1) Technical Data or Software to be Furnished With Restrictions | (2) Basis for Assertion | (3) Asserted Rights Category | (4) Name of Person Asserting Restrictions |
|---|---|---|---|
| SCBE-AETHERMOORE 14-layer pipeline (TypeScript canonical; Python reference; Rust experimental), including source, compiled artifacts, and layer-specific modules L1–L14 | Developed at private expense, 2024–2026, no Government funding; public commits predate 2026-03-24 SN issuance | Restricted Rights (software) / Limited Rights (technical data) | Issac D. Davis |
| Langues Weighting System (LWS) specification and implementation, including Sacred Tongues tokenizer (KO, AV, RU, CA, UM, DR with phi-scaled weights) | Developed at private expense, 2024–2026; published under KDP ASIN B0GSSFQD9G as *The Six Tongues Protocol* (timestamped prior art) | Restricted Rights / Limited Rights | Issac D. Davis |
| Harmonic wall formula *H(d, pd) = 1/(1 + d_H + 2·pd)* and reference implementations in TypeScript and Python | Developed at private expense, 2025–2026; disclosed in USPTO Provisional 63/961,403 | Restricted Rights / Limited Rights | Issac D. Davis |
| Audio-axis telemetry stack and vacuum-acoustics modules | Developed at private expense, 2025–2026 | Restricted Rights / Limited Rights | Issac D. Davis |
| PHDM (Polyhedral Hyperbolic Defense Manifold) and associated crypto primitives (ML-KEM-768, ML-DSA-65 integration) | Developed at private expense, 2025–2026; library integrations use open-source primitives with permissive licenses | Restricted Rights / Limited Rights | Issac D. Davis |

## Part 2 — Sub's (Hoags Inc.) Assertions

| (1) Technical Data or Software to be Furnished With Restrictions | (2) Basis for Assertion | (3) Asserted Rights Category | (4) Name of Person Asserting Restrictions |
|---|---|---|---|
| DAVA bare-metal Rust kernel, including source and compiled artifacts | Developed at private expense, 2024–2026, no Government funding | Restricted Rights / Limited Rights | Collin Hoag, Hoags Inc. |
| `phi_gradient.rs` module and phi-value tier thresholds (250/500/750) | Developed at private expense, 2025–2026 | Restricted Rights / Limited Rights | Collin Hoag, Hoags Inc. |
| `phi_beacon` telemetry surface and sealed-trace generation protocol | Developed at private expense, 2025–2026 | Restricted Rights / Limited Rights | Collin Hoag, Hoags Inc. |
| `proof_strategies.py` and `strategy5_for_issac.py` analysis tooling | Developed at private expense, 2026 | Restricted Rights / Limited Rights | Collin Hoag, Hoags Inc. |

## Part 3 — Joint Prior Work (not asserted as restricted but expressly identified)

| Item | Creation Dates | Rights |
|---|---|---|
| Joint blind-classification protocol design, seal-hash registry, 24/24 sealed-label result, permutation test *p ≤ 3.00×10⁻⁴* | 2026-03-15 through 2026-04-20 | 50/50 Joint IP per Article 4.3 |
| Joint Euclidean/hyperbolic capacity comparison methodology | 2026-04-14 through 2026-04-20 | 50/50 Joint IP per Article 4.3 |

*This Annex A is incorporated into the proposal submitted under DARPA-PA-26-05 as the pre-award DFARS 252.227-7017 assertions list. Any Award instrument shall incorporate this Annex A by reference.*

---

# ANNEX B — CONFIDENTIALITY (supplemental to Article 8)

*No additional terms; Article 8 governs in full.*

---

# ANNEX C — STATEMENT OF WORK (PHASE I)

## C.1 Phase I overview

Twelve-month period of performance; five deliverables; joint research program under Prime's technical direction with Sub as Co-PI.

## C.2 Prime (Issac D. Davis) tasks

**C.2.1 (Task 1 / Deliverable #1).** Formalize the geometric upper bound C*(κ, D, K) as a Working Hypothesis with falsifiable tests; prepare a technical memo suitable for peer review.

**C.2.2 (Task 2 / Deliverable #2).** Execute the `d_H` swap in `_assign_realm()` replacing Euclidean distance with true Poincaré hyperbolic distance; produce side-by-side channel-capacity measurements against both realm labels and `tier_code` ground truth.

**C.2.3 (Task 4 / Deliverable #4).** Extend the PSU(1,1) Möbius equivariance result from 2D (Test B 5-seed bit-identical) to PSU(1,2) 3D pre-embed; document group-action correctness proofs.

**C.2.4 (Task 5 / Deliverable #5).** Prepare joint paper draft for peer review (venue TBD; target: NeurIPS 2026 workshop or equivalent).

## C.3 Sub (Hoags Inc.) tasks

**C.3.1 (Supporting Task 2 / Deliverable #3).** Run `strategy5_for_issac.py` on the committed segmentation bundle to reproduce the 1.9576 bits/tick Euclidean baseline; deliver raw outputs, seed list, and reproduction script.

**C.3.2 (Supporting Task 3).** Generate a fresh 100-trace × 10K-tick blind replication set with HYPERVIGILANCE and DISSOCIATION regimes added, holding seeds independent of Prime's access; deliver sealed hashes on receipt, unsealed traces after Prime submits classification outputs.

**C.3.3 (Supporting Task 5).** Contribute co-authored sections on DAVA kernel architecture, phi-thresholds, and sealed-protocol design to the joint paper draft.

## C.4 Milestone schedule

| Month | Milestone | Party |
|---|---|---|
| 1 | Kickoff; rate letters exchanged; Annex A filed with DARPA | Both |
| 2 | Euclidean baseline reproduced; `d_H` swap design review | Sub / Prime |
| 4 | `d_H` swap implemented; initial hyperbolic capacity measurement | Prime |
| 5 | 100-trace replication set delivered | Sub |
| 7 | PSU(1,2) pre-embed correctness proofs | Prime |
| 9 | Joint paper first draft circulated | Both |
| 11 | Final technical report to DARPA | Prime |
| 12 | Close-out; Phase II go/no-go decision | Both |

---

# ANNEX D — PUBLICATION AND CREDIT POLICY

## D.1 Author order

Joint Prior Work and Joint IP publications shall list authors per Article 4.6(c). Authorship footnote shall include: "I.D.D. and C.H. contributed equally to this work" where applicable.

## D.2 Affiliations

  - Issac D. Davis, SCBE-AETHERMOORE (Port Angeles, WA)
  - Collin Hoag, Hoags Inc. (Eugene, OR)

## D.3 Grant acknowledgment

Post-Award publications shall include: "This material is based upon work supported by the Defense Advanced Research Projects Agency under Contract No. [AWARD NUMBER]. Any opinions, findings, and conclusions or recommendations expressed in this material are those of the authors and do not necessarily reflect the views of DARPA or the U.S. Government."

## D.4 Preprint policy

Preprints to arXiv, OSF, or equivalent are permitted after the thirty (30)-day review window of Article 4.6(a) elapses, unless export-control concerns require delay.

---

# ANNEX E — POST-AWARD SUBCONTRACT TERM SHEET (to be formalized on Award)

**E.1** Sub becomes a fixed-price-with-incentive-fee subcontractor to Prime, with payment milestones tied to Annex C deliverables.

**E.2** FAR/DFARS flowdown clauses applicable to subcontracts at the subcontract's dollar threshold shall be incorporated by reference, including at minimum:
  - FAR 52.203-13 (Contractor Code of Business Ethics)
  - FAR 52.204-25 (Prohibition on Covered Telecommunications)
  - FAR 52.219-8 (Utilization of Small Business Concerns)
  - FAR 52.222-26 (Equal Opportunity)
  - FAR 52.225-13 (Restrictions on Certain Foreign Purchases)
  - DFARS 252.204-7012 (Safeguarding Covered Defense Information)
  - DFARS 252.227-7013, -7014, -7017, -7018 (data and software rights; assertions; SBIR if applicable)

**E.3** Subcontract dollar value: thirty-five percent (35%) of Award value, subject to Article 3.

**E.4** Payment terms: net thirty (30) days from Prime's receipt of DARPA funds for the invoiced milestone.

**E.5** The Parties shall execute the full Subcontract Agreement within fifteen (15) business days of Award per Article 7.3.

---

# ANNEX F — BUDGET DETAIL (PRE-SUBMISSION ESTIMATE)

*Subject to DARPA cost-volume requirements and finalization by 2026-04-29.*

| Line Item | Total ($) | Prime Share (65%) | Sub Share (35%) |
|---|---:|---:|---:|
| Direct labor | 420,000 | 273,000 | 147,000 |
| Computing (GPU hours, cloud) | 100,000 | 75,000 | 25,000 |
| Travel (2× DARPA reviews, 1× conference) | 30,000 | 20,000 | 10,000 |
| Materials & supplies | 40,000 | 26,000 | 14,000 |
| Subcontract pass-through | n/a (internalized) | n/a | n/a |
| **Direct total** | **590,000** | **394,000** | **196,000** |
| Indirect / overhead (est. 30% blended) | 177,000 | 115,000 | 62,000 |
| Subtotal | 767,000 | 509,000 | 258,000 |
| G&A (est. 10%) | 76,700 | 51,000 | 25,700 |
| Fee (10% per DFARS 215.404-4) | 84,370 | 56,000 | 28,370 |
| **Contingency / reserve** | 42,000 | 28,000 | 14,000 |
| **Rounding to $1.4M target** | 29,930 | 19,000 | 10,930 |
| **TOTAL** | **1,400,000** | **910,000** | **490,000** |

*Percentages are approximate; final cost volume will rationalize line items per FAR 31.205 allowability and DCAA guidance. The 65/35 headline is binding.*

---

## END OF AGREEMENT
