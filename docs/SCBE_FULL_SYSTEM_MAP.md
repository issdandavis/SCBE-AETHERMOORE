# SCBE Full System Map

Status: working map from repository inspection on 2026-06-14.

This repository is a working lab plus product monorepo. It is not one app. It
contains canonical runtime code, product surfaces, research/theory notes,
training pipelines, operator workflows, lore-derived corpus material, and
generated evidence.

## Authority Chain

Use these first when files disagree:

1. `docs/specs/CANONICAL_FORMULA_REGISTRY.md`
2. `docs/CANONICAL_SYSTEM_STATE.md`
3. Runtime entrypoints: `api/main.py`, `src/api/main.py`, `src/index.ts`
4. Tests and benchmark lanes
5. Public docs
6. Notes, articles, archive, generated artifacts

The formula registry separates the unbounded harmonic wall
`H(d*, R) = R^((phi * d*)^2)` from the bounded compatibility scorer
`score = 1 / (1 + d + 2 * phaseDeviation)`.

## Repository Zones

- Product/runtime: `public/`, `app/`, `api/`, `src/api/`, `products/`,
  `scripts/aetherbrowser/`
- Platform core: `src/harmonic/`, `src/crypto/`, `src/governance/`,
  `src/tokenizer/`, `src/tongues/`, `src/coding_spine/`, `python/scbe/`
- Agentic/operator: `src/fleet/`, `packages/agent-bus/`, `agents/`,
  `scripts/system/`, `.agents/skills/`
- Research/training: `notes/`, `notebooks/`, `training/`, `training-data/`,
  `scripts/train/`, `scripts/eval/`, `scripts/benchmark/`
- Lore/corpus: `content/book/`, `book/`, `articles/`, `src/spiralverse/`
- Generated/evidence/noisy: `artifacts/`, `dist/`, `.hypothesis/`,
  `node_modules/`

## Core Runtime

The public runtime is an AI governance system based on hyperbolic geometry,
Sacred Tongue weighting, risk tiers, audit receipts, and post-quantum crypto.

Key paths:

- `src/index.ts`: package-level scan/isSafe API
- `packages/kernel/src/pipeline14.ts`: canonical TypeScript 14-layer pipeline
- `src/harmonic/`: harmonic wall, hyperbolic, audio, spectral, temporal,
  sacred tongue, and geometry modules
- `src/governance/`: runtime gates, negative tongue lattice, trichromatic
  governance, chemical bonds, bijective tamper checks
- `src/crypto/`: GeoSeal, PQC, Sacred Tongues, chromatics, code lattice,
  AetherLex seed material

## Sacred Tongues And Tokenizer

The Sacred Tongues are six phi-weighted semantic axes and token grids:

- KO, AV, RU, CA, UM, DR
- weights: `phi^0` through `phi^5`
- language map: Python, TypeScript, Rust, C, Julia, Haskell
- extended lanes: Go and Zig

Key paths:

- `src/ca_lexicon/__init__.py`: 64-row CA substrate linking op id, trit vector,
  8D feature vector, risk chi, valence, and language templates
- `python/scbe/ca_opcode_table.py`: CA opcode/trit/feature table
- `python/scbe/tongue_isa.py`: CA opcode compiler to primary target languages
- `python/scbe/tongue_isa_binary.py`: STIB binary format
- `src/crypto/sacred_tongue_payload_bijection.py`: canonical JSON/bytes/tongue
  round-trip proof
- `src/tokenizer/ss1.ts`, `src/crypto/sacred_tongues.py`: byte/token bijection
- `notes/System Library/Tokenizer Vault/`: tokenizer design notes

## One Alphabet, Many Decoders

The chemistry/tokenizer theory is explicit: one fixed alphabet can be read as
chemistry, math, pipeline semantics, governance, code, and narrative.

Key paths:

- `notes/theory/atomic-tokenizer-chemistry-unified.md`
- `python/scbe/atomic_tokenization.py`
- `python/scbe/chemical_fusion.py`
- `src/tokenizer/atomic_workflow_units.py`
- `src/tokenizer/chemistry_command_stack.py`

Current behavior:

- Natural/code tokens map to semantic element families, trit vectors, dual state,
  trust, resilience, and adaptivity.
- Workflow units carry semantic lanes, chemistry lanes, byte signatures, valence
  slots, bond capacity, reactivity, and resource costs.
- Direct element symbols are recognized as material chemistry; other tokens get
  structural chemistry lanes.

## Real Chemistry And Reaction Packets

The repo has a real computational chemistry lane plus symbolic chemistry lanes.

Key paths:

- `scripts/reaction_cli.py`: reaction packet CLI
- `python/scbe/reaction_balance.py`: stoichiometry balancer
- `python/scbe/geometry_view.py`: RDKit geometry descriptors
- `python/scbe/controlled_substances.py`: controlled-substance screen
- `python/scbe/reaction_state.py`: signed reaction-state packets
- `python/scbe/reaction_harness.py`: bijective/lossy/recoverable reaction checks
- `scripts/benchmark/compound_decomposition_recomposition.py`: RDKit
  decomposition/recomposition benchmark

## Code And Compiler Systems

Code is represented through deterministic opcode/tongue/IR layers before target
emission.

Key paths:

- `docs/TONGUE_CODING_LANGUAGE_MAP.md`
- `scripts/agents/scbe_code.py`
- `src/geoseal_cli.py`
- `tests/agents/test_scbe_code.py`
- `tests/cli/test_cross_build_ir.py`
- `tests/cli/test_cross_build_cli.py`

Current compiler lane:

- CA opcodes compile to Python, TypeScript, Go, Rust, C, Julia, Haskell, and Zig.
- Bijection is preserved by trace comments such as `add (0x00)`.
- Runtime preludes exist for generated CA programs.

## Math, Color, Music, And Harmonic Modes

These are structural lanes, not only metaphors.

Prime/number theory:

- `scripts/experiments/prime_vibration_edge_system.py`
- `src/tokenizer/nsm_primes.py`
- `tests/experiments/test_prime_vibration_edge_system.py`

Color/chromatic theory:

- `src/crypto/gallery_chromatics.py`
- `src/crypto/quantum_frequency_bundle.py`
- `src/harmonic/spectral_identity.py`
- `articles/12_trichromatic_forgery_resistance.md`

Music/action schema:

- `src/training/musical_schema.py`
- `src/audio/tongue_prosody.py`
- `src/crypto/choral_render.py`

## Agent, Fleet, Browser, And Operator Systems

The agent layer routes tasks through governance, model selection, receipts,
and deterministic tool surfaces.

Key paths:

- `packages/agent-bus/`: governed Node agent bus and Compass front door
- `packages/agent-bus-py/`: Python agent bus
- `src/fleet/`: fleet manager, Polly Pads, drone fleet, dispatch, governance
- `src/aetherbrowser/`: browser agent routing and provider execution
- `agents/`: local agent implementations
- `.agents/skills/`: local skills for governance, training, ops, browser swarm,
  disk management, docs, revenue, story, research, and more
- `scripts/system/ops_control.py`: cross-talk packet system

Important model: Compass formations include forge, scribe, broadcast, council,
scout, and field. Anything external becomes an adapter only if it has a
deterministic boundary, governance metadata, receipt output, and benchmark
coverage.

## Lore And Product Relationship

The README states the lore is the original encoding system:

Spiralverse logs -> custom tokenizer -> 6D semantic coordinate system ->
14-layer governance pipeline -> patent.

Key paths:

- `src/spiralverse/`
- `content/book/`
- `articles/05_six_sacred_tongues.md`
- `articles/01_the_spiralverse_introduction.md`
- `book/ai-governance-fundamentals/`

The repo keeps lore and runtime separate, but the lore is not decoration; it is
the origin corpus and naming/encoding layer.

## Working Conclusion

The full system is best described as a deterministic, governed symbolic
substrate:

`binary/hex/trit/ternary -> Sacred Tongue token atoms -> semantic/chemistry/code/math/color/music/persona modes -> governed runtime receipts -> target code, voice, documents, agents, or product actions`.

The immediate architectural gap is not another single integration. It is a
canonical internal lattice schema that can bind token atoms, bonds, mode
projections, chemistry values, compiler opcodes, numeric notations, harmonic
features, and GeoSeal receipts in one packet.
