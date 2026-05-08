# Scope of Mind — 2026-05-08

Single-page survey of every layer in scope before we extend `geoseal_cli`
into a governance-gated executable shell. Built from four parallel research
passes (SCBE 14-layer, swarm surface, PowerShell internals, geoseal_cli
current execution surface). Claims are tagged **[verified]** when this
author opened the file or ran the test, **[reported]** when only an agent
read it, **[drift]** when sources disagree.

---

## 1. SCBE 14-layer pipeline (canonical, verified)

Source of truth: `docs/LAYER_INDEX.md:14-27` (table) + `packages/kernel/src/harmonicScaling.ts` (math).

| L | Name | Formula / Operation | Canonical file |
|---|---|---|---|
| 1 | Complex Context State | `c(t) ∈ ℂᴰ` | `src/harmonic/pipeline14.ts` |
| 2 | Realification | `Φ₁: ℂᴰ → ℝ²ᴰ` (isometric) | `src/harmonic/pipeline14.ts` |
| 3 | Weighted Transform | `G^½ x` (SPD) | `src/harmonic/languesMetric.ts` |
| 4 | Poincaré Embedding | `Ψ_α` with `tanh` | `src/harmonic/pipeline14.ts` |
| 5 | Hyperbolic Distance | `d_H` (THE INVARIANT) | `src/harmonic/hyperbolic.ts` |
| 6 | Breathing Transform | `T_breath` (radial diffeomorphism) | `src/harmonic/hyperbolic.ts` |
| 7 | Phase Transform | Möbius ⊕ + rotation | `src/harmonic/adaptiveNavigator.ts` |
| 8 | Multi-Well Realms | `d* = min_k d_H(ũ, μ_k)` | `src/harmonic/hamiltonianCFI.ts` |
| 9 | Spectral Coherence | `S_spec = 1 - r_HF` | `src/spectral/index.ts` |
| 10 | Spin Coherence | `C_spin` (mean resultant length) | `src/spectral/index.ts` |
| 11 | Triadic Distance | `d_tri` (Byzantine consensus temporal) | `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/causality_axiom.py` |
| 12 | Harmonic Scaling (wall) | **see drift below** | `packages/kernel/src/harmonicScaling.ts` |
| 13 | Decision & Risk | ALLOW / QUARANTINE / ESCALATE / DENY | `src/symphonic_cipher/scbe_aethermoore/layer_13.py` |
| 14 | Audio Axis | `S_audio` (stellar octave mapping) | `src/harmonic/audioAxis.ts` |

### Documentation drift to fix [drift]

Two **different** L12 formulas live in the repo simultaneously:

- `docs/LAYER_INDEX.md:25` and `docs/SPEC.md`: `H(d*, R) = R^((φ · d*)²)` — superexponential.
- `packages/kernel/src/harmonicScaling.ts`: `H = 1 / (1 + d + 2·pd)` — bounded score in `(0, 1]`.

The TS file's own docstring (lines 12-21) explains why: the superexponential form caused numerical collapse (AUC 0.054 vs baseline 0.984). The bounded form is the production canonical. **Action: update `docs/LAYER_INDEX.md:25` to match `harmonicScaling.ts`.** Currently the docs lie about the production math.

A separate `harmonic_scaling_law.py` keeps a third form `H_wall = 1 + α·tanh(β·d*) ∈ [1, 1+α]` as a *risk amplification multiplier* used at L13 multiplication, not as the L12 score. That one isn't drift, it's a different role — `CLAUDE.md` lines 130-134 already document the coexistence.

### Cross-cutting axioms (5)

Each axiom has a Python implementation in `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/`:

| Axiom | Layers it touches | Implementation |
|---|---|---|
| Unitarity | L2, L4, L7 (norm preservation) | `unitarity_axiom.py` |
| Locality | L3, L8 (spatial bounds) | `locality_axiom.py` |
| Causality | L6, L11, L13 (time ordering) | `causality_axiom.py` |
| Symmetry | L5, L9, L10, L12 (gauge invariance) | `symmetry_axiom.py` |
| Composition | L1, L14 (pipeline integrity) | `composition_axiom.py` |

### Production status [verified]

- **Audited green:** L1-L7 complex→real chain, L9-L10 coherence, L12 harmonic wall (180/180 executable holdout, Wilson [0.979, 1.0]), L13 decision gate. Tests under `tests/harmonic/`, `tests/eval/`.
- **Partial:** L8 multi-well (numerical integration is research-stage), L11 Byzantine consensus (reference protocol, not production-hardened).
- **Research-stage:** L14 audio axis telemetry.

### Top 3 demo-ready layer touchpoints

1. **L12 harmonic wall** — bounded math, audited test count, browser+terminal demo already shipped (`demos/governance-gate/`).
2. **L5 hyperbolic distance** — pure formula, evidence JSON at `docs/evidence/layer5_hyperbolic_distance.json` [reported].
3. **L13 decision gate** — visible verdict pill, used in PWA and bus.

---

## 2. Swarm protocol surface

Source: `docs/research/DEFENSECLAW_TO_SCBE_SWARM_CAPABILITY_MAP.md` and the swarm skills under `.claude/skills/` and `external/codex-skills-live/`.

### What's coherent [reported, partially verified]

- **Six Sacred Tongues map to swarm roles.** Functional naming convention used in swarm docs is *role-first*: `COMMAND / QUERY / NEGOTIATE / STATUS / SIGNAL / LEARN`. The role mapping is real; the tongue *names* must stay canonical (Kor'aelin / Avali / Runethic / Cassisivadan / Umbroth / Draumric — anything else is drift, like the `Aelindra/Voxmara/...` set we just fixed in the demo files).
- **Spatial indexing**: octree-based proximity routing (`hydra/lattice25d_ops.py` exists [verified]; `src/octree_sphere_grid.py` claimed by an agent — file does **not** exist [verified missing]).
- **Safety governance**: `src/agent_comms/swarm_defense.py` + `tests/agent_comms/test_swarm_defense.py` [verified exist] — deterministic ALLOW/WARN/QUARANTINE/DENY verdicts with audit trails.
- **Multi-agent relay**: baton handoffs with overwatcher gates (`external/codex-skills-live/scbe-overwatch-relay-swarm/SKILL.md`).
- **Headless browser swarm**: 6 agents (Scout-KO, Reader-AV, Binder-RU, Compute-CA, Guard-UM, Synth-DR) with membrane enforcement (HONEYPOT/ISOLATE/DEGRADE).

### What's paper-only [reported]

- Generalized Six-Tongues protocol across non-medical domains.
- 6D medical vector navigation (depth/scope/timeline) — only validated in `external_repos/spiralverse-protocol/docs/MEDICAL_NANOBOT_SWARMS.md`.
- Multi-signature Byzantine tolerance at fleet scale.
- Full polyglot compression pipeline beyond medical context.

### Single capability that matters most to a defense buyer

**Traceable governance under mission degradation.** Deterministic verdicts (ALLOW/WARN/QUARANTINE/DENY) with JSONL audit trails enable replay and accountability. Spatial determinism (octree) keeps fleet behavior predictable across topology changes. The pitch is *governance-as-infrastructure*, not model superiority.

---

## 3. PowerShell layers and port targets

Source: PowerShell official docs + the agent's read of `learn.microsoft.com`.

| Subsystem | What it does | Public hook | Port pattern → `geoseal_cli` |
|---|---|---|---|
| **Console host + PSReadLine** | Line buffer + syntax color + Enter intercept | `Set-PSReadLineKeyHandler -Chord Enter -Function ValidateAndAcceptLine` | A `validate_line()` REPL hook that parses the buffer + scores it through L12 before dispatch. |
| **Parser / AST** | Token + AST without execution | `[System.Management.Automation.Language.Parser]::ParseInput(string)` | Python `ast.parse()` + an `AstVisitor` to scan for dangerous nodes pre-execution. |
| **Pipeline processor** | `cmd1 \| cmd2` streams typed objects (not text) | `PipelineProcessor` C# class | Make subcommands return `dataclass` instances; serialize between stages so each stage can be governance-gated on its output. |
| **Parameter binding** | Typed args via `[Parameter()]` attributes, `ParameterSetName`, `ValidateScript` | `Parameter` attribute + `Get-Command -Syntax` | `pydantic` dataclasses with `@field_validator`; emit synthetic `--help` from the schema. |
| **Command discovery** | Verb-Noun routing, autoload from `$env:PSModulePath` | `.psd1` module manifest | JSON/YAML registry for subcommand metadata; lazy-load Python modules by verb-noun. |
| **AMSI / `PerformSecurityChecks`** | Pre-compile content scan via `AmsiUtils.ScanContent` → `AmsiScanBuffer` | Hooks before `ReallyCompile()` | **This is the single highest-value port target.** Plug the SCBE harmonic wall here: scan the AST + parameter values → ALLOW/QUARANTINE/ESCALATE/DENY → log to ledger. |
| **Output formatting** | `.ps1xml` formatters convert objects to text *after* execution | `Format-Table` / `Format-List` | Pluggable Python output formatters (Jinja2 + pydantic schemas). Lower priority. |

**The cleanest port:** PowerShell's `AMSI → PerformSecurityChecks → ReallyCompile` flow is the closest existing analog to the SCBE pre-execution gate. Lifting that pattern (parse → scan → decide → execute) into Python is a weekend, not a month.

---

## 4. `geoseal_cli` current execution surface [partially verified]

Source: `src/geoseal_cli.py` (~1200 lines) + agent inventory.

### Subcommand inventory (execute? = whether it runs user code) [reported]

| Subcommand | Purpose | Executes? |
|---|---|---|
| `run` | Execute via tongue transport | **yes** |
| `code-roundtrip` | Encode/decode code through tongue transport (optional `--execute`) | partial |
| `shell` | Interactive shell | **yes** (REPL) |
| `replay` | Replay historical execution from ledger | **yes** |
| `testing-cli` | Run test suites via atomic workflow units | **yes** |
| `atomic` | Dispatch atomic workflow units | **yes** |
| `swarm` | Multi-tongue bot dispatch | **yes** |
| `encode-cmd` / `emit` / `verify` | Plan / sign / verify (no exec) | no |
| 20+ other subcommands | Various: graphs, manifests, telemetry | mostly no |

### Execution backbone [reported]

`run_tongue_call()` (around `src/geoseal_cli.py:560+`) wraps code via `_wrap_for_execution()` (`src/geoseal_cli.py:530+`), routes to a language-specific tongue (Python / Bash / JS), executes via subprocess, captures the result. The "execution ledger" claim from the audit agent is **[reported, not directly verified by me]** — needs a follow-up read before we cite it externally.

### Gaps for "real shell that executes code"

1. Pre-execution governance gate (no SCBE wall sits in front of `run`/`shell` today).
2. Persistent REPL state (in-memory Python context across commands).
3. Command history + readline editing.
4. Real-time output streaming with ANSI passthrough.
5. Persistent env-var + working-dir tracking across the session.
6. Transactional rollback when one tongue fails in a `swarm` batch.

### Already-shipped wins

1. **Multi-language transport abstraction** — single CLI, multiple language runtimes.
2. **Signed execution manifests** — every run produces a GeoSeal manifest.
3. **Atomic workflow unit dispatch** — composable execution graphs without bash scripting.

---

## 5. Synthesis — what we actually want to build

Goal: `geoseal_cli` becomes a real terminal that **executes code with SCBE governance in front of every command**, lifting the AMSI/PSReadLine pattern from PowerShell.

Smallest meaningful sequence (each step builds on the last):

1. **Fix the L12 doc drift first** (15 min). Update `docs/LAYER_INDEX.md:25` to the bounded formula. Otherwise everything downstream cites two different math sources.

2. **Add a `geoseal exec` subcommand with the AMSI-pattern gate** (1 weekend). `parse → scan → decide → execute`. Use Python's `ast.parse()` for the AST step (mirrors `Parser.ParseInput`); call the existing `harmonic_scale()` for the score; map to ALLOW/QUARANTINE/ESCALATE/DENY (mirrors `PerformSecurityChecks`); subprocess-execute on ALLOW.

3. **Wire the gate into the existing `run` and `shell` subcommands** (1 day). Same gate function; same audit log via the sealed-memory-packet primitive that landed today.

4. **Add a `validate_line` PSReadLine-style hook to the REPL** (1 day). Score the buffer pre-Enter; render the verdict pill in the prompt before the user even hits return.

5. **Then — and only then — bring in the swarm pieces.** `geoseal swarm exec --tongue ko --tongue av <task>` runs the task via two agents using the meet-in-the-middle protocol that landed in `src/agentic/meet_in_the_middle.py`. The CLI verbs are now: `exec` (single agent), `swarm exec` (parallel meet-in-the-middle), `seal` / `unseal-here` (geo-bound memory).

6. **Finally, port PowerShell's parameter-binding pattern** (1 weekend). Replace the wall of argparse subcommands with pydantic dataclasses + `--help` generated from the schema. This is what makes the CLI feel like PowerShell instead of a Python script.

Each step is testable and shippable on its own. Step 2 is the demo a defense scout sees first.

---

## 6. Files this scope-of-mind doc cited

All paths below were directly verified to exist (or marked **MISSING** when not):

```
docs/LAYER_INDEX.md
docs/SPEC.md
docs/research/DEFENSECLAW_TO_SCBE_SWARM_CAPABILITY_MAP.md
src/harmonic/pipeline14.ts
src/harmonic/harmonicScaling.ts
src/harmonic/hyperbolic.ts
src/harmonic/audioAxis.ts
packages/kernel/src/harmonicScaling.ts
src/symphonic_cipher/scbe_aethermoore/layers/fourteen_layer_pipeline.py
src/symphonic_cipher/scbe_aethermoore/layers_9_12.py
src/agent_comms/swarm_defense.py
tests/agent_comms/test_swarm_defense.py
hydra/lattice25d_ops.py
src/geoseal_cli.py
src/agentic/meet_in_the_middle.py
src/crypto/sealed_memory_packets.py
src/crypto/geo_fenced_seal.py

MISSING (claimed by an agent, does not exist):
src/octree_sphere_grid.py
```
