/**
 * @file tenant.ts
 * @module conference/api/services
 *
 * Multi-tenant organization service for Conferences-as-a-Service (CaaS).
 *
 * Each organization gets:
 * - Isolated data (conferences, projects, NDAs scoped to org)
 * - Customizable governance thresholds (coherence, HYDRA quorum, etc.)
 * - White-label branding (colors, logo, tagline, custom domain)
 * - API key for programmatic conference management
 * - Plan-based limits (starter / growth / enterprise)
 *
 * Tenant resolution: slug-based (e.g., /org/acme/conferences)
 * or API key header (x-org-api-key) for programmatic access.
 */

import { randomUUID, randomBytes } from 'crypto';

const uuid = randomUUID;
import type {
  Organization,
  OrgBranding,
  GovernanceConfig,
  OrgMember,
  OrgUsage,
  CaasPlan,
  PlanLimits,
} from '../../shared/types/index.js';

// ═══════════════════════════════════════════════════════════════
// Plan Definitions
// ═══════════════════════════════════════════════════════════════

export const PLAN_LIMITS: Record<CaasPlan, PlanLimits> = {
  starter: {
    maxConferencesPerMonth: 2,
    maxProjectsPerConference: 10,
    maxApiKeys: 1,
    customBranding: false,
    customDomain: false,
    customNda: false,
    sseRealtime: true,
    zoomIntegration: true,
    hydraAudit: false,
    dedicatedSupport: false,
  },
  growth: {
    maxConferencesPerMonth: 10,
    maxProjectsPerConference: 50,
    maxApiKeys: 5,
    customBranding: true,
    customDomain: false,
    customNda: true,
    sseRealtime: true,
    zoomIntegration: true,
    hydraAudit: true,
    dedicatedSupport: false,
  },
  enterprise: {
    maxConferencesPerMonth: -1, // unlimited
    maxProjectsPerConference: -1,
    maxApiKeys: -1,
    customBranding: true,
    customDomain: true,
    customNda: true,
    sseRealtime: true,
    zoomIntegration: true,
    hydraAudit: true,
    dedicatedSupport: true,
  },
};

// ═══════════════════════════════════════════════════════════════
// Default Governance Config
// ═══════════════════════════════════════════════════════════════

export const DEFAULT_GOVERNANCE_CONFIG: GovernanceConfig = {
  coherenceThreshold: 0.6,
  maxHyperbolicDistance: 2.5,
  hydraQuorum: 4,
  requireHydraAudit: true,
  ndaTemplate: null,
  allowedDecisions: ['ALLOW'],
};

// ═══════════════════════════════════════════════════════════════
// Tenant Service
// ═══════════════════════════════════════════════════════════════

export class TenantService {
  /** orgId -> Organization */
  private orgs: Map<string, Organization> = new Map();
  /** slug -> orgId */
  private slugIndex: Map<string, string> = new Map();
  /** apiKey -> orgId */
  private apiKeyIndex: Map<string, string> = new Map();
  /** orgId -> OrgMember[] */
  private members: Map<string, OrgMember[]> = new Map();

  /**
   * Create a new organization.
   */
  createOrg(
    name: string,
    slug: string,
    ownerId: string,
    plan: CaasPlan = 'starter'
  ): Organization | { error: string } {
    // Validate slug
    if (!/^[a-z0-9-]{3,40}$/.test(slug)) {
      return { error: 'Slug must be 3-40 characters, lowercase alphanumeric and hyphens only' };
    }
    if (this.slugIndex.has(slug)) {
      return { error: `Slug "${slug}" is already taken` };
    }

    const apiKey = `caas_${randomBytes(24).toString('hex')}`;

    const org: Organization = {
      id: uuid(),
      name,
      slug,
      ownerId,
      plan,
      branding: {
        displayName: name,
        primaryColor: '#00d4ff',
      },
      governanceConfig: { ...DEFAULT_GOVERNANCE_CONFIG },
      apiKey,
      usage: {
        conferencesCreated: 0,
        projectsSubmitted: 0,
        totalSoftCommits: 0,
        totalFundingVolume: 0,
      },
      createdAt: new Date().toISOString(),
    };

    this.orgs.set(org.id, org);
    this.slugIndex.set(slug, org.id);
    this.apiKeyIndex.set(apiKey, org.id);

    // Add owner as member
    const member: OrgMember = {
      id: uuid(),
      orgId: org.id,
      userId: ownerId,
      role: 'owner',
      addedAt: new Date().toISOString(),
    };
    this.members.set(org.id, [member]);

    return org;
  }

  /**
   * Resolve an organization by slug.
   */
  getBySlug(slug: string): Organization | undefined {
    const id = this.slugIndex.get(slug);
    return id ? this.orgs.get(id) : undefined;
  }

  /**
   * Resolve an organization by API key.
   */
  getByApiKey(apiKey: string): Organization | undefined {
    const id = this.apiKeyIndex.get(apiKey);
    return id ? this.orgs.get(id) : undefined;
  }

  /**
   * Get an organization by ID.
   */
  getById(id: string): Organization | undefined {
    return this.orgs.get(id);
  }

  /**
   * List all organizations (admin view).
   */
  listOrgs(): Organization[] {
    return Array.from(this.orgs.values());
  }

  /**
   * List organizations owned by a user.
   */
  listByOwner(ownerId: string): Organization[] {
    return Array.from(this.orgs.values()).filter(o => o.ownerId === ownerId);
  }

  /**
   * Update organization branding.
   */
  updateBranding(orgId: string, branding: Partial<OrgBranding>): Organization | undefined {
    const org = this.orgs.get(orgId);
    if (!org) return undefined;

    const limits = PLAN_LIMITS[org.plan];
    if (branding.customDomain && !limits.customDomain) {
      return undefined;
    }

    org.branding = { ...org.branding, ...branding };
    return org;
  }

  /**
   * Update governance configuration.
   */
  updateGovernanceConfig(orgId: string, config: Partial<GovernanceConfig>): Organization | undefined {
    const org = this.orgs.get(orgId);
    if (!org) return undefined;

    // Validate thresholds
    if (config.coherenceThreshold !== undefined) {
      config.coherenceThreshold = Math.max(0, Math.min(1, config.coherenceThreshold));
    }
    if (config.hydraQuorum !== undefined) {
      config.hydraQuorum = Math.max(1, Math.min(6, config.hydraQuorum));
    }

    const limits = PLAN_LIMITS[org.plan];
    if (config.ndaTemplate !== undefined && config.ndaTemplate !== null && !limits.customNda) {
      return undefined;
    }

    org.governanceConfig = { ...org.governanceConfig, ...config };
    return org;
  }

  /**
   * Rotate API key for an organization.
   */
  rotateApiKey(orgId: string): string | undefined {
    const org = this.orgs.get(orgId);
    if (!org) return undefined;

    // Remove old key from index
    this.apiKeyIndex.delete(org.apiKey);

    // Generate new key
    const newKey = `caas_${randomBytes(24).toString('hex')}`;
    org.apiKey = newKey;
    this.apiKeyIndex.set(newKey, orgId);

    return newKey;
  }

  /**
   * Get plan limits for an organization.
   */
  getPlanLimits(orgId: string): PlanLimits | undefined {
    const org = this.orgs.get(orgId);
    return org ? PLAN_LIMITS[org.plan] : undefined;
  }

  /**
   * Check if an organization can create another conference this month.
   */
  canCreateConference(orgId: string): boolean {
    const org = this.orgs.get(orgId);
    if (!org) return false;
    const limits = PLAN_LIMITS[org.plan];
    if (limits.maxConferencesPerMonth === -1) return true;
    return org.usage.conferencesCreated < limits.maxConferencesPerMonth;
  }

  /**
   * Increment usage counter.
   */
  incrementUsage(orgId: string, field: keyof OrgUsage, amount: number = 1): void {
    const org = this.orgs.get(orgId);
    if (org) {
      org.usage[field] += amount;
    }
  }

  /**
   * Get members for an organization.
   */
  getMembers(orgId: string): OrgMember[] {
    return this.members.get(orgId) ?? [];
  }

  /**
   * Add a member to an organization.
   */
  addMember(orgId: string, userId: string, role: OrgMember['role'] = 'viewer'): OrgMember | undefined {
    const org = this.orgs.get(orgId);
    if (!org) return undefined;

    const existing = this.members.get(orgId) ?? [];
    if (existing.some(m => m.userId === userId)) return undefined;

    const member: OrgMember = {
      id: uuid(),
      orgId,
      userId,
      role,
      addedAt: new Date().toISOString(),
    };

    existing.push(member);
    this.members.set(orgId, existing);
    return member;
  }

  /**
   * Check if a user has a specific role (or higher) in an org.
   */
  hasRole(orgId: string, userId: string, minRole: OrgMember['role']): boolean {
    const members = this.members.get(orgId) ?? [];
    const member = members.find(m => m.userId === userId);
    if (!member) return false;

    const hierarchy: OrgMember['role'][] = ['viewer', 'curator', 'admin', 'owner'];
    return hierarchy.indexOf(member.role) >= hierarchy.indexOf(minRole);
  }
}

/** Singleton tenant service */
export const tenantService = new TenantService();
