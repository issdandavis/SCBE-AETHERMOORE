/**
 * @file auth.ts
 * @module conference/api/middleware
 *
 * JWT-based auth middleware. Verifies access tokens and attaches user to request.
 * Backwards-compatible: also accepts raw user ID tokens for existing sessions.
 */

import type { Request, Response, NextFunction } from 'express';
import { store } from '../store.js';
import { verifyAccessToken } from '../services/jwt.js';
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

  const token = authHeader.slice(7);

  // Try JWT verification first
  const payload = verifyAccessToken(token);
  if (payload) {
    const user = store.getUser(payload.sub);
    if (user) {
      req.user = user;
      next();
      return;
    }
  }

  // Fallback: treat token as raw user ID (backwards compat with existing sessions)
  const userById = store.getUser(token);
  if (userById) {
    req.user = userById;
    next();
    return;
  }

  res.status(401).json({ success: false, error: 'Invalid or expired token' });
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
