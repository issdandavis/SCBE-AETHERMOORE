/**
 * @file orgs.ts
 * @module conference/api/routes
 *
 * Organization (CaaS tenant) management routes.
 *
 * - Create/list organizations
 * - Update branding and governance config
 * - Manage API keys
 * - Add/remove members
 * - View plan limits and usage
 */

import { Router, type Request, type Response } from 'express';
import { authMiddleware } from '../middleware/auth.js';
import { tenantService, PLAN_LIMITS } from '../services/tenant.js';
import type { CaasPlan } from '../../shared/types/index.js';

const router = Router();

router.use(authMiddleware);

/**
 * POST /api/orgs
 * Create a new organization.
 * Body: { name, slug, plan? }
 */
router.post('/', (req: Request, res: Response) => {
  const { name, slug, plan } = req.body as {
    name?: string;
    slug?: string;
    plan?: CaasPlan;
  };

  if (!name || !slug) {
    res.status(400).json({ success: false, error: 'name and slug are required' });
    return;
  }

  const result = tenantService.createOrg(name, slug, req.user!.id, plan ?? 'starter');

  if ('error' in result) {
    res.status(400).json({ success: false, error: result.error });
    return;
  }

  res.status(201).json({ success: true, data: sanitizeOrg(result) });
});

/**
 * GET /api/orgs
 * List organizations owned by the current user.
 */
router.get('/', (req: Request, res: Response) => {
  const orgs = tenantService.listByOwner(req.user!.id);
  res.json({ success: true, data: orgs.map(sanitizeOrg) });
});

/**
 * GET /api/orgs/:slug
 * Get organization details by slug.
 */
router.get('/:slug', (req: Request, res: Response) => {
  const org = tenantService.getBySlug(req.params.slug);
  if (!org) {
    res.status(404).json({ success: false, error: 'Organization not found' });
    return;
  }

  // Only members see full details; others see public profile
  const isMember = tenantService.hasRole(org.id, req.user!.id, 'viewer');
  if (isMember) {
    res.json({ success: true, data: sanitizeOrg(org) });
  } else {
    res.json({
      success: true,
      data: {
        id: org.id,
        name: org.name,
        slug: org.slug,
        plan: org.plan,
        branding: org.branding,
      },
    });
  }
});

/**
 * PATCH /api/orgs/:slug/branding
 * Update organization branding (admin+).
 */
router.patch('/:slug/branding', (req: Request, res: Response) => {
  const org = tenantService.getBySlug(req.params.slug);
  if (!org) {
    res.status(404).json({ success: false, error: 'Organization not found' });
    return;
  }

  if (!tenantService.hasRole(org.id, req.user!.id, 'admin')) {
    res.status(403).json({ success: false, error: 'Requires admin role' });
    return;
  }

  const updated = tenantService.updateBranding(org.id, req.body);
  if (!updated) {
    res.status(400).json({ success: false, error: 'Branding update failed (check plan limits)' });
    return;
  }

  res.json({ success: true, data: sanitizeOrg(updated) });
});

/**
 * PATCH /api/orgs/:slug/governance
 * Update governance configuration (admin+).
 */
router.patch('/:slug/governance', (req: Request, res: Response) => {
  const org = tenantService.getBySlug(req.params.slug);
  if (!org) {
    res.status(404).json({ success: false, error: 'Organization not found' });
    return;
  }

  if (!tenantService.hasRole(org.id, req.user!.id, 'admin')) {
    res.status(403).json({ success: false, error: 'Requires admin role' });
    return;
  }

  const updated = tenantService.updateGovernanceConfig(org.id, req.body);
  if (!updated) {
    res.status(400).json({ success: false, error: 'Governance update failed (check plan limits)' });
    return;
  }

  res.json({ success: true, data: updated.governanceConfig });
});

/**
 * POST /api/orgs/:slug/rotate-key
 * Rotate API key (owner only).
 */
router.post('/:slug/rotate-key', (req: Request, res: Response) => {
  const org = tenantService.getBySlug(req.params.slug);
  if (!org) {
    res.status(404).json({ success: false, error: 'Organization not found' });
    return;
  }

  if (!tenantService.hasRole(org.id, req.user!.id, 'owner')) {
    res.status(403).json({ success: false, error: 'Only the owner can rotate API keys' });
    return;
  }

  const newKey = tenantService.rotateApiKey(org.id);
  res.json({ success: true, data: { apiKey: newKey } });
});

/**
 * GET /api/orgs/:slug/members
 * List organization members (viewer+).
 */
router.get('/:slug/members', (req: Request, res: Response) => {
  const org = tenantService.getBySlug(req.params.slug);
  if (!org) {
    res.status(404).json({ success: false, error: 'Organization not found' });
    return;
  }

  if (!tenantService.hasRole(org.id, req.user!.id, 'viewer')) {
    res.status(403).json({ success: false, error: 'Not a member of this organization' });
    return;
  }

  const members = tenantService.getMembers(org.id);
  res.json({ success: true, data: members });
});

/**
 * POST /api/orgs/:slug/members
 * Add a member to the organization (admin+).
 * Body: { userId, role }
 */
router.post('/:slug/members', (req: Request, res: Response) => {
  const org = tenantService.getBySlug(req.params.slug);
  if (!org) {
    res.status(404).json({ success: false, error: 'Organization not found' });
    return;
  }

  if (!tenantService.hasRole(org.id, req.user!.id, 'admin')) {
    res.status(403).json({ success: false, error: 'Requires admin role' });
    return;
  }

  const { userId, role } = req.body as { userId?: string; role?: string };
  if (!userId) {
    res.status(400).json({ success: false, error: 'userId is required' });
    return;
  }

  const validRoles = ['viewer', 'curator', 'admin'];
  const memberRole = validRoles.includes(role ?? '') ? (role as any) : 'viewer';

  const member = tenantService.addMember(org.id, userId, memberRole);
  if (!member) {
    res.status(400).json({ success: false, error: 'Failed to add member (already exists or org not found)' });
    return;
  }

  res.status(201).json({ success: true, data: member });
});

/**
 * GET /api/orgs/:slug/limits
 * Get plan limits and current usage.
 */
router.get('/:slug/limits', (req: Request, res: Response) => {
  const org = tenantService.getBySlug(req.params.slug);
  if (!org) {
    res.status(404).json({ success: false, error: 'Organization not found' });
    return;
  }

  if (!tenantService.hasRole(org.id, req.user!.id, 'viewer')) {
    res.status(403).json({ success: false, error: 'Not a member' });
    return;
  }

  const limits = PLAN_LIMITS[org.plan];
  res.json({
    success: true,
    data: { plan: org.plan, limits, usage: org.usage },
  });
});

/**
 * GET /api/orgs/plans/all
 * Get all available plans and their limits (public).
 */
router.get('/plans/all', (_req: Request, res: Response) => {
  res.json({ success: true, data: PLAN_LIMITS });
});

/** Strip API key from org responses (show only to owner) */
function sanitizeOrg(org: any): any {
  const { apiKey, zoomConfig, ...safe } = org;
  return { ...safe, apiKeyPrefix: apiKey ? `${apiKey.slice(0, 12)}...` : null };
}

export default router;
