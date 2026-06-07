---
tags: [prime-fog, mod-layers, sieve, wheel, cone-reduction]
updated_at: 2026-06-05
---

# Mod Layers

Status: tested as the exact modular gate stack. **Useful as the search-cone
map; not a new targeting lane.**

The idea:

```text
integers -> mod 2 gate -> mod 3 gate -> mod 5 gate -> ... -> survivors
```

This is the classical sieve/wheel structure written as layers. Unlike decimal
layers, mod layers are directly tied to primality: every layer excludes one
family of composites and leaves all later primes intact.

## Probe

Script:

```powershell
python scripts\research\prime_mod_layer_probe.py --lower 100000 --upper 1000000
```

Artifact:

```text
artifacts/prime_mod_layer_probe/LATEST.md
```

Range:

```text
100,000 <= n < 1,000,000
range_count = 900,000
prime_count = 68,906
base_density = 0.076562
```

## Result

| Layer | Add p | Modulus | Candidates | Fraction | Precision | Recall | Lift | Cand/prime | Digits |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2 | 2 | 450,000 | 0.500000 | 0.153124 | 1.000 | 2.000 | 6.53 | 0.301 |
| 2 | 3 | 6 | 300,000 | 0.333333 | 0.229687 | 1.000 | 3.000 | 4.35 | 0.477 |
| 3 | 5 | 30 | 240,000 | 0.266667 | 0.287108 | 1.000 | 3.750 | 3.48 | 0.574 |
| 4 | 7 | 210 | 205,714 | 0.228571 | 0.334960 | 1.000 | 4.375 | 2.99 | 0.641 |
| 5 | 11 | 2310 | 187,013 | 0.207792 | 0.368456 | 1.000 | 4.812 | 2.71 | 0.682 |
| 6 | 13 | 30030 | 172,627 | 0.191808 | 0.399161 | 1.000 | 5.214 | 2.51 | 0.717 |
| 7 | 17 | 510510 | 162,471 | 0.180523 | 0.424113 | 1.000 | 5.539 | 2.36 | 0.743 |
| 8 | 19 | 9699690 | 153,918 | 0.171020 | 0.447680 | 1.000 | 5.847 | 2.23 | 0.767 |
| 9 | 23 | 223092870 | 147,225 | 0.163583 | 0.468032 | 1.000 | 6.113 | 2.14 | 0.786 |
| 10 | 29 | 6469693230 | 142,134 | 0.157927 | 0.484796 | 1.000 | 6.332 | 2.06 | 0.802 |
| 11 | 31 | 200560490130 | 137,535 | 0.152817 | 0.501007 | 1.000 | 6.544 | 2.00 | 0.816 |
| 12 | 37 | 7420738134810 | 133,804 | 0.148671 | 0.514977 | 1.000 | 6.726 | 1.94 | 0.828 |
| 13 | 41 | 304250263527210 | 130,545 | 0.145050 | 0.527833 | 1.000 | 6.894 | 1.89 | 0.838 |
| 14 | 43 | 13082761331670030 | 127,524 | 0.141693 | 0.540338 | 1.000 | 7.057 | 1.85 | 0.849 |
| 15 | 47 | 614889782588491410 | 124,847 | 0.138719 | 0.551924 | 1.000 | 7.209 | 1.81 | 0.858 |

## Reading

Mod layers are the real "where not to dig" map.

- Recall stays 1.0 because all true primes in the range survive every small
  prime divisibility gate.
- Precision rises from 7.66% base density to 55.19% after layers through 47.
- The first four layers (`2,3,5,7`, modulus 210) already do most of the cheap
  narrowing: candidates per prime falls from 13.06 raw integers/prime to 2.99
  candidates/prime.
- Later layers still help, but marginal decimal compression gets small:
  `+0.301`, `+0.176`, `+0.097`, `+0.067`, then below `+0.05` digits per new
  layer.

## Verdict

This is not a second lane. It is the legal-road map for the number line:

```text
mod layers define the open roads;
density estimates how far until the next checkpoint;
local targeters still have to beat that baseline.
```

So if the search is geography, mod layers are the roads and closed bridges.
They tell us where not to dig and how expensive each remaining corridor is.
