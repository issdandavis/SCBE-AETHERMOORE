import { hkdfSha256 } from './hkdf.js';
import crypto from 'node:crypto';

type SessionKey = string;
const counters = new Map<SessionKey, number>();

export function deriveNoncePrefix(kNonce: Buffer, sessionId: string): Buffer {
  // 64-bit prefix: HKDF(k_nonce, session_id)
  const info = Buffer.from(`scbe:nonce:prefix:v1`);
  const salt = crypto.createHash('sha256').update(sessionId).digest();
  return hkdfSha256(kNonce, salt, info, 8);
}

export function nextNonce(prefix: Buffer, sessionId: string): { nonce: Buffer; counter: number } {
  const key = sessionId;
  const cur = counters.get(key) ?? -1;
  const next = (cur + 1) >>> 0; // 32-bit counter
  counters.set(key, next);

  // Rotate before wrap
  if (next === 0xffffffff) {
    throw new Error('nonce counter exhausted; rotate key/session');
  }
  const counterBuf = Buffer.alloc(4);
  counterBuf.writeUInt32BE(next, 0);
  return { nonce: Buffer.concat([prefix, counterBuf]), counter: next };
}

export function resetSessionCounter(sessionId: string) {
  counters.delete(sessionId);
}
