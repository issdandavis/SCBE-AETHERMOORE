import type { FluxManifest } from './offline_mode.js';
import { isManifestStale, verifyManifest } from './offline_mode.js';

export type { FluxManifest } from './offline_mode.js';

export function verifyFluxManifest(
  manifest: FluxManifest,
  signerPublicKey: Uint8Array,
): boolean {
  return verifyManifest(manifest, signerPublicKey);
}

export function isFluxManifestStale(
  manifest: FluxManifest,
  nowMonotonic: bigint,
): boolean {
  return isManifestStale(manifest, nowMonotonic);
}

