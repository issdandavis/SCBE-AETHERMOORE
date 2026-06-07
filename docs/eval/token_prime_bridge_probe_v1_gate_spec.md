---
tags: [eval, prime-atlas, token-bridge, null-discipline, spec, codex-handoff]
updated_at: 2026-06-05
status: IMPLEMENTED — see scripts/eval/token_prime_bridge_probe_v1.py and docs/eval/token_prime_bridge_probe_v1.md
owns: scripts/eval/token_prime_bridge_probe_v1.py + tests/eval/test_token_prime_bridge_probe_v1.py + this doc
---

# v1 Probe Spec: Prime Structure vs Monotone-Index Baseline

## Decision (carry to Codex verbatim)

> v0 is **accepted** as a positive-control wiring test. It proves the bridge can recover an injected
> paired relation, and that shuffled-pair and id-only nulls behave correctly. It does **not** prove
> primes carry useful structure, because the v0 target (`prime_index`, `log(prime_value)`) is a
> monotone view of the same injected latent (`ring`/`sector`/`role`). Replace `primes[prime_index-1]`
> with `prime_index`, `prime_index**2`, or any monotone sequence and the v0 result is identical —
> so v0 tests "two views of one latent are bridgeable," not anything prime-specific.

v1 is the **missing control**. Without it, "prime bridge works" is not falsifiable against
"any smooth index works." Keep v0 as-is; v1 is a new file.

## Goal

Distinguish, under one fixed target and one fixed bridge:

```
"the bridge learned real prime structure"      (prime sidecar wins)
   vs
"the bridge learned any smooth index relation"  (prime ties a monotone sidecar)
```

The headline metric is **`delta_prime_minus_monotone`**, NOT `delta_prime_minus_null`.
Beating the shuffled null is necessary but not sufficient — the null only separates *real pairing
vs scrambled*; it cannot separate *prime structure* from *smooth recoverability*. (Same shape as the
PNT/scale-closure note: pi/C is a re-encoding of the scale axis, carrying nothing beyond `log_value`.)

## Core change from v0: use REAL primes, not an injected latent

v0 synthesized `prime_index` from `(ring, sector, role)`. v1 **must** operate on the actual prime
sequence so every feature is real arithmetic:

- Take `N` consecutive real primes (reuse v0 `_first_primes(N)`; default `N = 4000`), OR primes in a
  fixed high window `[W, W + span]` to avoid small-number edge effects. Pick one, record it.
- All features and the target are computed from these real primes — no constructed index latent.

## Sidecars (the experimental arms)

Run the **same** bridge architecture (same ridge `alpha`, same split seed, same candidate set, same
target) against:

```
A. prime_structure      prime-specific features (below)
B. monotone_index       prime-free smooth features (below)
C. shuffled_null        arm A inputs, training pairings permuted reproducibly
D. random_monotone      (optional) a random-but-monotone sequence's features
```

### RICHNESS PARITY (enforced, not aspirational)

A and B **must have the same feature dimensionality** (pad the smaller with zeros if needed) and use
identical `alpha`, split, seed, target, and candidate set. Otherwise a prime win could be extra
capacity, not structure. The test must `assert prime_features.shape[1] == monotone_features.shape[1]`.

### A. prime_structure sidecar (for prime `p` at index `i`)

Features that are NOT reducible to `i` alone:

```
p mod 6, p mod 30, p mod 210            (wheel residues; encode each as sin/cos phase, not raw int)
gap_prev = p - prev_prime
gap_next = next_prime - p
gap_next / log(p)                       (normalized gap)
residue lane (p mod 30 bucket index)
local P/NP phase                        (fraction of composites in [p-k, p+k])
small_factor_pressure of p-1 and p+1    (neighbor composites; reuse geoseal_cli _small_factor_pressure)
```

> Hard rule: do **not** include `gap_next` (or any direct function of the target) when `gap_next` is
> the target. The input may include `gap_prev` and residues, never the target coordinate.

Implementation note: `token_prime_bridge_probe_v1.py` tightens `local P/NP phase` to a **past-only**
window (`[p-k, p-1]`) rather than centered `[p-k, p+k]`, so the feature cannot see any part of the
future gap being classified.

### B. monotone_index sidecar (equally rich, prime-free)

```
i, log(i), i**2 (rank-normalized), sqrt(i), rank_normalized_i
sin(i / k), cos(i / k)  for a few k
```

This is the control for smooth recoverability: a monotone sidecar **can** capture "gaps grow ~log p
on average," so if prime ties monotone, the prime features added nothing beyond that average trend.

## Target (must NOT be encoded in any input)

First and best target — **`gap_next_bucket`** (prime-specific, not smoothly determined by index):

```
small:  gap_next < 0.75 * log(p)
normal: 0.75 * log(p) <= gap_next <= 1.5 * log(p)
large:  gap_next > 1.5 * log(p)
```

Secondary targets (later, same harness): `residue_transition_bucket`, `next_wheel_lane`,
`local_phase_class`.

## Metric correction (a gap in the outline — read before implementing)

v0's metric was **retrieval rank** among held-out candidates, which assumed each target was unique.
A 3-class bucket target makes retrieval degenerate (many candidates share a bucket → ties → "top1"
is meaningless). For a bucketed target, use **classification**, not retrieval:

- Train the ridge bridge to predict a one-hot of the bucket (or fit a small softmax/argmax head on
  the ridge output); evaluate on held-out primes.
- Headline score = **balanced accuracy** (macro-averaged recall across the 3 buckets) — buckets are
  imbalanced (`normal` dominates), so raw accuracy is inflated by the majority class.
- Report the **majority-class floor** (predict `normal` always) alongside, so a "win" is over the
  real floor, not over zero.

Keep retrieval only if you switch to a continuous, near-unique target (e.g. `gap_next/log(p)` as a
regression with rank retrieval); for the bucket target, balanced accuracy is correct.

## Leakage self-audit (the cheap closure — bake it into the script)

Both prior probes (d_H, corridor, and v0 itself) failed first on injected leakage. v1 must self-check:

```
assert target not in input columns (by construction + a name check)
assert prime/monotone feature dims equal              (richness parity)
report max |corr(input_feature_j, target)| per arm    (no single column should ~determine the target)
assert monotone_index sidecar contains NO prime-derived column (residues/gaps/factor pressure)
```

## Pass/fail logic

Report `prime_structure_score`, `monotone_index_score`, `shuffled_null_score`,
`delta_prime_minus_monotone`, `delta_prime_minus_null` (all balanced accuracy), plus `majority_floor`.

| Result                              | Meaning                                              |
| ----------------------------------- | ---------------------------------------------------- |
| prime ≈ monotone > floor/null       | bridge learns smooth ordering, NOT prime structure   |
| prime > monotone > floor/null       | prime features add real signal                       |
| prime ≈ monotone ≈ floor/null       | no useful signal                                     |
| monotone > prime                    | prime features are noisy/decorative                  |
| prime > null but not > monotone     | necessary but insufficient (the v0 trap, one level up)|

Use a margin, not bare `>`: require `delta_prime_minus_monotone` to exceed the monotone arm's own
shuffled-null p95 spread (i.e. beat sampling noise), not merely be positive.

## Claim discipline (carry verbatim)

If prime features do **not** beat monotone-index:

```
Result is positive-control only. Prime label is decorative.
```

If prime features beat monotone-index:

```
Prime-specific sidecar carries measurable structure beyond monotone scale/index under this target.
```

No stronger claim. (Specifically: not "primes improve an LLM" — that still needs the downstream
ablation v0/v1 both defer.)

## Minimal report schema

```
schema_version: token_prime_bridge_probe_v1
dataset: {source: first_N_primes|window, N, range}
split: {train, test, seed}
target: gap_next_bucket
feature_dim: {prime, monotone}        # must be equal
majority_floor:
prime_structure_score:                # balanced accuracy
monotone_index_score:
shuffled_null_score:                  # mean + p95
delta_prime_minus_monotone:           # HEADLINE
delta_prime_minus_null:
leakage_audit: {max_feature_target_corr_prime, max_feature_target_corr_monotone, dims_equal}
verdict:                              # from the table above
```

## Reuse map (v0 -> v1)

Keep v0's proven machinery; change only inventory + features + metric:

- `_first_primes`, `_primes_upto` — reuse for the real prime sequence.
- `_train_test_split`, `_zscore_fit`, `_ridge_bridge` — reuse unchanged.
- `_rank_retrieval` — **replace** with a `_bucket_balanced_accuracy(predicted_onehot, true_bucket)`.
- `_null_metrics` — reuse pattern (shuffle train pairings), but score with balanced accuracy.
- `_small_factor_pressure` — import from `src/geoseal_cli.py` (count of small residue-primes
  dividing value; 0 for a prime, so apply to `p-1`/`p+1` neighbors).

## Verification checklist (match v0's bar)

```
python scripts/eval/token_prime_bridge_probe_v1.py
python -m pytest tests/eval/test_token_prime_bridge_probe_v1.py -q
python -m flake8 --max-line-length 120 scripts/eval/token_prime_bridge_probe_v1.py
python -m black --check --target-version py311 --line-length 120 scripts/eval/token_prime_bridge_probe_v1.py
python -m py_compile scripts/eval/token_prime_bridge_probe_v1.py
# pin a Python 3.11 interpreter for black/compile (PEP-758 except syntax broke CI twice on 3.14)
# confirm no leftover Python workers
```

## Clean instruction to Codex (paste this)

```
Implement v1 as a non-tautological bridge probe. v0 is accepted as a wiring positive control, but it
is insufficient because prime_index/log_prime are monotone views of the same latent. v1 must compare
prime-specific features (residues mod 6/30/210, gap_prev, normalized gap, residue lane, local P/NP
phase, neighbor small_factor_pressure) against an EQUALLY RICH monotone-index sidecar (i, log i, i^2,
sqrt i, rank-norm, sin/cos i/k) of identical feature dimensionality. Operate on REAL consecutive
primes, not a synthetic index latent. Target = gap_next_bucket {small/normal/large vs 0.75/1.5*log p};
the target must not appear in any input column. Score with BALANCED ACCURACY (buckets are imbalanced)
against a majority-class floor and a shuffled-pair null. The headline metric is
delta_prime_minus_monotone, not delta_prime_minus_null. If prime does not beat the monotone sidecar
by more than null-noise, report "positive-control only; prime label is decorative."
```
