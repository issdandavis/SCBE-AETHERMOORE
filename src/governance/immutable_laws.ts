import { sha512 } from '@noble/hashes/sha2.js';
import type { ImmutableLaws } from './offline_mode.js';

function canonicalStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map((v) => canonicalStringify(v)).join(',')}]`;
  const record = value as Record<string, unknown>;
  const keys = Object.keys(record).sort();
  const entries = keys.map((k) => `${JSON.stringify(k)}:${canonicalStringify(record[k])}`);
  return `{${entries.join(',')}}`;
}

function hashLawsPayload(payload: Omit<ImmutableLaws, 'laws_hash'>): Uint8Array {
  return sha512(new TextEncoder().encode(canonicalStringify(payload)));
}

export function createImmutableLaws(
  payload: Omit<ImmutableLaws, 'laws_hash'>,
): ImmutableLaws {
  return {
    ...payload,
    laws_hash: hashLawsPayload(payload),
  };
}

export function verifyImmutableLawsHash(laws: ImmutableLaws): boolean {
  const payload: Omit<ImmutableLaws, 'laws_hash'> = {
    metric_signature: laws.metric_signature,
    tongues_set: laws.tongues_set,
    geometry_model: laws.geometry_model,
    layer_behaviors: laws.layer_behaviors,
  };
  const expected = hashLawsPayload(payload);
  if (expected.length !== laws.laws_hash.length) return false;
  let diff = 0;
  for (let i = 0; i < expected.length; i++) diff |= expected[i]! ^ laws.laws_hash[i]!;
  return diff === 0;
}

