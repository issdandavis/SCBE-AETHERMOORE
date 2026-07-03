# Machine Crystal Particle Chemistry Companion

Date: 2026-06-27

## Point

This companion keeps `machine_crystal_pne_cube.py` canonical and adds the two
non-duplicate chemistry pieces around it:

1. Exact balancer wiring from `python/scbe/reaction_balance.py`.
2. Valence-rung annotations from `python/scbe/atomic_tokenization.py`.

## What it validates

Balanced reactions:

```text
2 H2 + O2 -> 2 H2O
CH4 + 2 O2 -> CO2 + 2 H2O
Na+ + Cl- -> NaCl
```

Rejected fake:

```text
H2 -> H2O
```

The fake is rejected because oxygen appears only on the product side.

## Valence rung

Each formula gets:

```text
known_elements
total_valence_slots
total_valence_slots_even
max_valence
max_valence_rung
```

The rung names are:

```text
0 inert
1 monovalent
2 divalent
3 trivalent
4 tetravalent
else polyvalent
```

## Boundary

Exact stoichiometry and formula-level p/n/e ledgers are real.

Valence rung is a bounded routing annotation. It is not a proof that a compound
is stable, safe, synthesizable, thermodynamically favorable, or chemically
complete.

## Validation

Run:

```powershell
python -m python.scbe.machine_crystal_particle_chem
python scripts\system\review_machine_crystal_area.py
```

Expected result:

```text
verdict: PASS
artifact: artifacts/machine_crystal/particle_chem.json
```
