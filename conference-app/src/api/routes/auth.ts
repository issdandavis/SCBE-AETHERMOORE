/**
 * @file auth.ts
 * @module conference/api/routes
 *
 * Auth routes: register, login (simplified for MVP).
 * Production would use passwordless (email magic link) for coders,
 * stronger KYC-verified flow for investors.
 */

import { Router, type Request, type Response } from 'express';
import { v4 as uuid } from 'uuid';
import { store } from '../store.js';
import type { User, UserRole, ApiResponse } from '../../shared/types/index.js';

const router = Router();

/**
 * POST /api/auth/register
 * Body: { email, displayName, role }
 */
router.post('/register', (req: Request, res: Response) => {
  const { email, displayName, role } = req.body as {
    email?: string;
    displayName?: string;
    role?: UserRole;
  };

  if (!email || !displayName || !role) {
    const resp: ApiResponse<null> = { success: false, error: 'email, displayName, and role are required' };
    res.status(400).json(resp);
    return;
  }

  if (!['coder', 'investor', 'curator'].includes(role)) {
    const resp: ApiResponse<null> = { success: false, error: 'role must be coder, investor, or curator' };
    res.status(400).json(resp);
    return;
  }

  const existing = store.getUserByEmail(email);
  if (existing) {
    const resp: ApiResponse<null> = { success: false, error: 'Email already registered' };
    res.status(409).json(resp);
    return;
  }

  const user: User = {
    id: uuid(),
    email,
    displayName,
    role,
    createdAt: new Date().toISOString(),
    kycStatus: role === 'investor' ? 'pending' : undefined,
  };

  store.setUser(user);

  const resp: ApiResponse<{ user: User; token: string }> = {
    success: true,
    data: { user, token: user.id },
  };
  res.status(201).json(resp);
});

/**
 * POST /api/auth/login
 * Body: { email }
 * MVP: returns token (user ID) directly. Production: send magic link.
 */
router.post('/login', (req: Request, res: Response) => {
  const { email } = req.body as { email?: string };
  if (!email) {
    res.status(400).json({ success: false, error: 'email is required' });
    return;
  }

  const user = store.getUserByEmail(email);
  if (!user) {
    res.status(404).json({ success: false, error: 'User not found' });
    return;
  }

  res.json({ success: true, data: { user, token: user.id } });
});

export default router;
