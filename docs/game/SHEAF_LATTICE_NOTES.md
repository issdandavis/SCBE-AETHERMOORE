# Sheaf Cohomology for Lattice Watchers (Spiral Engine)

## Chosen Variant

For MVP we use a **Tarski-style lattice sheaf** approximation on a small watcher complex:

- 0-cochains: local watcher values on nodes (`fast`, `memory`, `governance`, `spectral`).
- 1-cochains: edge differences (`delta0`) across watcher links.
- Fixed-point flow: `Phi_t = (id ∧ L)^t`, where meet `∧` is `min` on [0,1].

This keeps the implementation deterministic and finite-time convergent.

## Why This Variant

- Works directly on bounded lattice values `[0,1]`.
- No linearization required.
- Maps naturally to consensus/gameplay semantics:
  - lower postfixpoint gap => higher global consistency,
  - larger gap => stronger obstruction pressure.

## Runtime Equations

1. Meet diffusion Laplacian (approx):

`L(node) = min(neighbor_values)`

2. Postfixpoint iteration:

`x_{t+1} = min(x_t, L(x_t))`

3. Obstruction score:

`sheaf_obstruction = mean(|x_local - x_fixed|)`

4. Stability factor for Omega:

`sheaf_stability = 1 / (1 + sheaf_obstruction)`

## Gameplay Interpretation

- **Low obstruction**: watchers align globally, mission flow remains stable.
- **High obstruction**: local watcher conflict triggers quarantine/deny drift.
- This acts as a topology-driven "consensus tension" independent of raw wall cost.

## Files

- Implementation: `scripts/spiral_engine_game_sim.py`
- Tests: `tests/test_spiral_engine_game_sim.py`
