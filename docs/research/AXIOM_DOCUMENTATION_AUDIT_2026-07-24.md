# Axiom Documentation Audit - 2026-07-24

## Scope

This audit reviewed the user-supplied SCBE overview against these executable or
canonical repository surfaces:

- `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/`
- `src/scbe_14layer_reference.py`
- `packages/kernel/src/pipeline14.ts`
- `python/scbe/atomic_tokenization.py`
- `python/scbe/chemical_fusion.py`
- `python/scbe/rhombic_bridge.py`
- `config/scbe_core_axioms_v1.yaml`
- `docs/specs/SCBE_CANONICAL_CONSTANTS.md`
- `benchmarks/scbe_benchmark_standalone.py`
- `benchmarks/results/scbe_benchmark_local_20260405_103757.json`
- focused axiom, atomic-fusion, Rhombic, and formal-reference tests

## Findings

| Draft claim | Audit result | Documentation action |
|---|---|---|
| Five axioms organize the 14-layer pipeline | **Supported** by the axiom-grouped package and tests. | Kept as the structural mesh. |
| The five axioms prove complete agent safety | **Unsupported overreach.** Tests establish selected transform properties, not universal behavior. | Replaced with domain-bounded invariant language. |
| Atomic tokenization is a universal periodic semantic lattice | **Overstated.** Runtime is a finite deterministic approximation with seven semantic classes and selected element prototypes. | Documented exact runtime scope. |
| Chemical Fusion has executable reconstruction algebra | **Supported.** Formula and tests exist. | Added exact formula and source links. |
| Noble-gas analogues preserve a neutral witness state | **Supported as an implementation convention**, not a natural semantic law. | Labeled as a designed mapping. |
| Rhombic Fusion is a cross-modal bridge | **Supported as an optional module.** | Kept outside the numbered L1-L14 mesh. |
| Layer 8 is Hamiltonian CFI / Multi-Well Realms | **Partially supported.** Canonical runtime L8 is realm distance; Hamiltonian CFI exists separately. | Canonical table names L8 realm distance. |
| Layer 12 is only `R^((phi*d)^2)` | **False across current runtimes.** Bounded score, bounded wall, quadratic-exponent cost, and pi-exponent cost regimes coexist. | Added mandatory regime tags. |
| Decisions always include ALLOW/QUARANTINE/ESCALATE/DENY | **Surface-dependent.** Core pipeline14 currently exposes three decisions; other governance surfaces expose four. | Avoided claiming one universal enum. |
| F1 `0.813` is the current reproducible baseline | **Reported but not tied to one current result artifact in this audit.** | Kept only as a reported result with a provenance requirement. |
| Python 3.10+ is canonical | **Incorrect for the package.** `pyproject.toml` requires Python 3.11+. | Corrected. |
| Every action is cryptographically secured through HYDRA | **Not established for every entry point.** Multiple runtimes and optional bridges exist. | Narrowed to tested/integrated paths. |
| Provisional application `63/961,403` | **Present in repository metadata; not independently verified here.** | Labeled as a repository-recorded status. |

## New Executable Surface

`AxiomLens` now provides the requested high-dimensional overlay without
rewriting or flattening the underlying node network:

- five residual channels per node,
- an explicit observation mask,
- explicit evidence coverage and status,
- edge residuals and edge-wise axiom deltas,
- analytical state gradients for unitarity, locality, symmetry, and
  composition,
- analytical temporal gradients for causality,
- weighted combined gradients,
- deterministic 5D-to-3D and stereo offsets for visualization.

The visualization is not used as the decision source. Full five-axis receipts
remain available for audit and training regularization.

## Verification

Baseline before the new lens:

```text
84 passed
```

New lens-focused suite:

```text
12 passed
```

The lens suite includes central finite-difference checks of the analytical
state and time gradients, strict-JSON receipt validation, and normal
repository-root import validation.

Combined focused governance suite:

```text
96 passed
```
