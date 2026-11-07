# Lexical-First Auxiliary Cascade Preregistration

Status: implemented before evaluation on its holdout; no promotion authority.

The full six-view field failed both the 11-query mechanics benchmark and the
31-request independently authored benchmark. The auxiliary views are therefore
retained as a thinner secondary layer rather than discarded or allowed to
overwrite lexical evidence.

## Frozen candidate

For every query, run the existing lexical-only and full six-view searches over
the same catalog. Rank the union lexicographically:

1. lexical-only score, descending;
2. full six-view score, descending only when lexical scores are exactly equal;
3. stable section ID, ascending.

This has no learned parameter and no scalar mixture coefficient. Any higher
lexical score is authoritative. Auxiliary evidence can only break an exact
lexical tie or order candidates when lexical score is zero.

## Controls and gate

- lexical-only baseline;
- no-intervention baseline;
- the rejected full six-view field as a reference;
- three one-to-one shuffled auxiliary-binding controls;
- at least 30 independently authored requests not used to design this cascade.

The candidate must beat lexical-only, no-intervention, and shuffled binding by
more than two pooled sample standard deviations. Anything else is `NO_GAIN` or
`UNDERPOWERED`. Even a passing result cannot promote a tokenizer, probability
table, serving pointer, or neural weight under this experiment's authority.

The first 31-request benchmark is development evidence because its aggregate
result was seen before this implementation. The cascade must be evaluated on a
new hash-disjoint reviewed request set before any capability claim.

## Holdout result

Status: `NO_GAIN`; no promotion.

The holdout contains 31 reviewed requests with zero query-hash overlap with the
development benchmark. Implementation commit `aa139626c` predates benchmark
generation and scoring.

| Arm | MRR | Recall@1 | Recall@5 |
|---|---:|---:|---:|
| full six-view reference | 0.7859 | 0.7742 | 0.8065 |
| lexical-first cascade | 0.7844 | 0.7742 | 0.8065 |
| lexical only | 0.7844 | 0.7742 | 0.8065 |
| no intervention | 0.7843 | 0.7742 | 0.8065 |
| shuffled cascade, every seed | 0.7844 | 0.7742 | 0.8065 |

The cascade was exactly equal to lexical-only and to all three shuffled
auxiliary-binding controls. Its MRR advantage over no-intervention was only
`0.00013`, far below the `0.81615` two-pooled-SD threshold. The full six-view
reference was `0.00154` higher than the cascade but remains non-promotable based
on its earlier controlled failures.

The cascade therefore proves a safety property, not a capability gain:
auxiliary views cannot harm stronger lexical evidence under the lexicographic
rule. They were inert on this holdout. Keep the auxiliary catalog as an external
evidence layer; do not promote it into token probabilities, serving defaults, or
neural weights.

Receipts:

- labels SHA-256:
  `67fef483440ce864ef47cc0f6f0a80065e7f0000705a5a8efca607b8b22839ef`;
- benchmark SHA-256:
  `d2c3a5d961a39d776fe46970a1accd4f59cb7c7271f86468623fc771d0ef9d30`;
- result SHA-256:
  `0be98b5a3bc6388ad35c00a581750a76c874be832ef3bd9de1eb64aefda20f15`;
- runtime result:
  `C:/dev/clay-training-runs/prime-token-catalog-20261106/lexical-first-holdout-20261107/RESULT.json`.
