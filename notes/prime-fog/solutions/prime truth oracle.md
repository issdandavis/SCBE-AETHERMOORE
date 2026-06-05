---
tags: [prime-fog, verifier, primality, truth-layer]
updated_at: 2026-06-04
---

# prime truth oracle

Hard primality layer for the prime-fog system.

The field map ranks places to look. The truth oracle answers:

```text
is n prime?
what is the next prime after n?
which known anchor values in this artifact are actually prime?
which known anchor values are P(P(n)) superprime anchors?
```

Script: `scripts/research/prime_truth_oracle.py`

## Scope

Exact deterministic Miller-Rabin for unsigned 64-bit integers:

```text
0 <= n < 2**64
```

This covers the current ring-scale anchors by a wide margin. Huge Mersenne-style primes need separate proof machinery.

## Commands

```powershell
python scripts\research\prime_truth_oracle.py --is-prime 531983927
python scripts\research\prime_truth_oracle.py --stream 600000000 5
python scripts\research\prime_truth_oracle.py --segment 100 130
python scripts\research\prime_truth_oracle.py --verify-artifact artifacts\ring_i_cascade_v4_ip\latest_report.json
python scripts\research\run_prime_truth_retrodict_sweep.py
```

`--verify-artifact` runs in superprime mode: it checks `p` is prime and
`pi(p)` is prime.

## Verified

- Retrodict sweep A-G/I/J/K available artifacts: 4,304 entries, 1,645 unique
  anchor values, 0 superprime failures.
- Focused pytest suite: `tests/research/test_prime_truth_oracle.py`

## Related

- [[inverse prime field]]
- [[target lock map]]
- [[Ring I]]
- [[Ring J]]
