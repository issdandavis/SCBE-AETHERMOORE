/**
 * @file regions.ts
 * @module game/regions
 * @layer Layer 3
 * @component Tongue Regions & Tower Floor Definitions
 *
 * Six tongue regions with palette, architecture, and tower floor mappings.
 * The 100-floor manhwa tower system.
 */

import { TongueRegion, TowerFloor, TongueCode } from './types.js';

// ---------------------------------------------------------------------------
//  Region Definitions
// ---------------------------------------------------------------------------

export const REGIONS: readonly TongueRegion[] = [
  {
    id: 'ember_reach',
    name: 'Ember Reach',
    tongue: 'KO',
    palette: { primary: '#DC503C', secondary: '#E8963C', accent: '#FFD080' },
    architectureStyle: 'Spiral-roof shrines, war temples, forge halls',
    floorRange: [1, 20],
    description: 'The command heartland. Warmth, force, origin. Where the first Tongue was spoken.',
  },
  {
    id: 'aerial_expanse',
    name: 'Aerial Expanse',
    tongue: 'AV',
    palette: { primary: '#5CB8E0', secondary: '#3C9090', accent: '#E0F0FF' },
    architectureStyle: 'Wind-bridges, sky platforms, transit hubs, floating docks',
    floorRange: [11, 30],
    description: 'The transport network. Everything moves through here. Wind carries the Tongue.',
  },
  {
    id: 'null_vale',
    name: 'Null Vale',
    tongue: 'RU',
    palette: { primary: '#8040C0', secondary: '#606080', accent: '#C0A0E0' },
    architectureStyle: 'Broken symmetry ruins, glitch terrain, entropy vents',
    floorRange: [21, 50],
    description: 'Where order breaks down. Entropy flows freely. The bold find power here.',
  },
  {
    id: 'glass_drift',
    name: 'Glass Drift',
    tongue: 'CA',
    palette: { primary: '#3CD8D8', secondary: '#D8C040', accent: '#FFFFFF' },
    architectureStyle: 'Geometric lattice cities, crystal processors, data towers',
    floorRange: [31, 60],
    description: 'The compute core. Logic made manifest. Encryption humming in the walls.',
  },
  {
    id: 'ward_sanctum',
    name: 'Ward Sanctum',
    tongue: 'UM',
    palette: { primary: '#40B870', secondary: '#F0F0E0', accent: '#006830' },
    architectureStyle: 'Crystal ward pylons, sealed vaults, cleansing pools',
    floorRange: [41, 80],
    description: 'The security bastion. Wards line every surface. Nothing corrupted survives.',
  },
  {
    id: 'bastion_fields',
    name: 'Bastion Fields',
    tongue: 'DR',
    palette: { primary: '#909080', secondary: '#D89898', accent: '#C0C0D0' },
    architectureStyle: 'Floating fractal towers, verification gates, authentication halls',
    floorRange: [51, 100],
    description: 'The structure pinnacle. Every step is verified. Only the proven may enter.',
  },
];

/** Lookup region by tongue code */
export function getRegionByTongue(tongue: TongueCode): TongueRegion | undefined {
  return REGIONS.find((r) => r.tongue === tongue);
}

/** Lookup region by ID */
export function getRegionById(id: string): TongueRegion | undefined {
  return REGIONS.find((r) => r.id === id);
}

// ---------------------------------------------------------------------------
//  Tower Floor Definitions (100 Floors)
// ---------------------------------------------------------------------------

/** Rank badges by floor range */
const RANKS: { maxFloor: number; rank: string }[] = [
  { maxFloor: 10, rank: 'F' },
  { maxFloor: 20, rank: 'E' },
  { maxFloor: 30, rank: 'D' },
  { maxFloor: 40, rank: 'C' },
  { maxFloor: 50, rank: 'B' },
  { maxFloor: 60, rank: 'A' },
  { maxFloor: 70, rank: 'S' },
  { maxFloor: 80, rank: 'SS' },
  { maxFloor: 90, rank: 'SSS' },
  { maxFloor: 99, rank: 'Transcendent' },
  { maxFloor: 100, rank: 'Millennium' },
];

/** Math domains by floor range */
const DOMAINS: { maxFloor: number; domain: string }[] = [
  { maxFloor: 10, domain: 'Arithmetic, basic algebra' },
  { maxFloor: 20, domain: 'Quadratics, systems of equations' },
  { maxFloor: 30, domain: 'Functions, graphing, transformations' },
  { maxFloor: 40, domain: 'Limits, sequences, convergence' },
  { maxFloor: 50, domain: 'Proofs, formal logic' },
  { maxFloor: 60, domain: 'Linear algebra, matrix theory' },
  { maxFloor: 70, domain: 'Discrete mathematics, combinatorics' },
  { maxFloor: 80, domain: 'Real analysis, topology' },
  { maxFloor: 90, domain: 'Optimization, variational methods' },
  { maxFloor: 99, domain: 'Open research problems' },
  { maxFloor: 100, domain: 'Millennium Prize problems' },
];

/** Region assignment by floor */
const FLOOR_REGIONS: { maxFloor: number; region: string }[] = [
  { maxFloor: 15, region: 'ember_reach' },
  { maxFloor: 25, region: 'aerial_expanse' },
  { maxFloor: 40, region: 'null_vale' },
  { maxFloor: 55, region: 'glass_drift' },
  { maxFloor: 75, region: 'ward_sanctum' },
  { maxFloor: 100, region: 'bastion_fields' },
];

function lookup<T extends { maxFloor: number }>(list: T[], floor: number): T {
  for (const item of list) {
    if (floor <= item.maxFloor) return item;
  }
  return list[list.length - 1];
}

/**
 * Generate tower floor definition.
 * Each floor: 5 encounters + 1 mini-boss (every 5th) + 1 boss (every 10th).
 */
export function getTowerFloor(floor: number): TowerFloor {
  if (floor < 1 || floor > 100) throw new RangeError('Floor must be 1-100');

  return {
    floor,
    mathDomain: lookup(DOMAINS, floor).domain,
    rank: lookup(RANKS, floor).rank,
    encounters: 5,
    miniBoss: floor % 5 === 0,
    boss: floor % 10 === 0,
    region: lookup(FLOOR_REGIONS, floor).region,
  };
}

/**
 * Get the rank for a given floor.
 */
export function getRank(floor: number): string {
  return lookup(RANKS, Math.min(100, Math.max(1, floor))).rank;
}

/**
 * Get all floors in a range (for UI display).
 */
export function getFloorRange(start: number, end: number): TowerFloor[] {
  const floors: TowerFloor[] = [];
  for (let f = Math.max(1, start); f <= Math.min(100, end); f++) {
    floors.push(getTowerFloor(f));
  }
  return floors;
}
