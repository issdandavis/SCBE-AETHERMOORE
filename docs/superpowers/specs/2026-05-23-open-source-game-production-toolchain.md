# Open Source Game Production Toolchain

Date: 2026-05-23
Status: R&D production-lane note
Source prompt: GitHub Blog, "Beyond the engine: 10 open source projects shaping how games actually get made" (2026-05-21)
Source URL: https://github.blog/open-source/gaming/beyond-the-engine-10-open-source-projects-shaping-how-games-actually-get-made/
Related repo surfaces:
- `docs/superpowers/specs/2026-05-21-narrative-combat-generator-design.md`
- `docs/superpowers/specs/2026-05-21-go-board-narrative-engine-design.md`
- `docs/superpowers/plans/2026-05-21-narrative-combat-generator-vertical-slice.md`
- `src/narrative_combat/`
- `game/godot/`
- `public/arena.html`

## Purpose

The engine is not the game. The production system needs authoring tools,
asset-prep tools, validation hooks, and an operator/debug surface. This note
turns the open-source game-tooling survey into a concrete SCBE/AetherMoore lane:
use stable external tools where they already solve the job, and wire our agent
bus around validation, export, and build commands instead of asking models to
"chat better."

This is not canonical SCBE governance architecture. It is an adjacent
game-production workflow that can reuse the same principle: agents can propose
content or commands, but deterministic tooling verifies the artifact.

## Production Shape

```
Writer / Designer
  -> Dialogue, encounter, map, asset, and audio authoring tools
  -> Repo import/export adapters
  -> Deterministic validators
  -> Agent bus operator commands
  -> Godot / web / narrative-combat runtime
  -> Smoke tests and playable review
```

The important boundary is simple:

- Tools own file formats and content-editing ergonomics.
- Repo code owns import, validation, deterministic runtime behavior, and tests.
- Agent bus owns orchestration: run exporters, validators, tests, and summaries.
- LLMs may draft or translate, but they do not decide truth.

## Tool Choices

The source article names ten tools: Blockbench, Pencil2D, Pixelorama, Material
Maker, LDtk, Tiled, Audacity, Yarn Spinner, Gum, and Dear ImGui. This lane does
not adopt all ten immediately; it maps each one to the production job it could
own, then prioritizes the tools that match current repo surfaces.

### Dialogue: Yarn Spinner First

Use Yarn Spinner as the first serious dialogue-authoring target because it
separates writer-owned branching script from programmer-owned runtime wiring.
That maps cleanly to the existing narrative-combat rule: structured truth first,
rendering second.

Initial repo target:
- Add an export adapter from narrative-combat fight packets to dialogue nodes.
- Validate every node has stable IDs, explicit choices, and no unreachable branch.
- Keep generated `.yarn` output under a generated/artifact lane until we choose a
  canonical source-of-truth location.

Future operator command:

```text
/game dialogue export --encounter boss_duel_demo --format yarn
/game dialogue validate path/to/file.yarn
```

### Maps and Encounters: LDtk or Tiled

Use LDtk when entity typing matters most: encounters, doors, features, hazards,
safe zones, and board nodes with enums. Use Tiled when the first need is broad
tilemap compatibility.

For this repo, LDtk is the better default for the narrative-combat lane because
the existing engine is feature/entity-driven:
- `Feature.kind`
- `innate_test`
- `consequence`
- terrain constraints
- encounter objective

Initial repo target:
- Define a small JSON schema for `EncounterMap`.
- Write a loader that accepts LDtk-style entity JSON first, with a Tiled adapter
  later if the Godot lane needs it.
- Validate that map entities can round-trip into `src/narrative_combat.models`.

Future operator command:

```text
/game map validate path/to/encounter.ldtk
/game encounter build --map path/to/encounter.ldtk --seed 1337
```

### 2D Assets: Pixelorama

Pixelorama fits the fast 2D lane: sprites, tilesets, animations, PNG sequences,
and spritesheets. It is a practical first art tool for the web/Godot slice
because it produces assets the runtime can consume without a custom art stack.

Initial repo target:
- Reserve an asset manifest format that records source file, exported frames,
  spritesheet path, frame size, license, and intended runtime lane.
- Add a validator that catches missing frames, inconsistent dimensions, and
  untracked generated outputs.

Future operator command:

```text
/game asset validate assets/game/manifest.json
```

### 2D Animation: Pencil2D As A Clean Animation Source

Pencil2D is a separate candidate from Pixelorama. Pixelorama owns game-native
pixel spritesheets; Pencil2D owns hand-drawn frame-by-frame animation, roughs,
camera passes, and image-sequence exports.

Initial repo target:
- Treat Pencil2D output as animation-source material, not runtime truth.
- Import only exported image sequences or spritesheets through the same asset
  manifest used for Pixelorama.
- Validate frame count, dimensions, naming, and intended runtime lane before any
  generated animation is consumed by Godot or the web runtime.

Future operator command:

```text
/game animation validate assets/game/animations/manifest.json
```

### Procedural Materials: Material Maker Later

Material Maker is useful when the art direction needs repeatable procedural PBR
materials rather than one-off painted textures. It is relevant for Godot and
3D/2.5D lanes, but it is not required for the current narrative-combat smoke.

Initial repo target:
- Defer until a scene actually consumes procedural materials.
- When adopted, record the source graph, exported texture set, target shader,
  license, and runtime path in the asset manifest.
- Validate that every exported material has the expected albedo/normal/roughness
  files before a build uses it.

Future operator command:

```text
/game material validate assets/game/materials/manifest.json
```

### 3D Assets: Blockbench Later

Blockbench is useful when the project needs low-poly 3D models, pixel-textured
objects, or simple animated props. It is not the first dependency for the current
narrative-combat vertical slice.

Initial repo target:
- Defer until there is a specific Godot scene or 3D prop requirement.
- When adopted, prefer glTF export and validate scale, origin, animation names,
  and texture paths.

### Audio: Audacity For Prep, Manifest For Runtime

Audacity is the practical audio-prep layer: trim, clean, loop, batch export. The
repo should not depend on Audacity directly; it should validate the outputs.

Initial repo target:
- Add audio manifest fields for sample rate, channels, loop flag, duration,
  loudness notes, source file, and runtime path.
- Validate presence and basic metadata with a Python script later.

Future operator command:

```text
/game audio validate assets/audio/manifest.json
```

### Runtime UI Layout: Gum As A Future UI Authoring Candidate

Gum belongs in the production map as a UI layout/editor candidate: menus, HUDs,
states, anchors, nested containers, and XML layouts that a runtime can load. It
is not the same job as the Arena operator surface.

Initial repo target:
- Defer until there is a real in-game UI/HUD need outside the existing web
  interface.
- Keep any Gum exports behind a small adapter that validates screens, states,
  and referenced assets.
- Do not replace the browser Arena/operator UI with Gum; this is for game
  runtime UI, not repo operations.

Future operator command:

```text
/game ui validate assets/game/ui/manifest.json
```

### Debug UI: ImGui Pattern, Browser Operator Surface Now

Dear ImGui matters here less as a direct dependency and more as the product
pattern: immediate, cheap debug controls should sit next to the running system.
For this repo, the immediate surface is the web Arena/operator panel and the
agent bus CLI, not a C++ ImGui dependency.

Initial repo target:
- Treat `public/arena.html` as the operator/debug surface for game generation.
- Add command verbs that run deterministic validators and targeted smokes.
- Keep raw model output collapsible; the default user-facing transcript should
  show structured operator summaries and command results.

Future operator commands:

```text
/game smoke narrative-combat
/game packet render --seed 1337
/game debug explain-failure artifacts/game/latest.json
```

## Agent Bus Contract

The agent bus should make game work executable, not more verbose. A model can
draft a scene, propose a map entity, or suggest a dialogue branch, but the bus
must turn that into one of these bounded operations:

| Operation | Deterministic check |
|---|---|
| Export fight packet | Seeded packet is valid JSON and matches schema |
| Export dialogue | Branch graph has stable IDs and reachable nodes |
| Import map | Entities map to known feature/terrain types |
| Validate assets | Manifest paths exist and dimensions/metadata match |
| Validate animation | Frame sequence names, dimensions, and counts match manifest |
| Validate materials | Texture-set files exist and match expected material channels |
| Validate UI | Screens, states, and referenced assets exist |
| Build runtime | Godot/web target can load referenced files |
| Smoke play | A tiny encounter runs from input to rendered packet |

No arbitrary shell from the browser. Browser/operator commands stay allowlisted
and route through backend dispatch, matching the current `/bus`, `/code`, and
`/cli` guardrail.

## Implemented Slice

The first useful implementation is intentionally small:

1. Add `docs/superpowers/specs/2026-05-23-open-source-game-production-toolchain.md`.
2. Add `/game` operator-command routing, scoped to read-only or
   generated-artifact-safe actions.
3. Implement one deterministic smoke command:

```text
/game smoke narrative-combat
```

Expected behavior:
- Run the existing narrative-combat fixture.
- Emit a compact operator summary: encounter ID, seed, beat count, winner, price.
- Link or print the artifact path if a packet is written.
- Fail closed if the fixture import, schema, or packet render breaks.

## Fences

Do not blur this note into the canonical SCBE architecture.

- Not a new engine mandate. Godot already exists in `game/godot/`; narrative
  combat already exists in `src/narrative_combat/`.
- Not an LLM-chat feature. The point is build/test/debug tooling that models can
  invoke through bounded commands.
- Not a commitment to adopt all listed tools. Yarn Spinner and LDtk are the first
  serious candidates because they match current repo data shapes.
- Not a claim that art tools are runtime dependencies. Pencil2D, Pixelorama,
  Material Maker, Blockbench, Audacity, and Gum are authoring/export sources;
  the repo should validate exported artifacts and manifests.
- Not a license to commit generated caches or bulky exports. Source manifests,
  adapters, and small fixtures belong in repo; generated assets need explicit
  review.

## Acceptance Criteria

A future implementation of this lane is credible when:

- A designer can author an encounter or dialogue file outside the engine.
- The repo can import and validate it deterministically.
- The Arena/operator surface can run the relevant `/game` command.
- Tests fail on invalid branches, unknown entity types, missing assets, or
  schema drift.
- The runtime can load a tiny validated packet without manual glue.
