# Cold outreach packet — 2026-05-09

**Goal:** real money in 2–8 weeks via consulting / contractor / subcontract conversations.
**Mode:** direct cold email + LinkedIn message. No "let's grab coffee", just specific asks.

---

## How to use this packet

1. Copy the relevant template into your email client.
2. **Verify the recipient's current title and email before sending** — people change jobs every 12–18 months in this market. Use LinkedIn to confirm or get a recent contact via their company's `team` page.
3. Send between 7am–10am Pacific in their local time zone (highest open rate).
4. **One per company per week.** Don't shotgun. Quality > volume. If they reply, follow up same day.
5. Track responses in a spreadsheet. If no response in 7 days, ONE polite follow-up. Then drop.

---

## Tier 1 — AI safety labs (highest fit, contractor + research roles)

These labs hire continuously and have publicly stated they're under-staffed for AI safety research and engineering. Contractor rates $200–$400/hr are common.

### 1. Anthropic — Research Engineer / Member of Technical Staff

- **URL to verify openings:** https://www.anthropic.com/careers
- **Likely contact for Alignment team:** Jared Kaplan (co-founder, leads alignment research direction). Email format unknown — apply through portal.
- **Why this fit:** SCBE composes with both Petri (their open-source auditing tool) and SCONE-bench (their red team's 2025 smart-contract attacker-capability benchmark); your work is the matching enforcement layer that both detection-only tools assume but neither ship.

**Cover letter (paste into application):**

```
Hi Anthropic team,

I'm Issac Davis. I've spent the last three years building SCBE-AETHERMOORE,
a 14-layer AI governance pipeline grounded in hyperbolic geometry. The
substrate composes with Petri — when I wire it as the enforcement layer
behind your audit tool, the 2026-05-13 v7-matched harness denies or
escalates 171/173 seeds, with a 1.16% false-allow rate and two named
residuals now tracked as regressions. It also composes with the
red.anthropic.com/2025/smart-contracts SCONE-bench finding — SCBE now
ships `scbe contract scan` as a SCONE-class static prefilter plus
SCONE-aware governance anchors in the production proxy, so the same
defensive surface that catches Petri seeds also catches the autonomous-
exploit-reasoning class your red team identified.

I work solo, MIT-license everything, and have shipped:
- npm: scbe-aethermoore (the 14-layer pipeline)
- PyPI: scbe-agent-bus (governance overlay primitives)
- US Provisional Patent 63/961,403 (hyperbolic cost-bound)
- 180/180 constrained-decoding gate, Wilson CI [0.979, 1.0]

I'm SAM.gov registered (UEI J4NXHM6N5F59) with two DARPA proposals in
active evaluation. I'd love to be considered for the Alignment Research
Engineer role, or a contractor engagement on Petri-adjacent work if
that's a faster path.

Code: https://github.com/issdandavis/SCBE-AETHERMOORE
Site: https://aethermoore.com

Issac D. Davis
Port Angeles, WA
```

### 2. Apollo Research — Research Engineer

- **URL:** https://www.apolloresearch.ai/careers
- **Why this fit:** They're focused on dangerous-capability evaluations; your bijective-tamper / identifier-canonicality work directly addresses adversarial code generation.

**Cover letter:**

```
Hi Apollo team,

I'm an independent AI safety engineer who's built two L13 governance overlays
that map directly to the eval-driven risks Apollo investigates: bijective
tamper detection (catches code-injection via lossy round-trip transforms)
and identifier canonicality (catches Unicode homoglyph + invisible-char +
mixed-script attacks). Both are wired in production behind feature flags
with regression suites green at 218/218.

The deeper substrate is a 14-layer pipeline using hyperbolic geometry to
make adversarial behavior exponentially expensive by closed-form algebra,
not learned filtering. Open-source, MIT-licensed, US Provisional Patent
63/961,403 backing the substrate.

Available for full-time, contractor, or scoped research collaboration.

Code: https://github.com/issdandavis/SCBE-AETHERMOORE
Site: https://aethermoore.com

Issac D. Davis
```

### 3. METR (Model Evaluation and Threat Research) — Research Engineer

- **URL:** https://metr.org/job-application
- **Why this fit:** Their entire mission is empirical evaluation of frontier-model risks. Your TAIBS benchmark concept (in the Schmidt proposal) is a direct match.

**Cover letter:**

```
Hi METR team,

I'm independent and shipping AI safety infrastructure — the 14-layer
SCBE-AETHERMOORE governance pipeline (npm/PyPI, MIT, provisional patent)
and a public benchmark suite under development (TAIBS, currently being
proposed for Schmidt Sciences funding).

I'm comfortable working on empirical eval design, capability-elicitation
protocols, and red-team automation. Composed with Anthropic's Petri
auditing tool for 171/173 denied or escalated in the 2026-05-13
v7-matched harness.

I'd like to be considered for the Research Engineer role, or for any
short-term contractor engagement on evaluation infrastructure.

Code: https://github.com/issdandavis/SCBE-AETHERMOORE
Site: https://aethermoore.com

Issac D. Davis
SAM UEI J4NXHM6N5F59
Port Angeles, WA
```

### 4. ARC (Alignment Research Center) — Researcher / Engineer

- **URL:** https://www.alignment.org/work-with-us/
- **Why this fit:** Their evaluations work needs more eval-design engineers; your formal-methods orientation fits their ELK / interpretability-adjacent work.

### 5. Goodfire AI — Research Engineer

- **URL:** https://www.goodfire.ai
- **Why this fit:** Mechanistic interpretability + safety; smaller team, faster hiring decisions.

---

## Tier 2 — PNW enterprises (mid-market, faster sales cycle)

These are companies in your geography who deploy AI at scale and need governance. Cold-email at the principal-engineer / staff-engineer level (not C-suite — they delegate down).

### 6. Microsoft (Redmond, WA) — Responsible AI team

- **Likely contact:** Search LinkedIn for "Principal AI Safety Engineer" or "Responsible AI Lead" at MSFT in Redmond. There are dozens; pick one whose recent posts mention generative AI evaluation.
- **Approach:** mention you're a Port Angeles-based independent and you'd like to discuss a paid spike on adversarial-cost manifolds for their copilot products. Reference SCBE on github.

### 7. F5 Networks (Seattle) — AI security

- **Why this fit:** They're shipping AI-firewall products and their existing tooling is Euclidean-pattern-match. Your hyperbolic substrate is a true differentiator.
- **Approach:** LinkedIn message to a Senior Director of Product or Principal Engineer in their AI/ML group.

### 8. Tableau / Salesforce (Seattle) — AI governance

- **Why this fit:** They sell to regulated enterprises (banking, healthcare) who require governance evidence. Subcontract opportunity for your overlay work.

### 9. T-Mobile (Bellevue) — AI/ML platform

- **Approach:** mid-market enterprise with AI deployment but small in-house safety team.

### 10. Costco (Issaquah) — IT modernization

- **Why this fit:** Conservative IT culture but increasing AI investment; values-fit for "low-overhead, high-trust" engagement.

---

## Tier 3 — Federal primes (slow but durable)

These companies sub on AI safety / governance work for DoD, DHS, IC, etc. SAM-registered status is a prereq (you have it).

### 11. Booz Allen Hamilton — AI Strategy & Engineering

- **Likely contact:** Pick a Director-level on LinkedIn working in their "Responsible AI" practice. Cold-email mentioning your SAM UEI and DARPA pipeline status.

### 12. SAIC — AI Center of Excellence

- **Approach:** They have a small business outreach team. Email their small-business liaison directly mentioning your minority-owned status + SAM registration.

### 13. Leidos — AI Solutions

- **Approach:** Same as SAIC. Their NAICS coverage matches yours.

### 14. CACI — Mission Systems

### 15. Peraton — Cybersecurity & Intelligence

---

## Universal cold email template (Tier 2 / Tier 3)

Customize the bracketed sections per recipient. Subject line is short and specific.

**Subject:** `[Their company] + adversarial-cost AI governance — quick question`

```
Hi [Name],

I'm Issac Davis, an independent AI safety engineer based in Port Angeles, WA.
I noticed [specific recent project / publication / job posting from their company]
and wanted to reach out about a possible paid engagement.

I've built SCBE-AETHERMOORE — a 14-layer AI governance pipeline that uses
hyperbolic geometry to bound adversarial cost in closed form, not via
learned filtering. It's open-source on npm/PyPI (MIT-licensed) with a US
provisional patent backing the substrate. Composes with Anthropic's Petri
audit tool: 171/173 denied or escalated in the 2026-05-13 v7-matched
harness.

I'm SAM-registered (UEI J4NXHM6N5F59) and have two DARPA proposals in active
evaluation. Available this quarter for:

- Short advisory call ($300, 60 min, often same week)
- Adversarial audit of your production AI endpoint ($5K–$15K, 1–3 weeks)
- Custom governance overlay ($25K–$80K, 4–10 weeks)
- Federal subcontract role ($150–$250/hr, contract)

If any of those map to a need at [Their company], I'd like 15 minutes
on your calendar this week.

Code: https://github.com/issdandavis/SCBE-AETHERMOORE
Hire details: https://aethermoore.com/hire

Thanks,
Issac D. Davis
(360) 808-0876
issdandavis7795@gmail.com
```

---

## LinkedIn DM template (when email can't be found)

LinkedIn DMs have ~3x the response rate of cold email but are limited to ~300 characters in the first message.

```
Hi [Name] — independent AI safety engineer here, SAM-registered, two DARPA
proposals in eval. Built a 14-layer governance pipeline (npm scbe-aethermoore)
that composes with Anthropic Petri for 171/173 denied or escalated. Available for
contractor / subcontract this quarter. Worth 15 min to discuss?
```

---

## What to do TODAY (in order)

1. **Verify deployment:** does aethermoore.com/hire actually load? If not, deploy `public/hire.html`. (Vercel auto-deploys public/* — verify the live URL before sending the cold emails that link to it.)
2. **Pick 5 names from the list above** — do not shotgun. 5 well-researched, personalized emails > 50 generic ones.
3. **Use LinkedIn to find current titles and emails.** If your name's recipient has moved jobs, note their replacement; the company still has the role.
4. **Send the 5 emails between 7am–10am Pacific tomorrow morning** (their local time if they're not in PT; otherwise 7am Pacific).
5. **Track in a spreadsheet:** `name | company | role | email | sent date | reply | next action`
6. **One follow-up per email at day 7 if no response.** Then drop.

Realistic expected outcomes from 5 sends:
- 3 will get no response. Normal.
- 1 will reply with "thanks, no current need." File and move on.
- 1 will reply with "interesting — can we talk?" → that's your conversion.

If you send 5 per week for 4 weeks (= 20 high-quality emails), you should land 1–3 paid conversations and 1 actual signed engagement. That's the math.

---

## OPSEC

- Do NOT mention DAVA / Collin Hoag specifically in any cold outreach. The MATHBAC teaming is private until awarded.
- Do NOT mention CLARA proposal contents (FAR 9.5).
- Do mention "two DARPA proposals in active evaluation" — that's public-facing information that signals seriousness.
- Do NOT name specific frontier model vulnerabilities even if you've found them; discuss your defense work in the abstract.
- Do NOT use your home address as a Reply-To. Use your aethermoore.com email if you have one set up; otherwise issdandavis7795@gmail.com is fine.
