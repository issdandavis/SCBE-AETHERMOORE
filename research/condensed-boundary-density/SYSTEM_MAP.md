# Condensed Boundary Density system map

Status: **scoped integration prototype**. Existing components are reused by
concept and verified independently; no current neural checkpoint or trainer is
modified by this work.

## Reused mathematical nodes

| Existing node | Exact local authority | Reused role |
| --- | --- | --- |
| Hodge layers | `C:\dev\loom\clay_hodge.py` | Boundary maps, Hodge Laplacians, closure checks |
| Complex hypergraph | `C:\dev\loom\clay_hypergraph.py` | Hermitian phase-weighted connections and cospectral warning |
| Multiplex thread | `C:\dev\loom\clay_multiplex.py` | Cross-layer identity coupling through a supra-Laplacian |
| Dual-trit relations | `C:\dev\loom\clay_relation_hypergraph.py` | Signed ternary state carried by cells |
| Emergent squads | `C:\dev\clay-wafer-net\clay_wafer_net\emergent_squads.py` | Deterministic behavioral clustering rather than assigned roles |
| Existing neural wafer block | `C:\dev\clay-wafer-net\clay_wafer_net\wafer_core.py` | Fixed-coordinate sparse routing into 64 private opcode experts; matched MoE baseline, not yet a shared recurrent cell fabric |
| 6D Quine map | `C:\dev\clay-wafer-net\clay_wafer_net\wafer_6d_quine.py` | 64 addresses, binary/trit round trips, phase/frequency lanes, routing records, and Q0 template replay |
| Quine-Wafer research gate | `C:\dev\loom\experiments\clay_quine_wafer_cellular_automata_20260824` | Proposed fixed-neighbor recurrent-cell, sector mutation, extraction, reinsertion, and control protocol |
| J-space boundary | `C:\dev\clay-wafer-net\clay_wafer_net\jspace_blender.py` | Explicit finite interior and divergent Poincare boundary |
| PHDM sheaf | `src/harmonic/phdmSheafLattice.ts` | Typed restriction maps and cross-cell obstruction checks |
| Nodal governance graph | `src/crypto/nodal_graph.py` | Stable records, weighted paths, and boundary outcomes |
| Measured Wafer screen | `C:\dev\loom\experiments\clay_warp_weft_wafer_20260824\visible_screen_v4\EXTERNAL_GRADE.json` | 33×2310 full-row-rank Jacobian evidence and failed external attribution gate |

## New bounded surface

```text
typed cells + boundary maps + stable concept IDs
    -> barycentric cell-as-node lift
    -> Hermitian connection Laplacian + diagonal density/mass
    -> coherent cross-layer cluster partition
    -> Galerkin coarse Laplacian and mass matrix
    -> generalized cluster modes Lc u = omega^2 Mc u
    -> stable linear transport step
    -> exact per-cell and per-path contribution ledger
```

The new capability is cluster-level state with mass and frequency while retaining
an exact map back to fine cells. No new tokenizer, neural layer, or security
decision is introduced yet.

## What exists versus what the wafer still needs

| Surface | Current evidence | Honest classification |
| --- | --- | --- |
| 64 opcode addresses and binary/trit mappings | Executable deterministic functions and round-trip checks | Coordinate fabric exists |
| Phase and frequency lanes | Executable complex-valued calculations and finite scans | Mathematical routing field exists; learned benefit untested |
| WaferBlock | Geometry score times trit gate selects top-k private experts | Sparse MoE, not local cell-to-cell recurrence |
| Variable-injection quine | Template replay plus self-check | Q0 reproducible record |
| Recursive meta-cells | CBD composes binary lifts and preserves Galerkin energy | Mechanics validated on synthetic fixtures |
| Shared repeated update rule | Present in the research design, absent from WaferBlock | Must be implemented and compared |
| Sector extraction and reinsertion | Detailed manifest/test protocol in the 2026-08-24 brief | Unexecuted experiment |
| Hardware wafer | Software-to-hardware analogy in the strip-mine map | No physical accelerator or performance evidence |

The nearest build target is a shared recurrent cell rule with the existing 64
addresses as immutable inputs, fixed local plus capped cross-sector candidates,
and optional sector residuals. Its controls are the current private-expert
WaferBlock, a parameter-matched graph/NCA layer, shuffled addresses, and random
gates at the same active-edge and arithmetic budget.

## Required interfaces for a neural integration

Each attached neural cell must provide a stable cell ID, canonical concept ID,
model layer, topological dimension, activation amplitude/phase, positive density,
intrinsic frequency estimate, and optional MultiSign trits. Every cross-layer
edge must provide a typed restriction map and provenance. Missing views remain
absent; deterministic encodings do not count as independent observations.

## Build gate

The next model experiment must include:

1. no-intervention parent;
2. equal-width and equal-parameter ordinary graph layer;
3. one-to-one shuffled cross-layer concept binding;
4. phase/frequency, density, Hodge, and cluster ablations;
5. at least three matched training seeds and a sealed holdout;
6. exact output-ledger reconstruction plus causal removal/injection of traced cells;
7. a stop if source pins, topology, binding IDs, trace equality, or retention fail.

Current real Wafer evidence is not promoted: its internal Jacobians are full rank,
while only one of twelve external effect gates passed. The prototype therefore
has status **MECHANICS_VALIDATED / MODEL_GAIN_UNTESTED**.
