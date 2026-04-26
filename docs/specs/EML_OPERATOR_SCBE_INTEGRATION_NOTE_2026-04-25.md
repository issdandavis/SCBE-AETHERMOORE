# EML Operator Source Review And SCBE Integration Note - 2026-04-25

## Source Boundary

Primary source:

- Andrzej Odrzywolek, "All elementary functions from a single binary operator", arXiv:2603.21852v2, submitted March 23, 2026 and revised April 4, 2026.
- arXiv link: https://arxiv.org/abs/2603.21852

Related public explainer:

- Sabine Hossenfelder, "Mathematician Collapses All Functions to One Weird Formula", Backreaction, April 20, 2026.
- Link: https://backreaction.blogspot.com/2026/04/mathematician-collapses-all-functions.html

Important critique / boundary:

- Robert Smith, "Not all elementary functions can be expressed with exp-minus-log", April 14, 2026.
- Link: https://www.stylewarning.com/posts/not-all-elementary/

## Verified Core Claim

The paper defines:

```text
eml(x, y) = exp(x) - ln(y)
```

The verified narrow claim is that `eml` plus the constant `1` generates the standard scientific-calculator basis used in the paper. This includes the calculator-style repertoire: constants such as `e`, `pi`, and `i`; arithmetic operations; exponentiation; and common algebraic/transcendental functions.

The paper also states that EML expressions form uniform binary trees:

```text
S -> 1 | eml(S, S)
```

This is the part that matters for SCBE: it gives a uniform expression grammar that can be compiled, searched, and tested.

## Do Not Overclaim

Do not write "all mathematics" or unrestricted "all elementary functions" in SCBE docs without the qualifier.

Safer wording:

```text
EML plus 1 constructively generates the scientific-calculator elementary-function basis studied in Odrzywolek 2026.
```

The critique argues that the result does not cover every meaning of "elementary function" used in broader pure mathematics, especially definitions closed under arbitrary algebraic adjunctions / polynomial roots. Treat that as a reviewer-risk boundary, not as a blocker for engineering experiments.

## SCBE Relevance

The useful part for this repo is not the hype. The useful part is the uniform tree grammar.

Possible SCBE integration lanes:

- `src/tokenizer/`: add an experimental EML-tree feature head that emits deterministic tree metadata, not claims of mathematical universality.
- `training-data/`: generate small JSONL records where a known formula, its EML expression, and its binary/token trace are paired.
- `scripts/benchmark/`: add a null-control benchmark that asks whether EML-tree features improve symbolic recovery versus byte histogram or token features.
- `src/api/free_llm_routes.py`: route EML experiment prompts through the existing agent bus as offline/audited work packets.
- `scripts/revenue/daily_cash_sprint.py`: use EML as one research-offer topic only after a runnable demo exists.

## Prototype Rule

First prototype should be small and falsifiable:

1. Implement `eml(x, y)` and a tiny tree evaluator.
2. Encode only paper-verified examples such as `exp(x) = eml(x, 1)` and `ln(x) = eml(1, eml(eml(1, x), 1))`.
3. Compare numerical output against Python `math` / `cmath`.
4. Save pass/fail JSON with source formula, EML tree, inputs, outputs, and error tolerance.
5. Only then connect to tokenizer or training data.

## Ternary Candidate Boundary

The transcript-style material discusses a possible constant-free ternary operator:

```text
T(x, y, z) = (exp(x) / ln(x)) * (ln(z) / exp(y))
```

It is algebraically true that `T(x, x, x) = 1` wherever the expression is defined. That only proves a self-seeding property. It does not prove full universality. Treat it as an experiment candidate, not a system claim.

## Immediate Implementation Target

Create an experimental, isolated module before touching production tokenizer logic:

```text
scripts/experiments/eml_tree_probe.py
tests/experiments/test_eml_tree_probe.py
artifacts/experiments/eml_tree_probe/
```

Minimum accepted result:

- `exp(x)` reconstruction passes over real and complex sample points.
- `ln(x)` reconstruction passes over positive real sample points.
- ternary `T(x,x,x)` self-seeding check passes for valid positive samples excluding `x=1`.
- failure cases around invalid domains are explicit, not hidden.

## Current Local Artifact

Implemented in:

```text
scripts/experiments/eml_tree_probe.py
tests/experiments/test_eml_tree_probe.py
```

Generated experimental SFT lane:

```text
training-data/sft/eml_operator_v1.sft.jsonl
training-data/sft/eml_operator_v1_manifest.json
```

Current local record count: `16`.

This dataset is intentionally smaller than external prototype claims because it only includes identities verified by the local probe:

- `exp(x) = eml(x, 1)`
- `ln(x) = eml(1, eml(eml(1, x), 1))` on positive real samples
- `T(x,x,x)=1` for valid samples
- one explicit claim-boundary record

Promotion rule: do not merge this into the main coding-training manifest until it has a held-out eval, null control, and a clear comparison against the existing binary interpretation matrix lane.
