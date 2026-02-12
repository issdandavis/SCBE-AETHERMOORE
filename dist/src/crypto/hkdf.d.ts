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
export declare function hkdfSha256(ikm: Buffer, salt: Buffer, info: Buffer, len: number): Buffer;
//# sourceMappingURL=hkdf.d.ts.map