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

const app = express();
const PORT = process.env.PORT ?? 3001;

app.use(cors());
app.use(express.json());

// Health check
app.get('/api/health', (_req, res) => {
  res.json({
    status: 'ok',
    service: 'vibe-coder-conference',
    version: '0.1.0',
    governance: 'SCBE-AETHERMOORE 14-layer pipeline',
    swarm: 'HYDRA 6-tongue audit',
  });
});

// Routes
app.use('/api/auth', authRoutes);
app.use('/api/projects', projectRoutes);
app.use('/api/ndas', ndaRoutes);
app.use('/api/conferences', conferenceRoutes);
app.use('/api/funding', fundingRoutes);

app.listen(PORT, () => {
  console.log(`[vibe-conference] API server running on http://localhost:${PORT}`);
  console.log(`[vibe-conference] SCBE governance: 14-layer pipeline active`);
  console.log(`[vibe-conference] HYDRA audit: 6-tongue swarm browser active`);
});

export default app;
