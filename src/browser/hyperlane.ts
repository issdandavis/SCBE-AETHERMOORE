/**
 * @file hyperlane.ts
 * @module browser/hyperlane
 * @layer Layer 13 (Risk Decision)
 * @component HyperLane Service Mesh Router
 *
 * Governed service mesh for the AetherBrowser.
 * All information flows through zones (GREEN/YELLOW/RED) with
 * ALLOW/DENY/QUARANTINE decisions on every request.
 *
 * Architecture:
 *   Services (rivers) -> HyperLane Router -> Basin (Dropbox/local store)
 *   AI agents request access through the user's service, not directly.
 */

import { RIVERS, type RiverPolicy } from './basin';

// ---------------------------------------------------------------------------
// Zone definitions
// ---------------------------------------------------------------------------

export type Zone = 'GREEN' | 'YELLOW' | 'RED';
export type Decision = 'ALLOW' | 'DENY' | 'QUARANTINE';

export interface ServiceConnector {
  id: string;
  name: string;
  zone: Zone;
  baseUrl: string;
  authType: 'bearer' | 'basic' | 'oauth2' | 'apikey' | 'local';
  envKey: string; // env var name for the token
  endpoints: string[]; // allowed API paths
  rateLimitPerMin: number;
  basin: 'dropbox' | 'local' | 'both'; // where data lands
  riverId?: string; // optional link to Basin access point
  accessPolicy?: Partial<ServiceAccessPolicy>;
}

export interface HyperLaneRequest {
  serviceId: string;
  action: 'read' | 'write' | 'search' | 'push' | 'pull';
  category?: string;
  path: string;
  payload?: unknown;
  agentId: string; // who is asking
  intent: number; // 0-1 intent score from governance
}

export interface HyperLaneResponse {
  decision: Decision;
  zone: Zone;
  data?: unknown;
  reason: string;
  latencyMs: number;
  depositPath?: string; // where the data was stored in the basin
  accessPointId?: string;
}

export interface ServiceAccessPolicy {
  allowedActions: Array<HyperLaneRequest['action']>;
  allowedCategories: string[]; // use ['*'] for unrestricted
  requireExplicitCategory: boolean;
  minIntent: number;
}

export interface TrajectoryPoint {
  ts: number;
  orbitKey: string;
  serviceId: string;
  action: HyperLaneRequest['action'];
  category: string;
  path: string;
  intent: number;
  decision: Decision;
}

interface AgentTrajectory {
  points: TrajectoryPoint[];
}

// ---------------------------------------------------------------------------
// Service Registry — all 17+ connected services
// ---------------------------------------------------------------------------

export const SERVICE_REGISTRY: ServiceConnector[] = [
  // === GREEN ZONE: Fully trusted, owned services ===
  {
    id: 'github',
    name: 'GitHub',
    zone: 'GREEN',
    baseUrl: 'https://api.github.com',
    authType: 'bearer',
    envKey: 'GITHUB_TOKEN',
    endpoints: ['/repos', '/gists', '/graphql', '/user'],
    rateLimitPerMin: 30,
    basin: 'both',
    riverId: 'github-api',
    accessPolicy: {
      allowedActions: ['read', 'write', 'search', 'push', 'pull'],
      allowedCategories: ['code', 'issues', 'prs', 'release', 'ops'],
      requireExplicitCategory: true,
      minIntent: 0.2,
    },
  },
  {
    id: 'github-codespaces',
    name: 'GitHub Codespaces',
    zone: 'GREEN',
    baseUrl: 'https://api.github.com',
    authType: 'bearer',
    envKey: 'GITHUB_TOKEN',
    endpoints: ['/user/codespaces', '/repos', '/graphql'],
    rateLimitPerMin: 25,
    basin: 'both',
    riverId: 'github-codespaces-api',
    accessPolicy: {
      allowedActions: ['read', 'write', 'search', 'push', 'pull'],
      allowedCategories: ['devenv', 'codespaces', 'code', 'ops'],
      requireExplicitCategory: true,
      minIntent: 0.2,
    },
  },
  {
    id: 'huggingface',
    name: 'HuggingFace',
    zone: 'GREEN',
    baseUrl: 'https://huggingface.co/api',
    authType: 'bearer',
    envKey: 'HF_TOKEN',
    endpoints: ['/repos', '/datasets', '/models', '/spaces', '/whoami-v2'],
    rateLimitPerMin: 20,
    basin: 'both',
    riverId: 'huggingface-api',
    accessPolicy: {
      allowedActions: ['read', 'write', 'search', 'push', 'pull'],
      allowedCategories: ['datasets', 'models', 'training', 'research'],
      requireExplicitCategory: true,
      minIntent: 0.2,
    },
  },
  {
    id: 'notion',
    name: 'Notion',
    zone: 'GREEN',
    baseUrl: 'https://api.notion.com/v1',
    authType: 'bearer',
    envKey: 'NOTION_TOKEN',
    endpoints: ['/pages', '/databases', '/blocks', '/search'],
    rateLimitPerMin: 30,
    basin: 'both',
  },
  {
    id: 'airtable',
    name: 'Airtable',
    zone: 'GREEN',
    baseUrl: 'https://api.airtable.com/v0',
    authType: 'bearer',
    envKey: 'AIRTABLE_TOKEN',
    endpoints: ['/meta/bases', '/${baseId}'],
    rateLimitPerMin: 30,
    basin: 'both',
  },
  {
    id: 'dropbox',
    name: 'Dropbox',
    zone: 'GREEN',
    baseUrl: 'local://C:/Users/issda/Dropbox',
    authType: 'local',
    envKey: 'DROPBOX_APP_KEY',
    endpoints: ['/**'],
    rateLimitPerMin: 999,
    basin: 'dropbox',
    riverId: 'dropbox',
    accessPolicy: {
      allowedActions: ['read', 'write', 'push', 'pull', 'search'],
      allowedCategories: ['research', 'content', 'products', 'assets', 'ops', 'archive', 'sync'],
      requireExplicitCategory: true,
      minIntent: 0.2,
    },
  },
  {
    id: 'onedrive-local',
    name: 'OneDrive (Local)',
    zone: 'GREEN',
    baseUrl: 'local://C:/Users/issda/OneDrive',
    authType: 'local',
    envKey: 'ONEDRIVE_LOCAL',
    endpoints: ['/**'],
    rateLimitPerMin: 999,
    basin: 'both',
    riverId: 'onedrive',
    accessPolicy: {
      allowedActions: ['read', 'write', 'push', 'pull', 'search'],
      allowedCategories: ['research', 'content', 'products', 'assets', 'ops', 'archive', 'sync'],
      requireExplicitCategory: true,
      minIntent: 0.2,
    },
  },
  {
    id: 'googledrive-local',
    name: 'Google Drive (Local Mount)',
    zone: 'GREEN',
    baseUrl: 'local://C:/Users/issda/Drive',
    authType: 'local',
    envKey: 'GOOGLEDRIVE_LOCAL',
    endpoints: ['/**'],
    rateLimitPerMin: 999,
    basin: 'both',
    riverId: 'googledrive',
    accessPolicy: {
      allowedActions: ['read', 'write', 'push', 'pull', 'search'],
      allowedCategories: ['research', 'content', 'products', 'assets', 'ops', 'archive', 'sync'],
      requireExplicitCategory: true,
      minIntent: 0.2,
    },
  },
  {
    id: 'dropbox-brain-local',
    name: 'Dropbox Brain (Local)',
    zone: 'GREEN',
    baseUrl: 'local://C:/Users/issda/dropbox_brain',
    authType: 'local',
    envKey: 'DROPBOX_BRAIN_LOCAL',
    endpoints: ['/**'],
    rateLimitPerMin: 999,
    basin: 'both',
    riverId: 'dropbox-brain',
    accessPolicy: {
      allowedActions: ['read', 'pull', 'search'],
      allowedCategories: ['brain', 'research', 'notes', 'archive'],
      requireExplicitCategory: true,
      minIntent: 0.2,
    },
  },
  {
    id: 'kaggle',
    name: 'Kaggle',
    zone: 'GREEN',
    baseUrl: 'https://www.kaggle.com/api/v1',
    authType: 'basic',
    envKey: 'KAGGLE_API_TOKEN',
    endpoints: ['/kernels', '/datasets', '/competitions'],
    rateLimitPerMin: 10,
    basin: 'both',
  },

  // === GREEN ZONE: Revenue services ===
  {
    id: 'stripe',
    name: 'Stripe',
    zone: 'GREEN',
    baseUrl: 'https://api.stripe.com/v1',
    authType: 'basic',
    envKey: 'STRIPE_API_KEY',
    endpoints: ['/balance', '/charges', '/customers', '/products', '/prices', '/payment_links'],
    rateLimitPerMin: 25,
    basin: 'local',
  },
  {
    id: 'shopify',
    name: 'Shopify',
    zone: 'GREEN',
    baseUrl: 'https://aethermore-works.myshopify.com/admin/api/2025-01',
    authType: 'bearer',
    envKey: 'SHOPIFY_ACCESS_TOKEN',
    endpoints: ['/products', '/orders', '/customers', '/collections'],
    rateLimitPerMin: 20,
    basin: 'local',
    accessPolicy: {
      allowedActions: ['read', 'write', 'search'],
      allowedCategories: ['products', 'orders', 'customers', 'content', 'ops'],
      requireExplicitCategory: true,
      minIntent: 0.25,
    },
  },
  {
    id: 'gumroad',
    name: 'Gumroad',
    zone: 'GREEN',
    baseUrl: 'https://api.gumroad.com/v2',
    authType: 'bearer',
    envKey: 'GUMROAD_ACCESS_TOKEN',
    endpoints: ['/products', '/sales', '/user'],
    rateLimitPerMin: 15,
    basin: 'local',
    accessPolicy: {
      allowedActions: ['read', 'write', 'search'],
      allowedCategories: ['products', 'sales', 'content', 'ops'],
      requireExplicitCategory: true,
      minIntent: 0.25,
    },
  },

  // === GREEN ZONE: Communication ===
  {
    id: 'telegram',
    name: 'Telegram',
    zone: 'GREEN',
    baseUrl: 'https://api.telegram.org',
    authType: 'apikey',
    envKey: 'TELEGRAM_BOT_TOKEN',
    endpoints: ['/sendMessage', '/getUpdates', '/getMe'],
    rateLimitPerMin: 20,
    basin: 'local',
  },
  {
    id: 'slack',
    name: 'Slack',
    zone: 'GREEN',
    baseUrl: 'https://slack.com/api',
    authType: 'bearer',
    envKey: 'SLACK_BOT_TOKEN',
    endpoints: ['/chat.postMessage', '/channels.list', '/auth.test'],
    rateLimitPerMin: 20,
    basin: 'local',
  },
  {
    id: 'discord',
    name: 'Discord',
    zone: 'GREEN',
    baseUrl: 'https://discord.com/api/v10',
    authType: 'bearer',
    envKey: 'DISCORD_BOT_TOKEN',
    endpoints: ['/users/@me', '/channels', '/guilds'],
    rateLimitPerMin: 20,
    basin: 'local',
  },

  // === GREEN ZONE: Workflow and hosting control points ===
  {
    id: 'n8n',
    name: 'n8n',
    zone: 'GREEN',
    baseUrl: 'http://127.0.0.1:5680',
    authType: 'local',
    envKey: 'N8N_WEBHOOK_URL',
    endpoints: ['/webhook', '/api'],
    rateLimitPerMin: 60,
    basin: 'both',
    riverId: 'n8n-local',
    accessPolicy: {
      allowedActions: ['read', 'write', 'search', 'push', 'pull'],
      allowedCategories: ['automation', 'posting', 'ops', 'research'],
      requireExplicitCategory: true,
      minIntent: 0.2,
    },
  },
  {
    id: 'zapier',
    name: 'Zapier Webhooks',
    zone: 'GREEN',
    baseUrl: 'https://hooks.zapier.com',
    authType: 'apikey',
    envKey: 'ZAPIER_WEBHOOK_URL',
    endpoints: ['/hooks'],
    rateLimitPerMin: 30,
    basin: 'local',
    riverId: 'zapier-webhooks',
    accessPolicy: {
      allowedActions: ['write', 'push'],
      allowedCategories: ['automation', 'posting', 'ops'],
      requireExplicitCategory: true,
      minIntent: 0.3,
    },
  },
  {
    id: 'firebase',
    name: 'Firebase Hosting',
    zone: 'GREEN',
    baseUrl: 'https://firebase.google.com',
    authType: 'oauth2',
    envKey: 'FIREBASE_PROJECT_ID',
    endpoints: ['/'],
    rateLimitPerMin: 20,
    basin: 'local',
    riverId: 'firebase-hosting',
    accessPolicy: {
      allowedActions: ['write', 'push', 'read'],
      allowedCategories: ['deploy', 'hosting', 'ops'],
      requireExplicitCategory: true,
      minIntent: 0.3,
    },
  },
  {
    id: 'gamma',
    name: 'Gamma',
    zone: 'YELLOW',
    baseUrl: 'https://gamma.app',
    authType: 'oauth2',
    envKey: 'GAMMA_TOKEN',
    endpoints: ['/'],
    rateLimitPerMin: 10,
    basin: 'local',
    riverId: 'gamma-mcp',
    accessPolicy: {
      allowedActions: ['read', 'search', 'write', 'push'],
      allowedCategories: ['slides', 'marketing', 'content', 'landing_pages', 'funnel'],
      requireExplicitCategory: true,
      minIntent: 0.5,
    },
  },

  // === YELLOW ZONE: AI providers — trusted but monitor usage ===
  {
    id: 'anthropic',
    name: 'Anthropic (Claude)',
    zone: 'YELLOW',
    baseUrl: 'https://api.anthropic.com/v1',
    authType: 'apikey',
    envKey: 'ANTHROPIC_API_KEY',
    endpoints: ['/messages', '/complete'],
    rateLimitPerMin: 10,
    basin: 'local',
  },
  {
    id: 'openai',
    name: 'OpenAI',
    zone: 'YELLOW',
    baseUrl: 'https://api.openai.com/v1',
    authType: 'bearer',
    envKey: 'OPENAI_API_KEY',
    endpoints: ['/chat/completions', '/embeddings', '/models'],
    rateLimitPerMin: 10,
    basin: 'local',
  },
  {
    id: 'gemini',
    name: 'Google Gemini',
    zone: 'YELLOW',
    baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
    authType: 'apikey',
    envKey: 'GEMINI_API_KEY',
    endpoints: ['/models'],
    rateLimitPerMin: 10,
    basin: 'local',
  },
  {
    id: 'xai',
    name: 'xAI (Grok)',
    zone: 'YELLOW',
    baseUrl: 'https://api.x.ai/v1',
    authType: 'bearer',
    envKey: 'XAI_API_KEY',
    endpoints: ['/chat/completions'],
    rateLimitPerMin: 10,
    basin: 'local',
  },

  // === YELLOW ZONE: Social publishing — monitor outbound ===
  {
    id: 'x-twitter',
    name: 'X / Twitter',
    zone: 'YELLOW',
    baseUrl: 'https://api.twitter.com/2',
    authType: 'oauth2',
    envKey: 'X_BEARER_TOKEN',
    endpoints: ['/tweets', '/users/me'],
    rateLimitPerMin: 5,
    basin: 'local',
    accessPolicy: {
      allowedActions: ['read', 'write', 'search'],
      allowedCategories: ['posting', 'content', 'analytics', 'ops'],
      requireExplicitCategory: true,
      minIntent: 0.55,
    },
  },

  // === RED ZONE: External/untrusted — max security ===
  // Add new external services here. They get QUARANTINE by default.
];

// ---------------------------------------------------------------------------
// HyperLane Router
// ---------------------------------------------------------------------------

export class HyperLaneRouter {
  private registry: Map<string, ServiceConnector>;
  private riverPolicies: Map<string, RiverPolicy>;
  private requestCounts: Map<string, { count: number; resetAt: number }> = new Map();
  private trajectories: Map<string, AgentTrajectory> = new Map();
  private basinRoot: string;
  private dropboxRoot: string;
  private trajectoryWindowMs: number;
  private trajectoryMinSamples: number;
  private trajectoryMaxIntentDrift: number;

  constructor(
    services: ServiceConnector[] = SERVICE_REGISTRY,
    basinRoot = 'C:/Users/issda/SCBE-AETHERMOORE/training/intake',
    dropboxRoot = 'C:/Users/issda/Dropbox',
    trajectoryWindowMs = 10 * 60_000,
    trajectoryMinSamples = 3,
    trajectoryMaxIntentDrift = 0.15
  ) {
    this.registry = new Map(services.map((s) => [s.id, s]));
    this.riverPolicies = new Map(
      RIVERS.filter((river) => river.policy).map((river) => [river.id, river.policy as RiverPolicy])
    );
    this.basinRoot = basinRoot;
    this.dropboxRoot = dropboxRoot;
    this.trajectoryWindowMs = trajectoryWindowMs;
    this.trajectoryMinSamples = trajectoryMinSamples;
    this.trajectoryMaxIntentDrift = trajectoryMaxIntentDrift;
  }

  private normalizeCategory(category?: string): string {
    return (category || '').trim().toLowerCase();
  }

  private orbitKey(req: HyperLaneRequest): string {
    const category = this.normalizeCategory(req.category) || 'uncategorized';
    return `${req.serviceId}:${req.action}:${category}`;
  }

  private isEndpointAllowed(service: ServiceConnector, requestPath: string): boolean {
    if (service.endpoints.includes('/**') || service.endpoints.includes('/')) {
      return true;
    }
    return service.endpoints.some((ep) => requestPath.startsWith(ep));
  }

  private recordTrajectory(req: HyperLaneRequest, decision: Decision): void {
    const now = Date.now();
    const point: TrajectoryPoint = {
      ts: now,
      orbitKey: this.orbitKey(req),
      serviceId: req.serviceId,
      action: req.action,
      category: this.normalizeCategory(req.category) || 'uncategorized',
      path: req.path,
      intent: req.intent,
      decision,
    };

    const entry = this.trajectories.get(req.agentId) || { points: [] };
    entry.points.push(point);
    entry.points = entry.points.filter((p) => now - p.ts <= this.trajectoryWindowMs);
    this.trajectories.set(req.agentId, entry);
  }

  private isPathWithinOrbit(recentOrbitPoints: TrajectoryPoint[], reqPath: string): boolean {
    if (recentOrbitPoints.length === 0) return false;
    const pathRoots = new Set(
      recentOrbitPoints.map((p) => {
        const parts = p.path.split('/').filter(Boolean);
        return `/${parts.slice(0, Math.min(2, parts.length)).join('/')}`;
      })
    );
    const reqParts = reqPath.split('/').filter(Boolean);
    const reqRoot = `/${reqParts.slice(0, Math.min(2, reqParts.length)).join('/')}`;
    return pathRoots.has(reqRoot);
  }

  private evaluateTrajectoryFastPath(
    service: ServiceConnector,
    req: HyperLaneRequest
  ): Omit<HyperLaneResponse, 'latencyMs'> | null {
    if (service.zone === 'RED') {
      return null;
    }
    const trajectory = this.trajectories.get(req.agentId);
    if (!trajectory || trajectory.points.length < this.trajectoryMinSamples) {
      return null;
    }

    const now = Date.now();
    const windowed = trajectory.points.filter((p) => now - p.ts <= this.trajectoryWindowMs);
    const orbit = this.orbitKey(req);
    const sameOrbit = windowed.filter((p) => p.orbitKey === orbit);
    if (sameOrbit.length < this.trajectoryMinSamples) {
      return null;
    }

    // Unitarity: intent must remain within a bounded drift envelope.
    const avgIntent = sameOrbit.reduce((sum, p) => sum + p.intent, 0) / sameOrbit.length;
    const drift = Math.abs(req.intent - avgIntent);
    if (drift > this.trajectoryMaxIntentDrift) {
      return null;
    }

    // Locality/causality/composition guardrails from recent trajectory.
    if (!this.isPathWithinOrbit(sameOrbit, req.path)) {
      return null;
    }
    if (sameOrbit.some((p) => p.decision === 'DENY' || p.decision === 'QUARANTINE')) {
      return null;
    }

    return {
      decision: 'ALLOW',
      zone: service.zone,
      reason: `Trajectory pre-authorized (orbit stable; drift ${drift.toFixed(3)})`,
      depositPath: this.resolveBasinPath(service, req),
    };
  }

  private resolveAccessPolicy(service: ServiceConnector): ServiceAccessPolicy {
    const zoneDefaults: Record<Zone, ServiceAccessPolicy> = {
      GREEN: {
        allowedActions: ['read', 'write', 'search', 'push', 'pull'],
        allowedCategories: ['*'],
        requireExplicitCategory: false,
        minIntent: 0.2,
      },
      YELLOW: {
        allowedActions: ['read', 'write', 'search', 'push', 'pull'],
        allowedCategories: ['*'],
        requireExplicitCategory: false,
        minIntent: 0.5,
      },
      RED: {
        allowedActions: ['read', 'search'],
        allowedCategories: ['*'],
        requireExplicitCategory: false,
        minIntent: 0.9,
      },
    };

    const basePolicy = zoneDefaults[service.zone];
    const riverPolicy = service.riverId ? this.riverPolicies.get(service.riverId) : undefined;
    const merged: ServiceAccessPolicy = {
      allowedActions: basePolicy.allowedActions,
      allowedCategories: basePolicy.allowedCategories,
      requireExplicitCategory: basePolicy.requireExplicitCategory,
      minIntent: basePolicy.minIntent,
      ...service.accessPolicy,
    };

    if (riverPolicy) {
      const riverAllowedActions: Array<HyperLaneRequest['action']> = [];
      if (riverPolicy.readFromRiver) {
        riverAllowedActions.push('read', 'search', 'pull');
      }
      if (riverPolicy.writeToRiver) {
        riverAllowedActions.push('write', 'push');
      }

      if (riverAllowedActions.length > 0) {
        merged.allowedActions = merged.allowedActions.filter((action) =>
          riverAllowedActions.includes(action)
        );
      }
      if (
        riverPolicy.allowedCategories.length > 0 &&
        !riverPolicy.allowedCategories.includes('*')
      ) {
        const riverCategories = riverPolicy.allowedCategories.map((c) => c.toLowerCase());
        if (merged.allowedCategories.includes('*')) {
          merged.allowedCategories = riverPolicy.allowedCategories;
        } else {
          merged.allowedCategories = merged.allowedCategories.filter((c) =>
            riverCategories.includes(c.toLowerCase())
          );
        }
      }
      if (riverPolicy.requireExplicitCategory) {
        merged.requireExplicitCategory = true;
      }
    }

    return merged;
  }

  private checkAccessPolicy(
    service: ServiceConnector,
    req: HyperLaneRequest
  ): Omit<HyperLaneResponse, 'latencyMs'> | null {
    const policy = this.resolveAccessPolicy(service);
    const category = this.normalizeCategory(req.category);

    if (!this.isEndpointAllowed(service, req.path)) {
      return {
        decision: 'DENY',
        zone: service.zone,
        reason: `Path '${req.path}' is not allowed for ${service.name}`,
      };
    }

    if (!policy.allowedActions.includes(req.action)) {
      return {
        decision: 'DENY',
        zone: service.zone,
        reason: `Action '${req.action}' is not allowed for ${service.name}`,
      };
    }

    if (req.intent < policy.minIntent) {
      return {
        decision: 'QUARANTINE',
        zone: service.zone,
        reason: `Intent ${req.intent} below policy minimum ${policy.minIntent} for ${service.name}`,
      };
    }

    if (policy.requireExplicitCategory && category.length === 0) {
      return {
        decision: 'DENY',
        zone: service.zone,
        reason: `Category is required for ${service.name}`,
      };
    }

    if (!policy.allowedCategories.includes('*')) {
      const categories = policy.allowedCategories.map((c) => c.toLowerCase());
      if (category.length > 0 && !categories.includes(category)) {
        return {
          decision: 'DENY',
          zone: service.zone,
          reason: `Category '${req.category}' is not allowed for ${service.name}`,
        };
      }
    }

    return null;
  }

  /**
   * Route a request through governance and return a decision.
   */
  route(req: HyperLaneRequest): HyperLaneResponse {
    const start = Date.now();
    const service = this.registry.get(req.serviceId);

    // Unknown service -> DENY
    if (!service) {
      return {
        decision: 'DENY',
        zone: 'RED',
        reason: `Unknown service: ${req.serviceId}`,
        latencyMs: Date.now() - start,
      };
    }

    const accessDecision = this.checkAccessPolicy(service, req);
    if (accessDecision) {
      this.recordTrajectory(req, accessDecision.decision);
      return {
        ...accessDecision,
        latencyMs: Date.now() - start,
        accessPointId: service.riverId,
      };
    }

    // Rate limit check
    if (this.isRateLimited(service)) {
      this.recordTrajectory(req, 'QUARANTINE');
      return {
        decision: 'QUARANTINE',
        zone: service.zone,
        reason: `Rate limited: ${service.name} (${service.rateLimitPerMin}/min)`,
        latencyMs: Date.now() - start,
        accessPointId: service.riverId,
      };
    }

    const trajectoryDecision = this.evaluateTrajectoryFastPath(service, req);
    if (trajectoryDecision) {
      this.incrementCount(service.id);
      this.recordTrajectory(req, trajectoryDecision.decision);
      return {
        ...trajectoryDecision,
        latencyMs: Date.now() - start,
        accessPointId: service.riverId,
      };
    }

    // Zone-based governance
    const decision = this.evaluateZone(service, req);

    this.incrementCount(service.id);
    this.recordTrajectory(req, decision.decision);

    return {
      ...decision,
      latencyMs: Date.now() - start,
      accessPointId: service.riverId,
    };
  }

  /**
   * Zone-based decision logic.
   * GREEN: ALLOW unless intent < 0.2 (suspicious)
   * YELLOW: ALLOW if intent > 0.5, QUARANTINE otherwise
   * RED: DENY unless intent > 0.9 AND action is read-only
   */
  private evaluateZone(
    service: ServiceConnector,
    req: HyperLaneRequest
  ): Omit<HyperLaneResponse, 'latencyMs'> {
    const { zone } = service;
    const { intent, action } = req;

    if (zone === 'GREEN') {
      if (intent < 0.2) {
        return {
          decision: 'QUARANTINE',
          zone,
          reason: `Low intent score (${intent}) on GREEN service ${service.name}`,
        };
      }
      return {
        decision: 'ALLOW',
        zone,
        reason: `GREEN zone: ${service.name} — ${action}`,
        depositPath: this.resolveBasinPath(service, req),
      };
    }

    if (zone === 'YELLOW') {
      if (intent < 0.5) {
        return {
          decision: 'QUARANTINE',
          zone,
          reason: `Intent ${intent} below threshold for YELLOW service ${service.name}`,
        };
      }
      return {
        decision: 'ALLOW',
        zone,
        reason: `YELLOW zone: ${service.name} — ${action} (intent: ${intent})`,
        depositPath: this.resolveBasinPath(service, req),
      };
    }

    // RED zone
    if (intent > 0.9 && action === 'read') {
      return {
        decision: 'QUARANTINE',
        zone,
        reason: `RED zone read allowed under max security: ${service.name}`,
        depositPath: this.resolveBasinPath(service, req),
      };
    }

    return {
      decision: 'DENY',
      zone,
      reason: `RED zone DENY: ${service.name} — ${action} (intent: ${intent})`,
    };
  }

  /**
   * Resolve where data lands in the basin.
   */
  private resolveBasinPath(service: ServiceConnector, req: HyperLaneRequest): string {
    const category = this.normalizeCategory(req.category) || 'uncategorized';
    if (service.basin === 'dropbox') {
      return `${this.dropboxRoot}/SCBE/${service.id}/${category}/${req.action}`;
    }
    if (service.basin === 'both') {
      return `${this.basinRoot}/${service.id}/${category}/${req.action}`;
    }
    return `${this.basinRoot}/${service.id}/${category}/${req.action}`;
  }

  /**
   * Check rate limits.
   */
  private isRateLimited(service: ServiceConnector): boolean {
    const now = Date.now();
    const entry = this.requestCounts.get(service.id);
    if (!entry || now > entry.resetAt) {
      return false;
    }
    return entry.count >= service.rateLimitPerMin;
  }

  private incrementCount(serviceId: string): void {
    const now = Date.now();
    const entry = this.requestCounts.get(serviceId);
    if (!entry || now > entry.resetAt) {
      this.requestCounts.set(serviceId, { count: 1, resetAt: now + 60_000 });
    } else {
      entry.count++;
    }
  }

  /**
   * List all services and their zones.
   */
  listServices(): Array<{
    id: string;
    name: string;
    zone: Zone;
    basin: string;
    accessPointId?: string;
    allowedActions: Array<HyperLaneRequest['action']>;
    allowedCategories: string[];
    minIntent: number;
  }> {
    return Array.from(this.registry.values()).map((s) => {
      const policy = this.resolveAccessPolicy(s);
      return {
        id: s.id,
        name: s.name,
        zone: s.zone,
        basin: s.basin,
        accessPointId: s.riverId,
        allowedActions: policy.allowedActions,
        allowedCategories: policy.allowedCategories,
        minIntent: policy.minIntent,
      };
    });
  }

  getTrajectory(agentId: string): TrajectoryPoint[] {
    return [...(this.trajectories.get(agentId)?.points || [])];
  }

  /**
   * Get a service by ID.
   */
  getService(id: string): ServiceConnector | undefined {
    return this.registry.get(id);
  }

  /**
   * Add a new service dynamically.
   */
  addService(service: ServiceConnector): void {
    this.registry.set(service.id, service);
  }

  /**
   * Move a service between zones (e.g., promote from YELLOW to GREEN).
   */
  setZone(serviceId: string, zone: Zone): boolean {
    const service = this.registry.get(serviceId);
    if (!service) return false;
    service.zone = zone;
    return true;
  }
}
