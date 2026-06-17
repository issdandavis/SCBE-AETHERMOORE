# SCBE-AETHERMOORE — Systems Catalog

A curated map of the systems in this project. The **9 canonical engine systems** are the
authoritative inventory emitted by `scbe systems` (run it for the live list); the families
around them are the larger surfaces built on top. Not exhaustive — the engine alone ships
~59 modules under `python/scbe/`.

_Verified 2026-06-16: `scbe -V` → `scbe 4.2.1`; CLI smoke green; wheel installs + runs._

## Core engine — the 9 canonical systems (`scbe systems`)

| System | What it is | Path | Commands |
|---|---|---|---|
| **bit_spine** | byte-exact binary/hex/trit + tiny Turing-machine substrate | `python/scbe/bit_spine.py` | `bits` `hex` `trits` `inc` |
| **sacred_tongues** | bijective six-tongue byte tokenization (the "keyboard") | `scbe.py` | `enc` `dec` `map` |
| **atomic_tokenization** | semantic element mapping → 6-channel trit state | `python/scbe/atomic_tokenization.py` | `chem atomize` `map` |
| **chemical_fusion** | atomic-state fusion, tau_hat reconstruction, edge tension, valence pressure | `python/scbe/chemical_fusion.py` | `chem atomize` `map` |
| **chemistry_command_stack** | reversible semantic chemistry command primitives | `src/tokenizer/chemistry_command_stack.py` | `map` |
| **atomic_workflow_units** | role/resource/valence/structural workflow units | `src/tokenizer/atomic_workflow_units.py` | `map` |
| **tongue_code_lanes** | tongue→code-lane contract + mismatch classification | `python/scbe/tongue_code_lanes.py` | `map` |
| **ast_cube** | Python AST → cube-token vector matrix | `python/scbe/ast_cube_encoder.py` | `encode-code` `stereo` |
| **rust_ast_cube_hot_loop** | Rust AST encoder hot loop + binary transport | `rust/ast_cube` | `encode` |

## Families built around the engine

- **Cube system** — `cube_token` (one core, many faces), `cube_faces` (7 faces:
  bits/chemistry/roles/audio/code/governance/wolfram), `wolfram_face` (256 elementary-CA
  rules → 256 token values), `tongue_roles`.
- **Geometry / routing** — `geometric_router` (Finsler / Poincaré-ball cost),
  `geometric_scheduler` (streaming + M4 multi-model fleet), `fleet_models`, `board.py`
  (reversible address), `torus.py` (periodic locality + wormhole seams, Q₆), `poly_mountain`
  (Z3-gated route packet).
- **Governance / safety** — **GeoSeal** execution gate (pre-exec policy, fail-closed,
  HMAC-sealed audit), `blocks.py` (Scratch-style destructive double-check),
  `block-destructive.ps1` (machine-wide AI-terminal guard).
- **Polyglot / codegen** — `polyglot.py` (18-language emitter from one CA-opcode core),
  `frontdoor.py` (Sacred-Tongue keyboard round-trip), **CodeCube** (`geoseal code-cube`,
  incl. `--target manifold` twist schedule).

## Product & delivery layer

- **CLIs** — `scbe` (Python, ~30 commands, pip-installable, **v4.2.1**) ·
  `geoseal` + `scbe-patent` + `scbe-scan` (Node, npm bins).
- **Web / product** — landing `docs/index.html` + labs: **ai-materials-bench** (flagship,
  runs 100% in-browser, no signup), `ai-chemistry-set`, `ai-waves-lab`, `atomic-lab`,
  `geoseal-hermes`.
- **Packaging** — PyPI (`numpy` core + extras `[crypto] [api] [science] [browser] [net]
  [dev] [all]`) · npm (`publishConfig` provenance).

## Research & infrastructure

- **Benchmarking** — `scripts/benchmarks/encoder_bench.py`,
  `research/benchmarks/benchmarking-reference.md` + `score-template.json`, `rust/parse_bench`,
  the **corridor-test** design (`research/benchmarks/coordination-test.md`), the Kaggle
  kernel builder (`scripts/kaggle/build_encoder_kernel.py`).
- **Research docs** — `research/aether-manifold/` (fluidic-computer design + rotation
  algebra), `research/marketing/playbook.md`, `articles/` (build-in-public posts).
- **M-TEF research packet** — `docs/research/mtef_research_compendium_2026-06-17.md`
  and the linked PDF preserve the Magneto-Triboelectric Fluid Cell literature synthesis.
  Treat it as concept/prototype evidence, not proof of a working device.

---
_Regenerate the canonical list anytime with `scbe systems` (or `scbe systems --json`)._
