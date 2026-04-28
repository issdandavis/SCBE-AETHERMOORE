# MATHBAC Past-Performance Advisor Outreach — Template v1

**Purpose:** Close the federal past-performance gap on the DARPA-PA-26-05 (MATHBAC) Phase I proposal by recruiting one named advisor with a documented federal R&D track record (DARPA / NSF / DoD / DOE / NIH) who is willing to be cited in Volume I §Proposer Capabilities and the OT Reps & Certs (Attachment I).
**Drafted:** 2026-04-27
**Status:** TEMPLATE — every `{{ }}` placeholder is fillable. Send is **GATED-USER** (no outbound until Issac authorizes per advisor).
**Hard deadline anchor:** Full proposal due 2026-06-16 16:00 ET via BAAT. Advisor commitment letter (or a documented willingness-to-advise email) needs to land by **2026-05-25** to leave 22 days for proposal integration.

---

## 0. When to use this template

Send the outreach when **all** of the following are true:

1. TA1 is locked (DONE — see `project_mathbac_proposal_spine_2026_04_21.md`).
2. The candidate appears in `teaming_targets_v1.md` Tier 1, Tier 2, or Tier 3, OR the user has independently identified them as a federal-track advisor.
3. The candidate has not declined a prior outreach within the last 12 months.
4. The candidate is not an FFRDC, UARC, Government Entity, or National Lab employee in their **primary** appointment (per `PA-26-05` lines 949–951; see §6 below for the academic-affiliation nuance).

If any of those is false, surface it to the user before drafting the personalized version of the message.

---

## 1. Role clarity — what the ask actually is

**Critical:** This template requests an **advisor** role, not a co-PI / sub / teaming partner role. Drift on this point will burn the relationship.

| Posture | What it means | When to use |
|---|---|---|
| **Advisor (this template's default)** | Named individual cited in Volume I §Proposer Capabilities; provides ≤40 hours of technical guidance over 16 months; no institutional contracting; no IP stake; no FRR covered-individual obligation unless they elect in. | Past-performance gap closure. The 95% case. |
| **Subaward / Consultant** | Their institution receives funds; they bill hours; covered-individual disclosures required. | Only if Issac decides to carve out budget AND the advisor's institution permits. Discuss before pitching. |
| **Co-PI / Teaming Partner** | Joint proposal; institutional teaming agreement; FRR for every covered individual; revenue-share. | The Tier 1 conversation — Chiriac, Jha, Reddy. **Do NOT use this template** for those; use `teaming_agreement_v2_draft.md` instead. |

If the candidate pushes toward a heavier posture in their reply, that is a good problem and a separate negotiation. Stay in the advisor frame in the outbound message.

---

## 2. Outreach email — base template

**Subject line variants (pick one):**

- `MATHBAC (DARPA-PA-26-05) — request for 30 minutes on past-performance advisor role`
- `MATHBAC TA1 advisor request — geometric upper bound, sealed-blind 24/24`
- `30-min ask: {{advisor first name}}, MATHBAC sole-performer past-performance advisor`

**Body:**

```
{{advisor salutation}},

I'm Issac D. Davis, sole performer on a Phase I submission for DARPA-PA-26-05
(MATHBAC, PM Yannis Kevrekidis, full proposal due 2026-06-16). I'm pursuing TA1
— Mathematics of Agentic Communication Protocols — with two pieces of evidence
already on the record:

  1. Sealed-blind 24/24 governance accuracy on a live agentic channel, with a
     permutation-test upper bound of p ≤ 3.00 × 10⁻⁴.
  2. KL channel capacity 1.5761 bits/tick (= 99.4% of log₂ 3) on the realm
     surface; 2.9818 bits/tick (= 99.4% of log₂ 8) on the regime surface.
     Both verified under hash-sealed protocol.

The geometric core is a Poincaré-ball embedding with PSU(1,1) Möbius
equivariance — bit-identical k-means++ under the group action — and a 14-layer
pipeline with five composed axioms. Frame is Carnot/Pasteur/Wright per
Kevrekidis's Proposers Day pitch (2026-04-21).

The gap I'm writing to close is past performance: I run as a U.S. sole
proprietor (UEI J4NXHM6N5F59, CAGE 1EXD5, SAM-active 2026-04-13) with a
provisional patent (USPTO 63/961,403), a published Six Tongues Protocol book
(KDP ASIN B0GSSFQD9G), and a working stack — but no prior federal prime
contract. The proposal is stronger if a named advisor with a documented federal
R&D track record is cited in Volume I §Proposer Capabilities.

The ask is light:
  • 30-minute intro call (any week before 2026-05-18)
  • If we're aligned, a one-paragraph willingness-to-advise letter or email I
    can attach as a non-binding indication of advisor support
  • Up to 40 hours of technical advice across the 16-month Phase I, billable
    or pro-bono — your preference. No IP stake, no institutional contracting,
    no FRR covered-individual paperwork unless you elect in.

If a heavier role makes sense after we talk, I'm open to that conversation
separately, but I want to be clear up front that I'm not asking for a teaming
commitment in this email.

Three artifacts I can share before the call:
  • 2-page MATHBAC abstract (sent 2026-04-27 to MATHBAC@darpa.mil; happy to
    share the PDF)
  • Annex A basis sheet (hash-sealed evidence with reproduction commands)
  • Proposer-metrics specs v1 (8 candidate metrics with 6-field schema each)

What's the best 30-minute window in the next two weeks?

Thank you for considering it.

Issac D. Davis
Sole performer, SCBE-AETHERMOORE
issdandavis7795@gmail.com · {{phone if user authorizes}}
SAM.gov: UEI J4NXHM6N5F59 · CAGE 1EXD5
```

---

## 3. Variant openers per advisor archetype

Replace the second paragraph (the evidence paragraph) with the variant that matches the advisor's published lane. Keep the first and third paragraphs as-is.

### 3a. Geometric / topological advisor (Chiriac, Kitchen, Lin)

```
The geometric substrate is a Poincaré-ball product manifold with PSU(1,1)
Möbius isometry, sealed at M0 against bit-identical TS/Python parity (5
fixtures, 25 cases, SHA-256 sealed in M0_fixture_seal_v1.md). Persistent-
homology sketches on the agentic channel preserve under the group action;
that's the substrate I'd most like 30 minutes of pushback on.
```

### 3b. Formal-methods advisor (Jha, Goldman, GrammaTech)

```
The formal substrate is a 5-axiom mesh — unitarity, locality, causality,
symmetry, composition — applied across a 14-layer pipeline. The harmonic wall
H(d, pd) = 1/(1 + φ·d_H + 2·pd) provides a bounded scoring function in (0,1]
with a closed-form upper bound on adversarial cost. I have an empirical
sealed-blind result; I do NOT have a capacity theorem yet, and that's the
formal gap I'd most like 30 minutes of advice on.
```

### 3c. Information-theoretic / decentralized-control advisor (Nayyar, Avestimehr, Huo)

```
The communication channel admits a clean information-theoretic readout:
KL capacity 1.5761 bits/tick on the realm surface (99.4% of log₂ 3),
2.9818 bits/tick on the regime surface (99.4% of log₂ 8), under hash-sealed
protocol. The framework is a phi-weighted six-language protocol substrate
(Sacred Tongues; weights phi^0..phi^5). I'd like 30 minutes on whether the
common-information / coded-computing toolset gives me a tighter capacity bound.
```

### 3d. Scientific-ML / dynamical-systems advisor (Reddy, Lin, Rudi)

```
The Phase I deliverable I'm proposing is a Living Metric — a performer-declared
scoring rubric (Mutual Encoding Efficiency, Axiom Compliance Vector,
Cross-Domain Principle Transfer Index, Principle Interpretability Score) that
carries a published 6-field schema per metric (definition, mechanism, inputs,
outputs, test, falsifier). Equation-free / dynamical-systems framing fits
Kevrekidis's vocabulary directly. I'd like 30 minutes on whether the metric
schema is the right level of abstraction for an IV&V handoff at M8.
```

### 3e. Big-prime DARPA-experienced advisor (Avestimehr only)

```
I'm running as sole performer because I want to keep the geometric substrate
as the proposal's center of gravity, but I recognize the past-performance gap
on a $2M Phase I award. If your read is "you need a prime to carry it," I'd
like to know that — and if there's a clean way to position SCBE as the
hyperbolic-geometric kernel under a Coded-Computing / NOVA outer envelope, I'd
like 30 minutes on the architecture.
```

---

## 4. Pre-call prep — what to send 24 hours before the meeting

Send exactly three attachments. More than three reads as desperate; fewer reads as unprepared.

| # | Artifact | Path | Purpose |
|---|---|---|---|
| 1 | MATHBAC 2-page abstract | `docs/proposals/DARPA_MATHBAC/pdf/SCBE_DAVA_MATHBAC_one_pager_v1.pdf` (or whichever was sent to MATHBAC@darpa.mil) | Establishes scope and frame |
| 2 | Annex A basis sheet (sealed evidence) | TBD — currently fragmented across `proposer_metrics_specs_v1.md §3.3`, `M0_fixture_seal_v1.md`, and the spine doc. **Open task: consolidate into single PDF before first outreach.** | Shows the hash-sealed evidence the advisor is being asked to vouch for |
| 3 | Proposer metrics specs v1 | `docs/proposals/DARPA_MATHBAC/proposer_metrics_specs_v1.md` (export as PDF) | Shows the 8-metric catalogue with 6-field schema |

**Do NOT send** the full PA-26-05 PDF (they have it or can get it), the compliance checklist (internal artifact), or the codebase (creates an evaluation burden the advisor didn't sign up for).

---

## 5. The 30-minute call — agenda script

This is the recommended structure. Adapt for tone, do not skip the disclosure block.

**0:00–0:03** — Thank them for the time. Confirm they have the 3 attachments. Confirm scope of the call: "I'm asking for 30 minutes of technical pushback on the geometric/formal/info-theory substrate, and 5 minutes at the end on whether you'd be willing to be cited as advisor."

**0:03–0:18** — Walk through one slide of evidence (the sealed-blind 24/24 + the KL capacity numbers). Stop and ask: "What's the first thing you'd push back on?" Listen. Take notes. Do not defend.

**0:18–0:25** — Working Hypothesis vs. Theorem language: "I have an empirical result, not a capacity theorem. I'm explicit about that in the abstract — §4 of the v3 markup uses 'Working Hypothesis,' not 'Theorem.' If you advise, that posture stays."

**0:25–0:28** — Disclosure block (read this verbatim if helpful):

> "Three things you should know before agreeing. (1) Award instrument is an
> Other Transaction for Research under 10 U.S.C. § 4021 — not FAR/DFARS. No
> cost-share floor. (2) FRR review applies post-selection; if you elect into a
> covered-individual role you'd file Common Disclosure Forms. If you stay in
> advisor-only posture, you don't. (3) I have a USPTO Provisional 63/961,403
> filed and a published book (Six Tongues Protocol, KDP ASIN B0GSSFQD9G) that
> establish prior art. Nothing I'd ask you to advise on infringes anyone I
> can identify; I want you to push back if you see otherwise."

**0:28–0:30** — The ask: "Would you be willing to send me a one-paragraph email, no later than {{date — default 2026-05-25}}, indicating that you're willing to advise this Phase I proposal in the capacity we just discussed? I'll cite you in Volume I §Proposer Capabilities. If you'd rather hold the decision until after the abstract response from MATHBAC@darpa.mil, that's fine — abstracts return ~mid-May."

---

## 6. Eligibility / affiliation checks

Before sending, confirm with the candidate's public profile:

- **Primary appointment:** Must NOT be FFRDC, UARC, Government Entity, or National Lab. Academic appointments at universities (Wisconsin, Virginia Tech, USC, Georgia Tech, Purdue, Michigan Tech, etc.) are fine. Aalyria (private company) is fine. Caveat: a university PI with a courtesy appointment at a National Lab is fine **as long as their MATHBAC role attaches to the university**.
- **OCI:** If the candidate's organization currently holds a SETA / A&AS contract on any DARPA program, raise it before pitching (PA-26-05 L952–959). Aalyria, UW-Madison, and Virginia Tech do not appear to hold such contracts as of 2026-04-27 — verify per candidate.
- **Foreign-affiliation flag:** If the candidate has visible Confucius-Institute or Malign-Foreign-Talent-Recruitment-Program ties, do not pursue. (Per FRR autodisqualifiers — see `frr_ot_eligibility_v1.md`.)
- **Export-control flag:** If the candidate's prior work touches ITAR/EAR-controlled tech that overlaps SCBE scope, raise it pre-call.

---

## 7. After the call — three outcomes

### 7a. Yes, advisor

Within 24 hours, send a follow-up:

```
{{advisor salutation}},

Thank you for the time today. To confirm: you've agreed to be cited as advisor
on the Phase I submission for DARPA-PA-26-05 (MATHBAC), with up to 40 hours of
technical guidance across the 16-month performance period if the award lands,
and no covered-individual / FRR obligation unless you elect in.

If you can send a one-paragraph email confirmation by {{date}}, I'll attach it
to Volume I §Proposer Capabilities. The text below is what I'd plan to cite —
let me know if anything needs to be adjusted:

  "{{advisor name}}, {{title}}, {{institution}}, has agreed to serve as
   technical advisor on this Phase I effort, providing up to 40 hours of
   technical guidance on {{geometric / formal-methods / info-theoretic / SciML
   — pick one}} aspects of the agentic-communication-protocol substrate.
   Affiliation in advisory capacity only; no subaward; no IP transfer."

Thank you again.

Issac
```

### 7b. No, but pushback was valuable

Save the pushback verbatim in `docs/proposals/DARPA_MATHBAC/advisor_outreach_log.md` (create on first declined outreach). Tag with date, advisor name, and which substrate (geometric / formal / info-theoretic / SciML) the pushback addresses. Adversarial pushback from a credible name is a Phase I drafting asset even without the citation.

### 7c. No, with no pushback

Log the no, do not follow up sooner than 90 days, move to the next candidate.

---

## 8. Outreach order — recommended

Per `teaming_targets_v1.md` and the spine doc's "highest priority after TA pick" flag (item 10).

| Priority | Candidate | Why first/later | Variant opener |
|---|---|---|---|
| 1 | **Somesh Jha** (UW-Madison) | Formal-methods complement, explicitly seeking exactly this collaboration shape per his proposer profile. **Highest hit rate.** | §3b |
| 2 | **Oliver Chiriac** (Aalyria) | Geometric substrate fit is near-perfect; he's already Tier-1 teaming target. **NOTE:** if pursued as advisor here, do NOT also send the teaming-agreement template. Pick one posture per candidate. | §3a |
| 3 | **Chandan K. Reddy** (Virginia Tech) | Local to Arlington; SciML/dynamical-systems lane fits Living Metric. | §3d |
| 4 | **Salman Avestimehr** (USC) | Big-prime / 3× DARPA lead PI; advisor role gives past-performance citation without committing to teaming. | §3e |
| 5 | **Sarah Kitchen** (MTRI) | Differential geometry + tokenization across modalities; Sacred Tongues bridge. | §3a |
| 6 | **Ashutosh Nayyar** (USC) | Decentralized stochastic control / common information; pure info-theoretic angle. | §3c |
| 7 | **Robert Goldman** (SIFT) | DARPA AICC finalist + small-business; advisor citation is feasible despite SIFT being a competitor on adjacent BAAs. **Verify no direct OCI before pitching.** | §3b |

**Cadence:** send no more than 2 outreaches per week. Each advisor needs 7–10 days to reply; staggering preserves the option to adapt subsequent messages based on early responses.

---

## 9. What to NEVER include in the outbound email

- The full DARPA solicitation PDF (they have it).
- Salary expectations or specific budget figures.
- Any reference to "co-PI," "team," "prime," or "subaward" unless the advisor uses the term first in their reply.
- The internal compliance checklist (`PA_26_05_compliance_checklist_v1.md`).
- Hash-sealed evidence reproduction commands beyond what's in the abstract / Annex A.
- Anything covered by USPTO Provisional 63/961,403's confidentiality posture beyond what's already in the published Six Tongues Protocol book (KDP ASIN B0GSSFQD9G).
- The phrase "sentient AI consciousness" or any mystical / lore framing. (See `reference_collin_hoag_dava.md` — the DAVA branding angle is a credibility liability for the MATHBAC audience; advisor outreach must stay in the formal-methods / geometric / information-theoretic register.)

---

## 10. Open decisions (user-auth required before first send)

| # | Decision | Default if user is silent | Owner |
|---|---|---|---|
| 10.1 | Phone number in signature block? | Omit (email-only contact) | User |
| 10.2 | Send the abstract PDF, or just describe it? | Send PDF | User |
| 10.3 | Mention Collin Hoag / DAVA in the outreach? | Do NOT mention (per `reference_collin_hoag_dava.md` credibility-liability flag); mention only if advisor asks about prior collaborations | User |
| 10.4 | Cite the provisional patent number, or just say "filed"? | Cite the number (63/961,403) — establishes seriousness | User |
| 10.5 | Use Issac's personal email, or a project alias? | Personal (issdandavis7795@gmail.com) — no aliased mailbox is set up | User |
| 10.6 | Send before or after the abstract response from MATHBAC@darpa.mil arrives (~mid-May)? | **Before.** Don't gate on the abstract response — advisor commitment letters are slower than abstract reviews | Recommendation |

---

## 11. Provenance

- Drafted 2026-04-27 from `project_mathbac_proposal_spine_2026_04_21.md` punch-list item 10, `teaming_targets_v1.md`, `frr_ot_eligibility_v1.md`, `PA_26_05_compliance_checklist_v1.md`, and `reference_collin_hoag_dava.md`.
- Spine doc flag: "Past performance: no federal contract history. Needs advisor with track record on team."
- This template is for **advisor** outreach only. Tier 1 teaming partner outreach uses `teaming_agreement_v2_draft.md`.
- Status of all outreach (date, candidate, posture, outcome) lives in `docs/proposals/DARPA_MATHBAC/advisor_outreach_log.md` (create on first send).

---

## 12. Amendment policy

This is a v1 template. Before the first outreach, the user reviews and either:
- Authorizes send-as-is, OR
- Requests `advisor_outreach_template_v2.md` with edits.

After three completed outreaches (regardless of outcome), revisit the template — what worked, what didn't, what to cut. Roll any learnings into v2 before the fourth outreach.
