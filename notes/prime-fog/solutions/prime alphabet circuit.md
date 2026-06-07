---
tags: [prime-fog, alphabet, symbolic-map, circuit, compression-test]
updated_at: 2026-06-05
---

# Prime Alphabet Circuit

Status: tested as a symbolic compression map. **Interesting, but not a
targeting lane.**

The idea:

```text
prime behavior -> letters -> rotating alphabet circuit -> n-gram graph
```

The important rule is that letters encode behavior, not order. Assigning
`prime #n -> A/B/C/...` is decoration. Assigning letters from `p mod 26`,
`gap mod 26`, `p mod 210`, normalized gap buckets, or ratio-curvature buckets is
a real compression test.

## Probe

Script:

```powershell
python scripts\research\prime_alphabet_circuit_probe.py --limit 1000000 --max-primes 50000 --null-seeds 120
```

Artifact:

```text
artifacts/prime_alphabet_circuit_probe/LATEST.md
```

Protocol:

- Generate 50,000 primes.
- Trim to complete 676-slot circuits (`26 letters x 26 rotations`).
- Apply the rotating alphabet schedule: A, Z, Y, ..., B, then repeat.
- Score adjacent-letter mutual information and trigram concentration.
- Null: shuffle the same behavior letters, then apply the same rotation schedule.

That null preserves the letter inventory and the circuit geometry, while
destroying prime order.

## Result

| Encoding | Mode | Adjacent MI | Null p95 | Verdict |
| --- | --- | ---: | ---: | --- |
| value_mod26 | direct | 0.295313 | 0.002533 | clears |
| value_mod26 | rotating | 1.054404 | 0.775206 | clears |
| gap_mod26 | direct | 0.154680 | 0.002623 | clears |
| gap_mod26 | rotating | 0.832475 | 0.798235 | clears |
| wheel210_bucket26 | direct | 2.594647 | 0.009990 | clears |
| wheel210_bucket26 | rotating | 2.530873 | 0.010163 | clears |
| normalized_gap_bucket | direct | 0.051855 | 0.008276 | clears |
| normalized_gap_bucket | rotating | 0.575890 | 0.615373 | null |
| ratio_curvature_bucket | direct | 0.626219 | 0.010031 | clears |
| ratio_curvature_bucket | rotating | 0.057731 | 0.010151 | clears |

## Interpretation

The alphabet circuit is **not empty**. Real primes produce letter transitions
that beat a same-inventory shuffle. That means the symbolic language carries
order information.

But this is not a new prime-fog locator:

- `value_mod26`, `gap_mod26`, and `wheel210_bucket26` mostly expose known
  modular/wheel constraints.
- `ratio_curvature_bucket` is likely the known weak gap-repulsion / local gap
  dependence already seen in the calibration reframe.
- The rotating circuit expands sparse residue alphabets into fuller coverage,
  but the null includes the same rotation, so the pass comes from prime order,
  not from the rotation alone.

## Verdict

Use this as a visualization and compression substrate:

```text
known primes -> behavior letters -> word graph -> compare to null
```

Do not treat it as a second targeting lane unless a future version beats a
stronger baseline that already accounts for wheel/PNT/residue structure.
