/**
 * @file caas.test.ts
 * @module tests/conference
 *
 * Tests for Conferences-as-a-Service: tenant service, plan limits,
 * governance config, and multi-tenant isolation.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  TenantService,
  PLAN_LIMITS,
  DEFAULT_GOVERNANCE_CONFIG,
} from '../../conference-app/src/api/services/tenant';

describe('TenantService', () => {
  let service: TenantService;

  beforeEach(() => {
    service = new TenantService();
  });

  describe('createOrg', () => {
    it('creates an organization with default settings', () => {
      const result = service.createOrg('Acme Accelerator', 'acme', 'user-1');

      expect('error' in result).toBe(false);
      if ('error' in result) return;

      expect(result.name).toBe('Acme Accelerator');
      expect(result.slug).toBe('acme');
      expect(result.ownerId).toBe('user-1');
      expect(result.plan).toBe('starter');
      expect(result.apiKey).toMatch(/^caas_/);
      expect(result.branding.displayName).toBe('Acme Accelerator');
      expect(result.branding.primaryColor).toBe('#00d4ff');
      expect(result.governanceConfig).toEqual(DEFAULT_GOVERNANCE_CONFIG);
      expect(result.usage.conferencesCreated).toBe(0);
    });

    it('rejects invalid slugs', () => {
      const result = service.createOrg('Test', 'AB', 'user-1');
      expect('error' in result).toBe(true);

      const result2 = service.createOrg('Test', 'Has Spaces', 'user-1');
      expect('error' in result2).toBe(true);
    });

    it('rejects duplicate slugs', () => {
      service.createOrg('First', 'same-slug', 'user-1');
      const result = service.createOrg('Second', 'same-slug', 'user-2');
      expect('error' in result).toBe(true);
      if ('error' in result) {
        expect(result.error).toContain('already taken');
      }
    });

    it('creates with specified plan', () => {
      const result = service.createOrg('Big Corp', 'bigcorp', 'user-1', 'enterprise');
      expect('error' in result).toBe(false);
      if (!('error' in result)) {
        expect(result.plan).toBe('enterprise');
      }
    });
  });

  describe('resolution', () => {
    it('resolves by slug', () => {
      const created = service.createOrg('Test', 'test-org', 'user-1');
      if ('error' in created) throw new Error('unexpected');

      const found = service.getBySlug('test-org');
      expect(found?.id).toBe(created.id);
    });

    it('resolves by API key', () => {
      const created = service.createOrg('Test', 'test-api', 'user-1');
      if ('error' in created) throw new Error('unexpected');

      const found = service.getByApiKey(created.apiKey);
      expect(found?.id).toBe(created.id);
    });

    it('resolves by ID', () => {
      const created = service.createOrg('Test', 'test-id', 'user-1');
      if ('error' in created) throw new Error('unexpected');

      const found = service.getById(created.id);
      expect(found?.id).toBe(created.id);
    });

    it('returns undefined for non-existent slug', () => {
      expect(service.getBySlug('nope')).toBeUndefined();
    });
  });

  describe('branding', () => {
    it('updates branding fields', () => {
      const created = service.createOrg('Test', 'brand-test', 'user-1');
      if ('error' in created) throw new Error('unexpected');

      const updated = service.updateBranding(created.id, {
        primaryColor: '#ff0000',
        tagline: 'Best demos ever',
      });

      expect(updated?.branding.primaryColor).toBe('#ff0000');
      expect(updated?.branding.tagline).toBe('Best demos ever');
      expect(updated?.branding.displayName).toBe('Test'); // unchanged
    });

    it('rejects custom domain on starter plan', () => {
      const created = service.createOrg('Test', 'domain-test', 'user-1', 'starter');
      if ('error' in created) throw new Error('unexpected');

      const result = service.updateBranding(created.id, { customDomain: 'demo.example.com' });
      expect(result).toBeUndefined();
    });

    it('allows custom domain on enterprise plan', () => {
      const created = service.createOrg('Test', 'ent-domain', 'user-1', 'enterprise');
      if ('error' in created) throw new Error('unexpected');

      const result = service.updateBranding(created.id, { customDomain: 'demo.example.com' });
      expect(result?.branding.customDomain).toBe('demo.example.com');
    });
  });

  describe('governance config', () => {
    it('updates governance thresholds', () => {
      const created = service.createOrg('Test', 'gov-test', 'user-1');
      if ('error' in created) throw new Error('unexpected');

      const updated = service.updateGovernanceConfig(created.id, {
        coherenceThreshold: 0.8,
        hydraQuorum: 5,
      });

      expect(updated?.governanceConfig.coherenceThreshold).toBe(0.8);
      expect(updated?.governanceConfig.hydraQuorum).toBe(5);
    });

    it('clamps coherence to [0, 1]', () => {
      const created = service.createOrg('Test', 'clamp-test', 'user-1');
      if ('error' in created) throw new Error('unexpected');

      service.updateGovernanceConfig(created.id, { coherenceThreshold: 1.5 });
      const org = service.getById(created.id);
      expect(org?.governanceConfig.coherenceThreshold).toBe(1);
    });

    it('clamps hydra quorum to [1, 6]', () => {
      const created = service.createOrg('Test', 'quorum-clamp', 'user-1');
      if ('error' in created) throw new Error('unexpected');

      service.updateGovernanceConfig(created.id, { hydraQuorum: 10 });
      const org = service.getById(created.id);
      expect(org?.governanceConfig.hydraQuorum).toBe(6);
    });

    it('rejects custom NDA on starter plan', () => {
      const created = service.createOrg('Test', 'nda-starter', 'user-1', 'starter');
      if ('error' in created) throw new Error('unexpected');

      const result = service.updateGovernanceConfig(created.id, { ndaTemplate: 'Custom NDA text' });
      expect(result).toBeUndefined();
    });

    it('allows custom NDA on growth plan', () => {
      const created = service.createOrg('Test', 'nda-growth', 'user-1', 'growth');
      if ('error' in created) throw new Error('unexpected');

      const result = service.updateGovernanceConfig(created.id, { ndaTemplate: 'Custom NDA text' });
      expect(result?.governanceConfig.ndaTemplate).toBe('Custom NDA text');
    });
  });

  describe('API key rotation', () => {
    it('rotates API key and invalidates old one', () => {
      const created = service.createOrg('Test', 'rotate-test', 'user-1');
      if ('error' in created) throw new Error('unexpected');

      const oldKey = created.apiKey;
      const newKey = service.rotateApiKey(created.id);

      expect(newKey).not.toBe(oldKey);
      expect(newKey).toMatch(/^caas_/);

      // Old key no longer resolves
      expect(service.getByApiKey(oldKey)).toBeUndefined();
      // New key resolves
      expect(service.getByApiKey(newKey!)).toBeDefined();
    });
  });

  describe('plan limits', () => {
    it('enforces conference creation limit', () => {
      const created = service.createOrg('Test', 'limit-test', 'user-1', 'starter');
      if ('error' in created) throw new Error('unexpected');

      expect(service.canCreateConference(created.id)).toBe(true);

      // Use up the limit (starter = 2/month)
      service.incrementUsage(created.id, 'conferencesCreated', 2);
      expect(service.canCreateConference(created.id)).toBe(false);
    });

    it('enterprise has unlimited conferences', () => {
      const created = service.createOrg('Test', 'unlimited', 'user-1', 'enterprise');
      if ('error' in created) throw new Error('unexpected');

      service.incrementUsage(created.id, 'conferencesCreated', 1000);
      expect(service.canCreateConference(created.id)).toBe(true);
    });
  });

  describe('members', () => {
    it('owner is added automatically', () => {
      const created = service.createOrg('Test', 'member-test', 'user-1');
      if ('error' in created) throw new Error('unexpected');

      const members = service.getMembers(created.id);
      expect(members).toHaveLength(1);
      expect(members[0].userId).toBe('user-1');
      expect(members[0].role).toBe('owner');
    });

    it('adds members with specified role', () => {
      const created = service.createOrg('Test', 'add-member', 'user-1');
      if ('error' in created) throw new Error('unexpected');

      const member = service.addMember(created.id, 'user-2', 'curator');
      expect(member?.role).toBe('curator');
      expect(service.getMembers(created.id)).toHaveLength(2);
    });

    it('rejects duplicate members', () => {
      const created = service.createOrg('Test', 'dup-member', 'user-1');
      if ('error' in created) throw new Error('unexpected');

      const result = service.addMember(created.id, 'user-1', 'admin');
      expect(result).toBeUndefined();
    });

    it('checks role hierarchy', () => {
      const created = service.createOrg('Test', 'role-check', 'user-1');
      if ('error' in created) throw new Error('unexpected');

      service.addMember(created.id, 'user-2', 'viewer');
      service.addMember(created.id, 'user-3', 'admin');

      // Owner has all roles
      expect(service.hasRole(created.id, 'user-1', 'owner')).toBe(true);
      expect(service.hasRole(created.id, 'user-1', 'viewer')).toBe(true);

      // Viewer doesn't have admin
      expect(service.hasRole(created.id, 'user-2', 'viewer')).toBe(true);
      expect(service.hasRole(created.id, 'user-2', 'admin')).toBe(false);

      // Admin has curator and viewer
      expect(service.hasRole(created.id, 'user-3', 'curator')).toBe(true);
      expect(service.hasRole(created.id, 'user-3', 'viewer')).toBe(true);
      expect(service.hasRole(created.id, 'user-3', 'owner')).toBe(false);
    });
  });

  describe('listing', () => {
    it('lists orgs by owner', () => {
      service.createOrg('Org1', 'org-one', 'user-1');
      service.createOrg('Org2', 'org-two', 'user-1');
      service.createOrg('Org3', 'org-three', 'user-2');

      const user1Orgs = service.listByOwner('user-1');
      expect(user1Orgs).toHaveLength(2);

      const user2Orgs = service.listByOwner('user-2');
      expect(user2Orgs).toHaveLength(1);
    });

    it('lists all orgs', () => {
      service.createOrg('A', 'org-a', 'u1');
      service.createOrg('B', 'org-b', 'u2');
      expect(service.listOrgs()).toHaveLength(2);
    });
  });
});

describe('PLAN_LIMITS', () => {
  it('starter has expected limits', () => {
    const starter = PLAN_LIMITS.starter;
    expect(starter.maxConferencesPerMonth).toBe(2);
    expect(starter.maxProjectsPerConference).toBe(10);
    expect(starter.customBranding).toBe(false);
    expect(starter.customDomain).toBe(false);
    expect(starter.zoomIntegration).toBe(true);
    expect(starter.sseRealtime).toBe(true);
  });

  it('growth unlocks branding and custom NDA', () => {
    const growth = PLAN_LIMITS.growth;
    expect(growth.customBranding).toBe(true);
    expect(growth.customNda).toBe(true);
    expect(growth.hydraAudit).toBe(true);
    expect(growth.customDomain).toBe(false);
  });

  it('enterprise is unlimited', () => {
    const ent = PLAN_LIMITS.enterprise;
    expect(ent.maxConferencesPerMonth).toBe(-1);
    expect(ent.maxProjectsPerConference).toBe(-1);
    expect(ent.customDomain).toBe(true);
    expect(ent.dedicatedSupport).toBe(true);
  });
});
