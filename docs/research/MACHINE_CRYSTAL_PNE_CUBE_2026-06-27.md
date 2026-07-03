# Machine Crystal p/n/e Cube

Date: 2026-06-27

## Point

The particle cube is a separate geometry surface:

```text
axis 1: protons
axis 2: neutrons
axis 3: electrons
```

It gives two related lanes:

| Lane | What moves | Gate |
|---|---|---|
| Chemistry | electron axis only | proton and neutron totals stay frozen; electrons/charge balance |
| Nuclear | full p/n/e cube | nucleon number and charge balance |

## Implemented examples

Chemistry:

```text
Na-23 -> Na-23+ + e-
Cl-35 + e- -> Cl-35-
```

Nuclear:

```text
C-14 -> N-14 + e-                  beta-minus
U-238 -> Th-234 + alpha            alpha decay
H-2 + H-3 -> He-4 + n              fusion
U-235 + n -> Ba-141 + Kr-92 + 3n   fission
```

Rejected fakes:

```text
C-14 -> N-15 + e-        rejected: nucleon count changes
C-14 -> C-14 + n         rejected: neutron from nothing
```

## Boundary

This is a conservation-gate surface, not a complete physics engine.

The current implementation uses a small explicit isotope table for the checked
examples. It proves that the p/n/e conservation relation works for these cases
and can be routed through the geometry review command.

## Validation

Run:

```powershell
python -m python.scbe.machine_crystal_pne_cube
python scripts\system\review_machine_crystal_area.py
```

Expected result:

```text
verdict: PASS
artifact: artifacts/machine_crystal/pne_cube.json
```
