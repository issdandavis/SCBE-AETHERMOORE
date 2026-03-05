/**
 * @file funding.ts
 * @module conference/api/routes
 *
 * Funding routes: soft-commits, deal rooms, interest ticker.
 * During live conferences, investors register interest and soft-commit
 * check sizes (non-binding). Post-event, deal rooms are opened for
 * serious follow-up.
 */

import { Router, type Request, type Response } from 'express';
import { v4 as uuid } from 'uuid';
import { store } from '../store.js';
import { authMiddleware, requireRole } from '../middleware/auth.js';
import { liveEventBus } from '../services/liveEvents.js';
import type { SoftCommit, DealRoom, ApiResponse } from '../../shared/types/index.js';

const router = Router();

router.use(authMiddleware);

/**
 * POST /api/funding/soft-commit
 * Register a soft-commit during a live conference (investor only, NDA required).
 */
router.post('/soft-commit', requireRole('investor'), (req: Request, res: Response) => {
  const { projectId, conferenceId, amount, tier, interestLevel, note } = req.body as {
    projectId?: string;
    conferenceId?: string;
    amount?: number;
    tier?: SoftCommit['tier'];
    interestLevel?: SoftCommit['interestLevel'];
    note?: string;
  };

  if (!projectId || !conferenceId || !amount || !tier) {
    res.status(400).json({ success: false, error: 'projectId, conferenceId, amount, and tier are required' });
    return;
  }

  // Verify NDA
  const investorId = req.user!.id;
  if (!store.hasSignedNda(investorId, null)) {
    res.status(403).json({ success: false, error: 'Platform NDA required before soft-committing' });
    return;
  }

  // Verify conference is live
  const conf = store.conferences.get(conferenceId);
  if (!conf || conf.status !== 'live') {
    res.status(400).json({ success: false, error: 'Conference must be live for soft-commits' });
    return;
  }

  // Verify project is in the conference
  const inConf = conf.slots.some(s => s.projectId === projectId);
  if (!inConf) {
    res.status(400).json({ success: false, error: 'Project is not scheduled in this conference' });
    return;
  }

  const commit: SoftCommit = {
    id: uuid(),
    investorId,
    projectId,
    conferenceId,
    amount,
    tier,
    interestLevel: interestLevel ?? 'interested',
    note,
    createdAt: new Date().toISOString(),
  };

  store.softCommits.set(commit.id, commit);

  // Broadcast real-time event to live conference
  const project = store.getProject(projectId);
  liveEventBus.emitNewCommit(
    conferenceId,
    req.user!.displayName,
    project?.title ?? projectId,
    amount,
    tier
  );

  // Also broadcast updated ticker
  const allCommits = store.listSoftCommits({ conferenceId });
  const byProject: Record<string, { projectId: string; totalAmount: number; commitCount: number }> = {};
  for (const c of allCommits) {
    if (!byProject[c.projectId]) byProject[c.projectId] = { projectId: c.projectId, totalAmount: 0, commitCount: 0 };
    byProject[c.projectId].totalAmount += c.amount;
    byProject[c.projectId].commitCount += 1;
  }
  liveEventBus.emitTickerUpdate(conferenceId, Object.values(byProject));

  res.status(201).json({ success: true, data: commit } as ApiResponse<SoftCommit>);
});

/**
 * GET /api/funding/ticker/:conferenceId
 * Get the live soft-commit ticker for a conference.
 * Returns aggregated interest without revealing individual investor identities
 * (except to the project creator).
 */
router.get('/ticker/:conferenceId', (req: Request, res: Response) => {
  const commits = store.listSoftCommits({ conferenceId: req.params.conferenceId });

  // Aggregate by project
  const byProject: Record<string, { projectId: string; totalAmount: number; commitCount: number; latestTier: string }> = {};

  for (const c of commits) {
    if (!byProject[c.projectId]) {
      byProject[c.projectId] = { projectId: c.projectId, totalAmount: 0, commitCount: 0, latestTier: c.tier };
    }
    byProject[c.projectId].totalAmount += c.amount;
    byProject[c.projectId].commitCount += 1;
    byProject[c.projectId].latestTier = c.tier;
  }

  const ticker = Object.values(byProject).sort((a, b) => b.totalAmount - a.totalAmount);

  res.json({ success: true, data: ticker });
});

/**
 * GET /api/funding/commits/:projectId
 * Get all soft-commits for a project (project creator or curator only).
 */
router.get('/commits/:projectId', (req: Request, res: Response) => {
  const project = store.getProject(req.params.projectId);
  if (!project) {
    res.status(404).json({ success: false, error: 'Project not found' });
    return;
  }

  const user = req.user!;
  if (user.role !== 'curator' && project.creatorId !== user.id) {
    res.status(403).json({ success: false, error: 'Only project creator or curator can view commits' });
    return;
  }

  const commits = store.listSoftCommits({ projectId: req.params.projectId });
  const totalAmount = commits.reduce((s, c) => s + c.amount, 0);

  res.json({
    success: true,
    data: { commits, totalAmount, commitCount: commits.length },
  });
});

/**
 * POST /api/funding/deal-room
 * Open a deal room for a project (curator only).
 */
router.post('/deal-room', requireRole('curator'), (req: Request, res: Response) => {
  const { projectId } = req.body as { projectId?: string };
  if (!projectId) {
    res.status(400).json({ success: false, error: 'projectId is required' });
    return;
  }

  const project = store.getProject(projectId);
  if (!project) {
    res.status(404).json({ success: false, error: 'Project not found' });
    return;
  }

  const commits = store.listSoftCommits({ projectId });
  const investorIds = [...new Set(commits.map(c => c.investorId))];
  const totalSoftCommits = commits.reduce((s, c) => s + c.amount, 0);

  const dealRoom: DealRoom = {
    id: uuid(),
    projectId,
    investorIds,
    documents: [],
    status: 'open',
    totalSoftCommits,
    createdAt: new Date().toISOString(),
  };

  store.dealRooms.set(dealRoom.id, dealRoom);

  res.status(201).json({ success: true, data: dealRoom } as ApiResponse<DealRoom>);
});

export default router;
