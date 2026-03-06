/**
 * @file server.ts
 * @module conference/api
 *
 * Express API server for the Vibe Coder Conference App.
 * Routes: auth, projects, NDAs, conferences, funding.
 *
 * SCBE/HYDRA governance is integrated as internal services:
 * - scoreProject() runs the 14-layer pipeline against project capsules
 * - auditProject() simulates HYDRA swarm browser crawl
 * - computeAccessLevel() derives NDA-gated access levels
 */

import express from 'express';
import cors from 'cors';
import authRoutes from './routes/auth.js';
import projectRoutes from './routes/projects.js';
import ndaRoutes from './routes/ndas.js';
import conferenceRoutes from './routes/conferences.js';
import fundingRoutes from './routes/funding.js';
import zoomRoutes from './routes/zoom.js';
import orgRoutes from './routes/orgs.js';
import { zoomService } from './services/zoom.js';
import { tenantResolver } from './middleware/tenant.js';

const app = express();
const PORT = process.env.PORT ?? 3001;

app.use(cors());
app.use(express.json());

// Tenant resolution — runs on all requests, attaches req.org if found
app.use(tenantResolver);

// Health check
app.get('/api/health', (_req, res) => {
  res.json({
    status: 'ok',
    service: 'vibe-coder-conference',
    version: '0.3.0',
    mode: 'conferences-as-a-service',
    governance: 'SCBE-AETHERMOORE 14-layer pipeline',
    swarm: 'HYDRA 6-tongue audit',
    zoom: zoomService.isConfigured() ? 'configured' : 'simulated (set ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET)',
    realtime: 'SSE event stream at /api/zoom/conferences/:id/events',
    caas: 'Multi-tenant org management at /api/orgs',
  });
});

// Routes
app.use('/api/auth', authRoutes);
app.use('/api/projects', projectRoutes);
app.use('/api/ndas', ndaRoutes);
app.use('/api/conferences', conferenceRoutes);
app.use('/api/funding', fundingRoutes);
app.use('/api/zoom', zoomRoutes);
app.use('/api/orgs', orgRoutes);

app.listen(PORT, () => {
  console.log(`[vibe-conference] API server running on http://localhost:${PORT}`);
  console.log(`[vibe-conference] SCBE governance: 14-layer pipeline active`);
  console.log(`[vibe-conference] HYDRA audit: 6-tongue swarm browser active`);
  console.log(`[vibe-conference] Zoom: ${zoomService.isConfigured() ? 'LIVE' : 'simulated (dev mode)'}`);
  console.log(`[vibe-conference] Real-time: SSE event streams enabled`);
  console.log(`[vibe-conference] CaaS: multi-tenant org management active`);
});

export default app;
