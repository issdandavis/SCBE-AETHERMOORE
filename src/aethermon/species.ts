/**
 * @file species.ts
 * @module aethermon/species
 * @layer Layer 5, Layer 13
 * @component AETHERMON — Species Catalog & Evolution Graph
 *
 * 39 species across six stages (EGG → MOTE → SPRITE → GUARDIAN → PARAGON
 * → APEX) in four starter lines that branch and re-merge. Every
 * non-terminal species has exactly one `fallback` evolution edge (only a
 * level requirement), so creatures never get stuck; better-raised
 * creatures qualify for higher-priority branches.
 *
 * Branching philosophy (classic virtual-pet rules):
 *  - Few care mistakes + bond/discipline → AEGIS branches
 *  - Neglect or aggression-heavy training → VENOM branches
 *  - Speed/logic-focused training        → FLUX branches
 *  - Scars + Hollow exposure             → the hidden Hollow branch
 *    (canon: Fracture Shade, Paradox Wraith — born in the gap between
 *    the tongues, gated on battle scars and Null Vale exposure)
 */

import type { SpeciesDef, Stage } from './types.js';

const SPECIES_LIST: readonly SpeciesDef[] = [
  // ═══════════════════════════ EGGS ═══════════════════════════
  {
    id: 'ember_egg',
    name: 'Ember Egg',
    stage: 'EGG',
    element: 'KO',
    alignment: 'FLUX',
    baseStats: { hp: 1, atk: 0, def: 0, spd: 0 },
    growth: 0,
    moves: [],
    evolvesTo: [{ targetId: 'kindlemote', minLevel: 1, fallback: true, priority: 1 }],
    lore: 'Warm to the touch, with a heartbeat like a struck match.',
  },
  {
    id: 'cipher_egg',
    name: 'Cipher Egg',
    stage: 'EGG',
    element: 'CA',
    alignment: 'FLUX',
    baseStats: { hp: 1, atk: 0, def: 0, spd: 0 },
    growth: 0,
    moves: [],
    evolvesTo: [{ targetId: 'glimmote', minLevel: 1, fallback: true, priority: 1 }],
    lore: 'Its shell is covered in shifting hexadecimal freckles.',
  },
  {
    id: 'umbral_egg',
    name: 'Umbral Egg',
    stage: 'EGG',
    element: 'UM',
    alignment: 'FLUX',
    baseStats: { hp: 1, atk: 0, def: 0, spd: 0 },
    growth: 0,
    moves: [],
    evolvesTo: [{ targetId: 'shademote', minLevel: 1, fallback: true, priority: 1 }],
    lore: 'Casts a shadow even in total darkness.',
  },
  {
    id: 'gale_egg',
    name: 'Gale Egg',
    stage: 'EGG',
    element: 'AV',
    alignment: 'FLUX',
    baseStats: { hp: 1, atk: 0, def: 0, spd: 0 },
    growth: 0,
    moves: [],
    evolvesTo: [{ targetId: 'galewing', minLevel: 1, fallback: true, priority: 1 }],
    lore: 'Light as a held breath. It rocks toward whichever window is open.',
  },

  // ═══════════════════════════ MOTES ═══════════════════════════
  {
    id: 'kindlemote',
    name: 'Kindlemote',
    stage: 'MOTE',
    element: 'KO',
    alignment: 'FLUX',
    baseStats: { hp: 32, atk: 10, def: 8, spd: 9 },
    growth: 0.06,
    moves: ['ember_jab'],
    evolvesTo: [
      { targetId: 'pyreling', minLevel: 5, fallback: false, priority: 2, maxCareMistakes: 2 },
      { targetId: 'gnashling', minLevel: 5, fallback: true, priority: 1 },
    ],
    lore: 'A floating cinder that chirps when praised.',
  },
  {
    id: 'glimmote',
    name: 'Glimmote',
    stage: 'MOTE',
    element: 'CA',
    alignment: 'FLUX',
    baseStats: { hp: 30, atk: 8, def: 9, spd: 11 },
    growth: 0.06,
    moves: ['bit_flick'],
    evolvesTo: [
      {
        targetId: 'runeling',
        minLevel: 5,
        fallback: false,
        priority: 2,
        minDiscipline: 25,
        maxCareMistakes: 2,
      },
      { targetId: 'bitling', minLevel: 5, fallback: true, priority: 1 },
    ],
    lore: 'A speck of light that counts everything it sees, twice.',
  },
  {
    id: 'shademote',
    name: 'Shademote',
    stage: 'MOTE',
    element: 'UM',
    alignment: 'FLUX',
    baseStats: { hp: 34, atk: 9, def: 10, spd: 7 },
    growth: 0.06,
    moves: ['shade_tap'],
    evolvesTo: [
      {
        targetId: 'veilkit',
        minLevel: 5,
        fallback: false,
        priority: 2,
        minBond: 25,
        maxCareMistakes: 2,
      },
      { targetId: 'gloomkit', minLevel: 5, fallback: true, priority: 1 },
    ],
    lore: 'A soft dark spot that hides behind its own tamer.',
  },
  {
    id: 'galewing',
    name: 'Galewing',
    stage: 'MOTE',
    element: 'AV',
    alignment: 'FLUX',
    baseStats: { hp: 31, atk: 9, def: 8, spd: 12 },
    growth: 0.06,
    moves: ['gale_jab'],
    evolvesTo: [
      {
        targetId: 'zephyrkit',
        minLevel: 5,
        fallback: false,
        priority: 2,
        maxCareMistakes: 2,
      },
      { targetId: 'squallkin', minLevel: 5, fallback: true, priority: 1 },
    ],
    lore: 'A scrap of wind with feathers it has not strictly earned yet.',
  },

  // ═══════════════════════════ SPRITES ═══════════════════════════
  {
    id: 'pyreling',
    name: 'Pyreling',
    stage: 'SPRITE',
    element: 'KO',
    alignment: 'AEGIS',
    baseStats: { hp: 48, atk: 16, def: 13, spd: 14 },
    growth: 0.07,
    moves: ['ember_jab', 'command_burst'],
    evolvesTo: [
      {
        targetId: 'blazewarden',
        minLevel: 12,
        fallback: false,
        priority: 2,
        minBond: 35,
        maxCareMistakes: 4,
      },
      { targetId: 'ashrevenant', minLevel: 12, fallback: true, priority: 1 },
    ],
    lore: 'A small flame knight that salutes before every meal.',
  },
  {
    id: 'gnashling',
    name: 'Gnashling',
    stage: 'SPRITE',
    element: 'RU',
    alignment: 'VENOM',
    baseStats: { hp: 44, atk: 18, def: 11, spd: 15 },
    growth: 0.07,
    moves: ['static_nip', 'chaos_bite'],
    evolvesTo: [
      { targetId: 'vexmaw', minLevel: 12, fallback: false, priority: 2, dominantStat: 'atk' },
      { targetId: 'ashrevenant', minLevel: 12, fallback: true, priority: 1 },
    ],
    lore: 'Mostly teeth. The rest is also teeth.',
  },
  {
    id: 'bitling',
    name: 'Bitling',
    stage: 'SPRITE',
    element: 'CA',
    alignment: 'FLUX',
    baseStats: { hp: 42, atk: 14, def: 12, spd: 18 },
    growth: 0.07,
    moves: ['bit_flick', 'logic_crush'],
    evolvesTo: [
      { targetId: 'cipherwarden', minLevel: 12, fallback: false, priority: 2, dominantStat: 'spd' },
      { targetId: 'glitchfiend', minLevel: 12, fallback: true, priority: 1 },
    ],
    lore: 'Solves mazes for fun. Builds them for revenge.',
  },
  {
    id: 'runeling',
    name: 'Runeling',
    stage: 'SPRITE',
    element: 'DR',
    alignment: 'AEGIS',
    baseStats: { hp: 46, atk: 13, def: 18, spd: 11 },
    growth: 0.07,
    moves: ['rune_tap', 'lattice_slam'],
    evolvesTo: [
      { targetId: 'runewarden', minLevel: 12, fallback: false, priority: 2, dominantStat: 'def' },
      { targetId: 'cipherwarden', minLevel: 12, fallback: true, priority: 1 },
    ],
    lore: 'A pebble golem that stacks itself neatly when resting.',
  },
  {
    id: 'veilkit',
    name: 'Veilkit',
    stage: 'SPRITE',
    element: 'UM',
    alignment: 'AEGIS',
    baseStats: { hp: 50, atk: 14, def: 16, spd: 12 },
    growth: 0.07,
    moves: ['shade_tap', 'veil_strike'],
    evolvesTo: [
      { targetId: 'fracture_shade', minLevel: 12, fallback: false, priority: 3, minScars: 3 },
      { targetId: 'umbrawarden', minLevel: 12, fallback: false, priority: 2, minDiscipline: 35 },
      { targetId: 'nullshade', minLevel: 12, fallback: true, priority: 1 },
    ],
    lore: 'A fox-shaped fold in the light, fiercely loyal.',
  },
  {
    id: 'gloomkit',
    name: 'Gloomkit',
    stage: 'SPRITE',
    element: 'RU',
    alignment: 'VENOM',
    baseStats: { hp: 44, atk: 17, def: 12, spd: 14 },
    growth: 0.07,
    moves: ['static_nip', 'shade_tap', 'chaos_bite'],
    evolvesTo: [
      { targetId: 'fracture_shade', minLevel: 12, fallback: false, priority: 3, minScars: 3 },
      { targetId: 'vexmaw', minLevel: 12, fallback: false, priority: 2, dominantStat: 'atk' },
      { targetId: 'nullshade', minLevel: 12, fallback: true, priority: 1 },
    ],
    lore: 'Sulks professionally. Bites semi-professionally.',
  },
  {
    id: 'zephyrkit',
    name: 'Zephyrkit',
    stage: 'SPRITE',
    element: 'AV',
    alignment: 'AEGIS',
    baseStats: { hp: 44, atk: 14, def: 13, spd: 19 },
    growth: 0.07,
    moves: ['gale_jab', 'wind_shear'],
    evolvesTo: [
      { targetId: 'stormherald', minLevel: 12, fallback: false, priority: 2, dominantStat: 'atk' },
      { targetId: 'skywarden', minLevel: 12, fallback: true, priority: 1 },
    ],
    lore: 'Rides thermals it makes up on the spot. Lands apologetically.',
  },
  {
    id: 'squallkin',
    name: 'Squallkin',
    stage: 'SPRITE',
    element: 'AV',
    alignment: 'VENOM',
    baseStats: { hp: 42, atk: 17, def: 10, spd: 18 },
    growth: 0.07,
    moves: ['gale_jab', 'chaos_bite', 'wind_shear'],
    evolvesTo: [
      {
        targetId: 'skywarden',
        minLevel: 12,
        fallback: false,
        priority: 2,
        maxCareMistakes: 2,
        minDiscipline: 30,
      },
      { targetId: 'stormherald', minLevel: 12, fallback: true, priority: 1 },
    ],
    lore: 'A pocket storm with opinions. The opinions are mostly thunder.',
  },

  // ═══════════════════════════ GUARDIANS ═══════════════════════════
  {
    id: 'blazewarden',
    name: 'Blazewarden',
    stage: 'GUARDIAN',
    element: 'KO',
    alignment: 'AEGIS',
    baseStats: { hp: 76, atk: 27, def: 22, spd: 22 },
    growth: 0.08,
    moves: ['command_burst', 'solar_lance', 'lattice_slam', 'rally_cry'],
    evolvesTo: [
      { targetId: 'solarchon', minLevel: 22, fallback: true, priority: 1 },
      {
        targetId: 'chaosdrake',
        minLevel: 22,
        fallback: false,
        priority: 2,
        minCareMistakes: 5,
      },
    ],
    lore: 'A knight of living fire sworn to whoever feeds it.',
  },
  {
    id: 'ashrevenant',
    name: 'Ashrevenant',
    stage: 'GUARDIAN',
    element: 'RU',
    alignment: 'VENOM',
    baseStats: { hp: 70, atk: 28, def: 18, spd: 24 },
    growth: 0.08,
    moves: ['chaos_bite', 'entropy_storm', 'siphon_hex', 'rust_hex'],
    evolvesTo: [{ targetId: 'chaosdrake', minLevel: 22, fallback: true, priority: 1 }],
    lore: 'What remains when a flame is raised carelessly.',
  },
  {
    id: 'vexmaw',
    name: 'Vexmaw',
    stage: 'GUARDIAN',
    element: 'RU',
    alignment: 'VENOM',
    baseStats: { hp: 68, atk: 30, def: 17, spd: 26 },
    growth: 0.08,
    moves: ['chaos_bite', 'entropy_storm', 'veil_strike', 'rust_hex'],
    evolvesTo: [{ targetId: 'chaosdrake', minLevel: 22, fallback: true, priority: 1 }],
    lore: 'Its growl desynchronizes nearby clocks.',
  },
  {
    id: 'cipherwarden',
    name: 'Cipherwarden',
    stage: 'GUARDIAN',
    element: 'CA',
    alignment: 'FLUX',
    baseStats: { hp: 70, atk: 24, def: 21, spd: 30 },
    growth: 0.08,
    moves: ['logic_crush', 'cipher_break', 'mend_protocol', 'rust_hex'],
    evolvesTo: [{ targetId: 'oraclemind', minLevel: 22, fallback: true, priority: 1 }],
    lore: 'Carries a key for every lock, including yours.',
  },
  {
    id: 'glitchfiend',
    name: 'Glitchfiend',
    stage: 'GUARDIAN',
    element: 'RU',
    alignment: 'VENOM',
    baseStats: { hp: 66, atk: 27, def: 18, spd: 28 },
    growth: 0.08,
    moves: ['chaos_bite', 'cipher_break', 'siphon_hex', 'rust_hex'],
    evolvesTo: [
      { targetId: 'oraclemind', minLevel: 22, fallback: false, priority: 2, minDiscipline: 45 },
      { targetId: 'chaosdrake', minLevel: 22, fallback: true, priority: 1 },
    ],
    lore: 'A rounding error that learned to enjoy itself.',
  },
  {
    id: 'runewarden',
    name: 'Runewarden',
    stage: 'GUARDIAN',
    element: 'DR',
    alignment: 'AEGIS',
    baseStats: { hp: 78, atk: 21, def: 30, spd: 18 },
    growth: 0.08,
    moves: ['lattice_slam', 'sigil_storm', 'mend_protocol', 'binding_lattice'],
    evolvesTo: [{ targetId: 'aegisgolem', minLevel: 22, fallback: true, priority: 1 }],
    lore: 'A walking archive of every promise ever kept to it.',
  },
  {
    id: 'umbrawarden',
    name: 'Umbrawarden',
    stage: 'GUARDIAN',
    element: 'UM',
    alignment: 'AEGIS',
    baseStats: { hp: 82, atk: 22, def: 28, spd: 19 },
    growth: 0.08,
    moves: ['veil_strike', 'umbral_edge', 'sigil_storm', 'ward_shatter'],
    evolvesTo: [{ targetId: 'duskmonarch', minLevel: 22, fallback: true, priority: 1 }],
    lore: 'A sentinel that guards the door between day and night.',
  },
  {
    id: 'nullshade',
    name: 'Nullshade',
    stage: 'GUARDIAN',
    element: 'UM',
    alignment: 'VENOM',
    baseStats: { hp: 72, atk: 27, def: 21, spd: 25 },
    growth: 0.08,
    moves: ['veil_strike', 'umbral_edge', 'siphon_hex', 'ward_shatter'],
    evolvesTo: [
      {
        targetId: 'paradox_wraith',
        minLevel: 22,
        fallback: false,
        priority: 3,
        minScars: 5,
        minHollowExposure: 1,
      },
      { targetId: 'chaosdrake', minLevel: 22, fallback: false, priority: 2, dominantStat: 'atk' },
      { targetId: 'duskmonarch', minLevel: 22, fallback: true, priority: 1 },
    ],
    lore: 'The space where something used to be, holding a grudge.',
  },
  {
    id: 'skywarden',
    name: 'Skywarden',
    stage: 'GUARDIAN',
    element: 'AV',
    alignment: 'AEGIS',
    baseStats: { hp: 74, atk: 24, def: 23, spd: 29 },
    growth: 0.08,
    moves: ['wind_shear', 'skyfall_dive', 'mend_protocol', 'tailwind'],
    evolvesTo: [{ targetId: 'zephyrarchon', minLevel: 22, fallback: true, priority: 1 }],
    lore: 'Patrols the wind-bridges of the Aerial Expanse. Nothing falls on its watch.',
  },
  {
    id: 'stormherald',
    name: 'Stormherald',
    stage: 'GUARDIAN',
    element: 'AV',
    alignment: 'VENOM',
    baseStats: { hp: 70, atk: 28, def: 18, spd: 27 },
    growth: 0.08,
    moves: ['wind_shear', 'skyfall_dive', 'siphon_hex', 'tailwind'],
    evolvesTo: [{ targetId: 'tempest_regent', minLevel: 22, fallback: true, priority: 1 }],
    lore: 'Arrives before the bad weather, because it is the bad weather.',
  },
  {
    id: 'fracture_shade',
    name: 'Fracture Shade',
    stage: 'GUARDIAN',
    element: 'UM',
    alignment: 'VENOM',
    baseStats: { hp: 70, atk: 29, def: 19, spd: 26 },
    growth: 0.08,
    moves: ['veil_strike', 'chaos_bite', 'siphon_hex', 'ward_shatter'],
    evolvesTo: [{ targetId: 'paradox_wraith', minLevel: 22, fallback: true, priority: 1 }],
    lore: 'Born where the tongues fall silent. Every scar it carries is a door.',
  },

  // ═══════════════════════════ PARAGONS ═══════════════════════════
  {
    id: 'solarchon',
    name: 'Solarchon',
    stage: 'PARAGON',
    element: 'KO',
    alignment: 'AEGIS',
    baseStats: { hp: 110, atk: 38, def: 32, spd: 31 },
    growth: 0.09,
    moves: ['solar_lance', 'kings_decree', 'mend_protocol', 'rally_cry'],
    evolvesTo: [{ targetId: 'radiant_sovereign', minLevel: 35, fallback: true, priority: 1 }],
    lore: 'A crowned dawn that rises whenever its tamer does.',
  },
  {
    id: 'chaosdrake',
    name: 'Chaosdrake',
    stage: 'PARAGON',
    element: 'RU',
    alignment: 'VENOM',
    baseStats: { hp: 102, atk: 41, def: 27, spd: 35 },
    growth: 0.09,
    moves: ['entropy_storm', 'null_cascade', 'siphon_hex', 'rust_hex'],
    evolvesTo: [{ targetId: 'void_sovereign', minLevel: 35, fallback: true, priority: 1 }],
    lore: 'A dragon whose scales each show a different bad timeline.',
  },
  {
    id: 'oraclemind',
    name: 'Oraclemind',
    stage: 'PARAGON',
    element: 'CA',
    alignment: 'FLUX',
    baseStats: { hp: 100, atk: 34, def: 31, spd: 41 },
    growth: 0.09,
    moves: ['cipher_break', 'proof_of_ruin', 'mend_protocol', 'rust_hex'],
    evolvesTo: [
      {
        // The general-purpose machine demands Victorian precision:
        // drilled discipline and balanced, unspecialized training.
        targetId: 'engine_sovereign',
        minLevel: 35,
        fallback: false,
        priority: 3,
        minDiscipline: 70,
        dominantStat: 'balanced',
      },
      {
        targetId: 'radiant_sovereign',
        minLevel: 35,
        fallback: false,
        priority: 2,
        minBond: 70,
      },
      { targetId: 'lattice_sovereign', minLevel: 35, fallback: true, priority: 1 },
    ],
    lore: 'It already knows how this battle ends. It fights anyway.',
  },
  {
    id: 'aegisgolem',
    name: 'Aegisgolem',
    stage: 'PARAGON',
    element: 'DR',
    alignment: 'AEGIS',
    baseStats: { hp: 118, atk: 31, def: 42, spd: 25 },
    growth: 0.09,
    moves: ['sigil_storm', 'worldframe', 'mend_protocol', 'binding_lattice'],
    evolvesTo: [{ targetId: 'lattice_sovereign', minLevel: 35, fallback: true, priority: 1 }],
    lore: 'A fortress that decided walls work better when they walk.',
  },
  {
    id: 'duskmonarch',
    name: 'Duskmonarch',
    stage: 'PARAGON',
    element: 'UM',
    alignment: 'VENOM',
    baseStats: { hp: 112, atk: 35, def: 36, spd: 30 },
    growth: 0.09,
    moves: ['umbral_edge', 'eclipse_ward', 'siphon_hex', 'ward_shatter'],
    evolvesTo: [{ targetId: 'void_sovereign', minLevel: 35, fallback: true, priority: 1 }],
    lore: 'Rules the hour when all the lights agree to look away.',
  },
  {
    id: 'zephyrarchon',
    name: 'Zephyrarchon',
    stage: 'PARAGON',
    element: 'AV',
    alignment: 'AEGIS',
    baseStats: { hp: 104, atk: 35, def: 33, spd: 40 },
    growth: 0.09,
    moves: ['skyfall_dive', 'tempest_crown', 'mend_protocol', 'tailwind'],
    evolvesTo: [{ targetId: 'storm_sovereign', minLevel: 35, fallback: true, priority: 1 }],
    lore: 'The high wind given a throne and the good sense not to sit still on it.',
  },
  {
    id: 'tempest_regent',
    name: 'Tempest Regent',
    stage: 'PARAGON',
    element: 'AV',
    alignment: 'VENOM',
    baseStats: { hp: 100, atk: 39, def: 28, spd: 38 },
    growth: 0.09,
    moves: ['skyfall_dive', 'tempest_crown', 'siphon_hex', 'tailwind'],
    evolvesTo: [
      { targetId: 'void_sovereign', minLevel: 35, fallback: false, priority: 2, minScars: 4 },
      { targetId: 'storm_sovereign', minLevel: 35, fallback: true, priority: 1 },
    ],
    lore: 'Wears lightning the way other royalty wears jewelry.',
  },
  {
    id: 'paradox_wraith',
    name: 'Paradox Wraith',
    stage: 'PARAGON',
    element: 'RU',
    alignment: 'VENOM',
    baseStats: { hp: 104, atk: 42, def: 26, spd: 37 },
    growth: 0.09,
    moves: ['entropy_storm', 'null_cascade', 'umbral_edge', 'rust_hex'],
    evolvesTo: [{ targetId: 'void_sovereign', minLevel: 35, fallback: true, priority: 1 }],
    lore: 'It remembers the gap between the tongues — and the gap remembers back.',
  },

  // ═══════════════════════════ APEXES ═══════════════════════════
  {
    id: 'radiant_sovereign',
    name: 'Radiant Sovereign',
    stage: 'APEX',
    element: 'KO',
    alignment: 'AEGIS',
    baseStats: { hp: 150, atk: 52, def: 44, spd: 44 },
    growth: 0.1,
    moves: ['kings_decree', 'rally_cry', 'tempest_crown', 'mend_protocol'],
    evolvesTo: [],
    lore: 'The realm’s first sunrise, wearing armor.',
  },
  {
    id: 'lattice_sovereign',
    name: 'Lattice Sovereign',
    stage: 'APEX',
    element: 'DR',
    alignment: 'AEGIS',
    baseStats: { hp: 158, atk: 45, def: 54, spd: 38 },
    growth: 0.1,
    moves: ['worldframe', 'binding_lattice', 'proof_of_ruin', 'mend_protocol'],
    evolvesTo: [],
    lore: 'The load-bearing thought at the bottom of Aethermoore.',
  },
  {
    // Canon: the steam-powered Analytical Engine (Babbage, 1837) — a Mill
    // for arithmetic, a Store of a thousand fifty-digit numbers, punched
    // cards borrowed from the Jacquard loom, and conditional branching:
    // it eats its own tail. Ada's Bernoulli sequence is its signature.
    id: 'engine_sovereign',
    name: 'Engine Sovereign',
    stage: 'APEX',
    element: 'CA',
    alignment: 'FLUX',
    baseStats: { hp: 156, atk: 48, def: 50, spd: 40 },
    growth: 0.1,
    moves: ['bernoulli_sequence', 'proof_of_ruin', 'mend_protocol', 'binding_lattice'],
    evolvesTo: [],
    lore:
      'The locomotive-sized first dream of a thinking machine: a Mill for thought, ' +
      'a Store for memory, punched cards for a soul. It eats its own tail — ' +
      'each result chooses the next instruction.',
  },
  {
    id: 'void_sovereign',
    name: 'Void Sovereign',
    stage: 'APEX',
    element: 'RU',
    alignment: 'VENOM',
    baseStats: { hp: 144, atk: 54, def: 40, spd: 48 },
    growth: 0.1,
    moves: ['null_cascade', 'eclipse_ward', 'rust_hex', 'siphon_hex'],
    evolvesTo: [],
    lore: 'Entropy, enthroned. Surprisingly polite about it.',
  },
  {
    id: 'storm_sovereign',
    name: 'Storm Sovereign',
    stage: 'APEX',
    element: 'AV',
    alignment: 'FLUX',
    baseStats: { hp: 146, atk: 50, def: 42, spd: 50 },
    growth: 0.1,
    moves: ['tempest_crown', 'tailwind', 'eclipse_ward', 'mend_protocol'],
    evolvesTo: [],
    lore: 'The Storm pair made flesh: Transport and Security, AV and UM, one crown.',
  },
];

/** Species catalog keyed by id. */
export const SPECIES: ReadonlyMap<string, SpeciesDef> = new Map(SPECIES_LIST.map((s) => [s.id, s]));

/** Eggs offered to a new tamer. */
export const STARTER_EGG_IDS: readonly string[] = [
  'ember_egg',
  'cipher_egg',
  'umbral_egg',
  'gale_egg',
];

/** All species definitions. */
export function allSpecies(): readonly SpeciesDef[] {
  return SPECIES_LIST;
}

/** Species filtered by stage. */
export function speciesByStage(stage: Stage): SpeciesDef[] {
  return SPECIES_LIST.filter((s) => s.stage === stage);
}

/** Look up a species; throws on unknown id. */
export function getSpecies(id: string): SpeciesDef {
  const species = SPECIES.get(id);
  if (!species) throw new RangeError(`Unknown species id: ${id}`);
  return species;
}
