# AetherPlay — AI Game-Playing & Branching Narrative Training System

**Design Document v1.0**
**Date**: 2026-02-28
**Status**: Research Complete → Ready for Implementation Planning

---

## 1. Vision

AI agents play branching interactive fiction games as a **dedicated creative activity** on self-imposed schedules. Every playthrough generates training data. Stories are generated from real conversation data (Colab pivot sessions) and authored templates. The games, templates, and training pipeline are sold as products on our own site.

**Key constraints from user**:
- Build our OWN branching narrative engine (not ChoiceScript's interpreter)
- Want the mass playtest/branch coverage feature (inspired by randomtest)
- Ability to write stories in the system
- Use conversation pivot data from Colab to generate branching narratives
- Nonprofit sector for non-commercial AI training
- Sell training templates + pipeline on our own platform
- NOT uploading to Choice of Games — these are for us and for sale as AI training tools

---

## 2. What Already Exists (CSTM Audit)

The codebase already has a **substantial** interactive fiction training system at `src/symphonic_cipher/scbe_aethermoore/concept_blocks/cstm/`. Here's what's built:

### Fully Implemented
| Module | LOC | What It Does |
|--------|-----|-------------|
| `models.py` | 356 | Scene, Choice (frozen), StoryGraph (DAG with BFS, validation), Curriculum, PlaythroughRecord |
| `story_engine.py` | 407 | JSON + Twee parsers, safe ConditionEvaluator (AST-sandboxed), StoryEngine with caching |
| `player_agent.py` | 434 | 21D PersonalityVector, DecisionEngine (heuristic scorer + softmax), 16 tag-to-personality mappings |
| `nursery.py` | 472 | Cohort management (64 agents), 5-criterion graduation, diversity scoring |
| `kernel.py` | 422 | GraduatedKernel extraction, DecisionTree, DriftAnalyzer, PreferenceMatrix |
| `telemetry_bridge.py` | 369 | SCBE concept block activation, HamiltonianTracker (rolling H(d,pd) window) |
| `cside_export.py` | 419 | Export to ChoiceScript format (one-directional: CSTM → ChoiceScript) |

### Known Bugs / Gaps
1. **DPO pairs broken**: `DecisionTree.to_preference_pairs()` always returns empty — `alternatives` list never populated in `KernelExtractor`
2. **No JSONL export**: Combat blockchain exports JSONL but CSTM has no direct training data export
3. **No mass playtesting**: No randomtest/quicktest equivalent
4. **No story content**: Engine built, zero stories shipped
5. **No async execution**: `max_concurrent=16` stored but unused
6. **ChoiceScript export disconnected**: Uses own types (`EnhancedScene`/`SceneChoice`) with no adapter from CSTM types
7. **No conversation-to-story pipeline**: No way to ingest chat data and produce StoryGraphs
8. **`graduation_score` type mismatch**: NurseryManager sets float, KernelExtractor expects dict
9. **HistoryBuffer.compress() unused**: 64D compressed vector computed but never consumed
10. **PLAN concept block never activated** in TelemetryBridge

### Game Systems (Tuxemon)
| Module | What It Does |
|--------|-------------|
| `combat_blockchain.py` | Immutable ledger, 14-layer data per block, JSONL SFT export |
| `battle_hook.py` | Monkey-patches Tuxemon combat, generates SFT + DPO pairs |
| `ai_schedule.py` | Spin-coherence driven NPC daily routines |
| `scbe_core.py` | L5/L6/L9/L11/L12/L13 Python math |

---

## 3. Research Synthesis

### 3.1 Mass Playtesting (The Key Feature)

**ChoiceScript's randomtest** is the gold standard:
- 10,000 iterations with seeded PRNG (reproducible)
- "Avoid used options" mode biases toward unexplored branches
- Line-level hit counts for coverage reporting
- Quicktest uses **recursive forking** — clones state at every branch, tests all paths

**Ink-Tester** (MIT licensed) provides similar capability for Ink:
- Thousands of random runs, CSV coverage reports
- Out-of-content detection
- Less sophisticated than ChoiceScript's tools

**Our implementation approach**: Build both algorithms into CSTM:
1. **Monte Carlo randomtest**: N iterations with avoid-used-options exploration
2. **Exhaustive quicktest**: Fork at every branch, deduplicate visited states
3. **Dominator analysis**: Find structural bottlenecks (compiler theory)
4. **Parallel execution**: Each worker gets different seed range (embarrassingly parallel)

### 3.2 Engine Comparison (Why Build Our Own)

| Feature | ChoiceScript | Ink | Twine | Our CSTM |
|---------|-------------|-----|-------|----------|
| License | Non-commercial | MIT | GPL v3 | Ours |
| Mass test | Built-in | 3rd party | None | **To build** |
| 21D personality | No | No | No | **Yes** |
| Governance gates | No | No | No | **Yes (14-layer)** |
| Training data export | No | No | No | **To build** |
| AI agent players | No | No | No | **Yes (PlayerAgent)** |
| Safe condition eval | No | No | No | **Yes (AST sandbox)** |
| Cohort training | No | No | No | **Yes (NurseryManager)** |

**Verdict**: We already have the most sophisticated system. We just need: mass testing, story content, training export, and conversation-to-story pipeline.

### 3.3 Conversation-to-Narrative Pipeline

Research shows three viable approaches:

**WHAT-IF (2024)**: Meta-prompting to convert linear narratives into branching plots:
1. Extract key events from source text
2. Identify decision points where the story could diverge
3. Generate alternative branches via LLM meta-prompting
4. Merge into branching plot tree
5. Export as playable IF

**GENEVA (Microsoft Research)**: Generate branching storylines from high-level descriptions using GPT-4, then visualize as graphs. Branch-and-reconverge structure (not exponential explosion).

**Story2Game (2025)**: Convert stories to playable games with preconditions/effects. Dynamic action generation for player-invented actions.

**Our pipeline**: Conversation pivot data → extract decision points → LLM generates branches → StoryGraph DAG → mass playtest → AI agents play → training data.

### 3.4 AI Game-Playing (Self-Directed Play)

**SIMA 2 (DeepMind, late 2025)**:
- Self-directed learning loop: generates own tasks, attempts, evaluates, feeds back
- 65% task completion (vs 31% SIMA 1)
- This IS "self-imposed schedule" AI play

**SPIRAL (2025)**:
- Self-play on zero-sum games teaches general reasoning
- +10.6% MATH500, +6.7% AIME from pure game play
- No math training data — reasoning transfers from game play

**Key insight**: Game self-play data is valuable because:
- Volume at zero marginal cost
- Automatic difficulty curriculum (self-play gets harder as agent improves)
- No distribution shift (training = deployment)
- But needs ~60% real data mixed in to prevent model collapse (golden ratio finding)

### 3.5 Orbiter Integration

**Status**: MIT license, Lua scripting, C++ SDK, Orb:Connect external API
**Trade mechanics**: Does NOT have built-in trade/economy — would need custom layer
**Value for us**: Physics telemetry (position, velocity, fuel, docking events) as training data
**Integration path**: Lua script streams telemetry to external process via Orb:Connect

### 3.6 Legal Position

**Our position is strong because**:
1. We build our OWN engine (no ChoiceScript interpreter = no CSL license applies)
2. We use MIT-licensed Ink syntax *concepts* (syntax isn't copyrightable)
3. Stories are our own creation (conversation pivot data = our IP)
4. Nonprofit sector for non-commercial training covers fair use
5. Selling training templates ≠ selling copyrighted game content
6. No pirated data — all training data self-generated

**Copyright Office (May 2025)**: Nonprofit status alone isn't a shield, but our use is genuinely transformative (training AI agents, not reproducing stories).

---

## 4. Architecture: AetherPlay

```
┌──────────────────────────────────────────────────────────┐
│                    AETHERPLAY SYSTEM                      │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────┐  │
│  │ Story Forge  │───▶│ Mass Tester  │───▶│  Training   │  │
│  │  (Author)    │    │ (Randomtest) │    │  Exporter   │  │
│  └─────┬───────┘    └──────────────┘    └─────┬──────┘  │
│        │                                       │         │
│  ┌─────▼───────┐    ┌──────────────┐    ┌─────▼──────┐  │
│  │ Conversation │───▶│  AI Agents   │───▶│  BVS/HF    │  │
│  │   Spinner    │    │  (21D Play)  │    │  Pipeline   │  │
│  └─────────────┘    └──────────────┘    └────────────┘  │
│                                                          │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────┐  │
│  │   Orbiter    │───▶│  Tuxemon     │───▶│  Product    │  │
│  │   Adapter    │    │   Bridge     │    │  Packager   │  │
│  └─────────────┘    └──────────────┘    └────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### 4.1 Story Forge (Author + Generator)

**What it does**: Write and generate branching narrative games.

**Inputs**:
- Hand-authored JSON/Twee stories (existing CSTM parsers)
- Conversation pivot data from Colab → LLM → StoryGraph
- Template-based generation (stat-gated branching, inspired by Choice of Robots' 4-stat system)

**Outputs**: StoryGraph DAGs ready for mass testing and AI play.

**New code needed**:
- `conversation_to_story.py` — Parse conversation transcripts, identify decision points, generate branches
- `story_templates.py` — Parameterized story templates (ethical dilemma, resource management, etc.)
- `story_validator.py` — Enhanced validation beyond current `StoryGraph.validate()`

### 4.2 Mass Tester (Randomtest + Quicktest)

**What it does**: Exhaustively test every story for coverage, dead ends, balance, and playability.

**Algorithms**:
1. **Randomtest**: N iterations (default 10,000), seeded PRNG, avoid-used-options exploration, line/node hit counts
2. **Quicktest**: Recursive forking at every branch point, both sides of every condition, dead code detection
3. **Coverage report**: Node coverage %, option balance, dead ends, bottleneck (dominator) nodes
4. **Path analysis**: Length distribution, convergence rate, ending distribution, difficulty curves

**New code needed**:
- `mass_tester.py` — Both algorithms + reporting
- `dominator.py` — Lengauer-Tarjan dominator tree for bottleneck detection

### 4.3 AI Agents (Existing CSTM + Extensions)

**What exists**: PlayerAgent (21D), DecisionEngine, NurseryManager, Cohort, GraduationCriteria

**Extensions needed**:
- Fix DPO pair generation (store alternatives in PlaythroughStep)
- Add neural scorer plug-in to DecisionEngine
- Add serialization/deserialization for agent state
- Add kernel re-loading (PlayerAgent.from_kernel())
- Add async/parallel execution in NurseryManager
- Add self-imposed scheduling (agent decides when to play, what to play, how long)

### 4.4 Training Exporter

**What it does**: Convert playthroughs to SFT/DPO training data.

**Formats**:
- SFT pairs: instruction=scene+choices, response=chosen+rationale
- DPO pairs: chosen choice vs rejected alternatives (with personality-based rationale)
- JSONL files compatible with HuggingFace datasets
- Kernel summaries (existing GraduatedKernel.save())

**New code needed**:
- `training_exporter.py` — Playthrough → JSONL pipeline
- Fix `to_preference_pairs()` bug in kernel.py

### 4.5 Conversation Spinner Integration

**What it does**: Takes the content spin engine's output + conversation data → training templates.

**Pipeline**:
1. Colab pivot conversations → extract narrative beats
2. Content spin (Fibonacci relay) → multiply into variations
3. LLM meta-prompting → branching alternatives at each beat
4. Governance gate → quality check each branch
5. StoryGraph DAG → ready for AI play
6. Mass test → validate coverage
7. Package as "AI Training Template" product

### 4.6 Game Adapters

**Tuxemon Bridge** (existing partial):
- Combat blockchain already generates SFT/DPO pairs
- Need: formal TelemetryEvent adapter between combat and CSTM
- Need: story content that references Tuxemon game state

**Orbiter Adapter** (new):
- Lua script exports telemetry via Orb:Connect
- External Python process ingests flight data
- Convert mission events to narrative beats
- Not a priority for v1

---

## 5. Product: AI Training Templates

### What We Sell

**"AetherPlay Training Templates"** — bundled story packs + the engine + training pipeline.

Each template pack includes:
1. 10-20 branching stories (StoryGraph JSON files)
2. Mass test coverage reports showing all paths work
3. Pre-generated training data (SFT + DPO JSONL)
4. Personality archetypes that emerge from play
5. The story forge tools for creating custom stories
6. Conversation-to-story converter

### Product Tiers

| Product | Price | Contents |
|---------|-------|----------|
| AetherPlay Starter | $19 | 10 stories, mass tester, training exporter |
| AetherPlay Pro | $49 | 30 stories, conversation spinner, story forge |
| AetherPlay Complete | $99 | Everything + Tuxemon bridge + custom story generation |
| Template Pack Add-on | $9 each | Theme packs: Ethical Dilemmas, Resource Management, Social Navigation, etc. |

### Legal Position for Sales

- We own the engine (CSTM is our code)
- We own the stories (generated from our conversation data)
- We own the training pipeline (SCBE governance)
- No ChoiceScript code used anywhere
- MIT/permissive components only
- Patent pending (USPTO #63/961,403) covers the governance layer

---

## 6. Build Order

### Phase 1: Fix CSTM Bugs + Add Training Export (4 files)

1. **Fix `kernel.py`**: Populate `alternatives` in DecisionNode, fix `graduation_score` type
2. **Fix `player_agent.py`**: Store available choices in PlaythroughStep for DPO
3. **New `training_exporter.py`**: Playthrough → SFT/DPO JSONL pipeline
4. **New `__init__.py` updates**: Export new symbols

### Phase 2: Mass Tester (2 files)

5. **New `mass_tester.py`**: Randomtest + Quicktest algorithms, coverage reporting
6. **New `graph_analysis.py`**: Dominator trees, path statistics, bottleneck detection

### Phase 3: Story Content (3 files)

7. **New `stories/ethical_dilemmas.json`**: 5 branching ethical scenarios
8. **New `stories/resource_management.json`**: 5 resource allocation scenarios
9. **New `stories/social_navigation.json`**: 5 social interaction scenarios

### Phase 4: Conversation-to-Story Pipeline (2 files)

10. **New `conversation_spinner.py`**: Parse conversations → decision points → branch generation
11. **New `story_templates.py`**: Parameterized story generators

### Phase 5: Self-Directed Play + Scheduling (2 files)

12. **New `play_scheduler.py`**: Self-imposed play schedules, session management
13. **Extend `nursery.py`**: Async execution, agent serialization

### Phase 6: Product Packaging (1 file)

14. **New `package_aetherplay.py`**: Build sellable ZIP packages

---

## 7. Key Design Decisions

### Why NOT use ChoiceScript
- CSL v1.0 prohibits commercial use of interpreter AND code written for it
- Choice of Games won't accept AI-written games on their store
- We already have a more powerful engine (21D personality, governance gates, cohort training)

### Why NOT use Ink
- MIT license is fine, but we'd still need to build everything around it
- Our CSTM already has features Ink lacks (personality vectors, governance, nursery)
- We'd be adding dependencies instead of building on what we have

### Why build mass testing ourselves
- ChoiceScript's randomtest is the best implementation but locked behind CSL
- Ink-Tester is simpler and less capable
- We need integration with our 21D personality system and governance gates
- Mass testing with AI agents (not just random choices) is novel

### The conversation spinner connection
- Content spin engine already generates 63+ variations from 5 seeds
- Conversation data is a natural "seed" — each conversation has decision points
- LLM generates alternative branches at each point
- Governance gate ensures quality
- This is the same pipeline, different input format

### Self-play data quality
- Research says ~60% real data / 40% synthetic to prevent model collapse
- Our existing 14,654 training pairs = real data foundation
- Game-generated data = synthetic component
- Combat blockchain + CSTM playthroughs = the 40%
- Web research + human-authored content = the 60%

---

## 8. References

### Academic Papers
- SIMA 2: arXiv:2512.04797 (DeepMind, self-directed AI play)
- SPIRAL: arXiv:2506.24119 (self-play → reasoning transfer)
- Story2Game: arXiv:2505.03547 (narrative → playable game)
- WHAT-IF: arXiv:2412.10582 (meta-prompting for branching narratives)
- GENEVA: arXiv:2311.09213 (Microsoft, narrative graph generation)
- Model Collapse Golden Ratio: arXiv:2502.18049

### Engines Studied
- ChoiceScript: github.com/dfabulich/choicescript (CSL v1.0)
- Ink: github.com/inkle/ink (MIT)
- CSIDE: github.com/ChoicescriptIDE/main (NW.js)
- ChroniclerQT: github.com/GarrettFleischer/ChroniclerQT (Qt, CC BY-NC 4.0)
- Ink-Tester: github.com/wildwinter/Ink-Tester (C#)
- Orbiter: github.com/orbitersim/orbiter (MIT)

### Training Environments
- TextWorld: github.com/microsoft/TextWorld
- Jericho: 57 human-written IF games for RL
- LIGHT (Meta): 663 locations, 3,462 objects, 11,000 episodes
- MineRL: 60M+ state-action pairs from human Minecraft play
- ALFWorld: Text ↔ embodied alignment (7x faster in text)

### Legal
- Copyright Office Part 3 (May 2025): Training may be fair use, depends on purpose
- Kadrey v. Meta (June 2025): Training on books = fair use (transformative)
- Bartz v. Anthropic (2025): Pirated acquisition ≠ fair use ($1.5B settlement)
- Thomson Reuters v. ROSS (Feb 2025): Competing products ≠ fair use
