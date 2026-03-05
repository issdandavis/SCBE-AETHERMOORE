/**
 * @file ndas.ts
 * @module conference/api/routes
 *
 * NDA workflow routes.
 * Investors must sign a platform NDA before seeing sensitive materials.
 * Project-specific NDAs gate access to deep IP / defense projects.
 *
 * In production, this would integrate with DocuSign/CLM for e-signature.
 */

import { Router, type Request, type Response } from 'express';
import { v4 as uuid } from 'uuid';
import { store } from '../store.js';
import { authMiddleware, requireRole } from '../middleware/auth.js';
import { computeAccessLevel } from '../../shared/governance/scbeGate.js';
import type { NDARecord, ApiResponse, AccessLevel } from '../../shared/types/index.js';

const router = Router();

router.use(authMiddleware);

/**
 * POST /api/ndas/sign
 * Sign an NDA (platform-wide or project-specific).
 * Body: { projectId?: string }
 *
 * MVP: auto-signs immediately. Production: triggers DocuSign envelope,
 * waits for webhook callback to mark as signed.
 */
router.post('/sign', requireRole('investor'), (req: Request, res: Response) => {
  const { projectId } = req.body as { projectId?: string };
  const investorId = req.user!.id;

  // Check if already signed
  const alreadySigned = store.hasSignedNda(investorId, projectId ?? null);
  if (alreadySigned) {
    res.status(409).json({ success: false, error: 'NDA already signed' });
    return;
  }

  // If project-specific, verify project exists and platform NDA is signed
  if (projectId) {
    const project = store.getProject(projectId);
    if (!project) {
      res.status(404).json({ success: false, error: 'Project not found' });
      return;
    }
    if (!store.hasSignedNda(investorId, null)) {
      res.status(400).json({ success: false, error: 'Must sign platform NDA first' });
      return;
    }
  }

  const nda: NDARecord = {
    id: uuid(),
    investorId,
    projectId: projectId ?? null,
    templateId: projectId ? 'project-nda-v1' : 'platform-nda-v1',
    status: 'signed',
    envelopeId: `env-${uuid().slice(0, 8)}`,
    signedAt: new Date().toISOString(),
    expiresAt: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
    createdAt: new Date().toISOString(),
  };

  store.setNda(nda);

  res.status(201).json({ success: true, data: nda } as ApiResponse<NDARecord>);
});

/**
 * GET /api/ndas/status
 * Check NDA status for current investor.
 * Query: ?projectId=xxx (optional)
 */
router.get('/status', requireRole('investor'), (req: Request, res: Response) => {
  const investorId = req.user!.id;
  const projectId = req.query.projectId as string | undefined;

  const platformSigned = store.hasSignedNda(investorId, null);
  const projectSigned = projectId ? store.hasSignedNda(investorId, projectId) : false;

  res.json({
    success: true,
    data: {
      platformNdaSigned: platformSigned,
      projectNdaSigned: projectSigned,
    },
  });
});

/**
 * GET /api/ndas/access/:projectId
 * Get the access level for an investor viewing a specific project.
 */
router.get('/access/:projectId', requireRole('investor'), (req: Request, res: Response) => {
  const project = store.getProject(req.params.projectId);
  if (!project) {
    res.status(404).json({ success: false, error: 'Project not found' });
    return;
  }

  const ndaSigned = store.hasSignedNda(req.user!.id, null) || store.hasSignedNda(req.user!.id, project.id);
  const decision = project.governance?.decision ?? 'DENY';

  const access = computeAccessLevel(ndaSigned, decision);
  res.json({ success: true, data: access } as ApiResponse<AccessLevel>);
});

export default router;
