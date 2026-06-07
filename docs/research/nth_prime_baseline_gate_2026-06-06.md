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
