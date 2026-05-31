# Aether-Lattice: Recursive Agentic Workcell Simulator

**Status:** v0.1 simulator, narrow proof harness.

## Claim Under Test

Recursive bounded workcells reduce failure propagation and improve traceability compared with a flat shared-state queue
under the same faulty-agent rate.

This does **not** claim infinite scalability, hardware fabrication, or full AI operating-system completeness. The purpose
is to turn the pocket-dimension idea into measurable routing and containment invariants.

## Architecture

| Component | Simulator Meaning | System Role |
| --- | --- | --- |
| Riemannian spinal log | Append-only hash-linked operation ledger | Causality and identity |
| Phi-indexed addressing | Golden-angle coordinate assigned per operation | Spatial distribution |
| Octree workcells | Recursive bounded pockets | Local state isolation |
| Mobius boundary exit | Validation gate before ledger append | Private-to-public projection |
| Value sink | Verified ledger output | User-visible result |

## Star Fortress Crypto Fallback

The simulator now carries a narrow crypto posture named `star-fortress-v1`.
This is not a new cryptographic implementation. It is a receipt model that
keeps the routing proof aligned with the existing PQC strategy catalog in
`src/crypto/pqc-strategies.ts`.

| Ring | Function | Algorithms / Status |
| --- | --- | --- |
| Outer lattice | Primary active boundary receipt for verified pocket exits | `ML-KEM-1024` + `ML-DSA-87` |
| Middle hash | Conservative fallback receipt for contained exits and lattice-break contingency | `SLH-DSA-256s`, `LMS/XMSS` |
| Inner dev fallback | Deterministic local fallback for tests only | `HMAC-SHA256-dev-fallback`, never marketed as PQ-secure |

The fallback order is triadic:

```text
outer-lattice -> middle-hash -> inner-dev-fallback
```

The production claim is intentionally bounded: verified exits use the outer
lattice receipt model, contained exits produce a middle-hash fail-to-noise
receipt, and the inner fallback is only a local test/development escape hatch.

## Sacred Eggs Alignment

The local Sacred Eggs docs are treated as the authority model for how secrets
move through the boundary:

| Sacred Egg Term | Aether-Lattice Use |
| --- | --- |
| Shell | Public-safe pocket / ledger routing handle |
| Albumen | Context-derived operational key label for a pocket boundary |
| Yolk | CORE secret material; never emitted by this simulator |
| Ring descent | Controlled transition from public routing handle toward operational authority |
| Triadic binding | Three-ring fallback structure used by the Star Fortress profile |
| Fail-to-noise | Bad exits produce a noise receipt instead of corrupt public ledger state |

The strongest local tokenizer-bound Sacred Eggs references are:

- `notes/System Library/Indexes/Tokenizer Sacred Eggs Canonical Reference.md`
- `docs/specs/SACRED_EGGS_GENESIS_PROTOCOL.md`
- `docs/specs/SACRED_EGGS_RITUAL_DISTRIBUTION.md`
- `src/symphonic_cipher/scbe_aethermoore/sacred_egg_integrator.py`
- `src/symphonic_cipher/scbe_aethermoore/sacred_eggs.py`

The related ring/yolk/shell/albumen model is in `src/crypto/sacred_eggs.py`.
It is used here for terminology alignment, while tokenizer-bound hatch logic
should continue to point at the `symphonic_cipher` implementation.

## Baselines

### Flat Queue

Agents read and write through shared global state. Once a faulty agent poisons global state, downstream operations can
inherit the corruption.

### Aether-Lattice

Each operation runs inside a local pocket. Corrupt output cannot append to the spinal ledger unless it passes the boundary
check. Failed exits are contained and retried in a fresh pocket.

## Run

```powershell
python scripts/research/aether_lattice_sim.py --ops 100 --fault-rate 0.05 --seed 42 --octree-depth 3
python scripts/research/aether_lattice_sim.py --ops 100 --fault-rate 0.05 --seed 42 --octree-depth 3 --trials 25
```

Outputs:

- `artifacts/aether_lattice/aether_lattice_sim_report.json`
- `artifacts/aether_lattice/aether_lattice_sim_metrics.csv`
- `artifacts/aether_lattice/aether_lattice_sim_trials.json`
- `artifacts/aether_lattice/aether_lattice_sim_trials.csv`

## Metrics

- **Public corruptions:** corrupted results visible in the global output stream.
- **Containment radius:** how far one failure spreads.
- **Trace cost:** how many steps are needed to trace a result back to its source.
- **Route load:** maximum work concentration on a routing/state surface.
- **Throughput:** verified operations divided by total operations.

## Current Limitations

- This is a stochastic routing model, not a neuromorphic hardware simulator.
- The flat queue baseline is intentionally weak because it models shared mutable state without isolation.
- The Mobius transform is represented as a boundary projection/validation function, not full complex-plane dynamics.
- Future versions should add graded faults, adversarial agents, resource costs, and realistic retry penalties.
