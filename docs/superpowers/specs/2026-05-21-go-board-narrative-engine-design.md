# Go-Board Narrative Combat Engine — Design

Date: 2026-05-21
Status: approved (author-delegated; user authorized autonomous build)
Package: `src/narrative_combat/go_board/` — a **domain-agnostic legality kernel** plus a
**narrative-combat adapter** (the first of several planned domains). Sibling to the linear
maze-director.

## The board is a legality engine (SCBE Board Kernel)

The board is not a writing engine; it is a **deterministic graph-lattice legality controller**.
The core rule across every domain:

> The LLM (or any agent) may *suggest* moves. The board decides whether a move is **legal**.

This matters because hard domains already have real truth gates; the board just gives those
gates a shared memory and a move system. Architecture: a generic `kernel` (players, points,
typed nodes, legality, capture, superko, score, graph view — **no domain words, no SCBE
imports**) with thin **domain adapters** on top.

| Board concept | Narrative (v1) | Coding (next adapter) |
|---|---|---|
| stone | character / faction / event | AST-IR node, file, function, type, test, API |
| liberty | possible next beat | valid compile/test/refactor path |
| capture | contradiction, dead branch, weak scene | type error, failing test, broken import, unsafe cmd, secret leak |
| ko (superko) | prevents repeated plot loops | prevents rewrite loops / repeated failed patches |
| territory | zone influence | module ownership, dependency boundary |
| qi (resource node) | pressure / emotional resource | compute, context, model/tool budget |
| treaty edge | brokered truce zone | contract between modules / APIs / schemas / tests |

The kernel is the publishable core and the future bridge into the SCBE 14-layer governance and
agent bus (that wiring is a *separate* adapter that imports both — the kernel itself stays pure).
v1 ships the narrative adapter end-to-end and proves the kernel by structuring it so a coding
adapter is an addition, not a rewrite.

## One-line

A deterministic **Go-derived graph-lattice** is the authoritative truth layer; a fixed
six-phase director drives narratively-meaningful moves across it; each verified board event
becomes a story beat the translator renders. Same invariant as the maze-director: **the board
is truth, the LLM only renders.**

> Framing (working definition): a deterministic Go-derived graph lattice where stones represent
> combatant parties, liberties represent available action space, captures represent
> failed/removed options, ko prevents looped reasoning, and added typed nodes represent borders,
> treaties, qi, terrain, and research/study moves. LLMs do not decide truth; they translate
> verified board events into narrative.

It is a **state-space / graph-lattice engine**, not a literal dimensional manifold — the
manifold/lattice math (if formalized) lives on the SCBE side; here a board "string" is a graph
node and liberties are its edges, which is the rigorous version of the lattice idea.

## Rules base

Tromp-Taylor-style backbone: **positional superko** (no whole-board repeat) and **area scoring**
(stones + surrounded empty points). Deliberate divergence for v1 simplicity: **suicide is
illegal** (mainstream convention) rather than T-T's legal-self-removal — documented, not silent.
Ref: https://tromp.github.io/go.html

Known T-T behavior (not a bug): the empty starting position is in the superko history at
construction, so a move that legitimately empties the board again would be rejected. This is
correct positional-superko under Tromp-Taylor; it only matters on tiny boards / full captures.

## Why a board

Go concepts map cleanly onto narrative structure:

| Go concept | Narrative meaning |
|---|---|
| stone / group | a combatant party's local presence |
| liberties | the options open to that group |
| atari (1 liberty) | a crisis / cliffhanger |
| capture | a faction's local position collapses |
| positional superko | a feud that cannot immediately repeat |
| sente / gote | who controls the scene's tempo |
| territory | influence over a zone |

Plus three pieces the linear engine never had:

- **Qi node** — a board point that, once claimed by an adjacent stone, grants a party qi
  (spendable power). Makes qi spatial and contestable, not a private counter.
- **Treaty zone** — a rectangle locked by a party; inside it, capture is forbidden. A truce
  made structural. Lets a duel end in a brokered peace, not only a kill.
- **Study move** — a party spends a turn to consult outside sources (web search), turning a
  turn into a knowledge advantage. **Web search is a move on the board**, governed and audited.

## Honest framing (the design hand-wave, resolved)

The arc does **not** emerge from free play (that is a research project). The director runs a
fixed phase machine; the board supplies the spatial mechanics that make each phase non-trivial.
Phases drop onto the existing `PhaseName` literal:

1. **opening** — each party places 2 separated stones (presence)
2. **first_tactic** — a forced-adjacency contact move
3. **hidden_problem** — moves that reduce a target group's liberties (incl. a Study move)
4. **cost_unavoidable** — target group brought to atari (1 liberty)
5. **strategy_change** — defender plays Treaty or Study, OR attacker commits to the capture
6. **understanding_wins** — capture executed / treaty locked; score + aftermath

The seed shuffles move ordering within a phase; the phase structure is fixed.

## Truth layer: `board.py` (Goban)

- 9×9 grid (hard-coded v1). Cell = party index (`int`) or `None`.
- `group_and_liberties(pt)` — BFS over same-color adjacency → (group points, liberty points).
- `place(party, pt)` — empty-check → place → remove opponent groups at 0 liberties →
  reject own-group suicide → reject positional-superko repeat (whole-board hash history) →
  commit. Returns captured points. Raises `IllegalMove` otherwise.
- `legal_placements(party)` — points where `place` would succeed (director picks from these).
- `score()` — stones + simple territory (empty region bordered by one color only). For aftermath.
- `ascii()` — text board for the packet + demo.

Cut from v1: life/eye detection (Benson's), the suicide-that-captures edge case, custom sizes.

## Governed search: `governor.py`

`SearchGovernor` (≤50 lines, fully local — **no SCBE governance imports**):
- allowlist + per-call audit-log entry (query, decision, backend, latency). The `timeout` is
  carried as an advisory bound and recorded, not enforced on the stub backend; a real v2 backend
  is responsible for honoring it.
- pluggable backend; **deterministic stub default** (mirrors `LLMTranslator` fallback exactly)
- result cache keyed by `(seed, turn_index, query)` → same encounter+seed ⇒ same fight even if
  a real backend is wired in v2.

## Rendering: `translator.py` (Go variant)

- `GoTemplateTranslator` — deterministic, golden-stable; renders a `TurnEvent` via a literal
  **board-event → beat-frame dispatch table** (not implicit director logic).
- `GoLLMTranslator` — opt-in; same pattern as the maze `LLMTranslator` (facts dict, party
  **temperament** wired in, fallback to template on any failure).

## Output

CLI `python -m src.narrative_combat.go_board.cli` emits a `scbe.narrative_combat.go_fight.v1`
packet: schema, encounter_id, seed, board_size, parties, qi/treaty state, ordered `turns`, final
ascii board, aftermath (captures, score, treaties, surviving qi).

Each turn carries four fields (the user's "board event → mechanical summary → story beat →
verifier note" shape):
- `board_event` — the typed event (presence / contact / liberty_pressure / atari / qi_claimed /
  study_revealed / treaty_locked / capture)
- `mechanical` — the deterministic truth (points changed, liberties remaining, captured stones,
  qi delta, score delta)
- `prose` — the rendered beat (template or LLM)
- `verifier` — a note asserting prose↔truth correspondence: the mechanical claim the prose must
  honor, plus a flag if the LLM fell back or the render is empty. (v1 records the contract; v2
  can run an NLI/keyword check against it.)

## Future axis (v2+) — board as shared world-state for an agent harness

User framing (2026-05-21): A→Z is visible (A = "write this fight / solve this scene / analyze
this system"; Z = final narrative or report); the board is the hidden b–y middle — board state,
legal moves, parallel attempts, rule checks, captures/failures, deliberation, rewrite, verifier,
render. The win over "spawn five agents and summarize" (cf. HeavySkill: parallel reasoning +
deliberation) is that the board gives agents a **real shared world** instead of a pile of vibes;
reasoning paths are shaped by board/legal-move constraints. Deferred v1 move types that this
needs: `move_party`, `break_treaty`, `TerrainCell`. Graph view (strings=nodes, liberties=edges,
captures=graph rewrites) is the bridge to the lattice-analysis idea.

## Invariants / constraints

- Board state is the only source of truth; the translator never invents captures/outcomes.
- Deterministic for a given seed (incl. the stub Study backend).
- Package isolated: no `agentbus` / `governance` / `harmonic` imports.
- Reuse `models.Fighter`/`Technique`/`Terrain` where they fit; add local dataclasses otherwise.

## Probe moves (sensing the state space)

Two move classes, not one:
- **legal move** — commits; changes board state.
- **probe move** — samples without committing: `probe(player, pt) → Observation` (would it be
  legal? what would it capture? would it repeat a ko / be suicide?). `commit: false`.

Then the caller's loop is: `if probe improves confidence: promote to legal move; else: reject
(capture the invalid branch)`. Superko also forbids *repeating a failed probe's* committed
result. This is how good coding already works — poke, measure, then play the real move. In v1
the kernel exposes `probe()` (it is the same simulation `legal_placements` already needs); the
narrative Study move and the "render one beat in N tones" comparison are probe moves in spirit.
Atari is the warning state: one more committed move breaks the group.

## Tests (v1 gate)

liberties correct · capture removes group · superko forbids immediate recapture · illegal move
rejected · packet shape + invariants · determinism by seed · search governor audits + falls back.

## Future axis (v2+) — boards as a cross-dimensional reference lattice

User seed (2026-05-21): treat a board as a **dimensional manifold** whose points are degrees of
freedom, and *stack* boards so that a "chemistry style" (each point carries a composition of
elements/stone-types, like bonds) mixes with an "algebraic style" (the existing weighted/
harmonic lattice) to form a **cross-dimensional analysis reference lattice**. Each board becomes
one coordinate axis; a lattice of boards becomes a higher-dimensional analysis surface.

v1 enabler, not v1 scope: keep the `Goban` a clean coordinate object — points addressed by
`(row, col)`, single-occupant cells, no global singletons — so a v2 can add a third "layer" axis
(stacked boards) and a per-point composition vector without reworking the core. The lattice
*analysis* itself belongs on the SCBE side (polyhedral / 47D-manifold machinery); the engine
stays isolated and just exposes board state as a serializable coordinate grid.
