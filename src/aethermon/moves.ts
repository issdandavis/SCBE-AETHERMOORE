/**
 * @file moves.ts
 * @module aethermon/moves
 * @layer Layer 5, Layer 12
 * @component AETHERMON — Move Catalog
 *
 * All battle moves, keyed by id. Each Sacred Tongue element has a tiered
 * ladder (jab ~35 / strike ~60 / burst ~90 / cataclysm ~120) with accuracy
 * falling as power rises, plus a few utility moves (drain, heal).
 */

import type { MoveDef } from './types.js';

const MOVE_LIST: readonly MoveDef[] = [
  // ── KO (Kor'aelin — Command) ──────────────────────────────────────────
  {
    id: 'ember_jab',
    name: 'Ember Jab',
    element: 'KO',
    power: 35,
    accuracy: 0.95,
    description: 'A quick spark-knuckled punch.',
  },
  {
    id: 'command_burst',
    name: 'Command Burst',
    element: 'KO',
    power: 60,
    accuracy: 0.9,
    description: 'A shouted directive that detonates on impact.',
  },
  {
    id: 'solar_lance',
    name: 'Solar Lance',
    element: 'KO',
    power: 90,
    accuracy: 0.85,
    description: 'A spear of compressed sunlight.',
  },
  {
    id: 'kings_decree',
    name: "King's Decree",
    element: 'KO',
    power: 120,
    accuracy: 0.75,
    description: 'An absolute order the world itself obeys.',
  },
  // ── AV (Avali — Transport) ────────────────────────────────────────────
  {
    id: 'gale_jab',
    name: 'Gale Jab',
    element: 'AV',
    power: 35,
    accuracy: 0.95,
    description: 'A wind-wrapped strike too fast to follow.',
  },
  {
    id: 'wind_shear',
    name: 'Wind Shear',
    element: 'AV',
    power: 60,
    accuracy: 0.9,
    description: 'Crossing blades of cutting air.',
  },
  {
    id: 'skyfall_dive',
    name: 'Skyfall Dive',
    element: 'AV',
    power: 90,
    accuracy: 0.85,
    description: 'A meteoric dive from the upper currents.',
  },
  {
    id: 'tempest_crown',
    name: 'Tempest Crown',
    element: 'AV',
    power: 120,
    accuracy: 0.75,
    description: 'A hurricane condensed into a single halo.',
  },
  // ── RU (Runethic — Entropy) ───────────────────────────────────────────
  {
    id: 'static_nip',
    name: 'Static Nip',
    element: 'RU',
    power: 35,
    accuracy: 0.95,
    description: 'A crackling bite of loose entropy.',
  },
  {
    id: 'chaos_bite',
    name: 'Chaos Bite',
    element: 'RU',
    power: 60,
    accuracy: 0.9,
    description: 'Jaws that scramble whatever they close on.',
  },
  {
    id: 'entropy_storm',
    name: 'Entropy Storm',
    element: 'RU',
    power: 90,
    accuracy: 0.85,
    description: 'A howling front of decoherence.',
  },
  {
    id: 'null_cascade',
    name: 'Null Cascade',
    element: 'RU',
    power: 120,
    accuracy: 0.75,
    description: 'Reality unravels in a chain reaction.',
  },
  {
    id: 'siphon_hex',
    name: 'Siphon Hex',
    element: 'RU',
    power: 50,
    accuracy: 0.9,
    effect: 'drain',
    description: 'Steals vitality — half the damage dealt is restored.',
  },
  // ── CA (Cassisivadan — Compute) ───────────────────────────────────────
  {
    id: 'bit_flick',
    name: 'Bit Flick',
    element: 'CA',
    power: 35,
    accuracy: 0.95,
    description: 'A single flipped bit, painfully placed.',
  },
  {
    id: 'logic_crush',
    name: 'Logic Crush',
    element: 'CA',
    power: 60,
    accuracy: 0.9,
    description: 'A contradiction driven home like a piston.',
  },
  {
    id: 'cipher_break',
    name: 'Cipher Break',
    element: 'CA',
    power: 90,
    accuracy: 0.85,
    description: 'Shatters the foe’s defenses key-first.',
  },
  {
    id: 'proof_of_ruin',
    name: 'Proof of Ruin',
    element: 'CA',
    power: 120,
    accuracy: 0.75,
    description: 'QED, written in craters.',
  },
  {
    id: 'mend_protocol',
    name: 'Mend Protocol',
    element: 'CA',
    power: 35,
    accuracy: 1.0,
    effect: 'heal',
    description: 'Self-repair routine — restores 35% of max HP.',
  },
  // ── UM (Umbroth — Security) ───────────────────────────────────────────
  {
    id: 'shade_tap',
    name: 'Shade Tap',
    element: 'UM',
    power: 35,
    accuracy: 0.95,
    description: 'A cold touch from inside a shadow.',
  },
  {
    id: 'veil_strike',
    name: 'Veil Strike',
    element: 'UM',
    power: 60,
    accuracy: 0.9,
    description: 'A blow thrown from behind a ward.',
  },
  {
    id: 'umbral_edge',
    name: 'Umbral Edge',
    element: 'UM',
    power: 90,
    accuracy: 0.85,
    description: 'A blade honed on the absence of light.',
  },
  {
    id: 'eclipse_ward',
    name: 'Eclipse Ward',
    element: 'UM',
    power: 120,
    accuracy: 0.75,
    description: 'The sky goes out. So does the opponent.',
  },
  // ── DR (Draumric — Structure) ─────────────────────────────────────────
  {
    id: 'rune_tap',
    name: 'Rune Tap',
    element: 'DR',
    power: 35,
    accuracy: 0.95,
    description: 'A precise knock on a load-bearing rune.',
  },
  {
    id: 'lattice_slam',
    name: 'Lattice Slam',
    element: 'DR',
    power: 60,
    accuracy: 0.9,
    description: 'A crystalline framework dropped from above.',
  },
  {
    id: 'sigil_storm',
    name: 'Sigil Storm',
    element: 'DR',
    power: 90,
    accuracy: 0.85,
    description: 'A blizzard of razor-edged glyphs.',
  },
  {
    id: 'worldframe',
    name: 'Worldframe',
    element: 'DR',
    power: 120,
    accuracy: 0.75,
    description: 'The architecture of reality, swung like a hammer.',
  },
];

/** Move catalog keyed by id. */
export const MOVES: ReadonlyMap<string, MoveDef> = new Map(MOVE_LIST.map((m) => [m.id, m]));

/** All move ids. */
export function allMoveIds(): string[] {
  return MOVE_LIST.map((m) => m.id);
}

/** Look up a move; throws on unknown id. */
export function getMove(id: string): MoveDef {
  const move = MOVES.get(id);
  if (!move) throw new RangeError(`Unknown move id: ${id}`);
  return move;
}
