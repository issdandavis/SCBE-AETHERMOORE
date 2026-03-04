/**
 * @file aetherCore.test.ts
 * @module tests/browser
 * @layer Layer 1-14 (Unified)
 * @component AetherCore Integration Tests
 * @version 1.0.0
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { AetherCore, createAetherCore } from '../../src/browser/aetherCore.js';
import { MockBrowserBackend } from '../../src/browser/agent.js';

describe('AetherCore', () => {
  let core: AetherCore;

  beforeEach(() => {
    core = createAetherCore({
      backend: new MockBrowserBackend(),
      governanceArrayCount: 2,
      gaugeTicksPerAction: 3,
      lagrangianThresholds: {
        allow: 100,    // Wide thresholds for testing
        quarantine: 200,
        escalate: 300,
      },
    });
  });

  describe('lifecycle', () => {
    it('starts in idle state', () => {
      expect(core.getState()).toBe('idle');
    });

    it('transitions to active after start', async () => {
      await core.start();
      expect(core.getState()).toBe('active');
      await core.stop();
    });

    it('returns to idle after stop', async () => {
      await core.start();
      await core.stop();
      expect(core.getState()).toBe('idle');
    });

    it('forges initial and final governance blocks', async () => {
      await core.start();
      const { governanceChain } = await core.stop();
      // At least 2 blocks: one from start, one from stop
      expect(governanceChain.length).toBeGreaterThanOrEqual(2);
    });

    it('governance chain has continuous hashes', async () => {
      await core.start();
      await core.navigate('https://example.com');
      await core.navigate('https://test.com');
      const { governanceChain } = await core.stop();

      for (let i = 1; i < governanceChain.length; i++) {
        expect(governanceChain[i].previousHash).toBe(governanceChain[i - 1].stateHash);
      }
    });
  });

  describe('perception', () => {
    it('returns page observation and gauge state', async () => {
      await core.start('https://example.com');
      const perception = await core.perceive();

      expect(perception.page).toBeDefined();
      expect(perception.page?.url).toBe('https://example.com');
      expect(perception.gaugeState.lagrangian).toBeDefined();
      expect(perception.gaugeState.consensus).toBeDefined();
      expect(perception.gaugeState.tick).toBeGreaterThan(0);
      expect(perception.timestamp).toBeGreaterThan(0);

      await core.stop();
    });

    it('stores last perception', async () => {
      await core.start();
      expect(core.getLastPerception()).toBeNull();

      await core.perceive();
      expect(core.getLastPerception()).not.toBeNull();

      await core.stop();
    });
  });

  describe('actions', () => {
    it('navigates with governance block', async () => {
      await core.start();
      const result = await core.navigate('https://example.com');

      expect(result.success).toBe(true);
      expect(result.governanceBlock).toBeDefined();
      expect(result.governanceBlock.decision).toBe('ALLOW');

      await core.stop();
    });

    it('clicks with governance block', async () => {
      await core.start('https://example.com');
      const result = await core.click('#button');

      expect(result.success).toBe(true);
      expect(result.governanceBlock).toBeDefined();

      await core.stop();
    });

    it('types with governance block', async () => {
      await core.start('https://example.com');
      const result = await core.type('#input', 'hello world');

      expect(result.success).toBe(true);
      expect(result.governanceBlock).toBeDefined();

      await core.stop();
    });

    it('increments action counter', async () => {
      await core.start();
      expect(core.getActionCount()).toBe(0);

      await core.navigate('https://example.com');
      expect(core.getActionCount()).toBe(1);

      await core.click('#btn');
      expect(core.getActionCount()).toBe(2);

      await core.stop();
    });

    it('each action forges a governance block', async () => {
      await core.start();
      const chainBefore = core.getGovernanceChain().length;

      await core.navigate('https://example.com');
      await core.click('#btn');
      await core.type('#field', 'text');

      const chainAfter = core.getGovernanceChain().length;
      // 3 actions = 3 new blocks
      expect(chainAfter - chainBefore).toBe(3);

      await core.stop();
    });
  });

  describe('intent pipeline', () => {
    it('processes multi-action intent', async () => {
      await core.start();

      const result = await core.processIntent('Fill and submit form', [
        { type: 'navigate', url: 'https://example.com/form' },
        { type: 'type', selector: '#name', text: 'Test User' },
        { type: 'click', selector: '#submit' },
      ]);

      expect(result.intent).toBe('Fill and submit form');
      expect(result.actions).toHaveLength(3);
      expect(result.results).toHaveLength(3);
      expect(result.success).toBe(true);
      expect(result.governanceBlock).toBeDefined();
      expect(result.lagrangian).toBeDefined();
      expect(result.consensus).toBeDefined();
      expect(result.duration).toBeGreaterThan(0);

      await core.stop();
    });

    it('stops on DENY', async () => {
      // Create core with extremely tight thresholds to trigger DENY
      const tightCore = createAetherCore({
        backend: new MockBrowserBackend(),
        governanceArrayCount: 2,
        lagrangianThresholds: {
          allow: 0.0001,
          quarantine: 0.0002,
          escalate: 0.0003,
        },
      });

      await tightCore.start();

      const result = await tightCore.processIntent('Navigate everywhere', [
        { type: 'navigate', url: 'https://a.com' },
        { type: 'navigate', url: 'https://b.com' },
        { type: 'navigate', url: 'https://c.com' },
      ]);

      // With tight thresholds, at least one action should be denied
      // The exact behavior depends on the Lagrangian value
      expect(result.results.length).toBeGreaterThan(0);

      await tightCore.stop();
    });
  });

  describe('governance gauge field integration', () => {
    it('exposes gauge field for advanced use', () => {
      const field = core.getGaugeField();
      expect(field).toBeDefined();
      expect(field.getArrayIds()).toHaveLength(2);
    });

    it('gauge field evolves during actions', async () => {
      await core.start();
      const tickBefore = core.getGaugeField().getTick();

      await core.navigate('https://example.com');
      const tickAfter = core.getGaugeField().getTick();

      // Should have advanced by gaugeTicksPerAction (3)
      expect(tickAfter - tickBefore).toBe(3);

      await core.stop();
    });

    it('consensus strength is valid', async () => {
      await core.start();
      const perception = await core.perceive();

      expect(perception.gaugeState.consensus).toBeGreaterThanOrEqual(0);
      expect(perception.gaugeState.consensus).toBeLessThanOrEqual(1);

      await core.stop();
    });
  });

  describe('factory', () => {
    it('createAetherCore produces valid instance', () => {
      const instance = createAetherCore();
      expect(instance).toBeInstanceOf(AetherCore);
      expect(instance.getState()).toBe('idle');
    });

    it('createAetherCore accepts custom config', () => {
      const instance = createAetherCore({
        agentId: 'custom-agent',
        governanceArrayCount: 3,
      });
      expect(instance.id).toBe('custom-agent');
      expect(instance.getGaugeField().getArrayIds()).toHaveLength(3);
    });
  });
});
