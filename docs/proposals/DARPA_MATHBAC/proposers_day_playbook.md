# MATHBAC Proposers Day — Execution Playbook

**Date:** 2026-04-21
**Program:** DARPA-SN-26-59 (MATHBAC TA1)
**PM:** Yannis Kevrekidis
**Your role:** SCBE-AETHERMOORE sole author · Joint with Collin Hoag (DAVA)

---

## What Proposers Day actually is

A DARPA Proposers Day is a **structured teaming and scoping event**, not a proposal pitch. The program manager describes what they're funding, what they're explicitly *not* funding, how the solicitation will be scored, and what the submission timeline looks like. Attendees spend the rest of the day identifying collaborators and asking clarifying questions.

There is no proposal submitted at Proposers Day. You leave with a sharper understanding of the scope and (ideally) 1–3 credible teaming conversations in progress.

---

## Typical agenda (MATHBAC-shaped guess based on standard DARPA format)

| Time | Block | What to do |
|---|---|---|
| Opening | Welcome + administrative | Keep handout visible if in-person |
| PM talk | Kevrekidis on program scope, TA1/TA2/TA3 boundaries, deliverables, scoring | **Take structured notes** — scope language will show up in the BAA |
| Government Q&A | Open mic or written questions | Submit a clarifying question early — it's a visibility event |
| Teaming session | Short self-introductions from attendees; sometimes a shared roster | **This is the main event**. 60–90 seconds each. |
| Breakouts | TA-specific rooms, sometimes one-on-ones with PM | Target TA1 breakout. If PM office hours slot, grab one. |
| Close | Admin announcements; post-event survey | Note submission timeline carefully |

Virtual events compress this into 3–4 hours with chat-based teaming. In-person runs 6–8 hours and has a networking reception.

---

## Pre-event checklist (do today, 2026-04-20)

### Registration & admin
- [ ] **Confirm registration went in before 2026-04-07 deadline.** If it did not, email the MATHBAC admin inbox listed in the SN and ask for late admission — sometimes granted. SAM.gov status (UEI `J4NXHM6N5F59`, CAGE `1EXD5`, ACTIVE 2026-04-13) helps the case.
- [ ] **Confirm teaming profile submitted by 2026-04-14.** If missed, prepare a short one anyway and bring it as a handout.
- [ ] Verify event format (virtual / in-person / hybrid). DARPA usually announces in reminder email 48h out.
- [ ] If virtual: test the webinar platform the night before. Confirm audio, screen share, and chat work.
- [ ] If in-person: Arlington, VA; confirm travel logistics; pack one-pagers; photo ID for Conference Center entry.

### Materials ready
- [x] One-pager (`one_pager_v1.md`) — print 20 copies if in-person, have PDF for DMs/email
- [x] Elevator pitches (30s / 60s / 90s) memorized, not read
- [x] Q&A crib answers for anticipated tough questions (K_active reconciliation, N=24, live-channel gap, "Theorem (sketch)")
- [ ] One-pager PDF (generating below)
- [ ] Joint memo PDF (`joint_memo_v1.md`)
- [ ] v3 markup status with Collin — needs sign-off before any DARPA-facing distribution
- [ ] Tar bundle `dava_v1_for_collin.tar.gz` on a thumb drive or linkable (no public posting — hash-protected but private)
- [ ] Business-card equivalent: UEI, CAGE, email, phone — printed or in signature

### Coordination with Collin
- [ ] Confirm Collin is attending (virtual or in-person)
- [ ] Agree on who takes the mic if both attend
- [ ] Agree on a shared Google Doc or Signal thread for live note-capture during PM talk
- [ ] Confirm both of us can answer DAVA + SCBE questions at a basic level (cross-train)
- [ ] Post-event debrief time agreed (same evening ideally)

---

## During the event

### First 15 minutes
- Take a seat (or join early). Listen for the scoring rubric — usually the PM drops it in the first 10 minutes of scope talk.
- Note every specific phrase Kevrekidis uses about what TA1 is and isn't. These will appear in the BAA.
- Write down every example he gives — those are the target applications.

### PM talk
- **Scoring criteria** — write down verbatim
- **Out-of-scope list** — equally important; tells you what NOT to propose
- **Deliverable cadence** — phase gates, Go/No-Go criteria
- **Contracting vehicle** — OT vs FAR; affects who can team

### Q&A period
- Submit at least one written question. Good questions for MATHBAC TA1:
  - "Is a communication channel between agents of independent architectures in scope, or does TA1 presume a single architecture?"
  - "Does 'mathematics of agentic AI communication' include verification geometry, or is verification assumed to be TA2's problem?"
  - "Is empirical evidence at N=24 with closed vocabulary adequate phase-1 evidence, or is open-vocabulary a phase-1 requirement?"
- Ask in a way that signals your angle. The question IS a pitch.

### Teaming session (this is the event)
- Deliver the 60-second pitch — do not go over.
- Listen for teams missing the piece you have:
  - Anyone doing formal verification without empirical evidence → we have hash-sealed empirics
  - Anyone doing empirical agentic behavior without geometric structure → we have Poincaré embedding
  - Anyone doing hyperbolic geometry without a verification protocol → we have the sealed-label harness
- Capture names, institutions, what they said. One-line notes per person.

### Breakouts
- TA1 breakout room is priority.
- If PM has 1:1 slots, grab one. 5 minutes with Kevrekidis > 1 hour with anyone else.
- Bring the one-pager to every conversation.

---

## Post-event (same day, 2026-04-21)

- [ ] Debrief with Collin within 12 hours. Compare notes on scope language.
- [ ] Draft 3–5 follow-up emails to teaming-session contacts. Send within 48 hours while names are fresh.
- [ ] Log every scope-language phrase Kevrekidis used into `docs/proposals/DARPA_MATHBAC/mathbac_scope_notes.md` (new file) — will drive BAA-response drafting.
- [ ] Update `joint_memo_v1.md` if scope language reveals misalignment. Don't ship external until the memo matches scope.
- [ ] Watch for Q&A document posting (usually 1–2 weeks post-event).
- [ ] Watch for BAA release (usually 4–8 weeks post-event).

---

## Risk & failure modes

- **Registration missed 2026-04-07** → email admin now, reference active SAM.gov status, be polite and brief. Even if denied, the BAA is open to all when released.
- **Collin unreachable before event** → you can speak to SCBE-AETHERMOORE alone; do NOT speak to DAVA internals without him. If asked DAVA-specific questions, say "Collin owns DAVA; I can loop him in after today."
- **PM talk contradicts our framing** → listen carefully; do NOT push our framing in Q&A if it doesn't fit. Teaming session is where to surface it.
- **Someone else claims a near-identical result** → congratulate them, ask about their seal protocol, exchange contacts. Two independent claims is stronger than one.
- **Reviewer anticipates `p < 10⁻³⁰⁰` from paper** → acknowledge immediately, cite the permutation-test fix (3.00 × 10⁻⁴), show you caught it in review. Owning the mistake is stronger than hiding it.

---

## Post-event submission timeline (expected)

| Milestone | Typical DARPA timeline |
|---|---|
| Proposers Day | 2026-04-21 |
| Q&A document posted | 2026-05-05 ± 1 wk |
| BAA released | 2026-05-15 – 2026-06-15 |
| Abstract due (if program uses abstracts) | BAA + 3–5 wk |
| Full proposal due | BAA + 8–12 wk |
| Award decision | BAA + 6 mo |

Exact dates will be in the BAA. Plan for a full proposal draft to be ready 2 weeks before deadline — internal review, APEX Accelerator review (free, Port Angeles), Collin cross-read.

---

## Single most important thing

**The scoring rubric the PM reads in the first 10 minutes is the whole game.** Write it down verbatim. Everything we build between Proposers Day and BAA response should map directly to those bullets.

---

## Go/No-Go for sending external

Before anything leaves this repo for DARPA, Collin, or a teaming partner:

1. Joint memo hash block verifies against disk. **Done (commit `b6cd9a7f`).**
2. v3 markup reflects working hypothesis language, not theorem. **Done.**
3. Collin has signed off on v3 markup. **Pending.**
4. One-pager has been proofread by Collin. **Pending.**
5. No PII beyond what's publicly listed (UEI, CAGE, business email, business phone). **Clean as of this memo.**
