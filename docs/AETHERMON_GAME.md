# AETHERMON — Creature-Raising Game

A Digimon-style virtual-pet battler set in the Aethermoore realm. Hatch a digital creature
from an egg, keep it fed and rested, train its stats, and battle through the Spiral Arena.
**How you raise it decides what it becomes** — the evolution graph branches on care
mistakes, training focus, bond, and discipline.

## Play

```bash
npm run game:aethermon         # interactive terminal game (saves to .aethermon-save.json)
npm run game:aethermon:demo    # scripted, deterministic playthrough — no input, no saves
```

Flags (after `--`): `--seed <n>` fixed RNG seed, `--save <path>` custom save location.

## Module

`src/aethermon/` — self-contained TypeScript module, exported as `scbe-aethermoore/aethermon`.

| File           | Responsibility                                                        |
| -------------- | --------------------------------------------------------------------- |
| `types.ts`     | Stages, alignment triangle, element wheel, stats, all interfaces      |
| `rng.ts`       | Mulberry32 seeded RNG — every outcome reproducible from a save        |
| `moves.ts`     | 24-move catalog (4 power tiers per Sacred Tongue + drain/heal)        |
| `species.ts`   | 28-species catalog and branching evolution graph                      |
| `monster.ts`   | Care meters, ticks, training economy, XP curve                        |
| `evolution.ts` | Requirement evaluation and branch selection                           |
| `battle.ts`    | Turn-based battle engine (guard, crits, drain, heal, AI policy)       |
| `game.ts`      | Eggs, wild encounters, the ten-rung Spiral Arena, JSON save/load      |
| `cli.ts`       | Playable terminal UI + demo mode                                      |

Tests live in `tests/aethermon/` (L2 unit, L3 integration, L4 fast-check properties).

## Core systems

### Stages

`EGG → MOTE (Lv.1) → SPRITE (Lv.5) → GUARDIAN (Lv.12) → PARAGON (Lv.22) → APEX (Lv.35)`

Three starter eggs (Ember/KO, Cipher/CA, Umbral/UM) hatch after three warm actions. Reaching
APEX puts the creature in the Hall of Fame.

### Type system (two axes)

- **Alignment triangle** — `AEGIS > VENOM > FLUX > AEGIS`, with golden-ratio multipliers:
  φ (≈1.618) on advantage, 1/φ (≈0.618) on disadvantage.
- **Element wheel** — the six Sacred Tongues in order `KO → AV → RU → CA → UM → DR → KO`;
  each is strong (×1.25) against the next and weak (×0.8) against the previous. Moves
  matching the user's element get a ×1.2 same-type bonus.

Damage: `raw = power × (atk/def) × 0.25 + 2`, then alignment × element × STAB × crit (×1.5,
1/16 chance) × variance (0.85–1.0); guarding halves it. Tuned for ~3–5 hits per knockout
between equals.

### Care (the virtual-pet loop)

Every action advances one tick; hunger (−6/tick) and energy (−4/tick) decay. Letting either
hit zero records a **care mistake** — permanent, and the single biggest factor in which
evolution branch you get. Feed, rest, play, praise (+bond, −discipline), scold
(+discipline, −mood), and train (+3 permanent stat points, capped at +50 per stat).

### Branching evolution

Each species has one **fallback** edge (level requirement only — nothing ever gets stuck)
plus gated branches checked in priority order:

- few care mistakes / high bond / high discipline → AEGIS lines (Pyreling → Blazewarden → Solarchon → Radiant Sovereign)
- neglect or ATK-dominant training → VENOM lines (Gnashling → Vexmaw → Chaosdrake → Void Sovereign)
- SPD/DEF-focused training → FLUX/structure lines (Bitling → Cipherwarden → Oraclemind, Runeling → Runewarden → Aegisgolem → Lattice Sovereign)

`dominantStat` requires that stat's training bonus to be ≥1.5× every other.

### Spiral Arena

Ten named rivals from Pip the Gate Sweeper (Lv.3) to The Archivist, Arena Sovereign (Lv.40,
a Lattice Sovereign). Beat all ten to become Champion. Wild encounters scale to your level
(±2) and stage.

### Determinism

All randomness flows through a mulberry32 RNG whose state lives in the save file — loading
a save replays the exact same future encounters and battle rolls (verified by property
tests).
