/**
 * KMS / HSM integration point.
 * Contract: getMasterKey(kid) returns a 32-byte key (Buffer).
 *
 * Set SCBE_KMS_URI to your KMS endpoint (e.g., "awskms://alias/scbe-master").
 * The mem://dev fallback is only allowed when NODE_ENV=development or NODE_ENV=test.
 */
import crypto from 'node:crypto';

const cache = new Map<string, Buffer>();

export async function getMasterKey(kid: string): Promise<Buffer> {
  if (cache.has(kid)) return cache.get(kid)!;

  const uri = process.env.SCBE_KMS_URI;
  const env = process.env.NODE_ENV || '';

  if (!uri) {
    if (env === 'development' || env === 'test') {
      // In-memory dev key derivation — deterministic, NOT secure.
      const key = crypto.createHash('sha256').update(`mem://dev:${kid}`).digest();
      cache.set(kid, key);
      return key;
    }
    throw new Error(
      'SCBE_KMS_URI is not set. Set it to your KMS endpoint (e.g., "awskms://alias/scbe-master") ' +
      'or set NODE_ENV=development for local testing.'
    );
  }

  if (uri === 'mem://dev' && env !== 'development' && env !== 'test') {
    throw new Error(
      'SCBE_KMS_URI=mem://dev is not allowed outside development/test. ' +
      'Configure a real KMS endpoint for production.'
    );
  }

  // Derive key from KMS URI + key ID. Replace this block with actual KMS API call.
  const key = crypto.createHash('sha256').update(`${uri}:${kid}`).digest();
  cache.set(kid, key);
  return key;
}
