# AETHERMON — Creature-Raising Game

A Digimon-style virtual-pet battler set in the Aethermoore realm. Hatch a digital creature
from an egg, keep it fed and rested, train its stats, travel the six tongue regions, and
battle through the Spiral Arena. **How you raise it decides what it becomes** — the
evolution graph branches on care mistakes, training focus, bond, discipline, battle scars,
and contact with the Hollow. Every form has a lifespan; when its season ends, the creature
returns to the egg and the next generation inherits part of its strength.

Design lineage: see `docs/AETHERMON_DESIGN_NOTES.md` for the "making of Digimon" research
and the Aethermoore canon (world bible / novel / Spiral Forge) each system is drawn from.

## Play

```bash
npm run game:aethermon         # interactive terminal game (saves to .aethermon-save.json)
npm run game:aethermon:demo    # scripted, deterministic playthrough — no input, no saves
```

Flags (after `--`): `--seed <n>` fixed RNG seed, `--save <path>` custom save location.

## Module

`src/aethermon/` — self-contained TypeScript module, exported as `scbe-aethermoore/aethermon`.

| File           | Responsibility                                                          |
| -------------- | ----------------------------------------------------------------------- |
| `types.ts`     | Stages, alignment triangle, element wheel, Hodge duals, stats, lifespan |
| `rng.ts`       | Mulberry32 seeded RNG — every outcome reproducible from a save          |
| `moves.ts`     | 24-move catalog (4 power tiers per Sacred Tongue + drain/heal)          |
| `species.ts`   | 39-species catalog and branching evolution graph (incl. Hollow branch)  |
| `regions.ts`   | The six canon tongue regions of Aethermoore                             |
| `monster.ts`   | Care meters, ticks, training economy, XP curve, lifespan                |
| `evolution.ts` | Requirement evaluation and branch selection                             |
| `battle.ts`    | Turn-based battle engine (guard, crits, resonance, scars, strain)       |
| `game.ts`      | Eggs, regions, encounters, arena, generations/rebirth, JSON save/load   |
| `cli.ts`       | Playable terminal UI + demo mode                                        |

Tests live in `tests/aethermon/` (L2 unit, L3 integration, L4 fast-check properties).

## Core systems

### Stages

`EGG → MOTE (Lv.1) → SPRITE (Lv.5) → GUARDIAN (Lv.12) → PARAGON (Lv.22) → APEX (Lv.35)`

Four starter eggs (Ember/KO, Cipher/CA, Umbral/UM, Gale/AV — canon names) hatch after three
warm actions. Reaching APEX puts the creature in the Hall of Fame.

### Type system (two axes + resonance)

- **Alignment triangle** — `AEGIS > VENOM > FLUX > AEGIS`, with golden-ratio multipliers:
  φ (≈1.618) on advantage, 1/φ (≈0.618) on disadvantage.
- **Element wheel** — the six Sacred Tongues in order `KO → AV → RU → CA → UM → DR → KO`;
  each is strong (×1.25) against the next and weak (×0.8) against the previous.
- **Affinity** — moves matching the user's element get ×1.2 STAB; moves matching the
  user's **Hodge dual** (KO↔DR, AV↔UM, RU↔CA) resonate at ×1.3 — canon: duals bond 30%
  stronger. Storm Sovereign (AV) carries the UM move Eclipse Ward for exactly this reason.

Damage: `raw = power × (atk/def) × 0.25 + 2`, then alignment × element × affinity × crit
(×1.5, 1/16 chance) × variance (0.85–1.0); guarding halves it. Tuned for ~3–5 hits per
knockout between equals.

### Care (the virtual-pet loop)

Every action advances one tick; hunger (−6/tick) and energy (−4/tick) decay. Letting either
hit zero records a **care mistake** — the single biggest factor in which evolution branch
you get. The counter resets on each evolution (Digimon World rule: every stage is a fresh
test). Feed, rest, play, praise (+bond, −discipline), scold (+discipline, −mood), and train
(+3 permanent stat points, capped at +50 per stat). Battles take a tick too — creatures age
in the arena — and fighting 4+ times without resting causes **strain**.

### Scars — the immune flywheel

Every loss leaves a scar. Scars harden defense (+1 each, capped at +10 — the system gets
stronger from attacks) and are the keys to the hidden Hollow branch.

### Regions & the Hollow

Six travelable canon regions — Ember Reach (KO), Aerial Expanse (AV), Null Vale (RU),
Glass Drift (CA), Ward Sanctum (UM), Bastion Fields (DR). Wild encounters lean 60% toward
the local tongue. Only the Null Vale touches **the Hollow** — the gap between the tongues
where no voice claims authority. Communing with it costs mood and marks the creature with
hollow exposure.

### Branching evolution

Each species has one **fallback** edge (level requirement only — nothing ever gets stuck)
plus gated branches checked in priority order:

- few care mistakes / high bond / high discipline → AEGIS lines (Pyreling → Blazewarden → Solarchon → Radiant Sovereign)
- neglect or ATK-dominant training → VENOM lines (Gnashling → Vexmaw → Chaosdrake → Void Sovereign)
- SPD/DEF-focused training → FLUX/structure lines (Bitling → Cipherwarden → Oraclemind, Runeling → Runewarden → Aegisgolem → Lattice Sovereign)
- the wind line (canon) → Galewing → Zephyrkit/Squallkin → Skywarden/Stormherald →
  Zephyrarchon/Tempest Regent → **Storm Sovereign** (AV apex, the AV↔UM Storm pair made flesh)
- **the Hollow branch** (scar-gated, priority over everything): 3+ scars turn Veilkit or
  Gloomkit into **Fracture Shade**; 5+ scars and hollow exposure turn Nullshade into
  **Paradox Wraith** — dark evolution as the cost of a hard life, SkullGreymon-style

`dominantStat` requires that stat's training bonus to be ≥1.5× every other. Squallkin →
Skywarden is the designed redemption path (discipline + clean care).

### Lifespan & generations

Every form has a season: MOTE 140 ticks → APEX 320 (power buys time; evolving resets the
clock). When the clock runs out, the creature **returns to its line's egg**: the tamer
keeps a memorial entry, and the next generation hatches with an **heirloom** — 40% of the
predecessor's training (plus prior heirloom), capped at +30 per stat. Mastery survives
death; the line is the character.

### Spiral Arena

Ten named rivals from Pip the Gate Sweeper (Lv.3) to The Archivist, Arena Sovereign (Lv.40,
a Lattice Sovereign). Beat all ten to become Champion. Wild encounters scale to your level
(±2) and stage.

### Determinism

All randomness flows through a mulberry32 RNG whose state lives in the save file — loading
a save replays the exact same future encounters and battle rolls (verified by property
tests). Version-1 saves migrate forward automatically.
