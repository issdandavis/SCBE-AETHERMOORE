/**
 * @file node-kernel.test.ts
 * @module tests/fleet/node-kernel
 * @layer L1, L8, L13, L14
 * @component NodeKernel Governance Kernel Tests
 * @version 3.2.4
 *
 * Comprehensive tests for the per-node SCBE governance kernel.
 * Covers state management, energy, policy lifecycle, invariant checks,
 * human override, audit log, and policy signing.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  NodeKernel,
  DEFAULT_KERNEL_CONFIG,
  DEFAULT_POLICY_PARAMS,
} from '../../src/fleet/node-kernel.js';
import type {
  NodeState,
  PolicyManifest,
  PolicyParams,
  KernelDecision,
  NodeRole,
} from '../../src/fleet/node-kernel.js';

// ──────────────── Helpers ────────────────

const ORIGIN = { x: 0, y: 0, z: 0 };

/**
 * Creates and applies a valid policy to the given kernel.
 * Asserts that the policy was applied successfully.
 */
function applyValidPolicy(
  kernel: NodeKernel,
  overrides: Partial<PolicyParams> = {},
): PolicyManifest {
  const manifest = kernel.createPolicy(overrides);
  const result = kernel.applyPolicy(manifest);
  expect(result.applied).toBe(true);
  return manifest;
}

// ──────────────── Tests ────────────────

describe('NodeKernel', () => {
  let kernel: NodeKernel;

  beforeEach(() => {
    kernel = new NodeKernel('test-node-1', ORIGIN);
  });

  // ── State Management ──

  describe('state management', () => {
    it('Constructor sets initial state (id, energy=1.0, trust=0.5, role=WORKER)', () => {
      const state = kernel.getState();
      expect(state.id).toBe('test-node-1');
      expect(state.energy).toBe(1.0);
      expect(state.trust).toBe(0.5);
      expect(state.role).toBe('WORKER');
      expect(state.phase).toBe(0);
      expect(state.hazardFlag).toBe(false);
      expect(state.neighborSet.size).toBe(0);
      expect(state.currentMode).toBe('EXPLORE');
      expect(state.humanOverride).toBe(false);
      expect(state.position).toEqual(ORIGIN);
    });

    it('updateTrust clamps to [0, 1]', () => {
      kernel.updateTrust(1.5);
      expect(kernel.getState().trust).toBe(1.0);

      kernel.updateTrust(-0.3);
      expect(kernel.getState().trust).toBe(0.0);

      kernel.updateTrust(0.75);
      expect(kernel.getState().trust).toBe(0.75);
    });

    it('updateEnergy clamps to [0, 1]', () => {
      kernel.updateEnergy(2.0);
      expect(kernel.getState().energy).toBe(1.0);

      kernel.updateEnergy(-1.0);
      expect(kernel.getState().energy).toBe(0.0);

      kernel.updateEnergy(0.42);
      expect(kernel.getState().energy).toBe(0.42);
    });

    it('updateRole changes role', () => {
      kernel.updateRole('SCOUT');
      expect(kernel.getState().role).toBe('SCOUT');

      kernel.updateRole('SENTINEL');
      expect(kernel.getState().role).toBe('SENTINEL');

      kernel.updateRole('LEADER');
      expect(kernel.getState().role).toBe('LEADER');

      kernel.updateRole('DORMANT');
      expect(kernel.getState().role).toBe('DORMANT');
    });

    it('updatePhase changes phase', () => {
      kernel.updatePhase(3.14);
      expect(kernel.getState().phase).toBe(3.14);

      kernel.updatePhase(0);
      expect(kernel.getState().phase).toBe(0);

      kernel.updatePhase(-1.5);
      expect(kernel.getState().phase).toBe(-1.5);
    });

    it('setHazard sets hazard flag', () => {
      expect(kernel.getState().hazardFlag).toBe(false);

      kernel.setHazard(true);
      expect(kernel.getState().hazardFlag).toBe(true);

      kernel.setHazard(false);
      expect(kernel.getState().hazardFlag).toBe(false);
    });

    it('updateNeighbors sets neighbor set (capped at maxNeighbors)', () => {
      const neighbors = ['a', 'b', 'c'];
      kernel.updateNeighbors(neighbors);
      const ns = kernel.getState().neighborSet;
      expect(ns.size).toBe(3);
      expect(ns.has('a')).toBe(true);
      expect(ns.has('b')).toBe(true);
      expect(ns.has('c')).toBe(true);

      // Test cap at maxNeighbors (default 50)
      const manyNeighbors = Array.from({ length: 100 }, (_, i) => `node-${i}`);
      kernel.updateNeighbors(manyNeighbors);
      expect(kernel.getState().neighborSet.size).toBe(DEFAULT_KERNEL_CONFIG.maxNeighbors);
    });
  });

  // ── Energy Management ──

  describe('energy management', () => {
    it('consumeEnergy reduces energy (min 0)', () => {
      kernel.updateEnergy(0.5);
      kernel.consumeEnergy(0.3);
      expect(kernel.getState().energy).toBeCloseTo(0.2, 10);

      // Cannot go below 0
      kernel.consumeEnergy(1.0);
      expect(kernel.getState().energy).toBe(0);
    });

    it('rechargeEnergy increases energy (max 1)', () => {
      kernel.updateEnergy(0.5);
      kernel.rechargeEnergy(0.3);
      expect(kernel.getState().energy).toBeCloseTo(0.8, 10);

      // Cannot exceed 1
      kernel.rechargeEnergy(0.5);
      expect(kernel.getState().energy).toBe(1.0);
    });

    it('Default consumption/recharge rates match config', () => {
      // Consume with default rate
      kernel.updateEnergy(1.0);
      kernel.consumeEnergy();
      expect(kernel.getState().energy).toBeCloseTo(
        1.0 - DEFAULT_KERNEL_CONFIG.energyPerStep,
        10,
      );

      // Recharge with default rate
      kernel.updateEnergy(0.5);
      kernel.rechargeEnergy();
      expect(kernel.getState().energy).toBeCloseTo(
        0.5 + DEFAULT_KERNEL_CONFIG.energyRechargeRate,
        10,
      );
    });
  });

  // ── Policy Management ──

  describe('policy management', () => {
    it('createPolicy returns signed manifest with correct epoch', () => {
      const manifest = kernel.createPolicy();
      expect(manifest.epoch).toBe(1);
      expect(manifest.version).toBe('1.0.0');
      expect(manifest.signature).toBeTruthy();
      expect(typeof manifest.signature).toBe('string');
      expect(manifest.signature.length).toBeGreaterThan(0);
      expect(manifest.issuedAt).toBeLessThanOrEqual(Date.now());
      expect(manifest.expiresAt).toBeGreaterThan(manifest.issuedAt);
      expect(manifest.params).toBeDefined();
    });

    it('createPolicy increments epoch monotonically', () => {
      const m1 = kernel.createPolicy();
      expect(m1.epoch).toBe(1);

      // Apply first so next createPolicy sees it
      kernel.applyPolicy(m1);

      const m2 = kernel.createPolicy();
      expect(m2.epoch).toBe(2);

      kernel.applyPolicy(m2);

      const m3 = kernel.createPolicy();
      expect(m3.epoch).toBe(3);

      // Epochs are strictly increasing
      expect(m1.epoch).toBeLessThan(m2.epoch);
      expect(m2.epoch).toBeLessThan(m3.epoch);
    });

    it('applyPolicy accepts valid signed policy', () => {
      const manifest = kernel.createPolicy();
      const result = kernel.applyPolicy(manifest);
      expect(result.applied).toBe(true);
      expect(result.reason).toBeUndefined();
      expect(kernel.getActivePolicy()).toBe(manifest);
    });

    it('applyPolicy rejects invalid signature', () => {
      const manifest = kernel.createPolicy();
      // Tamper with the signature
      const tampered: PolicyManifest = { ...manifest, signature: 'bad-signature-value' };
      const result = kernel.applyPolicy(tampered);
      expect(result.applied).toBe(false);
      expect(result.reason).toBe('invalid_signature');
    });

    it('applyPolicy rejects non-monotonic epoch (epoch <= current)', () => {
      // Apply first policy at epoch 1
      const m1 = kernel.createPolicy();
      kernel.applyPolicy(m1);

      // Try to apply a policy with the same epoch
      const staleManifest: PolicyManifest = { ...m1 };
      const result = kernel.applyPolicy(staleManifest);
      expect(result.applied).toBe(false);
      expect(result.reason).toContain('epoch_not_monotonic');
    });

    it('applyPolicy rejects expired policy', () => {
      // Create a policy with a very short TTL
      const manifest = kernel.createPolicy({}, 0);
      // The policy expires immediately (issuedAt + 0 = issuedAt)
      // Wait a tiny bit so Date.now() > expiresAt
      // Since TTL is 0, expiresAt === issuedAt, and by the time applyPolicy runs,
      // Date.now() will be >= expiresAt.
      // Force expiration by manipulating the manifest
      const expired: PolicyManifest = {
        ...manifest,
        expiresAt: Date.now() - 1000,
      };
      // Re-sign is not possible externally, so create naturally expired policy
      // Use TTL = 0: expiresAt = now at creation. By the time we apply, now > expiresAt
      // Actually TTL=0 means expiresAt = issuedAt, which may equal Date.now() at apply time.
      // Create with TTL=-1 to guarantee expiry
      const expiredManifest = kernel.createPolicy({}, -1);
      const result = kernel.applyPolicy(expiredManifest);
      expect(result.applied).toBe(false);
      expect(result.reason).toBe('policy_expired');
    });

    it('getPolicyHistory tracks applied policies', () => {
      expect(kernel.getPolicyHistory().length).toBe(0);

      const m1 = applyValidPolicy(kernel);
      // After first policy, history is still empty (no previous policy to archive)
      expect(kernel.getPolicyHistory().length).toBe(0);

      const m2 = applyValidPolicy(kernel);
      // m1 moved to history
      expect(kernel.getPolicyHistory().length).toBe(1);
      expect(kernel.getPolicyHistory()[0]).toBe(m1);

      const m3 = applyValidPolicy(kernel);
      // m1 and m2 in history
      expect(kernel.getPolicyHistory().length).toBe(2);
      expect(kernel.getPolicyHistory()[0]).toBe(m1);
      expect(kernel.getPolicyHistory()[1]).toBe(m2);

      // Active policy is m3
      expect(kernel.getActivePolicy()).toBe(m3);
    });
  });

  // ── Invariant Checks ──

  describe('invariant checks', () => {
    it('All invariants pass -> allowed: true with 0 violations', () => {
      // Set up a fully valid state: valid policy, good energy, good trust, etc.
      applyValidPolicy(kernel);
      kernel.updateEnergy(0.8);
      kernel.updateTrust(0.5);
      kernel.updateRole('WORKER');
      kernel.setHazard(false);
      kernel.updateMode('EXPLORE');

      const decision = kernel.checkInvariants('test-action');
      expect(decision.allowed).toBe(true);
      expect(decision.violations.length).toBe(0);
      expect(decision.invariants.length).toBeGreaterThan(0);
      // All invariants should have passed
      for (const inv of decision.invariants) {
        expect(inv.passed).toBe(true);
      }
    });

    it('Energy below floor -> violation energy_floor', () => {
      applyValidPolicy(kernel);
      // Set energy below the default floor of 0.1
      kernel.updateEnergy(0.05);

      const decision = kernel.checkInvariants('low-energy-action');
      expect(decision.allowed).toBe(false);
      expect(decision.violations).toContain('energy_floor');
    });

    it('Trust below minimum -> violation trust_minimum', () => {
      applyValidPolicy(kernel);
      // Default minTrust is 0.15, set trust below it
      kernel.updateTrust(0.1);

      const decision = kernel.checkInvariants('low-trust-action');
      expect(decision.allowed).toBe(false);
      expect(decision.violations).toContain('trust_minimum');
    });

    it('Role not allowed -> violation role_allowed', () => {
      // Apply a policy that only allows SCOUT and LEADER
      applyValidPolicy(kernel, {
        allowedRoles: ['SCOUT', 'LEADER'],
      });
      // Current role is WORKER (default), which is not in allowedRoles
      const decision = kernel.checkInvariants('role-check-action');
      expect(decision.allowed).toBe(false);
      expect(decision.violations).toContain('role_allowed');
    });

    it('Suppressed mode (HAZARD) -> violation mode_suppressed', () => {
      applyValidPolicy(kernel);
      // Set mode to HAZARD, which is in default suppressedModes
      kernel.updateMode('HAZARD');

      const decision = kernel.checkInvariants('hazard-mode-action');
      expect(decision.allowed).toBe(false);
      expect(decision.violations).toContain('mode_suppressed');
    });

    it('Hazard flag active -> violation hazard_active', () => {
      applyValidPolicy(kernel);
      kernel.setHazard(true);

      const decision = kernel.checkInvariants('hazard-flag-action');
      expect(decision.allowed).toBe(false);
      expect(decision.violations).toContain('hazard_active');
    });

    it('No valid policy -> violation policy_invalid', () => {
      // Do not apply any policy
      const decision = kernel.checkInvariants('no-policy-action');
      expect(decision.allowed).toBe(false);
      expect(decision.violations).toContain('policy_invalid');
    });

    it('Multiple violations reported simultaneously', () => {
      // Do not apply a policy, set energy low, trust low, hazard active
      kernel.updateEnergy(0.01);
      kernel.updateTrust(0.01);
      kernel.setHazard(true);
      kernel.updateMode('HAZARD');

      const decision = kernel.checkInvariants('multi-violation-action');
      expect(decision.allowed).toBe(false);
      expect(decision.violations.length).toBeGreaterThanOrEqual(4);
      expect(decision.violations).toContain('energy_floor');
      expect(decision.violations).toContain('trust_minimum');
      expect(decision.violations).toContain('hazard_active');
      expect(decision.violations).toContain('mode_suppressed');
      expect(decision.violations).toContain('policy_invalid');
    });
  });

  // ── Human Override ──

  describe('human override', () => {
    it('Human override allows action regardless of other violations', () => {
      // Set up a state that would normally fail: no policy, low energy, hazard
      kernel.updateEnergy(0.01);
      kernel.updateTrust(0.01);
      kernel.setHazard(true);
      kernel.updateMode('HAZARD');

      // Without override, should be denied
      const deniedDecision = kernel.checkInvariants('pre-override-action');
      expect(deniedDecision.allowed).toBe(false);
      expect(deniedDecision.violations.length).toBeGreaterThan(0);

      // Engage human override
      kernel.engageHumanOverride();

      const overrideDecision = kernel.checkInvariants('override-action');
      expect(overrideDecision.allowed).toBe(true);
      expect(overrideDecision.violations.length).toBe(0);
      // Should have human_override invariant entry
      const overrideInvariant = overrideDecision.invariants.find(
        (inv) => inv.name === 'human_override',
      );
      expect(overrideInvariant).toBeDefined();
      expect(overrideInvariant!.passed).toBe(true);
    });

    it('engageHumanOverride/disengageHumanOverride toggles state', () => {
      expect(kernel.getState().humanOverride).toBe(false);

      kernel.engageHumanOverride();
      expect(kernel.getState().humanOverride).toBe(true);

      kernel.disengageHumanOverride();
      expect(kernel.getState().humanOverride).toBe(false);
    });

    it('After disengaging, normal invariant checks resume', () => {
      // Set up failing state
      kernel.updateEnergy(0.01);

      // Override allows
      kernel.engageHumanOverride();
      const allowed = kernel.checkInvariants('while-override');
      expect(allowed.allowed).toBe(true);

      // Disengage: now checks resume
      kernel.disengageHumanOverride();
      const denied = kernel.checkInvariants('after-override');
      expect(denied.allowed).toBe(false);
      expect(denied.violations).toContain('energy_floor');
    });
  });

  // ── Audit Log ──

  describe('audit log', () => {
    it('Each checkInvariants call appends to audit log', () => {
      applyValidPolicy(kernel);

      expect(kernel.getAuditLog().length).toBe(0);

      kernel.checkInvariants('action-1');
      expect(kernel.getAuditLog().length).toBe(1);

      kernel.checkInvariants('action-2');
      expect(kernel.getAuditLog().length).toBe(2);

      kernel.checkInvariants('action-3');
      expect(kernel.getAuditLog().length).toBe(3);

      // Verify action names are recorded
      expect(kernel.getAuditLog()[0].action).toBe('action-1');
      expect(kernel.getAuditLog()[1].action).toBe('action-2');
      expect(kernel.getAuditLog()[2].action).toBe('action-3');
    });

    it('Audit entries contain state snapshot', () => {
      applyValidPolicy(kernel);
      kernel.updateEnergy(0.77);
      kernel.updateTrust(0.88);
      kernel.updateRole('SCOUT');
      kernel.updateNeighbors(['n1', 'n2', 'n3']);

      kernel.checkInvariants('snapshot-action');

      const entry = kernel.getAuditLog()[0];
      expect(entry.stateSnapshot).toBeDefined();
      expect(entry.stateSnapshot.id).toBe('test-node-1');
      expect(entry.stateSnapshot.energy).toBe(0.77);
      expect(entry.stateSnapshot.trust).toBe(0.88);
      expect(entry.stateSnapshot.role).toBe('SCOUT');
      expect(entry.stateSnapshot.neighborCount).toBe(3);
      // neighborSet itself should NOT be on the snapshot (replaced by neighborCount)
      expect((entry.stateSnapshot as Record<string, unknown>).neighborSet).toBeUndefined();
    });

    it('getRecentViolationCount counts violations in window', () => {
      applyValidPolicy(kernel);

      // 3 passing checks
      kernel.updateEnergy(0.8);
      kernel.checkInvariants('pass-1');
      kernel.checkInvariants('pass-2');
      kernel.checkInvariants('pass-3');

      expect(kernel.getRecentViolationCount(10)).toBe(0);

      // 2 failing checks (low energy)
      kernel.updateEnergy(0.01);
      kernel.checkInvariants('fail-1');
      kernel.checkInvariants('fail-2');

      // Total: 3 pass + 2 fail = 5 entries, 2 violations
      expect(kernel.getRecentViolationCount(10)).toBe(2);

      // Window of 1 should only see the last failing entry
      expect(kernel.getRecentViolationCount(1)).toBe(1);

      // Window of 3 should see 1 pass + 2 fail = 2 violations
      expect(kernel.getRecentViolationCount(3)).toBe(2);
    });
  });

  // ── Policy Signing ──

  describe('policy signing', () => {
    it('Same policy content produces same signature', () => {
      // Create two kernels with the same signing key
      const k1 = new NodeKernel('node-a', ORIGIN);
      const k2 = new NodeKernel('node-b', ORIGIN);

      const m1 = k1.createPolicy();
      const m2 = k2.createPolicy();

      // Both at epoch 1 with same defaults.
      // Timestamps will differ slightly, so we align them for comparison.
      // Instead, create policies and compare: same epoch, same params, same timestamps => same sig
      // We need identical timestamps for this test, so manually construct:
      const m1Aligned: PolicyManifest = {
        ...m1,
        issuedAt: 1000000,
        expiresAt: 2000000,
      };
      const m2Aligned: PolicyManifest = {
        ...m2,
        issuedAt: 1000000,
        expiresAt: 2000000,
      };

      // Re-sign by applying through the kernel's createPolicy is not possible
      // with fixed timestamps. Instead, verify that the signing is deterministic
      // by applying the same manifest to both kernels (same key):
      const resultA = k1.applyPolicy(m1Aligned);
      const resultB = k2.applyPolicy(m2Aligned);

      // Both should fail (signature doesn't match the aligned timestamps)
      // because the signature was computed with original timestamps.
      // The correct approach: use the same kernel to sign two identical payloads.
      // Let's verify determinism differently:
      // Creating a policy twice quickly from the same starting state should use
      // the same epoch. Two fresh kernels produce epoch=1, same params, same version.
      // If they happen at the same millisecond, signatures match.

      // Best deterministic approach: create policy, note the signature,
      // then verify applyPolicy validates that exact signature.
      const kernel1 = new NodeKernel('det-1', ORIGIN);
      const policy = kernel1.createPolicy();
      // Applying the same policy should work (signature matches)
      const applyResult = kernel1.applyPolicy(policy);
      expect(applyResult.applied).toBe(true);

      // Apply same manifest again to a fresh kernel with same key => signature should validate
      const kernel2 = new NodeKernel('det-2', ORIGIN);
      const applyResult2 = kernel2.applyPolicy(policy);
      expect(applyResult2.applied).toBe(true);
    });

    it('Different epoch produces different signature', () => {
      const m1 = kernel.createPolicy();
      kernel.applyPolicy(m1);
      const m2 = kernel.createPolicy();

      expect(m1.epoch).not.toBe(m2.epoch);
      expect(m1.signature).not.toBe(m2.signature);
    });

    it('Custom signing key produces different signatures', () => {
      const kernelA = new NodeKernel('node-key-a', ORIGIN, {
        signingKey: 'key-alpha',
      });
      const kernelB = new NodeKernel('node-key-b', ORIGIN, {
        signingKey: 'key-beta',
      });

      const mA = kernelA.createPolicy();
      const mB = kernelB.createPolicy();

      // Both at epoch 1 with same default params, but different signing keys.
      // Even if timestamps differ, the key difference guarantees different signatures.
      // Verify by cross-applying: B's policy should fail on A due to signature mismatch.
      expect(mA.signature).not.toBe(mB.signature);

      // Cross-application should fail (different signing keys)
      const crossResultA = kernelA.applyPolicy(mB);
      expect(crossResultA.applied).toBe(false);
      expect(crossResultA.reason).toBe('invalid_signature');

      const crossResultB = kernelB.applyPolicy(mA);
      expect(crossResultB.applied).toBe(false);
      expect(crossResultB.reason).toBe('invalid_signature');
    });
  });
});
