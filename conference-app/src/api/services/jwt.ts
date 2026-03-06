/**
 * @file jwt.ts
 * @module conference/api/services
 *
 * JWT-based authentication. Replaces the "token = user ID" MVP approach.
 *
 * - Access tokens: short-lived (15min), stateless, contain user ID + role
 * - Refresh tokens: long-lived (7d), stored hashed in DB, rotated on use
 * - Passwords: hashed with Node's built-in scrypt (no bcrypt native dep needed)
 */

import jwt from 'jsonwebtoken';
import { scryptSync, randomBytes, timingSafeEqual } from 'crypto';

// ═══════════════════════════════════════════════════════════════
// Config
// ═══════════════════════════════════════════════════════════════

const JWT_SECRET = process.env.JWT_SECRET ?? 'vibe-conference-dev-secret-change-in-prod';
const ACCESS_TOKEN_EXPIRY = '15m';
const REFRESH_TOKEN_EXPIRY_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

export interface AccessTokenPayload {
  sub: string;       // user ID
  email: string;
  role: string;
  displayName: string;
}

// ═══════════════════════════════════════════════════════════════
// Password Hashing (scrypt — no native bcrypt dependency)
// ═══════════════════════════════════════════════════════════════

/**
 * Hash a password with scrypt + random salt.
 * Returns "salt:hash" as a single string.
 */
export function hashPassword(password: string): string {
  const salt = randomBytes(16).toString('hex');
  const hash = scryptSync(password, salt, 64).toString('hex');
  return `${salt}:${hash}`;
}

/**
 * Verify a password against a stored "salt:hash" string.
 * Uses timing-safe comparison to prevent timing attacks.
 */
export function verifyPassword(password: string, stored: string): boolean {
  const [salt, storedHash] = stored.split(':');
  if (!salt || !storedHash) return false;
  const hash = scryptSync(password, salt, 64);
  const storedBuf = Buffer.from(storedHash, 'hex');
  if (hash.length !== storedBuf.length) return false;
  return timingSafeEqual(hash, storedBuf);
}

// ═══════════════════════════════════════════════════════════════
// JWT Token Management
// ═══════════════════════════════════════════════════════════════

/**
 * Sign an access token (short-lived, stateless).
 */
export function signAccessToken(payload: AccessTokenPayload): string {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: ACCESS_TOKEN_EXPIRY });
}

/**
 * Verify and decode an access token.
 * Returns the payload or null if invalid/expired.
 */
export function verifyAccessToken(token: string): AccessTokenPayload | null {
  try {
    const decoded = jwt.verify(token, JWT_SECRET) as AccessTokenPayload & { exp: number };
    return { sub: decoded.sub, email: decoded.email, role: decoded.role, displayName: decoded.displayName };
  } catch {
    return null;
  }
}

/**
 * Generate a refresh token (random bytes, stored hashed in DB).
 */
export function generateRefreshToken(): { token: string; hash: string; expiresAt: string } {
  const token = randomBytes(48).toString('hex');
  const hash = scryptSync(token, 'refresh-salt', 32).toString('hex');
  const expiresAt = new Date(Date.now() + REFRESH_TOKEN_EXPIRY_MS).toISOString();
  return { token, hash, expiresAt };
}

/**
 * Hash a refresh token for DB lookup.
 */
export function hashRefreshToken(token: string): string {
  return scryptSync(token, 'refresh-salt', 32).toString('hex');
}
