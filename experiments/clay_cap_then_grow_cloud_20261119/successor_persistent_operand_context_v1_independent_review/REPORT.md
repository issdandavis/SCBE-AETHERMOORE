# Independent Review: Persistent Operand Context

Verdict: **PASS_REPAIRED_PROTOTYPE_SCOPE**. Commit
`d864f35d085a148a8e6f3171fd1ad9f0888b6bf4` was not admission-correct as
written; the two defects below were repaired and independently rerun. This is
still a prototype/smoke pass, not evidence that the successor improves Clay.

## Correctness defects repaired

1. `generate_text` formerly rebuilt context from the prompt row. A
   context-permuted model therefore could not be evaluated with its sealed,
   independent control context. Generation and evaluation now take an explicit
   context row, keep its five operand/opcode features at every autoregressive
   step, and vary only the decode-position feature.
2. The preregistration retained the seed-level two-pooled-SD rule but omitted
   the finite-held-out uncertainty required when per-example ledgers exist. The
   runner now has a fail-closed admission decision requiring, for exact and
   operation-stratified macro accuracy, both the original 3-seed/2SD/3-of-3
   gate and a strictly positive one-sided 95% paired-bootstrap lower bound.
   Nonzero-per-operation, out-of-support add/multiply, retention/frozen identity,
   and independent-replay gates remain conjunctive. A test proves an identical
   one-row advantage cannot pass merely because seed variance is zero.

The target-shuffle description was also corrected from “deranged” to
“shuffled.” The inherited implementation does not promise a no-fixed-point
target derangement when duplicate target strings exist. Its behavior was not
changed. The context-permuted arm is a true bijective no-fixed-point
derangement for every train/held-out split and every sealed seed.

## Independent evidence

- Parameters: pinned 276-token core gives 140,820 adapter/head parameters;
  `Linear(6,192)` adds exactly 1,344; total is exactly 142,164.
- Dataset: SHA-256
  `c9945f6b8037557e72e167117a58adb2b4bb51bfdcb63da50e56150f49495ad0`;
  1,534 train and 1,509 held-out rows. Add/multiply result supports remain
  disjoint; subtraction result support remains equal.
- Frozen path: `e`, `g`, and `count_head` are excluded from the selected
  trainable modules and remained bit-identical through the bounded update.
- Tests: 10 Pytest tests passed; Python compilation, Ruff, bounded smoke, and
  `git diff --check` passed.
- Machine-readable receipt: `REVIEW_RESULT.json`, SHA-256
  `a7624b1e9f03ef4f68689c15a399d0f66010bae2026741043a1c4a7eb5b57df5`.

No cloud launch, checkpoint/model load, promotion, or push occurred. Full
checkpoint-aware campaign execution and independent replay remain unrun and
unauthorized. Promotion remains `NONE`.
