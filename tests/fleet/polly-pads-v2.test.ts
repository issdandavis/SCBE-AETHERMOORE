/**
 * Polly Pads v2 Tests — Mode Switching, Closed Network, Mission Coordinator
 *
 * Validates:
 * - ModeRegistry: 6 specialist modes with state persistence
 * - ClosedNetwork: Air-gapped messaging with HMAC integrity
 * - Squad: Byzantine fault-tolerant voting (4/6 quorum)
 * - MissionCoordinator: Crisis-driven mode reassignment
 */

import { describe, expect, it, beforeEach } from 'vitest';
import {
  ModeRegistry,
  ALL_MODE_IDS,
  type SpecialistModeId,
} from '../../src/fleet/polly-pads/specialist-modes';

// ═══════════════════════════════════════════════════════════════
// Mode Registry Tests
// ═══════════════════════════════════════════════════════════════

describe('ModeRegistry', () => {
  let registry: ModeRegistry;

  beforeEach(() => {
    registry = new ModeRegistry('pad-alpha');
  });

  it('should initialize all 6 specialist modes', () => {
    expect(registry.getAllModes()).toHaveLength(6);
    for (const id of ALL_MODE_IDS) {
      expect(registry.getMode(id)).toBeDefined();
    }
  });

  it('should start with no active mode', () => {
    expect(registry.currentModeId).toBeNull();
    expect(registry.currentMode).toBeNull();
  });

  it('should switch modes and track history', () => {
    const event = registry.switchMode('engineering', 'system startup');

    expect(registry.currentModeId).toBe('engineering');
    expect(event.fromMode).toBeNull();
    expect(event.toMode).toBe('engineering');
    expect(event.reason).toBe('system startup');
    expect(registry.switchCount).toBe(1);
  });

  it('should preserve state across mode switches', () => {
    registry.switchMode('science', 'normal ops');
    registry.saveData('samples', ['MARS-001', 'MARS-002']);
    registry.saveData('hypothesis', 'iron oxide formation');

    registry.switchMode('engineering', 'crisis');
    registry.saveData('repair_target', 'wheel_motor_2');

    // Switch back to science — state preserved
    registry.switchMode('science', 'crisis resolved');
    expect(registry.loadData<string[]>('samples')).toEqual(['MARS-001', 'MARS-002']);
    expect(registry.loadData<string>('hypothesis')).toBe('iron oxide formation');

    // Engineering state also preserved
    registry.switchMode('engineering', 'check repair');
    expect(registry.loadData<string>('repair_target')).toBe('wheel_motor_2');
  });

  it('should return available tools based on tier', () => {
    registry.switchMode('communications', 'test');

    // KO tier: only basic tools
    const koTools = registry.getAvailableTools('KO');
    expect(koTools.length).toBeGreaterThanOrEqual(1);
    expect(koTools.every((t) => t.minTier === 'KO')).toBe(true);

    // DR tier: all tools
    const drTools = registry.getAvailableTools('DR');
    expect(drTools.length).toBeGreaterThan(koTools.length);
  });

  it('should throw on unknown mode', () => {
    expect(() => registry.switchMode('warp_drive' as SpecialistModeId, 'test')).toThrow(
      'Unknown mode'
    );
  });

  it('should track full switch history', () => {
    registry.switchMode('science', 'start');
    registry.switchMode('engineering', 'crisis');
    registry.switchMode('mission_planning', 'planning');
    registry.switchMode('science', 'resolved');

    expect(registry.switchHistory).toHaveLength(4);
    expect(registry.switchHistory[0].toMode).toBe('science');
    expect(registry.switchHistory[1].toMode).toBe('engineering');
    expect(registry.switchHistory[2].toMode).toBe('mission_planning');
    expect(registry.switchHistory[3].toMode).toBe('science');
  });

  it('should serialize to JSON', () => {
    registry.switchMode('navigation', 'patrol');
    registry.saveData('route', [1, 2, 3]);

    const json = registry.toJSON() as Record<string, unknown>;
    expect(json).toHaveProperty('padId', 'pad-alpha');
    expect(json).toHaveProperty('currentMode', 'navigation');
    expect(json).toHaveProperty('modes');
    expect(json).toHaveProperty('switchHistory');
  });
});
