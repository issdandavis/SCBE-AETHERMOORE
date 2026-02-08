import crypto from 'node:crypto';

/**
 * Type for crypto.hkdfSync which exists in Node.js 18+
 * but may not be in older @types/node definitions
 */
type HkdfSyncFn = (
  digest: string,
  ikm: crypto.BinaryLike,
  salt: crypto.BinaryLike,
  info: crypto.BinaryLike,
  keylen: number
) => ArrayBuffer;

/**
 * Check if hkdfSync is available (Node.js 18+)
 */
function hasHkdfSync(): boolean {
  return typeof (crypto as { hkdfSync?: HkdfSyncFn }).hkdfSync === 'function';
}

/**
 * Get hkdfSync function if available
 */
function getHkdfSync(): HkdfSyncFn | undefined {
  return (crypto as { hkdfSync?: HkdfSyncFn }).hkdfSync;
}

/**
 * Derive key material using HKDF-SHA256
 * Uses native crypto.hkdfSync when available (Node.js 18+),
 * falls back to manual implementation for older versions.
 *
 * @param ikm - Input keying material
 * @param salt - Salt value
 * @param info - Context/application-specific info
 * @param len - Desired output length in bytes
 * @returns Derived key material
 */
export function hkdfSha256(ikm: Buffer, salt: Buffer, info: Buffer, len: number): Buffer {
  const hkdfSync = getHkdfSync();
  if (hasHkdfSync() && hkdfSync) {
    const result = hkdfSync('sha256', ikm, salt, info, len);
    // hkdfSync returns ArrayBuffer in newer Node versions, convert to Buffer
    return Buffer.from(result);
  }
  // Fallback implementation for older Node.js versions
  const prk = crypto.createHmac('sha256', salt).update(ikm).digest();
  const n = Math.ceil(len / 32);
  let t = Buffer.alloc(0);
  let okm = Buffer.alloc(0);
  for (let i = 0; i < n; i++) {
    t = crypto
      .createHmac('sha256', prk)
      .update(Buffer.concat([t, info, Buffer.from([i + 1])]))
      .digest();
    okm = Buffer.concat([okm, t]);
  }
  return okm.subarray(0, len);
}
