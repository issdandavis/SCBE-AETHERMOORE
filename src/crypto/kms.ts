/**
 * Replace with your real KMS/HSM integration.
 * Contract: getMasterKey(kid) returns a 32-byte key (Buffer) with export disabled in production.
 */
import crypto from 'node:crypto';

const cache = new Map<string, Buffer>();

export async function getMasterKey(kid: string): Promise<Buffer> {
  if (cache.has(kid)) return cache.get(kid)!;

  const uri = process.env.SCBE_KMS_URI || 'mem://dev';
  // DEMO ONLY: derive a process-unique pseudo-key from kid+uri (DO NOT USE IN PROD)
  const key = crypto.createHash('sha256').update(`${uri}:${kid}`).digest(); // 32 bytes
  cache.set(kid, key);
  return key;
}
