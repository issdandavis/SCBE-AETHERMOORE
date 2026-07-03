# Machine Crystal Geometry Relation Map

Date: 2026-06-27

## Working conclusion

The cube is a crossroads, not the whole city.

In the current SCBE codebase, the cube works as the local 8-address object:
three bits, eight corners, eight token faces, eight Machine Crystal operations.
But the surrounding geometry already extends past cubes:

| Surface | What it does here | Local evidence |
|---|---|---|
| Cube | 3-bit address hub, token-face object, 4x4x4 opcode board pattern | `python/scbe/board.py`, `python/scbe/cube_faces.py`, `python/scbe/ast_cube_encoder.py` |
| Octahedron | Dual executable surface; its 8 faces carry the 8 BF/tape ops | `python/scbe/machine_crystal.py`, `python/scbe/machine_crystal_dual.py` |
| Fano plane | Incidence structure over the 7 nonzero GF(2)^3 addresses | `python/scbe/machine_crystal_dual.py` |
| Cuboctahedron | PHDM bridge between cube and octahedron | `python/scbe/phdm_router.py` |
| Rhombic dodecahedron | PHDM space-filling/context bridge adjacent to cube/cuboctahedron | `python/scbe/phdm_router.py` |
| Tesseract / Rubix-Cubit | 4D lift with 16 vertices and exact twist/state receipts | `python/scbe/rubix_cubit.py` |
| Torus / hypercube | Wraparound embedding and one-bit-neighbor locality | `python/scbe/torus.py` |
| Bhargava cube | Arithmetic overlay on 8 cube entries; three quadratic forms share a discriminant | `python/scbe/machine_crystal_bhargava.py` |
| Bhargava factorial | Growth/factorial values that can feed cube overlays | `python/scbe/machine_crystal_bhargava_factorial.py` |
| p/n/e cube | Proton/neutron/electron conservation surface for chemistry and nuclear processes | `python/scbe/machine_crystal_pne_cube.py` |
| Particle chemistry | Exact balancer projected into p/n/e totals plus valence-rung annotations | `python/scbe/machine_crystal_particle_chem.py` |
| PHDM lattice | Larger polyhedral route network for governance and path checks | `python/scbe/phdm_router.py` |

## What the cube relates to

1. Cube to octahedron:
   The cube and octahedron are duals. In this system, the cube gives the 8
   addresses and the octahedron gives the 8 executable faces. This is the
   Machine Crystal runtime.

2. Cube to Fano plane:
   The 7 nonzero cube addresses form the Fano plane over GF(2)^3. The zero
   address still exists as a Machine Crystal operation, but it is not a Fano
   point.

3. Cube to cuboctahedron:
   The cuboctahedron is the natural bridge between cube and octahedron in the
   PHDM route graph. It should be treated as an adjacency/transition shape, not
   as another name for the cube.

4. Cube to rhombic dodecahedron:
   The rhombic dodecahedron is a connector and space-filling/context surface in
   the PHDM graph. It is useful for routing and neighborhood structure.

5. Cube to tesseract:
   The tesseract is the 4D lift. If the cube is 8 local positions, the tesseract
   is 16 higher-state positions. This is where Rubix-Cubit belongs.

6. Cube to torus/hypercube:
   The torus gives wraparound continuity. The hypercube graph gives one-bit
   adjacency. Together they explain why local moves can wrap and still preserve
   discrete neighbor structure.

7. Cube to Bhargava arithmetic:
   Bhargava's cube uses eight integer entries on a cube and derives three binary
   quadratic forms with equal discriminants. In this repo, that is now an
   arithmetic overlay on the same 8-address object, not a replacement runtime.

8. Bhargava factorial to cube:
   Generalized factorial values are a growth surface that can feed cube entries.
   Current implementation validates exact cases for `S = Z` and arithmetic
   progressions only.

9. Cube to p/n/e conservation:
   The p/n/e cube is a three-axis physical ledger. Chemistry uses the electron
   axis while proton and neutron totals stay frozen. Nuclear processes use the
   whole p/n/e cube, where protons and neutrons can transform or split as long
   as nucleon number and charge balance.

10. p/n/e cube to particle chemistry:
   The exact reaction balancer feeds balanced formulas into the p/n/e ledger.
   The valence rung annotates formulas with routing features from the existing
   periodic-token table.

## Boundaries

* The Machine Crystal is a software execution model, not a physical optical
  computer.
* The Bhargava cube layer validates the equal-discriminant overlay only. It does
  not claim full Gauss/class-group composition.
* The Bhargava factorial layer supports exact `Z` and arithmetic-progression
  formulas only. Arbitrary-set p-orderings are backlog.
* Golden-angle/quasicrystal sampling is a stress/generator surface. Distinct
  hashes do not prove crystallographic aperiodic order.
* The older "angular derivative" wording should stay retired. The implemented
  metric is discrete polyhedral path curvature.
* The p/n/e cube is a conservation gate over selected examples, not a full
  chemistry or nuclear database.
* Particle chemistry exact balancing is real stoichiometry. Valence rungs are
  route annotations, not stability or feasibility proof.

## Validation

Run:

```powershell
python scripts\system\review_machine_crystal_area.py
```

Expected result:

```text
verdict: PASS
artifact: artifacts/machine_crystal/area_review.json
```
