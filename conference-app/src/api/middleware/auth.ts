/**
 * @file auth.ts
 * @module conference/api/middleware
 *
 * Simplified auth middleware for MVP.
 * Uses a bearer token that is just the user ID (replace with JWT/WebAuthn in production).
 */

import type { Request, Response, NextFunction } from 'express';
import { store } from '../store.js';
import type { User } from '../../shared/types/index.js';

declare global {
  namespace Express {
    interface Request {
      user?: User;
    }
  }
}

export function authMiddleware(req: Request, res: Response, next: NextFunction): void {
  const authHeader = req.headers.authorization;
  if (!authHeader?.startsWith('Bearer ')) {
    res.status(401).json({ success: false, error: 'Missing authorization header' });
    return;
  }

  const userId = authHeader.slice(7);
  const user = store.getUser(userId);
  if (!user) {
    res.status(401).json({ success: false, error: 'Invalid user token' });
    return;
  }

  req.user = user;
  next();
}

export function requireRole(...roles: string[]) {
  return (req: Request, res: Response, next: NextFunction): void => {
    if (!req.user) {
      res.status(401).json({ success: false, error: 'Not authenticated' });
      return;
    }
    if (!roles.includes(req.user.role)) {
      res.status(403).json({ success: false, error: `Requires role: ${roles.join(' or ')}` });
      return;
    }
    next();
  };
}
