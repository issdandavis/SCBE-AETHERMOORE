/**
 * @file conferences.ts
 * @module conference/api/routes
 *
 * Conference / Demo Day management routes.
 * Curators create themed conferences, assign project slots.
 * Projects must be ALLOW-status to be scheduled.
 */

import { Router, type Request, type Response } from 'express';
import { v4 as uuid } from 'uuid';
import { store } from '../store.js';
import { authMiddleware, requireRole } from '../middleware/auth.js';
import type { Conference, ConferenceSlot, ApiResponse } from '../../shared/types/index.js';

const router = Router();

router.use(authMiddleware);

/**
 * POST /api/conferences
 * Create a new conference / demo day (curator only).
 */
router.post('/', requireRole('curator'), (req: Request, res: Response) => {
  const { title, theme, description, scheduledAt, duration } = req.body as {
    title?: string;
    theme?: string;
    description?: string;
    scheduledAt?: string;
    duration?: number;
  };

  if (!title || !theme || !description || !scheduledAt) {
    res.status(400).json({ success: false, error: 'title, theme, description, and scheduledAt are required' });
    return;
  }

  const conference: Conference = {
    id: uuid(),
    title,
    theme,
    description,
    status: 'scheduled',
    scheduledAt,
    duration: duration ?? 120,
    slots: [],
    createdAt: new Date().toISOString(),
  };

  store.conferences.set(conference.id, conference);
  res.status(201).json({ success: true, data: conference } as ApiResponse<Conference>);
});

/**
 * GET /api/conferences
 * List all conferences.
 */
router.get('/', (_req: Request, res: Response) => {
  const conferences = Array.from(store.conferences.values())
    .sort((a, b) => b.scheduledAt.localeCompare(a.scheduledAt));
  res.json({ success: true, data: conferences, meta: { total: conferences.length } });
});

/**
 * GET /api/conferences/:id
 */
router.get('/:id', (req: Request, res: Response) => {
  const conf = store.conferences.get(req.params.id);
  if (!conf) {
    res.status(404).json({ success: false, error: 'Conference not found' });
    return;
  }

  // Enrich slots with project data
  const enrichedSlots = conf.slots.map(slot => {
    const project = store.getProject(slot.projectId);
    return { ...slot, project };
  });

  res.json({ success: true, data: { ...conf, slots: enrichedSlots } });
});

/**
 * POST /api/conferences/:id/slots
 * Add a project slot to a conference (curator only).
 * Body: { projectId, durationMinutes?, pitchMinutes?, qaMinutes? }
 */
router.post('/:id/slots', requireRole('curator'), (req: Request, res: Response) => {
  const conf = store.conferences.get(req.params.id);
  if (!conf) {
    res.status(404).json({ success: false, error: 'Conference not found' });
    return;
  }

  const { projectId, durationMinutes, pitchMinutes, qaMinutes } = req.body as {
    projectId?: string;
    durationMinutes?: number;
    pitchMinutes?: number;
    qaMinutes?: number;
  };

  if (!projectId) {
    res.status(400).json({ success: false, error: 'projectId is required' });
    return;
  }

  const project = store.getProject(projectId);
  if (!project) {
    res.status(404).json({ success: false, error: 'Project not found' });
    return;
  }

  if (project.status !== 'allowed' && project.status !== 'scheduled') {
    res.status(400).json({
      success: false,
      error: `Project must be in ALLOW status to be scheduled (current: ${project.status})`,
    });
    return;
  }

  const totalDuration = durationMinutes ?? 15;
  const slot: ConferenceSlot = {
    id: uuid(),
    projectId,
    order: conf.slots.length + 1,
    durationMinutes: totalDuration,
    pitchMinutes: pitchMinutes ?? Math.ceil(totalDuration * 0.65),
    qaMinutes: qaMinutes ?? Math.floor(totalDuration * 0.35),
    status: 'upcoming',
  };

  conf.slots.push(slot);
  project.status = 'scheduled';
  project.updatedAt = new Date().toISOString();
  store.setProject(project);

  res.status(201).json({ success: true, data: slot });
});

/**
 * POST /api/conferences/:id/go-live
 * Set conference status to live (curator only).
 */
router.post('/:id/go-live', requireRole('curator'), (req: Request, res: Response) => {
  const conf = store.conferences.get(req.params.id);
  if (!conf) {
    res.status(404).json({ success: false, error: 'Conference not found' });
    return;
  }

  if (conf.status !== 'scheduled') {
    res.status(400).json({ success: false, error: `Conference must be scheduled to go live (current: ${conf.status})` });
    return;
  }

  conf.status = 'live';
  const { streamUrl } = req.body as { streamUrl?: string };
  if (streamUrl) conf.streamUrl = streamUrl;

  res.json({ success: true, data: conf });
});

/**
 * POST /api/conferences/:id/end
 * End a live conference (curator only).
 */
router.post('/:id/end', requireRole('curator'), (req: Request, res: Response) => {
  const conf = store.conferences.get(req.params.id);
  if (!conf) {
    res.status(404).json({ success: false, error: 'Conference not found' });
    return;
  }

  conf.status = 'ended';
  conf.slots.forEach(slot => { slot.status = 'completed'; });

  res.json({ success: true, data: conf });
});

export default router;
