/**
 * @file crawl-coordinator.test.ts
 * @module fleet/crawl-coordinator.test
 *
 * Tests for multi-agent browser crawl coordination system:
 *
 * A: CrawlMessageBus — pub/sub messaging, topics, wildcards
 * B: CrawlFrontier — URL queue, dedup, priority, rate limiting
 * C: CrawlCoordinator — agent management, role-based assignment
 * D: Role Switching — braid-governed transitions, BFT voting
 * E: Safety & Quarantine — score tracking, auto-quarantine
 * F: Integration — full crawl lifecycle
 */

import { describe, expect, it, beforeEach } from 'vitest';

import {
  CrawlMessageBus,
  buildTopic,
  parseTopic,
  topicMatches,
  type CrawlMessage,
} from '../../src/fleet/crawl-message-bus';

import {
  CrawlFrontier,
  extractDomain,
  canonicalizeUrl,
  DEFAULT_FRONTIER_CONFIG,
} from '../../src/fleet/crawl-frontier';

import {
  CrawlCoordinator,
  ROLE_BRAID_MAP,
  VALID_ROLE_TRANSITIONS,
  DEFAULT_CRAWL_CONFIG,
  type CrawlResult,
} from '../../src/fleet/crawl-coordinator';

// ═══════════════════════════════════════════════════════════════
// A: CrawlMessageBus
// ═══════════════════════════════════════════════════════════════

describe('A: CrawlMessageBus', () => {
  let bus: CrawlMessageBus;

  beforeEach(() => {
    bus = new CrawlMessageBus();
  });

  describe('Topic utilities', () => {
    it('buildTopic creates Kafka-style topic string', () => {
      expect(buildTopic('discovery', 'url_found')).toBe('scbe.crawl.discovery.url_found');
      expect(buildTopic('sentinel', 'safety_alert')).toBe('scbe.crawl.sentinel.safety_alert');
    });

    it('parseTopic extracts channel and event', () => {
      const result = parseTopic('scbe.crawl.discovery.url_found');
      expect(result).toEqual({ channel: 'discovery', event: 'url_found' });
    });

    it('parseTopic returns null for invalid topics', () => {
      expect(parseTopic('invalid')).toBeNull();
      expect(parseTopic('scbe.other.discovery.url')).toBeNull();
      expect(parseTopic('scbe.crawl.discovery')).toBeNull();
    });

    it('topicMatches supports exact match', () => {
      expect(topicMatches('scbe.crawl.discovery.url_found', 'scbe.crawl.discovery.url_found')).toBe(true);
      expect(topicMatches('scbe.crawl.discovery.url_found', 'scbe.crawl.discovery.url_failed')).toBe(false);
    });

    it('topicMatches supports * wildcard', () => {
      expect(topicMatches('scbe.crawl.discovery.url_found', 'scbe.crawl.discovery.*')).toBe(true);
      expect(topicMatches('scbe.crawl.sentinel.safety_alert', 'scbe.crawl.sentinel.*')).toBe(true);
      expect(topicMatches('scbe.crawl.discovery.url_found', 'scbe.crawl.sentinel.*')).toBe(false);
    });

    it('topicMatches supports global wildcard', () => {
      expect(topicMatches('scbe.crawl.discovery.url_found', '*')).toBe(true);
    });
  });

  describe('Pub/Sub', () => {
    it('publishes and delivers messages to subscribers', () => {
      const received: CrawlMessage[] = [];
      bus.subscribe('agent-1', 'scbe.crawl.discovery.*', (msg) => received.push(msg));

      bus.publish('agent-2', 'discovery', 'url_found', { url: 'https://example.com' });

      expect(received).toHaveLength(1);
      expect(received[0].payload).toEqual({ url: 'https://example.com' });
      expect(received[0].fromAgent).toBe('agent-2');
    });

    it('does not deliver to sender', () => {
      const received: CrawlMessage[] = [];
      bus.subscribe('agent-1', '*', (msg) => received.push(msg));

      bus.publish('agent-1', 'status', 'heartbeat', {});

      expect(received).toHaveLength(0);
    });

    it('delivers direct messages only to target', () => {
      const received1: CrawlMessage[] = [];
      const received2: CrawlMessage[] = [];
      bus.subscribe('agent-1', '*', (msg) => received1.push(msg));
      bus.subscribe('agent-2', '*', (msg) => received2.push(msg));

      bus.publish('agent-3', 'governance', 'role_switch_approved', { approved: true }, {
        toAgent: 'agent-1',
      });

      expect(received1).toHaveLength(1);
      expect(received2).toHaveLength(0);
    });

    it('supports multiple subscribers on same topic', () => {
      let count = 0;
      bus.subscribe('agent-1', 'scbe.crawl.discovery.*', () => count++);
      bus.subscribe('agent-2', 'scbe.crawl.discovery.*', () => count++);

      bus.publish('agent-3', 'discovery', 'url_found', {});

      expect(count).toBe(2);
    });

    it('unsubscribe stops delivery', () => {
      const received: CrawlMessage[] = [];
      const sub = bus.subscribe('agent-1', '*', (msg) => received.push(msg));

      bus.publish('agent-2', 'status', 'heartbeat', {});
      expect(received).toHaveLength(1);

      sub.unsubscribe();
      bus.publish('agent-2', 'status', 'heartbeat', {});
      expect(received).toHaveLength(1);
    });

    it('assigns monotonic sequence numbers per agent', () => {
      const m1 = bus.publish('agent-1', 'status', 'heartbeat', {});
      const m2 = bus.publish('agent-1', 'status', 'heartbeat', {});
      const m3 = bus.publish('agent-2', 'status', 'heartbeat', {});

      expect(m1.sequence).toBe(1);
      expect(m2.sequence).toBe(2);
      expect(m3.sequence).toBe(1); // Different agent, resets
    });

    it('includes correlationId for request-response', () => {
      const msg = bus.publish('agent-1', 'governance', 'consensus_request', {}, {
        correlationId: 'req-123',
      });
      expect(msg.correlationId).toBe('req-123');
    });

    it('priority defaults to normal', () => {
      const msg = bus.publish('agent-1', 'status', 'heartbeat', {});
      expect(msg.priority).toBe('normal');
    });

    it('supports critical priority', () => {
      const msg = bus.publish('agent-1', 'sentinel', 'safety_alert', {}, { priority: 'critical' });
      expect(msg.priority).toBe('critical');
    });
  });

  describe('Message queries', () => {
    it('getMessagesForAgent returns relevant messages', () => {
      bus.subscribe('agent-1', '*', () => {});
      bus.publish('agent-2', 'status', 'heartbeat', {});
      bus.publish('agent-3', 'discovery', 'url_found', {}, { toAgent: 'agent-1' });
      bus.publish('agent-1', 'status', 'heartbeat', {}); // Own message

      const msgs = bus.getMessagesForAgent('agent-1');
      expect(msgs).toHaveLength(2); // Broadcast + direct, not own
    });

    it('getMessagesByChannel filters correctly', () => {
      bus.publish('agent-1', 'discovery', 'url_found', {});
      bus.publish('agent-1', 'status', 'heartbeat', {});
      bus.publish('agent-1', 'discovery', 'url_completed', {});

      expect(bus.getMessagesByChannel('discovery')).toHaveLength(2);
      expect(bus.getMessagesByChannel('status')).toHaveLength(1);
    });
  });

  describe('Statistics', () => {
    it('tracks publish and delivery counts', () => {
      bus.subscribe('agent-1', '*', () => {});
      bus.publish('agent-2', 'discovery', 'url_found', {});
      bus.publish('agent-2', 'status', 'heartbeat', {});

      const stats = bus.getStats();
      expect(stats.totalPublished).toBe(2);
      expect(stats.totalDelivered).toBe(2);
      expect(stats.channelCounts.discovery).toBe(1);
      expect(stats.channelCounts.status).toBe(1);
    });

    it('tracks connected agents', () => {
      bus.subscribe('agent-1', '*', () => {});
      bus.subscribe('agent-2', '*', () => {});
      expect(bus.getStats().connectedAgents).toBe(2);
    });

    it('reset clears all state', () => {
      bus.subscribe('agent-1', '*', () => {});
      bus.publish('agent-2', 'status', 'heartbeat', {});
      bus.reset();

      const stats = bus.getStats();
      expect(stats.totalPublished).toBe(0);
      expect(stats.connectedAgents).toBe(0);
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// B: CrawlFrontier
// ═══════════════════════════════════════════════════════════════

describe('B: CrawlFrontier', () => {
  let frontier: CrawlFrontier;

  beforeEach(() => {
    frontier = new CrawlFrontier();
  });

  describe('URL utilities', () => {
    it('extractDomain handles standard URLs', () => {
      expect(extractDomain('https://example.com/path')).toBe('example.com');
      expect(extractDomain('http://sub.example.com:8080/path')).toBe('sub.example.com');
    });

    it('canonicalizeUrl removes fragments', () => {
      expect(canonicalizeUrl('https://example.com/page#section')).toBe('https://example.com/page');
    });

    it('canonicalizeUrl removes trailing slash', () => {
      const canon = canonicalizeUrl('https://example.com/page/');
      expect(canon).toBe('https://example.com/page');
    });

    it('canonicalizeUrl preserves root path', () => {
      expect(canonicalizeUrl('https://example.com/')).toContain('example.com');
    });

    it('canonicalizeUrl sorts query params', () => {
      const c1 = canonicalizeUrl('https://example.com?b=2&a=1');
      const c2 = canonicalizeUrl('https://example.com?a=1&b=2');
      expect(c1).toBe(c2);
    });
  });

  describe('Seed URLs', () => {
    it('adds seed URLs at depth 0', () => {
      const added = frontier.addSeedUrls(['https://example.com', 'https://test.com']);
      expect(added).toBe(2);
      expect(frontier.size).toBe(2);
    });

    it('deduplicates seed URLs', () => {
      frontier.addSeedUrls(['https://example.com', 'https://example.com']);
      expect(frontier.size).toBe(1);
    });

    it('seed URLs get boosted priority', () => {
      frontier.addSeedUrls(['https://example.com']);
      const entry = frontier.getEntry('https://example.com');
      expect(entry!.priority).toBe(DEFAULT_FRONTIER_CONFIG.seedPriorityBoost);
    });
  });

  describe('URL addition and dedup', () => {
    it('adds URL and marks as queued', () => {
      expect(frontier.addUrl('https://example.com/page', 1)).toBe(true);
      const entry = frontier.getEntry('https://example.com/page');
      expect(entry!.status).toBe('queued');
      expect(entry!.depth).toBe(1);
    });

    it('rejects duplicate URLs', () => {
      frontier.addUrl('https://example.com', 0);
      expect(frontier.addUrl('https://example.com', 0)).toBe(false);
    });

    it('rejects URLs beyond max depth', () => {
      expect(frontier.addUrl('https://example.com', 100)).toBe(false);
    });

    it('rejects blocked domains', () => {
      const f = new CrawlFrontier({ blockedDomains: ['evil\\.com'] });
      expect(f.addUrl('https://evil.com/page', 0)).toBe(false);
    });

    it('priority decreases with depth (φ^(-depth))', () => {
      frontier.addUrl('https://a.com', 0);
      frontier.addUrl('https://b.com', 1);
      frontier.addUrl('https://c.com', 3);

      const a = frontier.getEntry('https://a.com')!;
      const b = frontier.getEntry('https://b.com')!;
      const c = frontier.getEntry('https://c.com')!;
      expect(a.priority).toBeGreaterThan(b.priority);
      expect(b.priority).toBeGreaterThan(c.priority);
    });

    it('hasSeen returns true for added URLs', () => {
      frontier.addUrl('https://example.com', 0);
      expect(frontier.hasSeen('https://example.com')).toBe(true);
      expect(frontier.hasSeen('https://other.com')).toBe(false);
    });
  });

  describe('Claim and complete', () => {
    it('claim returns highest-priority URL', () => {
      frontier.addSeedUrls(['https://low.com']);
      frontier.addUrl('https://deep.com', 3);

      const entry = frontier.claim('agent-1');
      expect(entry).not.toBeNull();
      expect(entry!.url).toContain('low.com'); // Seeds have higher priority
    });

    it('claim marks URL as claimed', () => {
      frontier.addSeedUrls(['https://example.com']);
      const entry = frontier.claim('agent-1')!;
      expect(entry.status).toBe('claimed');
      expect(entry.claimedBy).toBe('agent-1');
    });

    it('claimed URL cannot be claimed again', () => {
      frontier.addSeedUrls(['https://example.com']);
      frontier.claim('agent-1');
      const second = frontier.claim('agent-2');
      expect(second).toBeNull();
    });

    it('complete marks URL and adds discovered URLs', () => {
      frontier.addSeedUrls(['https://example.com']);
      frontier.claim('agent-1');

      const added = frontier.complete('https://example.com', 'agent-1', [
        'https://example.com/page1',
        'https://example.com/page2',
      ]);

      expect(added).toBe(2);
      expect(frontier.size).toBe(3); // seed + 2 discovered
      expect(frontier.getEntry('https://example.com')!.status).toBe('completed');
    });

    it('markCrawling updates status', () => {
      frontier.addSeedUrls(['https://example.com']);
      frontier.claim('agent-1');
      expect(frontier.markCrawling('https://example.com', 'agent-1')).toBe(true);
      expect(frontier.getEntry('https://example.com')!.status).toBe('crawling');
    });
  });

  describe('Failure and retry', () => {
    it('fail requeues with reduced priority', () => {
      frontier.addSeedUrls(['https://example.com']);
      const original = frontier.getEntry('https://example.com')!;
      const originalPriority = original.priority;
      frontier.claim('agent-1');

      const requeued = frontier.fail('https://example.com', 'agent-1', 'timeout');
      expect(requeued).toBe(true);
      expect(frontier.getEntry('https://example.com')!.status).toBe('queued');
      expect(frontier.getEntry('https://example.com')!.priority).toBeLessThan(originalPriority);
    });

    it('fail marks as failed after max retries', () => {
      const f = new CrawlFrontier({ maxRetries: 1 });
      f.addSeedUrls(['https://example.com']);
      f.claim('agent-1');
      f.fail('https://example.com', 'agent-1', 'error1');
      f.claim('agent-1');
      const requeued = f.fail('https://example.com', 'agent-1', 'error2');
      expect(requeued).toBe(false);
      expect(f.getEntry('https://example.com')!.status).toBe('failed');
    });
  });

  describe('Domain rate limiting', () => {
    it('blocks rapid claims from same domain', () => {
      frontier.addUrl('https://example.com/page1', 0);
      frontier.addUrl('https://example.com/page2', 0);
      frontier.claim('agent-1');
      const second = frontier.claim('agent-2');
      expect(second).toBeNull(); // Rate limited
    });

    it('allows claims from different domains', () => {
      frontier.addUrl('https://a.com', 0);
      frontier.addUrl('https://b.com', 0);
      frontier.claim('agent-1');
      const second = frontier.claim('agent-2');
      expect(second).not.toBeNull();
    });
  });

  describe('Release and blocking', () => {
    it('release puts URL back in queue', () => {
      frontier.addSeedUrls(['https://example.com']);
      frontier.claim('agent-1');
      expect(frontier.release('https://example.com', 'agent-1')).toBe(true);
      expect(frontier.getEntry('https://example.com')!.status).toBe('queued');
    });

    it('blockDomain marks queued entries as blocked', () => {
      frontier.addUrl('https://evil.com/page1', 0);
      frontier.addUrl('https://evil.com/page2', 0);
      frontier.blockDomain('evil\\.com');
      expect(frontier.getByStatus('blocked')).toHaveLength(2);
    });
  });

  describe('Statistics', () => {
    it('tracks total added and completed', () => {
      frontier.addSeedUrls(['https://a.com', 'https://b.com']);
      frontier.claim('agent-1');
      frontier.complete('https://a.com', 'agent-1');

      const stats = frontier.getStats();
      expect(stats.totalAdded).toBe(2);
      expect(stats.totalCompleted).toBe(1);
      expect(stats.queued).toBe(1);
    });

    it('tracks unique domains', () => {
      frontier.addUrl('https://a.com', 0);
      frontier.addUrl('https://b.com', 0);
      frontier.addUrl('https://a.com/page', 1);
      expect(frontier.getStats().uniqueDomains).toBe(2);
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// C: CrawlCoordinator — Agent Management
// ═══════════════════════════════════════════════════════════════

describe('C: CrawlCoordinator — Agent Management', () => {
  let coord: CrawlCoordinator;

  beforeEach(() => {
    coord = new CrawlCoordinator({ requireConsensusForRoleSwitch: false });
  });

  it('registers agents with initial role', () => {
    const agent = coord.registerAgent('agent-1', 'scout');
    expect(agent.role).toBe('scout');
    expect(agent.status).toBe('idle');
    expect(agent.safetyScore).toBe(1.0);
  });

  it('getAgent returns registered agent', () => {
    coord.registerAgent('agent-1', 'scout');
    expect(coord.getAgent('agent-1')).toBeDefined();
    expect(coord.getAgent('nonexistent')).toBeUndefined();
  });

  it('getAllAgents returns all registered agents', () => {
    coord.registerAgent('a1', 'scout');
    coord.registerAgent('a2', 'analyzer');
    coord.registerAgent('a3', 'sentinel');
    expect(coord.getAllAgents()).toHaveLength(3);
  });

  it('getAgentsByRole filters by role', () => {
    coord.registerAgent('a1', 'scout');
    coord.registerAgent('a2', 'scout');
    coord.registerAgent('a3', 'analyzer');
    expect(coord.getAgentsByRole('scout')).toHaveLength(2);
    expect(coord.getAgentsByRole('analyzer')).toHaveLength(1);
  });

  it('removeAgent removes and releases URLs', () => {
    coord.registerAgent('a1', 'scout');
    coord.addSeedUrls(['https://example.com']);
    coord.assignNext('a1');
    expect(coord.removeAgent('a1')).toBe(true);
    expect(coord.getAgent('a1')).toBeUndefined();
  });
});

// ═══════════════════════════════════════════════════════════════
// C: CrawlCoordinator — Task Assignment
// ═══════════════════════════════════════════════════════════════

describe('C: CrawlCoordinator — Task Assignment', () => {
  let coord: CrawlCoordinator;

  beforeEach(() => {
    coord = new CrawlCoordinator({ requireConsensusForRoleSwitch: false });
    coord.registerAgent('scout-1', 'scout');
    coord.registerAgent('analyzer-1', 'analyzer');
    coord.registerAgent('sentinel-1', 'sentinel');
    coord.registerAgent('reporter-1', 'reporter');
  });

  it('assigns URLs to scouts', () => {
    coord.addSeedUrls(['https://example.com']);
    const entry = coord.assignNext('scout-1');
    expect(entry).not.toBeNull();
    expect(entry!.url).toContain('example.com');
  });

  it('assigns URLs to analyzers', () => {
    coord.addSeedUrls(['https://example.com']);
    const entry = coord.assignNext('analyzer-1');
    expect(entry).not.toBeNull();
  });

  it('does not assign URLs to sentinels', () => {
    coord.addSeedUrls(['https://example.com']);
    expect(coord.assignNext('sentinel-1')).toBeNull();
  });

  it('does not assign URLs to reporters', () => {
    coord.addSeedUrls(['https://example.com']);
    expect(coord.assignNext('reporter-1')).toBeNull();
  });

  it('respects maxConcurrent limit', () => {
    const c = new CrawlCoordinator({ maxConcurrent: 1, requireConsensusForRoleSwitch: false });
    c.registerAgent('a1', 'scout');
    c.registerAgent('a2', 'scout');
    c.addSeedUrls(['https://a.com', 'https://b.com']);
    c.assignNext('a1');
    expect(c.assignNext('a2')).toBeNull(); // Limit reached
  });

  it('returns null when no work available', () => {
    expect(coord.assignNext('scout-1')).toBeNull();
  });

  it('updates agent status on assignment', () => {
    coord.addSeedUrls(['https://example.com']);
    coord.assignNext('scout-1');
    expect(coord.getAgent('scout-1')!.status).toBe('crawling');
  });
});

// ═══════════════════════════════════════════════════════════════
// D: Role Switching (Braid-Governed)
// ═══════════════════════════════════════════════════════════════

describe('D: Role Switching', () => {
  describe('Braid mapping', () => {
    it('all 4 roles have valid braid coordinates', () => {
      for (const role of ['scout', 'analyzer', 'sentinel', 'reporter'] as const) {
        const coords = ROLE_BRAID_MAP[role];
        expect(coords.primary).toBeGreaterThanOrEqual(-1);
        expect(coords.primary).toBeLessThanOrEqual(1);
        expect(coords.mirror).toBeGreaterThanOrEqual(-1);
        expect(coords.mirror).toBeLessThanOrEqual(1);
      }
    });

    it('valid transitions have Chebyshev distance ≤ 1', () => {
      for (const [from, targets] of Object.entries(VALID_ROLE_TRANSITIONS)) {
        const fromCoords = ROLE_BRAID_MAP[from as keyof typeof ROLE_BRAID_MAP];
        for (const to of targets) {
          const toCoords = ROLE_BRAID_MAP[to as keyof typeof ROLE_BRAID_MAP];
          const chebyshev = Math.max(
            Math.abs(fromCoords.primary - toCoords.primary),
            Math.abs(fromCoords.mirror - toCoords.mirror),
          );
          expect(chebyshev).toBeLessThanOrEqual(1);
        }
      }
    });

    it('analyzer cannot directly become reporter (Chebyshev = 1 check)', () => {
      // analyzer (+1,+1) → reporter (0,0) = distance 1, should be valid
      expect(VALID_ROLE_TRANSITIONS.analyzer).not.toContain('reporter');
    });
  });

  describe('Auto-approved role switches', () => {
    it('allows valid transition without consensus', () => {
      const coord = new CrawlCoordinator({ requireConsensusForRoleSwitch: false });
      coord.registerAgent('a1', 'scout');
      const requestId = coord.requestRoleSwitch('a1', 'analyzer', 'need deep analysis');
      expect(requestId).not.toBeNull();
      expect(coord.getAgent('a1')!.role).toBe('analyzer');
    });

    it('rejects invalid braid transition', () => {
      const coord = new CrawlCoordinator({ requireConsensusForRoleSwitch: false });
      coord.registerAgent('a1', 'analyzer');
      const requestId = coord.requestRoleSwitch('a1', 'reporter', 'want to report');
      expect(requestId).toBeNull();
      expect(coord.getAgent('a1')!.role).toBe('analyzer'); // Unchanged
    });

    it('self-transition returns null', () => {
      const coord = new CrawlCoordinator({ requireConsensusForRoleSwitch: false });
      coord.registerAgent('a1', 'scout');
      expect(coord.requestRoleSwitch('a1', 'scout', 'same')).toBeNull();
    });

    it('increments roleSwitches counter', () => {
      const coord = new CrawlCoordinator({ requireConsensusForRoleSwitch: false });
      coord.registerAgent('a1', 'scout');
      coord.requestRoleSwitch('a1', 'analyzer', 'test');
      expect(coord.getAgent('a1')!.roleSwitches).toBe(1);
    });
  });

  describe('Consensus-based role switches', () => {
    let coord: CrawlCoordinator;

    beforeEach(() => {
      coord = new CrawlCoordinator({
        requireConsensusForRoleSwitch: true,
        roleSwitchQuorum: 2,
      });
      coord.registerAgent('a1', 'scout');
      coord.registerAgent('a2', 'analyzer');
      coord.registerAgent('a3', 'sentinel');
    });

    it('creates pending request', () => {
      const id = coord.requestRoleSwitch('a1', 'analyzer', 'deep analysis');
      expect(id).not.toBeNull();
      const req = coord.getRoleSwitchRequest(id!);
      expect(req!.status).toBe('pending');
      expect(req!.fromRole).toBe('scout');
      expect(req!.toRole).toBe('analyzer');
    });

    it('approves after quorum reached', () => {
      const id = coord.requestRoleSwitch('a1', 'sentinel', 'monitoring')!;
      coord.voteOnRoleSwitch(id, 'a2', true);
      const result = coord.voteOnRoleSwitch(id, 'a3', true);
      expect(result).toBe('approved');
      expect(coord.getAgent('a1')!.role).toBe('sentinel');
    });

    it('denies when too many rejections', () => {
      const id = coord.requestRoleSwitch('a1', 'sentinel', 'monitoring')!;
      coord.voteOnRoleSwitch(id, 'a2', false);
      const result = coord.voteOnRoleSwitch(id, 'a3', false);
      expect(result).toBe('denied');
      expect(coord.getAgent('a1')!.role).toBe('scout'); // Unchanged
    });

    it('pending while waiting for votes', () => {
      const id = coord.requestRoleSwitch('a1', 'sentinel', 'monitoring')!;
      const result = coord.voteOnRoleSwitch(id, 'a2', true);
      expect(result).toBe('pending');
    });

    it('cannot vote on own request', () => {
      const id = coord.requestRoleSwitch('a1', 'sentinel', 'monitoring')!;
      const result = coord.voteOnRoleSwitch(id, 'a1', true);
      expect(result).toBe('pending'); // Ignored
    });

    it('cannot vote twice', () => {
      const id = coord.requestRoleSwitch('a1', 'sentinel', 'monitoring')!;
      coord.voteOnRoleSwitch(id, 'a2', true);
      const result = coord.voteOnRoleSwitch(id, 'a2', true);
      expect(result).toBe('pending');
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// E: Safety & Quarantine
// ═══════════════════════════════════════════════════════════════

describe('E: Safety & Quarantine', () => {
  let coord: CrawlCoordinator;

  beforeEach(() => {
    coord = new CrawlCoordinator({ requireConsensusForRoleSwitch: false });
    coord.registerAgent('a1', 'scout');
    coord.registerAgent('a2', 'sentinel');
  });

  it('successful crawl increases safety score', () => {
    coord.addSeedUrls(['https://example.com']);
    coord.assignNext('a1');
    coord.reportResult(makeResult('https://example.com', 'a1', true));
    expect(coord.getAgent('a1')!.safetyScore).toBeGreaterThan(1.0 - 0.01);
  });

  it('unsafe crawl decreases safety score', () => {
    coord.addSeedUrls(['https://evil.com']);
    coord.assignNext('a1');
    coord.reportResult(makeResult('https://evil.com', 'a1', false));
    expect(coord.getAgent('a1')!.safetyScore).toBeLessThan(1.0);
  });

  it('agent auto-quarantined when safety score drops below threshold', () => {
    const c = new CrawlCoordinator({
      requireConsensusForRoleSwitch: false,
      minSafetyScore: 0.5,
      failurePenalty: 0.2,
    });
    c.registerAgent('a1', 'scout');

    // Drive safety score below threshold
    for (let i = 0; i < 5; i++) {
      c.addSeedUrls([`https://evil${i}.com`]);
      c.assignNext('a1');
      c.reportResult(makeResult(`https://evil${i}.com`, 'a1', false));
    }

    // Try to assign — should quarantine
    c.addSeedUrls(['https://next.com']);
    expect(c.assignNext('a1')).toBeNull();
    expect(c.getAgent('a1')!.status).toBe('quarantined');
  });

  it('quarantine blocks assignment', () => {
    coord.quarantineAgent('a1', 'suspicious behavior');
    coord.addSeedUrls(['https://example.com']);
    expect(coord.assignNext('a1')).toBeNull();
  });

  it('manual quarantine works', () => {
    expect(coord.quarantineAgent('a1', 'test')).toBe(true);
    expect(coord.getAgent('a1')!.status).toBe('quarantined');
  });

  it('release from quarantine requires sufficient safety score', () => {
    coord.quarantineAgent('a1', 'test');
    coord.adjustSafetyScore('a1', -0.8); // Drop to 0.2
    expect(coord.releaseFromQuarantine('a1')).toBe(false);

    coord.adjustSafetyScore('a1', 0.5); // Bring back to 0.7
    expect(coord.releaseFromQuarantine('a1')).toBe(true);
    expect(coord.getAgent('a1')!.status).toBe('idle');
  });

  it('adjustSafetyScore clamps to [0, 1]', () => {
    expect(coord.adjustSafetyScore('a1', 5.0)).toBe(1.0);
    expect(coord.adjustSafetyScore('a1', -5.0)).toBe(0.0);
  });

  it('reportFailure reduces safety score less than unsafe result', () => {
    const before = coord.getAgent('a1')!.safetyScore;
    coord.addSeedUrls(['https://example.com']);
    coord.assignNext('a1');
    coord.reportFailure('https://example.com', 'a1', 'timeout');
    const after = coord.getAgent('a1')!.safetyScore;
    expect(after).toBeLessThan(before);
    expect(after).toBeGreaterThan(before - DEFAULT_CRAWL_CONFIG.failurePenalty);
  });
});

// ═══════════════════════════════════════════════════════════════
// F: Integration — Full Crawl Lifecycle
// ═══════════════════════════════════════════════════════════════

describe('F: Full Crawl Lifecycle', () => {
  it('multi-agent crawl with role switching and safety', () => {
    const coord = new CrawlCoordinator({
      requireConsensusForRoleSwitch: false,
      maxConcurrent: 3,
    });

    // Register agents
    coord.registerAgent('scout-1', 'scout');
    coord.registerAgent('scout-2', 'scout');
    coord.registerAgent('sentinel-1', 'sentinel');

    // Seed URLs
    coord.addSeedUrls(['https://a.com', 'https://b.com', 'https://c.com']);
    expect(coord.hasWork()).toBe(true);

    // Scout-1 crawls first URL
    const e1 = coord.assignNext('scout-1')!;
    expect(e1).not.toBeNull();
    coord.reportResult(makeResult(e1.url, 'scout-1', true, ['https://a.com/page1']));

    // Scout-2 crawls second URL
    const e2 = coord.assignNext('scout-2')!;
    expect(e2).not.toBeNull();
    coord.reportResult(makeResult(e2.url, 'scout-2', true));

    // Scout-1 switches to analyzer for deep analysis
    coord.requestRoleSwitch('scout-1', 'analyzer', 'deep dive');
    expect(coord.getAgent('scout-1')!.role).toBe('analyzer');

    // Analyzer picks up discovered page
    const e3 = coord.assignNext('scout-1');
    if (e3) {
      coord.reportResult(makeResult(e3.url, 'scout-1', true));
    }

    // Stats
    const stats = coord.getStats();
    expect(stats.totalAgents).toBe(3);
    expect(stats.urlsCompleted).toBeGreaterThanOrEqual(2);
    expect(stats.roleSwitchesApproved).toBe(1);
    expect(stats.averageSafetyScore).toBeGreaterThan(0.9);
  });

  it('sentinel quarantines compromised agent', () => {
    const coord = new CrawlCoordinator({ requireConsensusForRoleSwitch: false });
    coord.registerAgent('scout-1', 'scout');
    coord.registerAgent('sentinel-1', 'sentinel');

    coord.addSeedUrls(['https://malicious.com']);
    const entry = coord.assignNext('scout-1')!;

    // Scout encounters unsafe page
    coord.reportResult(makeResult(entry.url, 'scout-1', false, [], 0.95));

    // Sentinel quarantines the scout
    coord.quarantineAgent('scout-1', 'encountered malicious page');
    expect(coord.getAgent('scout-1')!.status).toBe('quarantined');

    // Quarantined agent can't get new work
    coord.addSeedUrls(['https://safe.com']);
    expect(coord.assignNext('scout-1')).toBeNull();
  });

  it('message bus carries all coordination events', () => {
    const coord = new CrawlCoordinator({ requireConsensusForRoleSwitch: false });
    coord.registerAgent('a1', 'scout');
    coord.addSeedUrls(['https://example.com']);
    coord.assignNext('a1');
    coord.reportResult(makeResult('https://example.com', 'a1', true, ['https://example.com/p1']));

    const busStats = coord.bus.getStats();
    expect(busStats.totalPublished).toBeGreaterThan(0);
    expect(busStats.channelCounts.discovery).toBeGreaterThan(0);
  });

  it('results are tracked and queryable', () => {
    const coord = new CrawlCoordinator({ requireConsensusForRoleSwitch: false });
    coord.registerAgent('a1', 'scout');
    coord.registerAgent('a2', 'analyzer');
    coord.addSeedUrls(['https://a.com', 'https://b.com']);

    coord.assignNext('a1');
    coord.reportResult(makeResult('https://a.com', 'a1', true));
    coord.assignNext('a2');
    coord.reportResult(makeResult('https://b.com', 'a2', true));

    expect(coord.getResults()).toHaveLength(2);
    expect(coord.getResultsByAgent('a1')).toHaveLength(1);
    expect(coord.getResultsByAgent('a2')).toHaveLength(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// Test Helpers
// ═══════════════════════════════════════════════════════════════

function makeResult(
  url: string,
  agentId: string,
  safe: boolean,
  discoveredUrls: string[] = [],
  riskScore: number = safe ? 0.1 : 0.8,
): CrawlResult {
  return {
    url,
    agentId,
    role: 'scout',
    discoveredUrls,
    extractedData: { title: 'Test Page' },
    safetyAssessment: {
      safe,
      riskScore,
      flags: safe ? [] : ['malicious_content'],
    },
    timestamp: Date.now(),
    durationMs: 500,
  };
}
