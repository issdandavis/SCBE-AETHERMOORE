/**
 * @file manufacturing-scenarios.spec.ts
 * @module tests/cross-industry/manufacturing
 * @description Manufacturing / OT (Operational Technology) governance test scenarios
 *
 * Tests the 14-layer governance pipeline for industrial control security:
 * - Robot and process control commands
 * - Configuration changes
 * - Anomaly detection (slow-burn drift)
 * - Critical phase protection
 * - Emergency stop authorization
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  GovernanceEngine,
  createTestEngine,
  createValidContext,
  createValidEnvelope,
  applyAttack,
  createEntropyAttack,
  Context9D,
  SealedEnvelope,
} from '../common/index.js';

describe('Cross-Industry: Manufacturing / OT', () => {
  let engine: GovernanceEngine;
  let validContext: Context9D;
  let validEnvelope: SealedEnvelope;

  beforeEach(() => {
    engine = createTestEngine('manufacturing');
    validContext = createValidContext();
    validEnvelope = createValidEnvelope({ action: 'config-change', lineId: 'LINE-A1' });
  });

  describe('Happy Path: Normal Operations', () => {
    it('should ALLOW routine configuration change', () => {
      const context: Context9D = {
        ...validContext,
        identity: [0.12, 0.18, 0.15], // Close to normal-ops realm
        trajectory: [0.1, 0.12, 0.11, 0.13], // Stable trajectory
        commitment: 0.9,
      };
      const envelope = createValidEnvelope({
        action: 'config-change',
        lineId: 'LINE-A1',
        parameter: 'conveyor-speed',
        oldValue: 1.0,
        newValue: 1.1,
        operator: 'OP-456',
      });

      const result = engine.evaluate9D(context, envelope, 'config-change');

      expect(result.decision).toBe('ALLOW');
      expect(result.riskScore).toBeLessThan(0.4);
    });

    it('should ALLOW line start command', () => {
      const context: Context9D = {
        ...validContext,
        identity: [0.1, 0.2, 0.12],
        signatureFlag: true,
      };
      const envelope = createValidEnvelope({
        action: 'start',
        lineId: 'LINE-B2',
        operator: 'OP-789',
        shift: 'day',
      });

      const result = engine.evaluate9D(context, envelope, 'start');

      expect(result.decision).toBe('ALLOW');
    });

    it('should ALLOW scheduled maintenance stop', () => {
      const context: Context9D = {
        ...validContext,
        identity: [0.15, 0.22, 0.1],
        intentPhase: 0, // Maintenance intent
      };
      const envelope = createValidEnvelope({
        action: 'stop',
        lineId: 'LINE-A1',
        reason: 'scheduled-maintenance',
        maintenanceTicket: 'MT-2024-001',
      });

      const result = engine.evaluate9D(context, envelope, 'stop');

      expect(result.decision).toBe('ALLOW');
    });
  });

  describe('Edge Cases: Elevated Risk', () => {
    it('should QUARANTINE mid-process dangerous change', () => {
      const context: Context9D = {
        ...validContext,
        identity: [0.45, 0.48, 0.42], // Near critical-phase realm
        trajectory: [0.5, 0.52, 0.48, 0.51], // Active process
        timeFlow: 1.2, // Elevated time pressure
      };
      const envelope = createValidEnvelope({
        action: 'config-change',
        lineId: 'LINE-A1',
        parameter: 'robot-velocity',
        oldValue: 0.5,
        newValue: 1.5, // 3x increase
        processPhase: 'critical',
      });

      const result = engine.evaluate9D(context, envelope, 'config-change');

      expect(['QUARANTINE', 'DENY']).toContain(result.decision);
    });

    it('should QUARANTINE unauthorized operator', () => {
      const context: Context9D = {
        ...validContext,
        identity: [0.15, 0.2, 0.18],
        signatureFlag: false, // Not properly authenticated
        commitment: 0.4,
      };
      const envelope = createValidEnvelope({
        action: 'config-change',
        lineId: 'LINE-A1',
        operator: 'UNKNOWN',
      });

      const result = engine.evaluate9D(context, envelope, 'config-change');

      expect(['QUARANTINE', 'DENY']).toContain(result.decision);
    });

    it('should QUARANTINE command during active safety event', () => {
      const context: Context9D = {
        ...validContext,
        identity: [0.3, 0.35, 0.28],
        entropyDelta: 0.35, // Elevated entropy from safety event
      };
      const envelope = createValidEnvelope({
        action: 'start',
        lineId: 'LINE-C3',
        activeSafetyEvent: true,
        eventId: 'SAFETY-EVT-001',
      });

      const result = engine.evaluate9D(context, envelope, 'start');

      expect(['QUARANTINE', 'DENY']).toContain(result.decision);
    });
  });

  describe('Attack Scenarios: DENY Cases', () => {
    it('should DENY injection attack on control system', () => {
      const { context, envelope } = applyAttack('injection', validContext, validEnvelope);
      envelope.aad = {
        action: 'config-change',
        parameter: 'plc-register',
        value: 'MALICIOUS_PAYLOAD',
      };

      const result = engine.evaluate9D(context, envelope, 'config-change');

      expect(result.decision).toBe('DENY');
      expect(result.reason.toLowerCase()).toContain('poincare');
    });

    it('should DENY replay of old command', () => {
      const { context, envelope } = applyAttack('replay', validContext, validEnvelope);
      envelope.aad = {
        action: 'config-change',
        commandId: 'CMD-REPLAYED-OLD',
      };

      const result = engine.evaluate9D(context, envelope, 'config-change');

      expect(result.decision).toBe('DENY');
      expect(result.reason.toLowerCase()).toMatch(/replay|nonce/);
    });

    it('should DENY tampered safety override', () => {
      const { context, envelope } = applyAttack('tamper', validContext, validEnvelope);
      envelope.aad = {
        action: 'safety-override',
        reason: 'TAMPERED_JUSTIFICATION',
      };

      const result = engine.evaluate9D(context, envelope, 'safety-override');

      expect(result.decision).toBe('DENY');
    });

    it('should DENY remote access from untrusted network', () => {
      const context: Context9D = {
        ...validContext,
        identity: [0.9, 0.9, 0.85], // Far outside trusted realms
        signatureFlag: false,
      };
      const envelope = createValidEnvelope({
        action: 'config-change',
        lineId: 'LINE-A1',
        remoteAccess: true,
        sourceNetwork: 'EXTERNAL',
      });

      const result = engine.evaluate9D(context, envelope, 'config-change');

      expect(['DENY', 'QUARANTINE']).toContain(result.decision);
    });
  });

  describe('Slow-Burn Anomaly Detection', () => {
    it('should detect gradual entropy drift before critical threshold', () => {
      // Simulate gradual drift over time
      const driftLevels = [0.1, 0.2, 0.3, 0.4, 0.5];
      const results = driftLevels.map((entropy) => {
        const context = createEntropyAttack(validContext, entropy);
        context.identity = [0.12, 0.18, 0.15];
        return engine.evaluate9D(context, validEnvelope, 'config-change');
      });

      // Early drift should be allowed
      expect(results[0].decision).toBe('ALLOW');
      expect(results[1].decision).toBe('ALLOW');

      // Higher drift should trigger QUARANTINE before catastrophic
      const quarantineIndex = results.findIndex((r) => r.decision === 'QUARANTINE');
      expect(quarantineIndex).toBeGreaterThan(1);
      expect(quarantineIndex).toBeLessThan(results.length);
    });

    it('should flag spectral anomalies in sensor data', () => {
      const context: Context9D = {
        ...validContext,
        identity: [0.15, 0.2, 0.12],
        quantumState: [0.5, 0.5], // Non-normalized - sensor anomaly
        trajectory: [0.1, 0.5, 0.1, 0.5], // Oscillating - unusual pattern
      };

      const result = engine.evaluate9D(context, validEnvelope, 'config-change');

      // Spectral coherence should flag this
      const layer9 = result.layerBreakdown.find((l) => l.layer === 9);
      expect(layer9?.score).toBeLessThan(0.7);
    });

    it('should handle legitimate process variation', () => {
      const context: Context9D = {
        ...validContext,
        identity: [0.12, 0.19, 0.14],
        entropyDelta: 0.15, // Slight but acceptable variation
        quantumState: [0.98, 0.2], // Mostly coherent
      };
      const envelope = createValidEnvelope({
        action: 'config-change',
        lineId: 'LINE-A1',
        parameter: 'temperature-setpoint',
        variation: 'normal',
      });

      const result = engine.evaluate9D(context, envelope, 'config-change');

      expect(result.decision).toBe('ALLOW');
    });
  });

  describe('Critical Phase Protection', () => {
    it('should require multi-sig for emergency stop during production', () => {
      const context: Context9D = {
        ...validContext,
        identity: [0.52, 0.48, 0.5], // In critical-phase realm
        signatureFlag: false,
      };
      const envelope = createValidEnvelope({
        action: 'emergency-stop',
        lineId: 'LINE-A1',
        phase: 'production',
      });

      const result = engine.evaluate9D(context, envelope, 'emergency-stop');

      expect(['QUARANTINE', 'DENY']).toContain(result.decision);
      if (result.decision === 'QUARANTINE') {
        expect(result.reason.toLowerCase()).toContain('multi-sig');
      }
    });

    it('should ALLOW emergency stop with proper authorization', () => {
      const context: Context9D = {
        ...validContext,
        identity: [0.5, 0.5, 0.48],
        signatureFlag: true,
        commitment: 0.99,
      };
      const envelope = createValidEnvelope({
        action: 'emergency-stop',
        lineId: 'LINE-A1',
        reason: 'safety-hazard',
        authorizer: 'SAFETY-OFFICER-001',
        witnesses: ['OP-123', 'OP-456'],
      });

      // Add a realm that allows e-stop with multi-sig
      engine.addRealm({
        id: 'emergency-authorized',
        center: [0.5, 0.5],
        radius: 0.3,
        allowedActions: ['emergency-stop'],
        riskThreshold: 0.7,
        requiresMultiSig: true,
        multiSigThreshold: 2,
      });

      const result = engine.evaluate9D(context, envelope, 'emergency-stop');

      expect(['ALLOW', 'QUARANTINE']).toContain(result.decision);
    });
  });

  describe('Robot Safety', () => {
    it('should prevent unsafe velocity changes', () => {
      const context: Context9D = {
        ...validContext,
        identity: [0.2, 0.25, 0.18],
        trajectory: [0.5, 0.55, 0.58, 0.6], // Increasing trend
      };
      const envelope = createValidEnvelope({
        action: 'config-change',
        lineId: 'ROBOT-ARM-01',
        parameter: 'max-velocity',
        oldValue: 1.0,
        newValue: 5.0, // 5x increase
        safetyCheck: false,
      });

      const result = engine.evaluate9D(context, envelope, 'config-change');

      // Large velocity increases should be scrutinized
      expect(['QUARANTINE', 'DENY']).toContain(result.decision);
    });

    it('should ALLOW safe parameter adjustment', () => {
      const context: Context9D = {
        ...validContext,
        identity: [0.1, 0.2, 0.15],
      };
      const envelope = createValidEnvelope({
        action: 'config-change',
        lineId: 'ROBOT-ARM-01',
        parameter: 'max-velocity',
        oldValue: 1.0,
        newValue: 1.1, // 10% increase
        safetyCheck: true,
        safetyApproval: 'SAFETY-2024-001',
      });

      const result = engine.evaluate9D(context, envelope, 'config-change');

      expect(result.decision).toBe('ALLOW');
    });
  });

  describe('Supply Chain Integrity', () => {
    it('should verify firmware update authenticity', () => {
      const context: Context9D = {
        ...validContext,
        identity: [0.3, 0.28, 0.25],
        signatureFlag: true,
      };
      const envelope = createValidEnvelope({
        action: 'firmware-update',
        deviceId: 'PLC-001',
        version: '2.1.0',
        signedBy: 'VENDOR-CERT',
        hashVerified: true,
      });

      // Add firmware realm
      engine.addRealm({
        id: 'firmware-updates',
        center: [0.3, 0.3],
        radius: 0.25,
        allowedActions: ['firmware-update'],
        riskThreshold: 0.4,
        requiresMultiSig: true,
        multiSigThreshold: 2,
      });

      const result = engine.evaluate9D(context, envelope, 'firmware-update');

      expect(['ALLOW', 'QUARANTINE']).toContain(result.decision);
    });

    it('should DENY unsigned firmware', () => {
      const context: Context9D = {
        ...validContext,
        identity: [0.3, 0.28, 0.25],
        signatureFlag: false,
      };
      const envelope = createValidEnvelope({
        action: 'firmware-update',
        deviceId: 'PLC-001',
        version: '2.1.0-UNSIGNED',
        signedBy: null,
        hashVerified: false,
      });
      // Remove HMAC to simulate unsigned
      envelope.hmacChain = '';

      const result = engine.evaluate9D(context, envelope, 'firmware-update');

      expect(['DENY', 'QUARANTINE']).toContain(result.decision);
    });
  });
});
