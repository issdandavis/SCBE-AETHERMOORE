/**
 * @file auth.ts
 * @module conference/api/routes
 *
 * Auth routes: register, login, refresh, me.
 * Uses JWT access tokens (15min) + refresh tokens (7d).
 * Passwords hashed with scrypt.
 */

import { Router, type Request, type Response } from 'express';
import { randomUUID } from 'crypto';
import { store } from '../store.js';
import { authMiddleware } from '../middleware/auth.js';
import {
  hashPassword,
  verifyPassword,
  signAccessToken,
  generateRefreshToken,
  hashRefreshToken,
} from '../services/jwt.js';
import type { User, UserRole, ApiResponse } from '../../shared/types/index.js';

const router = Router();

/** In-memory refresh token store (moves to DB with database.ts) */
const refreshTokens: Map<string, { userId: string; expiresAt: string }> = new Map();

/**
 * POST /api/auth/register
 * Body: { email, displayName, role, password }
 */
router.post('/register', (req: Request, res: Response) => {
  const { email, displayName, role, password } = req.body as {
    email?: string;
    displayName?: string;
    role?: UserRole;
    password?: string;
  };

  if (!email || !displayName || !role || !password) {
    res.status(400).json({ success: false, error: 'email, displayName, role, and password are required' });
    return;
  }

  if (password.length < 8) {
    res.status(400).json({ success: false, error: 'Password must be at least 8 characters' });
    return;
  }

  if (!['coder', 'investor', 'curator'].includes(role)) {
    res.status(400).json({ success: false, error: 'role must be coder, investor, or curator' });
    return;
  }

  const existing = store.getUserByEmail(email);
  if (existing) {
    res.status(409).json({ success: false, error: 'Email already registered' });
    return;
  }

  const passwordHash = hashPassword(password);

  const user: User = {
    id: randomUUID(),
    email,
    displayName,
    role,
    createdAt: new Date().toISOString(),
    kycStatus: role === 'investor' ? 'pending' : undefined,
  };

  // Store user with password hash
  store.setUser(user);
  (store as any)._passwordHashes ??= new Map();
  (store as any)._passwordHashes.set(user.id, passwordHash);

  // Generate tokens
  const accessToken = signAccessToken({
    sub: user.id,
    email: user.email,
    role: user.role,
    displayName: user.displayName,
  });

  const refresh = generateRefreshToken();
  refreshTokens.set(refresh.hash, { userId: user.id, expiresAt: refresh.expiresAt });

  res.status(201).json({
    success: true,
    data: { user, token: accessToken, refreshToken: refresh.token },
  } as ApiResponse<{ user: User; token: string; refreshToken: string }>);
});

/**
 * POST /api/auth/login
 * Body: { email, password }
 */
router.post('/login', (req: Request, res: Response) => {
  const { email, password } = req.body as { email?: string; password?: string };

  if (!email || !password) {
    res.status(400).json({ success: false, error: 'email and password are required' });
    return;
  }

  const user = store.getUserByEmail(email);
  if (!user) {
    // Timing-safe: still hash to prevent user enumeration
    hashPassword('dummy-password-to-prevent-timing-attack');
    res.status(401).json({ success: false, error: 'Invalid email or password' });
    return;
  }

  const storedHash = (store as any)._passwordHashes?.get(user.id);
  if (!storedHash || !verifyPassword(password, storedHash)) {
    res.status(401).json({ success: false, error: 'Invalid email or password' });
    return;
  }

  const accessToken = signAccessToken({
    sub: user.id,
    email: user.email,
    role: user.role,
    displayName: user.displayName,
  });

  const refresh = generateRefreshToken();
  refreshTokens.set(refresh.hash, { userId: user.id, expiresAt: refresh.expiresAt });

  res.json({
    success: true,
    data: { user, token: accessToken, refreshToken: refresh.token },
  });
});

/**
 * POST /api/auth/refresh
 * Body: { refreshToken }
 * Returns new access token + rotated refresh token.
 */
router.post('/refresh', (req: Request, res: Response) => {
  const { refreshToken } = req.body as { refreshToken?: string };
  if (!refreshToken) {
    res.status(400).json({ success: false, error: 'refreshToken required' });
    return;
  }

  const hash = hashRefreshToken(refreshToken);
  const stored = refreshTokens.get(hash);

  if (!stored) {
    res.status(401).json({ success: false, error: 'Invalid refresh token' });
    return;
  }

  if (new Date(stored.expiresAt) < new Date()) {
    refreshTokens.delete(hash);
    res.status(401).json({ success: false, error: 'Refresh token expired' });
    return;
  }

  // Rotate: delete old, issue new
  refreshTokens.delete(hash);

  const user = store.getUser(stored.userId);
  if (!user) {
    res.status(401).json({ success: false, error: 'User no longer exists' });
    return;
  }

  const accessToken = signAccessToken({
    sub: user.id,
    email: user.email,
    role: user.role,
    displayName: user.displayName,
  });

  const newRefresh = generateRefreshToken();
  refreshTokens.set(newRefresh.hash, { userId: user.id, expiresAt: newRefresh.expiresAt });

  res.json({
    success: true,
    data: { user, token: accessToken, refreshToken: newRefresh.token },
  });
});

/**
 * GET /api/auth/me
 * Returns current user from access token.
 */
router.get('/me', authMiddleware, (req: Request, res: Response) => {
  res.json({ success: true, data: req.user });
});

export default router;
