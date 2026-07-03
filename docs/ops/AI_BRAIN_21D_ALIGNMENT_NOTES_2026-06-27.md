# AI Brain 21D Alignment Notes - 2026-06-27

This note records the mismatch found while comparing Issac's pasted 21D conservation-law spec to the current local implementation.

## The mismatch

Current product/repo layout, based on `src/ai_brain/unified-state.ts` from the static audit:

- SCBE/context dimensions: 6
- navigation dimensions: 6
- cognitive dimensions: 3
- semantic dimensions: 3
- swarm dimensions: 3
- total: 21

Pasted conservation-law layout:

- Poincare position: 3
- six tongue phases: 6
- torus coordinates: 3
- trust ring position: 3
- momentum: 3
- energy: 1
- lattice phase: 1
- dimensional flux: 1
- total: 21

Both are valid design surfaces, but they are not the same state. Treating them as identical would corrupt claims, tests, and training data.

## Decision needed

Use two named types until the system proves which one should be canonical:

- `BrainState21Product`: current runtime/product vector used by `src/ai_brain/unified-state.ts`.
- `BrainState21Conservation`: conservation-law vector from the pasted 21D note.

Add a conversion/projection layer only after the fields are explicitly mapped.

## Immediate tasks

- [ ] Add a typed schema for `BrainState21Conservation`.
- [ ] Add a converter design from product state to conservation state.
- [ ] Decide which UI widgets read product state and which read conservation state.
- [ ] Ensure claim artifacts name which 21D layout they used.
- [ ] Never publish a metric that says only "21D" without naming the layout.

## Which 21D works best for what

Use both, but do not blur them.

| Need | Best state layout | Why |
|---|---|---|
| AetherDesk product UI | `BrainState21Product` | It already matches the running product idea: context, navigation, cognition, semantic/tongue state, swarm state. Good for dashboards and action routing. |
| Browser/terminal action gate | `BrainState21Product` first, projected into `BrainState21Conservation` for safety | Product state knows what the user/agent is doing. Conservation state checks whether the action is drifting, incoherent, or unsafe. |
| GeoSeal/PHDM safety checks | `BrainState21Conservation` | The older conservation layout has the useful safety fields: Poincare position, phases, trust ring, momentum, energy, flux. |
| Visual telemetry | Both | Product state explains the work context. Conservation state explains whether the work is stable, risky, or quarantined. |
| Training data labels | Both, but tagged separately | Small models should learn `what task is happening` from product state and `why the gate allowed/blocked it` from conservation state. |
| Patent / architecture support | `BrainState21Conservation` | It maps cleanly to conservation laws, dimensional analysis, and geometric containment language. |
| Real-time orchestration | `BrainState21Product` | It is closer to active agent routing, navigation, and swarm coordination. |
| Claim validation | Neither by itself | Claims need code path + test path + saved artifact. The state layout only defines what was measured. |

## Practical decision

Keep the newer/current product 21D as the runtime state. Keep the older conservation-law 21D as the safety/diagnostic state. Build a projection between them instead of choosing one and deleting the other.

Recommended names:

- `BrainState21Product`: what the AI is doing in the computer/workspace.
- `BrainState21Conservation`: whether that action is geometrically/operationally safe.
- `BrainState21Receipt`: saved summary containing product state, conservation projection, decision, violations, and artifact hash.

This is the clean split:

1. Product state drives the car.
2. Conservation state checks the engine, brakes, lane position, and crash risk.
3. Receipt state proves what happened later.

## Converter goal

The converter should not pretend every field maps perfectly. It should produce a diagnostic projection with confidence flags.

Example mapping direction:

- product context/navigation -> Poincare position and torus coordinates
- product semantic/tongue state -> six tongue phases
- product trust/confidence -> trust ring
- product action delta -> momentum
- detector score / cost -> energy
- runtime mode -> flux
- phason/quasi-space state -> lattice phase

If a field cannot be inferred, mark it `estimated` or `unknown`. Do not silently invent precision.
