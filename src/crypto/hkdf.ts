import crypto from 'node:crypto';

export function hkdfSha256(ikm: Buffer, salt: Buffer, info: Buffer, len: number): Buffer {
  if ((crypto as any).hkdfSync) {
    const result = (crypto as any).hkdfSync('sha256', ikm, salt, info, len);
    // hkdfSync returns ArrayBuffer in newer Node versions, convert to Buffer
    return Buffer.from(result);
  }
  // Fallback implementation
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
