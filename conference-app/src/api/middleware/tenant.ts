/**
 * @file tenant.ts
 * @module conference/api/middleware
 *
 * Tenant resolution middleware for CaaS multi-tenancy.
 *
 * Resolution order:
 * 1. x-org-api-key header (programmatic access)
 * 2. x-org-slug header (frontend access)
 * 3. :orgSlug route param (URL-based)
 *
 * Attaches the resolved Organization to req.org.
 * Enforces plan limits on write operations.
 */

import type { Request, Response, NextFunction } from 'express';
import { tenantService, PLAN_LIMITS } from '../services/tenant.js';
import type { Organization } from '../../shared/types/index.js';

declare global {
  namespace Express {
    interface Request {
      org?: Organization;
    }
  }
}

/**
 * Resolve tenant from request. Attaches req.org if found.
 * Does NOT reject requests without a tenant — allows platform-level access.
 */
export function tenantResolver(req: Request, _res: Response, next: NextFunction): void {
  // 1. API key header
  const apiKey = req.headers['x-org-api-key'] as string | undefined;
  if (apiKey) {
    req.org = tenantService.getByApiKey(apiKey);
    next();
    return;
  }

  // 2. Slug header
  const slugHeader = req.headers['x-org-slug'] as string | undefined;
  if (slugHeader) {
    req.org = tenantService.getBySlug(slugHeader);
    next();
    return;
  }

  // 3. Route param
  const orgSlug = req.params.orgSlug as string | undefined;
  if (orgSlug) {
    req.org = tenantService.getBySlug(orgSlug);
  }

  next();
}

/**
 * Require a resolved tenant. Returns 400 if no org is set.
 */
export function requireTenant(req: Request, res: Response, next: NextFunction): void {
  if (!req.org) {
    res.status(400).json({
      success: false,
      error: 'Organization context required. Set x-org-slug or x-org-api-key header.',
    });
    return;
  }
  next();
}

/**
 * Check that the requesting user has at least the given role in the tenant.
 */
export function requireOrgRole(...roles: Array<'owner' | 'admin' | 'curator' | 'viewer'>) {
  return (req: Request, res: Response, next: NextFunction): void => {
    if (!req.org || !req.user) {
      res.status(403).json({ success: false, error: 'Authentication and organization context required' });
      return;
    }

    const minRole = roles[0];
    if (!tenantService.hasRole(req.org.id, req.user.id, minRole)) {
      res.status(403).json({ success: false, error: `Requires ${roles.join(' or ')} role in ${req.org.name}` });
      return;
    }

    next();
  };
}

/**
 * Enforce conference creation limit for the current org's plan.
 */
export function enforceConferenceLimit(req: Request, res: Response, next: NextFunction): void {
  if (!req.org) {
    next();
    return;
  }

  if (!tenantService.canCreateConference(req.org.id)) {
    const limits = PLAN_LIMITS[req.org.plan];
    res.status(429).json({
      success: false,
      error: `Conference limit reached (${limits.maxConferencesPerMonth}/month on ${req.org.plan} plan). Upgrade to create more.`,
      plan: req.org.plan,
      limit: limits.maxConferencesPerMonth,
    });
    return;
  }

  next();
}
