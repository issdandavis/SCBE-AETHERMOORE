/**
 * @file regions.ts
 * @module aethermon/regions
 * @layer Layer 3, Layer 8
 * @component AETHERMON — Tongue Regions (canon geography)
 *
 * The six realms of Aethermoore, one per Sacred Tongue, taken from the
 * world bible / Spiral Forge canon (src/game/regions.ts). Tamers travel
 * between regions; wild encounters lean toward the local tongue, and the
 * Null Vale uniquely exposes creatures to the Hollow — the gap between
 * the tongues where no voice claims authority.
 */

import type { TongueCode } from './types.js';

/** Region identifiers (canon names, snake_cased). */
export type RegionId =
  | 'ember_reach'
  | 'aerial_expanse'
  | 'null_vale'
  | 'glass_drift'
  | 'ward_sanctum'
  | 'bastion_fields';

/** A travelable region of Aethermoore. */
export interface RegionDef {
  readonly id: RegionId;
  readonly name: string;
  readonly tongue: TongueCode;
  readonly description: string;
  /** Chance a wild encounter matches the region's tongue. */
  readonly elementBias: number;
  /** Only the Null Vale touches the Hollow. */
  readonly touchesHollow: boolean;
}

/** Canon regions, in tongue order. */
export const REGIONS: readonly RegionDef[] = [
  {
    id: 'ember_reach',
    name: 'Ember Reach',
    tongue: 'KO',
    description:
      'The command heartland. Warmth, force, origin — where the first Tongue was spoken.',
    elementBias: 0.6,
    touchesHollow: false,
  },
  {
    id: 'aerial_expanse',
    name: 'Aerial Expanse',
    tongue: 'AV',
    description: 'The transport network. Everything moves through here; wind carries the Tongue.',
    elementBias: 0.6,
    touchesHollow: false,
  },
  {
    id: 'null_vale',
    name: 'Null Vale',
    tongue: 'RU',
    description:
      'Where order breaks down and entropy flows freely. The bold find power here — and the Hollow finds them.',
    elementBias: 0.6,
    touchesHollow: true,
  },
  {
    id: 'glass_drift',
    name: 'Glass Drift',
    tongue: 'CA',
    description: 'The compute core. Logic made manifest, encryption humming in the walls.',
    elementBias: 0.6,
    touchesHollow: false,
  },
  {
    id: 'ward_sanctum',
    name: 'Ward Sanctum',
    tongue: 'UM',
    description: 'The security bastion. Wards line every surface; nothing corrupted survives.',
    elementBias: 0.6,
    touchesHollow: false,
  },
  {
    id: 'bastion_fields',
    name: 'Bastion Fields',
    tongue: 'DR',
    description: 'The structure pinnacle. Every step is verified; only the proven may enter.',
    elementBias: 0.6,
    touchesHollow: false,
  },
] as const;

/** Region lookup by id; throws on unknown id. */
export function getRegion(id: string): RegionDef {
  const region = REGIONS.find((r) => r.id === id);
  if (!region) throw new RangeError(`Unknown region id: ${id}`);
  return region;
}

/** All region ids in canon order. */
export const REGION_IDS: readonly RegionId[] = REGIONS.map((r) => r.id);
