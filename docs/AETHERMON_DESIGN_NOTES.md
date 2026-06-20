# AETHERMON Design Notes — the Making of Digimon × Aethermoore Canon

How the game's systems were derived: design research into the original Digimon
(1997 Bandai V-Pet, Digimon World PS1) crossed with this repo's worldbuilding canon
(world bible, the Six Tongues Protocol novel, Spiral Forge RPG module).

## Part 1 — Research: how Digimon was actually made

**Origins.** Digital Monster launched June 26, 1997 (Bandai, co-developed with WiZ) as
the explicit "Tamagotchi for boys" — Tamagotchi's audience had skewed female, so Bandai
built a masculine counterpart. Creator credit "Akiyoshi Hongo" is a pseudonym blending
Aki Maita (Tamagotchi), Takeichi Hongo (Bandai), and Hiroshi Izawa (manga). Character
designer Kenji Watanabe started cute, was told it was generic, and pivoted to American
comics influences (Spawn/McFarlane, Bisley, Mignola) — "strong and cool," with the rule
that even cute creatures keep "an element of fearsomeness." The battle connector (two
units docking to fight) was the core innovation: **battling other players was required to
evolve** — the social loop was mechanical.
Sources: Wikipedia (Digital Monster), DigiLab & garm-translated Watanabe interviews,
90sToys retrospective, DigimonWiki.

**V-Pet care.** Two meters (hunger/strength); feeding adds weight, which gates both
evolution and battle — care and combat share one economy. A "care mistake" is logged
only when a call light goes unanswered (~10–20 min). Training is cumulative; sleep is
a fixed schedule and a missed bedtime is a mistake; over-battling (4+ consecutive)
risks sickness or death. Death is real — the US manual euphemized it as returning to
the "Megalithic Mainframe." Neglect produces shameful-but-playable forms (Numemon from
3+ mistakes — or from *miscalibrated* training); good care produces elites (Metal
Greymon: ~0–2 mistakes plus ~15 battles at 80%+ win rate). The weakest form has a
hidden redemption path (Numemon → Monzaemon).
Sources: Digivicemon Ver.1 guide, Humulos DM/DM20 guides, Wikimon.

**Digimon World (PS1, 1999) evolution.** Formalized branching: meet all 3 main
conditions (stat thresholds, weight ±5 of target, care-mistake count — some forms
require a *minimum* number of mistakes) or 2 of 3 plus a bonus condition (happiness,
discipline, battles, techniques). **The care-mistake counter resets on each
evolution** — only the current form's treatment matters. Partners live ~15 in-game
days; reaching the top stage extends life. **On death the partner returns to an egg
and the next generation inherits a percentage of its stats (1%/Tamer level, cap
10%)** — a roguelite legacy loop from 1999.
Sources: GameFAQs (SydMontague's evolution guide), Digimon World Wiki, Grindosaur.

**The triangle and the fields.** Vaccine > Virus > Data > Vaccine is a flat
rock-paper-scissors of *alignment*, with habitat "Fields" (Nature Spirits, Metal
Empire, Nightmare Soldiers…) as an orthogonal second taxonomy. Attribute is moral
flavor, not destiny.

**What made it distinct from Pokémon.** Impermanence (death/rebirth), the same
creature evolving differently per playthrough, creatures-as-data (corruptible,
restorable), and consequence carried in identity: the anime's SkullGreymon arc
(Adventure ep. 16) canonized "dark evolution from forced growth" — Tai cheats the
bond, Greymon digivolves into something uncontrollable.

## Part 2 — Canon: what Aethermoore brings

From the repo's worldbuilding (file references in parentheses):

- **The six regions** — Ember Reach (KO), Aerial Expanse (AV), Null Vale (RU),
  Glass Drift (CA), Ward Sanctum (UM), Bastion Fields (DR), each with palette,
  architecture, and description (`src/game/regions.ts`).
- **The Hollow** — not a seventh tongue: "binding is not another voice. It is what
  the six become when they agree to carry someone together" (novel ch12); the Hollow
  is the *gap* where no tongue claims authority, held closed by Izack Thorne "through
  sheer presence" (ch27). Existing Spiral Forge mechanics: `hollowExposure`, drift >
  0.8 → corrupted, scar-gated dark species **Fracture Shade** (minScars 3) and
  **Paradox Wraith** (minScars 5 + hollow contact) (`src/game/evolution.ts`,
  `companion.ts`).
- **Sacred Eggs** — canon mono-tongue eggs: Ember (KO), **Gale (AV) → Galewing**,
  Void (RU), Crystal (CA), Ward (UM), Helix (DR); "the egg you hatch reveals how you
  play" (`src/game/sacredEggs.ts`).
- **Hodge dual pairs** — KO↔DR, AV↔UM, RU↔CA; "Hodge duals bond 30% stronger"
  (Cl(4,0): e_ij ∧ e_kl = e₁₂₃₄) (`src/game/types.ts`, `symbioticNetwork.ts`).
- **Synesthesia** — each tongue has a note/frequency/color (KO=A 220Hz … DR=G 392Hz)
  (`src/game/types.ts` SYNESTHESIA_MAP).
- **Design philosophy** — "the system should get stronger from attacks (immune
  flywheel)" (round-table synthesis).

## Part 3 — The mapping: research × canon → AETHERMON systems

| Digimon mechanic (research) | Aethermoore canon | AETHERMON implementation |
| --- | --- | --- |
| Care mistakes steer branching | Spiral Forge behavioral evolution | `maxCareMistakes` / `minCareMistakes` edges (v1) |
| Care-mistake counter resets per evolution (Digimon World) | — | `evolve()` resets `careMistakes`: every stage is a fresh test |
| Vaccine/Data/Virus triangle + Fields (dual taxonomy) | Six Tongues + φ weights | AEGIS/VENOM/FLUX triangle (×φ / ×1/φ) × element wheel |
| Habitat fields → where you hunt matters | The six tongue regions | `regions.ts`: travel; wild encounters lean 60% toward the local tongue |
| Lifespan; death returns the partner to an egg; heir inherits stats (1%/level, cap 10%) | Sacred Eggs as sealed memory; "the egg you hatch reveals how you play" | `STAGE_LIFESPAN_TICKS` per form; `checkRebirth()`: memorial + same-line egg + 40% heirloom, capped (`HEIRLOOM_CAP`) |
| Top-stage evolution extends life ("power buys time") | — | Lifespan grows by stage (MOTE 140 → APEX 320 ticks); evolving resets the clock |
| Over-battling sickness (4+ consecutive) | — | `STRAIN_THRESHOLD`: 4+ battles without rest → strain penalties; `rest()` clears |
| Win-ratio/battle requirements for elites | — | `minBattlesWon` requirement support |
| Dark evolution from forced growth (SkullGreymon) | The Hollow; Fracture Shade / Paradox Wraith; "stronger from attacks" | Scars on losses (+DEF immune memory, capped) gate `fracture_shade` (3 scars); `communeWithGap()` in Null Vale + 5 scars gate `paradox_wraith` |
| Battle connector as social core | Hodge duals bond 30% stronger | `HODGE_RESONANCE` ×1.3 when a creature speaks its dual's element (Storm Sovereign ships with a UM move as proof) |
| Shameful-but-playable forms + redemption paths | — | Gnashling (neglect form) → Vexmaw build; Squallkin → Skywarden discipline redemption |
| Same species, different life per playthrough | A3 causality: deterministic from history | Whole graph branches on recorded history; seeded RNG makes each life replayable |

## Where to take it next

- **Weight economy** (feeding choices gate evolution ±5 of a target) — the one big
  V-Pet system not yet adopted.
- **Sleep schedule** as a daily commitment device (real-time hook).
- **Hodge egg tier** — canon Eclipse/Storm/Paradox dual eggs and the Prism omni egg
  as post-champion starters.
- **Synesthesia audio** — battles already know each tongue's note; L14 audio-axis
  telemetry could literally play the fight.
