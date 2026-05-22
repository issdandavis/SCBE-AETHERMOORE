# Narrative Combat Generator — Design Spec

Date: 2026-05-21
Status: approved for vertical-slice implementation after review corrections
Author: Issac (design), drafted with Claude

## 1. Purpose

A **standalone, genre-agnostic engine** that generates *story-first* combat for
progression fantasy / wuxia / xianxia / LitRPG / grimdark. It is **not** a combat
log. A combat log's payload is state deltas (HP, dice, cooldowns); this engine's
payload is **meaning** — what the exchange reveals about the fighters and whether
the impossible just became possible.

Core principles:

- **Story-first.** Tactics emerge from narrative state, not grid math.
- **Dice generate pivots, not outcomes.** The result of a roll is a *narrative
  state shift*, never "you hit for 8."
- **Earned outcomes.** Without an HP ledger, what makes a win legible is a
  **price**: a fighter overcomes a gap by spending something trackable (a read,
  a secret, terrain, willpower, a permanent cost). The reader follows that ledger.
- **Every exchange changes** positioning, qi/resources, emotion, tactical intent,
  momentum, injury state, audience perception, spiritual pressure, terrain control.

## 2. The director is a pathfinder over a populated fight-maze

This is the heart of the engine. Writing a fight is "find the shortest path and
the longest path to the goal, decide neither is fun, and route your own using both
plus the walls of the world." The director does exactly that.

### 2.1 Goal, walls, paths

- **Goal (the maze exit)** is planned *arc-first*: who wins, the price paid, the
  aftermath, how the objective resolves.
- **Walls of the world** are hard constraints any path must respect: terrain &
  hazards, the power-law (what magic can/can't do here), technique qi/cooldown
  costs, fighter temperament & tier-gap, the objective's win/lose conditions,
  persistent injuries. A path cannot pass through a wall — no free qi, no
  un-setup trump card, no terrain doing what it physically can't.
- The director computes two reference routes — **shortest** (the decisive
  most-efficient line) and **longest** (every technique, maximally drawn out).
  Both are valid; both are boring.
- The **chosen path** is a *synthesis*: it borrows the decisiveness of the short
  and the texture of the long, bounded by the walls, and forced through required
  **craft waypoints** (the 8-phase template from `BATTLE_ACTION_REVISION_PASS.md`:
  objective → first tactic → true rule → hidden problem noticed → cost becomes
  unavoidable → strategy change → understanding wins → aftermath).
- **Dice generate texture and local pivots** *along* the chosen path — how each
  exchange reads, the small swings — never moving the goal.

### 2.2 The maze is a populated feature-graph

The maze is not empty corridors. It is seeded with **typed features** the path
threads through. Each feature poses an **innate test** — the path *is* the
sequence of tests, and how a fighter answers each (forced by temperament + dice)
*is* the characterization. A fight does not describe who someone is; it finds out.

| Feature | In a fight | The test it poses |
|---|---|---|
| **Safe zone** | a lull, regroup, eye-of-storm, defensive hold | patience — rest and cede tempo, or push and stay exposed? |
| **Treasure** | mid-fight breakthrough, technique unlocked under pressure, dropped weapon, enlightenment | restraint/greed — grab it now at the cost of an opening? (the progression payload) |
| **Monster** | reinforcement, boss hidden phase, a hazard waking | resolve — escalate or disengage? |
| **Friend** | party arrives, the rescue, an ally covers a weakness | trust — share the win, or try to solo it? |
| **Hazard** (terrain-as-combatant) | collapsing bridge, conducting rain, choking ash | spatial judgment — weaponize it or avoid it? |

The feature taxonomy is **extensible** (new feature types register a test + a
state-shift consequence).

### 2.3 All paths are different; reroll

The director samples *which* features the path engages and *in what order* —
combinatorial, not cosmetic. The **reversal and the price emerge from which tests
were passed or failed**, so a reroll is a genuinely different fight, not a reskin.

- **Soft reroll:** new seed → re-route a different valid path through the *same*
  goal + walls + features.
- **Hard reroll:** re-plan the goal itself (different winner / cost / aftermath).

### 2.4 Encounter templates = feature populations (the Battle Scale Ladder)

Different encounters carry different feature populations:

- **Rescue:** a friend-to-save + a time hazard + monsters.
- **Hazard fight:** terrain-as-monster dominant, few enemies.
- **Siege / hold:** monster waves + a hold objective + friends (allies).
- **Boss duel:** one monster behind ideology-walls + a treasure (enlightenment).
- **Split-party:** two sub-mazes solved in parallel.

Objective types (beyond "win"): rescue, hold, escape, protect, disable, purify,
learn, endure, **choose** (win without becoming what the villain says you are).

## 3. Components

Each unit has one job and a clear interface; each is testable in isolation.

| Unit | Job |
|---|---|
| **Data models** | `Fighter`, `Technique`, `Terrain`, `Feature`, `Encounter` (below) |
| **FightState** | the relational state (Section 5) — *not* an HP bar |
| **Director** | the pathfinder of Section 2: plan goal → walls → short/long → synthesize chosen path through craft waypoints + features → drive beats |
| **Resolver** | the dice (Section 4): roll → margin → outcome band → **narrative state shift**; deterministic given seed |
| **Translator** (interface, 3 impls) | `LLMTranslator` (glm-5.1 via Ollama), `TemplateTranslator` (phrasebanks off `narrative_tags` + bands), `HybridTranslator` (template skeleton + LLM polish) |
| **StyleProfile** | wuxia / xianxia / LitRPG / grimdark / anime / military — parameterizes the translator (idiom, technique-naming, whether numbers/system-text surface) |
| **Fight** (output) | ordered beats (structured outcome + prose) + aftermath; serializable as an Author-Echo-compatible combat scene packet |

The shared research reference for combat lanes is
`docs/narrative_combat/COMBAT_SOURCE_COMPARISON_MATRIX.md`. Treat it as a
system-level input, not a Kyle-only manuscript note. Project adapters can add
their own local overlays, but the base combat lanes and source comparisons live
there.

### 3.1 Data models (sketch)

```jsonc
// Fighter
{
  "name": "Wu Jin", "tier": "Iron Body",
  "stats": {"body": 8, "qi": 7, "speed": 9, "focus": 6},
  "temperament": ["prideful", "patient"],
  "techniques": ["falling_river_cleave"],
  "concealed": ["hidden_meridian_art"],   // not yet revealed; spending it is a beat
  "resources": {"qi": 30, "stamina": 20},
  "injuries": [], "momentum": 0, "morale": 1.0,
  "goal": "humiliate"                       // intent: kill/delay/escape/test/humiliate/protect
}

// Technique
{
  "name": "Falling River Cleave", "type": "saber", "cost": 3, "range": "mid",
  "grade": "low", "hidden": false,
  "effect": {"momentum_shift": 2, "guard_break": true},
  "narrative_tags": ["flood", "weight", "pressure"]
}

// Terrain / Feature / Encounter carry the maze: walls (constraints), features
// (Section 2.2), objective (Section 2.4), stakes, time pressure, style, seed.
```

## 4. Resolver (the dice)

```
margin = d20 + combat_stat + technique_mod + momentum + terrain_mod
         - defender_state
```

Margin → **outcome band** (not damage):

| Margin | Band |
|---|---|
| ≥ +15 | Dominating strike |
| +5..+14 | Strong advantage |
| 0..+4 | Minor success |
| around 0 | Clash |
| −5..−1 | Defensive loss |
| −10..−6 | Severe opening exposed |
| ≤ −15 | Catastrophic reversal |

Each band emits a **Narrative State Shift** describing what changed across the
state model (Section 5), which the Director consumes and the Translator renders.
**Momentum** is a `−5..+5` rhythm advantage that feeds back into the next roll
(positive = initiative/flow/pressure; negative = panic/broken guard/unstable qi).

## 5. State model (relational, not HP)

The interesting state is *who controls the fight*, not how much life remains:

- **Momentum / tempo** (−5..+5) — who dictates the exchange, and when it flips.
- **Reads** — each fighter's model of the other; misreads and revelations are
  drama.
- **Revealed vs concealed** — hidden techniques/realm; spending a secret is a beat.
- **Resources** — qi/stamina that gate the trump card.
- **Injuries** — persistent; they *subtract options from the move-set*, not a
  number off a bar.
- **Morale / composure**, **terrain control**, **audience perception**,
  **spiritual pressure**.

Injuries persist across exchanges and are returned in the aftermath for
cross-scene continuity (feeds Author Echo "continuity facts").

## 6. Data flow & determinism

```
Encounter(fighters, terrain, objective, features, stakes, style, seed)
  -> Director.plan()        # goal + walls + shortest/longest + chosen path
  -> loop beats:
       Director.choose_intent()   # per fighter, from temperament + state + tier
       Resolver.resolve()         # roll -> band -> StateShift
       Director.advance_arc()     # honor waypoints, engage features, place reversal
       Translator.render(beat, style) -> prose
  -> Director.resolve_ending()    # winner + price
  -> aftermath
  -> Fight(beats[], aftermath, final_state)
```

- **Seeded RNG ⇒ identical mechanics every run** (same seed = same structured
  fight + rolls). The LLM prose layer is the *only* non-deterministic part and is
  cacheable by `(seed, beat_id)`.
- **Reroll:** soft = new seed; hard = re-plan goal.

## 7. Decisions

- **Location:** `src/narrative_combat/` in this repo, deliberately **outside SCBE
  governance scope** (mirrors the Author Echo rule about not absorbing creative
  material into the federal/compliance surface). It *emits* a combat scene packet
  the Author Echo pipeline can consume; it does not depend on Author Echo or SCBE.
- **Build order:** **vertical slice first** (Section 8), then broaden.
- **Translator backends:** all three, behind one interface; the vertical slice
  ships the deterministic `TemplateTranslator` only, with `LLMTranslator`
  (glm-5.1 via Ollama, already proven in this stack) added next.

## 8. First build slice (vertical)

Prove the maze-director end-to-end with the smallest real fight:

- one fighter-pair, one `Terrain`, one `Encounter` objective (a **boss duel**),
- a small `Technique` library (≈4 techniques, one concealed),
- the maze with ≈3 features (one safe zone, one treasure, one monster) so
  "all paths different" is demonstrable,
- the `Director` (plan → walls → shortest/longest → synthesis → waypoints →
  feature engagement → reversal + price),
- the `Resolver` (bands + momentum + state shift), seeded,
- the `TemplateTranslator` only (deterministic, no model dependency),
- output a `Fight` with structured beats + aftermath + prose.

Acceptance: same seed reproduces the fight; two different seeds produce two
*structurally different* fights (different feature order / reversal placement);
the chosen path is neither the shortest nor the longest; a reversal and a price
always appear.

### 8.1 Vertical-slice output packet

The first slice must emit a plain JSON-serializable packet, not only prose:

```jsonc
{
  "schema": "scbe.narrative_combat.fight.v1",
  "encounter_id": "boss_duel_demo",
  "seed": 1337,
  "style": "xianxia",
  "objective": "choose",
  "planned_goal": {
    "winner": "Wu Jin",
    "price": "spends the concealed meridian art and carries qi backlash",
    "aftermath": ["right arm tremor", "enemy ideology disproven but not erased"]
  },
  "path": {
    "shortest": ["monster", "treasure", "ending"],
    "longest": ["safe_zone", "monster", "safe_zone", "treasure", "ending"],
    "chosen": ["safe_zone", "monster", "treasure", "ending"],
    "reversal_index": 1,
    "price_index": 2
  },
  "beats": [
    {
      "beat_id": "beat_001",
      "phase": "first_tactic",
      "feature": "safe_zone",
      "roll": 17,
      "margin": 8,
      "band": "strong_advantage",
      "state_shift": {
        "momentum": 2,
        "resources": {"Wu Jin.qi": -3},
        "revealed": [],
        "injuries": [],
        "continuity_facts": []
      },
      "prose": "..."
    }
  ],
  "aftermath": {
    "winner": "Wu Jin",
    "price_paid": ["concealed technique revealed", "qi backlash"],
    "continuity_facts": ["Wu Jin's right arm trembles after meridian backlash."]
  }
}
```

Author Echo integration is only packet compatibility in this slice. No source
manuscript path, adaptation hash, or author voice anchor is required until a
later adapter consumes this packet as scene material.

### 8.2 Structural difference definition

Two generated fights are structurally different when at least one of these
machine-checkable fields differs:

- `path.chosen` feature order
- `path.reversal_index`
- `path.price_index`
- the feature that triggers the concealed technique
- the final `price_paid`

Different wording alone does **not** count as a different fight.

### 8.3 Fixture-first rule

The first build must ship with one hardcoded fixture encounter used by both the
CLI and tests. Do not start by building a full content database. The fixture
should include two fighters, four techniques, one terrain object, and three
features. The broader library comes after the director proves deterministic
pathing and state shifts.

## 9. Testing

- **Golden-seed:** same seed → identical structured `Fight`.
- **Wall tests:** constraints never violated (no negative qi, no un-setup hidden
  card, terrain never does the impossible).
- **Arc-invariant:** every fight has ≥1 reversal, extracts a price, escalation
  trends up across phases.
- **Path-synthesis:** chosen path ≠ shortest and ≠ longest.
- **Feature/test:** each feature poses its test and applies its consequence.
- **Translator:** `TemplateTranslator` deterministic & golden; `LLMTranslator`
  smoke-only (renders without error; not asserted on exact prose).
- **Packet schema:** output includes `schema`, `encounter_id`, `seed`, `path`,
  `beats`, and `aftermath`; every beat includes `phase`, `feature`, `band`,
  `state_shift`, and `prose`.
- **Structural reroll:** two known seeds produce different structure by the
  definition in Section 8.2, not merely different prose.

## 10. Out of scope (YAGNI for now)

- Author Echo / SCBE integration beyond emitting a packet shape.
- A GUI. The engine is a library + CLI.
- Multi-fighter melee beyond the encounter templates listed; start with duel +
  small party, add mass-battle scaling later.
- Image/audio rendering of fights.
