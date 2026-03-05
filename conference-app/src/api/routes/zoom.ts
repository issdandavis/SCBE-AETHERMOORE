/**
 * @file zoom.ts
 * @module conference/api/routes
 *
 * Zoom meeting management and live event streaming routes.
 *
 * - Curators create Zoom meetings for conferences
 * - Investors get NDA-gated join links
 * - SSE endpoint streams real-time events (soft-commits, slot changes, reactions)
 */

import { Router, type Request, type Response } from 'express';
import { store } from '../store.js';
import { authMiddleware, requireRole } from '../middleware/auth.js';
import { zoomService } from '../services/zoom.js';
import { liveEventBus } from '../services/liveEvents.js';

const router = Router();

router.use(authMiddleware);

/**
 * POST /api/zoom/conferences/:id/meeting
 * Create a Zoom meeting for a conference (curator only).
 *
 * Body: { hostEmail: string }
 */
router.post('/conferences/:id/meeting', requireRole('curator'), async (req: Request, res: Response) => {
  const conf = store.conferences.get(req.params.id);
  if (!conf) {
    res.status(404).json({ success: false, error: 'Conference not found' });
    return;
  }

  const { hostEmail } = req.body as { hostEmail?: string };
  const email = hostEmail ?? req.user!.email;

  try {
    const meeting = await zoomService.createMeeting(
      conf.id,
      `vibe::conference — ${conf.title}`,
      conf.scheduledAt,
      conf.duration,
      email
    );

    // Store the Zoom join URL as the conference stream URL
    conf.streamUrl = meeting.joinUrl;

    res.status(201).json({
      success: true,
      data: {
        meetingId: meeting.id,
        joinUrl: meeting.joinUrl,
        startUrl: meeting.startUrl,
        password: meeting.password,
        configured: zoomService.isConfigured(),
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    res.status(500).json({ success: false, error: `Zoom error: ${message}` });
  }
});

/**
 * GET /api/zoom/conferences/:id/join
 * Get the Zoom join link for a conference.
 * NDA-gated for investors. Curators get the start URL.
 */
router.get('/conferences/:id/join', (req: Request, res: Response) => {
  const user = req.user!;
  const confId = req.params.id;

  const conf = store.conferences.get(confId);
  if (!conf) {
    res.status(404).json({ success: false, error: 'Conference not found' });
    return;
  }

  // Investors must have signed platform NDA
  if (user.role === 'investor') {
    const hasPlatformNda = store.hasSignedNda(user.id, null);
    if (!hasPlatformNda) {
      res.status(403).json({
        success: false,
        error: 'You must sign the platform NDA before joining a live conference',
        ndaRequired: true,
      });
      return;
    }
  }

  const meeting = zoomService.getMeeting(confId);
  if (!meeting) {
    res.status(404).json({ success: false, error: 'No Zoom meeting created for this conference yet' });
    return;
  }

  // Curators get start URL (host), everyone else gets join URL
  if (user.role === 'curator') {
    res.json({
      success: true,
      data: {
        url: meeting.startUrl,
        role: 'host',
        meetingId: meeting.id,
        password: meeting.password,
      },
    });
  } else {
    res.json({
      success: true,
      data: {
        url: meeting.joinUrl,
        role: 'attendee',
        meetingId: meeting.id,
      },
    });
  }
});

/**
 * GET /api/zoom/conferences/:id/events
 * Server-Sent Events stream for real-time conference events.
 *
 * Clients connect here to receive:
 * - commit:new — when an investor soft-commits
 * - commit:ticker — aggregated ticker updates
 * - slot:start / slot:end — presentation transitions
 * - chat:message — live chat
 * - reaction — emoji reactions
 * - governance:alert — mid-stream governance flags
 * - phase:update — HYDRA agent phase visualization
 */
router.get('/conferences/:id/events', (req: Request, res: Response) => {
  const confId = req.params.id;

  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no',
  });

  // Send recent events as catch-up
  const recent = liveEventBus.getRecent(confId);
  for (const event of recent) {
    res.write(`event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`);
  }

  // Subscribe to new events
  const unsubscribe = liveEventBus.subscribe(confId, (event) => {
    res.write(`event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`);
  });

  // Send heartbeat every 15s to keep connection alive
  const heartbeat = setInterval(() => {
    res.write(': heartbeat\n\n');
  }, 15_000);

  // Emit viewer count on connect
  const viewers = liveEventBus.subscriberCount(confId);
  res.write(`event: viewers\ndata: ${JSON.stringify({ count: viewers })}\n\n`);

  req.on('close', () => {
    unsubscribe();
    clearInterval(heartbeat);
  });
});

/**
 * POST /api/zoom/conferences/:id/chat
 * Send a chat message to the conference live feed.
 */
router.post('/conferences/:id/chat', (req: Request, res: Response) => {
  const { message } = req.body as { message?: string };
  if (!message || message.trim().length === 0) {
    res.status(400).json({ success: false, error: 'message is required' });
    return;
  }

  // Sanitize: strip anything that looks like a URL (basic anti-phishing during live)
  const sanitized = message.slice(0, 500);

  liveEventBus.emitChat(
    req.params.id,
    req.user!.id,
    req.user!.displayName,
    sanitized
  );

  res.json({ success: true });
});

/**
 * POST /api/zoom/conferences/:id/reaction
 * Send an emoji reaction to the conference live feed.
 */
router.post('/conferences/:id/reaction', (req: Request, res: Response) => {
  const { emoji } = req.body as { emoji?: string };
  const allowed = ['fire', 'rocket', 'money', 'clap', 'think', 'heart'];
  if (!emoji || !allowed.includes(emoji)) {
    res.status(400).json({ success: false, error: `emoji must be one of: ${allowed.join(', ')}` });
    return;
  }

  liveEventBus.emitReaction(req.params.id, req.user!.id, emoji);
  res.json({ success: true });
});

export default router;
