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
