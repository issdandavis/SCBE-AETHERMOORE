# Claim Exposure Memo — what the benchmark does and does not threaten

**Prepared:** 2026-06-09
**Filing:** US Non-Provisional 19/691,526 (filed 2026-05-28); priority to Provisional 63/961,403 (filed 2026-01-15)
**Title:** "System and Method for Hyperbolic Geometry-Based Authorization with Topological Control-Flow Integrity"
**Prepared by:** working analysis (Claude) — **NOT legal advice, NOT a patent attorney.** This is an engineering/strategy read of your own claim text against your own benchmark, for you to use pro se and when you get a professional review. Treat every "should" as "consider, then confirm with a registered practitioner."

---

## One-line answer

Your **independent claims (1, 9, 15) claim a method/system — a sequence of steps that gates execution.** They do **not** claim "the geometry beats a baseline." So the benchmark result (a plain text model out-detects the tongue features) **does not threaten the spine of the patent.** It only dents **two dependent claims**.

---

## What the benchmark actually showed

`experiments/honest_injection_benchmark.py` on real public injection corpora (deepset, jackhhao), metric = TPR@1% FPR:

- A character n-gram + logistic-regression baseline beats the SCBE tongue/bit-signature representation **2–6×** at detecting injection text.
- The golden-ratio (φ) six-axis weighting is **decorative** — removing it does not change the result.
- Scope: this tested the *byte/bit-signature feature representation*, not the full embedding gate or the AST tamper detector. Earlier ~0.99 AUC numbers came from a **saturated synthetic toy** and rank nothing.

A patent's validity does **not** depend on outperforming alternatives. Validity = novel + non-obvious + useful + enabled + eligible. "A simpler method works better" is not on that list. So the benchmark's reach into the patent is narrow and specific, below.

---

## When you use this (prosecution timeline — you filed 2026-05-28)

You don't "resubmit." The application is alive; you **respond** to it. The path:

1. **Now → first Office Action:** it sits in the examiner queue, often **12–24 months**. Nothing to do but optionally file a *preliminary amendment* (see below).
2. **First Office Action = almost always a rejection.** This is **normal, not failure** — the large majority of applications get a non-final rejection first. It's the opening of a negotiation, not a "no."
3. **You respond** (this memo is the ammo): amend claims and/or argue, usually within **3 months** (extendable to 6 with fees). You keep the independent claims, trim/cancel weak dependents, and rebut the examiner's art.
4. **Maybe a Final Rejection →** respond again, or file an **RCE** (request continued examination) to keep going, or appeal. Still the same application.

**Two things worth doing before the Office Action, not after:**
- **Preliminary amendment** — you *may* proactively cancel/narrow claims 3(i) and 4 now so the examiner never weighs them. Optional; some prefer to hold them as bargaining chips.
- **The marketing/honesty cleanup is independent of all this** — retire the "exponential cost / anti-fragile" language from public pages today regardless of prosecution timing.

**One hard rule:** you **cannot add new technical matter** after filing. So the claim-12 PQC "fix" isn't "go add liboqs to the spec" — it's "be ready to argue the spec's citation to FIPS 203/204 already enables it" (it likely does, since those are public standards). If that argument fails, the route is a continuation, not editing the filed spec.

---

## Claim-by-claim exposure

| Claim | Type | What it recites | Benchmark exposure | Verdict |
|---|---|---|---|---|
| **1** | Independent **method** | Embed in Poincaré ball → maintain session centroid → measure drift as hyperbolic distance → nonlinear cost → combine signals → **emit allow/review/quarantine/deny that controls whether the action executes** | None — it's a steps claim, not a performance claim | **SOLID** |
| **9** | Independent **system** | Same pipeline as a system with persistent runtime state restored after restart | None | **SOLID** |
| **15** | Independent **CRM** | Detect tampered source code via bijective re-encode + canonical-AST divergence + Unicode-confusable / bidi / homoglyph checks; gate execution on the tamper signal | None — different mechanism entirely; defends the "Trojan Source" (CVE-2021-42574) attack class | **SOLID — your strongest, most concrete claim** |
| **2** | Dependent | Narrows distance to the arcosh formula | Implemented (reduction to practice ✓); benchmark neutral | OK |
| **3(i)** | Dependent | Narrows cost to exponential `H(d,R)=R^(d²)` | Null-tests say the exponential form is **not load-bearing** | **EXPENDABLE — don't build value on it** |
| **4** | Dependent | Narrows to six-axis golden-ratio φ^k weighting | Benchmark says φ weighting is **decorative** (no measurable benefit) | **WEAK — could be attacked as an arbitrary, non-functional design choice; deprioritize** |
| **12** | Dependent | PQC receipt: FIPS 204 (ML-DSA-65) + FIPS 203 (ML-KEM-768) | Old coverage doc backed PQC with **simulated** Kyber (`np.random`) | **ENABLEMENT FIX — back with real `liboqs`** |
| 5–8, 10, 11, 13, 14, 16–21 | Dependent | Centroid update, deny-noise, persistence, quarantine containment, pre-filter stack, audit receipt, AST fingerprint details, Sacred-Egg predicates | Benchmark neutral | OK |

**Net:** 3 independent claims intact. 2 dependent claims (3(i), 4) dented. 1 dependent claim (12) needs an enablement fix. The rest are untouched.

---

## Eligibility (§101 / Alice) — your real long-term risk, and you're positioned OK

The usual software-patent killer is "you just claimed math." Your claims avoid that because they don't stop at computing a number — they **gate/route/control execution of a computational action**, persist state across restarts, and emit a verifiable signed receipt. That concrete application is the anchor that gets you past the abstract-idea rejection. Whether the geometry is *optimal* never enters the eligibility question. Keep the "controls whether the computational action is executed" language central; never let a claim collapse to pure calculation.

---

## Title vs. claims — know this gap

The title sells "Topological Control-Flow Integrity." The Hamiltonian-path / dimensional-lift "topological linearization" from the provisional is **not** what carries the independent claims here. Claim 15 is **AST-based code-tamper detection** — concrete and defensible. That's good drafting (the concrete claim survives), but the title oversells relative to the claim spine. Don't lean on the exotic topological-Hamiltonian story in front of an examiner or a buyer; lean on claims 1, 9, 15 as written.

---

## Action list (pro se)

1. **Stop publishing the effect, keep the method.** Retire "exponentially more cost" and "anti-fragile / stronger under attack" from README, site, and any examiner-facing argument. The claims survive on steps; the results language is pure downside. (README honesty pass already started — `README.md` Measured Results section.)
2. **Center everything on claims 1, 9, 15.** In any office-action response, argue the method steps + the execution-gating application, not performance.
3. **Treat 3(i) and 4 as expendable.** If an examiner pushes on them, you can amend/cancel without touching the independent claims. Do not build the commercial story on the exponential form or the φ weighting.
4. **Fix the PQC enablement.** Ensure the spec as filed enables claim 12 with real `liboqs` (ML-KEM-768 / ML-DSA-65), not the simulated `np.random` version in the old coverage doc. If the as-filed spec only simulates it, note it and be ready to rely on the real implementation in the codebase as evidence of enablement.
5. **Make one claim demonstrably real.** Commercial value (and non-obviousness arguments) get stronger when a claimed method visibly does something. **Claim 15 (Trojan-Source / AST tamper) is the most demonstrable** — a small honest benchmark on confusable/bidi code samples would do more for this patent than any geometry result.

---

## Getting real help without lawyer rates (you said you have no attorney)

These are legitimate, low/no-cost routes for pro se inventors — verify current details at uspto.gov:

- **USPTO Patent Pro Bono Program** — matches income-qualifying inventors with volunteer patent attorneys, free. Regional; has an income ceiling and usually a "some knowledge of the system" requirement (you qualify on knowledge). This is the highest-value option for a real claims review at $0.
- **USPTO Inventors Assistance Center (IAC) / Pro Se Assistance** — free phone help for unrepresented applicants on procedure and forms: 1-800-786-9199. They won't strategize claims but will keep your prosecution from dying on paperwork.
- **Registered patent agent (not attorney)** — USPTO-registered agents can draft/amend claims and prosecute, typically cheaper than attorneys. A one-time paid "claims review + office-action strategy" session is the targeted spend if Pro Bono doesn't land.
- **What to ask whoever you get:** (a) "Do claims 1, 9, 15 rest only on method steps tied to a concrete application, clean under §101?" (b) "Should we narrow or cancel 3(i) and 4 given they recite mechanisms with no measured benefit?" (c) "Is claim 12's PQC adequately enabled as filed?"

---

## First Office Action → do X (checklist for future-you)

When the rejection lands (likely 2027–2028):

1. **Read what kind of rejection it is**, per claim: §102 (anticipation — one prior-art ref shows it all), §103 (obviousness — combination of refs), §101 (abstract idea / eligibility), §112 (enablement / indefiniteness). Each is answered differently.
2. **Calendar the deadline immediately:** normally 3 months, extendable to 6 with escalating fees. Missing it abandons the application.
3. **Defend the independent claims (1, 9, 15) on the steps + the application** — the "controls whether the computational action is executed" limitation. Do not let them be recast as pure math.
4. **If 3(i) or 4 are cited:** cancel or narrow, don't die on them. They are bargaining chips, not the spine.
5. **If §101:** point to execution-gating + persistent runtime state + signed PQC receipt = practical application, not abstract idea.
6. **If §112 on PQC (claim 12):** argue the FIPS 203/204 citation enables a person of skill to implement.
7. **File the response through Patent Center** (patentcenter.uspto.gov). **Strongly consider the USPTO Patent Pro Bono Program for this step** — it's the technical fight where free expert help most changes the outcome.

---

## Bottom line

"The geometry doesn't beat a baseline" and "do I have a patent that matters" are nearly **orthogonal**. The patent matters because it fences a specific, implemented, execution-gating method (claims 1, 9) and a specific code-tamper detector (claim 15) — not because the math is state-of-the-art. The benchmark told you which two dependent claims and which marketing lines to quietly retire. The spine stands.

*Reference: `experiments/honest_injection_benchmark.py`, `experiments/honest_injection_results.json`, `docs/PATENT_CLAIMS_COVERAGE.md`, claims as drafted in `docs/legal/patent-workbench/assembled/SCBE_NONPROVISIONAL_SPEC_DRAFT_v1.md`.*
