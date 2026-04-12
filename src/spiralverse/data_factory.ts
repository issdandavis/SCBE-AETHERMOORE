/**
 * Spiralverse Synthetic Conversation Data Factory
 * ===============================================
 *
 * Minimal, deterministic generator for cryptographically verifiable
 * RWP v2 wire envelopes (ver="2") suitable for training-data harnesses.
 *
 * This is intentionally small and test-friendly:
 * - Deterministic PRNG (seeded) for reproducible datasets
 * - Topic pivoting produces a simple topic graph (edges)
 * - Output envelopes are verifiable with the same keyring
 *
 * @module spiralverse/data_factory
 * @since 2026-04-07
 */

import type { Keyring } from './types';
import type { RWP2WireEnvelope, RWP2WireTongue } from './rwp_v2_wire';
import { signRoundtableV2Wire, verifyRoundtableV2Wire } from './rwp_v2_wire';

export interface TopicEdge {
  from: string;
  to: string;
  tongue: RWP2WireTongue;
  step: number;
}

export interface SyntheticConversation {
  baseTopic: string;
  envelopes: RWP2WireEnvelope[];
  edges: TopicEdge[];
}

class XorShift32 {
  private state: number;

  constructor(seed: number) {
    // avoid zero-state lockup
    this.state = (seed >>> 0) || 0x6d2b79f5;
  }

  nextU32(): number {
    let x = this.state;
    x ^= x << 13;
    x ^= x >>> 17;
    x ^= x << 5;
    this.state = x >>> 0;
    return this.state;
  }

  nextByte(): number {
    return this.nextU32() & 0xff;
  }

  bytes(len: number): Buffer {
    const out = Buffer.allocUnsafe(len);
    for (let i = 0; i < len; i++) out[i] = this.nextByte();
    return out;
  }

  pick<T>(arr: T[]): T {
    const idx = this.nextU32() % arr.length;
    return arr[idx]!;
  }
}

function canonicalizeAad(aad: string): string {
  // Preserve existing caller formatting; only normalize whitespace.
  return aad.trim();
}

function makePivotTopic(current: string, tongue: RWP2WireTongue, step: number): string {
  // Deterministic "pivot" that remains human-readable for audits.
  return `${current}::${tongue.toLowerCase()}::p${step}`;
}

/**
 * Generate a deterministic synthetic conversation as a list of signed envelopes.
 *
 * Each step:
 * - chooses a tongue
 * - derives a pivot topic
 * - emits a signed envelope with payload containing { step, from, to, tongue }
 *
 * @throws if any generated envelope fails verification (should never happen)
 */
export function generateSyntheticConversationV2Wire(params: {
  baseTopic: string;
  numPivots: number;
  seed: number;
  aad?: string;
  primaryTongue?: RWP2WireTongue;
  signingTongues?: RWP2WireTongue[];
  keyring: Keyring;
  policy?: 'standard' | 'strict' | 'critical';
}): SyntheticConversation {
  const {
    baseTopic,
    numPivots,
    seed,
    aad = 'source=synthetic;factory=spiralverse;ver=2',
    primaryTongue = 'KO',
    signingTongues = ['KO', 'RU'], // default to 2+ tongues for Roundtable
    keyring,
    policy = 'standard',
  } = params;

  const prng = new XorShift32(seed);
  const tongues: RWP2WireTongue[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];

  const envelopes: RWP2WireEnvelope[] = [];
  const edges: TopicEdge[] = [];

  let topic = baseTopic;
  const aadNorm = canonicalizeAad(aad);

  // Base timestamp in seconds.
  // Must not be in the future (verification rejects that) and should be recent enough
  // to pass replay windows in strict modes. We anchor to "now" and apply a small
  // deterministic offset so same-seed calls within a run remain stable.
  const nowSec = Math.floor(Date.now() / 1000);
  const ts0 = nowSec - 10 + (seed % 5);

  for (let i = 0; i < numPivots; i++) {
    const tongue = prng.pick(tongues);
    const next = makePivotTopic(topic, tongue, i);

    const payload = {
      step: i,
      from: topic,
      to: next,
      tongue,
    };

    const env = signRoundtableV2Wire(payload, primaryTongue, aadNorm, keyring, signingTongues, {
      timestamp: ts0 + i,
      nonce: prng.bytes(16),
    });

    const vr = verifyRoundtableV2Wire(env, keyring, { policy });
    if (!vr.valid) {
      throw new Error(`Synthetic envelope failed verification at step ${i}: ${vr.error ?? 'unknown error'}`);
    }

    envelopes.push(env);
    edges.push({ from: topic, to: next, tongue, step: i });
    topic = next;
  }

  return { baseTopic, envelopes, edges };
}
