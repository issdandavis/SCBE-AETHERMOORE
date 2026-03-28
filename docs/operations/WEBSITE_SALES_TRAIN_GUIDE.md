# Website Sales Train Guide

Purpose: keep the homepage and attached funnel pages improving on a fixed rail instead of drifting into random copy edits.

## Primary outcome

Move the right buyer from:

1. attention
2. inspection
3. trust
4. checkout

without turning the site into a wall of internal architecture language.

## Page hierarchy

1. `docs/index.html`
- page type: `launch-surface`
- job: convert cold or warm traffic into one clear purchase decision

2. `docs/product-manual/ai-governance-toolkit.html`
- page type: `support-surface`
- job: reduce purchase friction and increase trust

3. `docs/research/index.html`
- page type: `research-surface`
- job: hold technical proof without hijacking the sales page

4. `docs/articles/index.html`
- page type: `research-surface`
- job: nurture readers who need more context before buying

## Conversion rules

1. One primary offer per page.
2. One primary CTA above the fold.
3. Put proof before lore.
4. Put manual and delivery links before GitHub and repo depth.
5. Do not promise enterprise outcomes from a $29 starter pack.
6. Separate:
- implemented
- documented
- research
- future

## Sales pass sequence

Each pass should produce one concrete improvement:

1. `hero-pass`
- tighten the offer
- clarify buyer outcome
- reduce internal jargon

2. `proof-pass`
- improve trust surfaces
- link manual, delivery, support, technical proof

3. `fit-pass`
- define who the product is for
- define who it is not for

4. `friction-pass`
- shorten confusing copy
- remove unnecessary nav leakage
- keep checkout path obvious

5. `expansion-pass`
- propose adjacent pages:
  - use-case page
  - comparison page
  - quickstart page
  - proof page

## Expansion page standards

Each new page must declare:

- audience
- problem
- proof
- CTA
- parent discovery surface

No orphan pages.

## Model pass roles

Use larger models as bounded reviewers, not unconstrained rewriters.

1. `Closer pass`
- asks: does this page sell?
- focuses on offer, pain, objection, CTA

2. `Operator pass`
- asks: does the buyer know what happens after checkout?
- focuses on delivery, manual, support, friction

3. `Proof pass`
- asks: are claims inspectable and defensible?
- focuses on trust, evidence, and claim boundaries

4. `Expansion pass`
- asks: what next page would improve conversion without bloating the homepage?

## Required outputs per run

1. audit JSON
2. page backlog JSON
3. model prompt packets
4. implementation brief

## Scoring rubric

Score each page 0-10 on:

1. clarity
2. offer strength
3. proof
4. buyer fit
5. CTA discipline
6. friction control

Target:

- homepage average: `>= 8.5`
- no category below `7.5`
