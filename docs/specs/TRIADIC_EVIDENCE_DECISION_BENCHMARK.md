# Triadic evidence decision benchmark

This follow-up addresses the failure found by the multiview perspective run:
free truth, stance, and reason heads memorized labeled states instead of learning
the relationship between complete and partial evidence.

The six tongues remain reversible transport and provenance views. After those
forms align into an invariant core, a separate six-coordinate evidence field is
read by three explicit roles:

1. **Affirm head:** nonnegative evidence supporting the current conclusion.
2. **Counter head:** nonnegative evidence opposing it.
3. **Judge head:** both totals, their signed margin, total activity, overlap,
   confidence, and support ratio.

For signed contribution `c`, the two sides are

`affirm(c) = softplus(3c)/3` and `counter(c) = softplus(-3c)/3`.

Their difference is exactly `c`; their minimum is a nonzero overlap near the
uncertain center. Omitting a perspective coordinate zeros that coordinate in
both roles, and the same judge evaluates the partial view. The reason receipt is
derived: it contains the omitted coordinate when partial and invariant outcomes
differ, and `6` otherwise. It is not a free seven-class label.

Every arm has the same architecture and parameter count:

- aligned tongues with explicit role supervision;
- aligned tongues without role supervision;
- ordinary equal-width exact-byte features with role supervision;
- shuffled tongue bindings with role supervision; and
- fixed random features with role supervision.

The registered traceability gate requires every aligned supervised seed to
reach at least 0.90 on held-out truth, stance, disagreement reason, minority
views, and contribution-sign recovery. Separate two-pooled-SD gates test role
supervision and tokenizer-specific effects. Three seeds are mandatory. The run
does not promote a result automatically.
