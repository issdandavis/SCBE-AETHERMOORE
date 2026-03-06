/**
 * @file projects.ts
 * @module conference/api/routes
 *
 * Project submission and management routes.
 * Projects flow through: draft → submitted → scoring → allowed/quarantined/denied → scheduled → presented → funded
 */

import { Router, type Request, type Response } from 'express';
import { v4 as uuid } from 'uuid';
import { store } from '../store.js';
import { authMiddleware, requireRole } from '../middleware/auth.js';
import { scoreProject, auditProject } from '../../shared/governance/scbeGate.js';
import type { ProjectCapsule, FundingAsk, ApiResponse } from '../../shared/types/index.js';

const router = Router();

/** Express v5 params may be string | string[]; extract safely */
function param(req: Request, name: string): string {
  const v = req.params[name];
  return Array.isArray(v) ? v[0] : v;
}

router.use(authMiddleware);

/**
 * POST /api/projects
 * Create a new project capsule (coder only).
 */
router.post('/', requireRole('coder'), (req: Request, res: Response) => {
  const { title, tagline, description, techStack, repoUrl, demoUrl, videoUrl, pitchDeckUrl, fundingAsk } = req.body as {
    title?: string;
    tagline?: string;
    description?: string;
    techStack?: string[];
    repoUrl?: string;
    demoUrl?: string;
    videoUrl?: string;
    pitchDeckUrl?: string;
    fundingAsk?: FundingAsk;
  };

  if (!title || !tagline || !description || !techStack || !fundingAsk) {
    res.status(400).json({ success: false, error: 'title, tagline, description, techStack, and fundingAsk are required' });
    return;
  }

  const project: ProjectCapsule = {
    id: uuid(),
    scbeId: `scbe-${uuid().slice(0, 8)}`,
    creatorId: req.user!.id,
    title,
    tagline,
    description,
    techStack,
    repoUrl,
    demoUrl,
    videoUrl,
    pitchDeckUrl,
    fundingAsk,
    status: 'draft',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  store.setProject(project);
  res.status(201).json({ success: true, data: project } as ApiResponse<ProjectCapsule>);
});

/**
 * GET /api/projects
 * List projects. Coders see their own; investors see allowed; curators see all.
 */
router.get('/', (req: Request, res: Response) => {
  const user = req.user!;
  let projects: ProjectCapsule[];

  if (user.role === 'coder') {
    projects = store.listProjects({ creatorId: user.id });
  } else if (user.role === 'investor') {
    projects = store.listProjects().filter(
      p => p.status === 'allowed' || p.status === 'scheduled' || p.status === 'presented' || p.status === 'funded'
    );
  } else {
    projects = store.listProjects();
  }

  res.json({ success: true, data: projects, meta: { total: projects.length } });
});

/**
 * GET /api/projects/:id
 */
router.get('/:id', (req: Request, res: Response) => {
  const project = store.getProject(param(req, 'id'));
  if (!project) {
    res.status(404).json({ success: false, error: 'Project not found' });
    return;
  }
  res.json({ success: true, data: project });
});

/**
 * POST /api/projects/:id/submit
 * Submit project for SCBE/HYDRA governance scoring.
 */
router.post('/:id/submit', requireRole('coder'), (req: Request, res: Response) => {
  const project = store.getProject(param(req, 'id'));
  if (!project) {
    res.status(404).json({ success: false, error: 'Project not found' });
    return;
  }
  if (project.creatorId !== req.user!.id) {
    res.status(403).json({ success: false, error: 'Not your project' });
    return;
  }
  if (project.status !== 'draft') {
    res.status(400).json({ success: false, error: 'Project already submitted' });
    return;
  }

  // Run SCBE governance pipeline
  project.status = 'scoring';
  project.submittedAt = new Date().toISOString();

  const governance = scoreProject(project);
  const hydraAudit = auditProject(project);

  project.governance = governance;
  project.hydraAudit = hydraAudit;

  // Map governance decision to project status
  switch (governance.decision) {
    case 'ALLOW':
      project.status = 'allowed';
      break;
    case 'QUARANTINE':
    case 'ESCALATE':
      project.status = 'quarantined';
      break;
    case 'DENY':
      project.status = 'denied';
      break;
  }

  project.updatedAt = new Date().toISOString();
  store.setProject(project);

  res.json({
    success: true,
    data: {
      project,
      governance,
      hydraAudit,
    },
  });
});

/**
 * GET /api/projects/:id/governance
 * Get detailed governance scores and HYDRA audit for a project.
 */
router.get('/:id/governance', (req: Request, res: Response) => {
  const project = store.getProject(param(req, 'id'));
  if (!project) {
    res.status(404).json({ success: false, error: 'Project not found' });
    return;
  }

  if (!project.governance) {
    res.status(400).json({ success: false, error: 'Project has not been scored yet' });
    return;
  }

  res.json({
    success: true,
    data: {
      governance: project.governance,
      hydraAudit: project.hydraAudit,
    },
  });
});

export default router;
