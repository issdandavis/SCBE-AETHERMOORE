# Public Benchmark Source of Truth

## Use this wording in public copy

Primary claim:

`SCBE-AETHERMOORE blocked 91 out of 91 attacks in the current public adversarial suite, with 0/15 clean false positives.`

Short version:

`91/91 attacks blocked. 0/15 clean false positives.`

## What this benchmark refers to

- attack classes: 10
- total attack cases: 91
- clean prompt set for false positives: 15
- comparison baseline on the public proof page:
  - ProtectAI DeBERTa v2: `62/91` blocked
  - keyword filter: `27/91` blocked with high false positives

Primary reference file:
- [SCBE_ADVERSARIAL_ATTACK_SUITE_DESIGN.md](C:/Users/issda/SCBE-AETHERMOORE/docs/security/SCBE_ADVERSARIAL_ATTACK_SUITE_DESIGN.md)

Primary public proof page:
- `https://issdandavis.github.io/SCBE-AETHERMOORE/redteam.html`

## Do not use these in public sales copy without a linked methodology page

- `95.3% detection rate`
- `93%` novel-attack stress number
- `zero false positives` without the benchmark scope attached

Reason:
- they float without test-scope context
- they create contradictory public claims
- they are weaker than the counted benchmark line because they are easier to challenge

## Recommended copy patterns

### Good
- `91/91 attacks blocked in the current public adversarial suite.`
- `0/15 clean false positives on the current public benchmark.`
- `See the red-team proof page and benchmark dataset.`

### Bad
- `95.3% detection rate` with no source
- `zero false positives` with no benchmark scope
- `best in class` without comparison setup

## Landing page routing

Use these URLs by audience:

- proof / security traffic:
  - `https://issdandavis.github.io/SCBE-AETHERMOORE/redteam.html`
- technical / builder traffic:
  - `https://issdandavis.github.io/SCBE-AETHERMOORE/`
- demo / curiosity traffic:
  - `https://issdandavis.github.io/SCBE-AETHERMOORE/demos/index.html`
- direct buyer traffic:
  - `https://aethermoorgames.com/`

## Hard rule

One benchmark sentence. One landing page per audience. No mixed claims.
