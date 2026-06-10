# SCBE System Grade — Now → "Cursor Level"

_Last updated: 2026-06-10. Author: overnight autonomous pass. Honest read, not the pitch._

## What "Cursor level" means here

Cursor is an AI-first code editor. SCBE is a governance/guardrail framework. They
are **not the same product category**, so this is not a feature-for-feature
comparison. "Cursor level" is used as a **proxy for a production bar**: one thing
done extremely well, fast and reliable, polished onboarding, a value prop people
pay for, claims that match reality, and real distribution/trust.

Graded on that bar, where **10 = Cursor-level polished product** and **1 = pile of
promising parts**.

## Composite: **3.0 / 10**

Real engine and real governance primitives underneath, but mispackaged,
over-claimed against its own data, and with no focused single-product surface or
distribution. The substance is a 6; the product is a 2; the honesty-of-claims was
a 2 and is now climbing because this branch stopped the bleeding.

## Per-axis grades

| Axis | Grade | Honest basis (this session's evidence) |
|---|---|---|
| **1. Core value prop clarity** | 3 | No single sentence answer to "what do I buy and why." M5 Mesh Foundry (governed data ops) is the most sellable framing; the governance gate + audit receipt is the most defensible atom. Both are buried under 14-layer/hyperbolic mythos. |
| **2. Does the core thing work (verified)** | 5 | The governance **envelope** works: gate → decision → audit receipt → escalation, and now a **fixed-anchor enforcement wall that actually fires** (cumulative-cost AUC **0.999**, ~99% intruders stopped, ~4% citizens blocked on real human-attack corpora). That is genuine and newly real this branch. |
| **3. Reliability / correctness** | 4 | CI is green but **was hiding things**: semantic-mode tests silently ran the stats fallback, then hard-**segfaulted** once `sentence-transformers` was installed (repeated in-process model loads under py3.14). Fixed at source (process-wide model cache). 3 real semantic-mode gaps are now honest `xfail`s instead of fake-green. |
| **4. Differentiation / moat** | 2 | The headline differentiators are **contradicted by our own committed benchmarks**: Euclidean AUC 0.9995 > hyperbolic 0.9553; 2-layer 0.9987 > full 14-layer 0.978; char n-gram TF-IDF beats the tongue/bit signature 2–6× on real injection text. The geometry is largely **decorative** for detection. The moat is the governance envelope + receipts + escalation, **not** the math superlatives. |
| **5. UX / packaging / onboarding** | 2 | npm security lib shipped a tweet-CLI and ~1351 files; HF dataset viewer broken (ArrowInvalid row 0); install.js npm-pack crash (fixed locally). No clean "install → first governed result in 60s" path. |
| **6. Trust surfaces / claims** | 3 | Public site still had "nine repos" copy and an "Isaac Thorne" byline leak; articles over-claim ("sentient AI", inflated counts). README reframed locally to "local-first governance gate" and publishes the losing numbers — that honesty is the asset; finish propagating it. |
| **7. Distribution / adoption** | 1 | No store presence, no users, no funnel that closes. Patent (provisional + non-provisional filed) is real IP but is method-claim based, not adoption. |

## The one true thing to sell

**A local-first governance gate that returns ALLOW/QUARANTINE/ESCALATE/DENY + a
signed audit receipt, and a cost wall that demonstrably stops an agent walking
toward forbidden behavior (AUC 0.999).** That is defensible, demonstrable, and
now tested. Everything else is supporting cast.

## Reach path

### Now (3) → Sellable (6)
1. **Wire the working wall into the live cost path.** The 3 `xfail`ed semantic
   tests are xfailed precisely because the gate's *native* cost doesn't rank
   maliciousness on embeddings, while `src/governance/anchor_wall.py` does (AUC
   0.999). Make the anchor wall the semantic cost axis; the xfails should flip to
   pass (they're `strict=False`, so flipping is safe — then tighten to strict).
2. **Pick ONE product surface** (governance gate API + receipt) and cut a clean
   `install → governed decision in 60s` quickstart. Strip the junk from the npm
   security package (no tweet-CLI, no 1351 files).
3. **Make every public claim match a committed number.** Finish the README/site
   reframe: drop "hyperbolic/14-layer" superlatives, lead with the gate + receipt
   + the AUC-0.999 wall. Kill the "nine repos" copy and the Isaac Thorne byline.
4. **Fix the trust surfaces**: HF dataset viewer, install crash, archived-repo
   links. These are cheap and they read as "abandoned" right now.

### Sellable (6) → Cursor level (9)
5. **One-thing-extremely-well + fast + reliable.** Sub-second gate decision,
   deterministic receipts, zero silent fallbacks (the semantic fallback that hid
   broken behavior is the anti-pattern to never repeat). Promote the `xfail`s to
   `strict=True` once fixed so the suite can never silently regress again.
6. **Onboarding a non-expert can finish.** A real first-run, a dashboard for the
   receipts/audit chain, copy that a buyer understands without the mythos.
7. **Distribution**: a store/marketplace listing for the gate (the M5 Foundry
   "Launch Pack" is the natural first SKU), and one reference deployment.

## What this branch (`fix/gate-math-honesty`) already moved
- Built + productized the fixed-anchor wall (`src/governance/anchor_wall.py`,
  AUC 0.999) and wired it into `RuntimeGate` as an opt-in overlay.
- Added a sliding-window mode so the wall holds on long-lived sessions.
- Killed the semantic-mode segfault at the source (shared model cache).
- Replaced fake-green semantic tests with an honest invariant + documented
  `xfail`s — the suite now tells the truth about what works.

The honest version of this system is **more** sellable than the over-claimed one,
because the thing that's left after the cuts (gate + receipt + a wall that fires)
is real, and buyers can verify it.
