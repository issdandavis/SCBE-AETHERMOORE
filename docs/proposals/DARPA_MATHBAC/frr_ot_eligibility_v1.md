# MATHBAC FRR + OT Eligibility Posture (v1)

**Solicitation:** DARPA-PA-26-05 — Mathematics of Boosting Agentic Communication (MATHBAC)
**Award instrument:** Other Transaction Agreement for Research, **10 U.S.C. §4021**
**Drafted:** 2026-04-28 (Auto Mode, sourced from public statutory and DARPA documents)
**Status:** Working artifact for Phase I full-proposal IP/employment posture section.

---

## 1. Statutory hook: §4021, not §4022

The MATHBAC PA explicitly funds via **OT for Research under 10 U.S.C. §4021**, not §4022 (prototype OT). The earlier punch-list note in `project_mathbac_proposal_spine_2026_04_21.md` referenced §4022; that is wrong for this solicitation and is being corrected here.

The two authorities differ in ways that materially affect SCBE's posture as a sole-prop prime:

| Provision | §4021 (Research OT — MATHBAC) | §4022 (Prototype OT) |
|---|---|---|
| Cost share | Discretionary: *"to the extent that the Secretary determines practicable, the funds provided by the Government … do not exceed the total amount provided by other parties."* | Hard one-third floor is one of several eligibility paths in §4022(d). |
| Nontraditional defense contractor required | **No.** §4021 has no analog to §4022(d). | Yes, unless an alternate path is met (small-business-only, ≥1/3 cost share, or senior procurement executive exception). |
| Eligible primes | Broad: "any person" / various entity types. | Same broad eligibility but gated by the (d) requirements. |
| Award sizing/approval thresholds | Not codified in statute. | $100M–$500M needs head-of-contracting-activity written determination; >$500M needs senior procurement exec + 30-day Congressional notice. |
| Follow-on production | Not the typical use. | §4022(f) provides a follow-on production pathway. |

**SCBE implication:** As a sole-prop prime applying for Phase I (≤$2M, 16 months) under §4021, **we do not need to demonstrate ≥1/3 non-federal cost share, and we do not need to be classified as a nontraditional defense contractor as a precondition of eligibility**. We may still volunteer cost share if it strengthens the proposal, but the BAA does not require it.

(Verbatim §4022 quotes are in `notes/frr_4022_4021_extracts.md` if needed for the abstract — not duplicated here.)

---

## 2. Fundamental Research Risk-Based Security Review (FRRBS / "FRR")

DARPA runs every fundamental-research proposal selected for negotiation through the FRRBS, also referred to as the Countering Foreign Influence Program (CFIP). The review is **pre-award, post-selection** — it happens during negotiation, not at submission, and is not a gate on whether you may submit.

### 2.1 Required disclosure forms

As of 2024-11-01, DARPA requires the **OSTP Common Disclosure Forms** in place of the legacy biosketch + current/pending support:

1. **Common Form for Biographical Sketch** — mandatory for the PD/PI and all designated *covered individuals*; optional but encouraged for other key personnel. Must include the ORCID Digital Persistent Identifier.
2. **Common Form for Current and Pending (Other) Support** — mandatory for **all covered individuals including the PD/PI**, covering both proposals/active projects and in-kind contributions.

These replace the SF-424/biosketch/current-and-pending stack for fundamental research.

### 2.2 Risk tiers

DARPA assigns one of four scores after reviewing the disclosure forms and publicly available federal lists:

- **Low**
- **Moderate**
- **High**
- **Very High**

Triggers include active affiliations with export-restricted institutions, participation in foreign talent recruitment programs, and "receiving funds from or has an active affiliation with entities connected to the governments of countries of concern."

### 2.3 Countries of concern (FCOC)

DARPA explicitly names four:

- **China**
- **Russia**
- **Iran**
- **North Korea**

### 2.4 Automatic disqualifiers

Two findings are auto-disqualifying without a Secretary of Defense waiver:

- Institutions hosting **Confucius Institutes**.
- Individuals participating in **Malign Foreign Talent Recruitment Programs (MFTRPs)**.

### 2.5 Mitigation pathway

For Moderate/High/Very High findings, the applicant can propose **risk-mitigation measures or alternate project personnel** to reduce the rating before award. Projects with a residual High or Very High rating require Deputy Director approval to proceed.

---

## 3. SCBE posture against the FRR rubric

This section is the operational read for our submission, not legal advice.

| Factor | SCBE-AETHERMOORE (sole prop, Issac Davis PI) | Risk read |
|---|---|---|
| Citizenship of PI | US citizen, Port Angeles WA | Low |
| Active affiliations w/ FCOC entities | None | Low |
| Foreign talent recruitment programs | None | Low |
| Confucius Institute hosting | Not applicable (no campus) | N/A |
| Foreign sources of funding | None disclosed in current/pending | Low |
| Foreign in-kind contributions | None | Low |
| Foreign sub-awardees on this proposal | None planned | Low |

**Expected FRR rating: Low.** The disclosure forms still must be filed correctly; "Low expected" is not "no filing required." Carrying SCBE through FRR is a paperwork exercise, not a substantive risk.

### 3.1 If DAVA (Collin Hoag) is a subawardee

Memory `reference_collin_hoag_dava.md` has already flagged that the public DAVA repo's "sentient AI consciousness" framing is a credibility liability for MATHBAC, and that we should reconsider the citation. From an FRR standpoint, the additional question is whether Collin or any DAVA-side covered individual has any FCOC affiliation we are unaware of. **Action item before any joint submission:** request Collin complete the OSTP Common Disclosure Forms (biosketch + current-and-pending) and confirm no MFTRP participation; we cannot underwrite his rating without that input.

---

## 4. What this means for the IP / employment-posture section of the full proposal

The MATHBAC full proposal (due 2026-06-16 @ 4pm ET) needs:

1. **Award instrument acknowledgment** — proposal volume should reference §4021 explicitly, and Annex A basis sheet should not assume the §4022 cost-share floor.
2. **Cost-share statement** — we are not required to offer cost share. If we choose to (e.g., contributed labor on the SCBE codebase), it must be valued and substantiated; otherwise we should leave it out rather than promise vapor.
3. **Covered-individual list** — at minimum: Issac Davis (PI). If joint with DAVA, add Collin Hoag and any DAVA technical lead as covered individuals.
4. **Common Disclosure Forms** — file the biosketch (with ORCID) and current-and-pending for every covered individual. Memory `user_sam_registration.md` confirms SAM is active; the SF-424 family is not what's needed for §4021 OTs but the entity registration still matters for OT signing.
5. **FCOC posture statement** — the proposal should affirm in plain language that no covered individual has FCOC affiliations, no MFTRP participation, and no Confucius-Institute hosting. This is one paragraph, but its absence is a red flag in negotiation.
6. **Pre-existing IP carveout** — already drafted in `ip_carveout_v1.md`; the §4021 reframe does not change the IP structure but the proposal volume should cite §4021's standard data-rights language (DFARS 252.227-7013/7014/7017 still apply by reference for OT data clauses unless the OT itself negotiates different terms).

---

## 5. Open items / follow-ups

- [ ] Confirm DAVA covered-individual disclosures are obtainable before deciding whether to keep Collin on the joint submission.
- [ ] Update `project_mathbac_proposal_spine_2026_04_21.md` punch-list item 8 to reference §4021 (research) instead of §4022 (prototype).
- [ ] Verify the MATHBAC PA-26-05 PDF (in `sam_gov_attachments/`) does not impose any §4022-style cost-share floor by BAA-level direction even though the statutory hook is §4021. The statute floor doesn't apply, but DARPA can still ask for it in the solicitation. (Item blocked behind SAM.gov login per the memory.)
- [ ] If Phase II contemplates moving from §4021 (research) to §4022 (prototype) with a follow-on production tail, plan the cost-share story now — switching authorities mid-program is a paperwork event.

---

## 6. Sources

- **10 U.S.C. §4021** — Research projects: transactions other than contracts and grants. Cornell LII: <https://www.law.cornell.edu/uscode/text/10/4021>
- **10 U.S.C. §4022** — Authority of the Department of Defense to carry out certain prototype projects. Cornell LII: <https://www.law.cornell.edu/uscode/text/10/4022>
- **DARPA Grant & Cooperative Agreements** — disclosure form requirements, FRRBS, automatic disqualifiers. <https://www.darpa.mil/work-with-us/grant-cooperative-agreements>
- **DARPA Fundamental Research Risk-Based Review FAQs** (PDF, 2025-01) — `darpa-fundamental-research-risk-based-review-faqs.pdf` (binary on disk; PDF was unparseable in this session, recheck before final submission).
- **AIP FYI summary of DARPA foreign-affiliation screening** — risk tiers, FCOC, mitigation language. <https://www.aip.org/fyi/2022/darpa-screening-risk-researchers-foreign-affiliations>
- **MATHBAC program page** — confirms §4021 award instrument. <https://www.darpa.mil/work-with-us/opportunities/darpa-pa-26-05>
