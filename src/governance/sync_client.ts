import type { FluxManifest, SyncPayload, SyncResult } from './offline_mode.js';
import { resolveManifestConflict } from './offline_mode.js';

export interface SyncCursor {
  lastAuditIndex: number;
  lastCapsuleIndex: number;
}

export interface SyncState {
  cursor: SyncCursor;
  pending: SyncPayload[];
}

export function enqueueSync(state: SyncState, payload: SyncPayload): SyncState {
  return {
    cursor: state.cursor,
    pending: [...state.pending, payload],
  };
}

export function ackSync(
  state: SyncState,
  result: SyncResult,
  nextCursor: SyncCursor,
): SyncState {
  const remaining = state.pending.slice(result.accepted_capsules > 0 || result.accepted_events > 0 ? 1 : 0);
  return {
    cursor: nextCursor,
    pending: remaining,
  };
}

export function chooseManifest(
  local: FluxManifest,
  remote: FluxManifest,
  signerPub: Uint8Array,
): FluxManifest {
  return resolveManifestConflict(local, remote, signerPub);
}

