/**
 * @file fluxState.test.ts
 * @description Tests for flux-state access tiering.
 *
 * Verifies that navigation operations are properly restricted
 * based on the entity's current flux state.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  FluxState,
  NavigationOp,
  FluxStateGate,
  FLUX_POLICIES,
  getValidTransitions,
  coherenceToFluxState,
  RealmID,
} from '../../src/harmonic/fluxState';

describe('FluxState', () => {
  // ═══════════════════════════════════════════════════════════════
  // Policy Definitions
  // ═══════════════════════════════════════════════════════════════

  describe('FLUX_POLICIES', () => {
    it('should define policies for all flux states', () => {
      expect(FLUX_POLICIES[FluxState.POLLY]).toBeDefined();
      expect(FLUX_POLICIES[FluxState.SUPERPOSITION]).toBeDefined();
      expect(FLUX_POLICIES[FluxState.COLLAPSED]).toBeDefined();
      expect(FLUX_POLICIES[FluxState.ENTANGLED]).toBeDefined();
    });

    it('POLLY should allow all operations', () => {
      const policy = FLUX_POLICIES[FluxState.POLLY];
      expect(policy.allowedOps).toContain(NavigationOp.FULL_NAVIGATE);
      expect(policy.allowedOps).toContain(NavigationOp.ENCRYPT_TRANSPORT);
      expect(policy.allowedRealms).toBeNull(); // all realms
      expect(policy.maxStepNorm).toBeNull(); // no limit
      expect(policy.canEncrypt).toBe(true);
    });

    it('SUPERPOSITION should restrict realms', () => {
      const policy = FLUX_POLICIES[FluxState.SUPERPOSITION];
      expect(policy.allowedRealms).toEqual(['KO', 'AV', 'RU']);
      expect(policy.maxStepNorm).toBe(0.3);
      expect(policy.canEncrypt).toBe(true);
    });

    it('COLLAPSED should have minimal access', () => {
      const policy = FLUX_POLICIES[FluxState.COLLAPSED];
      expect(policy.allowedOps).toContain(NavigationOp.LIMBIC_ONLY);
      expect(policy.allowedOps).not.toContain(NavigationOp.FULL_NAVIGATE);
      expect(policy.canEncrypt).toBe(false);
    });

    it('ENTANGLED should restrict to security-related realms', () => {
      const policy = FLUX_POLICIES[FluxState.ENTANGLED];
      expect(policy.allowedRealms).toEqual(['KO', 'RU', 'UM']);
      expect(policy.canEncrypt).toBe(true);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // FluxStateGate
  // ═══════════════════════════════════════════════════════════════

  describe('FluxStateGate', () => {
    let gate: FluxStateGate;

    beforeEach(() => {
      gate = new FluxStateGate(FluxState.POLLY);
    });

    it('should initialize with given state', () => {
      expect(gate.getState()).toBe(FluxState.POLLY);
    });

    it('should return the current policy', () => {
      const policy = gate.getPolicy();
      expect(policy.allowedRealms).toBeNull();
    });

    describe('POLLY state navigation checks', () => {
      it('should allow navigation to any realm', () => {
        const realms: RealmID[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
        for (const realm of realms) {
          const result = gate.checkNavigation(realm, [0.1, 0, 0, 0, 0, 0]);
          expect(result.allowed).toBe(true);
        }
      });

      it('should allow any step magnitude', () => {
        const result = gate.checkNavigation('KO', [0.9, 0, 0, 0, 0, 0]);
        expect(result.allowed).toBe(true);
      });

      it('should allow encryption', () => {
        const result = gate.checkEncrypt();
        expect(result.allowed).toBe(true);
      });
    });

    describe('SUPERPOSITION state navigation checks', () => {
      beforeEach(() => {
        gate = new FluxStateGate(FluxState.SUPERPOSITION);
      });

      it('should allow navigation to KO, AV, RU', () => {
        expect(gate.checkNavigation('KO', [0.1, 0, 0, 0, 0, 0]).allowed).toBe(true);
        expect(gate.checkNavigation('AV', [0.1, 0, 0, 0, 0, 0]).allowed).toBe(true);
        expect(gate.checkNavigation('RU', [0.1, 0, 0, 0, 0, 0]).allowed).toBe(true);
      });

      it('should deny navigation to CA, UM, DR', () => {
        expect(gate.checkNavigation('CA', [0.1, 0, 0, 0, 0, 0]).allowed).toBe(false);
        expect(gate.checkNavigation('UM', [0.1, 0, 0, 0, 0, 0]).allowed).toBe(false);
        expect(gate.checkNavigation('DR', [0.1, 0, 0, 0, 0, 0]).allowed).toBe(false);
      });

      it('should deny steps exceeding max norm', () => {
        const result = gate.checkNavigation('KO', [0.5, 0, 0, 0, 0, 0]);
        expect(result.allowed).toBe(false);
        expect(result.reason).toContain('magnitude');
      });

      it('should allow steps within max norm', () => {
        const result = gate.checkNavigation('KO', [0.2, 0.1, 0, 0, 0, 0]);
        expect(result.allowed).toBe(true);
      });
    });

    describe('COLLAPSED state navigation checks', () => {
      beforeEach(() => {
        gate = new FluxStateGate(FluxState.COLLAPSED);
      });

      it('should deny encryption', () => {
        expect(gate.checkEncrypt().allowed).toBe(false);
      });

      it('should enforce limbic-only (nearest realm)', () => {
        // Position near KO realm center [0.3, 0, 0, 0, 0, 0]
        const position = [0.25, 0.01, 0, 0, 0, 0];

        const koResult = gate.checkCollapsedRealm(position, 'KO');
        expect(koResult.allowed).toBe(true);

        const avResult = gate.checkCollapsedRealm(position, 'AV');
        expect(avResult.allowed).toBe(false);
        expect(avResult.reason).toContain('nearest realm KO');
      });

      it('should deny steps exceeding max norm', () => {
        const result = gate.checkNavigation('KO', [0.2, 0, 0, 0, 0, 0]);
        expect(result.allowed).toBe(false);
      });

      it('should allow small steps', () => {
        const result = gate.checkNavigation('KO', [0.05, 0, 0, 0, 0, 0]);
        expect(result.allowed).toBe(true);
      });
    });

    describe('ENTANGLED state', () => {
      it('should track partner ID', () => {
        const entangled = new FluxStateGate(FluxState.ENTANGLED, 'partner-123');
        expect(entangled.getPartnerId()).toBe('partner-123');
      });

      it('should allow navigation to KO, RU, UM', () => {
        const entangled = new FluxStateGate(FluxState.ENTANGLED);
        expect(entangled.checkNavigation('KO', [0.1, 0, 0, 0, 0, 0]).allowed).toBe(true);
        expect(entangled.checkNavigation('RU', [0.1, 0, 0, 0, 0, 0]).allowed).toBe(true);
        expect(entangled.checkNavigation('UM', [0.1, 0, 0, 0, 0, 0]).allowed).toBe(true);
      });

      it('should deny navigation to AV, CA, DR', () => {
        const entangled = new FluxStateGate(FluxState.ENTANGLED);
        expect(entangled.checkNavigation('AV', [0.1, 0, 0, 0, 0, 0]).allowed).toBe(false);
        expect(entangled.checkNavigation('CA', [0.1, 0, 0, 0, 0, 0]).allowed).toBe(false);
        expect(entangled.checkNavigation('DR', [0.1, 0, 0, 0, 0, 0]).allowed).toBe(false);
      });
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // State Transitions
  // ═══════════════════════════════════════════════════════════════

  describe('State Transitions', () => {
    it('should allow POLLY → SUPERPOSITION', () => {
      const gate = new FluxStateGate(FluxState.POLLY);
      const result = gate.transition(FluxState.SUPERPOSITION);
      expect(result.success).toBe(true);
      expect(gate.getState()).toBe(FluxState.SUPERPOSITION);
    });

    it('should allow POLLY → COLLAPSED', () => {
      const gate = new FluxStateGate(FluxState.POLLY);
      expect(gate.transition(FluxState.COLLAPSED).success).toBe(true);
    });

    it('should allow POLLY → ENTANGLED', () => {
      const gate = new FluxStateGate(FluxState.POLLY);
      expect(gate.transition(FluxState.ENTANGLED).success).toBe(true);
    });

    it('should deny COLLAPSED → SUPERPOSITION', () => {
      const gate = new FluxStateGate(FluxState.COLLAPSED);
      const result = gate.transition(FluxState.SUPERPOSITION);
      expect(result.success).toBe(false);
      expect(result.reason).toContain('Cannot transition');
    });

    it('should allow COLLAPSED → POLLY (re-authentication)', () => {
      const gate = new FluxStateGate(FluxState.COLLAPSED);
      expect(gate.transition(FluxState.POLLY).success).toBe(true);
    });

    it('should deny COLLAPSED → ENTANGLED', () => {
      const gate = new FluxStateGate(FluxState.COLLAPSED);
      expect(gate.transition(FluxState.ENTANGLED).success).toBe(false);
    });

    it('should allow ENTANGLED → POLLY (disentanglement)', () => {
      const gate = new FluxStateGate(FluxState.ENTANGLED, 'partner');
      expect(gate.transition(FluxState.POLLY).success).toBe(true);
      expect(gate.getPartnerId()).toBeUndefined();
    });

    it('should clear partner ID on non-entangled transition', () => {
      const gate = new FluxStateGate(FluxState.ENTANGLED, 'partner');
      gate.transition(FluxState.COLLAPSED);
      expect(gate.getPartnerId()).toBeUndefined();
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Helper Functions
  // ═══════════════════════════════════════════════════════════════

  describe('Helper Functions', () => {
    it('should list valid transitions', () => {
      const pollyTransitions = getValidTransitions(FluxState.POLLY);
      expect(pollyTransitions).toContain(FluxState.SUPERPOSITION);
      expect(pollyTransitions).toContain(FluxState.COLLAPSED);
      expect(pollyTransitions).toContain(FluxState.ENTANGLED);

      const collapsedTransitions = getValidTransitions(FluxState.COLLAPSED);
      expect(collapsedTransitions).toEqual([FluxState.POLLY]);
    });

    it('should map coherence to flux state', () => {
      expect(coherenceToFluxState(1.0)).toBe(FluxState.POLLY);
      expect(coherenceToFluxState(0.85)).toBe(FluxState.POLLY);
      expect(coherenceToFluxState(0.6)).toBe(FluxState.SUPERPOSITION);
      expect(coherenceToFluxState(0.3)).toBe(FluxState.ENTANGLED);
      expect(coherenceToFluxState(0.1)).toBe(FluxState.COLLAPSED);
      expect(coherenceToFluxState(0.0)).toBe(FluxState.COLLAPSED);
    });

    it('should clamp coherence values', () => {
      expect(coherenceToFluxState(-0.5)).toBe(FluxState.COLLAPSED);
      expect(coherenceToFluxState(1.5)).toBe(FluxState.POLLY);
    });
  });
});
