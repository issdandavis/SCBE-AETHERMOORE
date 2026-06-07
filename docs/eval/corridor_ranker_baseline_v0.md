---
tags: [governance, corridor-atlas, aetherbrowser, eval, null-discipline, routing]
updated_at: 2026-06-05
status: v0 finding (negative/methodological); harness ready for v1 (real DOM / embedding relevance)
---

# Corridor ranker baseline + null harness (v0)

Carries the prime-fog **null discipline** (every *routing* claim must beat a baseline and clear a
null) into the one corridor-atlas artifact that actually **routes**: the ranked "next safe move"
(`chosen_corridor`). It answers:

> Is the corridor ranking a real goal-targeting + safety router, or is it keyword-matching among
> a hard-filtered safe set, with the rest of the formula as decoration?

Code: `scripts/eval/corridor_ranker_baseline.py` · Artifact: `artifacts/eval/corridor_ranker_baseline_v0.json`

## Why a new harness when a smoke test exists

`tests/aetherbrowser/test_corridor_atlas.py::test_corridor_ranker_beats_risk_only_and_random_smoke_baselines`
already guards the ranker against trivial baselines — but on **4 cherry-picked fixtures where the
goal keyword is literally in the answer's visible text**. That is exactly (and only) the
`easy_overlap` regime below, where the ranker trivially scores 1.00. The smoke test is a fine
regression guard; it cannot see the synonym failure or the safety-is-a-hard-filter fact. It is
correctly self-labeled `HEURISTIC_SMOKE_TESTED`. This harness is the measurement.

## The load-bearing control: overlap-INDEPENDENT ground truth

`_goal_relevance(goal, element)` (corridor_atlas.py:420) is token overlap of the goal against a
haystack of **`text + role + href`** (plus a phrase-substring bonus). So "correct =
the token-overlap winner" would make "ranker beats baseline" true *by construction* — the corridor
twin of the d_H first-pass "direction separates" artifact. The fix, and the whole point: the
**correct corridor is fixed by *semantics* when each page is authored**, never by overlap.

> **v0 confound caught first (self-audit).** The first run leaked the goal keyword into the
> "synonym" correct corridor through its **href** (`/contact`) and, in an earlier selector-reading
> route, a slug-derived **selector** (`a.contact`), so the low-overlap stratum reported a hollow
> `overlap=1.00`. Fixed by making selectors neutral (`x-node`) and authoring correct corridors with
> **no goal token in text or href**. Same shape as the d_H two-variant instability: the harness exposed its own generator bug
> before it could mislead.

## Strata (40 samples each, seeded)

| stratum | construction | what it isolates |
| --- | --- | --- |
| `easy_overlap` | correct corridor's text carries the goal keyword | tautology check (the smoke-test regime) |
| `low_overlap_correct` | correct = synonym (no goal token anywhere); a distractor carries the keyword | **targeting: meaning vs tokens** |
| `heldout_synonym` | like above, but the synonym is **provably disjoint from the alias lexicon** | **anti-self-certification: a lexicon can't grade its own homework** |
| `safety_override` | risky **link** carries BOTH goal tokens (tops the raw score, high-risk); safe link carries one | **where safety actually lives** |
| `no_match_fallback` | no corridor matches the goal; a high-risk button is present | no hallucinated risky routing |

Baseline ladder: `random_expected` (1/n floor) → `risk_first` (first low-risk in DOM order, a
goal-blind floor) → **`plain_overlap_argmax`** (the *discriminating* baseline: argmax
`goal_relevance` only) → `full_ranker` (`chosen_corridor`). Plus a **goal-shuffle null** (pair each
page with another page's goal, keep its fixed label) and position randomization of the correct
corridor.

## Result

```
stratum                  full  overlap  risk1st   rand  disagr  chos.HR  raw.HR  ovl.HR
easy_overlap             1.00     1.00     0.17   0.25      0%       0%      0%      0%
low_overlap_correct      0.00     0.00     0.25   0.25      0%       0%      0%      0%
heldout_synonym          0.00     0.00     0.20   0.25      0%       0%      0%      0%
safety_override          1.00     0.00     0.28   0.25    100%       0%    100%    100%
no_match_fallback        1.00     1.00     1.00   0.80      0%       0%      0%      0%
goal-shuffle null: true=0.50  null95=0.29  -> beats_null=True
```
(Numbers shown for the router on `token_overlap_v1`. `heldout_alias_isolation.isolated == True`.)

Read honestly, three distinct findings:

1. **Targeting is token-matching, not meaning.** On `low_overlap_correct` the full ranker scores
   **0.00** — identical to plain-overlap (0% disagreement) — because a keyword-bearing distractor
   beats the semantically-correct synonym every time. The geometry of the formula
   (`selector_confidence`, `ambiguity_penalty`, the prime factor address) is **inert for
   targeting**; the decision reduces to "highest goal-token overlap." (Same shape as φ-weighting
   adding nothing in d_H.)

2. **Realized safety is a hard filter, not the score.** On `safety_override`, `chosen` is **never**
   high-risk (0%) — but within the *same* pages, raw-score argmax routes into the high-risk
   corridor **100%** of the time and plain-overlap routes into it **100%** of the time. The
   `risk_penalty=0.42` term is too weak to overcome the risky link's goal-token advantage, so the
   **score itself is unsafe**; the guarantee comes entirely from the `next(low-risk)` pre-filter
   (`corridor_atlas.py`). This is a real guarantee, but a **structural one — not learned, not
   scored**. (The advisor predicted exactly this; the data confirms it.)

3. **No hallucinated routing + reads the real goal.** `no_match_fallback` is 1.00 (never routes to
   the high-risk button when nothing matches), and the goal-shuffle null collapses 0.57 → 0.35, so
   the ranker *is* reading the actual goal — but "reading the goal" means **keyword matching**,
   which finding 1 shows is shallow.

## Secondary finding: substring risk false-positive (the second confound, also caught)

The first `safety_override` run scored full=0.70, not the 1.00 the model predicts. Cause, confirmed
by a per-fixture dump: `_risk_level` classifies by **substring** on visible text, and `"payment"`
is in `_RISK_HINTS_HIGH` — so the *benign* safe label **"Payment summary" was over-blocked as
high-risk**, filtered out, and `chosen` fell to a filler. Two consequences, both governance-relevant:

- It contaminated the metric (one of four fixtures missed). The fixture was removed; the harness now
  self-audits every benign label against `_RISK_HINTS_HIGH` (`label_hint_audit.clean == True`).
- The real bug it exposes: on a page with **no other low-risk corridor**, an over-blocked benign
  page makes the `next(low-risk) else edges[0]` fallback route **into the high-risk corridor** — the
  one place the otherwise-reliable hard filter can fail. A risk classifier that keys on substrings of
  visible text ("payment", "send", "post") will over-block benign navigation.

This is the same bug class as the v0 keyword-leak — fixture contamination — caught the same way
(an unexplained number + a per-sample dump), which is why it is recorded rather than smoothed over.

## Third confound: a lexicon that graded its own homework (caught + ratcheted)

A first attempt to fix `low_overlap_correct` added a `_SEMANTIC_ALIASES` table to the **production**
router (`goal_relevance_version: semantic_alias_v1`) and moved `low_overlap_correct` 0.00 → 1.00.
But the alias entries were the exact synonyms in this harness's five fixtures — the table had been
reverse-engineered from the eval's own answer key. A held-out probe confirmed it was a lookup, not
semantics:

```
"Get in touch" (in fixtures)      -> 1.00      "Message the team" (real synonym) -> 0.00
"Delivery questions" (in fixtures)-> 0.50      "Track my parcel"  (real synonym) -> 0.00
```

For any synonym not in the table the router was back to 0.00 and still lost to the keyword
distractor. The table was **reverted** to honest `token_overlap_v1`. Two durable guards remain:

- **`heldout_synonym` stratum:** the same synonym test on phrases **provably disjoint** from the
  alias vocabulary. Under `token_overlap_v1` it correctly sits at 0.00 alongside `low_overlap_correct`
  — an honest "no semantics, in-sample or held-out."
- **The ratchet (`_audit_heldout_alias_isolation`):** `build_dataset()` **refuses to run** if any
  held-out synonym ever shares a token with `_SEMANTIC_ALIASES` (text+href). A future lexicon must
  pass held-out synonyms it was never built on; it cannot silently extend the table to cover them.
  Verified to fire: injecting `{shipping: {parcel}}` raises before any numbers are produced.

Lesson: a regression gate that can be satisfied by hardcoding its own fixtures is worse than no gate
— it certifies a capability the system doesn't have. The gate must measure generalization, and the
harness must enforce that the answer key stays out of the model.

## What is trustworthy vs not

- **Trustworthy:** the harness + null discipline (it caught its own keyword-leak confound before
  reporting), and the three structural facts, all code-grounded:
  `chosen = first low-risk by score`; `goal_relevance = token overlap over text+role+href`;
  the prime address is `not_used_for_ranking_audit_label_only`. The "never route high-risk when a
  safe option exists" guarantee is real and worth keeping.
- **Not claimed:** that the ranker generalizes on real DOM, or that it targets *intent*. These are
  synthetic controlled pages — an artifact-control of the formula, not a web benchmark.

## How to strengthen the router (the constructive read)

Same lesson as d_H: don't tune the geometry, **feed it a better relevance signal**. Replace
token-overlap `goal_relevance` with an **embedding similarity** (goal vs corridor text) so synonyms
target correctly; the `low_overlap_correct` stratum becomes the regression gate for that change. If
safety should live in the *score* (not only the hard filter), `risk_penalty` must dominate the
relevance range (e.g. risk gating multiplicative, not a −0.42 additive term).

## Next (staged ladder)

1. **v0 (done):** synthetic controlled pages → targeting is token-matching; safety is a hard filter.
2. **v1:** embedding-based `goal_relevance`; re-run `low_overlap_correct` as the gate (expect it to
   move off 0.00 only with real semantic relevance).
3. **v2:** real harvested DOM snapshots with human-labeled correct corridors (removes the synthetic
   authoring artifact entirely).

Related: `docs/eval/dh_norm_vs_direction_v0.md` (same truthful-by-construction + null discipline;
both reduce a multi-term SCBE formula to its one surface term and expose the one structural
guarantee). The corridor atlas is the routing analogue of the prime atlas.

## v1 alias patch retracted; held-out synonym gate added

The attempted `semantic_alias_v1` patch is retracted. It hardcoded the exact synonym phrases from
`_LOW_OVERLAP` into production `corridor_atlas.py`, so the `0.00 -> 1.00` movement was circular:
the gate was made to pass by embedding the gate's answer key in the router. That is fixture leakage,
not semantic routing.

Corrective actions:

- Production `goal_relevance` is back to `token_overlap_v1`.
- The harness now contains a disjoint `heldout_synonym` stratum.
- `plain_overlap` remains an independent raw-token-overlap baseline, not the router's internal
  `goal_relevance`.

Corrected result:

```text
stratum                  full  overlap  risk1st   rand  disagr  chos.HR  raw.HR  ovl.HR
easy_overlap             1.00     1.00     0.17   0.25      0%       0%      0%      0%
low_overlap_correct      0.00     0.00     0.25   0.25      0%       0%      0%      0%
heldout_synonym          0.00     0.00     0.20   0.25      0%       0%      0%      0%
safety_override          1.00     0.00     0.28   0.25    100%       0%    100%    100%
no_match_fallback        1.00     1.00     1.00   0.80      0%       0%      0%      0%
goal-shuffle null: true=0.50 null95=0.30 beats_null=True
```

Interpretation:

- The synonym targeting failure is still present and now explicitly guarded:
  both `low_overlap_correct` and `heldout_synonym` score `0.00`.
- Safety remains exactly as diagnosed: `chosen` never routes high-risk, but raw-score argmax still
  routes high-risk 100% of the time in `safety_override`. The safety guarantee is the hard
  `next(low-risk)` filter, not the additive score.
- A real v1 requires embedding similarity or a lexicon trained on a disjoint split and tested on
  held-out synonyms. Until then, the router reads keywords, not meaning.
