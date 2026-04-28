# DARPA DSO HR001125S0013 — Repo Evidence Stack (v1)

**Purpose:** Map each paragraph of `exec_summary_v1_2026-04-28.md` to specific GitHub repositories
(public + private) and concrete code paths under `issdandavis/`. Used as the back-of-the-summary
evidence anchor; not for direct submission.

**Inventory baseline:** 95 repos enumerated via `gh repo list issdandavis --limit 100` on 2026-04-28.

---

## §1 Thesis — "Platform-agnostic autonomy core, environment-specific constraints"

| Claim | Repo | Code path / artifact |
|---|---|---|
| Autonomy core is identical earth↔space | `SCBE-AETHERMOORE` (private) | `src/fleet/polly-pads/drone-core.ts`, `specialist-modes.ts` |
| Sealed-blind 24/24 bench, p ≤ 3e-4 | `SCBE-AETHERMOORE` | `artifacts/mathbac/MATHBAC_ABSTRACT_SEND_CANDIDATE_v1_2026-04-27.md` |
| Bit-identical Möbius equivariance | `SCBE-AETHERMOORE` | `src/harmonic/pipeline14.ts` (L7 Möbius phase) |
| Mars-drone fail-operational demo | `SCBE-AETHERMOORE` | `artifacts/mathbac/atomic_workflow_composition/mars_drone_resource_decay_demo.json` |
| Patent-pending coverage | `scbe-aethermoore.2` (public) | US Provisional #63/961,403 |

## §2 Math/Computation Contributions (DSO thrust)

| Math object | Repo | Code path |
|---|---|---|
| Hyperbolic trust radius `H(d,pd)` | `SCBE-AETHERMOORE` | `src/harmonic/harmonicScaling.ts`, `src/symphonic_cipher/scbe_aethermoore/` |
| Hyperbolic distance `d_H` | `SCBE-AETHERMOORE` | `src/harmonic/hyperbolic.ts` |
| Phi-weighted Hamiltonian wells | `SCBE-AETHERMOORE` | `src/harmonic/hamiltonianCFI.ts` |
| Chladni nodal-line gating | `hyperbolica` (public) + `SCBE-AETHERMOORE` | geometry-gated memory (Chladni layer in pipeline) |
| Sacred-Tongue 60° basis | `scbe-tongues-toolchain` (public), `six-tongues-geoseal` (public) | Tongue weights KO=1.00 / AV=1.62 / RU=2.62 / CA=4.24 / UM=6.85 / DR=11.09 |
| KL realm 1.5761 b/t, regime 2.9818 b/t | `SCBE-AETHERMOORE` | `artifacts/mathbac/` (sealed-blind audit) |
| Star Fortress / Saturn Ring recovery | `SCBE-AETHERMOORE` | `src/harmonic/adaptiveNavigator.ts` |
| Pipeline integrity (14 layers) | `SCBE-AETHERMOORE` | `src/harmonic/pipeline14.ts`, `LAYER_INDEX.md` |
| 21D state lift | `phdm-21d-embedding` (public HF model + repo) | `issdandavis/phdm-21d-embedding` |

## §3 Defense Application — Drone Autonomy

| Constraint | Repo | Code path / evidence |
|---|---|---|
| 5-class drone taxonomy (RECON/CODER/DEPLOY/RESEARCH/GUARD) | `SCBE-AETHERMOORE` | `src/fleet/` |
| 6-mode specialist (Eng/Nav/Sys/Sci/Comm/MissionPlan) | `SCBE-AETHERMOORE` | `src/fleet/polly-pads/specialist-modes.ts` |
| DTN/BPv7 relay primitives | `SCBE-AETHERMOORE` | `external/codex-skills-live/polyhedral-workflow-mesh/references/relay-and-cadence-patterns.md` |
| Mars-drone comms-budget overrun → `hold` fallback | `SCBE-AETHERMOORE` | `mars_drone_resource_decay_demo.json` (4 degradation_events, 4 readvance_attempts) |
| APNT / PNT-denied geometry-gating | `SCBE-AETHERMOORE`, `hyperbolica` | Chladni nodal layer + Möbius equivariance |
| Fail-operational (not just fail-safe) | `SCBE-AETHERMOORE` | resource-harmonic predictive overrun gate |
| Multi-agent BFT consensus | `SCBE-AETHERMOORE` | `hydra/` (Spine, Heads, Limbs, Ledger) |
| Adversarial sim arena | `SCBE-AETHERMOORE` | `src/security-engine/redblue-arena.ts` |
| Space-domain reference implementation | `orbiter` (fork) | Orbiter Space Flight Simulator integration target |
| 3D pose estimation for drones | `isaac_ros_pose_estimation` (fork) | NVIDIA Isaac ROS pose pipeline |
| Multi-agent RL substrate (JAX) | `Mava` (fork) | InstaDeep multi-agent RL |

## §4 Evidence Anchors (sealed-blind + working code)

| Anchor | Repo | Path |
|---|---|---|
| MATHBAC sealed-blind report | `SCBE-AETHERMOORE` | `artifacts/mathbac/` (full proposal v1, attachment packet, supplemental research, visual appendix) |
| MATHBAC abstract submission packet | `SCBE-AETHERMOORE` | `docs/proposals/DARPA_MATHBAC/` |
| MATHBAC archive (private backup) | `mathbac-archive` (private) | full proposal materials, sealed-blind audit trail |
| Memory archive (private) | `claude-memory-archive` (private) | conversation context across grant cycle |
| Hardware-rooted PQC | `pypqc`, `nethsm`, `pico-hsm`, `wolfHSM` (forks) | post-quantum / HSM substrate |
| Defense-adjacent hyperbolic suite | `cyber-suite` (private) | R^(d²) hyperbolic security suite |
| Entropy defense engine | `Entropicdefenseengineproposal` (private) | proposal evidence |
| Anima k8s | `anima-k8s` (private) | container orchestration substrate |
| Spiralverse protocol | `spiralverse-protocol`, `Spiralverse-AetherMoore` (public) | tongue protocol reference |
| Quantum prototype | `SCBE-QUANTUM-PROTO` (public) | quantum-axiom early implementation |
| Browser-side training | `aetherbrowser` (public) | governed training surface |
| Memory palace | `mempalace` (public) | memory architecture |
| Distinct training lab | `scbe-training-lab` (public) | training pipeline |
| Agent surface | `scbe-agents` (public) | agent registry, dispatch |
| Security gate | `scbe-security-gate` (public) | governance gate reference |
| Public demo | `scbe-aethermoore-demo` (public) | end-to-end demo |
| Nodal network | `scbe-nodal-network` (public) | GeoSeed / nodal substrate |
| Experiments | `scbe-experiments` (public) | research probes |

## §5 Ask — Phase 1 / Phase 2

| Deliverable | Repo / artifact |
|---|---|
| Reproducibility packet (Phase 1) | `SCBE-AETHERMOORE/artifacts/mathbac/` + signed equivariance cert |
| DARPA-furnished scenario harness | new repo `scbe-dso-bench` (TBD; create on award) |
| Earth-domain evaluation | `SCBE-AETHERMOORE` + `aetherbrowser` |
| Space-domain evaluation | `orbiter` (fork) + `mars_drone_resource_decay_demo` |

---

## Cluster Summary (95 repos)

- **Core SCBE (public):** SCBE-AETHERMOORE (private master), scbe-experiments, scbe-training-lab,
  scbe-agents, scbe-security-gate, scbe-aethermoore-demo, scbe-aethermoore.2 (Patent), scbe-tongues-toolchain,
  scbe-nodal-network, six-tongues-geoseal, spiralverse-protocol, Spiralverse-AetherMoore, SCBE-QUANTUM-PROTO,
  hyperbolica, phdm-21d-embedding, aetherbrowser, mempalace.
- **Defense-adjacent (private):** Entropicdefenseengineproposal, mathbac-archive, cyber-suite, anima-k8s,
  claude-memory-archive.
- **Hardware/PQC (forks):** pypqc, nethsm, pico-hsm, wolfHSM.
- **Space/robotics (forks):** orbiter, isaac_ros_pose_estimation.
- **ML infra (forks):** transformers, LocalAI, Mava.

## Authorship Anchors

- UEI **J4NXHM6N5F59** (SAM.gov ACTIVE 2026-04-13)
- CAGE **1EXD5**
- US Provisional **#63/961,403**
- KDP ASIN **B0GSSFQD9G** (*The Six Tongues Protocol*) — public timestamped prior art
- HF user **issdandavis**
- HUBZone certification: in progress (post-MATHBAC sequence per APEX guidance)
