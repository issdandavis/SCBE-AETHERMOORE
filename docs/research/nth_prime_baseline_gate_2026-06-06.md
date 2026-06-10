# Nth-Prime Baseline Gate

Date: 2026-06-06

Status: baseline comparator.

## Purpose

This is the engineering baseline for the prime atlas/fog-of-war work. It answers
the practical question:

```text
Given index n, recover p_n exactly.
```

The geometry/operator probes only earn operational value if they reduce work
against this baseline or improve one of its stages.

## Method

Standard 1-based indexing:

```text
nth_prime(1) = 2
```

Pipeline:

```text
n
  -> Dusart/Rosser corridor [lower, upper]
  -> count primes below lower
  -> base primes up to sqrt(upper)
  -> segmented wheel sieve over [lower, upper]
  -> recover p_n exactly
```

QueenJewels uses the convention `p_0 := 2`, so compare with an index shift.

## Smoke Results

Plain Python, not speed-optimized:

```text
n=10         p_n=29        elapsed 0.15 ms
n=1,000      p_n=7,919     elapsed 1.11 ms
n=10,000     p_n=104,729   elapsed 12.70 ms
n=100,000    p_n=1,299,709 elapsed 158.92 ms
n=1,000,000  p_n=15,485,863 elapsed 2371.83 ms
```

For `n=1,000,000`:

```text
corridor              [15,479,360, 16,441,335]
corridor width        961,976
count before lower    999,615
remaining index       385
base primes           559
segments scanned      4
candidates touched    256,526
composites marked     198,479
```

## Verdict

`NTH_PRIME_BASELINE_READY`

This is a correctness/instrumentation baseline. It is not intended to match the
QueenJewels LLVM implementation or a production-grade prime-counting engine.

Artifacts:

- `artifacts/nth_prime_baseline_gate/summary.json`

## Update 2026-06-09 — sublinear count step (the floor-lever)

The original "count primes below lower" step was a **full Eratosthenes sieve to
~pₙ** (`len(simple_sieve(lower-1))`), and the corridor was validated by ~3 such
sieves (`nth_prime_corridor` checks π(lower-1) and π(upper)). Profiling located
the runtime floor there, not in the corridor:

```text
count-below-lower (full sieve to ~15.48M)   ~815 ms   <- the floor
corridor segment sieve (962k-wide band)      ~54 ms
ratio                                        ~15x
```

So the corridor's 256,526 candidate-touches were never the work budget; the
count step was, and it scaled with x. The corridor being ~18x looser than a
tight Dusart band only ever touched the ~2% segment stage.

**Fix:** the count step now uses a **sublinear π(x)** — `prime_pi_lucy`
(Lucy_Hedgehog / Dirichlet-hyperbola method). It evaluates the running count
only at the ~2·√x distinct `floor(x/i)` "ratio" points and lets the primes ≤ √x
sieve across them in ever-larger steps. Time ~O(x^0.75), memory O(√x).

```text
count step π(15,479,359):  full sieve 815 ms  ->  Lucy 26.6 ms   (31x, exact)
end-to-end nth_prime(1e6):       2371 ms       ->      340 ms     (7x)
count-step work (ratio-keys):    7,867   vs corridor candidates 256,526
```

**Acceptance gate** (`tests/research/test_nth_prime_baseline_gate.py`):
1. exactness — `prime_pi_lucy` matches the full-sieve oracle and the π(x) table;
   `nth_prime(10**6) == 15485863` preserved end-to-end;
2. floor moved — `count_step_keys < candidates_touched` (the count is no longer
   the dominant stage).

**Honesty boundary.** This is not new mathematics. The ratio/hyperbola method is
the **Meissel–Lehmer family** (1870s–1980s; the modern frontier is
Lagarias–Miller–Odlyzko / Deléglise–Rivat at ~O(x^{2/3})). It is a *compute*
lever on a known-solution count, not a *predict* lever — it adds zero signal to
the fog-of-war search, which stays closed. With the count floor gone, the
corridor segment is now the largest single stage, so tightening the corridor to
a modern Dusart band is the next (and only then worthwhile) marginal lever.
